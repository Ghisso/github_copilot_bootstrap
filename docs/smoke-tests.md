# Smoke Tests

## Deterministic Generation

```bash
python3 scripts/generate_targets.py --all
python3 scripts/validate_targets.py
```

Expected:

- Validator prints `PASS generated target is structurally valid`.
- Re-running generation does not change generated output.

## Custom Agent Portability

Expected:

- GitHub Copilot has 8 `.github/agents/*.agent.md` files.
- The generated output has 8 canonical `.claude/agents/*.md` files.
- OpenAI Codex has 8 `.codex/agents/*.toml` files.
- The generated output mirrors every repository skill under `.claude/skills/`.
- The generated output mirrors every review profile under `.claude/review-profiles/`.
- OpenAI Codex has one enabled `[[skills.config]]` entry per `.claude/skills/<name>`.
- `dist/` contains `multi-agent/` and no obsolete `github-copilot/`, `claude-code/`, or `openai-codex/` generated target directories.
- The generated output has no obsolete `.github/skills/`, `.agents/skills/`, `.codex/skills/`, or target-local state directories.
- Claude and Codex outputs do not contain Copilot model pins.
- Codex does not generate deprecated `.codex/rules/` output.
- Generated output contains `MEMORY.md`, workflow directories, templates, prompts, hook scripts, and `quality_score.py` in the shared `.claude/` basis.

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

- Guardrail scripts exist under `.claude/hooks/scripts/`.
- `protect-files.sh` denies protected files through structured write tools and Bash writes such as `touch .env`.
- Hook config edits through Bash redirection are protected, with Codex denying and GitHub/Claude asking for approval.
- Hook configs invoke `.claude/hooks/scripts/` and pass an explicit target id.
- Missing `context-mode`, `npx`, or `uvx` reports warnings only.
- GitHub Copilot hook config remains native at `.github/hooks/hooks.json` but calls shared `.claude` scripts.
