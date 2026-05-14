# Migration

## For This Bootstrap Repository

1. Edit source files under `shared/`.
2. Regenerate targets:

   ```bash
   python3 scripts/generate_targets.py --all
   ```

3. Validate generated outputs:

   ```bash
   python3 scripts/validate_targets.py
   ```

4. Check optional runtime wiring:

   ```bash
   python3 scripts/check_runtime.py
   ```

## For Consumer Repositories

Use the generated target that matches the agent environment:

- Copy `dist/github-copilot/` for GitHub Copilot in VS Code.
- Copy `dist/claude-code/` for Claude Code.
- Copy `dist/openai-codex/` for OpenAI Codex.

Legacy root `.github/`, `.vscode/mcp.json`, and `AGENTS.md` files remain active in this repository during the first migration pass.

## Deprecation Rule

Do not remove duplicated legacy files until the generated GitHub Copilot target is validated against existing behavior.
