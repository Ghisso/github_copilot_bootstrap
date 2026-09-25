# Session: Sidecar Phase A — provider contract

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-A-sidecar-provider-contract.md`
**Status:** IN-PROGRESS

## Goal

Record documented and native discovery evidence for each client (Claude
Code, OpenAI Codex, GitHub Copilot in VS Code, Google Antigravity), then
freeze the read list, write list, and bridge paths in
`docs/sidecar-provider-contract.md`. No installer, generator, validator, or
test code changes in this phase.

## Work Log

- Pre-flight on `dev` at `1a06f1e`: clean outer and nested trees;
  `scripts/check_runtime.py` passes; `verify.py fast` is NOT_APPLICABLE (no
  changed Python). Branch `consumer-sidecar-bootstrap-overlay_implementation`
  created; the branch hook set the big plan `in-progress` and activated
  Phase A.
- Host clients checked 2026-09-25: Claude Code 2.1.226, codex-cli 0.147.0,
  VS Code 1.139.0 (WSL remote server), Git 2.43.0. The Antigravity CLI
  `agy` is not installed on this host.
- User decisions for step 3 (native runs), 2026-09-25:
  - Claude Code and Codex: the orchestrator runs `claude -p` and
    `codex exec` non-interactively in the fixture after the user runs the
    fixture recipe in their own shell (the agent-session commit gate blocks
    `git commit` even in other repositories). No trust or user-setting
    change; only marker-phrase yes/no results and structured skill lists are
    recorded, never raw transcripts.
  - Copilot in VS Code: the user runs the Local agent and Agent Host
    sessions and reports results.
  - Google Antigravity: recorded as `unavailable`. Its rules-file bridge
    therefore does not ship in v1 (Decision 14); `.agents/skills/` can still
    ship on Codex evidence.
- Steps 1-2 (documentation re-check and fixture recipe) delegated to
  `coder`. Result: `docs/sidecar-provider-contract.md`. Notable change from
  the plan's table: `code.claude.com/docs/en/memory` now documents that a
  rule without `paths` loads at launch with `CLAUDE.md` priority. The
  orchestrator added a "save as a file and run with bash" instruction,
  because pasting a `set -e` / `exit 1` block into an interactive shell
  closes that shell on the first error.
- Step 3, fixture: the user ran the recipe in their own shell on 2026-09-25;
  it printed `FIXTURE OK` at `/home/ghisso/sidecar-fixture-20260925-122447`.
  Orchestrator confirmed 7 tracked team files, 7 `!!` ignored sidecar files,
  empty `git status --porcelain --untracked-files=all`.
- Step 3, Claude Code 2.1.226 (`claude -p`, `--tools ""`,
  `--no-session-persistence`, `--strict-mcp-config`, clean environment via
  `env`-filtered subprocess; raw output discarded):
  - `system/init` event `skills` and `slash_commands`: `sidecar-marker-a`,
    `sidecar-marker-b`, `team-claude-skill`; no `team-agents-skill`, no
    `team-github-skill`. Ignored skills through `info/exclude` are
    discovered.
  - Zero tool uses; the reply quoted `TEAM-CLAUDE-MD-MARKER` and
    `BRIDGE-CLAUDE-RULE-MARKER`, not the `AGENTS.md`, Copilot, or
    Antigravity markers. The rule without `paths` loads with `CLAUDE.md`.
  - `/sidecar-marker-b` -> `SIDECAR-MARKER-B-CLAUDE`; `/sidecar-marker-a`
    -> `SIDECAR-MARKER-A-CLAUDE`.
  - `memory_paths` in the init event lists only the auto-memory folder, so
    it is not evidence for rules.
- Step 3, Codex 0.147.0:
  - `codex debug prompt-input` (the model-visible input, no model call):
    contains `TEAM-AGENTS-MD-MARKER`; skills `team-agents-skill`,
    `sidecar-marker-a`, `sidecar-marker-b`, all with
    `.agents/skills/<name>/SKILL.md` paths; no `.claude/` or `.github/`
    skill paths; no bridge marker.
  - `codex exec --json --ephemeral -s read-only`: zero
    `command_execution` items; reply lists the same three skills and the
    `AGENTS.md` marker.
- Fixture unchanged after both probes (empty status, still 7 ignored).
- Step 3, Copilot in VS Code 1.139.0 (built-in Copilot Chat 0.67.0, WSL
  remote), run by the user:
  - Local agent: prompt with no tool steps quoted both bridge markers
    (`.github/instructions` and `.claude/rules`), `copilot-instructions.md`,
    `AGENTS.md`, and `CLAUDE.md`. Each sidecar skill listed once, from
    `.agents/skills/`. `/sidecar-marker-b` -> `SIDECAR-MARKER-B-AGENTS`: the
    sidecar copy hid the team's `.github/skills/sidecar-marker-b` (native
    evidence for Decision 8). The `/sidecar-marker-a` reply was not captured
    (the paste repeated the marker-b reply).
  - Agent Host, Copilot harness: prompt quoted the `.github/instructions`
    bridge, `copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`; not the
    `.claude/rules` bridge. Skills listed once each. `/sidecar-marker-a` ->
    `.agents` copy. `/sidecar-marker-b` -> `-GITHUB-TEAM`, but weak: the
    agent ran terminal commands and read all three copies first.
- Step 4 (owner changed from `coder` to orchestrator, because the
  orchestrator held the raw observations): froze the matrix and the read
  list, write list, and bridge lists in `docs/sidecar-provider-contract.md`.
  Write list: `.claude/skills/`, `.agents/skills/`. Bridges:
  `.claude/rules/ai-bootstrap-sidecar.md` (no frontmatter) and
  `.github/instructions/ai-bootstrap-sidecar.instructions.md`
  (`applyTo: "**"`). Read list adds `.github/skills/` (native-run),
  `.agent/skills/` (documented), `.codex/skills/` (source).
- Step 5, decision gate: proceed. The only change from the expected layout
  is that the Antigravity bridge does not ship (Antigravity
  `unavailable`). The plan already made it conditional, so no planner
  revision; one-line notes added to Phase B step 2 and Phase D step 4.
  `validate_plan_frontmatter.py` exits 0 after the edits.

## [LEARN] Entries

- [LEARN:testing] Native discovery probes need evidence the model cannot
  produce by reading files: `claude -p --tools ""` with the stream-json
  `system`/`init` event (`skills`, `slash_commands`), and
  `codex debug prompt-input` (model-visible input as JSON, no model call).
  Any `command_execution` item in `codex exec --json` invalidates a marker
  result. Saved to `.claude/MEMORY.md`.
- [LEARN:architecture] All tested clients load skills and rules that only
  `info/exclude` ignores; Copilot's Local agent prefers `.agents/skills/`
  and let a sidecar copy hide a team skill of the same name in
  `.github/skills/`; the Local agent loads both `.github/instructions/` and
  `.claude/rules/`. Saved to `.claude/MEMORY.md`.

## Review

- Reviewer profiles `documentation`, `architecture`, `security`: gate PASS,
  0 critical, 0 major, 1 minor (Step 3's "Record" list omitted the skill
  names and folders that Step 4 reports). Fixed with the reviewer's
  suggested bullet; the same reviewer was asked to confirm the fix.
- `ponytail` was not selected, as the big plan specifies for Phase A. The
  commit gate agrees: `diff_requires_ponytail` requires it only for more
  than one outer path or a control-plane/script path, and the outer diff is
  the single file `docs/sidecar-provider-contract.md`. The plan-note edits
  live in the nested `.claude` repository.
- Documentation: the new contract document is this phase's documentation.
  README is unchanged because sidecar mode does not exist until Phase C;
  Phase D adds the README guidance and links the contract.

## Verification

Pending.

## Open Questions / Next Steps

- Step 3: user runs the fixture recipe; orchestrator runs Claude Code and
  Codex probes; user runs Copilot sessions.
- Step 4: freeze the matrix. Step 5: apply the decision gate.
