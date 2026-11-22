"""The options form shared by creating and editing a recurring poll."""

from typing import Self

import discord

from std_bot.bot import StdBot
from std_bot.domain.recurring import RecurringPollDraft
from std_bot.ui.fields import RolePicker, UserPicker
from std_bot.ui.text import cannot_attend_label

MAX_EXPECTED_USERS = 25


def _role_defaults(role_id: int | None) -> list[discord.SelectDefaultValue]:
    if role_id is None:
        return []
    return [discord.SelectDefaultValue(id=role_id, type=discord.SelectDefaultValueType.role)]


def _first_id(select: RolePicker) -> int | None:
    return select.values[0].id if select.values else None


class RecurringOptionsView(discord.ui.View):
    """Pick the role to mention, who to remind, and whether to offer "can't make any"; subclasses commit it.

    Nothing touches the draft until the commit button is pressed.
    """

    def __init__(self, bot: StdBot, draft: RecurringPollDraft, *, commit_label: str) -> None:
        """Create the view, pre-selecting what `draft` already has."""
        super().__init__(timeout=300)
        self.bot = bot
        self.draft = draft
        self.mention_role_id = draft.mention_role_id
        self.expected_ids = list(draft.expected_respondent_ids)
        self.expected_role_id = draft.expected_role_id
        self.allow_cannot_attend = draft.allow_cannot_attend

        self.mention_role.default_values = _role_defaults(self.mention_role_id)
        self.expected_users.default_values = [
            discord.SelectDefaultValue(id=user_id, type=discord.SelectDefaultValueType.user)
            for user_id in self.expected_ids[:MAX_EXPECTED_USERS]
        ]
        self.expected_role.default_values = _role_defaults(self.expected_role_id)
        self.cannot_toggle.label = cannot_attend_label(enabled=self.allow_cannot_attend)
        self.commit_button.label = commit_label

    async def commit(self, interaction: discord.Interaction) -> None:
        """Save the chosen options; implemented by the subclass."""
        raise NotImplementedError

    def apply_to_draft(self) -> None:
        """Copy the chosen options onto the draft."""
        self.draft.mention_role_id = self.mention_role_id
        self.draft.expected_respondent_ids = self.expected_ids
        self.draft.expected_role_id = self.expected_role_id
        self.draft.allow_cannot_attend = self.allow_cannot_attend

    @discord.ui.select(
        cls=RolePicker,
        placeholder="Mention a role when posting? (optional)",
        min_values=0,
        max_values=1,
        row=0,
    )
    async def mention_role(self, interaction: discord.Interaction, select: RolePicker) -> None:
        """Remember the role to mention when posting."""
        self.mention_role_id = _first_id(select)
        await interaction.response.defer()

    @discord.ui.select(
        cls=UserPicker,
        placeholder="Remind specific people? (optional)",
        min_values=0,
        max_values=MAX_EXPECTED_USERS,
        row=1,
    )
    async def expected_users(self, interaction: discord.Interaction, select: UserPicker) -> None:
        """Remember the people to remind."""
        self.expected_ids = [user.id for user in select.values]
        await interaction.response.defer()

    @discord.ui.select(
        cls=RolePicker,
        placeholder="Remind everyone in a role? (optional)",
        min_values=0,
        max_values=1,
        row=2,
    )
    async def expected_role(self, interaction: discord.Interaction, select: RolePicker) -> None:
        """Remember the role whose members to remind."""
        self.expected_role_id = _first_id(select)
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.secondary, row=3)
    async def cannot_toggle(self, interaction: discord.Interaction, button: discord.ui.Button[Self]) -> None:
        """Switch the "can't make any" option on or off."""
        self.allow_cannot_attend = not self.allow_cannot_attend
        button.label = cannot_attend_label(enabled=self.allow_cannot_attend)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(style=discord.ButtonStyle.success, row=4)
    async def commit_button(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Apply the options and save."""
        self.apply_to_draft()
        await self.commit(interaction)
