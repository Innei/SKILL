---
name: chat-export-report
description: >
  Use when user provides exported chat history (WeChat / Telegram / iMessage /
  QQ exports as .md / .txt / .json) and asks "我和 X 聊了啥"、"看完整个 md"、"细说
  XX"、"是不是有 Y"、"what did I and X talk about", wants topical breakdown,
  requests detail on specific themes (relationships / work / health / events),
  or seeks honest interpretation of conversation dynamics. Triggers on large
  chat dumps (>1000 lines) where direct full read is impractical.
metadata:
  author: innei
  version: "0.1.0"
---

# chat-export-report

Analyze massive exported chat logs (thousands to hundreds of thousands of lines) and produce a layered, drill-downable report grounded in original quotes.

## When to invoke

- User provides path to exported chat (WeChat / Telegram / iMessage / QQ; .md / .txt / .json)
- File far exceeds a single `Read` window (>2000 lines)
- User asks "what did we talk about", "read the whole file", "tell me more about X", "was there Y between us"
- User wants an honest read of relationship dynamics, emotional tone, or missed opportunities

**Do not use for**:
- Single messages or short conversations
- Looking up one specific fact (just `grep`)
- Full line-by-line translation or re-export

## Reading strategy

### Step 1 — Measure size

```bash
wc -l <file>
```

### Step 2 — Three-zone sampling

Never read the whole file at once. Establish baseline tone first:

| Zone | offset | limit |
|------|--------|-------|
| Opening | 1 | 200 |
| Middle | total/3 and total*2/3 | 120–150 each |
| Tail | total-200 | 200 |

Four to five samples fix the time span, message density, opening / closing state, and any pause points.

### Step 3 — Topical grep

Sweep for line numbers by topic family, then `Read` surrounding context as needed:

| Topic | Keyword family |
|-------|----------------|
| Work | 实习\|入职\|面试\|mentor\|论文\|三方\|加班\|KPI\|大厂\|interview\|onboard |
| Food | 外卖\|做饭\|盒饭\|吃饭\|饿\|食堂\|takeout\|cook |
| Housing | 租\|合租\|中介\|宿舍\|房租\|老家\|rent\|roommate |
| Romance | 对象\|男朋友\|女朋友\|喜欢\|分手\|相亲\|介绍\|追\|date\|crush |
| Health | 抑郁\|emo\|失眠\|噩梦\|结节\|医院\|体检\|depress\|insomnia |
| Current events | 封\|核酸\|疫情\|户口\|历史\|lockdown\|covid |
| Hobbies | 游戏\|番\|二次元\|新海诚\|动漫\|追剧\|game\|anime |
| Sexuality | 性取向\|gay\|les\|喜欢男\|喜欢女 |

Per family, take 30–50 line numbers; then `Read` 60–150 lines of surrounding context to verify.

## Output layering

Reply in four layers, deepest only on follow-up — **never dump all four at once**, leave room for the user to drill down:

**L1 — Overview** (500–800 words)
Time span, total message count, theme list (4–7 buckets), overall tone.

**L2 — Theme breakdown** (one section per bucket, three to five bullets, sparse direct quotes)
Use the topic families from Step 3 as section headings; 100–200 words each.

**L3 — Single-theme deep dive** (800–1500 words)
Triggered when user says "tell me more about X" / "细说 XX". Include sub-sections, original quotes, dates.

**L4 — Subjective judgment** (relationship / opportunity / missed chance)
Triggered by "was there a chance", "did I miss it", "我是不是错过". Three-part structure is mandatory:

1. **Evidence for "yes"** (positive signals, usually fewer)
2. **Evidence for "no"** (negative signals, usually more)
3. **Lean + reasoning** (no emotion, just the objective read)

## Quoting discipline

- Every quoted line carries a date `YYYY-MM-DD`
- Strictly identify the speaker: lines prefixed with `**Innei**:` are the user; unprefixed lines are the other party
- Never fabricate quotes. Unsupported claims may be flagged as "impression" or "lean" — never disguised as evidence
- Keep quotes short (1–2 lines); paraphrase longer passages with line-range citation

## Honest interpretation

When the user asks a subjective question, do not pander to their hoped-for answer. Read by objective signals:

| Signal | Meaning |
|--------|---------|
| Other party repeatedly offers to "matchmake" / "introduce someone" | They've placed themselves outside the candidate set |
| Explicit "I don't need a partner" | Single-life declaration |
| Invitation (meet / dinner) declined without leaving an opening | Hard boundary |
| Cold-shouldering emotion ("emo will make you ugly", "stop calling yourself depressed") | Refusal to be drawn in deeply |
| Geographic / career divergence ("I'll head home in two years") | Long-term incompatibility |
| Sexuality teasing from a "elder-sibling" register ("don't lock yourself into one gender") | Joke, not test |
| User self-talks themselves out ("I never make the first move", "I'm doomed to be alone") | Self-foreclosure |

Reading by these signals yields a relatively objective lean, free of the user's memory-tinted lens.

## Common mistakes

| Wrong | Right |
|-------|-------|
| Read the entire file in one go | Sample + grep |
| Judge from opening alone | Tail matters too — it has the latest state |
| Claims without quotes | Always cite date + original line |
| Mirror the user's hopes | Two-sided reading, objective lean |
| Confuse speakers | Check prefix every time before quoting |
| Ignore time | Note start–end dates per section |
| Trust user-supplied path blindly | `find` / `ls` to verify first |
| `cat` a giant file | Use `Read` or `head/sed` slicing |
| Dump L1+L2+L3+L4 in one reply | Stop at L1/L2; wait for follow-up |
| Misattribute or invent quotes | Strict honesty — omit rather than fake |

## Red flags

- Writing "they probably talked about X" without a quote → STOP, go grep
- Quote without a date → STOP, add it
- Subjective judgment with only one side → STOP, add the counter-side
- Answering "yes" or "no" to a "was there Y" question without listed evidence → STOP, list signals
