---
name: 2026-09-24_phase-E-sidecar-knowledge-refresh
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 5
status: planned
closeout_session_log:
---

# Small Plan: Phase E — Sidecar Knowledge Refresh

## Scope

The big plan's final knowledge-refresh phase, as defined by the
Knowledge-Refresh Final Phase rule in `shared/policies/workflow.instructions.md`.
Refresh the OpenWiki layer, then audit stale claims that assume every
consumer installation owns the full agent harness, or that a batch update
stops at the first failure.

Add no implementation scope unless the audit exposes a concrete defect.

### Required Skills

- `shared/skills/knowledge-refresh/SKILL.md`
- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/learn/SKILL.md`
- `shared/skills/ponytail/SKILL.md` — `full`, only for a required code correction

## Steps

- [ ] **1. Refresh OpenWiki.**
  - **Owner:** `documenter`
  - Follow `.claude/skills/knowledge-refresh/SKILL.md`: call OpenWiki's own
    MCP tools with `mode: "update"`. Never run an init, and never create a
    scheduled workflow.
  - The `openwiki` MCP server must be connected before this step. Check it
    with `/mcp`. A provider or authentication failure blocks this phase until
    it is fixed; it is never skipped.
  - Known cause of a failed connection: a cold start. On 2026-09-23 and
    2026-09-24 the server timed out within a minute of WSL booting, when
    every MCP server was slow (`semble` took 28 s instead of about 1 s), and
    it passed Claude Code's 30-second startup limit (`MCP_TIMEOUT`, default
    `30000` ms). Later starts in the same boot took 1.3-7 s. Reconnect it
    with `/mcp`, or start a new session.
  - To prevent the cold-start failure, set `MCP_TIMEOUT=90000` in the
    environment that starts VS Code's WSL server, for example in
    `~/.profile`. The docs do not confirm that the `env` key in
    `settings.json` changes this startup limit, or that the VS Code extension
    reads it, so read the connection log after the next WSL boot:
    `~/.cache/claude-cli-nodejs/-home-ghisso-work-github-copilot-bootstrap/mcp-logs-openwiki/`.
  - `Executable not found in $PATH: openwiki` is a different failure: the
    client that started the server could not find `openwiki` on its `PATH`.
    The current devcontainer image installs `openwiki@0.5.2`, so rebuild an
    older container, or add `~/.local/bin` to the launching client's `PATH`
    on the host.

- [ ] **2. Review the generated diff.**
  - **Owner:** `documenter`
  - Treat generated pages as descriptive context, not policy. Source, tests,
    and policies stay authoritative.
  - Never hand-edit a generated page. Never stage `openwiki/.run.json`.

- [ ] **3. Audit stale claims.**
  - **Owner:** `documenter`
  - Surfaces: `README.md`, `docs/architecture.md`, `docs/target-mapping.md`,
    `docs/runtime-checks.md`, `docs/smoke-tests.md`, `shared/policies/`,
    skills that describe installer ownership (including
    `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`), the docstrings
    and `--help` text of `scripts/install_bootstrap.py` and
    `scripts/update_consumers.py`,
    `.claude/instructions/project-context.instructions.md`, and
    `.claude/MEMORY.md`.
  - Topics: consumer installation, `.claude` and `.agents` ownership, update
    behavior, batch failure handling, supported clients, Copilot VS Code
    versus CLI scope, VS Code session types, hooks, local Git exclusion,
    worktree limits, license notices for vendored skills, generated target
    structure (`dist/sidecar/`), and any assumption that every consumer uses
    a full install.
  - Record every surface and its outcome under
    `## Stale-claims surfaces checked` in the closeout session log.

- [ ] **4. Correct normative documentation.**
  - **Owner:** `documenter`
  - Keep the distinction explicit:

    ```text
    full install    -> bootstrap owns the harness
    sidecar install -> local personal overlay inside a team-owned harness
    ```

- [ ] **5. Record reusable lessons only.**
  - **Owner:** `documenter`
  - Run LEARN for reusable implementation knowledge. Do not store transient
    phase details as durable memory.

- [ ] **6. Complete the final lifecycle checks.**
  - **Owner:** `orchestrator`
  - Run verification, review, and closeout as the workflow requires.

## Acceptance Criteria

- No documentation implies that every consumer installation owns the full
  agent harness.
- Full and sidecar modes are documented with correct ownership boundaries.
- No documentation says that a batch update stops at the first failed
  target.
- The generated knowledge layer reflects the sidecar lifecycle.
- No generated OpenWiki page is hand-edited.
- No unrelated feature scope is introduced.

## Verification

```bash
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py fast --format json
```

## Review Profiles

Every multi-file diff is control-plane/high-risk
(`shared/policies/workspace.instructions.md`, Review Profiles), so this
phase uses the full set:

- `documentation`
- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
