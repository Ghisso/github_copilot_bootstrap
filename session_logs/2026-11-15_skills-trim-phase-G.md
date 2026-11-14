# Session: Knowledge refresh and final audit (skills-and-instructions-trim, Phase G)

**Date:** 2026-11-15
**Plan:** `.claude/plans/2026-11-14_phase-G-knowledge-refresh.md`
**Status:** COMPLETED

## Goal

Refresh the OpenWiki pages that carry review finding R23 or describe what Phases E and F changed, through OpenWiki's own tools; run the standing final-phase documentation, memory, and LEARN audit with the surface list Phase E extended; regenerate and self-refresh; record the audit under `## Stale-claims surfaces checked` (REQ-013).

## Work Log

- Phase F committed as `ea8b475` and pushed; the post-commit hook set Phase G `in-progress` and moved `current_phase`. Material-impact check: Phases E and F are the content this phase documents; no planner run.
- Read `.claude/skills/knowledge-refresh/SKILL.md` and `.claude/skills/openwiki/SKILL.md` before the refresh. No other agent edits tracked files while the OpenWiki run is open; the audit runs after `openwiki_finish`.
- Step 1, OpenWiki refresh (run `a3fd2131`): `openwiki_begin` with `mode: "update"` opened planning; right after it, `git status --porcelain -- AGENTS.md CLAUDE.md` was empty and neither file held `<!-- OPENWIKI:START -->`. OpenWiki flagged 28 stale or unresolved claims on seven pages; a sweep of every page for the plan's stale phrases found the same seven pages and nothing on the other three. Planned and refreshed: `architecture/agents-and-skills.md` (coder conditional reads, Codex fallback policy names, YAML-form rejection, hash-pinned exemption reason, shipped-marker and surface checks, the Before-you-write scope, merged bodies "moved" not "unchanged"); `architecture/source-generated-consumer-layout.md` (six budgets, the three-message recovery pin, the sidecar `hydra-config` replacement); `operations/deterministic-verification.md` (findings versus receipt content hashes, the recovery-section pin, six budgets, the new skill checks, test pointers); `operations/install-ownership-and-runtime-checks.md` (new "Never writing through a symlink" section with the exact scope and the state-sync exception, the newly-shipped-name refusal, the honest no-record wording, the unprotected-parent rule, mirror exclusions and walk errors, the stale `.agents` explanation, the corrected RAG history, the sequence renumbered with the preflight as step 6); `operations/sidecar-overlay.md` (the workflow profile's policy-pointer removal; the two test files named); `workflows/lifecycle-and-task-lanes.md` (literal MEMORY search, VERIFY without the persisted phase check, the three recoveries, the provenance and errata rules, the gate's other checks, the double blank line); `quickstart.md` (two routing rows). Every flagged claim was revised with current evidence or confirmed after a recheck, plus new claims for each new fact. OpenWiki refused evidence ranges that start or end on a blank line ("Evidence does not resolve"), so those ranges were tightened. `openwiki_finish` returned `complete`; `openwiki/.run.json` absent.
- Step 2, audit (surface list from the closeout file, which Phase E extended): scripted sweeps for every claim on the plan's list, then looser shape searches (MEMORY search wording, Copilot timing, the `.agents/skills/` hand-edit rule, overflow claims, the errata condition, phase-check timing, budgets, counts, retired paths). No live stale claim remained; the details are below. The orchestrator's user-level memory note on this plan and its index line were updated from "nothing fixed yet" to the reopen's outcome.
- Step 3: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0, no refusal; every quick Verification item PASS (`validate_targets.py` PASS, `check_runtime.py` exit 0, `validate_plan_frontmatter.py` exit 0); full `verify.py phase --format text` PASS (Ruff 0, mypy 0, pytest 5198 passed, 1 skipped).
- Review round 1 (`reviewer`, six profiles): no CRITICAL or MAJOR; gate WARN only on the open request for the full `verify.py phase` result (PASS, given in round 2). Three MINORs on wiki prose: the sidecar page said the generator removes any pointer to a full-install policy file (it rewrites two named paths and deletes one sentence; the validator catches the rest); the install page's RAG parenthetical had no cited source and an unexplained name; the full-install sequence omitted `update_devcontainer_state_remote` (pre-existing). The reviewer also found the orchestrator's user-level memory `project_context_mode_agent_matcher.md` still saying "Once that branch merges"; corrected in place (PR #55 merged).
- Second OpenWiki run (`296e6399`) for the three MINORs, on two pages: the sidecar paragraph states exactly what `SIDECAR_WORKFLOW_PATH_REPLACEMENTS` handles; the RAG parenthetical removed; the sequence gains step 12 `update_devcontainer_state_remote` (later steps renumbered), with the sequence claim revised and one new claim. `openwiki_finish` returned `complete`; no run file; no root block; every quick Verification item still PASS.
- Review round 2 (same reviewer): gate PASS, no open request; the three round-1 MINORs closed; one new MINOR: step 12 and line 133 say the devcontainer write and its symlink check happen "with `--state-remote`", but an exported `AI_STATE_REMOTE` triggers both too (the same wording is in README and `docs/runtime-checks.md`). It understates when the check runs, the safe direction, so under the user's acceptance bar it became a recorded follow-up in `docs/target-mapping.md` instead of a third OpenWiki run. Round 3 (same reviewer) confirmed the follow-up text and gate PASS.
- CLOSEOUT step 1: documentation is this phase's content (seven refreshed pages, the follow-up bullet in `docs/target-mapping.md`) and the standing final-phase audit below.
- CLOSEOUT step 2: read `.claude/skills/learn/SKILL.md`. One lesson went to `.claude/MEMORY.md` (below). Small plan set to `status: complete` with every step ticked; Phase G ticked in the big plan (the post-commit hook completes the big plan). The surviving MINOR is recorded with disposition `accepted`.

## [LEARN] Entries

- [LEARN:tooling] OpenWiki's `openwiki_submit_page` refuses a Claim whose evidence range starts or ends on a blank line (`Evidence does not resolve`), even on a plain confirm when the stored range's edge became blank; revise the Claim with the same `id` and a tightened range. Saved to `.claude/MEMORY.md`.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS        0.0s  uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' openwiki/workflows/lifecycle-and-task-lanes.md 'phase --persist` before review' 'repeat step 6 alone'
PASS        0.0s  uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' openwiki/architecture/agents-and-skills.md 'workspace Ponytail rule' 'lives unchanged'
PASS        0.0s  uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.is_dir()] + [str(p) for r in roots if r.is_dir() for p in sorted(r.rglob("*.md")) if p.is_file() and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'skills/(review-api|run-tests|refactor|pdf|caveman-compress|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing|pipeline-patterns|haystack-conditional-router|docling-haystack|ollama-chat-generator|pandas-nan-bool-coercion|networkx-igraph-graphml-interop|pyvis-xss-testing|csv-driven-integration-tests|deploy-service|context-manager-testing|test-helper-public-api)/|lost its own' openwiki
PASS        0.0s  grep -q -F 'findings report content_hash is stale' openwiki/workflows/lifecycle-and-task-lanes.md
PASS        0.0s  grep -q -F 'Refusing to write through symlinks:' openwiki/operations/install-ownership-and-runtime-checks.md
PASS        0.0s  test ! -e openwiki/.run.json
PASS        0.0s  test "$(grep -c -F '<!-- OPENWIKI:START -->' AGENTS.md)" = "0"
PASS        0.0s  test "$(grep -c -F '<!-- OPENWIKI:START -->' CLAUDE.md)" = "0"
PASS       47.0s  uv run python scripts/validate_targets.py
PASS        0.7s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      350.0s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-14_phase-G-knowledge-refresh.json` (1 MINOR, disposition `accepted`; gate PASS; six profiles; round 1 WARN on the open verify request with three MINORs, fixed through a second OpenWiki run; rounds 2 and 3 PASS).
- Phase receipt: `verify.py phase --persist` PASS (Ruff, mypy, pytest, freshness, provenance, generation); the last full run before it reported pytest 5198 passed, 1 skipped.
- optional 1: PASS — the reviewer read every refreshed page's prose, not only its flagged claims, against the code and tests it cites, in three rounds. It found three prose mismatches (sidecar pointer scope, an unexplained RAG parenthetical, the missing devcontainer step), all fixed through a second OpenWiki run. One wording nuance (`--state-remote` or `AI_STATE_REMOTE`) remains as a recorded follow-up.

## Stale-claims surfaces checked

- `CLAUDE.md`, `AGENTS.md` (authoring and generated): current; Phase E gave both the literal MEMORY search and removed "phase before REVIEW"; no stale claim found.
- `README.md`: current; Phases E and F corrected the receipt-recovery pointer, the Codex fallback wording, the refusal list (one list, the symlink and newly-shipped-name refusals, the record definition), the Copilot row, and the one allowed `.agents/skills/` deletion; no "only refusal", "never shipped", or RAG incident remains.
- `.github/` and `SECURITY.md`: no claim this plan changed.
- Undated `docs/` (`architecture.md`, `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, and the rest): current after Phases E and F (validation contract with the two new checks, the refusal section and record definition, six budgets, Codex `.agents/skills/` wording, the Antigravity pointer note, the recorded follow-ups including the 37 `[[skills.config]]` entries and the state-sync gap). No remaining "16 KiB" claim that names only the workflow core.
- `shared/policies/`: current; the docs-only shortcut, the narrow errata condition, the three-reminder session-log lines, "(see root guidance)", and the consumer-missing validator paths were fixed in Phase E; no "phase before review" or two-message recovery remains.
- `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, `shared/sidecar/`: current; learn's consumer rows, the cap, the refresh skill's no-record check, retired-skill table, second-clone recovery, and symlink refusal (Phase F); the coder's conditional reads and `hydra-config`'s policy pointer (Phase E). No `skills/<retired-name>/` path.
- State READMEs (`.claude/plans`, `explorations`, `session_logs`, `quality_reports`, and their `shared/` seeds): no claim this plan changed.
- `.claude/instructions/project-context.instructions.md`: current; Phase E corrected the Context Mode status (PR #55 merged, `dev` pins `2.1.8`); no "lost its own" or "55 skills".
- `openwiki/`: seven pages refreshed in Step 1 through OpenWiki's tools; the three unrefreshed pages (`hooks-and-guardrails`, `git-backed-ai-state-sync`, `context-mode-dispatcher`) hold no statement Phases E to G changed.
- Active plans: the big plan `.claude/plans/skills-and-instructions-trim.md` (reopen section, Decisions 8 to 12, done criteria, requirement rows) and the three reopen small plans match the outcomes; Phase F's one deviation (the blanket substitution and `.gitignore` check) is within Decision 8 and recorded as a follow-up.
- `.claude/MEMORY.md`: Phase E and F lessons were added; the Phase D audit lesson was corrected in place (the closeout file's audit list now names project context, `.github/`, and `openwiki/`). No entry repeats a corrected claim.
- User-level memory (orchestrator's own notes): `project_skills_trim.md` and its index line updated to the reopen's outcome; the earlier corrections (niche skills, closeout order, PR #55) stand.
- Dated records left unchanged: archived plans, explorations, quality reports (including the 2026-11-14 review reports), `docs/evidence/`, `docs/2026-*`, and closed session logs.

## Open Questions / Next Steps
