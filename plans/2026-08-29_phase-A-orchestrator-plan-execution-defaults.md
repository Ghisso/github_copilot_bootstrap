---
name: 2026-08-29_phase-A-orchestrator-plan-execution-defaults
type: small-plan
parent_plan: orchestrator-plan-execution-defaults
phase_index: 1
status: in-progress
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
---
# Small Plan: 2026-08-29_phase-A-orchestrator-plan-execution-defaults
## Scope
Make existing-plan execution a standard orchestrator behavior so users do not need to repeat a long prompt. Make planner use conditional, improve delegation context reuse, strengthen language compliance, and enable the already-supported bounded Context Mode repository-directory indexing path through the existing guarded filter.
This is control-plane/high-risk work. Use Ponytail in `full` mode. Keep one phase and keep the implementation small.
### Required Skills
- `.claude/skills/ponytail/SKILL.md` — `full`
- `.claude/skills/ponytail-review/SKILL.md`
- `.claude/skills/humanize/SKILL.md` — `edit`, docs profile
- `.claude/skills/commit/SKILL.md` at closeout
### Primary Files
Modify:
- `shared/agents/orchestrator/prompt.md`
- `shared/policies/workflow.instructions.md`
- `shared/policies/workspace.instructions.md`
- `shared/policies/tool-routing.instructions.md`
- `shared/policies/agent-reporting.instructions.md`
- `shared/hooks/scripts/context-mode-mcp-filter.mjs`
- `scripts/generate_targets.py`
- `scripts/validate_targets.py`
- focused existing Context Mode filter/runtime tests
- `README.md`
Modify only if inspection proves necessary:
- `shared/agents/documenter/prompt.md`
- `scripts/check_runtime.py`
Regenerate `dist/multi-agent/**`. Do not hand-edit generated output.
## Verified Context Mode Facts
Re-check the pinned runtime before editing. Current verified `1.0.169` behavior:
- directory `ctx_index` exists;
- defaults are `maxDepth: 5`, `maxFiles: 200`, `respectGitignore: true`, `followSymlinks: false`;
- upstream also has default extension filtering and noisy-path exclusions;
- root and per-file Read deny-policy checks are applied;
- directory indexing creates per-file source labels derived from the supplied source prefix;
- relevance `ctx_search` uses LIKE-mode source matching;
- changed indexed file-backed sources can auto-refresh on later search.
Current bootstrap filter keeps:
```text
PINNED_VERSION = 1.0.169
INDEX_ARGS = content, path, source
```
and already enforces traversal rejection, canonical containment, root-symlink rejection, and regular-file checks. It currently contains one explicit directory denial.
Do not broaden the plan if these facts still hold.

## Steps
- [ ] **1. Make approved existing-plan execution explicit in the orchestrator.**
  - Owner: `coder`
  - Modify `shared/agents/orchestrator/prompt.md`.
  - Preserve lifecycle ownership and all gates.
  - Existing-plan PRE-FLIGHT must:
    - read `README.md`;
    - read applicable workflow/tool-routing/reporting instructions;
    - read selected big plan and current small plan;
    - inspect current branch/Git/source state because plans can become stale.
  - Change PLAN:
    - no implementation-ready plan -> normal planner flow;
    - approved existing plan that remains implementation-ready -> skip planner.
  - Before every new phase, inspect completed-phase implementation outcomes and relevant verifier/reviewer findings.
  - If new evidence/constraints/regressions/architecture decisions materially affect remaining work:
    - invoke one planner;
    - pass a compact evidence packet;
    - revise affected future phases only;
    - do not reopen completed or unaffected scope.
  - Otherwise proceed directly to IMPLEMENT.
- [ ] **2. Enable guarded repository-directory `ctx_index` with the smallest filter change.**
  - Owner: `coder`
  - Modify `shared/hooks/scripts/context-mode-mcp-filter.mjs`.
  - Keep unchanged:
    - pinned version gate;
    - four-tool allow-list;
    - `INDEX_ARGS = content,path,source`;
    - one-of content/path validation;
    - source length bound;
    - traversal rejection;
    - path canonicalization;
    - repository containment;
    - root symlink rejection.
  - Replace only the current directory prohibition with acceptance of a real contained directory.
  - Final path policy should be equivalent to:
    ```text
    contained regular file -> allow
    contained real directory -> allow
    everything else -> deny
    ```
  - Do not add filter arguments for `include`, `exclude`, `maxDepth`, `maxFiles`, `extensions`, `respectGitignore`, or `followSymlinks`.
  - Do not implement another directory walker.
