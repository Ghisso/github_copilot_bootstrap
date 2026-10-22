---
name: 2026-07-18_phase-A-vendor-ponytail
type: small-plan
parent_plan: ponytail-integration
phase_index: 1
status: complete
closeout_session_log: plans/2026-07-18_ponytail-integration-closeout.md
---

# Small Plan: 2026-07-18_phase-A-vendor-ponytail

## Scope

Add a pinned, license-compliant copy of Ponytail's portable coding and review
skills to the editable `shared/` source of truth. Consumer projects must receive
the skills through normal target generation and installation without network
access or a global plugin install.

## Steps

- [ ] Create `shared/third_party/ponytail/UPSTREAM.md` with upstream repository,
  release `v4.8.4`, commit `bc9ee94`, copied paths, local transformations, and
  the explicit upgrade procedure.
- [ ] Copy the upstream MIT license verbatim to
  `shared/third_party/ponytail/LICENSE`.
- [ ] Add upstream-derived `shared/skills/ponytail/SKILL.md` and
  `shared/skills/ponytail-review/SKILL.md`.
  - Preserve the behavior, ladder, safety boundaries, and review format from
    the pinned release.
  - Add only the bootstrap's required `visibility: public` metadata and a
    provenance note that does not weaken trigger phrases.
  - Do not import Ponytail's benchmark, status-line, runtime state, or plugin
    hooks.
- [ ] Modify `scripts/generate_targets.py` so third-party notice and license
  render to `.claude/third_party/ponytail/` while the two skills continue
  through the existing shared skill renderer.
- [ ] Extend `scripts/validate_targets.py`.
  - Require both skills and the downstream license/provenance files.
  - Assert the pinned upstream version/commit.
  - Assert the skill count and Codex `[[skills.config]]` entries include both
    Ponytail skills.
  - Assert Claude and Copilot adapters discover the same canonical skill paths.
  - Assert no generated file references a workstation plugin directory.
- [ ] Add deterministic fixture/hash checks for the vendored upstream files.
  A changed vendored file must require updating provenance deliberately rather
  than silently drifting from the pinned release.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
