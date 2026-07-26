import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks
from dotenv import load_dotenv

from bot_instance import bot
from helpers import build_closed_poll_embed, build_poll_embed, next_week_dates
from models import PollData, active_polls, active_recurring_configs
from persistence import (
    delete_poll,
    init_db,
    load_polls,
    load_recurring_polls,
    save_poll,
    update_recurring_after_post,
)
from ui import PollTypeView, PollView

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found")


@bot.tree.command(name="std", description="Create an availability poll for an event")
async def std_command(interaction: discord.Interaction):
    await interaction.response.send_message("What type of poll?", view=PollTypeView(), ephemeral=True)


async def _post_recurring_poll(config, iso_week: str):
    guild = bot.get_guild(config.guild_id)
    if guild is None:
        return
    channel = guild.get_channel(config.channel_id)
    if channel is None:
        return

    # Close previous poll for this recurring config
    if config.last_poll_msg_id is not None:
        old_poll = active_polls.pop(config.last_poll_msg_id, None)
        if old_poll is not None:
            delete_poll(config.last_poll_msg_id)
            try:
                old_msg = await channel.fetch_message(config.last_poll_msg_id)
                await old_msg.edit(embed=build_closed_poll_embed(old_poll), view=None)
            except discord.HTTPException:
                pass

    dates = next_week_dates()
    poll = PollData(
        event_name=config.event_name,
        description=config.description,
        creator_id=config.creator_id,
        guild_id=config.guild_id,
        channel_id=config.channel_id,
        dates=dates,
        votes={i: set() for i in range(len(dates))},
    )
    view = PollView(poll)
    embed = build_poll_embed(poll)
    content = f"<@&{config.mention_role_id}>" if config.mention_role_id else None
    msg = await channel.send(content=content, embed=embed, view=view)

    active_polls[msg.id] = poll
    view.msg_id = msg.id
    save_poll(msg.id, poll)
    bot.add_view(view, message_id=msg.id)
    update_recurring_after_post(config.id, iso_week, msg.id)
    config.last_posted_week = iso_week
    config.last_poll_msg_id = msg.id
    log.info("recurring poll posted: %s week=%s msg=%d", config.event_name, iso_week, msg.id)


@tasks.loop(minutes=1)
async def check_recurring_polls():
    now_utc = datetime.now(timezone.utc)
    iso_week = now_utc.strftime("%G-W%V")
    for config_id, config in list(active_recurring_configs.items()):
        try:
            tz = ZoneInfo(config.post_timezone)
            now_local = now_utc.astimezone(tz)
            if (
                now_local.weekday() == config.post_weekday
                and now_local.hour == config.post_hour
                and now_local.minute == config.post_minute
                and config.last_posted_week != iso_week
            ):
                await _post_recurring_poll(config, iso_week)
        except Exception:
            log.exception("error in recurring poll check id=%d", config_id)


@bot.event
async def on_ready():
    init_db()
    for msg_id, poll in load_polls():
        active_polls[msg_id] = poll
        view = PollView(poll)
        view.msg_id = msg_id
        bot.add_view(view, message_id=msg_id)
    log.info("restored %d active poll(s)", len(active_polls))
    for config in load_recurring_polls():
        active_recurring_configs[config.id] = config
    log.info("restored %d recurring poll config(s)", len(active_recurring_configs))
    check_recurring_polls.start()
    await bot.tree.sync()
    log.info("connected: %s", bot.user)


bot.run(TOKEN)
