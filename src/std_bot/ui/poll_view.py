"""The persistent buttons under every poll message."""

import logging
from typing import Self

import discord

from std_bot.bot import StdBot
from std_bot.domain.poll import PollData
from std_bot.embeds import build_poll_embed, build_votes_embed
from std_bot.polls.lifecycle import untrack_poll
from std_bot.storage.polls import save_poll
from std_bot.timestamps import date_label, format_date
from std_bot.ui.finalize.context import FinalizeContext
from std_bot.ui.finalize.select import FinalizeSelectView

log = logging.getLogger(__name__)

DATES_PER_ROW = 5
LAST_DATE_ROW = 3
ACTION_ROW = 4


class MissingMessageError(RuntimeError):
    """A poll button was used on an interaction that has no message."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("poll interaction has no message")


def message_id(interaction: discord.Interaction) -> int:
    """Return the id of the message a component interaction came from."""
    if interaction.message is None:
        raise MissingMessageError
    return interaction.message.id


class VoteButton(discord.ui.Button["PollView"]):
    """The button for one candidate date."""

    def __init__(self, owner: "PollView", index: int, timestamp: int) -> None:
        """Create the button for date number `index`."""
        super().__init__(
            label=date_label(timestamp),
            custom_id=f"vote_{index}",
            style=discord.ButtonStyle.secondary,
            row=min(index // DATES_PER_ROW, LAST_DATE_ROW),
        )
        self.owner = owner
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        """Toggle the user's vote for this date."""
        await self.owner.vote(interaction, self.index)


class PollView(discord.ui.View):
    """Voting, "See Votes", Finalize and Cancel buttons for one poll.

    Persistent: it has no timeout and fixed custom ids, so it keeps working after a restart.
    """

    def __init__(self, bot: StdBot, poll: PollData) -> None:
        """Create the view with one button per date of `poll`."""
        super().__init__(timeout=None)
        self.bot = bot
        self.poll = poll
        for index, timestamp in enumerate(poll.dates):
            self.add_item(VoteButton(self, index, timestamp))
        if not poll.allow_cannot_attend:
            self.remove_item(self.cannot_attend)

    async def _update_message(self, interaction: discord.Interaction) -> None:
        save_poll(message_id(interaction), self.poll)
        await interaction.response.edit_message(embed=build_poll_embed(self.poll), view=self)

    async def vote(self, interaction: discord.Interaction, index: int) -> None:
        """Toggle a vote and refresh the poll message."""
        added = self.poll.toggle_vote(index, interaction.user.id)
        log.info(
            "vote_%s user=%s poll=%s date=%s",
            "added" if added else "removed",
            interaction.user.id,
            message_id(interaction),
            index,
        )
        await self._update_message(interaction)

    @discord.ui.button(
        label="Can't make any",
        emoji="🚫",
        style=discord.ButtonStyle.secondary,
        custom_id="cannot_attend",
        row=ACTION_ROW,
    )
    async def cannot_attend(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Toggle the user's "can't make any" mark and refresh the poll message."""
        added = self.poll.toggle_cannot_attend(interaction.user.id)
        log.info(
            "cannot_attend_%s user=%s poll=%s",
            "added" if added else "removed",
            interaction.user.id,
            message_id(interaction),
        )
        await self._update_message(interaction)

    @discord.ui.button(label="See Votes", style=discord.ButtonStyle.primary, custom_id="see_votes", row=ACTION_ROW)
    async def see_votes(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Show who voted for what, privately."""
        await interaction.response.send_message(embed=build_votes_embed(self.poll), ephemeral=True)

    @discord.ui.button(label="Finalize Event", style=discord.ButtonStyle.success, custom_id="finalize", row=ACTION_ROW)
    async def finalize(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Start picking the winning date."""
        lines = [
            f"**{index + 1}.** {format_date(timestamp)} — {len(self.poll.voters(index))} votes"
            for index, timestamp in enumerate(self.poll.dates)
        ]
        view = FinalizeSelectView(FinalizeContext(self.bot, self.poll, message_id(interaction)))
        await interaction.response.send_message(
            "**Pick the winning date:**\n" + "\n".join(lines), view=view, ephemeral=True
        )

    @discord.ui.button(label="Cancel Poll", style=discord.ButtonStyle.danger, custom_id="cancel", row=ACTION_ROW)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button[Self]) -> None:
        """Delete the poll; only its creator may."""
        if interaction.user.id != self.poll.creator_id:
            await interaction.response.send_message("Only the poll creator can cancel.", ephemeral=True)
            return
        untrack_poll(self.bot.state, message_id(interaction))
        log.info("poll cancelled: %s", self.poll.event_name)
        await interaction.response.defer()
        if interaction.message is not None:
            await interaction.message.delete()
