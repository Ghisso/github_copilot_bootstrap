---
name: 2026-09-19_phase-J-openwiki-docs-memory-migration
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 10
status: planned
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-J-openwiki-docs-memory-migration

## Scope

After the user has inspected the Phase I wiki and explicitly confirmed, reduce duplicated
descriptive documentation and MEMORY content only where generated coverage is proven adequate.
Keep policy, security, ADRs, operator instructions, README entry-point material, plans/logs, and
non-derivable MEMORY content under human ownership. No OpenWiki refresh runs here; Phase K does
that. This is a transition phase, not the template for future knowledge-refresh phases.

## Steps

### Step J1 — Confirmation gate

- [ ] **Owner:** orchestrator
- **Behavior:** do not begin J2 until the user has explicitly confirmed migration after
  inspecting `openwiki/**`; quote the confirmation in this phase's session log. Requested wiki
  changes belong to a refresh (Phase K shape), not here.

### Step J2 — Audit generated coverage before removing manual knowledge

- [ ] **Owner:** `documenter`
- **Target files (read-only):** `openwiki/**`, `README.md`, live `docs/**`, `shared/MEMORY.md`,
  root/manual policy and ADR surfaces
- **Required Skills:** `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`,
  `shared/skills/deep-audit/SKILL.md`
- **Disposition per surface:** KEEP; SHORTEN/LINK; REMOVE (purely descriptive duplicate
  adequately generated and grounded); KEEP + OPENWIKI GAP (update `openwiki/INSTRUCTIONS.md`).
- **MEMORY disposition:** keep rationale, durable caveats, environmental facts, non-derivable
  decisions; remove live advice that merely restates current source now covered by OpenWiki;
  never rewrite closed plans/logs.
- **Acceptance criteria:** no file removed merely because OpenWiki exists; every
  removal/shortening names its generated replacement or entry-point rationale.
- **Verification:** `documentation` profile review of the disposition before any removal.

### Step J3 — Apply the conservative migration

- [ ] **Owner:** `coder` for tracked edits, `documenter` for prose
- **Target files:** `README.md`, selected live `docs/**`, `shared/MEMORY.md`,
  `openwiki/INSTRUCTIONS.md` when J2 found gaps, links to removed docs
- **Required Skills:** `shared/skills/ponytail/SKILL.md` in `full` mode for any code change,
  `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`,
  `shared/skills/learn/SKILL.md`
- **Rules:** prefer shortening over deletion for human-audience docs; preserve ADRs, security,
  policy, procedures, dated records (including the Phase F spike narrative); keep README a small
  entry point; narrow MEMORY, never delete it; update references atomically
  (`validate_targets.py` link integrity covers `README.md`, `AGENTS.md`, `docs/*.md`).
- **Verification:** `uv run python scripts/validate_targets.py`;
  `uv run python .claude/scripts/verify.py fast --format json`

### Step J4 — Review

- [ ] **Owner:** `reviewer`
- **Review Profiles:** `documentation`, `architecture`, `security`; `code`, `tests`, `ponytail`
  when any code changed
- **Review focus:** no normative information exists only in generated OpenWiki; no unique human
  content erased; no stale live link.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [ ] User confirmation quoted in the session log before any migration edit
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and names this a transition phase
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)

## Pause Checkpoint

(template text, identical to Phase F)
