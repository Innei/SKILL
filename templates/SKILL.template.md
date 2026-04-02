---
name: skill-name
description: State precisely what the skill does, when it should be used, and what special workflow or domain knowledge it provides.
---

# Skill Title

Use this skill when the task requires a repeatable workflow that benefits from stable procedural guidance rather than ad hoc reasoning.

## Scope

- Define the target task class.
- State the expected environment or prerequisites.
- State what this skill does not cover.

## Inputs

| Variable | Meaning |
|---|---|
| `INPUT_NAME` | Explain the required input |

## Workflow

```text
[1] Gather context
      -> identify required inputs and constraints

[2] Execute the core procedure
      -> apply the domain-specific method

[3] Validate the result
      -> confirm correctness before reporting completion
```

## Rules

- Keep instructions concise.
- Prefer deterministic commands for fragile steps.
- Move large reference material into `references/` when necessary.
- Do not embed secrets or machine-specific credentials.

## Verification

- State the minimum read-only or non-destructive checks that should be run before completion.
