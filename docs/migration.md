# Migration

## For This Bootstrap Repository

1. Edit source files under `shared/`.
2. Regenerate the installable output:

   ```bash
   python3 scripts/generate_targets.py --all
   ```

3. Validate generated output:

   ```bash
   python3 scripts/validate_targets.py
   ```

4. Check optional runtime wiring:

   ```bash
   python3 scripts/check_runtime.py
   ```

## For Consumer Repositories

Copy the single generated target:

```bash
rsync -av dist/multi-agent/ /path/to/your-project/
chmod +x /path/to/your-project/.claude/hooks/scripts/*.sh
```

The generated `.claude/` tree is the shared basis for all tools, while `.github/`, `.codex/`, `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, and `.vscode/mcp.json` are native adapters/config. If a consumer repo does not use one tool, delete only that tool's native adapter/config files and keep `.claude/`.

Optional pruning:

- No Copilot: delete `.github/` and `.vscode/mcp.json`.
- No Claude Code: delete `CLAUDE.md`, `.mcp.json`, and `.claude/settings.json`.
- No Codex: delete `AGENTS.md` and `.codex/`.

## Deprecation Rule

Target-local history/support directories such as `.github/plans/`, `.github/session_logs/`, `.codex/plans/`, `.codex/session_logs/`, and `.agents/skills/` are obsolete for new installs. New projects should write plans, explorations, logs, quality reports, memory, and skills under `.claude/`.
