# parrot-check

Deterministic 复读 / 多问 detector for Chinese interview transcripts. No LLM, no network — char-bigram set precision over agent's first sentence vs the user's prior turn.

## Dims

| key | label | range | direction | description |
|---|---|---|---|---|
| `paraphrase_rate` | 改述率 / Paraphrase Rate | 0–100 | ↑ better | `100 − avg Echo Ratio` over agent turns |
| `single_question_rate` | 一题一问率 / Single-Q Rate | 0–100 | ↑ better | % agent turns asking ≤ 1 question |

## Echo Ratio (ER) — per agent turn

1. Take reply's **first sentence** (cut at first `。/？/！/!/?` within first 30 chars, else first 30 chars)
2. Strip punctuation + whitespace from both reply head + last user turn
3. Build char-level **2-gram sets** for each
4. `ER = |agent_grams ∩ user_grams| / |agent_grams| × 100`

`0%` = totally fresh phrasing. `100%` = every bigram in the reply head is also in the user's turn.

## Aggregation

- `paraphrase_rate     = 100 − mean(ER across agent turns)`
- `single_question_rate = mean(1 if (?+？) ≤ 1 else 0) × 100`

## Worked example

User: `搭配舒服感`
Agent: `明白，色调搭配舒服。那你具体喜欢哪种？`

| step | value |
|---|---|
| reply first sentence (cut at `。`) | `明白，色调搭配舒服` |
| stripped (8 chars) | `明白色调搭配舒服` |
| agent 2-grams (7) | {明白, 白色, 色调, 调搭, 搭配, 配舒, 舒服} |
| user stripped (5) | `搭配舒服感` |
| user 2-grams (4) | {搭配, 配舒, 舒服, 服感} |
| intersection (3) | {搭配, 配舒, 舒服} |
| **ER** | `3 / 7 × 100 = 42.86 %` |
| Q-count | 1 → `single_q` = 1.0 |

## Relation to BLEU

ER ≈ directional **BLEU-2 precision against an anti-reference** (user's prior turn — what we DON'T want the agent to mirror), without a brevity penalty, on agent's first sentence only.

- **2-gram only**: 1-gram (common chars 的/了) inflates noise; 4-gram rarely matches in 30 chars and floors to 0. 2-gram alone hits the human-readable "phrase echo" signal in Chinese.
- **No BP**: good agent reply *should* be shorter than user; BP would punish that.
- **First-sentence cut**: the parrot lives in the acknowledgement prefix; truncating focuses the signal.

## Blind spots

- **Semantic paraphrase**: agent says `画风` when ASR-garbled user said `颁发` meaning 画风 → no 2-gram overlap, ER = 0 % even though human still hears repetition. Pair with sentence-embedding cosine.
- **Long acknowledgements**: if the parrot lives after the first sentence, the 30-char cut misses it. Most real-world parrots are in the first 20 chars.
- **Cross-language**: tuned for CJK char bigrams. For English use word-bigrams.

## Run it

```bash
python -m rubric run parrot-check metrics/parrot_check/examples/x03_q6.json
```

```
metric:  parrot-check v0.1.0
sample:  x03_q6.json

  ↑ 改述率 (Paraphrase Rate):     46.07 / 100   100 − avg Echo Ratio over agent turns. ...
  ↑ 一题一问率 (Single-Q Rate):   50.00 / 100   % agent turns asking ≤ 1 question.
    avg_echo_ratio: 53.93  (diagnostic)
    n_agent_turns: 6       (diagnostic)
    per_turn: [...]        (diagnostic)
```
