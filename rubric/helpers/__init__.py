"""Optional helpers for LLM-judge metrics.

Plugins that just compute deterministic functions on text shouldn't import
anything here. Plugins that need an LLM judge (FED-style, PKBench-style)
can do:

    from rubric.helpers import ask_claude, extract_json, extract_rating, format_context

`ask_claude` uses Anthropic primary with automatic b.ai fallback so a
single API outage doesn't break the eval pipeline. Anthropic SDK is
listed as an optional dep — `pip install 'rubric[llm]'` to get it.

Env vars consumed:
  ANTHROPIC_API_KEY  — primary
  EVAL_MODEL         — Claude model id (default claude-sonnet-4-20250514)
  BAI_API_KEY        — fallback gateway
  BAI_BASE_URL       — default https://api.b.ai/v1
  BAI_MODEL          — default gpt-5.2
"""
from .format import format_context
from .llm import ask_claude
from .parsing import extract_json, extract_rating

__all__ = ["ask_claude", "extract_json", "extract_rating", "format_context"]
