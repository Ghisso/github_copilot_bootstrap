# Session: Knowledge refresh and final audit (skills-and-instructions-trim, Phase D)

**Date:** 2026-11-14
**Plan:** `.claude/plans/2026-11-12_phase-D-knowledge-refresh.md`
**Status:** COMPLETED

## Goal

Refresh the OpenWiki pages that describe skills, installer ownership, and the lifecycle through OpenWiki's own tools; run the standing final-phase documentation, memory, and LEARN audit over every live-advice surface; regenerate and self-refresh; record the audit under `## Stale-claims surfaces checked` (REQ-010).

## Work Log

- Phase C committed as `1afc619` and pushed; the post-commit hook set Phase D `in-progress`. Material-impact check: Phases A-C's outcomes are what this phase documents; no planner run. The OpenWiki base is `950dde7` (2026-11-12).
- Read `.claude/skills/knowledge-refresh/SKILL.md` (installed copy) before the refresh. Per MEMORY, no other agent edits tracked files while the OpenWiki run is open; the audit runs after `openwiki_finish`.
- Step 1, OpenWiki refresh (run `d33af114`): `openwiki_begin` with `mode: "update"` opened planning; right after it, `git status --porcelain -- AGENTS.md CLAUDE.md` was empty and neither file held `<!-- OPENWIKI:START -->`. A sweep of every wiki page for stale text found hits only in the seven pages with flagged claims, so the plan was those seven: `architecture/agents-and-skills.md` (37 skills, merges, the 300-character cap, loading rules, project skills, Codex listing from `.agents/skills/`), `architecture/source-generated-consumer-layout.md` (the two new instruction files, the Codex config comment, the validator's new first checks), `operations/deterministic-verification.md` (the closeout file as the written gate, a new "Static checks on the guidance itself" section), `operations/install-ownership-and-runtime-checks.md` (marker, refusals, shipped-before record, mirror, renumbered full-install sequence), `operations/sidecar-overlay.md` (22 workflow skills; marker inert), `workflows/lifecycle-and-task-lanes.md` (three-file split, closeout summary with link, stale-receipt recovery, targeted MEMORY search), and `quickstart.md` (routing rows for closeout, plan lifecycle, and project skills). 31 flagged claims reconciled (revised with current evidence, or confirmed after a recheck), plus new claims for each new fact. `openwiki_finish` returned `complete`; `openwiki/.run.json` absent.
- Step 2, audit: a scripted sweep (`audit_scan.py` in the session scratchpad) over 127 live-advice files for the plan's claim list, then targeted greps for references that send readers to the workflow policy for moved sections. Fixes: `docs/runtime-checks.md:767` (reopening now points at `plan-lifecycle.instructions.md`); `shared/policies/closeout.instructions.md` step 4 now names the full recorder command `uv run python .claude/scripts/record_findings.py` (Phase B optional-1 gap); authoring `AGENTS.md` now says to follow the closeout file at CLOSEOUT (Phase B optional-3 gap); two `.claude/MEMORY.md` entries corrected in place (the closeout-status lesson now names `closeout.instructions.md`; the progressive-disclosure lesson no longer names the retired `caveman-compress` as if current); user-level memory: `feedback_personal_bootstrap_not_generic.md` updated (niche content kept, merged into two skills on 2026-11-13), `project_closeout_order_hooks.md` repointed to the closeout file, new `project_skills_trim.md`, index updated.
- Second OpenWiki run (`632266c5`): the closeout-file fix changed the evidence of two lifecycle-page claims; a one-page update rechecked and confirmed both (no prose change); `openwiki_finish` returned `complete`.
- Step 3: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0, no refusal.
- Review round 1 (six profiles): gate FAIL on three MAJOR documentation findings, all audit misses: `.claude/instructions/project-context.instructions.md` still said "55 reusable skills" with an old policy list, and twice said a refresh deletes everything under `.claude/` outside consumer state (no project-skill exception or refusal); `shared/plans/README.md:15` still said "Always: `plan-decomposition/SKILL.md`". The first audit record had wrongly called project context refreshed by Step 3 (it is consumer state). The reviewer confirmed the three source fixes, the seven refreshed pages against the code, the wiki process (no run file, no root block, only OpenWiki-owned sidecars changed), and no remaining retired names.
- Fixes: the three project-context passages and the plans README line; a README bullet pair under `workflow.instructions.md` (reviewer note); the audit record corrected, with an Active plans row. After: regenerate + self-refresh 0 (installed `.claude/plans/README.md` updated); `validate_targets.py` PASS; `check_runtime.py` 0; a wider re-sweep found nothing.
- Review round 2 (same reviewer): gate PASS, no CRITICAL or MAJOR, one MINOR (the audit record's README row did not mention the README fix), fixed by updating that row before CLOSEOUT step 2; recorded with disposition `fixed`. Follow-ups needing a later OpenWiki update (cosmetic, non-blocking): a double blank line and a "plan templates point here" sentence on the lifecycle page; the sidecar page's test bullet does not name the two test files.
- CLOSEOUT step 1: README, `docs/runtime-checks.md`, `shared/plans/README.md`, the authoring `AGENTS.md`, and the standing audit below. CLOSEOUT step 2: read the learn skill; one MEMORY entry added (below); small plan `status: complete`, boxes ticked; Phase D ticked in the big plan (the post-commit hook completes the big plan).

## [LEARN] Entries

- [LEARN:workflow] The final-phase audit must read consumer-state files such as `.claude/instructions/project-context.instructions.md` directly (the self-refresh never rewrites them) and search claim shapes loosely; an exact-phrase sweep missed three stale claims the review caught. Saved to `.claude/MEMORY.md`.

## Verification

```text
PASS        0.2s  uv run python scripts/generate_targets.py --all
PASS        0.0s  uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.is_dir()] + [str(p) for r in roots if r.is_dir() for p in sorted(r.rglob("*.md")) if p.is_file() and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'skills/(review-api|run-tests|refactor|pdf|caveman-compress|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing|pipeline-patterns|haystack-conditional-router|docling-haystack|ollama-chat-generator|pandas-nan-bool-coercion|networkx-igraph-graphml-interop|pyvis-xss-testing|csv-driven-integration-tests|deploy-service|context-manager-testing|test-helper-public-api)/|(?i:there are 55)' openwiki
PASS        0.0s  grep -q -F 'data-and-graph-pitfalls' openwiki/architecture/agents-and-skills.md
PASS        0.0s  grep -q -E '\b37\b' openwiki/architecture/agents-and-skills.md
PASS        0.0s  grep -q -F '.project-skill' openwiki/operations/install-ownership-and-runtime-checks.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' openwiki/workflows/lifecycle-and-task-lanes.md
PASS        0.0s  uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.exists()] + [str(p) for r in roots if r.exists() for p in ([r] if r.is_file() else sorted(r.rglob("*"))) if p.is_file() and "__pycache__" not in p.parts and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'loaded into every session|Never checkpoint after the receipts are persisted' shared README.md docs/architecture.md docs/target-mapping.md
PASS        0.0s  test ! -e openwiki/.run.json
PASS        0.0s  test "$(grep -c -F '<!-- OPENWIKI:START -->' AGENTS.md)" = "0"
PASS        0.0s  test "$(grep -c -F '<!-- OPENWIKI:START -->' CLAUDE.md)" = "0"
PASS       45.0s  uv run python scripts/validate_targets.py
PASS        0.7s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      314.5s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-12_phase-D-knowledge-refresh.json` (1 MINOR, disposition `fixed`; gate PASS; six profiles; round 1 had three MAJORs, all fixed before round 2).
- Phase receipt: `verify.py phase --persist` PASS (pytest completed (5084 passed, 1 skipped in 309.23s (0:05:09)); mypy 0 errors; Ruff 0 violations).
- optional 1: PASS — each refreshed page's prose was written against the cited code during the run, and the Phase D reviewer read all seven pages against `scripts/install_bootstrap.py`, `scripts/runtime_ownership.py`, `scripts/validate_targets.py`, `scripts/generate_targets.py`, and `shared/policies/*` in two rounds; no prose mismatch, only the three cosmetic follow-ups listed above.

## Stale-claims surfaces checked

- `CLAUDE.md` (authoring): no stale claim (Phase B already points at the closeout file and uses the targeted MEMORY search).
- `AGENTS.md` (authoring): stale by omission; it named no closeout file. Added "At CLOSEOUT, follow `.claude/instructions/closeout.instructions.md` step by step."
- `README.md`: two stale bullets under `workflow.instructions.md` in "Most Important Instructions" fixed after the Phase D review ("commit/PR gates" now points at `closeout.instructions.md`; "recovery reminders" became "context management", since the recovery checklist was removed in Phase B). Line 937 "A full refresh deletes every file under `.claude/` it does not generate" opens the Project-owned skills section and the next sentence gives the marker exception; kept. Retired names, "hidden helpers", 55/25 counts: none.
- Undated `docs/` pages (`architecture.md`, `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, and the rest): one stale pointer fixed (`runtime-checks.md:767`, reopening procedure location). `runtime-checks.md:836` correctly keeps the Verification Evidence Contract in the workflow core. `docs/sidecar-provider-contract.md:40` ("Undocumented" duplicate-name behavior for Copilot) is the documentation-tier column of a dated evidence record whose later native-run rows supersede it; left unchanged as a dated record.
- `shared/policies/`: one gap fixed (the closeout file's recorder command lacked its `uv run python .claude/scripts/` prefix). No "loaded into every session", no full MEMORY read, no CLOSEOUT restatement outside the closeout file.
- `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, `shared/sidecar/`: no retired skill name, Completion Protocol, "Never checkpoint after the receipts", or stale closeout location.
- State READMEs (`.claude/plans`, `explorations`, `session_logs`, `quality_reports` and their `shared/` seeds): one stale claim, found by the Phase D review and fixed: `shared/plans/README.md:15` said "Always: `plan-decomposition/SKILL.md`"; it now says full-plan mode only, with micro-plans reading the two templates (the installed copy refreshes through Step 3).
- `.claude/instructions/project-context.instructions.md` (consumer state, so Step 3 never rewrites it; the first record wrongly said it did): three stale claims, found by the Phase D review and fixed: "55 reusable skills" (now 37), the policy list (now names closeout and plan-lifecycle), and two sentences saying a refresh deletes everything under `.claude/` outside consumer state (now name the third-party and `.project-skill` exceptions and the `validate_project_skills` refusal).
- Active plans: the big plan `.claude/plans/skills-and-instructions-trim.md` and its four small plans are consistent with the final outcomes (the Phase A scope change is recorded in the big plan's Design Overview); no other plan is active.
- This repository's installed `.claude/` overlay: refreshed by Step 3 from `shared/`; `check_runtime.py` passes.
- `.claude/MEMORY.md`: two entries corrected in place (closeout authority; retired skill named as current). The July 2026 "keep niche skills" decision is not in this file; it lives in user-level memory, which was updated.
- The generated Codex config comment and docs repeating the old Codex skills claim: fixed in Phase C; recheck found none.
- Dated records left unchanged: archived plans, explorations, `docs/evidence/`, `docs/2026-*`, closed session logs.

## Open Questions / Next Steps

- All four phases of `skills-and-instructions-trim` are done; a PR to `dev` is the user's call.
- User follow-ups: remove the 55 inert `[[skills.config]]` entries from the generated Codex config (spike S1 showed they add no skill); the three cosmetic wiki items above at the next OpenWiki update; `CODEX_POLICY_SKILL_FALLBACKS` checks only that each fallback skill exists.
