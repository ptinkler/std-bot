import logging
from datetime import datetime, timedelta, timezone
from datetime import time as dtime
from zoneinfo import ZoneInfo

import discord

from bot_instance import bot
from helpers import WEEKDAY_NAMES, build_closed_poll_embed, build_poll_embed, date_label, fmt_date, parse_time, parse_weekday, resolve_expected_ids, upcoming_days
from models import TIMEZONES, PollData, RecurringPollConfig, active_polls, active_recurring_configs
from persistence import delete_poll, delete_recurring, save_poll, save_recurring, update_recurring

log = logging.getLogger(__name__)


class PollTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="One-time Poll", style=discord.ButtonStyle.primary, row=0)
    async def one_time(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EventModal())

    @discord.ui.button(label="Weekly Recurring Poll", style=discord.ButtonStyle.secondary, row=0)
    async def recurring(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RecurringSetupModal())

    @discord.ui.button(label="Manage Recurring Polls", style=discord.ButtonStyle.danger, row=1)
    async def manage(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_configs = [c for c in active_recurring_configs.values() if c.guild_id == interaction.guild_id]
        if not guild_configs:
            await interaction.response.send_message("No recurring polls set up in this server.", ephemeral=True)
            return
        view = ManageRecurringView(guild_configs)
        await interaction.response.send_message("Manage recurring polls:", view=view, ephemeral=True)


class RecurringSetupModal(discord.ui.Modal, title="Set Up Weekly Recurring Poll"):
    event_name = discord.ui.TextInput(label="Poll Name", max_length=100, placeholder="e.g. Weekly Game Night")
    description = discord.ui.TextInput(
        label="Description (optional)",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph,
    )
    post_day = discord.ui.TextInput(
        label="Post on which day?",
        placeholder="e.g. Thursday, Thurs, Thu",
        max_length=20,
    )
    post_time_input = discord.ui.TextInput(
        label="Post at what time? (UTC)",
        placeholder="e.g. 18:00, 1800, or 6:00 PM",
        max_length=15,
    )

    async def on_submit(self, interaction: discord.Interaction):
        weekday = parse_weekday(str(self.post_day))
        if weekday is None:
            await interaction.response.send_message(
                "Couldn't parse day. Use e.g. `Monday`, `Mon`, `Thurs`.", ephemeral=True
            )
            return
        t = parse_time(str(self.post_time_input))
        if t is None:
            await interaction.response.send_message(
                "Couldn't parse time. Use e.g. `18:00`, `1800`, or `6:00 PM`.", ephemeral=True
            )
            return
        view = RecurringRoleConfirmView(
            event_name=str(self.event_name),
            description=str(self.description or ""),
            creator_id=interaction.user.id,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            post_weekday=weekday,
            post_hour=t.hour,
            post_minute=t.minute,
        )
        day_name = WEEKDAY_NAMES[weekday]
        await interaction.response.send_message(
            f"**{self.event_name}** — every **{day_name}** at **{t.hour:02d}:{t.minute:02d} UTC**\nOptionally ping a role, then confirm:",
            view=view,
            ephemeral=True,
        )


class RecurringRoleConfirmView(discord.ui.View):
    def __init__(self, event_name, description, creator_id, guild_id, channel_id, post_weekday, post_hour, post_minute):
        super().__init__(timeout=300)
        self.event_name = event_name
        self.description = description
        self.creator_id = creator_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.post_weekday = post_weekday
        self.post_hour = post_hour
        self.post_minute = post_minute
        self.selected_role_id: int | None = None
        self.expected_ids: list[int] = []
        self.expected_role_id: int | None = None
        self.allow_cannot_attend = True

        self.role_select = discord.ui.RoleSelect(
            placeholder="Mention a role when posting? (optional)",
            min_values=0,
            max_values=1,
            row=0,
        )
        self.role_select.callback = self._on_role
        self.add_item(self.role_select)

        self.user_select = discord.ui.UserSelect(
            placeholder="Remind specific people? (optional)",
            min_values=0,
            max_values=25,
            row=1,
        )
        self.user_select.callback = self._on_users
        self.add_item(self.user_select)

        self.expected_role_select = discord.ui.RoleSelect(
            placeholder="Remind everyone in a role? (optional)",
            min_values=0,
            max_values=1,
            row=2,
        )
        self.expected_role_select.callback = self._on_expected_role
        self.add_item(self.expected_role_select)

        self.cannot_toggle = discord.ui.Button(
            label="🚫 \"Can't make any\" option: ON",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.cannot_toggle.callback = self._on_toggle_cannot
        self.add_item(self.cannot_toggle)

        self.confirm_btn = discord.ui.Button(
            label="Confirm & Save", style=discord.ButtonStyle.success, row=4
        )
        self.confirm_btn.callback = self._on_confirm
        self.add_item(self.confirm_btn)

    async def _on_role(self, interaction: discord.Interaction):
        self.selected_role_id = self.role_select.values[0].id if self.role_select.values else None
        await interaction.response.defer()

    async def _on_users(self, interaction: discord.Interaction):
        self.expected_ids = [u.id for u in self.user_select.values]
        await interaction.response.defer()

    async def _on_expected_role(self, interaction: discord.Interaction):
        self.expected_role_id = self.expected_role_select.values[0].id if self.expected_role_select.values else None
        await interaction.response.defer()

    async def _on_toggle_cannot(self, interaction: discord.Interaction):
        self.allow_cannot_attend = not self.allow_cannot_attend
        self.cannot_toggle.label = f"🚫 \"Can't make any\" option: {'ON' if self.allow_cannot_attend else 'OFF'}"
        await interaction.response.edit_message(view=self)

    async def _on_confirm(self, interaction: discord.Interaction):
        config = RecurringPollConfig(
            event_name=self.event_name,
            description=self.description,
            creator_id=self.creator_id,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            post_weekday=self.post_weekday,
            post_hour=self.post_hour,
            post_minute=self.post_minute,
            post_timezone="UTC",
            mention_role_id=self.selected_role_id,
            expected_respondent_ids=self.expected_ids,
            expected_role_id=self.expected_role_id,
            allow_cannot_attend=self.allow_cannot_attend,
        )
        config_id = save_recurring(config)
        config.id = config_id
        active_recurring_configs[config_id] = config
        day_name = WEEKDAY_NAMES[self.post_weekday]
        log.info("recurring poll saved id=%d name=%s", config_id, self.event_name)
        role_note = f" Pings <@&{self.selected_role_id}>." if self.selected_role_id else ""
        if self.expected_ids or self.expected_role_id:
            who = []
            if self.expected_ids:
                who.append(f"{len(self.expected_ids)} listed member(s)")
            if self.expected_role_id:
                who.append(f"everyone in <@&{self.expected_role_id}>")
            expected_note = f"\n⏳ Will remind {' and '.join(who)} who haven't responded ~24h before each reset."
        else:
            expected_note = ""
        await interaction.response.edit_message(
            content=(
                f"✅ **{self.event_name}** saved! Posts every **{day_name}** at "
                f"**{self.post_hour:02d}:{self.post_minute:02d} UTC** in this channel.{role_note}{expected_note}"
            ),
            view=None,
        )




class ManageRecurringView(discord.ui.View):
    def __init__(self, configs: list[RecurringPollConfig]):
        super().__init__(timeout=120)
        self.configs = configs
        self.selected: RecurringPollConfig | None = None

        options = [
            discord.SelectOption(
                label=c.event_name[:100],
                description=f"Every {WEEKDAY_NAMES[c.post_weekday]} at {c.post_hour:02d}:{c.post_minute:02d}",
                value=str(c.id),
            )
            for c in configs
        ]
        self.poll_select = discord.ui.Select(placeholder="Select recurring poll...", options=options, row=0)
        self.poll_select.callback = self._on_select
        self.add_item(self.poll_select)

        self.edit_btn = discord.ui.Button(
            label="Edit Respondents / Options", style=discord.ButtonStyle.primary, disabled=True, row=1
        )
        self.edit_btn.callback = self._on_edit
        self.add_item(self.edit_btn)

        self.cancel_btn = discord.ui.Button(
            label="Cancel This Recurring Poll", style=discord.ButtonStyle.danger, disabled=True, row=2
        )
        self.cancel_btn.callback = self._on_cancel
        self.add_item(self.cancel_btn)

    async def _on_select(self, interaction: discord.Interaction):
        config_id = int(self.poll_select.values[0])
        self.selected = next((c for c in self.configs if c.id == config_id), None)
        self.cancel_btn.disabled = False
        self.edit_btn.disabled = False
        for opt in self.poll_select.options:
            opt.default = opt.value == str(config_id)
        day_name = WEEKDAY_NAMES[self.selected.post_weekday]
        await interaction.response.edit_message(
            content=f"Selected: **{self.selected.event_name}** — every {day_name} at {self.selected.post_hour:02d}:{self.selected.post_minute:02d}",
            view=self,
        )

    async def _on_edit(self, interaction: discord.Interaction):
        is_creator = self.selected.creator_id == interaction.user.id
        is_admin = interaction.user.guild_permissions.manage_guild
        if not (is_creator or is_admin):
            await interaction.response.send_message(
                "Only the poll creator or a server admin can edit this.", ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content=f"Editing **{self.selected.event_name}** — set expected respondents and options, then Save:",
            view=RecurringEditView(self.selected),
        )

    async def _on_cancel(self, interaction: discord.Interaction):
        is_creator = self.selected.creator_id == interaction.user.id
        is_admin = interaction.user.guild_permissions.manage_guild
        if not (is_creator or is_admin):
            await interaction.response.send_message(
                "Only the poll creator or a server admin can cancel this.", ephemeral=True
            )
            return
        delete_recurring(self.selected.id)
        active_recurring_configs.pop(self.selected.id, None)
        log.info("recurring poll cancelled id=%d name=%s", self.selected.id, self.selected.event_name)
        await interaction.response.edit_message(
            content=f"✅ Recurring poll **{self.selected.event_name}** cancelled.", view=None
        )


class RecurringScheduleEditModal(discord.ui.Modal, title="Edit Name & Schedule"):
    def __init__(self, config: RecurringPollConfig):
        super().__init__()
        self.config = config
        self.name_input = discord.ui.TextInput(
            label="Poll Name", max_length=100, default=config.event_name
        )
        self.desc_input = discord.ui.TextInput(
            label="Description (optional)",
            required=False,
            max_length=300,
            style=discord.TextStyle.paragraph,
            default=config.description or "",
        )
        self.day_input = discord.ui.TextInput(
            label="Post on which day?",
            placeholder="e.g. Thursday, Thurs, Thu",
            max_length=20,
            default=WEEKDAY_NAMES[config.post_weekday],
        )
        self.time_input = discord.ui.TextInput(
            label="Post at what time? (UTC)",
            placeholder="e.g. 18:00, 1800, or 6:00 PM",
            max_length=15,
            default=f"{config.post_hour:02d}:{config.post_minute:02d}",
        )
        self.add_item(self.name_input)
        self.add_item(self.desc_input)
        self.add_item(self.day_input)
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction):
        weekday = parse_weekday(str(self.day_input))
        if weekday is None:
            await interaction.response.send_message(
                "Couldn't parse day. Use e.g. `Monday`, `Mon`, `Thurs`. No changes saved.", ephemeral=True
            )
            return
        t = parse_time(str(self.time_input))
        if t is None:
            await interaction.response.send_message(
                "Couldn't parse time. Use e.g. `18:00`, `1800`, or `6:00 PM`. No changes saved.", ephemeral=True
            )
            return
        self.config.event_name = str(self.name_input)
        self.config.description = str(self.desc_input or "")
        self.config.post_weekday = weekday
        self.config.post_hour = t.hour
        self.config.post_minute = t.minute
        update_recurring(self.config)
        log.info("recurring poll schedule edited id=%s", self.config.id)
        day_name = WEEKDAY_NAMES[weekday]
        await interaction.response.send_message(
            f"✅ **{self.config.event_name}** now posts every **{day_name}** at "
            f"**{t.hour:02d}:{t.minute:02d} UTC**. (Takes effect from the next weekly cycle.)",
            ephemeral=True,
        )


class RecurringEditView(discord.ui.View):
    def __init__(self, config: RecurringPollConfig):
        super().__init__(timeout=300)
        self.config = config
        self.expected_ids: list[int] = list(config.expected_respondent_ids)
        self.expected_role_id: int | None = config.expected_role_id
        self.mention_role_id: int | None = config.mention_role_id
        self.allow_cannot_attend = config.allow_cannot_attend

        user_defaults = [
            discord.SelectDefaultValue(id=uid, type=discord.SelectDefaultValueType.user)
            for uid in self.expected_ids[:25]
        ]
        self.user_select = discord.ui.UserSelect(
            placeholder="Remind specific people? (optional)",
            min_values=0,
            max_values=25,
            default_values=user_defaults,
            row=0,
        )
        self.user_select.callback = self._on_users
        self.add_item(self.user_select)

        self.expected_role_select = discord.ui.RoleSelect(
            placeholder="Remind everyone in a role? (optional)",
            min_values=0,
            max_values=1,
            default_values=self._role_default(self.expected_role_id),
            row=1,
        )
        self.expected_role_select.callback = self._on_expected_role
        self.add_item(self.expected_role_select)

        self.mention_role_select = discord.ui.RoleSelect(
            placeholder="Mention a role when posting? (optional)",
            min_values=0,
            max_values=1,
            default_values=self._role_default(self.mention_role_id),
            row=2,
        )
        self.mention_role_select.callback = self._on_mention_role
        self.add_item(self.mention_role_select)

        self.cannot_toggle = discord.ui.Button(
            label=f"🚫 Can't-make-any: {'ON' if self.allow_cannot_attend else 'OFF'}",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.cannot_toggle.callback = self._on_toggle_cannot
        self.add_item(self.cannot_toggle)

        self.schedule_btn = discord.ui.Button(
            label="Edit Name & Schedule", style=discord.ButtonStyle.secondary, row=3
        )
        self.schedule_btn.callback = self._on_schedule
        self.add_item(self.schedule_btn)

        self.save_btn = discord.ui.Button(label="Save Changes", style=discord.ButtonStyle.success, row=4)
        self.save_btn.callback = self._on_save
        self.add_item(self.save_btn)

    @staticmethod
    def _role_default(role_id):
        if role_id is None:
            return []
        return [discord.SelectDefaultValue(id=role_id, type=discord.SelectDefaultValueType.role)]

    async def _on_users(self, interaction: discord.Interaction):
        self.expected_ids = [u.id for u in self.user_select.values]
        await interaction.response.defer()

    async def _on_expected_role(self, interaction: discord.Interaction):
        self.expected_role_id = self.expected_role_select.values[0].id if self.expected_role_select.values else None
        await interaction.response.defer()

    async def _on_mention_role(self, interaction: discord.Interaction):
        self.mention_role_id = self.mention_role_select.values[0].id if self.mention_role_select.values else None
        await interaction.response.defer()

    async def _on_toggle_cannot(self, interaction: discord.Interaction):
        self.allow_cannot_attend = not self.allow_cannot_attend
        self.cannot_toggle.label = f"🚫 Can't-make-any: {'ON' if self.allow_cannot_attend else 'OFF'}"
        await interaction.response.edit_message(view=self)

    async def _on_schedule(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RecurringScheduleEditModal(self.config))

    async def _on_save(self, interaction: discord.Interaction):
        self.config.expected_respondent_ids = self.expected_ids
        self.config.expected_role_id = self.expected_role_id
        self.config.mention_role_id = self.mention_role_id
        self.config.allow_cannot_attend = self.allow_cannot_attend
        update_recurring(self.config)
        log.info("recurring poll edited id=%s expected_users=%d role=%s", self.config.id, len(self.expected_ids), self.expected_role_id)

        # Apply the new expected set + can't-attend option to the currently-open poll,
        # if any, so its "waiting on" line and buttons stay accurate between resets.
        guild = bot.get_guild(self.config.guild_id)
        if self.config.last_poll_msg_id in active_polls:
            poll = active_polls[self.config.last_poll_msg_id]
            poll.expected_respondent_ids = resolve_expected_ids(guild, self.expected_role_id, self.expected_ids)
            poll.allow_cannot_attend = self.allow_cannot_attend
            save_poll(self.config.last_poll_msg_id, poll)
            channel = guild.get_channel(self.config.channel_id) if guild else None
            if channel is not None:
                # Rebuild the view so the can't-make-any button appears/disappears if toggled.
                fresh = PollView(poll)
                fresh.msg_id = self.config.last_poll_msg_id
                try:
                    msg = await channel.fetch_message(self.config.last_poll_msg_id)
                    await msg.edit(embed=build_poll_embed(poll), view=fresh)
                    bot.add_view(fresh, message_id=self.config.last_poll_msg_id)
                except discord.HTTPException:
                    pass

        who = []
        if self.expected_ids:
            who.append(f"{len(self.expected_ids)} listed member(s)")
        if self.expected_role_id:
            who.append(f"everyone in <@&{self.expected_role_id}>")
        who_str = " and ".join(who) if who else "nobody (reminders off)"
        await interaction.response.edit_message(
            content=(
                f"✅ Updated **{self.config.event_name}** — reminders: {who_str}; "
                f"can't-make-any option {'ON' if self.allow_cannot_attend else 'OFF'}."
            ),
            view=None,
        )


class EventModal(discord.ui.Modal, title="Create Availability Poll"):
    event_name = discord.ui.TextInput(label="Event Name", max_length=100, placeholder="e.g. Game Night")
    description = discord.ui.TextInput(
        label="Description (optional)",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph,
        placeholder="What's this about?",
    )

    async def on_submit(self, interaction: discord.Interaction):
        log.info("poll created: %s", self.event_name)
        days = upcoming_days(25)
        options = [discord.SelectOption(label=date_label(ts), value=str(ts)) for ts in days]
        view = DateSelectView(str(self.event_name), str(self.description or ""), options)
        await interaction.response.send_message(
            "Pick dates to include in the poll (up to 20):", view=view, ephemeral=True
        )


async def _create_event_and_confirm(
    interaction: discord.Interaction,
    poll: PollData,
    msg_id: int,
    event_ts: int,
    voice_channel=None,
):
    event_dt = datetime.fromtimestamp(event_ts, tz=timezone.utc)
    end_dt = event_dt + timedelta(hours=2)
    try:
        if voice_channel:
            event = await interaction.guild.create_scheduled_event(
                name=poll.event_name,
                description=poll.description or "",
                start_time=event_dt,
                end_time=end_dt,
                entity_type=discord.EntityType.voice,
                privacy_level=discord.PrivacyLevel.guild_only,
                channel=voice_channel,
            )
        else:
            event = await interaction.guild.create_scheduled_event(
                name=poll.event_name,
                description=poll.description or "",
                start_time=event_dt,
                end_time=end_dt,
                entity_type=discord.EntityType.external,
                privacy_level=discord.PrivacyLevel.guild_only,
                location="TBD",
            )
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Failed to create event: {e}", ephemeral=True)
        return

    channel = interaction.guild.get_channel(poll.channel_id)
    if channel:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=build_poll_embed(poll, event_ts), view=None)
        except discord.HTTPException:
            pass

    active_polls.pop(msg_id, None)
    delete_poll(msg_id)
    log.info("event created: %s", poll.event_name)
    await interaction.response.edit_message(content="✅ Event created!", view=None)
    await interaction.followup.send(f"✅ **{poll.event_name}** scheduled for <t:{event_ts}:F>!\n{event.url}")


class LocationView(discord.ui.View):
    def __init__(self, poll: PollData, msg_id: int, event_ts: int):
        super().__init__(timeout=600)
        self.poll = poll
        self.msg_id = msg_id
        self.event_ts = event_ts
        self.voice_channel = None

        ch_select = discord.ui.ChannelSelect(
            placeholder="Voice channel (optional)...",
            channel_types=[discord.ChannelType.voice],
            min_values=0,
            max_values=1,
            row=0,
        )
        ch_select.callback = self._on_channel
        self.add_item(ch_select)

        create_btn = discord.ui.Button(label="Create Event", style=discord.ButtonStyle.success, row=1)
        create_btn.callback = self._on_create
        self.add_item(create_btn)

    async def _on_channel(self, interaction: discord.Interaction):
        self.voice_channel = self.children[0].values[0] if self.children[0].values else None
        await interaction.response.defer()

    async def _on_create(self, interaction: discord.Interaction):
        await _create_event_and_confirm(interaction, self.poll, self.msg_id, self.event_ts, self.voice_channel)


class DateSelectView(discord.ui.View):
    def __init__(
        self,
        name: str,
        desc: str,
        options: list[discord.SelectOption],
        selected: list[int] | None = None,
        allow_cannot_attend: bool = True,
    ):
        super().__init__(timeout=300)
        self.name = name
        self.desc = desc
        self.options = options
        self.selected: list[int] = selected or []
        self.allow_cannot_attend = allow_cannot_attend

        self.select = discord.ui.Select(
            placeholder="Select dates...",
            min_values=1,
            max_values=min(len(options), 20),
            options=[discord.SelectOption(label=o.label, value=o.value) for o in options],
            row=0,
        )
        self.select.callback = self._on_select
        self.add_item(self.select)

        self.cannot_toggle = discord.ui.Button(
            label=f"🚫 \"Can't make any\" option: {'ON' if allow_cannot_attend else 'OFF'}",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        self.cannot_toggle.callback = self._on_toggle_cannot
        self.add_item(self.cannot_toggle)

        self.confirm_btn = discord.ui.Button(
            label="Confirm",
            style=discord.ButtonStyle.success,
            disabled=not self.selected,
            row=2,
        )
        self.confirm_btn.callback = self._on_confirm
        self.add_item(self.confirm_btn)

    def _rebuilt(self) -> "DateSelectView":
        return DateSelectView(self.name, self.desc, self.options, self.selected, self.allow_cannot_attend)

    async def _on_select(self, interaction: discord.Interaction):
        self.selected = sorted(int(v) for v in self.select.values)
        lines = "\n".join(fmt_date(ts) for ts in self.selected)
        fresh = self._rebuilt()
        await interaction.response.edit_message(
            content=f"Pick dates to include in the poll (up to 20):\n**Selected:**\n{lines}",
            view=fresh,
        )

    async def _on_toggle_cannot(self, interaction: discord.Interaction):
        self.allow_cannot_attend = not self.allow_cannot_attend
        fresh = self._rebuilt()
        lines = "\n".join(fmt_date(ts) for ts in self.selected) if self.selected else "*none yet*"
        await interaction.response.edit_message(
            content=f"Pick dates to include in the poll (up to 20):\n**Selected:**\n{lines}",
            view=fresh,
        )

    async def _on_confirm(self, interaction: discord.Interaction):
        poll = PollData(
            event_name=self.name,
            description=self.desc,
            creator_id=interaction.user.id,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            dates=self.selected,
            votes={i: set() for i in range(len(self.selected))},
            allow_cannot_attend=self.allow_cannot_attend,
        )
        view = PollView(poll)
        embed = build_poll_embed(poll)
        msg = await interaction.channel.send(embed=embed, view=view)
        log.info("poll posted: %s", poll.event_name)
        active_polls[msg.id] = poll
        view.msg_id = msg.id
        save_poll(msg.id, poll)
        bot.add_view(view, message_id=msg.id)
        await interaction.response.edit_message(content="✅ Poll posted!", view=None)


class TimeInputModal(discord.ui.Modal, title="Set Event Time"):
    event_time = discord.ui.TextInput(
        label="Start time",
        placeholder="e.g. 19:00 or 7:00 PM",
        max_length=10,
    )

    def __init__(self, poll: PollData, msg_id: int, date_idx: int):
        super().__init__()
        self.poll = poll
        self.msg_id = msg_id
        self.date_idx = date_idx

    async def on_submit(self, interaction: discord.Interaction):
        t = parse_time(str(self.event_time))
        if t is None:
            await interaction.response.send_message(
                "Couldn't parse time. Use `19:00` or `7:00 PM`.", ephemeral=True
            )
            return
        view = TimezoneSelectView(self.poll, self.msg_id, self.date_idx, t)
        await interaction.response.send_message(
            f"Time set to **{self.event_time}**. Now pick your timezone:",
            view=view,
            ephemeral=True,
        )


class TimezoneSelectView(discord.ui.View):
    def __init__(self, poll: PollData, msg_id: int, date_idx: int, t: dtime):
        super().__init__(timeout=600)
        self.poll = poll
        self.msg_id = msg_id
        self.date_idx = date_idx
        self.t = t
        options = [discord.SelectOption(label=label, value=iana) for iana, label in TIMEZONES]
        sel = discord.ui.Select(placeholder="Select timezone...", options=options)
        sel.callback = self._on_select
        self.add_item(sel)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def _on_select(self, interaction: discord.Interaction):
        tz = ZoneInfo(self.children[0].values[0])
        base_dt = datetime.fromtimestamp(self.poll.dates[self.date_idx], tz=timezone.utc)
        event_dt = datetime(base_dt.year, base_dt.month, base_dt.day, self.t.hour, self.t.minute, tzinfo=tz)
        event_ts = int(event_dt.timestamp())
        view = LocationView(self.poll, self.msg_id, event_ts)
        await interaction.response.edit_message(
            content=f"<t:{event_ts}:F> — pick a voice channel or skip straight to Create:",
            view=view,
        )


class PollView(discord.ui.View):
    def __init__(self, poll: PollData):
        super().__init__(timeout=None)
        self.poll = poll
        self.msg_id: int = 0

        for i, ts in enumerate(poll.dates):
            btn = discord.ui.Button(
                label=date_label(ts),
                custom_id=f"vote_{i}",
                style=discord.ButtonStyle.secondary,
                row=min(i // 5, 3),
            )
            btn.callback = self._vote_cb(i)
            self.add_item(btn)

        if poll.allow_cannot_attend:
            cannot_btn = discord.ui.Button(
                label="Can't make any",
                emoji="🚫",
                style=discord.ButtonStyle.secondary,
                custom_id="cannot_attend",
                row=4,
            )
            cannot_btn.callback = self._cannot_attend_cb
            self.add_item(cannot_btn)

        see_votes_btn = discord.ui.Button(
            label="See Votes", style=discord.ButtonStyle.primary, custom_id="see_votes", row=4
        )
        see_votes_btn.callback = self._see_votes_cb
        self.add_item(see_votes_btn)

        finalize_btn = discord.ui.Button(
            label="Finalize Event", style=discord.ButtonStyle.success, custom_id="finalize", row=4
        )
        finalize_btn.callback = self._finalize_cb
        self.add_item(finalize_btn)

        cancel_btn = discord.ui.Button(
            label="Cancel Poll", style=discord.ButtonStyle.danger, custom_id="cancel", row=4
        )
        cancel_btn.callback = self._cancel_cb
        self.add_item(cancel_btn)

    def _vote_cb(self, idx: int):
        async def cb(interaction: discord.Interaction):
            voters = self.poll.votes.setdefault(idx, set())
            if interaction.user.id in voters:
                voters.discard(interaction.user.id)
                log.info("vote_removed user=%s poll=%s date=%s", interaction.user.id, self.msg_id, idx)
            else:
                voters.add(interaction.user.id)
                # Voting for a date clears any "can't make any" mark.
                self.poll.cannot_attend.discard(interaction.user.id)
                log.info("vote_added user=%s poll=%s date=%s", interaction.user.id, self.msg_id, idx)
            save_poll(self.msg_id, self.poll)
            await interaction.response.edit_message(embed=build_poll_embed(self.poll), view=self)
        return cb

    async def _cannot_attend_cb(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid in self.poll.cannot_attend:
            self.poll.cannot_attend.discard(uid)
            log.info("cannot_attend_removed user=%s poll=%s", uid, self.msg_id)
        else:
            self.poll.cannot_attend.add(uid)
            # "Can't make any" is exclusive with date votes.
            for voters in self.poll.votes.values():
                voters.discard(uid)
            log.info("cannot_attend_added user=%s poll=%s", uid, self.msg_id)
        save_poll(self.msg_id, self.poll)
        await interaction.response.edit_message(embed=build_poll_embed(self.poll), view=self)

    async def _see_votes_cb(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"📅 {self.poll.event_name} — Votes", color=discord.Color.blurple())
        for i, ts in enumerate(self.poll.dates):
            voters = self.poll.votes.get(i, set())
            count = len(voters)
            mentions = " ".join(f"<@{uid}>" for uid in voters) if voters else "*no votes*"
            embed.add_field(
                name=f"{fmt_date(ts)} — {count} {'person' if count == 1 else 'people'}",
                value=mentions,
                inline=False,
            )
        if self.poll.cannot_attend:
            embed.add_field(
                name=f"🚫 Can't make any — {len(self.poll.cannot_attend)}",
                value=" ".join(f"<@{uid}>" for uid in self.poll.cannot_attend),
                inline=False,
            )
        if self.poll.expected_respondent_ids:
            responded = self.poll.responded_users()
            pending = [uid for uid in self.poll.expected_respondent_ids if uid not in responded]
            embed.add_field(
                name="⏳ Expected but not yet responded",
                value=" ".join(f"<@{uid}>" for uid in pending) if pending else "*everyone has responded*",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _cancel_cb(self, interaction: discord.Interaction):
        if interaction.user.id != self.poll.creator_id:
            await interaction.response.send_message("Only the poll creator can cancel.", ephemeral=True)
            return
        active_polls.pop(self.msg_id, None)
        delete_poll(self.msg_id)
        log.info("poll cancelled: %s", self.poll.event_name)
        await interaction.response.defer()
        await interaction.message.delete()

    async def _finalize_cb(self, interaction: discord.Interaction):
        view = FinalizeSelectView(self.poll, self.msg_id)
        lines = [
            f"**{i+1}.** {fmt_date(ts)} — {len(self.poll.votes.get(i, set()))} votes"
            for i, ts in enumerate(self.poll.dates)
        ]
        await interaction.response.send_message(
            "**Pick the winning date:**\n" + "\n".join(lines), view=view, ephemeral=True
        )


class FinalizeSelectView(discord.ui.View):
    def __init__(self, poll: PollData, msg_id: int):
        super().__init__(timeout=600)
        self.poll = poll
        self.msg_id = msg_id
        options = [
            discord.SelectOption(
                label=date_label(ts),
                description=f"{len(poll.votes.get(i, set()))} votes",
                value=str(i),
            )
            for i, ts in enumerate(poll.dates)
        ]
        sel = discord.ui.Select(placeholder="Choose date...", options=options)
        sel.callback = self._on_select
        self.add_item(sel)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def _on_select(self, interaction: discord.Interaction):
        idx = int(self.children[0].values[0])
        await interaction.response.send_modal(TimeInputModal(self.poll, self.msg_id, idx))
