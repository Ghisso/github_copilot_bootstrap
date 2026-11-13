---
name: 2026-11-12_phase-D-knowledge-refresh
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 4
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: complete
closeout_session_log: .claude/session_logs/2026-11-14_skills-trim-phase-D.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-12_phase-D-knowledge-refresh

## Scope

This is the final knowledge-refresh phase that the Knowledge-Refresh Final Phase rule requires (now in `.claude/instructions/plan-lifecycle.instructions.md`). It does four things:
- refreshes the OpenWiki pages that describe skills, installer ownership, and the lifecycle, through OpenWiki's own tools;
- runs the standing final-phase documentation, memory, and LEARN audit across every live-advice surface;
- regenerates `dist/` and refreshes this repository, so that any audit fix to `shared/` reaches the generated and installed copies;
- records the audit under `## Stale-claims surfaces checked`.

Covers REQ-010. The phase owns the files its steps list; a file may be revisited after a review finding.

Risk notes:
- OpenWiki can time out right after the host boots. Reconnect with `/mcp` and retry.
- A provider failure blocks the phase. It is reported and retried, never skipped.

## Steps

- [x] **1. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator, in the main session, where the earlier knowledge-refresh phases ran it. Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`. Plan these pages plus every page OpenWiki flags:
    - `architecture/agents-and-skills.md`: 37 skills, the merges, the cap, project skills;
    - `operations/install-ownership-and-runtime-checks.md`: the marker, the refusals, the shipped-before record, the mirror;
    - `workflows/lifecycle-and-task-lanes.md` and `operations/deterministic-verification.md`: the closeout and plan-lifecycle files;
    - `architecture/source-generated-consumer-layout.md`: the instruction files;
    - `operations/sidecar-overlay.md`: the workflow-profile skills.
  - Right after `openwiki_begin`, run `git status --porcelain -- AGENTS.md CLAUDE.md` (the skill's restore check).
  - Reconcile every flagged claim, and require `openwiki_finish` to return `complete`.
  - Never hand-edit a generated page, a `.claims` file, or the root snippet.

- [x] **2. Audit live advice for stale claims.**
  - Owner: orchestrator; `documenter` for fixes in `README.md`, `docs/`, and `shared/`. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Surfaces:
    - `CLAUDE.md`, `AGENTS.md`, `README.md`;
    - undated `docs/` pages;
    - `shared/policies/`, `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`;
    - the state READMEs;
    - this repository's `.claude/` overlay and project context;
    - `.claude/MEMORY.md`.
  - Claims to find:
    - names of the 20 retired skills;
    - "55 skills" or "25 public skills";
    - "background skills are hidden";
    - "loaded into every session";
    - "read `.claude/MEMORY.md`" as a full read;
    - the CLOSEOUT sequence placed in `workflow.instructions.md`;
    - the Completion Protocol;
    - "Never checkpoint after the receipts are persisted";
    - the July 2026 "keep niche skills" decision presented as current;
    - Codex skills "sourced from the shared .claude basis";
    - a refresh "deletes every other file" with no project-skill exception or refusal.
  - Correct each live claim in place. MEMORY entries are corrected, not appended to. A fix whose statement a generated page repeats goes through another OpenWiki `update`.
  - Leave dated records unchanged: archived plans, explorations, `docs/evidence/`, and closed session logs.
  - The orchestrator also updates its user-level memory notes about this work.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked`.

- [x] **3. Regenerate and refresh this repository.**
  - Owner: orchestrator. This always runs, even when Step 2 changed nothing in `shared/`. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [x] **4. Review.**
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
uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.is_dir()] + [str(p) for r in roots if r.is_dir() for p in sorted(r.rglob("*.md")) if p.is_file() and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'skills/(review-api|run-tests|refactor|pdf|caveman-compress|dataclass-classvar-constant|domain-type-placement|graph-schema-compat-migration|extraction-metadata-sourcing|pipeline-patterns|haystack-conditional-router|docling-haystack|ollama-chat-generator|pandas-nan-bool-coercion|networkx-igraph-graphml-interop|pyvis-xss-testing|csv-driven-integration-tests|deploy-service|context-manager-testing|test-helper-public-api)/|(?i:there are 55)' openwiki
grep -q -F 'data-and-graph-pitfalls' openwiki/architecture/agents-and-skills.md
grep -q -E '\b37\b' openwiki/architecture/agents-and-skills.md
grep -q -F '.project-skill' openwiki/operations/install-ownership-and-runtime-checks.md
grep -q -F 'closeout.instructions.md' openwiki/workflows/lifecycle-and-task-lanes.md
uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.exists()] + [str(p) for r in roots if r.exists() for p in ([r] if r.is_file() else sorted(r.rglob("*"))) if p.is_file() and "__pycache__" not in p.parts and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'loaded into every session|Never checkpoint after the receipts are persisted' shared README.md docs/architecture.md docs/target-mapping.md
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

- [x] Step 1: documentation updated, or skipped as pure-internal with a reason
- [x] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

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