- [ ] **3. Add focused security/regression coverage for the directory path.**
  - Owner: `coder`
  - Extend existing Context Mode filter/native MCP fixtures; do not create a new framework.
  - Required cases:
    1. repository root directory -> allowed;
    2. contained subdirectory -> allowed;
    3. contained regular file -> still allowed;
    4. outside-repository directory -> denied;
    5. traversal path -> denied;
    6. root symlink to contained target -> denied;
    7. root symlink to outside target -> denied;
    8. non-file/non-directory path where fixture supports it -> denied;
    9. `respectGitignore` argument -> denied;
    10. `maxDepth` argument -> denied;
    11. `maxFiles` argument -> denied;
    12. tool-list/version-gate behavior -> unchanged.
  - If existing tests already run a pinned Context Mode process, add one integration case:
    - guarded `ctx_index` on a small temp repo directory;
    - confirm success;
    - `ctx_search` for a known marker.
  - If native integration is unavailable in CI, record it as not run instead of building a new harness.
- [ ] **4. Add bounded project indexing to orchestrator retrieval pre-flight.**
  - Owner: `coder`
  - Update `shared/agents/orchestrator/prompt.md` and `shared/policies/tool-routing.instructions.md`.
  - Preserve direct reads for known authoritative paths.
  - After README/instructions/plans/Git-state reads, when broader repository discovery is useful:
    - if guarded Context Mode is available, issue one directory `ctx_index`;
    - use the absolute repository root;
    - use stable source `project:<repository-name>`;
    - pass no directory-policy override argument.
  - Use focused `ctx_search` only when useful.
  - Reuse discovered facts in later evidence packets.
  - Do not automatically index again for every subagent.
  - At later phase boundaries, perform another directory index only when discovery of newly created/unindexed files is materially useful.
  - Indexing is nonblocking:
    - unavailable/error/capped -> continue with direct read/`rg`/Semble;
    - do not raise cap automatically;
    - do not ask the user merely because the 200-file cap was reached.
  - Files that will be edited must still be read normally before modification.
  - State explicitly that Git/filesystem state is authoritative over cached index content.
- [ ] **5. Make delegation context reuse explicit without weakening role isolation.**
  - Owner: `coder`
  - Update the existing Delegation Rules.
  - Evidence packets must include:
    - phase/task;
    - plan requirements/non-goals;
    - known files/symbols;
    - verified invariants;
    - relevant previous-phase findings/outcomes;
    - settled decisions/rejected approaches;
    - required skills/review profiles;
    - verification commands;
    - relevant artifact paths;
    - useful Context Mode source/search terms or Semble results already established;
    - `.claude/instructions/agent-reporting.instructions.md` pointer.
  - Prefer derived facts + exact source locations over raw retrieval dumps.
  - Reuse/continue an existing role when the follow-up is the same role/phase and context remains valid.
  - Spawn fresh for independent reviewer/verifier judgment, materially stale context, unavailable prior role, or runtime requirements.
  - Do not reuse coder as reviewer/verifier merely to save usage.
- [ ] **6. Make workflow/workspace policy consistent with conditional planner use.**
  - Owner: `coder`
  - In `shared/policies/workflow.instructions.md`:
    - retain Plan-First when plan creation is actually needed;
    - make per-phase PLAN conditional;
    - require the prior-phase material-impact check;
    - constrain replanning to affected future phases.
  - In `shared/policies/workspace.instructions.md`:
    - replace fixed `orchestrator -> planner -> ...` wording with a concise conditional-planner route;
    - keep workflow policy normative for trigger details.
  - Do not change branch, pause, score, commit, review, or closeout semantics.
- [ ] **7. Strengthen language compliance at the existing policy boundary.**
  - Owner: `coder`
  - Modify `shared/policies/agent-reporting.instructions.md`.
  - Keep it the single language-policy source.
  - Add a mandatory send-time self-check against the human-facing rules.
  - State this is part of composing the response, not a separate rewrite lifecycle.
  - Compact internal handoffs may remain compressed but must not be relayed verbatim when unsuitable for users.
  - Preserve exact technical evidence.
  - Keep ordinary chat exempt from mandatory `humanize`.
  - Keep documentation's existing `humanize` `edit` self-check.
  - Touch `documenter/prompt.md` only if the existing requirement is not operationally clear.
