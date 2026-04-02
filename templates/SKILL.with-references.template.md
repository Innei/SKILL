---
name: skill-name
description: State precisely what the skill does, when it should be used, and what bundled references should be consulted.
---

# Skill Title

Use this skill when the task requires a repeatable workflow plus a small amount of domain reference material.

## Scope

- Define the target task class.
- State the expected environment or prerequisites.
- State which details live in `references/`.

## Inputs

| Variable | Meaning |
|---|---|
| `INPUT_NAME` | Explain the required input |

## Workflow

```text
[1] Gather context
      -> identify required inputs and constraints

[2] Read the necessary reference file
      -> load only the relevant file from references/

[3] Execute the core procedure
      -> apply the domain-specific method

[4] Validate the result
      -> confirm correctness before reporting completion
```

## References

- `references/domain.md`: Explain when this file should be read.

## Rules

- Keep the main skill concise.
- Move long schemas, policies, or examples into `references/`.
- Do not duplicate large blocks between `SKILL.md` and `references/`.
- Do not embed secrets or machine-specific credentials.
