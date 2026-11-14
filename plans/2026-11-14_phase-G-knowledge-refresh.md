---
name: 2026-11-14_phase-G-knowledge-refresh
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 7
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-14_phase-G-knowledge-refresh

## Scope

This is the final knowledge-refresh phase that the reopened big plan needs, per the Knowledge-Refresh Final Phase rule in `.claude/instructions/plan-lifecycle.instructions.md`. It does four things:
- refreshes the OpenWiki pages that carry finding R23 or describe what Phases E and F changed, through OpenWiki's own tools;
- runs the standing final-phase documentation, memory, and LEARN audit with the surface list Phase E extended;
- regenerates `dist/` and refreshes this repository, so that any audit fix to `shared/` reaches the generated and installed copies;
- records the audit under `## Stale-claims surfaces checked`.

Covers REQ-013 in the big plan. The phase owns the files its steps list; a file may be revisited after a review finding.

Risk notes:
- OpenWiki can time out right after the host boots. Reconnect with `/mcp` and retry.
- A provider failure blocks the phase. It is reported and retried, never skipped.

## Steps

- [ ] **1. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator, in the main session. Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`. Plan these pages plus every page OpenWiki flags:
    - `workflows/lifecycle-and-task-lanes.md`: the persisted phase check runs at CLOSEOUT step 4, not before review; the corrected stale-receipt recoveries; "the plan templates point here"; the double blank line;
    - `architecture/agents-and-skills.md`: drop the removed workspace Ponytail rule; say the merged bodies kept their text apart from frontmatter and the CSV pair's link renames; the restored trigger phrases if the page quotes descriptions;
    - `operations/install-ownership-and-runtime-checks.md`: the symlink refusal, the newly-shipped-name refusal, the reworded no-record refusal, the mirror's exclusions and walk errors, the stale `.agents` explanation;
    - `operations/deterministic-verification.md`: the new validator checks (fallback policy names, YAML forms, budgets, stray marker, section-scoped recovery pin);
    - `operations/sidecar-overlay.md`: name the files of the two project-skill sidecar tests.
  - Right after `openwiki_begin`, run `git status --porcelain -- AGENTS.md CLAUDE.md` (the skill's restore check).
  - Reconcile every flagged claim, and require `openwiki_finish` to return `complete`.
  - Never hand-edit a generated page, a `.claims` file, or the root snippet.

- [ ] **2. Audit live advice for stale claims.**
  - Owner: orchestrator; `documenter` for fixes in `README.md`, `docs/`, and `shared/`. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Surfaces: the standing final-phase audit list in `.claude/instructions/closeout.instructions.md`, including the project context, `.github/`, and `openwiki/` that Phase E added, and the orchestrator's user-level memory notes.
  - Claims to find:
    - the docs-only recovery that skips findings ("repeat step 6 only", "findings do not cover documentation");
    - "`verify.py phase` before review";
    - the RAG incident stated as fact ("lost its own");
    - "never shipped" for the no-record refusal;
    - "only refusal" about existing content;
    - "55" `[[skills.config]]` entries;
    - consumer guidance to edit a shipped skill;
    - Copilot seeing project skills only after a refresh;
    - "never edit `.agents/skills/` by hand" without the stale-folder exception;
    - the Context Mode 2.x migration described as unmerged;
    - the skill-listing overflow described as fixed for every model.
  - Correct each live claim in place. MEMORY entries are corrected, not appended to. A fix whose statement a generated page repeats goes through another OpenWiki `update`.
  - Leave dated records unchanged: archived plans, explorations, `docs/evidence/`, quality reports, and closed session logs.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked`.

- [ ] **3. Regenerate and refresh this repository.**
  - Owner: orchestrator. This always runs, even when Step 2 changed nothing in `shared/`. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [ ] **4. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - the refreshed pages match the code they cite;
    - every audit fix that a page repeats went through another OpenWiki `update`;
    - the generated and installed copies match `shared/`;
    - no root adapter carries an OpenWiki block, and no `openwiki/.run.json` remains.

## Verification

<!-- Every non-comment line in a `bash`/`sh` block below is a required item:
     a shell command `verify closeout` runs itself, from the repository
     root, and that must exit 0. Never list `verify.py closeout` itself.
     Anything a script cannot run — an interactive probe, a host session, a
     manual inspection — belongs under `## Optional Verification` instead.
     See the Verification Evidence Contract in
     `.claude/instructions/workflow.instructions.md`. -->

```bash
uv run python scripts/generate_targets.py --all
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' openwiki/workflows/lifecycle-and-task-lanes.md 'phase --persist` before review' 'repeat step 6 alone'
uv run python -I -c 'import pathlib, sys; text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"); hits = [s for s in sys.argv[2:] if s in text]; sys.exit("stale text: " + "; ".join(hits) if hits else 0)' openwiki/architecture/agents-and-skills.md 'workspace Ponytail rule'
uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.is_dir()] + [str(p) for r in roots if r.is_dir() for p in sorted(r.rglob("*.md")) if p.is_file() and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'skills/(review-api|run-tests|refactor|pdf|caveman-compress|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing|pipeline-patterns|haystack-conditional-router|docling-haystack|ollama-chat-generator|pandas-nan-bool-coercion|networkx-igraph-graphml-interop|pyvis-xss-testing|csv-driven-integration-tests|deploy-service|context-manager-testing|test-helper-public-api)/|lost its own' openwiki
grep -q -F 'content_hash' openwiki/workflows/lifecycle-and-task-lanes.md
grep -q -F '.project-skill' openwiki/operations/install-ownership-and-runtime-checks.md
test ! -e openwiki/.run.json
test "$(grep -c -F '<!-- OPENWIKI:START -->' AGENTS.md)" = "0"
test "$(grep -c -F '<!-- OPENWIKI:START -->' CLAUDE.md)" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Read each refreshed page's prose against the code it cites, not only its flagged claims, and record any mismatch.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [ ] Step 1: documentation updated, or skipped as pure-internal with a reason
- [ ] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
