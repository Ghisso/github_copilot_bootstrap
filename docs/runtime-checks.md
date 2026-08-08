# Runtime Checks

Run:

```bash
uv run python scripts/check_runtime.py
```

The runtime checker verifies generated runtime files exist, including the
Ponytail coding/review skills and upstream license/provenance, and reports
optional helper availability.

## Refreshing This Repository's Own Overlay

The bootstrap's dogfood overlay is refreshed with `--allow-self`:

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/install_bootstrap.py . --allow-self --local-only
```

`install_bootstrap.py` normally refuses overlapping source and target, because
the generated source (`dist/multi-agent`) lives inside this repository.
`--allow-self` permits **only** that case, and only when the target is the
bootstrap repository itself. Installing a tree over itself, or into a directory
beneath the source, stays rejected with or without the flag. Removal is safe
here because it walks only `target/.claude` and the restorable root adapters,
so `dist/` is never a removal candidate. `update_consumers.py` accepts the same
flag and forwards it.

Never hand-copy `dist/` into place; always regenerate and install.

### What a self-refresh removes

Files under `.claude/` that the generated target does not contain are removed as
obsolete owned files. Consumer state (`MEMORY.md`, `plans`, `explorations`,
`session_logs`, `quality_reports`, `project-context.instructions.md`) is
preserved, as are tracked authoring adapters such as `.codex/config.toml` and
`AGENTS.md`.

`.claude/settings.local.json` is now consumer state and is preserved. It used
to be deleted as an obsolete owned file on **every** install, in every consumer
— and because `state-sync.sh` deliberately gitignores it in the nested repo
("local convenience only; never synced"), that deletion was unrecoverable. Any
file matching the nested ignore list is local-only by design and must never be
treated as bootstrap-owned.

A file that exists under `.claude/` but not in the generated target is still
removed as obsolete. `check_runtime.py` reports such orphans before a refresh
does anything, so read its output first. An authored skill living only in the
overlay should be promoted into `shared/skills/` so it regenerates, rather than
being left to be deleted by the next refresh.

### Expected side effects

A self-refresh writes the consumer ignore block into `.gitignore`
(`.claude/`, `.codex/`, the Copilot surface, `.vscode/mcp.json`). Files already
tracked stay tracked; the installer prints a `git rm --cached` hint if you want
to untrack them.

The refreshed hook guards are stricter than older installed copies. They fail
closed on opaque shell syntax — process substitution and heredocs piped into an
interpreter are denied even when the command is read-only. Prefer plain
commands, or run a script from a file, inside a refreshed repository.

It also performs a read-only, bidirectional dogfood drift check. Bootstrap-owned
files in this source checkout must match freshly generated output (after the
documented project-name substitution); unexpected obsolete owned files fail too.
The check deliberately excludes consumer-owned `.claude` state: `MEMORY.md`,
plans, explorations, session logs, quality reports, and explicit project-context
customization. Tracked source adapters such as root `AGENTS.md` are checked for
their authoring invariants rather than byte-compared to a generated consumer
adapter. A failure names the stale path, its authoritative source, and the
regenerate/reinstall command.

Optional helpers:

- `context-mode`
- `npx`
- `gh`
- `uv`
- `uvx`
- Semble through `uvx --from "semble[mcp]" semble`
- context7 through `npx -y @upstash/context7-mcp` (missing `npx` warns, does not fail; falls back to training-data knowledge)

Missing optional binaries produce `WARN`, not `FAIL`.

## Native Client Release Checks (Opt-In)

`check_runtime.py` remains an offline structural/runtime check. It does not
authenticate or start Codex or Claude, and a structural PASS is not evidence of
native instruction delivery, hook trust, compact/resume behavior, or Codex role
routing. The native probe's default temporary mode deliberately does not launch
either client, so it is only a structure/missing-client smoke and reports an
installed client as unresolved `WARN`/`untrusted`. For actual native execution,
prepare, inspect, and manually trust a dedicated stable workspace, then rerun
against that same workspace:

```bash
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe --prepare-only --json
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe \
  --client codex --require --json
