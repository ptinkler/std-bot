import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True  # required to read role membership for expected-respondent reminders
bot = commands.Bot(command_prefix="!", intents=intents)
