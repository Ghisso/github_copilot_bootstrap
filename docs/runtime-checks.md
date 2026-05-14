# Runtime Checks

Run:

```bash
python3 scripts/check_runtime.py
```

The runtime checker verifies generated runtime files exist and reports optional helper availability.

Optional helpers:

- `context-mode`
- `npx`
- `uvx`
- Semble through `uvx --from "semble[mcp]" semble`

Missing optional binaries produce `WARN`, not `FAIL`.

Guardrail scripts are generated for each target:

- `protect-files.sh`
- `git-protection.sh`
- `context-mode-dispatch.sh`
- `session-log.sh`

The scripts must remain executable in generated targets.

Codex-specific runtime notes:

- `.codex/config.toml` must include `[features] codex_hooks = true`.
- `.codex/config.toml` includes `[agents]` with `max_depth = 1` to keep generated custom-agent fan-out bounded.
- `.codex/agents/*.toml` files are project-scoped custom agents and must define `name`, `description`, and `developer_instructions`.
- `.agents/skills/*/SKILL.md` stores repository-scoped Codex skills.
- `.codex/hooks.json` uses event groups with nested `hooks` arrays.
- Repo-local Codex hook commands resolve scripts from `$(git rev-parse --show-toplevel)` so hooks still work when Codex starts in a subdirectory.
- Because Codex `PreToolUse` cannot request approval, edits to Codex hook config are denied instead of downgraded to an approval prompt.
