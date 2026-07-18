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

- GitHub Copilot has 6 `.github/agents/*.agent.md` files.
- The generated output has 6 canonical `.claude/agents/*.md` files.
- OpenAI Codex has 6 `.codex/agents/*.toml` files.
- `reviewer` runs its own passes with no helper agents: a primary pass, then a verification pass that receives the primary findings and refutes each (dropping any that do not survive re-verification, converging when a pass yields nothing new twice or after 3 rounds). An orchestrated review therefore completes and can PASS a PR gate identically on GitHub Copilot, Claude Code, and OpenAI Codex (no dependence on subagent nesting depth).
- The generated output mirrors every repository skill under `.claude/skills/`.
- The generated output contains the pinned Ponytail coding/review skills plus its MIT license and `v4.8.4` provenance.
- The generated output mirrors every review profile under `.claude/review-profiles/`.
- OpenAI Codex has one enabled `[[skills.config]]` entry per `.claude/skills/<name>`.
- `dist/` contains `multi-agent/` and no obsolete `github-copilot/`, `claude-code/`, or `openai-codex/` generated target directories.
- The generated output has no obsolete `.github/skills/`, `.agents/skills/`, `.codex/skills/`, or target-local state directories.
- Claude and Codex outputs do not contain Copilot model pins.
- Codex does not generate deprecated `.codex/rules/` output.
- Generated output contains `MEMORY.md`, workflow directories, templates, prompts, hook scripts, and `quality_score.py` in the shared `.claude/` basis.
- Generated output contains `templates/plan-big.md`, `templates/plan-small.md`, and `templates/session-log.md`.
- Generated output contains `.devcontainer/devcontainer.json`, `.devcontainer/Dockerfile`, `.devcontainer/post-start.sh`, `.devcontainer/state-sync.sh`, and `.devcontainer/restore-root-adapters.sh`.

## MCP Routing

Expected:

- GitHub and Claude JSON MCP files include `semble`, `context-mode`, and `context7`.
- Codex config includes `[mcp_servers.semble]`, `[mcp_servers.context-mode]`, and `[mcp_servers.context7]`.
- Tool-routing policy preserves:
  - direct reads for known paths
  - `rg` for exact literals
  - Semble for semantic discovery
  - context-mode for long outputs and continuity
  - context7 for current external library API documentation
  - no duplicate broad searches

## Hooks

Expected:

