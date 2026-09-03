---
name: 2026-09-03_phase-1-ownership-scale-note
type: small-plan
parent_plan: upgrade-note-ownership-scale
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-09-03_phase-1-ownership-scale-note.md
---

# Phase 1 — Ownership Scale Note

**Parent:** `upgrade-note-ownership-scale`
**Phase:** 1 of 1
**Primary objective:** close the MAJOR finding by stating the true scale of
root-owned tracked files and how to enumerate them.

## 1. The finding

Reviewer, against merged commit `4a3c0c2`:

> The note reads "If a tracked file is owned by `root`... fix ownership first:
> `sudo chown "$(id -un):$(id -gn)" <path>`," implying an isolated,
> single-file event. The investigation that produced this exact documentation
> found **156** root-owned Python files in one project, versus the 2 initially
> visible. An operator who fixes the couple of currently-failing files and
> refreshes will succeed today, but remains unaware that dozens or hundreds of
> other root-owned files may be silently latent (correctly formatted for now)
> and will surface unpredictably, one `Permission denied` at a time.

Locations: `README.md:275-278` and `docs/runtime-checks.md:391-394`.

## 2. What to change

In both places, add that ownership can affect many more tracked files than the
ones currently failing, and give a read-only way to see the extent at once so
the reader is not left discovering it incrementally.

Suggested enumeration shape, to be verified before documenting:

```bash
find . -user root -not -path './.git/*' -not -path './.venv/*'
```

Consider narrowing to tracked files, since an untracked root-owned artifact
(a `__pycache__` directory, a vendored asset) is not what blocks the gate and
including it inflates the count in a way that misleads differently.

If a recursive ownership fix is offered, caution it. A recursive change across
a source tree is not self-evidently safe.

## 3. Non-goals

- Do not change any gate, check, threshold, or scope.
- Do not restructure the surrounding sections or add a new heading. One clause
  plus a command in each location.
- Do not restate the incident; the operator needs the fact and the command.
- Do not patch consumer repositories.
- Add no compatibility allowance.

## 4. Verification

The enumeration command must be run and confirmed to work, and confirmed
read-only. Then:

```
uv run python scripts/generate_targets.py --all
uv run python scripts/update_consumers.py --allow-self --local-only .
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## 5. Acceptance criteria

- [ ] both locations state that scale can exceed the currently-failing files.
- [ ] a read-only enumeration command is given and verified to run.
- [ ] any recursive ownership guidance carries a caution.
- [ ] no gate behavior changed; changes remain additive prose.
- [ ] no new stale claim introduced.
- [ ] full tests and validation pass with no regeneration drift.

## 6. Completion evidence

Updated plan status, deterministic verification PASS, a findings report with
zero surviving findings or explicit dispositions, and the closeout session log
including `## Stale-claims surfaces checked` since this is the final phase.
