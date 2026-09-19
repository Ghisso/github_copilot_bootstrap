---
name: 2026-09-19_phase-I-openwiki-enable-and-first-generation
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 11
status: planned
closeout_session_log:
---

# Small Plan: 2026-09-19_phase-I-openwiki-enable-and-first-generation

## Scope

Enable OpenWiki for `github_copilot_bootstrap`, install the Claude Code and Codex integrations
into this checkout, re-probe the guard against the real OpenWiki server, run one host-driven
generation from a Claude Code session, and commit the result. **This phase deliberately ends
there.** No manual documentation or MEMORY content changes. The user inspects `openwiki/**`
after this phase's commit; Phase J does not start without the user's explicit confirmation
recorded in its session log. This is a transition phase, not the template for future
knowledge-refresh phases; the closeout log must say so.

## Steps

### Step I1 — Write the brief and the ignore file

- [ ] **Owner:** `coder`
- **Target files:** create `openwiki/INSTRUCTIONS.md`; create `.openwikiignore`
- **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`,
  `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`
- **Brief scope:** the bootstrap as a source-of-truth plus generated multi-target coding-agent
  system; prioritize `shared/`, `scripts/`, `tests/`, lifecycle, agents, skills, hooks, target
  generation, consumer ownership, state sync, deterministic verification; explain authoring
  repo vs `dist/multi-agent/` vs consumer outer repo vs nested `.claude` ai-state; prefer
  current implementation evidence and tests; do not treat archived plans or session logs as
  current behavior.
- **Ignore intent:** exclude `.claude/`, `.codex/`, `.agents/`, `.github/hooks/` and other
  generated adapters, `dist/`, root `AGENTS.md`/`CLAUDE.md`, caches (`.context-mode/`,
  `.uv-cache/`, `.venv/`), secrets and build output; keep source, tests, and human-authored
  normative docs as evidence; do not exclude `openwiki/` itself.
- **Acceptance criteria:** OpenWiki can still explain the real architecture; no canonical
  source needed to verify claims is hidden; `git check-ignore openwiki/.run.json` succeeds.
- **Verification:** `uv run python .claude/scripts/verify.py fast --format json`

### Step I2 — Install the host integrations into this checkout

- [ ] **Owner:** `coder`; the user approves the project MCP server in Claude Code
- **Target files (written by OpenWiki's installer, then reviewed):** `.mcp.json`,
  `.codex/config.toml` (tracked control-plane), `.claude/skills/openwiki/**` (nested ai-state
  repo), `.agents/skills/openwiki/**` (ignored)
- **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`
- **Execution:** `openwiki integrations install claude --project .`;
  `openwiki integrations install codex --project .`; `openwiki integrations list --project .`
  reports `installed` for both; restart the Claude Code session so it discovers the new skill
  and server.
- **Acceptance criteria:** `.mcp.json` gained exactly `{"openwiki": {"command": "openwiki",
  "args": ["mcp", "--host", "claude"]}}`; `.codex/config.toml` gained exactly the
  `# OPENWIKI:MCP:START … # OPENWIKI:MCP:END` block; existing entries untouched;
  `uv run python scripts/check_runtime.py` passes (Phase G exemption); no `--force`; no
  `*.openwiki-backup-*` directory exists.
- **Verification:** `git diff -- .mcp.json .codex/config.toml`; `check_runtime.py`

### Step I3 — Re-probe the guard against the real server

- [ ] **Owner:** `coder` (Claude Code; repeat in Codex when available)
- **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/knowledge-refresh/SKILL.md`
- **Probes:** (1) `openwiki_begin` with `mode: "init"` → deny before the tool runs (on hosts
  the spike marked O1/O2/O5); record the reason text; (2) with the marker temporarily renamed,
  `openwiki_begin` with `mode: "update"` → deny (not enabled); restore the marker; (3) confirm
  the snapshot directory is empty and `git status --porcelain -- AGENTS.md CLAUDE.md` is empty.
  On a host the spike marked O3/O4, run the documented manual path instead and record it.
- **Acceptance criteria:** observations match the spike's per-host outcome; a divergence
  stops this phase and is recorded — the backstop still blocks a dirty commit.

### Step I4 — Run the first host-driven generation

- [ ] **Owner:** `coder` (Claude Code session)
- **Target files:** generated `openwiki/**` except `openwiki/INSTRUCTIONS.md`; nothing else
- **Required Skills:** `shared/skills/knowledge-refresh/SKILL.md`, then OpenWiki's installed
  `.claude/skills/openwiki/SKILL.md`
- **Execution:** `openwiki_begin` with the absolute repository root and `mode: "update"`;
  confirm adapters clean at once; if it reports `noop` on an empty wiki or refuses `update`,
  stop and report — never `init`. Otherwise submit a plan (include `/openwiki/quickstart.md`),
  loop pages, `openwiki_finish`. Keep the run bounded.
- **Acceptance criteria:** adapters byte-identical to pre-run; `openwiki-update.yml` absent;
  changes confined to `openwiki/**`; `.claims/`, `.last-update.json`, `.page-manifest.json`
  present; `openwiki/.run.json` absent after `finish` (or present and ignored if interrupted);
  no secrets or AI-state content in output; representative claims verified against source.
- **Verification:** `git status`, `git diff --stat`;
  `uv run python .claude/scripts/verify.py phase --format json` (`VFY-OPENWIKI-001` PASS)

### Step I5 — Review

- [ ] **Owner:** `reviewer`
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `documentation` (`ponytail`
  only if a script changed)
- **Review focus:** MCP entries are exactly OpenWiki's managed form; no credential or private
  config in Git or ai-state; `.openwikiignore` hides state without hiding evidence; generated
  content subordinate to source/tests/policy; the brief does not treat archived records as
  current.

## Verification

```bash
openwiki integrations list --project .
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`, names this a transition phase, and records the tool-call sequence and probe results
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged (`openwiki/**`, `.openwikiignore`, `.mcp.json`, `.codex/config.toml`) and `git diff --cached` reviewed; `openwiki/.run.json` not staged
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Root adapters byte-stable across the run; no scheduled workflow created
- [ ] **Stop.** Phase J starts only after the user inspects `openwiki/**` and confirms in writing

## Pause Checkpoint

(template text, identical to Phase F)
