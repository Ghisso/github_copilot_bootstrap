# Session: OpenWiki Phase I — enable and first generation

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-I-openwiki-enable-and-first-generation.md`
**Status:** IN-PROGRESS

This is a transition phase, not the template for future knowledge-refresh
phases. It enables OpenWiki in this checkout for the first time and proves
one host-driven generation; later refreshes follow the small
knowledge-refresh shape in `workflow.instructions.md`.

## Goal

Enable OpenWiki for `github_copilot_bootstrap`: write the brief and ignore
file, install the Claude Code and Codex integrations once, re-probe the guard
against the real server, run one host-driven `update` from a Claude Code
session, and commit. Stop there; the user inspects `openwiki/**` before
Phase J.

## Work Log

- Phase started 2026-09-21 after Phase H's completion commit `cf6c4ac`.
- Plan pre-check against the installed `openwiki@0.5.2` package: the
  `.openwikiignore` file is honored (`dist/agent/openwiki-ignore.js`);
  `/openwiki/INSTRUCTIONS.md` is read as the user-authored brief and never
  rewritten by routine runs; the integration installer writes the `.mcp.json`
  entry `{"command":"openwiki","args":["mcp","--host","claude"]}`, an
  `# OPENWIKI:MCP:START … END` block in the Codex config, and skill bundles
  with `.openwiki-install.json` markers under `.claude/skills/openwiki` and
  `.agents/skills/openwiki`; `openwiki/.run.json` was already ignored by
  `.gitignore:38`. All plan facts held.
- Plan correction before IMPLEMENT: Steps I3 and I4 call OpenWiki's MCP
  tools. The `coder` agent's tool list has no OpenWiki server, and a running
  Claude Code session does not discover a server added to `.mcp.json`, so
  both steps are owned by the orchestrator on the main thread in a session
  started after Step I2, once the user approves the project server.
- Step I1 (Phase H coder reused): created `openwiki/INSTRUCTIONS.md` (the
  four-way split of authoring `shared/`, generated `dist/multi-agent/`, a
  consumer's outer repository, and the nested `.claude` ai-state repository;
  priorities; the rule that `.claude/plans/`, `.claude/session_logs/`,
  `docs/2026-*`, and root `plans/` are historical evidence, not current
  behaviour) and `.openwikiignore` (excludes `dist/`, `.claude/`, `.codex/`,
  `.agents/`, `.github/hooks/`, `.devcontainer/` (an untracked self-install
  overlay here), root `/AGENTS.md` and `/CLAUDE.md`, caches, the
  context-mode provenance secret, and Python build output; keeps source,
  tests, undated docs, and `openwiki/` itself). Ignore syntax confirmed
  gitignore-compatible with one difference: OpenWiki matches
  case-insensitively by design. `verify.py fast` PASS.
- Step I2: `openwiki integrations install claude --project .` and
  `... codex --project .` both exit 0 with no unmanaged-skill warning (the
  Phase H rename freed both paths). `openwiki integrations list --project .`
  reports `installed` for `claude` and `codex`. Diffs are exactly the
  additions the plan names; `semble` and `context-mode` entries untouched;
  no `*openwiki-backup*` directory; both bundles carry
  `.openwiki-install.json`; `check_runtime.py` exit 0 (Phase G exemption
  held); `validate_targets.py` exit 0; the installer did not touch
  `AGENTS.md`/`CLAUDE.md`.
- Discovery after Step I2 (recorded as Step I2b in the plan): the self
  overlay refresh `install_bootstrap.py . --local-only --allow-self` exits 1
  with `Refusing .agents takeover ... .claude/bootstrap-root/.agents/skills/openwiki ...`.
  No such mirror directory exists; `_agents_conflicts` labels every
  difference with the mirror prefix, and the difference is OpenWiki's
  marker-claimed live bundle, which `_agents_tree` walks without consulting
  `is_third_party_skill_dir`. `verify.py fast` fails with
  `receipt metadata control-plane provenance is invalid` because the live
  root adapters OpenWiki's installer edited no longer match their
  `.claude/bootstrap-root/` mirror. Phase G exempted the bundles from
  `check_runtime.py` drift only. Step I2b fixes the installer (and the
  verifier's fingerprint if `.agents` is an owned path) with regression
  tests; `ponytail` added to the review profiles.

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: paste `verify closeout --format text` summary lines)

- optional 1: (pending)

## Open Questions / Next Steps

- After Step I2b: restart the Claude Code session so it discovers the
  `openwiki` MCP server and OpenWiki's installed `openwiki` skill; approve the
  project server when asked; then the orchestrator runs Steps I3 and I4 on
  the main thread.
