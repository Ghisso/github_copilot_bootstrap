---
name: 2026-09-19_phase-F3-hook-target-scoping
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 8
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-F3-hook-target-scoping

## Scope

Phase F recorded two control-plane defects in
`.claude/session_logs/2026-09-19_openwiki-phase-F-hook-mechanics-spike.md`. Both are the
same mistake in two guards: the guard judges the *text* of a command, or its own installed
location, instead of the *target* the command acts on.

1. `enforce-commit-gate.sh` refused `git -C <scratch-dir> commit --allow-empty -m spike` in a
   throwaway directory outside this checkout, naming this repository's Phase F plan in the denial.
2. `protect-files.py` refused an ordinary Python heredoc containing `os.environ` (the `.env`
   inside `environ`), and refused any Bash command whose text mentioned `.claude/settings.json`,
   `.codex/config.toml` or `.codex/hooks.json` regardless of which directory those files were in.

3. Found by inspection while fixing the first two: `enforce-pr-gate.sh` and
   `enforce-branch-state.sh` both work out which repository they govern from where the hook script
   itself is installed (`:8` and `:9`), so a `git push` or a `git checkout -b` aimed at another
   repository is judged against this repository's current branch, working tree and plan files.

This phase scopes three gates to their actual targets — the commit gate, the push gate, and the
branch-creation gate — and scopes the protected-file classifier's control-plane rules to this
repository. It changes no gate's verdict for any command that acts on this repository. Phase F's
`[LEARN:quality]` entry is the reason this is worth a phase: both the coder and the orchestrator
worked around the classifier by switching from Bash to `Write`/`Edit`/`Read`, and a guard that
people route around by changing tools has stopped being a guard.

This is control-plane work under the repository's own classification in `CLAUDE.md`: it edits
`shared/hooks/scripts/`. It therefore requires a full plan and the `code`, `architecture`,
`security`, `tests` and `ponytail` review profiles. Every fix here makes a guard stand down for a
target it was never meant to govern, which is the point. One of them needs a closer security
reading than the rest: the classifier scoping in Step F3.4 decides whether to stand down by
resolving a path and testing whether it falls inside this repository, rather than by reading an
explicit redirect the operator typed. Path resolution can be argued with; an explicit `-C` cannot.
Step F3.8 points the `security` profile at that difference.

Four contained fixes to existing code. No rewrite of `protect-files.py` (1397 lines of established
reasoning about heredocs, variable substitution and quoting), no new hook script, and no change to
`record-branch-state.sh`, the `PostToolUse` handler that writes plan state after a branch is
created: it already declines to write unless this repository's own `HEAD` matches the branch name
it parsed (`:21-25`), so a branch created elsewhere cannot reach the plan-state write.

**Three design decisions, resolved here rather than left to the implementer.**

*The shared helper keeps one subcommand per call.* `git_targets_other_repository`, added in
Step F3.1, takes a command string and a single git subcommand and answers whether every invocation
of that subcommand in the command provably acts on a different repository. Step F3.2 calls it with
`commit` and Step F3.5 calls it with `push`.

*Branch creation gets its own predicate instead.* It does not fit the shared helper, because it
spans two subcommands with different flag grammars — `git checkout -b` and `git switch -c` — and
calling the helper once per subcommand gives the wrong answer: the helper requires at least one
invocation of the named subcommand to exist, so the conjunction of two calls is false whenever only
one of the two shapes appears. Step F3.6 therefore builds a dedicated predicate on the same
underlying resolver, mirroring how the library already gives branch creation a dedicated parser
rather than routing it through a generic subcommand walker.

*Pull-request creation is deliberately not scoped, and keeps gating every time.* Unlike `git`,
the `gh` command line has no directory redirect: it works out its target from an `owner/repo` pair
passed to `-R`, falling back to the current directory's remote. Scoping it would mean normalising
and comparing remote URLs — `https://` and `git@host:` forms, optional `.git` suffixes,
case-insensitive owner names — inside the control plane, and a comparison that wrongly reported
"different repository" would let a real pull request skip this repository's closeout ceremony.
That is the worst failure available in this phase, and nothing observed in Phase F asks for it. So
`gh pr create` is checked from this checkout whatever repository it names. Step F3.5 still changes
that file, for a reason that stands on its own: the hook's existing exemption for the nested
state-sync repository currently exits the whole hook, which lets a pull request slip past
unchecked.

