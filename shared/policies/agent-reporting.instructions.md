---
description: Define audience-aware communication for users and agent handoffs.
applicability: always
---

# Audience-Aware Reporting Policy

This is the single home for how agents communicate. Agents reference this policy
rather than restating its rules elsewhere.

## Human-facing communication

Use precise, clear, direct, natural prose for communication with people. These
rules are inspired by ASD-STE100 principles, but this project does not claim
formal ASD-STE100 compliance.

Apply these rules to every top-level message to the user: clarifying questions,
progress or status updates, explanations, recommendations, decisions, warnings,
summaries, and final reports. Apply them lightly to commit messages. Do not
apply them to source code or exact technical material.

Before sending a human-facing response, perform a send-time self-check against
these rules as part of composing that response, not as a separate rewrite
lifecycle. Preserve exact technical evidence during the check.

- Use common words when they are as precise as uncommon words.
- Use one term consistently for one concept; avoid unnecessary synonyms.
- Use short, direct sentences. Split a complex explanation into smaller
  statements, and use active voice where practical.
- Avoid idioms, buzzwords, marketing language, and unnecessary abbreviations.
- Define an uncommon abbreviation or technical term when you first use it.
- Keep established technical terms when they are the most precise words.
  Technical precision has priority over simpler vocabulary.

Keep exact technical material exact. Do not lossily rewrite identifiers, API
names, commands, paths, logs, errors, structured findings, quotations, source
code, or other material whose wording is evidence. Preserve tables, code
blocks, severity labels, scores, and safety-critical detail literally.

Do not make a general rewrite stage mandatory. The documenter has a narrow
mandatory `humanize` `edit` self-check for prose it creates or changes. It does
not replace authorial judgment, and exact-content protection always wins.

## Agent-to-agent status and handoffs

For compact internal status messages and handoffs, `caveman full` may be the
default when it improves precision and token efficiency. It is not the default
for user communication. Use normal human-facing prose for safety warnings,
destructive actions, and ordered procedures when extra clarity matters.

Compact internal handoffs may remain compressed, but do not relay them verbatim
when they are unsuitable for the user; compose user-facing prose under the
human-facing rules instead.

The documenter writes user-facing documentation in normal prose under the
human-facing rules above.
