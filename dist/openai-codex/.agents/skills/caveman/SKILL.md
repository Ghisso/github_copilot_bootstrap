---
name: caveman
description: |
  Ultra-terse communication mode for token-efficient technical work. Use when:
  - User asks for "caveman mode", "less tokens", "be brief", "be terse",
    "shorter answers", or "less verbose"
  - Implementation or review output should stay accurate but cut filler
  - You need terse findings, terse coding updates, or terse rewrite passes
argument-hint: "[lite|full|ultra]"
---

# Caveman

## Problem

Some tasks benefit from much shorter prose: reviewer findings, implementation
updates, and terse explanations that keep the technical substance but cut the
filler.

## Context / Trigger Conditions

Use this skill when the user wants lower token usage or explicitly asks for a
shorter style.

Common triggers:

- "caveman mode"
- "less tokens"
- "be brief"
- "be terse"
- "shorter answers"
- "less verbose"

Default to `full` unless the user specifies another level.

## Solution

### Intensity levels

| Level | Behavior |
| --- | --- |
| `lite` | Full sentences, no filler, no hedging, still professional |
| `full` | Default. Drop filler and articles where safe. Fragments allowed |
| `ultra` | Maximum compression. Short fragments, abbreviations, arrows, minimal glue words |

### Core rules

1. Keep technical terms exact.
2. Keep code, commands, paths, URLs, versions, error messages, and quoted text exact.
3. Prefer this pattern when it fits: `[issue] [cause]. [fix]. [next step].`
4. Drop filler, hedging, pleasantries, and repeated framing.
5. Keep safety-critical detail. Never trade clarity for terseness in warnings.

### Drop aggressively

- Articles and filler when meaning stays clear
- Hedging like "you might want to" or "it would be good to"
- Repeated restatement of the same point
- Introductory throat-clearing before the actual answer

### Preserve exactly

- Code blocks and inline code
- File paths and commands
- URLs and markdown links
- Environment variables, version numbers, and identifiers
- Error text when diagnosing a failure

### Auto-clarity exceptions

Suspend caveman mode and write normally for:

- destructive or irreversible actions
- security warnings
- multi-step sequences where order matters
- cases where the user seems confused and compression would hide key nuance

Resume terse mode after the high-risk section is clear.

## Verification

- The response is materially shorter than the default version.
- Code, commands, file paths, and quoted errors remain exact.
- Warnings stay explicit when safety or reversibility matters.

## Example

Original:

> The failing test is caused by a missing null guard in the parser. Add the
> guard before dereferencing `node.text`, then rerun the parser tests.

`full`:

> Parser miss null guard. `node.text` deref crash. Add guard, rerun parser tests.

## References

- Inspired by the upstream `JuliusBrussee/caveman` project, adapted for this bootstrap.
