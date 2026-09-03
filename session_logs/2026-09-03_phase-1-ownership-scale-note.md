# Session: Ownership Scale Note

**Date:** 2026-09-03
**Plan:** `.claude/plans/2026-09-03_phase-1-ownership-scale-note.md`
**Status:** COMPLETED

## Goal

Close the MAJOR finding against merged commit `4a3c0c2`: the root-owned-file
guidance understated scale, so an operator would fix the visible files and
remain unaware of the latent ones.

## Work Log

- **08:40** - The `reviewer` agent type became spawnable again after the user
  restarted VS Code, so commit `4a3c0c2` finally got the independent review it
  had shipped without. The review found one MAJOR.
- **08:45** - The finding was fair and pointed: the note described an isolated
  file with a single-path `chown`, while the investigation behind that very
  documentation had found 156 root-owned Python files against the 2 visible.
  The review noted that the session's own recorded lesson —
  "[LEARN:diagnostics] Report the scale of a problem, not the first instance"
  — was reproduced rather than applied.
- **08:50** - Measured the enumeration options before documenting one. My
  original `find . -user root` suggestion is the wrong tool: in the affected
  project it returned **3,530** hits, inflated by untracked `__pycache__`,
  vendored `lib/` assets, and data caches no gate reads, and it errored with
  `bfs: error: ./data/undl_cache: Permission denied` because it walks the tree.
- **08:55** - Confirmed the user's recursive `chown` had already cleared the
  real problem: all three consumer projects and this repository now report
  zero tracked files not owned by the invoking user.
- **09:10** - Review of the fix: PASS, one MINOR. It reproduced a genuine
  filename edge case, and separately surfaced a pre-existing inaccuracy in the
  same bullet.

## The pre-existing inaccuracy, which mattered more than the MINOR

Commit `4a3c0c2` claimed `ruff format`/`ruff format --check` "fails with
`Permission denied` rather than reporting a formatting diff". Verified against
real Ruff on a `chmod 444` tracked file:

```text
ruff format --check .   -> "Would reformat: unwritable.py"  exit 0
ruff format .           -> "error: Failed to write unwritable.py: Permission denied (os error 13)"
```

So `--check`, which is what `VFY-RUFF-001` actually runs, only reads and
reports an ordinary formatting diff. The permission error appears when the
operator runs `ruff format` to *clear* that diff. The original wording
conflated the gate's check with the operator's fix, and I had repeated that
conflation when first explaining it to the user.

Both notes now say plainly that a root-owned file breaks the fix, not the
check, so the symptom is a formatting failure that cannot be cleared.

## Design decisions

- **No hard-coded incident count.** The 156 was specific to one project and is
  already zero after the user's `chown`, so quoting it would have become a
  stale claim of exactly the kind this work exists to remove. The guidance
  states the mechanism — an already-formatted file is never rewritten, so it
  stays silent — and gives a command that measures the reader's own tree.
- **A NUL-delimited loop, not `stat | awk`.** The review reproduced the first
  form printing a spurious `name.py` fragment for a tracked file named
  `weird<LF>name.py`, because `stat`'s plain-text output interpolates the
  filename and `awk` then reads it as two records. This repository already
  holds a `newline_filename` regression test, so NUL-safe path handling is its
  established standard rather than a hypothetical. Verified the documented loop
  against filenames containing both a space and a newline: each is reported as
  a single correct entry, with no fragment.
- **One authoritative copy of the command.** It now lives only in
  `docs/runtime-checks.md`; the README states the effect and links there.
  Duplicating a subtle shell pipeline in two places is how one copy silently
  drifts from the other.
- **The recursive `chown` caution is kept proportionate.** It names the blast
  radius — every file beneath the path, including anything deliberately owned
  by another user — and recommends the enumerated list as the default, without
  a blanket prohibition.

## [LEARN] Entries

- [LEARN:diagnostics] A gate that only reads and a fix that writes fail
  differently, and conflating them misdirects the operator. `ruff format
  --check` reports a normal diff on a file it could never write; only the
  write-mode fix raises `Permission denied`. State which step the permission
  actually blocks.
- [LEARN:documentation] Do not quote an incident's file count in durable
  guidance. The number is specific to one tree, goes stale the moment it is
  fixed, and the reader needs a command that measures their own situation
  instead.
- [LEARN:tooling] Prefer `git ls-files -z` piped into a NUL-delimited loop
  over `find` for enumerating tracked files by ownership. `find` walks the
  tree, so it stops on an unreadable directory and counts untracked caches and
  vendored assets no gate inspects — 3,530 hits versus the tracked set that
  actually matters.
- [LEARN:tooling] `-z`/`-0` protect the `git ls-files` to `xargs` boundary but
  not a later text pipeline: `stat -c '%U %n'` interpolates the filename, so
  `awk` reading line-by-line splits a newline-bearing path into two records and
  emits a fragment matching no real file. Keep each path bound to its own
  lookup inside one loop iteration.
- [LEARN:review] Publishing without an independent pass cost a real finding
  here. Commit `4a3c0c2` shipped while the `reviewer` type was unavailable; the
  first review after it became spawnable again found a MAJOR that my own
  verification had missed, in prose I had written and checked myself.

## Stale-claims surfaces checked

Final phase of this big plan, so the standing audit applies. This phase changed
documentation only and corrected one false claim it inherited.

| Surface | Outcome |
|---|---|
| `docs/runtime-checks.md` | Corrected — scale, enumeration command, recursive-`chown` caution, and the false `--check` permission claim |
| `README.md` | Corrected — same effect stated briefly, command de-duplicated to a link |
| Ruff behavior on an unwritable tracked file | Verified directly against real Ruff rather than asserted; `--check` reads, write mode fails |
| The documented enumeration command | Run verbatim against space- and newline-bearing filenames, and confirmed read-only against `git status` |
| `.claude/MEMORY.md` | Checked — no ownership or formatting claim to update |
| Other `docs/*.md`, `shared/policies/`, `shared/skills/`, `shared/templates/` | Checked — none describe root-owned-file recovery; nothing to update |

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1242 passed

uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 25 source files

uv run ruff check shared scripts tests
# All checks passed!

uv run ruff format --check shared scripts tests
# 25 files already formatted

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py phase --format text
# phase: PASS
```

Diff is two files, additive prose plus one fenced command block. No code,
config, check id, or threshold touched.

## Open Questions / Next Steps

- The `reviewer` agent type was unspawnable for part of the previous session
  and recovered on restart. Cause appears session-cumulative rather than
  configuration; recorded in case it recurs.
- No compatibility allowance exists in this plan, so none carries a removal
  condition.
- The user owns the merge decision; no PR was opened.
