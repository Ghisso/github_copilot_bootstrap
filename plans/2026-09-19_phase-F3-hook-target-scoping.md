---
name: 2026-09-19_phase-F3-hook-target-scoping
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 8
status: planned
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
  with no redirect returns 1; `--git-dir <tmp-repo>/.git commit` and
  `--work-tree=<tmp-repo> commit` return 0; `-C <nonexistent>` returns 1; `-C "$SOME_VAR"` returns
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
    commit through. `git -C <dir> commit` is the supported way to commit elsewhere, and Step F3.5
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

### Step F3.5 — Document the two scope changes

- [ ] **Owner:** `documenter`
- **Target files:**
  - modify `docs/runtime-checks.md`: extend the classifier contract paragraph at `:218-230` with
    the repository-scoped versus global split and the fail-closed rule; add one paragraph on the
    commit gate's target scoping, naming `git -C <dir> commit` as the supported way to commit in
    another repository and recording that a `cd` prefix stays gated
  - modify `docs/smoke-tests.md`: extend the `protect-files.sh` line at `:203` with the scoping
    split
  - modify `docs/architecture.md` at `:464` only where it describes the classifier's reach
- **Required Skills:**
  - `shared/skills/documentation/SKILL.md`
  - `shared/skills/humanize/SKILL.md`
- **Acceptance criteria:** a reader who hits either guard in another repository finds the reason
  and the supported command in `docs/runtime-checks.md`; no document claims the classifier
  protects control-plane names outside this repository.

### Step F3.6 — Review

- [ ] **Owner:** `reviewer`
- **Target files:** scoped Phase F3 diff
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
- **Review focus:**
  - `security`, pointed at Step F3.4 specifically: the six-row split table is accurate and
    complete; each repository-scoped alternative's safety argument holds; every unresolvable
    candidate stays protected; containment cannot be tricked by a relative path, a `..` sequence,
    a symlink in either direction, or a sibling directory whose name shares a prefix with
    `REPO_ROOT`; no secret-shaped alternative was narrowed.
  - `security`, on Step F3.1: the resolver forwards only `-C`, `--git-dir` and `--work-tree`, so a
    command string cannot inject `-c` configuration or `--exec-path` into the resolver's own `git`
    call.
  - `architecture`: the gate reuses `git_targets_nested_claude`'s per-invocation shape rather than
    a new scheme; the nested exemption still precedes the foreign exemption; no fourth copy of the
    resolution logic survives.
  - `code`: `enforce-commit-gate.sh`'s `REPO_ROOT`, bypass, branch and invariant paths are
    untouched; array expansions satisfy the scanner at `tests/test_hook_gates.py:334`.
  - `tests`: every allowed-case test demonstrably fails on the pre-change tree; the two
    still-denies proofs exist (in-repository commit; secret-shaped filename outside the
    repository); the tests exercise the real `git` binary against real temporary repositories and
    the real classifier, with no test double standing in for either.
  - `ponytail`: the promoted resolver is the reuse, not a reinvention; both fixes stay inside
    existing functions.
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
  --local-only`, after the `generate_targets.py --all` above) and reproduce both Phase F commands
  live in a host session: `git -C <scratch-dir> commit --allow-empty -m spike` and a Bash heredoc
  containing `os.environ`. This is optional because the required pytest cases above already run
  both guards end to end against real temporary repositories, and because refreshing the overlay
  mid-phase mutates `.claude/` outside this phase's diff, which is an orchestrator-owned
  operational action rather than a check this plan owns. Record the outcome, or record NOT RUN
  with a reason, in the closeout log.

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
- [ ] Both defects have a regression test that fails on the pre-change tree and passes after, and
      both still-denies proofs exist: an in-repository commit is still gated, and a secret-shaped
      filename outside the repository is still protected
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
