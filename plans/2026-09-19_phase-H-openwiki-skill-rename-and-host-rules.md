---
name: 2026-09-19_phase-H-openwiki-skill-rename-and-host-rules
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 10
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-H-openwiki-skill-rename-and-host-rules

## Scope

OpenWiki's host integration installs its own skill, named `openwiki`, at
`.claude/skills/openwiki` (Claude Code) and `.agents/skills/openwiki` (Codex), and refuses to
install while an unmanaged skill occupies either path. The bootstrap-generated skill of the same
name occupies both, and skill names must be unique per host. This phase renames the bootstrap
skill to `knowledge-refresh`, rewrites it for host-driven operation, and replaces the three
committed rules that forbade host integrations with the precise rule below.

The two skills have different jobs: OpenWiki's `openwiki` skill is the tool-lifecycle and
authoring contract; the bootstrap's `knowledge-refresh` skill is the lifecycle policy around it
(when to refresh, enablement, the guard, ownership, rebaseline, commit hygiene).

## Steps

### Step H1 — Rename and rewrite the bootstrap skill

- [ ] **Owner:** `coder` (rename, validators) + `documenter` (prose)
- **Target files:** move `shared/skills/openwiki/SKILL.md` →
  `shared/skills/knowledge-refresh/SKILL.md` (`name: knowledge-refresh`; `visibility: public`)
- **Required Skills:** `shared/skills/ponytail/SKILL.md` in `full` mode,
  `shared/skills/code-style/SKILL.md`, `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`
- **Skill body must cover, in plain language:**
  - trigger and negative scope: refresh, enable, or rebaseline this repository's generated
    `openwiki/**` layer through OpenWiki's MCP tools; not for README/docs writing or other wiki
    tools; load OpenWiki's own `openwiki` skill for the tool sequence itself
  - ownership pointer to `workspace.instructions.md` Knowledge Ownership (unchanged)
  - enablement procedure: write `openwiki/INSTRUCTIONS.md` and `.openwikiignore`; run
    `openwiki integrations install claude --project <root>` and
    `openwiki integrations install codex --project <root>` once per checkout; approve the
    project MCP server in Claude Code; confirm `openwiki integrations list --project <root>`
    reports `installed`; commit the resulting `.mcp.json`/`.codex/config.toml` diffs; a
    reported unmanaged skill at either path is a stale bootstrap copy from before this rename —
    confirm it has no `.openwiki-install.json`, remove it, re-run; never `--force`
  - running a refresh: always `mode: "update"`, never `init`; the bootstrap's `openwiki-guard`
    hook denies `init` and unenabled repositories and restores the root adapters after
    `openwiki_begin` on the hosts named in `docs/2026-09-19-openwiki-hook-mechanics-spike.md`
    (state any per-host adaptation Phase G applied); after `openwiki_begin` check
    `git status --porcelain -- AGENTS.md CLAUDE.md` is empty, otherwise run
    `.claude/hooks/scripts/openwiki-guard.sh post </dev/null`; one run per checkout; a failed
    run leaves `openwiki/.run.json` for resume — never delete it, never commit it; `noop` means
    nothing to do; report success only after `openwiki_finish` returns `complete`
  - what never changes: never hand-edit generated pages or `.claims`; never `init`; never
    create or modify a scheduled workflow; never run the integration installer from hooks,
    `verify.py`, the bootstrap installer, state-sync, CI, or as part of a refresh; never
    `--force`; provider credentials are not needed in host-driven mode and never enter the
    repository; supported hosts are Claude Code and Codex — other targets read `openwiki/**`
    but cannot refresh it
  - rebaseline rule unchanged in substance ("first generation in `update` mode")
- **Acceptance criteria:** passes the skill validators in `scripts/validate_targets.py`; no
  sentence describes a mechanism that does not exist at this commit.
- **Verification:** `uv run python scripts/generate_targets.py --all && uv run python scripts/validate_targets.py`

### Step H2 — Sweep every reference and amend the rules

- [ ] **Owner:** `coder` for generator strings, `documenter` for prose
- **Target files:** authoring `AGENTS.md:9`, `CLAUDE.md:14`, `render_root_guidance` in
  `scripts/generate_targets.py`; `shared/policies/workflow.instructions.md` (OpenWiki Refresh;
  Knowledge-Refresh Shape); `shared/policies/workspace.instructions.md` if the skill is named;
  `shared/agents/orchestrator/prompt.md:56`, `shared/agents/documenter/prompt.md:42`;
  `docs/architecture.md`; `README.md`; after self-install remove the stale bootstrap copies
  `.claude/skills/openwiki/` (nested repo) and `.agents/skills/openwiki/` that
  `check_runtime.py` reports as obsolete, so Phase I's installer finds the paths free
- **Required Skills:** `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`
- **Acceptance criteria:** `grep -rn 'skills/openwiki' shared scripts docs README.md AGENTS.md CLAUDE.md`
  returns only lines that intentionally describe OpenWiki's own installed skill; the Codex
  `[[skills.config]]` set equals the `shared/skills` set (validator-enforced).
- **Verification:** `uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py`

### Step H3 — Review

- [ ] **Owner:** `reviewer`
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`
- **Review focus:** the rule is precise (what, by whom, when); no target loses the skill;
  wording consistent across policy, prompts, root guidance, docs, and the spike evidence.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] `.claude/skills/openwiki/` and `.agents/skills/openwiki/` no longer exist in this checkout

## Pause Checkpoint

(template text, identical to Phase F)
