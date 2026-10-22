# Devil's Advocate Review: Sidecar Onboard Plan

**Date:** 2026-10-22  
**Reviewer:** Independent GPT-6 Sol subagent, high effort  
**Scope:** `.claude/plans/sidecar-onboard-and-validator.md` and its three small plans  
**Method:** `shared/skills/devils-advocate/SKILL.md`; checked the handoff, workflow rules, validator, and hook-test source

| Concern | Risk | Alternative | Recommendation | Disposition |
| --- | --- | --- | --- | --- |
| The sidecar phase required the validator before the missing-`pytest` defect was fixed. | HIGH | Put the validator fix first. | CHANGE | Validator is now Phase A; sidecar is Phase B. Required closeout uses the devcontainer or a full toolchain, and Phase A's validator command provisions `pytest`. |
| A symlinked `.ai-bootstrap/` state path can write outside the ignored folder. | HIGH | Refuse symlinked, tracked, or escaping destinations before writing. | CHANGE | The sidecar skill plan now requires these refusals and a negative source-contract check; optional native acceptance exercises a symlink to a tracked file. |
| One negative case cannot prove the generated skill check covers case variants, both roots, and copy divergence. | MED | Inject each violation separately. | CHANGE | Phase B now requires each negative case and restoration after it. |
| Direct execution of `tests/test_hook_gates.py` runs five smoke tests, although the file has many more pytest tests. | MED | Name the smoke scope or run the full file. | INVESTIGATE | The plan preserves the existing five-test check as the smallest requested fix, names its scope, and relies on the canonical phase verifier for full test-suite coverage. |

**Second pass:** The reviewer confirmed the first three changes and the smoke-test decision. It identified a remaining host-environment closeout gap; the plan now names the devcontainer or full toolchain for required checks and provisions `pytest` in Phase A's validator command.

**Open plan findings:** None after the revisions. The old-build upgrade fixture and interactive symlink refusal remain implementation acceptance checks, not planning evidence.
