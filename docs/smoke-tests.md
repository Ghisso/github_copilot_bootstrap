# Smoke Tests

## Deterministic Generation

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
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
- Generated output contains `.devcontainer/devcontainer.json`, `.devcontainer/Dockerfile`, `.devcontainer/post-start.sh`, and `.devcontainer/hf-ai-sync.py`.

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
- Stop hooks invoke `hf-ai-sync.sh` to push mutable AI state to Hugging Face.
- Missing `context-mode`, `npx`, or `uvx` reports warnings only.
- GitHub Copilot hook config remains native at `.github/hooks/hooks.json` but calls shared `.claude` scripts.

## Devcontainer And HF Sync

Expected:

- `.devcontainer/` is trackable and generated AI content is ignored by the installer.
- The generated devcontainer forwards `HF_TOKEN` and `HUGGING_FACE_HUB_TOKEN`.
- The generated devcontainer does not require `/dev/fuse`, `SYS_ADMIN`, or apparmor overrides.
- The HF sync helper reads installed `.devcontainer` sync settings, falls back to `Ghisso/vscode_mounts`, and supports dry-run operation without network access.
