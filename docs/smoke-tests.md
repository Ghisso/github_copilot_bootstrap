# Smoke Tests

## Deterministic Generation

```bash
python3 scripts/generate_targets.py --all
python3 scripts/validate_targets.py
```

Expected:

- Validator prints `PASS generated targets are structurally valid`.
- Re-running generation does not change generated output.

## Custom Agent Portability

Expected:

- GitHub Copilot has 17 `.github/agents/*.agent.md` files.
- Claude Code has 17 `.claude/agents/*.md` files.
- OpenAI Codex has 17 `.codex/agents/*.toml` files.
- OpenAI Codex has 52 repository skills under `.agents/skills/` and no `.codex/skills/` directory.
- Claude and Codex outputs do not contain Copilot model pins.
- Codex does not generate deprecated `.codex/rules/` output.
- Generated targets contain `MEMORY.md`, workflow directories, templates, and `quality_score.py` in the target-native namespace.

## MCP Routing

Expected:

- GitHub and Claude JSON MCP files include `semble` and `context-mode`.
- Codex config includes `[mcp_servers.semble]` and `[mcp_servers.context-mode]`.
- Tool-routing policy preserves:
  - direct reads for known paths
  - `rg` for exact literals
  - Semble for semantic discovery
  - context-mode for long outputs and continuity
  - no duplicate broad searches

## Hooks

Expected:

- Guardrail scripts exist for all targets.
- `protect-files.sh` denies protected files through structured write tools and Bash writes such as `touch .env`.
- Hook config edits through Bash redirection are protected, with Codex denying and GitHub/Claude asking for approval.
- Missing `context-mode`, `npx`, or `uvx` reports warnings only.
- Existing GitHub Copilot hook config is preserved in generated output.
