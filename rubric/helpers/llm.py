"""Claude primary + b.ai fallback.

Ported verbatim from pikaia_eval/adapters/base.py so existing adapters
produce byte-identical LLM responses after the rubric migration.
"""
from __future__ import annotations

import os
import sys

_ANTHROPIC_CLIENT = None
_BAI_CLIENT = None


def _anthropic_client():
    """Lazy — anthropic SDK is an optional dep (`rubric[llm]` extra)."""
    global _ANTHROPIC_CLIENT
    if _ANTHROPIC_CLIENT is None:
        import anthropic  # type: ignore[import-not-found]
        _ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _ANTHROPIC_CLIENT


def _bai_client():
    global _BAI_CLIENT
    if _BAI_CLIENT is None:
        import openai  # type: ignore[import-not-found]
        _BAI_CLIENT = openai.OpenAI(
            base_url=os.environ.get("BAI_BASE_URL", "https://api.b.ai/v1"),
            api_key=os.environ.get("BAI_API_KEY", ""),
        )
    return _BAI_CLIENT


def _ask_anthropic(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    response = _anthropic_client().messages.create(
        model=os.environ.get("EVAL_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )
    return response.content[0].text


def _ask_bai(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    response = _bai_client().chat.completions.create(
        model=os.environ.get("BAI_MODEL", "gpt-5.2"),
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def ask_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Primary: Claude. Fallback: b.ai. Name kept for adapter compat."""
    try:
        return _ask_anthropic(system_prompt, user_prompt, max_tokens)
    except Exception as e:
        if not os.environ.get("BAI_API_KEY"):
            raise
        print(
            f"[ask_claude] claude failed ({type(e).__name__}: {e}); falling back to b.ai",
            file=sys.stderr,
        )
        return _ask_bai(system_prompt, user_prompt, max_tokens)
