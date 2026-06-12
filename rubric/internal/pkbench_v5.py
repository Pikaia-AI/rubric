"""PKBench v5 shared data + scoring helper.

21 dims + verbatim prompt template, snapshotted from
github.com/Pikaia-AI/pikaia_benchmarking (commit cbd08bb, 2026-05-07).

The 21 single-dim plugins under `rubric.builtin_metrics.pkbench_<key>/`
all import `score_dim(dim_key, turns)` from here so the LLM-call protocol
+ criteria text stay in one place.

Resync workflow when bench updates dimensions:
  cd /tmp && rm -rf pikaia_benchmarking && \\
    gh repo clone Pikaia-AI/pikaia_benchmarking
  cp /tmp/pikaia_benchmarking/prisma/seed-data/dimensions.json \\
     rubric/internal/data/pkbench_dimensions_v5.json
  # bump SOURCE_COMMIT below
  # diff PROMPT_TEMPLATE against /tmp/pikaia_benchmarking/prisma/seed.ts
"""
from __future__ import annotations

import json
import pathlib

from rubric.helpers import ask_claude, extract_json

SOURCE_COMMIT = "cbd08bb"
SNAPSHOT_DATE = "2026-05-07"
DIMENSION_SET_VERSION = "v5"

# Verbatim from pikaia_benchmarking/prisma/seed.ts (default 评测模板 v1)
PROMPT_TEMPLATE = """你是一个专业的用户访谈质量评测专家。请根据以下评分标准，对给定的访谈记录在"{{dimension_name}}"维度上打分。

## 评分标准

- **0分**: {{criteria_0}}
- **1分**: {{criteria_1}}
- **2分**: {{criteria_2}}

## 输出要求

请以 JSON 格式输出，**score 字段必须放在最前面**，包含以下字段：
- score: 你的评分（0、1 或 2，必须是数字）
- thinking: 你的推理过程（string）

示例：{"score": 1, "thinking": "..."}

请基于访谈大纲和转录文本进行评估。"""


# Chinese name → English key for plugin/dim id.
ZH_TO_KEY = {
    # 用户质量 (10)
    "回答长度": "answer_length",
    "回答扩展": "answer_expansion",
    "追问配合": "followup_cooperation",
    "准确理解问题": "question_comprehension",
    "个人观点表达": "personal_opinion",
    "表达逻辑": "logic_clarity",
    "细节程度": "detail_level",
    "观点明确": "viewpoint_clarity",
    "回答相关性": "answer_relevance",
    "有效信息密度": "info_density",
    # 主持人质量 (9)
    "问题表达清晰": "question_clarity",
    "中立无诱导": "neutrality",
    "开放问题": "open_questions",
    "行为导向": "behavior_oriented",
    "一题一问": "one_question_per_turn",
    "细节覆盖": "detail_coverage",
    "时机节奏": "pacing",
    "对话控制": "conversation_control",
    "鼓励表达": "encouragement",
    # 结果质量 (2)
    "研究问题覆盖": "research_coverage",
    "信息一致": "info_consistency",
}

ZH_TO_EN = {
    "回答长度": "Answer Length",
    "回答扩展": "Answer Expansion",
    "追问配合": "Follow-up Cooperation",
    "准确理解问题": "Question Comprehension",
    "个人观点表达": "Personal Opinion",
    "表达逻辑": "Logic Clarity",
    "细节程度": "Detail Level",
    "观点明确": "Viewpoint Clarity",
    "回答相关性": "Answer Relevance",
    "有效信息密度": "Info Density",
    "问题表达清晰": "Question Clarity",
    "中立无诱导": "Neutrality",
    "开放问题": "Open Questions",
    "行为导向": "Behavior-Oriented",
    "一题一问": "One Question per Turn",
    "细节覆盖": "Detail Coverage",
    "时机节奏": "Pacing",
    "对话控制": "Conversation Control",
    "鼓励表达": "Encouragement",
    "研究问题覆盖": "Research Coverage",
    "信息一致": "Info Consistency",
}