**Carried into this phase (2026-09-20).** Four files edited after Phase F2's completion commit
ride in this phase's diff and review: `shared/policies/workflow.instructions.md` (new numbered
`### CLOSEOUT sequence` with two hard rules), `shared/agents/orchestrator/prompt.md` (CLOSEOUT
step points to it), `shared/skills/commit/SKILL.md` and `README.md` (the commit-gate hook judges a
command's text before it runs, so `git commit` runs in its own command). They are policy prose
requested by the user after two closeout ordering mistakes; the `documentation` review profile is
added to Step F3.8 for them.

**Test-file deviation.** Steps F3.3 and F3.4 put their tests in a new
`tests/test_protect_files_scoping.py` instead of `tests/test_hook_gates.py`, so the two coders
working in parallel do not edit the same test file.

## Steps

### Step F3.1 — Promote the target-repository resolver into the shared hook library

The machinery already exists twice. `_git_invocation_targets_nested_claude`
(`shared/hooks/scripts/_lib-frontmatter.sh:482`) tokenises one git invocation and reads `-C`,
`--git-dir`, `--git-dir=`, `--work-tree` and `--work-tree=`; `git_targets_nested_claude`
(`:525`) walks every `git` invocation in a compound command and answers per invocation rather
than per command string. Separately, `git_command_targets_repo_root`
(`shared/hooks/scripts/reporting-reminder.sh:101-124`) already resolves an invocation's effective
top level with `git "${options[@]}" rev-parse --show-toplevel` (`:122`) and compares it
physically to `REPO_ROOT`. Promote the third one into the library so the commit gate reuses it
instead of growing a fourth copy.

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/hooks/scripts/_lib-frontmatter.sh`; modify
  `shared/hooks/scripts/reporting-reminder.sh`; extend `tests/test_hook_gates.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/refactor/SKILL.md`
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract:**
  - `_git_invocation_top_level <tokens...>` — private, mirroring
    `_git_invocation_targets_nested_claude`'s shape. Reads only the global flags before the first
    positional token. Prints the physical top level of the repository that invocation acts on, or
    prints nothing when the target cannot be determined.
  - It forwards exactly `-C`, `--git-dir`, `--git-dir=`, `--work-tree` and `--work-tree=` to
    `git -C "$REPO_ROOT" <forwarded> rev-parse --show-toplevel`, anchoring a relative value to
    `REPO_ROOT` the way `reporting-reminder.sh:103` already does. It prints nothing for any other
    flag before the subcommand. `-c`, `--config-env`, `--exec-path`, `--namespace` and
    `--super-prefix` are never forwarded, so a command string cannot inject configuration into
    the resolver's own `git` call.
  - It prints nothing when a value-taking flag has no value token, when a value is empty, or when
    a value still contains `$`, a backtick, or a leading `~`, because the hook does not evaluate
    shell expansion.
  - `git_targets_other_repository <command> <subcommand>` — public, with the same signature and
    the same all-invocations semantics as `git_targets_nested_claude`. Returns 0 only when at
    least one `git <subcommand>` invocation exists **and** every one of them carries an explicit
    directory redirect that resolves to a non-empty top level different from `$REPO_ROOT`.
    Returns 1 in every other case, including no matching invocation, no explicit redirect, an
    unresolvable target, and an equal top level.
  - `git_command_targets_repo_root` in `reporting-reminder.sh` is rewritten to call
    `_git_invocation_top_level` and keeps its current observable behavior.
  - Both comparisons use the physical path on both sides (`cd "$path" && pwd -P`), so a symlinked
    checkout does not read as a different repository.
  - New array code uses the guarded expansion idiom the static scanner at
    `tests/test_hook_gates.py:334` enforces (`${tokens[@]+"${tokens[@]}"}`).
- **Must not:** change `git_targets_nested_claude`, `_git_invocation_targets_nested_claude`,
  `repo_root_from_script` (`:752`), `_shell_tokenize` (`:338`), or `_git_first_subcommand`
  (`:389`).
- **Test scenarios** (`tests/test_hook_gates.py`, reusing `_bash_source` at `:75` and the
  `_git_targets_nested_claude` probe shape at `:90`): a real temporary git repository created
  under `tmp_path` resolves to itself; `git -C <tmp-repo> commit -m x` returns 0; `git commit -m x`
  with no redirect returns 1; `--git-dir <tmp-repo>/.git --work-tree <tmp-repo> commit` and
  `--work-tree=<tmp-repo> commit` return 0; `--git-dir <tmp-repo>/.git commit` **alone** returns 1
  (corrected 2026-09-20 during implementation: without `--work-tree`, git treats the current
  directory as the working tree, so from inside this checkout that command commits this
  repository's files into a borrowed object store and must stay gated); `-C <nonexistent>` returns 1; `-C "$SOME_VAR"` returns
  1; `-C <tmp-dir-that-is-not-a-repo>` returns 1; `-C .claude` returns 1 (inside this repository,
  and still handled by the nested exemption); a bare repository returns 1; `git -c foo=bar -C
  <tmp-repo> commit` returns 1 because an unforwarded flag makes the invocation undeterminable.
- **Verification:** `uv run pytest tests/test_hook_gates.py -k "top_level or other_repository" -q`
  and `uv run pytest tests/test_lifecycle_hooks.py -q`, which covers the rewritten
  `git_command_targets_repo_root` through the existing `run_reporting_reminder`
  (`tests/test_lifecycle_hooks.py:493`) and `copy_reporting_reminder` (`:564`) harnesses.
- **Acceptance criteria:** the reminder's behavior is unchanged, proven by
  `tests/test_lifecycle_hooks.py` passing without edits to its assertions; no fourth copy of the
  resolution logic exists in the tree.

### Step F3.2 — Scope the commit gate to this repository

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/hooks/scripts/enforce-commit-gate.sh`; extend
  `tests/test_hook_gates.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract:**
  - Add one exemption immediately after the existing nested-`.claude` exemption at
    `enforce-commit-gate.sh:28`: `if git_targets_other_repository "$COMMAND" commit; then exit 0;
    fi`. Ordering matters and is not interchangeable — the nested `ai-state` repository lives
    physically inside `REPO_ROOT`, so the foreign-repository test cannot subsume it.
  - Extend the docstring at `:20-27` with the same per-invocation reasoning for the foreign case:
    a compound command that mixes a commit in another repository with a commit targeting this one
    is still gated in full.
  - `REPO_ROOT` (`:9`), the bypass path (`:37`), the branch check (`:43`) and
    `assert_commit_invariants` (`:63`) are untouched, because the new exemption returns before any
    of them.
  - **Fail closed.** Every undeterminable case keeps gating: no explicit redirect, an unresolvable
    redirect, a bare repository, an unforwarded flag, a missing value token.
  - **A `cd` prefix is out of scope, and stays gated.** `cd /tmp/x && git commit -m y` continues
    to be judged against this repository. Modelling `cd` here would *narrow* a gate, and the hook
    library deliberately does not evaluate shell semantics: `_shell_tokenize` discards operators
    and never tracks a working directory. `protect-files.py` does model `cd`, but there the model
    *widens* protection, so an error is conservative; here an error would let a real in-repository
    commit through. `git -C <dir> commit` is the supported way to commit elsewhere, and Step F3.7
    documents it.
- **Test scenarios:** run `enforce-commit-gate.sh` through a `PreToolUse` Bash payload with
  `_isolated_hook_scripts_dir` (`tests/test_hook_gates.py:38`) so `REPO_ROOT` is a synthetic
  checkout:
  - a real temporary git repository outside that root, `git -C <other> commit --allow-empty -m
    spike` — exits 0, emits no denial. **This reproduces the exact Phase F command and fails
    before the change.**
  - `git commit -m "x"` with no redirect, on a non-implementation branch — still denies, message
    still prefixed `commit gate failed for`. **This is the proof the gate still fires for a commit
    that does target this repository.**
  - `git -C <other> commit -m a && git commit -m b` — still denies.
  - `git commit -m b && git -C <other> commit -m a` — still denies.
  - `git -C <other-a> commit -m a && git -C <other-b> commit -m b` — exits 0.
  - `git -C .claude commit -m sync` — exits 0 through the pre-existing nested exemption, unchanged.
  - `cd /tmp/elsewhere && git commit -m x` — still denies, recording the documented limit.
  - `git -C <path-that-is-not-a-repo> commit -m x` — still denies.
- **Verification:** `uv run pytest tests/test_hook_gates.py -k commit_gate -q`
- **Acceptance criteria:** each of the eight scenarios is a named test; the scratch-directory test
  and the in-repository test both exist and assert opposite outcomes; the scratch-directory test
  fails on the pre-change tree and passes after.

### Step F3.3 — Give the literal extractor token boundaries

`PROTECTED_PATH_LITERAL` (`shared/hooks/scripts/protect-files.py:73-78`) is a *candidate
generator*, not the decider: its only call site is `protected_path_literals` at `:274`, whose
output is later classified by `protected()`. The `.env` alternative has no boundary on either
side, so it extracts the `.env` out of `os.environ` and hands `protected()` a candidate whose
basename is exactly `.env`. Every global alternative has some version of this problem.

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/hooks/scripts/protect-files.py`; extend
  `tests/test_hook_gates.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract — audit every alternative, fix each demonstrated boundary defect:**
  - `\.env(?:\.[\w.-]+)?` gains a left and a right word boundary. `os.environ` and `.environment`
    stop matching; `.env`, `.env.local`, `foo/.env.production` keep matching.
  - `uv\.lock` gains both boundaries. `myuv.lock` and `uv.lockfile` stop yielding the bare
    `uv.lock` fragment.
  - `credentials[-_.][\w.-]+` gains a left boundary. `mycredentials.json` stops yielding
    `credentials.json`.
  - `[^\s/'\"]+\.(?:pem|key)` gains a right boundary. `bundle.keys` stops yielding `bundle.key`.
  - The three control-plane alternatives are left to Step F3.4.
  - The `.rstrip(",;:)")` normalization at `:274` is unchanged.
- **Must not:** narrow any alternative in a way that loses a candidate `protected()` would have
  classified as protected. Prove it, do not assert it.
- **Test scenarios:** a table-driven test over the extractor asserting, for each alternative, one
  string that must match and one near-miss that must not; the Phase F reproduction as an
  end-to-end `_run_protect_files` case — a Python heredoc containing `os.environ` is allowed; an
  `echo` whose message text contains the literal `.env` is allowed; `touch .env` and
  `touch /tmp/other/.env` are both still denied; `rm config/service.pem` is still denied; the
  existing corpus at `tests/test_hook_gates.py:979` and `:1050` passes unchanged.
- **Verification:** `uv run pytest tests/test_hook_gates.py -k protect_files -q`
- **Acceptance criteria:** the `os.environ` heredoc test and the `.env`-in-`echo` test each fail
  on the pre-change tree and pass after; no existing `protect_files` test is weakened or deleted
  to make them pass.

### Step F3.4 — Repository-scope the control-plane alternatives, keep the secret-shaped ones global

Two clauses make control-plane names fire anywhere on the filesystem. First, the three
control-plane alternatives in `PROTECTED_PATH_LITERAL` (`:73-78`) match a *substring* of a longer
path, so `/tmp/scratch/.claude/settings.json` yields the fragment `.claude/settings.json`, which
`protected()` then reads as repository-relative and refuses. Second, `protected()` itself
(`:183-215`) tests `normalized in HOOK_CONFIGS` and three `"/.claude/hooks/" in normalized`-style
substrings at `:198-207`, which are global by construction. `REPO_ROOT` is already available:
`protect-files.sh:36` passes it as `argv[2]` and `main` unpacks it at `:1370`.

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/hooks/scripts/protect-files.py`; extend
  `tests/test_hook_gates.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **The split, stated explicitly:**

  | Alternative | Scope after this phase | Why |
  | --- | --- | --- |
  | `.claude/settings.json`, `.codex/config.toml`, `.codex/hooks.json`, `.github/hooks/hooks.json` (`HOOK_CONFIGS`, `:15-20`) | This repository only | These names identify *this* repository's guardrail configuration. A file with the same name in another checkout is that checkout's control plane, and this repository's hooks hold no mandate over it. `CLAUDE.md` defines the control plane as this repository's own root guidance, hook directories, settings and devcontainer. |
  | `(.github\|.claude\|.codex)/hooks/**` | This repository only | Same argument: these are the scripts this repository's own gates execute. |
  | `.env`, `.env.*` | Global, unchanged | Credential-shaped. Harmful to mutate or exfiltrate in any tree. |
  | `uv.lock` | Global, unchanged | Lockfile integrity is a supply-chain concern wherever the file lives. |
  | `credentials*` | Global, unchanged | Credential-shaped. |
  | `*.pem`, `*.key` | Global, unchanged | Credential-shaped. |

- **Contract:**
  - The control-plane alternatives in `PROTECTED_PATH_LITERAL` capture the **whole** path token,
    not a repository-relative-looking tail: a left boundary refuses a preceding path character and
    an explicit optional directory prefix carries the rest of the token. An absolute in-repository
    path in opaque interpreter text still matches and is still refused; a foreign absolute path is
    captured whole and handed to `protected()` for the containment decision.
  - `protected()` gains one containment predicate and applies it **only** to the control-plane
    clause at `:198-207`. The secret-shaped clause at `:208-214` is untouched.
  - Containment reuses the two-candidate structure `protected()` already builds at `:191-195`: a
    candidate counts as in-repository when **either** its lexical form **or** its
    `os.path.realpath()` form lands inside `repo_root`. Either one being inside is enough. This is
    the conservative direction and it mirrors the existing `normalized_paths` logic rather than
    inventing a second scheme.
  - Containment is decided on resolved path **components**, not on a string prefix, so
    `/repo-evil/.claude/settings.json` is not read as inside `/repo`.
  - `..` traversal is collapsed by `realpath` before the test. `<repo>/x/../../other/.claude/
    settings.json` resolves outside and is not repository-scoped;
    `/elsewhere/../<repo>/.claude/settings.json` resolves inside and stays protected.
  - Symlinks are followed by `realpath`. A symlink inside the repository pointing at a foreign
    control-plane file resolves outside; a symlink outside pointing into the repository resolves
    inside, and the lexical-or-resolved rule keeps both the link and its target protected when
    either lands in-repository.
  - **Fail closed.** A candidate that cannot be resolved to an absolute real path — an
    unexpanded variable, an unmatched glob, a `QUOTED_VALUE_PREFIX` marker, or any `OSError` from
    `realpath` — is treated as in-repository and stays protected. An empty `repo_root`, or a
    `repo_root` that is not a directory, makes **every** candidate in-repository.
  - Relative candidates keep their current meaning: `protected()` already joins them onto
    `repo_root` at `:188-189`, so a bare `.claude/settings.json` in a command is repository-local
    and stays protected.
- **Must not:** change `HOOK_CONFIGS`' contents, change the secret-shaped basename tests, or make
  `protected()` perform any filesystem write or subprocess call.
- **Test scenarios,** driven through `_run_protect_files(payload, repo_root)` with
  `_isolated_hook_scripts_dir` (`tests/test_hook_gates.py:38`) so the classifier runs against a
  synthetic `REPO_ROOT`:
  - `rm <outside>/.claude/settings.json` is allowed; `rm <repo>/.claude/settings.json` is denied.
    **These two are the before/after pair for defect 2(b).**
  - The same pair for `.codex/config.toml`, `.codex/hooks.json` and `.github/hooks/hooks.json`.
  - `rm <outside>/.claude/hooks/run-hook.sh` is allowed; `rm .claude/hooks/run-hook.sh` is denied.
  - A bare relative `.claude/settings.json` in a mutating command is denied.
  - `rm /tmp/scratch/.env`, `rm /tmp/scratch/uv.lock`, `rm /tmp/scratch/id_rsa.key` and
    `rm /tmp/scratch/credentials.json` are all **still denied**. **This is the proof a
    secret-shaped filename is still protected outside the repository.**
  - A symlink at `<repo>/link.json` pointing at `<outside>/.claude/settings.json` is allowed; a
    symlink at `<outside>/link.json` pointing at `<repo>/.claude/settings.json` is denied.
  - `<repo>/a/../../outside/.claude/settings.json` is allowed;
    `/outside/../<repo>/.claude/settings.json` is denied.
  - `rm "$UNKNOWN_DIR/.claude/settings.json"` is denied (unresolvable, fails closed).
  - An empty `repo_root` argument denies `.claude/settings.json`.
  - A read-only `cat` of a protected configuration remains allowed, matching the contract in
    `docs/smoke-tests.md:203`.
- **Verification:** `uv run pytest tests/test_hook_gates.py -k protect_files -q`
- **Acceptance criteria:** every allowed case above fails on the pre-change tree and passes after;
  every denied case passes on both trees; the whole existing `protect_files` corpus passes
  unchanged.

### Step F3.5 — Scope the push gate, and split the hook's two command shapes apart

`enforce-pr-gate.sh` guards two unrelated command shapes in one pass: pushing with `git push`, and
opening a pull request with `gh pr create`. Only the push shape is scoped to this repository here.
The pull-request shape keeps gating every time, for the reason recorded in Scope.

The step still has to change the file's control flow, and that change earns its place on its own.
The hook opens with an exemption for the nested `.claude` state-sync repository: `:23-25` asks
whether every `git push` in the command is aimed at that nested repository, and exits the hook when
they all are, so routine state syncing is not judged against this repository's release ceremony.
The problem is that it exits the *whole* hook, not just the push half. So
`git -C .claude push && gh pr create --base dev` opens a pull request with no branch check, no
`--base dev` check, and no closeout-evidence check: the nested push satisfies the question at
`:23`, and `:24` returns before any pull-request logic runs. **That hole exists today and closing
it is the main reason this step touches the file.** Adding a second whole-hook exemption next to it
would have made the hole bigger; making both exemptions answer per shape closes it.

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/hooks/scripts/enforce-pr-gate.sh`; extend
  `tests/test_lifecycle_hooks.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract — the push half:**
  - Reuse `git_targets_other_repository` from Step F3.1, called with the subcommand `push`. It
    reports whether every `git push` invocation in the command carries an explicit `-C`,
    `--git-dir` or `--work-tree` redirect that resolves to a repository other than this one, and
    reports false whenever any of them is undeterminable. This step adds nothing to
    `_lib-frontmatter.sh`; the library work was all done in Step F3.1.
- **Contract — the pull-request half:**
  - Unchanged. No predicate, no remote-URL parsing, no new library function. Every command
    containing a `gh pr create` reaches the existing checks below it.
- **Contract — the restructured exemption block, replacing `:20-28`:**
  - Work out once whether each shape is present, using the two existing detectors:
    `is_gh_pr_create_command`, which reports whether any `gh` invocation in the command is a
    `pr create`, and `is_git_push_command`, which reports whether the command contains a
    `git push`.
  - Write those as `if is_gh_pr_create_command "$COMMAND"; then IS_PR=1; fi`, never as
    `is_gh_pr_create_command "$COMMAND" && IS_PR=1`. This file runs under `set -euo pipefail`, and
    the second form makes the whole hook exit when the detector reports false, which would silently
    disable the gate.
  - Exit 0 when neither shape is present, exactly as `:26-28` does today.
  - Skip the gate only when **every shape that is present** provably acts elsewhere. The push shape
    qualifies when either the nested-repository question at `:23` or the
    `git_targets_other_repository` question answers yes. The pull-request shape never qualifies. So
    in practice: a command containing a `gh pr create` always proceeds to the checks below, and a
    push-only command proceeds unless its pushes all provably target the nested repository or
    another repository.
  - The nested-repository exemption keeps its current meaning and its explanatory comment at
    `:20-22`, and moves inside the push arm so it can no longer excuse a pull request.
  - Everything below the exemption block is untouched, because the skip returns before all of it:
    reading the current branch (`:30`), the implementation-branch requirement (`:31-34`), the
    `--base dev` requirement for pull requests (`:36-41`), the closeout-evidence checks that run
    for a pull request and the push-invariant checks that run for a push (`:44-48`), and the
    message explaining that a chained commit-and-push is evaluated against the pre-commit `HEAD`
    (`:53-60`).
- **Must not:** invoke `gh`, read any git remote, or parse a remote URL. The hook gains no
  dependency on the `gh` binary, on its stored authentication, or on the network.
- **Test scenarios,** in `tests/test_lifecycle_hooks.py`, reusing the existing fixture
  `enforce_pr_gate_repo` (`:904`), which builds a temporary repository on an implementation branch
  with no big plan so the invariant checks fail with one predictable finding, and the runner
  `run_enforce_pr_gate` (`:917`):
  - `git -C <other-repo> push` exits 0. **The foreign-push case; fails before the change.**
  - `git push` with no redirect still denies. **The proof the push gate still fires for a push that
    does target this repository.**
  - `git -C <other-repo> push && git push` still denies, because one push is undeterminable.
  - `git -C <path-that-is-not-a-repo> push` still denies.
  - `cd /tmp/elsewhere && git push` still denies, the same documented `cd` limit as Step F3.2.
  - `gh pr create --base dev` still denies. **The proof the pull-request gate is unchanged.**
  - `gh pr create -R other/repo --base dev` still denies. **The proof that naming another
    repository does not excuse a pull request — this is the decision recorded in Scope, asserted as
    behavior.**
  - `git -C .claude push && gh pr create --base dev` still denies, on the pull-request shape.
    **This is the pre-existing hole; the test fails before the change, and it is the one test here
    that proves the restructure rather than the scoping.**
  - `git -C <other-repo> push && gh pr create --base dev` still denies, on the pull-request shape.
    This is the same hole in its new form, proving the added push exemption did not reopen it.
  - `git -C .claude push` alone still exits 0, unchanged.
- **Verification:** `uv run pytest tests/test_lifecycle_hooks.py -k pr_gate -q`
- **Acceptance criteria:** the foreign-push test fails on the pre-change tree and passes after; the
  two hole-closing tests fail on the pre-change tree and pass after; the three still-denies proofs
  (bare push, bare pull request, pull request naming another repository) pass on both trees; no
  test invokes `gh`; the findings record the hole as a pre-existing defect closed here rather than
  as new behavior.

### Step F3.6 — Scope the branch-state gate to this repository

`enforce-branch-state.sh` reads `REPO_ROOT` for all three of its substantive checks —
`CURRENT_BRANCH` at `:41`, `git status --porcelain` at `:47`, and the big-plan lookup at `:53` — so
a branch created in another repository is judged against this repository's HEAD, working tree and
plan inventory. All three are meaningless for a foreign target, which is the defect.

- [ ] **Owner:** `coder`
- **Target files:** modify `shared/hooks/scripts/enforce-branch-state.sh`; modify
  `shared/hooks/scripts/_lib-frontmatter.sh`; extend `tests/test_hook_gates.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/refactor/SKILL.md`
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Contract:**
  - Extract the per-invocation body of `parse_branch_create_command` (`_lib-frontmatter.sh:423-465`)
    into `_git_invocation_created_branch <tokens...>`, which prints the branch name one invocation
    would create, or prints nothing. The grammar moves unchanged: the global-flag skip at `:428-437`
    including `-C`, `--git-dir` and `--work-tree` with their values, the `checkout` arm's `-b`/`-B`,
    the `switch` arm's `-c`/`-C`/`--create`/`--create=`, and the quote stripping at `:456-459`.
  - `parse_branch_create_command` keeps its exact signature, its walk, and its observable behavior,
    and now calls the extracted function. Its two callers — `enforce-branch-state.sh:21` and
    `record-branch-state.sh:16` — are not edited.
  - **There are two subcommands, not three.** The parser has no `branch` arm, so `git branch foo`
    is not gated today. This phase does not add one; widening what the gate catches is a different
    change from scoping what it already catches.
  - `branch_create_targets_other_repository <command>` — public. Walks `git` invocations the same
    way, and for each invocation where `_git_invocation_created_branch` yields a name, resolves
    that same invocation's tokens through `_git_invocation_top_level`. Returns 0 only when at least
    one branch-creating invocation exists **and** every one of them resolves to a non-empty top
    level different from `$REPO_ROOT`. Returns 1 in every other case.
  - In `enforce-branch-state.sh`, insert the skip between the `command -v git` check (`:26-29`) and
    the branch-name check (`:31`): `if branch_create_targets_other_repository "$COMMAND"; then exit
    0; fi`. Placing it after the git-availability check means the resolver never runs without
    `git`; placing it before `:31` means a foreign repository's own branch naming is not judged
    against `<plan_name>_implementation`.
  - **No nested-`.claude` exemption is added, and the plan states why.** `state-sync.sh` contains
    no `checkout`, no `switch -c` and no `git branch` — it commits and pushes only — so no branch
    is ever created in the nested `ai-state` repository and such an exemption would be dead code.
    This is why this hook has no nested exemption today.
  - **Fail closed.** No explicit redirect, an unresolvable redirect, a bare repository, an
    unforwarded flag, or a missing value token all keep gating. A `cd` prefix stays gated, for the
    reason given in Step F3.2.
  - `record-branch-state.sh` is unchanged: its `CURRENT_BRANCH != BRANCH` bail at `:21-25` already
    declines to record when the created branch is not this repository's own HEAD, so a foreign
    branch creation cannot reach the plan-state write at `:34` onward.
- **Test scenarios,** predicate tests via `_bash_source` (`tests/test_hook_gates.py:75`),
  end-to-end tests through `_isolated_hook_scripts_dir` (`:38`) as in Step F3.2:
  - `git -C <other-repo> switch -c anything` exits 0. **Foreign case, fails before the change.**
  - `git -C <other-repo> checkout -b anything` exits 0.
  - `git switch -c foo_implementation` with no redirect, from a non-`dev` branch, still denies.
    **This is the proof the branch gate still fires for a branch created in this repository.**
  - `git checkout -b not-an-implementation-name` still denies with the naming message.
  - `git -C <other> switch -c a && git switch -c b_implementation` still denies.
  - `git -C <path-that-is-not-a-repo> checkout -b x` still denies.
  - `cd /tmp/elsewhere && git checkout -b x` still denies.
  - `git branch foo` produces no gate before or after, confirming the unchanged parser coverage.
  - `parse_branch_create_command` returns byte-identical results to the pre-change function across
    the existing corpus, asserted directly.
  - A `PostToolUse` run of `record-branch-state.sh` after a foreign `git -C <other> switch -c
    <name>` writes no plan state, asserted against the untouched big plan.
- **Verification:** `uv run pytest tests/test_hook_gates.py -k "branch_create or branch_state" -q`
  and `uv run pytest tests/test_branch_state.py -q`
- **Acceptance criteria:** the two foreign cases fail on the pre-change tree and pass after; the
  in-repository denial proofs pass on both trees; `tests/test_branch_state.py` passes without edits
  to its assertions, proving the extraction changed no recorder behavior.

### Step F3.7 — Document the target-scoping changes

- [ ] **Owner:** `documenter`
- **Target files:**
  - modify `docs/runtime-checks.md`: extend the paragraph describing what the protected-file
    classifier must cover (`:218-230`) with the split between rules that apply only inside this
    repository and rules that apply to any path anywhere, and with the rule that an unresolvable
    path stays protected; add one paragraph on target scoping that states plainly which gates now
    stand down for another repository and which does not — committing, pushing and creating a
    branch stand down when the command carries an explicit `-C`, `--git-dir` or `--work-tree`
    pointing at a different repository, so `git -C <dir> commit`, `git -C <dir> push` and
    `git -C <dir> switch -c` are the supported ways to act on another repository from this
    checkout; creating a pull request is always checked from this checkout, whatever repository
    `-R` names; and a `cd` into another directory followed by any of these commands is still
    checked against this repository, everywhere
  - modify the "Other gates that newly block a refresh" table in `docs/runtime-checks.md`
    (`:495-503`): add no row, because nothing newly blocks — add instead the reverse note that
    three gates now stand down for a provably different target, with the unresolvable-target rule
    stated once
  - modify `docs/smoke-tests.md`: extend the `protect-files.sh` line (`:203`) with the same split,
    and extend the gate lines with the stand-down and its one exception
  - modify `docs/architecture.md` (`:464`) only where it describes how far the classifier reaches
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Acceptance criteria:** a reader who hits any of these gates in another repository finds the
  reason and the supported command in `docs/runtime-checks.md`; the pull-request exception is
  stated as a deliberate choice, with its reason, rather than left as an inconsistency; no document
  describes a repository comparison for `gh`, an accepted `-R` value format, or any remote-URL
  handling, because none exists; no document claims the classifier protects control-plane names
  outside this repository; no document claims `git branch foo` is gated.

### Step F3.8 — Review

- [ ] **Owner:** `reviewer`
- **Target files:** scoped Phase F3 diff
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
  - `documentation` (carried policy prose and Step F3.7)
- **Review focus:**
  - `security`, on Step F3.5's restructured hook: confirm that no command containing a
    `gh pr create` can leave the hook before reaching the branch check, the `--base dev` check and
    the closeout-evidence checks. That single invariant is what closes the pre-existing hole and
    what keeps the unscoped pull-request decision real. Confirm also that the file reads no git
    remote and parses no URL.
  - `security`, on Step F3.4, the one place in this phase where a guard stands down on the strength
    of a path this code resolved rather than a redirect the operator typed: the six-row table
    splitting repository-scoped rules from global ones is accurate and complete; each
    repository-scoped entry's safety argument holds; a path that cannot be resolved stays
    protected; the containment test cannot be fooled by a relative path, a `..` sequence, a symlink
    in either direction, or a sibling directory whose name merely starts with this repository's
    path; no rule covering credential-shaped filenames was narrowed.
  - `security`, on the resolver added in Step F3.1 and every predicate built on it in Steps F3.2,
    F3.5 and F3.6: it forwards only `-C`, `--git-dir` and `--work-tree` to the `git` call it makes
    to identify the target repository, so a command string cannot smuggle `-c` configuration or an
    `--exec-path` override into that call.
  - `architecture`: the three decisions recorded in Scope are the ones implemented — one
    single-subcommand helper serving `commit` and `push`, one dedicated predicate for branch
    creation, and no predicate at all for pull requests; the nested-repository exemption still
    encloses or precedes the different-repository exemption in both hooks that have one; the logic
    that identifies a target repository exists in exactly one place in the library.
  - `code`: in `enforce-commit-gate.sh`, the repository root, the bypass path, the branch check and
    the commit-invariant call are untouched; in `enforce-pr-gate.sh`, everything below the
    exemption block is untouched; in `enforce-branch-state.sh`, the three reads of the repository
    root are untouched; no `command && VAR=1` assignment was used under `set -euo pipefail`; array
    expansions use the guarded idiom the static scanner at `tests/test_hook_gates.py:334` enforces.
  - `tests`: every case that newly exits 0 demonstrably fails on the pre-change tree; all four
    still-denies proofs exist — an in-repository commit, an in-repository push, a pull request that
    names another repository, and an in-repository branch creation — plus the proof that a
    credential-shaped filename outside this repository is still protected; the two hole-closing
    tests in Step F3.5 fail before the change; the equivalence of `parse_branch_create_command`
    before and after Step F3.6's extraction is asserted directly and `tests/test_branch_state.py`
    passes with no edits to its assertions; the tests drive the real `git` binary against real
    temporary repositories and the real classifier, with no test double standing in for either, and
    no test invokes `gh`.
  - `ponytail`: the resolver promoted in Step F3.1 and the branch parser extracted in Step F3.6 are
    reuse of existing logic rather than new implementations of it; all four fixes stay inside
    existing functions and existing hook scripts.
  - this plan's own `## Verification` block and its closeout log satisfy the Verification
    Evidence Contract introduced by Phase F2.

## Verification

```bash
uv run pytest tests/test_hook_gates.py tests/test_lifecycle_hooks.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Optional Verification

- Refresh this repository's own overlay (`uv run python scripts/install_bootstrap.py . --allow-self
  --local-only`, after the `generate_targets.py --all` above) and reproduce the Phase F commands
  live in a host session: `git -C <scratch-dir> commit --allow-empty -m spike`, a Bash heredoc
  containing `os.environ`, `git -C <scratch-dir> push` against a scratch remote, and
  `git -C <scratch-dir> switch -c throwaway`. This item is optional because the required pytest
  cases above already drive all three gates and the classifier end to end against real temporary
  repositories, and because refreshing the overlay mid-phase mutates `.claude/` outside this
  phase's diff, which is an orchestrator-owned operational action rather than a check this plan
  owns. Record the outcome, or record NOT RUN with a reason, in the closeout log.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, CLOSEOUT); the order below mirrors it rather than restating it.

- [ ] Documentation updated (`docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/architecture.md`)
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED` and a `## Verification` section recording
      each of the eight required items above as PASS, plus the one optional item's outcome
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] All four fixes have a regression test that fails on the pre-change tree and passes after, and
      every still-denies proof exists: an in-repository commit, an in-repository push, a pull
      request that names another repository, an in-repository branch creation, and a
      credential-shaped filename outside this repository
- [ ] The pull-request arm carries no repository comparison and no remote-URL parsing, and the
      pre-existing hole that let a nested-repository push excuse an unchecked pull request is
      recorded in the findings as closed by this phase
- [ ] The parent plan's `phases:` list carries this phase between F2 and G, and G through K carry
      their renumbered `phase_index` values

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the required pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.

Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
