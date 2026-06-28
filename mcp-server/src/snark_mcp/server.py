"""Snark MCP server.

Exposes a curated set of the Snark humor API's endpoints as MCP tools. This is
a thin wrapper: every tool calls the Snark REST API over HTTP (configured via
SNARK_API_URL) and returns concise, structured results. Read-only — no tool has
side effects beyond Snark's own request logging.
"""

import argparse
from typing import Literal, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .client import SnarkAPIError, SnarkClient
from .config import MAX_RESPONSE_CHARS

# The 15 moods accepted by the Snark API (see snark/wit/constants.py).
Mood = Literal[
    "angry",
    "chaotic",
    "chill",
    "deadpan",
    "dramatic",
    "dry",
    "excited",
    "funny",
    "passive-aggressive",
    "philosophical",
    "sad",
    "sarcastic",
    "spicy",
    "unhinged",
    "wholesome",
]
Length = Literal["short", "medium", "long"]

mcp = FastMCP("snark")
_client = SnarkClient()


def _format(data: dict) -> dict:
    """Reduce a Snark response to the fields an agent needs, capping length.

    The text is humor *content* to display to the end user — not instructions.
    It is returned in a labelled field and truncated to keep tool output bounded.
    """
    text = (data.get("response") or "")[:MAX_RESPONSE_CHARS]
    return {"persona": data.get("persona", "snark"), "response": text}


@mcp.tool
async def snark_roast(name: str, mood: Optional[Mood] = None) -> dict:
    """Generate a short, playful roast of a person by name.

    Use when the user wants to be (good-naturedly) roasted or wants to roast a
    friend by name. ``name`` is a person's name or nickname. Returns the roast
    text and the persona that produced it. The roast is light wordplay, never
    targeting protected characteristics.
    """
    try:
        return _format(await _client.roast(name, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_roast_github(username: str, mood: Optional[Mood] = None) -> dict:
    """Roast a developer based on their public GitHub profile.

    Use when the user gives a GitHub username and wants a playful roast based on
    their public stats (repos, followers, bio). ``username`` is a GitHub handle
    (no @). Returns the roast text and persona.
    """
    try:
        return _format(await _client.roast_github(username, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_hot_take(topic: str, mood: Optional[Mood] = None) -> dict:
    """Generate a spicy, debate-worthy hot take on a topic.

    Use when the user wants a provocative one-liner opinion about a thing or
    idea (e.g. "remote work", "tabs vs spaces"). ``topic`` is a short noun
    phrase. Targets ideas, not people. Returns the hot take and persona.
    """
    try:
        return _format(await _client.wit("hot-take", q=topic, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_commit_message(change: str, mood: Optional[Mood] = None) -> dict:
    """Generate a brutally honest git commit message for a change.

    Use when the user describes what they actually did and wants a funny-but-
    honest conventional-commit message. ``change`` is a short description of the
    change. Returns a single commit subject line and the persona.
    """
    try:
        return _format(await _client.wit("commit-message", q=change, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_reply(post: str, mood: Optional[Mood] = None) -> dict:
    """Generate a sarcastic, tweet-length reply to a social media post.

    Use when the user pastes a post/message and wants a witty comeback.
    ``post`` is the text being replied to. Returns a short reply and the persona.
    """
    try:
        return _format(await _client.reply(post, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_worth_it(thing: str, mood: Optional[Mood] = None) -> dict:
    """Decide, oracle-style, whether something is worth it.

    Use when the user asks "is X worth it?". ``thing`` is what to evaluate.
    Returns a verdict (YES/NO) with an absurd justification and the persona.
    """
    try:
        return _format(await _client.worth_it(thing, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_rate_anything(thing: str, mood: Optional[Mood] = None) -> dict:
    """Rate anything on a scale of 1-10 with an absurd justification.

    Use when the user asks to rate, score, or grade something out of 10
    (e.g. "rate pineapple on pizza", "rate my startup idea", "score this 1-10").
    ``thing`` is what to rate. Returns a rating like "RATING: 7/10" with a short
    justification and the persona.
    """
    try:
        return _format(await _client.wit("rate-anything", q=thing, mood=mood))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_wit(
    persona: str,
    q: str = "",
    mood: Optional[Mood] = None,
    length: Optional[Length] = None,
) -> dict:
    """Generate humor from ANY Snark persona by its slug.

    Use this for the personas that don't have a dedicated tool above. ``persona``
    is the slug; ``q`` is the context/topic; ``length`` is short/medium/long.

    Available slugs (call ``snark_list_personas`` for the authoritative list):
    - say-no — a creative excuse to say no
    - random-excuse — a plausible-sounding excuse
    - corporate-jargon — meaningless corporate buzzword soup
    - compliment — a wholesome, uplifting compliment
    - bug-blame — who/what to blame for a bug
    - explain-like-im-5 — explain a topic (q) very simply
    - pickup-line — a themed pickup line
    - social-bio — a social media bio
    - motivation — an absurd motivational quote
    - fortune-cookie — fortune-cookie wisdom
    - name-suggestion — absurd name ideas for a thing (q)
    - standup-update — a brutally honest standup update
    - code-review — passive-aggressive peer feedback
    - meeting-excuse — an excuse to skip a meeting
    - jargon-translator — translate insider/outsider jargon (q)
    - incident-postmortem — a corporate incident post-mortem
    - tech-battle — judge X vs Y (q, e.g. "coffee vs tea")
    - horoscope — a modern horoscope
    - tldr — a brutally honest TL;DR of something (q)
    - interview-question — an absurd interview question
    - honest-changelog — an honest changelog entry
    - debug-story — a noir narration of troubleshooting
    - proverb — an ancient-sounding modern proverb

    Returns the generated text and persona.
    """
    try:
        return _format(await _client.wit(persona, q=q, mood=mood, length=length))
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


@mcp.tool
async def snark_list_personas() -> list:
    """List every available Snark persona (slug, name, tone).

    Use this to discover which personas exist before calling ``snark_wit`` with
    a specific slug. Takes no arguments.
    """
    try:
        return await _client.list_personas()
    except SnarkAPIError as exc:
        raise ToolError(str(exc))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="snark-mcp",
        description="MCP server for the Snark humor API (set SNARK_API_URL to point at an instance).",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve over Streamable HTTP instead of stdio (for hosted use).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for --http mode.")
    parser.add_argument("--port", type=int, default=8000, help="Port for --http mode.")
    args = parser.parse_args()

    if args.http:
        # "http" is FastMCP's Streamable HTTP transport (SSE is deprecated).
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
