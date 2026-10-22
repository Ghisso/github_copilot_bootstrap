# ADR-001: Multi-target bootstrap over native per-platform packaging

**Status:** Accepted
**Date:** 2026-07-08
**Revisit trigger:** annually (next: 2027-07), or earlier if (a) Copilot or Codex ship a plugin-equivalent distribution mechanism, or (b) a Claude-only consumer repo appears.

## Decision

This repo ships one shared `.claude/` basis (skills, agents, hooks, policies, templates) plus thin native adapters for GitHub Copilot (`.github/`), Claude Code (`CLAUDE.md`, `.mcp.json`, `.claude/settings.json`), and OpenAI Codex (`AGENTS.md`, `.codex/`), all rendered from `shared/` by [scripts/generate_targets.py](../scripts/generate_targets.py). There is no Claude plugin/marketplace packaging today.

## Context

[architecture-review-2026-07.md §3.3](../plans/architecture-review-2026-07.md) verified what each platform provides natively as of 2026-07:

- **Claude Code** ships native plan mode, persistent plan files, `/goal` end-state verification, checkpointing, auto-memory, and **plugins/marketplaces as the sanctioned cross-repo packaging mechanism**.
- **Copilot** has no plugin-equivalent; custom agents are native `.github/agents/*.agent.md` files, discovered per-repo, with no cross-repo distribution story beyond copying files.
- **Codex** likewise has no plugin-equivalent; custom agents are `.codex/agents/*.toml` files with the same per-repo, copy-based distribution.

Supporting all three from one source forces lowest-common-denominator (LCD) design: the shared basis can only rely on capabilities every target has (files under a project directory, hook scripts, skill files), never on a Claude-only mechanism like plugin packaging — even though Claude Code alone could distribute this bootstrap more natively that way.

**What the LCD choice costs:** no plugin distribution, no marketplace-driven updates, no `/plugin install` experience for Claude users. In its place, this repo built its own distribution mechanism — the Hugging Face sync machinery (`hf-ai-sync.py`, the devcontainer `post-start.sh` pull, `install_bootstrap.py`) — to move the generated bundle and mutable AI state into and between consumer repos across all three targets uniformly.

**What the LCD choice buys:** one editable source of truth (`shared/`) instead of three diverging copies, one validator (`scripts/validate_targets.py`) instead of three, and identical workflow/hook/quality-gate behavior regardless of which AI tool a consumer repo's contributors use.

## Consequences

- The HF-sync + devcontainer distribution model ([docs/runtime-checks.md](runtime-checks.md#devcontainer-and-hf-sync)) exists **because of** this decision — it is the substitute for the plugin distribution the LCD trade forgoes on the Claude side.
- Every new capability considered for the shared basis is filtered through "can Copilot and Codex do this too", not just "can Claude do this" — this is a deliberate constraint, not an oversight, and shows up as omitted Claude-only features (e.g. native plan-mode integration) throughout `shared/`.
- Consumers who only use Claude Code pay the LCD cost (no plugin ergonomics) for no benefit specific to them; this is the trade-off this ADR makes explicit rather than leaving as a silent inheritance.

## Revisit option (not implemented by this ADR)

If the trigger fires, the recorded option is to add a **plugin-manifest adapter** as one more `generate_targets.py` output — a `plugin.json` plus marketplace layout generated over the same `.claude/` payload, alongside (not instead of) the existing Copilot/Codex adapters. This mirrors [armory](https://github.com/Mathews-Tom/armory)'s pattern of one source tree with generated multi-platform adapters *and* Claude plugin-marketplace packaging. It is **not** a fork of the source tree, and is out of scope for this ADR.
