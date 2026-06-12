"""Common parsing helpers for LLM judge responses."""
from __future__ import annotations

import json
import re


def extract_rating(text: str, pattern: str = r"\[\[(\d+(?:\.\d+)?)\]\]") -> float | None:
    """Extract a numeric rating from an LLM response.

    Supports `[[N]]` format first, then a "Rating: N" / "Score: N" fallback.
    Returns None if neither pattern is found.
    """
    match = re.search(pattern, text)
    if match:
        return float(match.group(1))
    match = re.search(r"(?:Rating|Score|rating|score)[:\s]+(\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None


def extract_json(text: str) -> dict | None:
    """Extract the first single-level JSON object from an LLM response."""
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
