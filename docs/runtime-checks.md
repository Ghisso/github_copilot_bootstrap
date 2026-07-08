# Runtime Checks

Run:

```bash
uv run python scripts/check_runtime.py
```

The runtime checker verifies generated runtime files exist and reports optional helper availability.

Optional helpers:

- `context-mode`
- `npx`
- `gh`
- `uv`
- `uvx`
- Semble through `uvx --from "semble[mcp]" semble`

Missing optional binaries produce `WARN`, not `FAIL`.

Guardrail scripts are generated under the shared `.claude/hooks/scripts/` basis:

- `run-hook.sh`
- `protect-files.sh`
- `git-protection.sh`
- `context-mode-dispatch.sh`
- `session-log.sh`
- `hf-ai-sync.sh`
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

## Two-Layer Commit Enforcement

The plan/score/closeout/LEARN ceremony above is enforced twice, from a single shared contract (`assert_commit_invariants` in `_lib-frontmatter.sh`):

- **`PreToolUse` (`enforce-commit-gate.sh`)** gates the AI agent's own Bash tool calls. It can `ask`/`deny` before a turn is wasted and denies an agent commit on any branch that isn't `<plan_name>_implementation`.
- **`commit-msg` (a real git hook, generated under `.claude/hooks/git-hooks/`)** gates every commit that reaches git itself — human, IDE, script, or alias (`git ci`) — on one code path, with no command string to classify and no timeout to fail open on. It is installed by setting `git config core.hooksPath .claude/hooks/git-hooks` (done by `install_bootstrap.py` and, for containers, by `post-start.sh`), and it only runs the ceremony checks on `<plan_name>_implementation` branches — `dev`/`main` commits pass through untouched.

`git commit --no-verify` is the sanctioned manual escape from the `commit-msg` layer (git skips the hook entirely; no git hook fires when hooks are skipped). Because `.claude/` is gitignored and Hugging Face-synced, a fresh clone has no `.claude/hooks/git-hooks/` until the first sync — git warns and runs no hook in that window, which is a known, accepted degradation (see `docs/plan-deterministic-commit-gate.md`).

## Devcontainer And HF Sync

Generated output includes `.devcontainer/`:

- `devcontainer.json` uses the GPU sandbox by default and forwards `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, and `HF_XET_HIGH_PERFORMANCE=1` for high-performance Xet transfers. UV environment variables (`UV_PROJECT_ENVIRONMENT`, `UV_CACHE_DIR`, `UV_LINK_MODE`) are set to isolate the virtualenv and cache inside the container.
- `Dockerfile` installs Python, uv, git, sudo, `context-mode`, and `semble[mcp]`. `huggingface_hub>=1.0` is pinned directly (not `hf_transfer`; Xet transfers are enabled via `HF_XET_HIGH_PERFORMANCE` instead). The lower bound is required because `HfApi.sync_bucket` was added in 1.0; without it, sync calls raise `AttributeError` that the broad exception handler swallows silently, causing the script to exit 0 having done nothing. If a project's `pyproject.toml` introduces a transitive dep that would downgrade `huggingface_hub` below 1.0, the `import_hf_api()` function in `hf-ai-sync.py` detects the missing method, emits a named warning, and falls back to the `hf` CLI so the failure is visible rather than silent.
- `post-start.sh` fixes git object ownership on the bind-mounted workspace (root can create files in `.git` during container init, breaking subsequent git writes), then sets `core.hooksPath` to `.claude/hooks/git-hooks` before calling `.devcontainer/hf-ai-sync.py pull` to restore ignored AI bootstrap/state files — so the commit-msg gate is wired the instant the pull populates the hook directory. `REPO_ROOT` is resolved via `git rev-parse --show-toplevel` with a path-relative fallback.

There is **no baked-in default bucket** — a bucket must be configured. The installer
requires `--bucket <org/bucket[/prefix]>` or `HF_AI_SYNC_BUCKET` and exits with an
instruction otherwise; it writes the project-specific bucket path (e.g.
`your-org/your-bucket/your-project`) into `.devcontainer/devcontainer.json`. The sync
helper resolves settings in this order: explicit CLI arguments, `HF_AI_SYNC_*`
environment variables, then `.devcontainer` config; with none configured it warns and
no-ops rather than falling back to any namespace. Auth resolves in this order: `HF_TOKEN`,
`HUGGING_FACE_HUB_TOKEN`, then the cached token created by `hf auth login` or
`huggingface-cli login`. Missing auth or bucket access produces warnings and does not
fail the container start or agent hook.

Prefer CLI sync through `huggingface_hub` over `hf-mount`. The generated devcontainer
does not require `/dev/fuse` or apparmor overrides. It does set `SYS_ADMIN` and
`seccomp=unconfined` so `bubblewrap` can create namespaces inside Docker.

Codex-specific runtime notes:

- `.codex/config.toml` omits the `[features]` block — hooks are on by default in current Codex, so restating `hooks = true` is redundant.
- `.codex/config.toml` includes `[agents]` with `max_depth = 1` to keep generated custom-agent fan-out bounded (the reviewer runs its own passes, so no second nesting level is needed).
- `.codex/config.toml` includes one `[[skills.config]]` entry per skill whose `path` points at the skill's `SKILL.md` file (`../.claude/skills/<name>/SKILL.md`), matching Codex's documented skill registration.
- `.codex/hooks.json` wires the documented `PreCompact` event (alongside SessionStart/PreToolUse/PostToolUse/Stop).
- `.codex/agents/*.toml` files are project-scoped custom agents and must define `name`, `description`, and `developer_instructions`.
- `.claude/skills/*/SKILL.md` stores the shared skills used by Codex, Claude, and Copilot.
- `.claude/review-profiles/*.md` stores the unified reviewer checklists.
- `.codex/hooks.json` uses event groups with nested `hooks` arrays.
- Repo-local Codex hook commands resolve shared scripts from `$(git rev-parse --show-toplevel)/.claude/hooks/scripts` so hooks still work when Codex starts in a subdirectory.
- Codex project trust is required before `.codex/config.toml`, hooks, and skill path wiring are loaded.
- Because Codex `PreToolUse` cannot request approval, edits to Codex hook config are denied instead of downgraded to an approval prompt.
