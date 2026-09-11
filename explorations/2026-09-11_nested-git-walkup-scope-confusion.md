# Brief: nested-state readers resolve to the outer repository when `.claude` has no `.git`

**Date:** 2026-09-11
**Author:** prior agent session (Claude Opus 5), during big plan `2026-09-11_outer-repo-auto-push`
**Status:** OPEN — not fixed. Wants independent confirmation and a severity ruling.
**Code state:** branch `dev` at merge commit `2258f18` (PR #35), which contains `f92fe22`.
`origin/main` does not contain it.
**Authoring source under review:** `shared/scripts/verify.py`. Generated mirrors
(`.claude/scripts/verify.py`, `dist/multi-agent/.claude/scripts/verify.py`) are
byte-identical copies; do not review or edit those.

## What I want from you

I am asking for confirmation or refutation, not agreement. Specifically:

1. **Confirm or refute the mechanism** in "Confirmed behavior" below. Re-run the
   reproductions; do not take my word for the outputs.
2. **Rule on severity.** My assessment is "real correctness defect, low severity,
   no known exploit". I may be wrong in either direction. I am most interested in
   whether you can construct a *fail-open* path I missed — one where a push or
   commit gate PASSES when it should FAIL.
3. **Challenge my reachability argument.** I argue the vulnerable state is
   transient and self-healing. If it is actually reachable in a steady state, the
   severity rises sharply.
4. **Rule on the proposed fix**, including whether gating the readers would break
   the migration path the state is part of.
5. **Tell me if the fix is worth doing at all.** "Leave it, document it" is an
   acceptable answer if the reasoning holds.

Please state explicitly which of my claims you verified, which you could not, and
which you believe are wrong.

## Background: why this code exists

`shared/scripts/verify.py` implements the lifecycle verification gates. Two of its
concepts matter here.

`.claude/` is normally its **own nested Git repository**, on a branch named
`ai-state`, separate from the outer project repository. It holds mutable AI state:
plans, session logs, quality reports, memory. `shared/hooks/scripts/state-sync.sh`
manages it.

`control_plane_provenance` (`shared/scripts/verify.py:899`) binds a verification
receipt to the governing runtime and the active plans, so a receipt cannot be
reused after the things it certifies change. Its fields:

| Field | Source |
| --- | --- |
| `nested_head` | `nested_git_head(root)` |
| `runtime_fingerprint` | filesystem hash of nested runtime paths + root adapters |
| `tracked_state_fingerprint` | `nested_tracked_state_fingerprint(root, active_plan_paths)` |
| `big_plan_digest` | `digest_file(<big plan>)` — working-tree bytes |
| `small_plan_digest` | `digest_file(<small plan>)` — working-tree bytes |

`nested_git_head` (`shared/scripts/verify.py:802`) is implemented as:

```python
def nested_git_head(root: Path) -> str:
    """Return the nested AI-state HEAD only when it is available."""
    nested = root / ".claude"
    if not nested.is_dir() or nested.is_symlink():
        return ""
    return git_output(["-C", str(nested), "rev-parse", "--verify", "HEAD"], root)
```

The guard checks that `.claude` is a real directory. It does **not** check that
`.claude` is a Git repository.

## The state in question

A consumer whose `.claude/` directory **has content but no `.claude/.git`**. The
outer repository tracks `.claude/` as ordinary files, or ignores it.

`docs/architecture.md` documents this as a named migration state
(`migrate-from-hf`). Search that file for "no `.claude/.git` yet".

## Confirmed behavior

All of the following I ran against the merged `shared/scripts/verify.py`, loaded
via `runpy.run_path`, in throwaway temp directories. Reproductions are in the
appendix. **Re-run them.**

### 1. `nested_git_head` returns the OUTER repository's HEAD

Git walks *up* the directory tree from `.claude` and finds the outer repository,
so `rev-parse --verify HEAD` succeeds and returns a real SHA.

```
.claude/.git exists            : False
nested_git_head(root)          : e80f772cfef8b31929618474626cac01348b7690
outer repo HEAD                : e80f772cfef8b31929618474626cac01348b7690
identical                      : True
```

Consequence: any caller testing `if not nested_head` to mean "no nested state"
does not fire. That was a real CRITICAL defect in this same big plan: the new
`unpublishable_closeout_reason` precondition used exactly that test and therefore
refused **every** closeout for such a consumer. It was fixed in `f92fe22` by
adding `nested_state_repository` (`shared/scripts/verify.py:772`), which checks
for `.claude/.git` directly. That fix is in place and is not what this brief is
about. This brief is about the **other** callers, which were left unchanged and
still use the walk-up primitives.

### 2. The nested file readers return OUTER repository CONTENT

This is the part I consider most serious, and the part I under-described when I
first raised it. It is not merely a wrong SHA — it reads the wrong file's bytes.

Fixture: `.claude/plans/big.md` contains `NESTED plan bytes`. The outer repo has a
top-level `plans/big.md` containing `OUTER plan bytes`. No `.claude/.git`.

```
indexed_nested_file(root, 'plans/big.md')        -> b'OUTER plan bytes\n'
nested_revision_file(root, head, 'plans/big.md') -> b'OUTER plan bytes\n'
```

Both returned outer-repository content while a different nested file of that
relative path existed on disk. Relevant definitions:
`indexed_nested_file` at `shared/scripts/verify.py:990`, `nested_revision_file` at
`:1012`. Both guard `nested.is_dir()` and path safety; neither checks that
`.claude` is a repository.

Requirement for this: the outer repository must contain the same relative path at
its root (`plans/…`, `session_logs/…`, `quality_reports/…`).

### 3. `git status --porcelain` path spellings collide exactly

This is the mechanism that makes the dirty-state signal ambiguous.
`--porcelain` reports paths relative to the **repository root**, not the working
directory. Run from inside a `.git`-less `.claude`, the repository root is the
outer root. Measured, with `is_relevant_nested_path(path, {"plans/big.md"})`:

| Edited file | Reported by status | `is_relevant_nested_path` |
| --- | --- | --- |
| `.claude/plans/big.md` | `.claude/plans/big.md` | True |
| outer `plans/big.md` | `plans/big.md` | True |

The outer file's repo-root-relative spelling is byte-identical to the
nested-relative spelling the code expects. So an edit to the outer repo's
top-level `plans/<slug>.md` is indistinguishable from an edit to
`.claude/plans/<slug>.md`.

Affected: `relevant_nested_status_changes` (`:1035`) and
`nested_tracked_state_fingerprint` (`:810`), which both run
`git status --porcelain=v1 -z --untracked-files=all` inside `.claude`.

Measured on `nested_tracked_state_fingerprint` for the same fixture: it changed
when the nested plan was edited AND when the outer plan was edited. So it is
sensitive to outer state it should not bind at all.

One sub-finding that partially mitigates: `git ls-files --stage` run from inside
`.claude` **does** limit to the current directory subtree and reports
cwd-relative paths, so the index half of that fingerprint reads genuinely nested
files. Only the status half is confused. I would like this confirmed — I am
inferring it from observed output, and I am not fully certain of `ls-files`
path-scoping semantics across Git versions.

### 4. Full list of affected call sites

Five, none of which were changed by `f92fe22`:

| Line | Site | What goes wrong |
| --- | --- | --- |
| `:920` | `control_plane_provenance` | records outer HEAD as `nested_head` |
| `:810` | `nested_tracked_state_fingerprint` | status half binds outer state |
| `:1035` | `relevant_nested_status_changes` | outer edits look like nested edits |
| `:990`, `:1012` | `indexed_nested_file`, `nested_revision_file` | return outer file content |
| `:1340` | `has_only_checkpointed_terminal_big_plan_change` | `current_head` is the outer HEAD, so its `git diff recorded_head current_head` diffs outer commits |

## My severity assessment — challenge this

**I assess this as a real correctness defect, low severity, with no exploit I can
construct.** Three reasons, each of which I want tested.

### Reason 1: the state is transient and self-healing

`cmd_checkpoint` in `shared/hooks/scripts/state-sync.sh:337` begins:

```bash
cmd_checkpoint() {
  if [[ ! -d "$CLAUDE_DIR/.git" ]]; then
    init_nested_repo
    restore_root_adapters
  fi
  commit_local_state
}
```

So any checkpoint initializes the nested repository. The `post-commit` git hook
runs state-sync after every outer commit. `install_bootstrap.py` calls
`state-sync.sh setup`. So the `.git`-less state ends at the first commit, install,
or checkpoint.

**What I could not verify:** `install_bootstrap.py` calls into state-sync with
`check=False`, so a partial or failed setup could leave a consumer in this state
for longer than intended. I did not build that failure case. If you can show the
state persists across a normal working session, my severity assessment is wrong.

### Reason 2: the realistic paths fail closed, not open

For the terminal push gate, `control_plane_provenance_matches` (`:971`) is tried
first, then `terminal_control_plane_provenance_matches` (`:1361`). For a
`.git`-less consumer whose big plan was rewritten by `post-commit`:

- strict match fails, because `big_plan_digest` is computed from the real nested
  working-tree file via `digest_file` and that file changed;
- `has_only_terminal_big_plan_change` (`:1263`) requires
  `relevant_nested_status_changes(...) == [(" M", [relative])]`;
- `has_only_checkpointed_terminal_big_plan_change` (`:1301`) requires
  `nested_revision_file(root, recorded_head, relative)` to hash to the recorded
  digest, where `recorded_head` is an outer SHA.

The observed outcome is a refused push (`closeout receipt governing control-plane
provenance is stale`), which is the safe direction. I confirmed the refusal
direction on the real repository earlier in this big plan, though for a *different*
root cause (a dirty big plan, since fixed).

**The one theoretical substitution path I see**, and could not make fire: an outer
top-level `plans/<slug>.md` whose bytes hash exactly to the recorded
`big_plan_digest` would be accepted as `source` by `plan_bytes_matching_digest`
(`:787`). Combined with the status-spelling collision producing exactly
`[(" M", ["plans/<slug>.md"])]` from an outer edit, `has_only_terminal_big_plan_change`
could in principle be satisfied from outer state. I did not build this. It also
requires `plan.read_bytes()` — the genuinely nested file — to equal
`terminal_big_plan_bytes(source, phase)`, which constrains both files at once.

**Please try to build that.** If it fires, this is not low severity.

### Reason 3: it grants nothing the actor already lacked

`big_plan_digest` is recorded from the real nested file. For outer bytes to be
accepted they must hash identically to the nested plan, which means the actor
already controls the plan bytes. An actor who can write `plans/<slug>.md` in the
outer repo and `.claude/plans/<slug>.md` could simply write the plan directly.

**Where I think this argument is weakest:** it assumes the same actor controls
both trees. A case where the outer repo's top-level `plans/` is populated by
something other than the agent — vendored content, a submodule, a generated
directory, another team's files — breaks the assumption. I have not looked for
such a case.

## Proposed fix, for your ruling

Gate the nested readers on the predicate this big plan already added,
`nested_state_repository` (`shared/scripts/verify.py:772`), so they report absence
rather than outer content:

- `indexed_nested_file` (`:990`) and `nested_revision_file` (`:1012`) return `None`.
- `nested_tracked_state_fingerprint` (`:810`) returns `""`, which its callers
  already treat as unavailable.
- `relevant_nested_status_changes` (`:1035`) returns `None`, which its signature
  already permits (`list[...] | None`) and callers already handle.
- `nested_git_head` (`:802`) returns `""`.

Roughly a dozen lines plus one test per reader, each building a real `.claude`
directory with plan content and no `git init` — not the absent-`.claude` shortcut,
which is what the pre-existing test did and why the original defect survived
review the first time.

**Open questions I could not settle:**

1. Changing `nested_git_head` changes what `control_plane_provenance` records for
   such consumers: `nested_head` becomes `""`. `has_control_plane_provenance`
   (`:938`) requires `nested_head` to match `[0-9a-f]{40,64}`, so provenance would
   become *unavailable* rather than merely wrong. Is that the correct outcome, or
   does it break the migration path the state exists to serve? I lean toward
   correct — provenance genuinely is unavailable — but it is a behavior change for
   a documented configuration and I did not trace every consumer of
   `has_control_plane_provenance`.
2. Does this warrant a `CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION` bump? I believe
   not, since no field changes shape, but receipts recorded by the old code for
   such consumers would hold an outer SHA in `nested_head`.
3. Should the fix be scoped to the readers only, leaving `nested_git_head` alone,
   as the smaller and safer change?

## Provenance of this brief — what to distrust

- I found this while fixing an adjacent CRITICAL defect in the same function
  family, so I may be pattern-matching the new finding onto the shape of the old
  one.
- Everything in "Confirmed behavior" is from my own throwaway reproductions
  against the merged source. I have not seen it occur on a real consumer
  repository.
- Both severity-reducing arguments 1 and 3 are reasoning, not measurement. Only
  argument 2's observed refusal direction is measured, and for a different cause.
- A reviewer in this session independently reproduced finding 1 and agreed the
  broader walk-up was out of scope for that phase. It did **not** review findings
  2, 3, or 4, which I established afterward.

## Appendix: reproductions

Each loads the merged verifier and builds a throwaway fixture. Run from the
repository root with `uv run python <file>`.

### A. Walk-up and wrong-file reads (findings 1 and 2)

```python
import pathlib, runpy, subprocess, sys, tempfile
REPO = pathlib.Path("/home/ghisso/work/github_copilot_bootstrap")
sys.argv = ["verify.py"]
mod = runpy.run_path(str(REPO / "shared" / "scripts" / "verify.py"))

with tempfile.TemporaryDirectory() as tmp:
    root = pathlib.Path(tmp) / "consumer"
    (root / ".claude" / "plans").mkdir(parents=True)
    (root / ".claude" / "plans" / "big.md").write_text("NESTED plan bytes\n")
    (root / "plans").mkdir()
    (root / "plans" / "big.md").write_text("OUTER plan bytes\n")
    for args in (
        ("git", "init", "-q", "-b", "dev"),
        ("git", "config", "user.email", "a@example.com"),
        ("git", "config", "user.name", "A"),
        ("git", "add", "-A"),
        ("git", "commit", "-qm", "outer with a top-level plans/ dir"),
    ):
        subprocess.run(args, cwd=root, check=True, capture_output=True)

    head = mod["nested_git_head"](root)
    print("nested_state_repository:", mod["nested_state_repository"](root))
    print("nested_git_head        :", head)
    print("outer HEAD             :", subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=root, text=True,
        capture_output=True, check=True).stdout.strip())
    print("indexed_nested_file    :", mod["indexed_nested_file"](root, "plans/big.md"))
    print("nested_revision_file   :", mod["nested_revision_file"](root, head, "plans/big.md"))
```

Expected: `nested_state_repository` False, `nested_git_head` equal to the outer
HEAD, both readers returning `b'OUTER plan bytes\n'`.

### B. Status path collision (finding 3)

Same fixture. Then, with `ACTIVE = frozenset({"plans/big.md"})`:

```python
nested = root / ".claude"
def show(label):
    out = subprocess.run(("git", "status", "--porcelain=v1", "--untracked-files=all"),
                         cwd=nested, text=True, capture_output=True, check=True).stdout
    print(label)
    for line in out.splitlines():
        print("   ", repr(line), "is_relevant=",
              mod["is_relevant_nested_path"](line[3:], ACTIVE))

(nested / "plans" / "big.md").write_text("NESTED v2\n")
show("after editing .claude/plans/big.md:")
(nested / "plans" / "big.md").write_text("NESTED v1\n")
(root / "plans" / "big.md").write_text("OUTER v2\n")
show("after editing outer plans/big.md:")
```

Expected: `' M .claude/plans/big.md'` and `' M plans/big.md'`, both
`is_relevant=True`.

### C. Fingerprint sensitivity to outer state (finding 3, continued)

Same fixture. Call `mod["nested_tracked_state_fingerprint"](root, ACTIVE)` at a
clean baseline, after editing only the nested plan, and after editing only the
outer plan. Expected: all three digests differ, showing the fingerprint binds
outer state it should ignore.

## Related records

- `.claude/plans/2026-09-11_phase-B-terminal-publication-recovery.md` — the phase
  that added `nested_state_repository` and fixed the CRITICAL escape-hatch defect.
- `.claude/session_logs/2026-09-11_phase-B-terminal-publication-recovery.md` —
  under "Known gap, deliberately left open". **That entry understates this**: it
  describes only the outer-HEAD resolution and does not mention the wrong-file
  reads or the status-spelling collision. Treat this brief as the accurate record.
- `.claude/MEMORY.md` — `[LEARN:review]` on `git -C <dir> rev-parse HEAD` walking
  up, and `[LEARN:testing]` on the fixture that avoided the hazard instead of
  reproducing it.