- [ ] **8. Update generated root guidance and validation atomically.**
  - Owner: `coder`
  - In `scripts/generate_targets.py`:
    - keep root language summary compact;
    - add that reporting rules are output requirements and user-facing prose must be self-checked;
    - make planner conditional in the root workflow route;
    - add only a short Context Mode note if needed; do not duplicate tool-routing policy.
  - In `scripts/validate_targets.py`, extend existing checks for:
    - conditional planner route;
    - prior-phase material-impact trigger;
    - affected-future-only replanning;
    - evidence packet/context reuse;
    - reporting-policy pointer;
    - send-time language self-check;
    - guarded directory project indexing is supported and optional;
    - no text claims directory indexing is disabled.
  - Preserve explicit tests that extra `ctx_index` arguments remain denied.
  - Do not add a parser dependency, style scorer, AI-writing detector, or network lookup.
- [ ] **9. Document the minimal workflow and Context Mode boundary.**
  - Owner: `documenter`
  - Required Skills: `documentation/SKILL.md`, `humanize/SKILL.md` (`edit`).
  - Update the smallest relevant README/runtime sections.
  - Show:
    ```text
    Implement big plan `<plan-name>`.
    ```
  - Explain briefly:
    - approved existing plans normally skip planner;
    - prior-phase evidence can trigger targeted replanning;
    - known authoritative files are read directly;
    - guarded Context Mode may establish a bounded project index for broader discovery;
    - the filter keeps directory-policy knobs fixed;
    - indexing is optional/nonblocking and never repository truth;
    - existing agent context/results are reused;
    - retrieval, language, verification, review, and lifecycle rules remain mandatory.
  - Remove/update text saying Context Mode directory indexing is disabled.
  - Do not claim delete/rename cache guarantees.
- [ ] **10. Run adversarial control-plane review and Ponytail shrink pass.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`, `ponytail`.
  - Challenge explicitly:
    - directory allowance can escape containment through symlink/path handling;
    - index-policy knobs accidentally became accepted;
    - pinned upstream defaults are bypassed;
    - indexing became mandatory/a gate;
    - cap exhaustion triggers automatic widening;
    - cached results are treated as repository truth;
    - each subagent redundantly re-indexes;
    - custom indexing code duplicates upstream behavior;
    - planner is skipped after material prior-phase evidence;
    - planner is rerun when nothing changed;
    - agent reuse compromises independent review/verification;
    - language rules are duplicated rather than enforced at the canonical boundary;
    - internal compact language leaks to users.
  - Run Ponytail last and remove unnecessary machinery.
## Verification

```bash
node --check shared/hooks/scripts/context-mode-mcp-filter.mjs
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Run the repository's existing Context Mode filter/runtime tests plus the new directory cases.

Inspect generated guidance:

```bash
rg -n "planner|Context Mode|ctx_index|agent-reporting|user-facing|self-check|reuse" \
  dist/multi-agent/CLAUDE.md \
  dist/multi-agent/AGENTS.md
```

Inspect canonical/generated orchestrator material using actual generated paths:

```bash
rg -n "planner|ctx_index|project:|evidence packet|reporting|reuse|fresh" \
  shared/agents/orchestrator/prompt.md \
  dist/multi-agent/
```

Persist the normal quality score and findings through the repository's existing closeout workflow.

## Acceptance Cases
| Situation | Expected behavior |
|---|---|
| Approved plan exists and remains valid | Skip planner |
| No implementation-ready plan exists | Use planner |
| Completed phase materially changes next phase assumptions | Planner revises affected future work |
| Completed phase does not affect future assumptions | Do not invoke planner |
| Known README/plan/instruction path | Direct read |
| Broad discovery + Context Mode available | One bounded project directory index, then focused search as useful |
| Context Mode unavailable/errors | Continue with direct read / `rg` / Semble |
| Directory index hits upstream cap | Continue; do not auto-increase cap |
| `ctx_index` on repository root | Allow |
| `ctx_index` on contained subdirectory | Allow |
| `ctx_index` on contained regular file | Allow |
| `ctx_index` outside repository | Deny |
| `ctx_index` root symlink | Deny |
| `ctx_index` with `maxFiles`/`maxDepth`/`respectGitignore` | Deny |
| Agent needs to edit indexed file | Read current file normally before editing |
| Same coder has valid context | Reuse when supported |
| Independent review required | Fresh/independent reviewer |
| Internal compact report | Keep internal or adapt before user-facing output |
| User-facing response | Self-check against reporting policy before send |
| Documentation changes | Apply existing `humanize` edit check |
| User says `Implement big plan X` | Start standard workflow without long boilerplate |
## Closeout Checklist
- [ ] Context Mode security/regression tests passed
- [ ] Generator/validator/runtime checks passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
## Pause Checkpoint

Use only after an explicit user request to pause/checkpoint. Follow the pause behavior present in the repository at implementation time. Keep the same current phase and required PAUSED evidence. Do not use pause to hide failed checks or unresolved required review work.
