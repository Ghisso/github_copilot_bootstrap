# Session: OpenWiki Phase G — host-driven guard

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-G-openwiki-host-driven-guard.md`
**Status:** IN-PROGRESS

## Goal

Replace the Phase A subprocess runner with a deterministic hook guard around
OpenWiki's `openwiki_begin` MCP tool (snapshot the root adapters before, restore
them byte-for-byte after), fold the managed-state backstop into `VFY-GEN-001`
and the commit gate, fix the devcontainer smoke line, add a real-binary MCP
handshake test, make OpenWiki-installed skill bundles third-party-owned, and
remove every runner mention. Built against the Phase F spike evidence: Claude
Code fires `PreToolUse`, `PostToolUse`, and `PostToolUseFailure`; Codex fires
`PostToolUse` on success only (adaptation O2).

## Work Log

- Phase started 2026-09-21 after Phase F3's completion commit `2cc8ca4`.
- Agent assignment: the Phase F3 git-gate coder (hook conventions fresh in
  context) owns the guard hook, runner retirement, devcontainer smoke line and
  MCP handshake test, and the generator/validator edits (Steps G1, G3, G4, plus
  the generator string from G6); the Phase F2 script coder (verifier expert)
  owns the backstop in `verify.py` (Step G2); a fresh coder owns the
  third-party skill-bundle ownership (Step G5); the Phase F2 prose coder owns
  the documentation rewrite (Step G6 prose).
- Environment: this session runs outside the devcontainer and had no `openwiki`
  binary, which the required real-binary handshake test needs (it must not
  skip). Installed the pinned `openwiki@0.5.2` globally with npm and linked its
  binary into `~/.local/bin`, which is on PATH; `openwiki integrations list
  </dev/null` exits 0. Reversible with `npm uninstall -g openwiki` and removing
  the link.
- Step G2 done by the verifier coder: `openwiki_managed_state_violations(root)`
  reads the two adapters and asks git only about the workflow file and
  `openwiki/.run.json`; `VFY-GEN-001`'s phase check FAILs first on any
  violation; `gate_receipt_errors` adds one `openwiki-managed-state:` error per
  violation under `exact` only. 19 new tests on real temporary repositories;
  one docs row. No check ID or schema change.
- Step G6 prose done by the prose coder across seven files; three stale
  "the runner" claims beyond the two named sections were also corrected. The
  skill now states per-host restore coverage and the manual `post` command.
  The coder saw `verify.py fast` fail with `receipt metadata control-plane
  provenance is invalid`; expected after editing root `AGENTS.md`/`CLAUDE.md`
  (their installed mirror under `.claude/bootstrap-root/` is stale until the
  self overlay refresh at VERIFY), not a defect.
- Step G5 first draft preserved `skills/openwiki` on every refresh. The coder
  reported the conflict: the bootstrap still generates that skill (G6 rewrites
  it in this phase, Phase H renames it), so this repository's own installed
  copy would have frozen on the old text. Decision: third-party ownership is
  gated on OpenWiki's own marker file `.openwiki-install.json`; recorded in
  the plan's Step G5.

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: runner summary lines pasted at closeout)

- optional 1: (pending)

## Open Questions / Next Steps

(pending)
