"""parrot-paraphrase_rate — single-dim plugin.

Per-agent-turn Echo Ratio (char-bigram precision of reply's first sentence
vs the user's prior turn), aggregated as 100 − avg(ER). Higher = less
literal echo of user's words.

See rubric.internal.parrot for the shared echo_ratio + role normalization.
"""
from rubric.internal.parrot import echo_ratio, iter_agent_turns

DIM_KEY = "paraphrase_rate"

META = {
    "id": f"parrot-{DIM_KEY}",
    "name": "改述率",
    "version": "0.1.0",
    "description": (
        "100 − avg Echo Ratio over agent turns. ER = char-bigram set "
        "precision of agent's first sentence vs the user's prior turn. "
        "Higher = less literal echo. Char-level Chinese, no LLM."
    ),
    "level": "transcript",
    "group": "Parrot Check",
    "homepage": "https://github.com/Pikaia-AI/rubric/tree/main/rubric/builtin_metrics/parrot_paraphrase_rate",
    "deterministic": True,
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": "改述率", "en": "Paraphrase Rate"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "100 − avg Echo Ratio over agent turns. Higher = less literal echo of user's words.",
            "formula": """
逐 agent turn (须有前置 user turn 且 reply 非空):

  head        = reply 截首句 (截到首个 。 ？ ！ ! ? 在前 30 字内, 否则取前 30 字)
  head_clean  = head 去掉标点和空白
  user_clean  = 前置 user turn 去掉标点和空白

  agent_grams = { head_clean[i:i+2] for i in 0..len-1 }    ← 字符 2-gram 集合
  user_grams  = { user_clean[i:i+2] for i in 0..len-1 }

  ER          = |agent_grams ∩ user_grams| / |agent_grams| × 100      ← 单 turn Echo Ratio

聚合:
  paraphrase_rate = 100 − mean(ER over 所有计分的 agent turn)

边界:
  无前置 user turn 或 head_clean<2 字 → 跳过
  无可计分 agent turn → 返回 0.0

范围 [0, 100], 越高越好""",
            "category": "提问质量",
        }
    ],
}


def score(turns):
    er_values = [echo_ratio(t["text"], lu) for _, t, lu in iter_agent_turns(turns)]
    if not er_values:
        return {DIM_KEY: 0.0}
    avg_er = sum(er_values) / len(er_values)
    return {DIM_KEY: round(100.0 - avg_er, 2)}
