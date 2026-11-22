"""Discord form fields and pickers specialised to the owner types this bot uses."""

import discord

TextField = discord.ui.TextInput[discord.ui.Modal]
RolePicker = discord.ui.RoleSelect[discord.ui.View]
UserPicker = discord.ui.UserSelect[discord.ui.View]
