"""The embeds shown for polls."""

from std_bot.embeds import (
    build_closed_poll_embed,
    build_finalized_poll_embed,
    build_poll_embed,
    build_votes_embed,
)
from tests.factories import make_poll


def _description(**changes: object) -> str:
    return build_poll_embed(make_poll(**changes)).description or ""


def test_poll_embed_counts_votes_and_pluralises() -> None:
    """One voter is "person", two are "people"."""
    text = _description(votes={0: {10}, 1: {10, 11}})
    assert "**1** person\n<@10>" in text
    assert "**2** people" in text


def test_poll_embed_without_votes() -> None:
    """A date nobody picked says so."""
    assert "*no votes yet*" in _description()


def test_poll_embed_truncates_long_voter_lists() -> None:
    """Only the first few voters are named; the rest are counted."""
    assert "*+3 more…*" in _description(votes={0: set(range(100, 109))})


def test_poll_embed_waiting_on_and_everyone_responded() -> None:
    """The poll lists who is still expected, then says when nobody is."""
    poll = make_poll(votes={0: {10}}, cannot_attend={11}, expected_respondent_ids=[10, 11, 12])
    assert "**Waiting on:** <@12>" in (build_poll_embed(poll).description or "")
    poll.cannot_attend.add(12)
    assert "Everyone expected has responded" in (build_poll_embed(poll).description or "")


def test_poll_embed_cannot_attend_section_and_footer() -> None:
    """The "can't make any" line and footer hint appear only when that option is offered."""
    embed = build_poll_embed(make_poll(cannot_attend={7}))
    assert "Can't make any" in (embed.description or "")
    assert "🚫" in (embed.footer.text or "")
    assert "🚫" not in (build_poll_embed(make_poll(allow_cannot_attend=False)).footer.text or "")


def test_poll_embed_shows_the_description() -> None:
    """The description is italicised above the dates."""
    assert _description(description="bring snacks").startswith("*bring snacks*")


def test_finalized_and_closed_embeds() -> None:
    """The finalised embed carries the event time; the closed one says the poll closed."""
    done = build_finalized_poll_embed(make_poll(description="bring snacks"), 1234)
    assert "<t:1234:F>" in (done.description or "")
    assert "bring snacks" in (done.description or "")
    assert "Poll Closed" in (build_closed_poll_embed(make_poll()).title or "")


def test_votes_embed_lists_every_group() -> None:
    """Each date, the "can't make any" group and the pending respondents get a field."""
    poll = make_poll(votes={0: {10}}, cannot_attend={11}, expected_respondent_ids=[10, 11, 12])
    fields = {field.name: field.value for field in build_votes_embed(poll).fields}
    assert any((name or "").endswith("— 1 person") and value == "<@10>" for name, value in fields.items())
    assert any((name or "").endswith("— 0 people") and value == "*no votes*" for name, value in fields.items())
    assert fields["🚫 Can't make any — 1"] == "<@11>"
    assert fields["⏳ Expected but not yet responded"] == "<@12>"
