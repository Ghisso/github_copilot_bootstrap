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

Guardrail scripts are generated under the shared `.claude/hooks/scripts/` basis:

- `protect-files.sh`
- `git-protection.sh`
- `context-mode-dispatch.sh`
- `session-log.sh`

The scripts must remain executable in `dist/multi-agent/` and copied consumer repos.

Codex-specific runtime notes:

- `.codex/config.toml` must include `[features] codex_hooks = true`.
- `.codex/config.toml` includes `[agents]` with `max_depth = 1` to keep generated custom-agent fan-out bounded.
- `.codex/config.toml` includes one `[[skills.config]]` entry for each `.claude/skills/<name>` directory.
- `.codex/agents/*.toml` files are project-scoped custom agents and must define `name`, `description`, and `developer_instructions`.
- `.claude/skills/*/SKILL.md` stores the shared skills used by Codex, Claude, and Copilot.
- `.codex/hooks.json` uses event groups with nested `hooks` arrays.
- Repo-local Codex hook commands resolve shared scripts from `$(git rev-parse --show-toplevel)/.claude/hooks/scripts` so hooks still work when Codex starts in a subdirectory.
- Codex project trust is required before `.codex/config.toml`, hooks, and skill path wiring are loaded.
- Because Codex `PreToolUse` cannot request approval, edits to Codex hook config are denied instead of downgraded to an approval prompt.
