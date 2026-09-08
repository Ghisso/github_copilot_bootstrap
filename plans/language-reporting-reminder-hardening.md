---
name: language-reporting-reminder-hardening
type: big-plan
status: planning
originating_branch: dev
implementation_branch: language-reporting-reminder-hardening_implementation
started_at:
phases:
  - 2026-09-08_phase-A-language-reporting-reminder-hardening
current_phase:
---

# Big Plan: language-reporting-reminder-hardening

## Context

Claude Code repeatedly drifts from the shared human-facing reporting rules during
long orchestrated turns. OpenAI Codex shows the same problem less often. Static
guidance and a send-time self-check are already present, but their influence can
weaken after many tool calls and a long implementation lifecycle.

The first implementation should reinforce the existing policy without creating
a second writing authority or injecting reminders after every tool call. Claude
Code and Codex have compatible `UserPromptSubmit` context output and existing
`PostToolUse` hook wiring. GitHub Copilot and Google Antigravity do not have a
verified equivalent per-prompt contract in this bootstrap and must retain their
current hook behavior.

## Goals

- Add concrete examples that help agents recognize unclear labels,
  abbreviations, idioms, and vague options before sending a response.
- Remind Claude Code and Codex of the reporting rules when a user submits a
  prompt.
- Refresh the reminder late in long implementation turns after commands that
  normally precede the final user report.
- Keep each injected reminder short, non-blocking, and bounded by a validated
  byte limit.
- Preserve existing state synchronization and hook safety behavior.
- Keep GitHub Copilot and Google Antigravity as supported targets without
  inventing unsupported hook events.
- Measure the result before considering periodic or compaction-time reminders.

## Design Overview

Keep `shared/policies/agent-reporting.instructions.md` as the only detailed
writing policy. Add a small violation-recognition section with before-and-after
examples while preserving exact technical material and the separate compact
agent-to-agent style.

Add one canonical `reporting-reminder.sh` script. It uses the existing
`run-hook.sh` dispatcher and `_lib-frontmatter.sh` JSON helper. In prompt mode it
always emits one `UserPromptSubmit.additionalContext` object. In late-report mode
it reads a `PostToolUse` payload and emits one `PostToolUse.additionalContext`
object only after a successful Bash command that represents a final workflow
boundary, such as `verify.py closeout`, phase-completion `git commit`, or another
existing closeout command selected from the canonical lifecycle. Non-matches,
malformed input, or internal failures warn on standard error and exit zero.

Wire prompt mode beside the existing state-sync handler in both Claude and
Codex. Wire late-report mode into their existing Bash `PostToolUse` groups. Do
not add a fixed every-N-tools counter. Do not add `PreCompact` wiring in this
first version: whether injected context survives compaction as intended remains
an external runtime assumption, and the accepted late-report boundary addresses
the observed implementation-workflow failure with lower recurring cost.

The reminder text should remain semantically equivalent to:

> For user-facing updates, use direct language. Explain internal labels and
> uncommon abbreviations. Avoid idioms. Describe what options mean in practice.
> Preserve exact technical text.

## Non-Goals

- Do not add Gemini CLI support or change the set of supported targets.
- Do not add GitHub Copilot or Google Antigravity hook events.
- Do not block, rewrite, or inspect a completed assistant response from a Stop
  hook.
- Do not use a language model, external service, or dependency to judge prose.
- Do not inject the reminder after every tool call or maintain a per-session
  tool-call counter.
- Do not add `PreCompact` behavior without separate source and runtime evidence.
- Do not change consumer continuous-integration behavior; that work remains in
  `.claude/explorations/2026-09-08_consumer-ci-enforcement/evidence.md`.
- Do not hand-edit `dist/multi-agent/` or the installed generated adapters.

## Phases

- [ ] `2026-09-08_phase-A-language-reporting-reminder-hardening` — strengthen
  the policy, add bounded Claude/Codex reminders, validate target boundaries,
  regenerate, and document the behavior.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/ -q --tb=short
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Completion Evidence

The final and only phase must run a documentation, memory, and LEARN audit. It
must check every live-advice surface for stale reporting and target-support
claims, correct current guidance, and leave historical records unchanged unless
they actively mislead. The completed session log must record the checked
surfaces and outcomes under the exact heading
`## Stale-claims surfaces checked`.

