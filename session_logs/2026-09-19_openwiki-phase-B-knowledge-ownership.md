# OpenWiki Phase B: Knowledge Ownership and Agent Access

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-19_phase-B-openwiki-knowledge-ownership-and-agent-access.md`

## Goal

Encode who owns which kind of knowledge, add one narrow OpenWiki skill wrapping the Phase A
runner, and add short provider-neutral root guidance. This phase does not change planner,
orchestrator, documenter, learn, or onboard behavior; Phase C does that on top of this contract.

The central rule: **OpenWiki is derived context, not authority.**

## Approach

- One ownership rule set, not several competing definitions across policy, skill, and root files.
- The skill wraps `.claude/scripts/openwiki_refresh.py` and never reaches for raw `openwiki --init`.
- Rebaseline means preserving `openwiki/INSTRUCTIONS.md`, removing the rest of `openwiki/**`, and
  running the ordinary runner again.
- Root guidance stays short; detail lives in the skill and the policies.

## Inherited Context From Phase A

Phase A shipped the runner with documented residual limits that the skill must not contradict:

1. A write landing outside the repository is not detected (Phase E covers this).
2. Inside a validated Git directory, files off the execution allowlist are not fingerprinted.
3. A `gitdir:` pointer outside the tracked tree escapes the mechanism.
4. `.claude/.cache/` is excluded by deliberate exception.
5. Concurrent agent-session writes to `.claude` cause a fail-closed failure naming unrelated
   files; re-run when the checkout is quiet. This is why the skill must require serial execution.

## Progress

- Phase A committed and pushed as `e9cf57d`; both repositories clean.
- Big plan `current_phase` advanced to Phase B by the branch hooks.
- B1, B2, B3 implemented. One review round; one MAJOR found and fixed.

## Completed Work

- **B1 — canonical ownership contract.** One new `## Knowledge Ownership` section in
  `shared/policies/workspace.instructions.md`, a five-layer table plus two closing rules.
  `workflow.instructions.md`, `shared/MEMORY.md`, `docs/architecture.md`, `README.md`
  (one hop via `docs/architecture.md`), and the skill all link to it rather than restate it.
  The canonical home was chosen to match the existing "one table, everyone links here"
  precedent already used for Review Profiles in the same file.
- **B2 — `shared/skills/openwiki/SKILL.md`.** Narrow trigger with explicit negative scope
  ruling out README/docs writing and other wiki tools. Wraps `.claude/scripts/openwiki_refresh.py`
  only; never raw `openwiki`, never `--init`, including in the rebaseline rule. No test changes
  were needed: skills are discovered by directory glob and the validator already exercises the
  real `shared/skills/` tree.
- **B3 — root guidance.** One line each in authoring `AGENTS.md`, `CLAUDE.md`, and the shared
  body of `render_root_guidance()` so every target receives it.

## Verification

- `scripts/generate_targets.py --all`: passed.
- `scripts/validate_targets.py`: PASS.
- `scripts/check_runtime.py`: passed after a local-only self-install.
- `verify.py fast`: PASS.
- Focused skill and root-guidance tests: 63 passed, 97 deselected.
- Full suite: 1582 passed.
- Root guidance budgets, measured on the generated copies the gate checks:
  `CLAUDE.md` 64/200 lines, `AGENTS.md` 9398/16384 bytes.
- Authoring root files byte-stable across a real self-refresh, confirmed by hashing and
  independently by reading `install_bootstrap.py`'s preserve logic.

## Review

Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.

Round 1 result: FAIL on one MAJOR. Root `AGENTS.md` restated the ownership rule instead of
copying it, and drifted three ways: `shared/` instead of `source`; the authoring-source skill
path `shared/skills/openwiki/SKILL.md` instead of the installed `.claude/skills/openwiki/SKILL.md`
that every other reference uses and that skill loading actually reads; and the required
"never commit OpenWiki's own root snippet" clause omitted. The generated consumer artifact was
correct throughout, so only the hand-authored contributor-facing file was affected.

Fixed, and confirmed by a scoped confirmation pass: gate result PASS, empty findings. The
confirmation independently re-hashed the generated artifact (`86089f8e823b54445e8b2c63b427
1802cfda3dfc5d6fadff90555a258084ed4e`, 9398 bytes, 120 lines, unchanged) and verified the
`.claude/bootstrap-root/AGENTS.md` mirror is back in sync.

Everything else passed on independent verification: the ranking is strictly linear with no
circular authority; the skill's serial-execution reason matches the runner's module docstring
word for word; `--init` appears nowhere including examples; failure guidance correctly says
retry rather than clean up; the trigger is narrow without being too narrow; and no model-backed
OpenWiki execution reached `verify.py`, hooks, the installer, state-sync, post-commit, or CI.

## [LEARN] Entries

- [LEARN:quality] Editing a live root adapter leaves `.claude/bootstrap-root/AGENTS.md`, the
  mirror `verify.py` diffs the live adapter against, out of sync, and `verify.py` then fails
  with `ValueError: receipt metadata control-plane provenance is invalid`, which names neither
  the stale file nor the remedy. `install_bootstrap.py . --allow-self --local-only` clears it.
  The resync is needed before `verify.py`, not only before `check_runtime.py`.
- [LEARN:review] When the same sentence must appear in two files, copy it; do not retype it.
  Retyping produced three drifts in one line, one of which pointed agents at
  `shared/skills/`, an authoring path no skill-loading runtime reads. A near-restatement is
  more dangerous than an obvious duplicate because it reads as deliberate.
- [LEARN:workflow] When one contract must appear in many places, give it a single canonical
  home and have every other location link to it. Pick the home by existing precedent: this
  repository already used "one authoritative table, everyone links here" for Review Profiles,
  so the ownership table went in the same file.

## Follow-Up Observation (not acted on)

`render_root_guidance("openai-codex")` in `scripts/generate_targets.py` has no call site.
Codex's root guidance is served by the `multi-agent` output, which does carry the new line, so
no target misses it and this phase is unaffected. Confirmed independently by the reviewer.
Worth cleaning up in its own change.

## Follow-Up: verify.py error message (pre-existing, out of scope)

Traced by the reviewer to a real, narrow inconsistency rather than a vague complaint.
`bootstrap_root_fingerprint_diagnostics()` (`verify.py:620`) already computes a precise
`{"path", "side", "category"}` diagnostic, and the closeout-enforcement path uses it to produce
an actionable message. The generic receipt-shape validator (`verify.py:220-273`) only re-checks
already-serialized field shapes and has no access to live adapter diagnostics by construction,
so it degrades to a bare `ValueError`. Classified MINOR, `code` profile, pre-existing:
`shared/scripts/verify.py` is not in Phase B's diff. Suggested fix is to refuse to write a
receipt with an empty `root_fingerprint` at generation time, where the good message is
available, instead of deferring to the later, worse one. Recorded in `.claude/MEMORY.md`.
