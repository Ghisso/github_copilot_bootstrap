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
- Step G5 redone under the marker rule: `is_third_party_skill_dir` requires both
  the `skills/openwiki` shape and the marker file on disk; refresh preservation
  and drift exemption apply only then, and the bootstrap-root mirror follows
  the live `.agents` marker. Tests prove the unmarked copy is still overwritten
  and compared, the marked copy is preserved and exempt. 50 installer tests
  pass; `check_runtime.py` PASS on this marker-free checkout.
- Steps G1, G3, G4 done by the hook coder: `openwiki-guard.py` (stdlib, 3.9)
  and `openwiki-guard.sh`; Claude Code wiring on `PreToolUse`, `PostToolUse`
  and `PostToolUseFailure`; Codex wiring on `PreToolUse`, `PostToolUse` and
  the `Stop` hook (adaptation O2); runner and its test deleted; Dockerfile
  smoke line replaced with the version pin check and a non-interactive start;
  real-binary MCP handshake test observed `serverInfo.version 0.5.2` and the
  six tools. 18 guard tests. Deviations accepted: the guard computes its own
  root three directories up with a lexical path (the isolated-hook test
  pattern relies on symlinks); no `deny_pretool` call (same as
  `protect-files.sh`); a stale snapshot that cannot be healed denies the new
  call; the `post` success line format is the coder's.
- VERIFY round 1: the overlay refresh pruned the obsolete installed runner
  copy; `docs/runtime-checks.md` guardrail list gained `openwiki-guard.sh`;
  the skill's mention of the forbidden workflow file was reworded so the
  reference validator does not demand it exist. `validate_targets.py` exit 0,
  `check_runtime.py` exit 0, plan lint exit 0; `verify.py phase` FAIL on three
  tests that encode the pre-guard hook wiring (Codex single Stop handler,
  Claude lifecycle shape, routing-group fixture), handed to the hook coder.
- Observed: the overlay refresh reported `.claude/.gitignore` as an obsolete
  generated file and removed it; `state-sync.sh` recreated it with `.cache/`
  ignored, so the guard's snapshot directory stays out of the nested
  repository. Pre-existing behaviour, recorded for follow-up.
- Three tests updated to state the real invariants with the guard present
  (Codex `Stop` keeps the local wrapper plus the payload-free restore; Claude
  keeps one `Stop` handler and gains the `PostToolUseFailure` group; the
  routing fixture has four groups). VERIFY round 2: `validate_targets.py` exit
  0, `check_runtime.py` exit 0, plan lint exit 0, `verify.py phase` PASS with
  1743 tests.

## Review findings and dispositions

Round 1 (Phase F3 reviewer reused; profiles `code`, `architecture`,
`security`, `tests`, `ponytail`, `documentation`): 1 CRITICAL, 1 MAJOR, 0
MINOR. Gate FAIL. Both reproduced against the real guard script.

- CRITICAL code — a manifest that is valid JSON but lacks its `adapters` or
  `workflow` keys was treated like an explicit "file was absent" record, so
  `post` (and `pre`'s heal step) deleted root `AGENTS.md` and `CLAUDE.md` and
  reported success. On Codex `Stop` runs `post` every turn, so a corrupted
  cache file would have removed real repository content. Fix: validate the
  manifest shape first; absence must come only from an explicit
  `present: false`; a malformed manifest makes `post` exit 2 touching nothing
  and `pre` deny.
- MAJOR security — a symlinked adapter was followed: `pre` copied the link
  target's bytes into the repo-local cache, and `post` flattened the link into
  a regular file. Fix: a symlinked adapter or workflow path is undeterminable;
  `pre` denies naming it, `post` refuses it; recorded in the residual limits.
- Dropped by the reviewer after reproduction: a suspected repeat of the Phase
  F3 symlinked-root defect; here both sides open the filesystem, so the two
  spellings reach the same file.
- Noted, not a finding: the verifier's "staged as new" check for the workflow
  file accepted any staged change. Tightened to `--diff-filter=A` by the
  verifier coder as a precision fix.

Held up on review: per-host wiring matches the spike; the real-binary smoke
test has no skip path; the marker-gated ownership predicate does not confuse
`skills/openwiki-review`; docs match the code and the spike.

## [LEARN] Entries

- [LEARN:security] Carried from the retired Phase A runner so nine review
  rounds survive as design: a guard that fails closed on ordinary activity
  gets routed around, so allow-list the one surface you own instead;
  detection at commit time is not prevention, so pair the backstop with a
  guard at the moment of the write; and never let a child process you did not
  spawn define your safety boundary. The host-driven guard applies all three:
  it wraps one MCP tool, snapshots before and restores after, and the
  verifier refuses the commit if anything slipped through.
- [LEARN:workflow] Ownership of a directory two parties write must key on a
  fact only the intended owner produces. Path shape alone froze this
  repository's own installed skill on stale text; keying on OpenWiki's own
  `.openwiki-install.json` marker made the hand-over automatic and testable.
- [LEARN:testing] A validator that treats every backticked repository path as a
  file that must exist cannot describe a forbidden file. Name such a file
  without a repository prefix, or the reference check demands its presence.
- [LEARN:workflow] A required real-binary check needs the binary in the
  environment that runs closeout, not only in the devcontainer image. Install
  the pinned version where the phase actually closes out and record that in
  the log, or the closeout runner fails on the first item.

## Verification

(pending: runner summary lines pasted at closeout)

- optional 1: (pending)

## Open Questions / Next Steps

(pending)