```

Default availability/trust failures are `WARN`; `--require` makes them `FAIL`.
`--require` also makes unresolved `unexercised` WARNs nonzero. The probe runs
two separate read-only temporary consumers (control and shim-removed candidate)
with ephemeral/non-persistent sessions, a minimal environment, process-group
timeout cleanup, no Codex MCP/apps/web search, no hook approval, and no trust
mutation. It keeps client output out of the result. Schema v2 records only
instruction sentinels; trust is preflight/execution status. Codex role metadata
can PASS only from explicit JSONL agent/thread/subagent events; undocumented or
absent events are WARN, not proof. Compact/resume and coder escalation are
currently unexercised WARNs. Claude has no Codex-role matrix. Read [Native
Client Acceptance](native-client-acceptance.md) before interpreting a report or
changing a compatibility gate.

The persistent path must be dedicated: preparation refuses broad paths and
nonempty directories without its ownership marker. A later preparation refreshes
only marker-owned probe children. It never writes a trust setting, approves a
hook, or forces a safety bypass; trust remains an explicit operator action.

Ponytail does not add a runtime binary requirement. Its portable skills are
vendored into `.claude/skills/`; the bootstrap's existing reviewer and pure
Bash git gates enforce the fresh zero-finding Ponytail review. Node.js is used
elsewhere by the managed devcontainer, but is not required solely for this
Ponytail integration.

Guardrail scripts are generated under the shared `.claude/hooks/scripts/` basis:

- `run-hook.sh`
- `protect-files.sh`
- `pretool-bash-guard.sh`
- `git-protection.sh`
- `context-mode-dispatch.sh`
- `session-log.sh`
- `state-sync.sh`
- `claude-stop.sh`
- `codex-stop.sh`
- `restore-root-adapters.sh`
- `session-start-state.sh`
- `enforce-branch-state.sh`
- `record-branch-state.sh`
- `enforce-commit-gate.sh`
- `record-commit-closeout.sh`
- `enforce-pr-gate.sh`
- `stop-session-log-check.sh`

The scripts must remain executable in `dist/multi-agent/` (gitignored; regenerate before checking) and in copied consumer repos. `run-hook.sh` is especially important because Claude and Codex hook configs execute it directly; generated output is invalid if that dispatcher is not runnable.

For the primary targets, generated `PreToolUse` routing must remain split into
three groups: native file mutations (`Edit|MultiEdit|Write` for Claude,
`Edit|Write` for Codex) call `protect-files.sh`; `Bash` calls the single ordered
`pretool-bash-guard.sh`; and `*` calls only best-effort
`context-mode-dispatch.sh`. `Read` and MCP tools must have no mutation handler.
The Bash wrapper must preserve the guard order: protected files, dangerous Git,
branch state, commit gate, then PR gate. Lifecycle Stop/Session wrappers are
outside that lane and retain their existing sequencing.

`protect-files.sh` requires `python3` and calls its bundled classifier directly;
it never depends on `uv run` or a project virtual environment. Missing Python,
malformed payloads, classifier errors, incomplete redirects, indeterminate
in-place targets, and ambiguous shell syntax must fail closed. The classifier
must preserve the proven read-only path while checking both source and
destination operands of copy/install/move operations, so a protected source
cannot be exfiltrated through a write-bearing command. For opaque command or
interpreter syntax, verify conservative literal coverage for `.env*`, `uv.lock`,
`credentials*`, secret names, `.pem`/`.key` files, hook paths, and protected
hook configuration files; do not require denial of unknown commands that carry
none of those literals.

The runtime checker also runs the plan frontmatter validator when it is present. Invalid lifecycle metadata produces `WARN`, not `FAIL`, so partially migrated consumer repos can still start while showing exactly what needs cleanup.

Runtime verification also expects the installer and updater defaults to create
and publish nested `ai-state` commits. With `--local-only`, they must instead
complete the full generated refresh and leave a clean, committed nested
repository without invoking fetch, `ls-remote`, pull, merge, or push. A legacy
consumer must retain ordered `migrate: import pre-git state` and subsequent
`bootstrap:` history; the installer reports nested status and a shell-safe
manual publish command.

The installer writes `.claude/bootstrap-ownership.env` as inert data, never as
executable shell input. It records whether the Copilot surface is local-only or
committed and which root adapters may be restored from `.claude/bootstrap-root/`.
An update retains that mode unless you explicitly select the opposite
`--[no-]commit-copilot-surface` option. During a refresh, obsolete files that
are bootstrap-owned by the active mode are removed safely; consumer state and
the nested repository metadata are retained.

The generated `state-sync.sh` supports `setup`, `pull`, `checkpoint`,
`publish`, `push`, `status`, and `migrate-from-hf`. Verify `checkpoint` without
network access: it must create only a local commit. Verify `publish` only from
a clean nested worktree: it must not stage or commit, and it must preserve dirty
state for a later checkpoint. `push` remains the compatible checkpoint-then-
publish operation. Operational output belongs on stderr; `status` alone writes
a read-only, network-free report using local and cached tracking state, without
printing a remote URL or credentials. Failures remain auditable in
`.claude/session_logs/hooks-errors.log`.

For generated Codex and Claude hooks, verify one runtime-specific Stop wrapper
runs sequentially for each turn: session log, session-log check, `checkpoint`,
then best-effort `publish`. Codex stdout must be exactly one valid JSON object;
Claude's wrapper emits no stdout. Both `UserPromptSubmit` hooks retry `push`
with a 60-second timeout. Codex delayed, best-effort `SessionEnd` invokes only
local `checkpoint` with timeout `3`; Claude `StopFailure` also invokes only
local `checkpoint`, while Claude `SessionEnd` invokes `push` with timeout `60`.
No lifecycle event may split checkpoint and publication into concurrent handlers.
Timeout or network failure must preserve the local commit for a later retry;
use `state-sync.sh status` and `.claude/session_logs/hooks-errors.log` to
inspect recovery state. Post-commit and the manual VS Code **AI state: push**
task remain the durable checkpoint-and-publish paths.

An install or update can change `.codex/hooks.json`, whose Codex for VS Code
project trust is content/hash-bound. Verify the installer and batch updater
only print the reopen/reload-and-review guidance: they must never approve hooks
or mutate user trust settings. A dry run must describe the potential review
without claiming that it changed hooks. If sync is not progressing after you
approve updated hooks, run `state-sync.sh status` and inspect
`.claude/session_logs/hooks-errors.log`.

Lifecycle score reports must be written as `.claude/quality_reports/score-<timestamp>.json`. Commit gates read persisted JSON reports, not terminal output, and require matching branch, phase, base ref, merge-base SHA, and current HEAD SHA. The report must also record `tests_passed: true`, must not be `tests_skipped`, must be `dirty: false` (no unstaged changes), must target a repo-relative path, and must carry a `content_hash` (`git hash-object` of the diff against the merge base) that still matches the working tree. The newest report by `generated_at` wins, and the gate is written to be `uv`-independent — the pure-bash guardrails still enforce even when `uv` is absent (only `quality_score.py` itself needs `uv`).

For non-documentation diffs, the matching findings report must also contain
`ponytail_reviewed: true` and `ponytail_findings: 0`. `record_findings.py`
receives `--profile ponytail`; its existing content hash invalidates the
review after any real source, test, script, hook, config, manifest, template,
container, or generator edit. All-Markdown and documented workflow-state
diffs are exempt.

## Two Layers, Two Invariants: Commit And Push Enforcement

Two workflow invariants are each enforced twice, from a single shared contract per invariant:

- **Commit invariant** — the plan/score/closeout/LEARN ceremony, via `assert_commit_invariants` in `_lib-frontmatter.sh`:
  - **`PreToolUse` (`enforce-commit-gate.sh`)** gates the AI agent's own Bash tool calls. It can `ask`/`deny` before a turn is wasted and denies an agent commit on any branch that isn't `<plan_name>_implementation`. It exempts commits that target the nested `ai-state` repo (`git -C .claude commit`, `--git-dir=.claude/.git`, `--work-tree .claude`) — `state-sync.sh` commits there constantly and has no ceremony of its own to satisfy — but only when the *matching commit invocation itself* carries the nested-repo flag, not merely because some other `git` call earlier or later in the same compound command happens to touch `.claude/`.
  - **`commit-msg` (a real git hook, generated under `.claude/hooks/git-hooks/`)** gates every commit that reaches git itself — human, IDE, script, or alias (`git ci`) — on one code path, with no command string to classify and no timeout to fail open on. It only runs the ceremony checks on `<plan_name>_implementation` branches — `dev`/`main` commits pass through untouched.
- **Push invariant** — the big-plan/phase-completeness/commit-count/bypass-acknowledgment ceremony, via `assert_push_invariants` in `_lib-frontmatter.sh`:
  - **`PreToolUse` (`enforce-pr-gate.sh`)** gates the agent's own `git push` and `gh pr create` Bash calls, and is the only layer that checks `gh pr create --base dev` (a `pre-push` hook has no PR-creation concept to gate). It exempts nested `ai-state` pushes the same way, and with the same per-invocation scoping, as the commit gate above.
  - **`pre-push` (a real git hook, generated under `.claude/hooks/git-hooks/`)** gates every push that reaches git itself, reading ref lines from stdin (`<local-ref> <local-sha> <remote-ref> <remote-sha>`). It derives the branch and the commit-count check from the *pushed* ref/sha, not from whatever is checked out, so a push of `foo_implementation` from elsewhere is still gated. It skips branch deletions (all-zero local sha) and only runs the ceremony checks on `<plan_name>_implementation` refs — `dev`/`main` pushes pass through untouched.

Both git-hook layers are installed by setting `git config core.hooksPath .claude/hooks/git-hooks` (done by `install_bootstrap.py` and, for containers, by `post-start.sh`).

The hooks and their shared library (`_lib-frontmatter.sh`) are pure bash with no dependency on `uv`, and are written to the **bash 3.2** baseline — the version macOS still ships as `/bin/bash` — so no bash-4-only builtins (`mapfile`/`readarray`), associative arrays, or negative array indices. This keeps the gates working identically on a stock macOS consumer machine and on the `macos-latest` CI runner (`.github/workflows/validate.yml`), which is where `_lib-frontmatter.sh`'s GNU-vs-BSD `stat`/`find` fallbacks are actually exercised.

`git commit --no-verify` / `git push --no-verify` are the sanctioned manual escapes from the `commit-msg` / `pre-push` layers respectively (git skips the hook entirely; no git hook fires when hooks are skipped). Because `.claude/` is gitignored, a fresh clone has no `.claude/hooks/git-hooks/` until it is checked out — git warns and runs no hook in that window, which is a known, accepted degradation (see `docs/plan-deterministic-commit-gate.md`). That window shrank when AI state moved from a Hugging Face bucket to a nested git repo (`plans/adr-002-git-backed-state-sync.md`): `post-start.sh` now checks `.claude/` out via `state-sync.sh setup` using the same git credentials as the code checkout, with no separate authenticated pull to wait on, and sets `core.hooksPath` immediately after.

Per `githooks(5)`, `commit-msg` also fires for `git merge` (not just `git commit`). A plain merge commit authors no content of its own, so the hook passes merge commits through unledgered on an implementation branch — the ceremony re-attaches at the next real commit, since the score's `merge_base_sha`/`content_hash` checks force a fresh report once new content lands. `git rebase` and `git cherry-pick` do **not** invoke `commit-msg` at all (this is git behavior, not a bootstrap bug); commits they create skip the git layer, but the next real commit on the branch is still gated normally. `git commit --amend` *does* invoke `commit-msg`, and the `content_hash` check is designed to survive a content-preserving amend (the diff against the merge base is unchanged, so a report scored before the amend still matches). **Known, accepted escape:** the `MERGE_HEAD`-based passthrough cannot distinguish a pure merge from `git merge --no-commit` followed by manually staging extra changes before completing the commit — this is a second, undetected way to land ungated content on an implementation branch, alongside the sanctioned `--no-verify` escape. It requires deliberately reaching for `--no-commit`, the same trust boundary as `--no-verify`.

## Devcontainer And Git-Backed State Sync

Generated output includes `.devcontainer/`:

- `devcontainer.json` uses the GPU sandbox by default and forwards `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, and `HF_XET_HIGH_PERFORMANCE=1` for high-performance Xet transfers (used by the projects themselves, e.g. models/datasets — not by AI state sync anymore). UV environment variables (`UV_PROJECT_ENVIRONMENT`, `UV_CACHE_DIR`, `UV_LINK_MODE`) are set to isolate the virtualenv and cache inside the container.
- `Dockerfile` installs Python, uv, git, sudo, `context-mode`, and `semble[mcp]`. `huggingface_hub>=1.0` stays pinned (not `hf_transfer`; Xet transfers are enabled via `HF_XET_HIGH_PERFORMANCE` instead) for the projects' own use.
- `post-start.sh` fixes git object ownership on the bind-mounted workspace (root can create files in `.git` during container init, breaking subsequent git writes), then runs `state-sync.sh setup` (checks `.claude/` out from the `ai-state` branch, creating it fresh if this is the very first sync anywhere), sets `core.hooksPath` to `.claude/hooks/git-hooks` immediately after — so the commit-msg gate is wired the instant the checkout populates the hook directory — then `state-sync.sh pull` and `restore-root-adapters.sh` (restores `.claude/bootstrap-root/**` to the repo root: `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `.codex/**`, etc.). `REPO_ROOT` is resolved via `git rev-parse --show-toplevel` with a path-relative fallback; `state-sync.sh` and `restore-root-adapters.sh` are rendered into `.devcontainer/` itself (not just `.claude/hooks/scripts/`) because `.claude/` does not exist at all before the first of these runs.

There is **no separate credential to configure** — by default the nested `.claude/`
repo's remote is the outer repo's own `origin`, so it authenticates the same way the
code checkout does. `install_bootstrap.py --state-remote <git-url>` (env
`AI_STATE_REMOTE`) points it somewhere else instead (a private personal repo, for
example); when set, the installer persists `AI_STATE_REMOTE` into
`.devcontainer/devcontainer.json`'s `containerEnv` so a fresh container clone still
finds it. A missing remote or network access produces warnings and does not fail
the container start or agent hook (see `plans/adr-002-git-backed-state-sync.md`).

Source-layout validation permits a root `.github/` self-install overlay only
when Git ignores it and it is byte-identical to the generated target. A tracked,
unignored, or stale mirror fails validation, preventing generated runtime files
from becoming a second editable source.

The generated devcontainer does not require `/dev/fuse` or apparmor overrides for
`huggingface_hub`. It does set `SYS_ADMIN` and `seccomp=unconfined` so `bubblewrap`
can create namespaces inside Docker.

Codex-specific runtime notes:

- `.codex/config.toml` omits the flat `[features]` block — hooks are on by default, so restating `hooks = true` is redundant — but includes `[features.multi_agent_v2]` with visible spawn metadata in the `agents` namespace so named custom-agent model and effort overrides are honored.
- `.codex/config.toml` leaves the interactive session model and reasoning effort unpinned; generated custom agents carry their explicit model intent.
- `.codex/config.toml` sets the documented `agents.max_concurrent_threads_per_session = 6`, never emits the legacy `agents.max_threads`, and omits `agents.enabled` because its documented default is `true`.
- `.codex/config.toml` retains `max_depth = 1` as a separate protected removal candidate to keep custom-agent fan-out bounded (the reviewer runs its own passes, so no second nesting level is needed).
- `.codex/config.toml` includes one `[[skills.config]]` entry per skill whose `path` points at the skill's `SKILL.md` file (`../.claude/skills/<name>/SKILL.md`), matching Codex's documented skill registration.
- `.codex/hooks.json` wires the documented `PreCompact` event (alongside SessionStart/PreToolUse/PostToolUse/Stop).
- `.codex/hooks.json` uses the narrow native-edit, ordered-Bash, and wildcard-observability matcher groups; it must not send every tool through the mutation guard.
- `.codex/agents/*.toml` files are project-scoped custom agents and must define `name`, `description`, `model`, `model_reasoning_effort`, and `developer_instructions`; model and effort must match canonical `agent.yaml` metadata. Each instruction body has one generated delimiter and the exact transformed shared prompt, with no runtime read of a Claude-native agent file. Per-agent MCP and skill overrides are omitted, so the trusted project config supplies the shared registrations. The validator checks structural parity and records actual sizes; native probes, not a static size threshold, must establish delivery without truncation.
- `.claude/skills/*/SKILL.md` stores the shared skills used by Codex, Claude, and Copilot.
- `.claude/review-profiles/*.md` stores the unified reviewer checklists.
- `.codex/hooks.json` uses event groups with nested `hooks` arrays.
- Repo-local Codex hook commands resolve shared scripts from `$(git rev-parse --show-toplevel)/.claude/hooks/scripts` so hooks still work when Codex starts in a subdirectory.
- Codex project trust is required before `.codex/config.toml`, hooks, and skill path wiring are loaded.
- Because Codex `PreToolUse` cannot request approval, hook-config mutations are denied instead of downgraded to an approval prompt. Claude asks for approval. Both allow a read-only inspection of a protected configuration when the command classifier can prove it has no mutation target; redirects, in-place edits, and ambiguous commands fail closed.

The generated consumer `.codex/config.toml` is carried in
`.claude/bootstrap-root/.codex/` and restored on a fresh consumer machine. In
this bootstrap repository, the root `.codex/config.toml` is protected tracked
authoring, so a dogfood refresh preserves it while it updates generated sibling
adapters. The protected V2 shim is not removed based on parsing or static
validation alone. See the [dated Codex routing compatibility record](2026-08-08-codex-routing-compatibility.md): repeated trusted-project, six-role native probes on two supported versions are required before removing the shim; `max_depth` has its own removal gate. Six-role routing was verified on 2026-08-09 with the shim present.
