---
name: 2026-09-19_phase-E-openwiki-child-process-sandbox
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 5
status: planned
closeout_session_log:
---
# Small Plan: 2026-09-19_phase-E-openwiki-child-process-sandbox

## Scope

Phase A contains OpenWiki by checking the repository before and after the run and refusing the
run when anything moved outside `openwiki/**`. That is detection, not prevention. This phase
replaces it with prevention: start the OpenWiki child process inside an isolation boundary the
operating system enforces, so a write outside the allowed directory cannot happen at all.

## Why This Phase Exists

The OpenWiki command is an outside tool that writes files. A symlink is a file that points at
another location, so a file created inside `openwiki/` can point at `CLAUDE.md` at the top of
the repository, and writing to it lands outside the allowed directory. Phase A scans for such
pointers before the child starts and again after it exits. The child runs in between, and a
pointer created and used during that window is only ever found afterwards.

Phase A's after-the-fact detection covers what it can reach: the root adapters are restored
from pre-run bytes automatically, every changed path inside the repository is named in the
failure result, and nothing is committed. Two gaps remain and are the reason for this phase:

- A write landing outside the repository entirely, for example in the user's home directory,
  is not noticed by any repository-scoped check.
- Damage is reported after it has already happened, so recovery depends on a human or agent
  acting on the failure result.

This phase was deliberately separated from Phase A on 2026-09-19 to keep the runtime and
safety boundary closeable. The decision was: detect now, prevent later.

## Steps

### Step E1 — Choose and prove the isolation mechanism

- [ ] **Owner:** `coder`
- **Target files:**
  - create a throwaway evidence script; commit nothing from this step
- **Required Skills:**
  - `shared/skills/integration-gate-spike/SKILL.md`
  - `shared/skills/ponytail/SKILL.md` in `full` mode
- **Behavior:**
  - Compare the realistic candidates on the pinned devcontainer image: `bubblewrap`
    (`bwrap`), `unshare` with a mount namespace, and Linux Landlock through a small
    pre-exec step.
  - Decide against the constraints that actually bind here: the child must still read the
    whole repository to generate its knowledge, must still reach the user's `~/.openwiki`
    configuration directory and the network for its provider, and must write only under
    `openwiki/**`.
  - Record which candidate satisfies all four, whether it needs elevated privileges, and
    whether it works unprivileged inside the devcontainer.
- **Acceptance criteria:**
  - one mechanism selected with written evidence of the read, write, config, and network
    behavior actually observed, not assumed;
  - the unavailable-on-host case has a decided answer before any code is written.
- **Verification:**
  - the evidence script output, quoted in the session log.

### Step E2 — Wrap the child process in the chosen boundary

- [ ] **Owner:** `coder`
- **Target files:**
  - modify `shared/scripts/openwiki_refresh.py`
  - modify `shared/devcontainer/Dockerfile` if the mechanism needs a system package
  - modify `scripts/validate_targets.py` if a new pinned package is added
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/code-style/SKILL.md`
  - `shared/skills/testing-patterns/SKILL.md`
- **Behavior:**
  - Launch the OpenWiki child inside the boundary. Keep the existing argument vector,
    the child environment with the telemetry default, and the `flock`.
  - When the mechanism is unavailable on the host, follow the Step E1 decision. Do not
    silently fall back to an unprotected run without saying so in the structured result.
  - Keep every Phase A check in place. Prevention and detection are layers, not
    alternatives; do not delete the post-run walk or the fingerprint comparison.
- **Acceptance criteria:**
  - a write outside `openwiki/**` fails inside the child rather than being reported after
    the fact;
  - the structured result states which isolation mode was used;
  - the runner still succeeds on a normal refresh with no behavior change visible to a
    caller.
- **Verification:**
  - `uv run pytest tests/test_openwiki_refresh.py -q --tb=short`;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step E3 — Prove the boundary holds

- [ ] **Owner:** `coder`
- **Target files:**
  - extend `tests/test_openwiki_refresh.py`
- **Required Skills:**
  - `shared/skills/ponytail/SKILL.md` in `full` mode
  - `shared/skills/testing-patterns/SKILL.md`
- **Test scenarios:**
  - a fake `openwiki` that writes directly to a repository path outside `openwiki/**` is
    blocked, not merely detected;
  - a fake `openwiki` that creates a symlink inside `openwiki/` and writes through it is
    blocked;
  - a fake `openwiki` that writes to a path outside the repository is blocked, which is the
    case Phase A cannot cover;
  - a normal successful refresh still writes `openwiki/**` and still reads the whole
    repository;
  - the unavailable-mechanism path behaves exactly as Step E1 decided and says so in the
    result.
- **Acceptance criteria:**
  - tests stay deterministic, with no provider call, model call, or network access;
  - a failing test names the exact boundary that broke.
- **Verification:**
  - `uv run pytest tests/test_openwiki_refresh.py -q --tb=short`;
  - `uv run python .claude/scripts/verify.py fast --format json`.

### Step E4 — Review and closeout

- [ ] **Owner:** `reviewer`
- **Target files:** scoped Phase E diff
- **Review Profiles:**
  - `code`
  - `architecture`
  - `security`
  - `tests`
  - `ponytail`
- **Review focus:**
  - the boundary cannot be bypassed by the child;
  - the unavailable-mechanism path cannot degrade to an unprotected run without saying so;
  - no new dependency is unpinned;
  - Phase A's detection layers are still present.
- **Acceptance criteria:**
  - CRITICAL/MAJOR findings resolved;
  - surviving MINOR findings have explicit disposition and reason;
  - canonical closeout receipts pass.

## Verification

```bash
uv run pytest tests/test_openwiki_refresh.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py fast --format json
```

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, CLOSEOUT).

- [ ] Documentation updated for any new system dependency, or explicitly skipped
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Phase A's detection layers verified still present and still tested
