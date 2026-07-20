# Runtime Checks

Run:

```bash
uv run python scripts/check_runtime.py
```

The runtime checker verifies generated runtime files exist, including the
Ponytail coding/review skills and upstream license/provenance, and reports
optional helper availability.

Optional helpers:

- `context-mode`
- `npx`
- `gh`
- `uv`
- `uvx`
- Semble through `uvx --from "semble[mcp]" semble`
- context7 through `npx -y @upstash/context7-mcp` (missing `npx` warns, does not fail; falls back to training-data knowledge)

Missing optional binaries produce `WARN`, not `FAIL`.

Ponytail does not add a runtime binary requirement. Its portable skills are
vendored into `.claude/skills/`; the bootstrap's existing reviewer and pure
Bash git gates enforce the fresh zero-finding Ponytail review. Node.js is used
elsewhere by the managed devcontainer, but is not required solely for this
Ponytail integration.

Guardrail scripts are generated under the shared `.claude/hooks/scripts/` basis:

- `run-hook.sh`
- `protect-files.sh`
- `git-protection.sh`
- `context-mode-dispatch.sh`
- `session-log.sh`
- `state-sync.sh`
- `restore-root-adapters.sh`
- `session-start-state.sh`
- `enforce-branch-state.sh`
- `record-branch-state.sh`
- `enforce-commit-gate.sh`
- `record-commit-closeout.sh`
- `enforce-pr-gate.sh`
- `stop-session-log-check.sh`

The scripts must remain executable in `dist/multi-agent/` (gitignored; regenerate before checking) and in copied consumer repos. `run-hook.sh` is especially important because Claude and Codex hook configs execute it directly; generated output is invalid if that dispatcher is not runnable.

The runtime checker also runs the plan frontmatter validator when it is present. Invalid lifecycle metadata produces `WARN`, not `FAIL`, so partially migrated consumer repos can still start while showing exactly what needs cleanup.

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
  - **`PreToolUse` (`enforce-commit-gate.sh`)** gates the AI agent's own Bash tool calls. It can `ask`/`deny` before a turn is wasted and denies an agent commit on any branch that isn't `<plan_name>_implementation`.
  - **`commit-msg` (a real git hook, generated under `.claude/hooks/git-hooks/`)** gates every commit that reaches git itself — human, IDE, script, or alias (`git ci`) — on one code path, with no command string to classify and no timeout to fail open on. It only runs the ceremony checks on `<plan_name>_implementation` branches — `dev`/`main` commits pass through untouched.
- **Push invariant** — the big-plan/phase-completeness/commit-count/bypass-acknowledgment ceremony, via `assert_push_invariants` in `_lib-frontmatter.sh`:
  - **`PreToolUse` (`enforce-pr-gate.sh`)** gates the agent's own `git push` and `gh pr create` Bash calls, and is the only layer that checks `gh pr create --base dev` (a `pre-push` hook has no PR-creation concept to gate).
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

The generated devcontainer does not require `/dev/fuse` or apparmor overrides for
`huggingface_hub`. It does set `SYS_ADMIN` and `seccomp=unconfined` so `bubblewrap`
can create namespaces inside Docker.

Codex-specific runtime notes:

- `.codex/config.toml` omits the flat `[features]` block — hooks are on by default, so restating `hooks = true` is redundant — but includes `[features.multi_agent_v2]` with visible spawn metadata in the `agents` namespace so named custom-agent model and effort overrides are honored.
- `.codex/config.toml` leaves the interactive session model and reasoning effort unpinned; generated custom agents carry their explicit model intent.
- `.codex/config.toml` includes `[agents]` with `max_depth = 1` to keep generated custom-agent fan-out bounded (the reviewer runs its own passes, so no second nesting level is needed).
- `.codex/config.toml` includes one `[[skills.config]]` entry per skill whose `path` points at the skill's `SKILL.md` file (`../.claude/skills/<name>/SKILL.md`), matching Codex's documented skill registration.
- `.codex/hooks.json` wires the documented `PreCompact` event (alongside SessionStart/PreToolUse/PostToolUse/Stop).
- `.codex/agents/*.toml` files are project-scoped custom agents and must define `name`, `description`, `model`, `model_reasoning_effort`, and `developer_instructions`; model and effort must match the canonical shared agent metadata.
- `.claude/skills/*/SKILL.md` stores the shared skills used by Codex, Claude, and Copilot.
- `.claude/review-profiles/*.md` stores the unified reviewer checklists.
- `.codex/hooks.json` uses event groups with nested `hooks` arrays.
- Repo-local Codex hook commands resolve shared scripts from `$(git rev-parse --show-toplevel)/.claude/hooks/scripts` so hooks still work when Codex starts in a subdirectory.
- Codex project trust is required before `.codex/config.toml`, hooks, and skill path wiring are loaded.
- Because Codex `PreToolUse` cannot request approval, edits to Codex hook config are denied instead of downgraded to an approval prompt.