- Guardrail scripts exist under `.claude/hooks/scripts/`.
- `protect-files.sh` denies protected files through structured write tools and Bash writes such as `touch .env`.
- Hook config edits through Bash redirection are protected, with Codex denying and GitHub/Claude asking for approval.
- Hook configs invoke `.claude/hooks/scripts/` and pass an explicit target id.
- Generated `run-hook.sh` is executable because Claude and Codex hook commands call it directly.
- Branch creation is allowed only from clean `dev` into `<plan_name>_implementation`, including `checkout -b`/`-B` and `switch -c`/`-C`/`--create`/`--create=<branch>` forms.
- Normal commits are blocked until the current small plan is complete, the session closeout log is completed, `[LEARN]` evidence exists, and a fresh score >= 90 report matches the branch, phase, base ref, merge-base SHA, HEAD SHA, target, dirty flag, and changed-files metadata.
- Commit closeout advances plan state only when the intercepted commit subject can be correlated with `HEAD`.
- PR creation uses `--base dev`, and implementation-branch pushes are blocked until all phases are complete.
- SessionStart/Stop hooks invoke `state-sync.sh` to pull/push mutable AI state on the git-backed `ai-state` branch.
- Missing `context-mode`, `npx`, or `uvx` reports warnings only.
- GitHub Copilot hook config remains native at `.github/hooks/hooks.json` but calls shared `.claude` scripts.
- `.claude/hooks/git-hooks/commit-msg` exists and is executable in generated output.
- With `core.hooksPath` set to the generated `git-hooks` directory, on a `<plan_name>_implementation` branch: a `git commit` with no score report, a score below 90, a stale `content_hash`, an incomplete small plan, a closeout log missing `**Status:** COMPLETED`, or missing `[LEARN]` evidence is each rejected by git; a fully valid commit succeeds.
- The `git ci` alias (`git config alias.ci commit`) and `git -C <path> commit` invoked from outside the repo are rejected identically to a bare invalid `git commit` — there is no command string for either to evade.
- Commits on `dev`/`main` pass through the `commit-msg` hook regardless of ceremony state.
- `git commit --no-verify` bypasses the `commit-msg` hook on an implementation branch — the documented, sanctioned escape.
- `.claude/hooks/git-hooks/pre-push` exists and is executable in generated output; it shares `assert_push_invariants` with `enforce-pr-gate.sh`.
- With `core.hooksPath` set to the generated `git-hooks` directory, pushing a `<plan_name>_implementation` ref with an incomplete small plan, a missing commit-per-phase, or an unacknowledged bypass log is rejected by git and names the phase; a push after all phases are complete succeeds.
- Pushing `dev`/`main`, or deleting a branch (`git push origin :foo_implementation`), passes through `pre-push` regardless of ceremony state.
- `git push --no-verify` bypasses `pre-push` on an implementation branch — the same sanctioned escape as the commit layer.
- `gh pr create --base dev` is checked only at the `PreToolUse` layer; `pre-push` has no PR-creation concept.
- A valid score report with no matching `findings-*.json` report blocks the commit.
- A non-documentation diff without `ponytail_reviewed: true` blocks the commit.
- Any surviving Ponytail finding, including `MINOR`, blocks the commit.
- A Markdown/docs-only diff does not require Ponytail fields.
- A findings report with any `CRITICAL` finding blocks the commit, and the failure message names the finding's title.
- A stale findings `content_hash` (edited since the reviewer generated it) blocks the commit, mirroring the score report's freshness check.
- Two findings reports for the same branch/phase select the newest by `generated_at`, not filename — a lexically-later but older clean report loses to a lexically-earlier but newer report containing a `CRITICAL` finding.
- A findings report with `counts.critical == 0` but `counts.major > 0` allows the commit (the commit gate only checks `critical`) but blocks the push, naming a `MAJOR` finding.
- A findings report generated pre-commit (its `head_sha` is the certified commit's parent) still satisfies the push gate, since `pre-push` accepts any ancestor of the pushed commit, not only an exact match.
- All-zero findings counts (`critical`, `major`, `minor` all `0`) allow both the commit and the push.

## Devcontainer And Git-Backed State Sync

Expected:

- `.devcontainer/` is trackable and generated AI content is ignored by the installer.
- The generated devcontainer forwards `HF_TOKEN` and `HUGGING_FACE_HUB_TOKEN` (for the projects' own Hugging Face use, not AI state sync).
- The generated devcontainer does not require `/dev/fuse` or apparmor overrides, and still includes the `SYS_ADMIN`/`seccomp=unconfined` run args needed by `bubblewrap`.
- `state-sync.sh` resolves the nested `.claude/` repo's remote from `AI_STATE_REMOTE` / `--state-remote` at install time / the outer repo's own `origin` (no separate credential), warns and stays local-only when none is configured, and never fails a hook or session on a sync problem.
- `install_bootstrap.py <repo>` (no bucket flag needed) sets `git -C <repo> config core.hooksPath` to `.claude/hooks/git-hooks`, leaves `commit-msg` executable, and creates+pushes the nested `.claude/` ai-state repo with a `bootstrap:`-prefixed commit; `--state-remote <url>` pushes to that remote instead of `origin` and persists it into `.devcontainer/devcontainer.json`.
- `post-start.sh` runs `state-sync.sh setup` before setting `core.hooksPath`, then `state-sync.sh pull` and `restore-root-adapters.sh`; the checkout inside `setup` already carries the correct executable bits for `.claude/hooks/git-hooks/*` (git preserves them, unlike the retired HF bucket sync).