# Per-dim short Chinese description (ported from pikaia_eval/dashboard.html
# DESCRIPTIONS dict). Single source of truth lives here.
ZH_TO_DESC = {
    "回答长度": "平均每轮回答长度（字数），反映受访者的表达流畅度。",
    "回答扩展": "受访者是否主动补充信息，反映其积极配合度。",
    "追问配合": "受访者面对追问时的展开程度。",
    "准确理解问题": "受访者是否正确理解了主持人意图。",
    "个人观点表达": "受访者是否敢于表达个人判断和真实观点，区别于客观描述。",
    "表达逻辑": "受访者的推理链是否合理、自洽、易于理解。",
    "细节程度": "受访者回答是否包含具体事实/数字/细节/时间/地点。",
    "观点明确": "受访者观点是否清晰、边界明确，无模糊表述。",
    "回答相关性": "受访者回答是否高度围绕主持人的问题。",
    "有效信息密度": "受访者单次回答中含多少个核心有效信息。",
    "问题表达清晰": "主持人提问的语言简洁、语义明确，受访者无需额外澄清。",
    "中立无诱导": "主持人提问无价值判断/褒贬词汇，不预设答案。",
    "开放问题": "主持人封闭式问题占比，越低越好。",
    "行为导向": "主持人提问是否引导用户基于真实经历回答，而非抽象/假设。",
    "一题一问": "主持人一回合是否只问一个核心问题，无叠加/嵌套/≥3 选项。",
    "细节覆盖": "主持人是否主动深挖事实细节、行为原因、决策权衡。",
    "时机节奏": "主持人追问是否紧跟受访者刚说的内容，无机械延迟。",
    "对话控制": "主持人是否避免打断受访者完整表达。",
    "鼓励表达": "主持人是否给出有效的鼓励回应，推动用户持续/深入输出。",
    "研究问题覆盖": "实际访谈对大纲中预设问题的覆盖比例。",
    "信息一致": "整段访谈中是否无逻辑或事实性矛盾/前后不一致。",
}

_DATA = pathlib.Path(__file__).parent / "data" / "pkbench_dimensions_v5.json"
with _DATA.open(encoding="utf-8") as _f:
    DIMS_RAW = json.load(_f)

# Validate snapshot completeness
_missing_k = [d["name"] for d in DIMS_RAW if d["name"] not in ZH_TO_KEY]
_missing_e = [d["name"] for d in DIMS_RAW if d["name"] not in ZH_TO_EN]
if _missing_k or _missing_e:
    raise ValueError(
        f"pkbench snapshot has new dims requiring ZH_TO_KEY/ZH_TO_EN/ZH_TO_DESC: "
        f"keys={_missing_k}, en={_missing_e}"
    )

# By-key lookup
KEY_TO_DIM = {ZH_TO_KEY[d["name"]]: d for d in DIMS_RAW}


def dim_zh(dim_key: str) -> str:
    return KEY_TO_DIM[dim_key]["name"]


def dim_en(dim_key: str) -> str:
    return ZH_TO_EN[dim_zh(dim_key)]


def dim_category(dim_key: str) -> str:
    return KEY_TO_DIM[dim_key]["group"]


def dim_description(dim_key: str) -> str:
    return ZH_TO_DESC.get(dim_zh(dim_key), "")


def dim_formula(dim_key: str) -> str:
    """Math-notation formula + criteria text injected into the plugin META.

    Math is the contract; criteria text stays Chinese because the LLM
    prompt is Chinese — translating would break score parity with the
    bench source-of-truth.
    """
    d = KEY_TO_DIM[dim_key]
    return (
        f"score(transcript) = parse_json(LLM(system, user)).score ∈ {{0, 1, 2}}\n"
        f"                  ⤳ 0.0 on parse error\n\n"
        f"system = PROMPT_TEMPLATE with placeholders bound:\n"
        f"  {{{{dimension_name}}}}  ← '{d['name']}'\n"
        f"  {{{{criteria_0}}}}     ← criteria[0]\n"
        f"  {{{{criteria_1}}}}     ← criteria[1]\n"
        f"  {{{{criteria_2}}}}     ← criteria[2]\n\n"
        f"user   = '## 转录文本 (Transcript)\\n<role>: <text>\\n...'\n\n"
        f"criteria (snapshot {DIMENSION_SET_VERSION} @ {SOURCE_COMMIT}):\n"
        f"  [0] {d['criteria0']}\n"
        f"  [1] {d['criteria1']}\n"
        f"  [2] {d['criteria2']}\n\n"
        f"LLM:   Claude Sonnet (ask_claude, b.ai fallback)\n"
        f"Range: {{0, 1, 2}} (dashboard normalizes to [0, 5]), higher = better."
    )


def _build_user_content(turns, outline: str = "") -> str:
    transcript = "\n".join(f"{t['role']}: {t['text']}" for t in turns)
    parts = []
    if outline:
        parts.append(f"## 大纲 (Outline)\n{outline}\n")
    parts.append(f"## 转录文本 (Transcript)\n{transcript}")
    return "\n".join(parts)


def score_dim(dim_key: str, turns) -> float:
    """ONE LLM call for ONE dim — matches pikaia_benchmarking's protocol."""
    d = KEY_TO_DIM[dim_key]
    system = (
        PROMPT_TEMPLATE
        .replace("{{dimension_name}}", d["name"])
        .replace("{{criteria_0}}", d["criteria0"])
        .replace("{{criteria_1}}", d["criteria1"])
        .replace("{{criteria_2}}", d["criteria2"])
    )
    response = ask_claude(system, _build_user_content(turns), max_tokens=512)
    parsed = extract_json(response)
    if parsed is None:
        return 0.0
    s = parsed.get("score", 0)
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


# All dim keys, ordered same as snapshot (sortOrder).
DIM_KEYS = [ZH_TO_KEY[d["name"]] for d in DIMS_RAW]
