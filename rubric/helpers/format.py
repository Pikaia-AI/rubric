"""Transcript / context formatting helpers."""
from __future__ import annotations


def format_context(context_turns: list[str], max_turns: int = 5) -> str:
    """Format a list of pre-formatted turn strings into a readable block.

    Args:
        context_turns: each item already pre-formatted (e.g. "user: hi").
        max_turns: keep only the most recent N.
    """
    if not context_turns:
        return "(start of conversation)"
    return "\n".join(context_turns[-max_turns:])
