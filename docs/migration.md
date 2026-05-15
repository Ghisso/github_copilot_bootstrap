# Migration

## For This Bootstrap Repository

1. Edit source files under `shared/`.
2. Regenerate the installable output:

   ```bash
   uv run python scripts/generate_targets.py --all
   ```

3. Validate generated output:

   ```bash
   uv run python scripts/validate_targets.py
   ```

4. Check optional runtime wiring:

   ```bash
   uv run python scripts/check_runtime.py
   ```

## For Consumer Repositories

Install the single generated target:

```bash
TARGET_REPO="/path/to/your-project"
HF_BUCKET_PATH="Ghisso/vscode_mounts/$(basename "$TARGET_REPO")"
uv run python scripts/install_bootstrap.py "$TARGET_REPO" --bucket "$HF_BUCKET_PATH"
```

For `img-classification`, that is:

```bash
uv run python scripts/install_bootstrap.py /path/to/your-project/ --bucket Ghisso/vscode_mounts/img-classification
```

The installer copies the generated bootstrap, keeps `.devcontainer/` trackable, adds
an idempotent `.gitignore` block for generated/private AI content, and uploads the
bootstrap bundle to `hf://buckets/Ghisso/vscode_mounts/<project-name>/bootstrap/`
when Hugging Face auth is available. It also writes the sync path into
`.devcontainer/devcontainer.json`, so hooks and container startup use the same HF
prefix.

The generated `.claude/` tree is the shared basis for all tools, while `.github/`,
`.codex/`, `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, and `.vscode/mcp.json` are native
adapters/config. In consumer repos those AI files should stay ignored; `.devcontainer/`
is committed so a fresh clone can reopen in a container and pull the ignored AI bundle
and state from Hugging Face.

Optional pruning:

- No Copilot: delete `.github/` and `.vscode/mcp.json`.
- No Claude Code: delete `CLAUDE.md`, `.mcp.json`, and `.claude/settings.json`.
- No Codex: delete `AGENTS.md` and `.codex/`.

## Deprecation Rule

Target-local history/support directories such as `.github/plans/`, `.github/session_logs/`, `.codex/plans/`, `.codex/session_logs/`, and `.agents/skills/` are obsolete for new installs. New projects should write plans, explorations, logs, quality reports, memory, and skills under `.claude/`.

## Reviewer Agent Migration

Specialized reviewer agent names were retired in favor of one profile-driven `reviewer` agent.

| Old agent name | New reviewer profiles |
|---|---|
| `code-reviewer` | `code` |
| `security-reviewer` | `security` |
| `architecture-reviewer` | `architecture` |
| `test-reviewer` | `tests` |
| `api-reviewer` | `api`, `security`, `tests` |
| `config-reviewer` | `config` |
| `performance-reviewer` | `performance` |
| `documentation-reviewer` | `documentation` |
| `domain-reviewer` | `domain` |

Review helper names also changed from model-specific names to `review-pass-primary` and `review-pass-adversarial`.
