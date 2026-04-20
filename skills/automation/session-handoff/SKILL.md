---
name: session-handoff
description: >
  Produce a self-contained handoff prompt for another agent (Codex, a fresh
  Claude session, a teammate) when the user wants to delegate continued work.
  Triggers on: "写一个 prompt 给 codex"、"交接一下"、"让 xxx 跟进"、"summary
  一下再写个 prompt"、"handoff to another agent"、"write a prompt so X can
  continue", or any request to capture the current session state for
  continuation elsewhere.
metadata:
  author: innei
  version: "0.1.0"
---

# session-handoff

Write a handoff prompt that lets a cold receiving agent continue the current
work without re-asking the user for context. The receiving agent has **zero**
knowledge of this session — the prompt must be self-contained.

## When to invoke

- User explicitly asks to hand off: "让 codex 跟进", "write a prompt for X",
  "交接给 xxx".
- User asks for a session summary that will be forwarded to another agent.
- User wants to pause and capture state for later continuation.

Do **not** invoke when the user just wants a status update or a summary *for
themselves* — those are conversational, this produces a delegation artifact.

## Required sections

The output is a single Markdown document the user will copy and paste. It
must contain the following sections, in order, with the section titles as
written (Chinese / English mix is fine — match whatever the rest of the
session is using):

1. **用户与环境 / User & Environment**
   - Who the user is (name, handle, role) and contact if known.
   - Working directory, current branch, target merge branch.
   - Local services / databases (host, port, db name, credentials) the
     receiving agent will need. Redact `.env` contents and cloud tokens.
   - Dev workflow commands actually in use (`bun run dev:spa`, `pnpm xxx`,
     etc.).
   - User preferences and hard constraints (git rules, commit conventions,
     "do not touch" list, lint/test scoping rules, output style).

2. **当前正在处理的事项 / Current Task**
   - Top-level goal in 1–2 sentences.
   - The current blocker or open question.
   - If a previous approach was abandoned, say **why** so the receiver
     doesn't retry it.

3. **本会话已完成的工作 / History**
   - Chronological or grouped bullets.
   - Each bullet names: what changed, which files/lines, the rationale, and
     any user feedback that shaped the decision.
   - Include deprecations/migrations touched, not just additions.

4. **下一步待做 / Next Steps**
   - Numbered, concrete actions.
   - For each: files to touch, the specific change, and any preconditions.
   - Inline open questions that the receiver must ask the user before
     committing.
   - State which path you **recommend** and why, so the receiver can challenge
     the recommendation instead of rediscovering it.

5. **关键文件速查 / Key Files Index**
   - Grouped by concern (UI / services / server / schema / packages / tests).
   - One line per file explaining its role in this task.

6. **调试 / 验证方法 / Debug & Verification**
   - Exact shell commands to verify state (DB queries, log filters, curl
     invocations).
   - The test scenarios that should pass before shipping.
   - How to reproduce the original bug (if applicable).

7. **需要用户定夺的点 / Open Decisions**
   - Policy or UX questions the receiving agent must NOT silently choose.
   - Phrase each as a question with the options already identified.

## Writing rules

- **Self-contained.** No phrases like "as we discussed earlier" or "per the
  previous exchange". Inline the context.
- **Concrete over abstract.** "改 `foo.ts:42` 的 `MAX_RETRIES` 从 3 到 5" beats
  "tune retry behavior".
- **Backticks** around file paths, commands, identifiers, and DB rows.
- **Line numbers** whenever referencing a specific location — paths alone rot
  less, but line numbers make the handoff immediately actionable.
- **Shell blocks** for DB queries, `gh` commands, `bunx` invocations. Use
  real, pasteable snippets; don't pseudocode.
- **Quote user feedback verbatim** when it shaped a decision — the receiver
  needs to know what the user said literally, not a paraphrase.
- **No filler.** Skip "this was a great discussion", emoji, or apology prose.
- **Redact secrets.** `.env`, tokens, API keys never go into the prompt. If
  the receiver needs them, tell them to ask the user.

## Presentation to the user

- Preface the prompt with a short single sentence in the user's preferred
  style saying "this is the handoff prompt, paste it into $target".
- Wrap the entire prompt in a fenced code block (four backticks if the prompt
  contains triple-backtick code blocks internally). The user should be able
  to copy once and paste into the target tool.
- Do **not** execute the handoff yourself (don't spawn the other agent). Your
  job is to produce the artifact.

## Quality bar

Before emitting, check:

- [ ] Could a cold teammate start from this prompt and work for an hour
      without needing to ask the user anything other than the listed Open
      Decisions?
- [ ] Are all file paths real? No invented paths.
- [ ] Are user-visible decisions and trade-offs preserved, not averaged out?
- [ ] Are there concrete shell commands in the debug section?
- [ ] Did any secret sneak in? Scan for tokens, passwords, DSNs.

If any answer is "no", revise before showing to the user.
