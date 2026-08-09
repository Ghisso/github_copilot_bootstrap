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

Apply these rules strongly to user answers, plans, architecture explanations,
reviews, quality reports, summaries, session summaries, and documentation.
Apply them lightly to commit messages. Do not apply them to source code or exact
technical material.

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

Do not make a rewrite stage mandatory. The optional `humanize` skill can help
when it is useful, but it does not replace authorial judgment or exact-content
protection.

## Agent-to-agent status and handoffs

For compact internal status messages and handoffs, `caveman full` may be the
default when it improves precision and token efficiency. It is not the default
for user communication. Use normal human-facing prose for safety warnings,
destructive actions, and ordered procedures when extra clarity matters.

The documenter writes user-facing documentation in normal prose under the
human-facing rules above.
