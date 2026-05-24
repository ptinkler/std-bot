import logging
import os

import discord
from dotenv import load_dotenv

from bot_instance import bot
from models import active_polls
from persistence import init_db, load_polls
from ui import EventModal, PollView

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not found")


@bot.tree.command(name="std", description="Create an availability poll for an event")
async def std_command(interaction: discord.Interaction):
    await interaction.response.send_modal(EventModal())


@bot.event
async def on_ready():
    init_db()
    for msg_id, poll in load_polls():
        active_polls[msg_id] = poll
        view = PollView(poll)
        view.msg_id = msg_id
        bot.add_view(view, message_id=msg_id)
    log.info("restored %d active poll(s)", len(active_polls))
    await bot.tree.sync()
    log.info("connected: %s", bot.user)


bot.run(TOKEN)
