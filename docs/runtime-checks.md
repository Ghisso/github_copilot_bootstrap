# Runtime Checks

Run:

```bash
uv run python scripts/check_runtime.py
```

The runtime checker verifies generated runtime files exist and reports optional helper availability.

Optional helpers:

- `context-mode`
- `npx`
- `uv`
- `uvx`
- Semble through `uvx --from "semble[mcp]" semble`

Missing optional binaries produce `WARN`, not `FAIL`.

Guardrail scripts are generated under the shared `.claude/hooks/scripts/` basis:

- `protect-files.sh`
- `git-protection.sh`
- `context-mode-dispatch.sh`
- `session-log.sh`
- `hf-ai-sync.sh`

The scripts must remain executable in `dist/multi-agent/` (gitignored; regenerate before checking) and in copied consumer repos.

## Devcontainer And HF Sync

Generated output includes `.devcontainer/`:

- `devcontainer.json` uses the GPU sandbox by default and forwards `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, and `HF_XET_HIGH_PERFORMANCE=1` for high-performance Xet transfers. UV environment variables (`UV_PROJECT_ENVIRONMENT`, `UV_CACHE_DIR`, `UV_LINK_MODE`) are set to isolate the virtualenv and cache inside the container.
- `Dockerfile` installs Python, uv, git, sudo, `context-mode`, and `semble[mcp]`. `huggingface_hub>=1.0` is pinned directly (not `hf_transfer`; Xet transfers are enabled via `HF_XET_HIGH_PERFORMANCE` instead). The lower bound is required because `HfApi.sync_bucket` was added in 1.0; without it, sync calls raise `AttributeError` that the broad exception handler swallows silently, causing the script to exit 0 having done nothing. If a project's `pyproject.toml` introduces a transitive dep that would downgrade `huggingface_hub` below 1.0, the `import_hf_api()` function in `hf-ai-sync.py` detects the missing method, emits a named warning, and falls back to the `hf` CLI so the failure is visible rather than silent.
- `post-start.sh` fixes git object ownership on the bind-mounted workspace (root can create files in `.git` during container init, breaking subsequent git writes). It then calls `.devcontainer/hf-ai-sync.py pull` to restore ignored AI bootstrap/state files. `REPO_ROOT` is resolved via `git rev-parse --show-toplevel` with a path-relative fallback.

The default bucket base is `Ghisso/vscode_mounts`, but installed consumer repos should
store a project-specific bucket path such as `Ghisso/vscode_mounts/img-classification`
in `.devcontainer/devcontainer.json`. The sync helper resolves settings in this order:
explicit CLI arguments, `HF_AI_SYNC_*` environment variables, `.devcontainer` config,
then the default bucket base. Auth resolves in this order: `HF_TOKEN`,
`HUGGING_FACE_HUB_TOKEN`, then the cached token created by `hf auth login` or
`huggingface-cli login`. Missing auth or bucket access produces warnings and does not
fail the container start or agent hook.

Prefer CLI sync through `huggingface_hub` over `hf-mount`. The generated devcontainer
does not require `/dev/fuse`, `SYS_ADMIN`, or apparmor overrides.

Codex-specific runtime notes:

- `.codex/config.toml` must include `[features] codex_hooks = true`.
- `.codex/config.toml` includes `[agents]` with `max_depth = 1` to keep generated custom-agent fan-out bounded.
- `.codex/config.toml` includes one `[[skills.config]]` entry for each `.claude/skills/<name>` directory.
- `.codex/agents/*.toml` files are project-scoped custom agents and must define `name`, `description`, and `developer_instructions`.
- `.claude/skills/*/SKILL.md` stores the shared skills used by Codex, Claude, and Copilot.
- `.claude/review-profiles/*.md` stores the unified reviewer checklists.
- `.codex/hooks.json` uses event groups with nested `hooks` arrays.
- Repo-local Codex hook commands resolve shared scripts from `$(git rev-parse --show-toplevel)/.claude/hooks/scripts` so hooks still work when Codex starts in a subdirectory.
- Codex project trust is required before `.codex/config.toml`, hooks, and skill path wiring are loaded.
- Because Codex `PreToolUse` cannot request approval, edits to Codex hook config are denied instead of downgraded to an approval prompt.
