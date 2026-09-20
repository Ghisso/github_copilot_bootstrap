---
name: 2026-09-19_phase-G-openwiki-host-driven-guard
type: small-plan
parent_plan: 2026-09-19_openwiki-knowledge-layer-integration
phase_index: 9
status: complete
closeout_session_log: .claude/session_logs/2026-09-19_openwiki-phase-G-host-driven-guard.md
---

# Small Plan: 2026-09-19_phase-G-openwiki-host-driven-guard

## Scope

OpenWiki 0.5.2 runs host-driven: the coding agent (Claude Code or Codex) calls OpenWiki's MCP
tools, and OpenWiki's server writes `openwiki/**` plus, at exactly one point (`openwiki_begin`),
a managed `<!-- OPENWIKI:START -->…<!-- OPENWIKI:END -->` block into root `AGENTS.md` and
`CLAUDE.md`. There is no bootstrap-spawned child process, so Phase A's subprocess runner is the
wrong shape and cannot pass its own preflight against the real CLI.

This phase replaces the runner with a deterministic hook guard around `openwiki_begin`, adds a
commit-time backstop in `verify.py`, fixes the devcontainer smoke line that breaks the image
build, adds a real-binary MCP handshake test, and makes OpenWiki-installed skill bundles
third-party-owned.

**Entry condition.** This phase is built only against the observed evidence in
`docs/2026-09-19-openwiki-hook-mechanics-spike.md`. If that document's decision is RE-PLAN, this
phase is re-planned before any step starts; do not implement it as written. If the decision is
GO with adaptations, apply the per-host adaptations in the table below and record which applied.

| Spike outcome (per host) | Adaptation in this phase |
| --- | --- |
| O1 GO | Build as written for that host |
| O2 `PostToolUse` unreliable | Keep `pre`; add the payload-free `post` call to that host's existing `Stop` hook so adapters are clean by end of turn; skill instructs a manual `post` right after `openwiki_begin` |
| O3 deny not honored | Do not claim deterministic `init` prevention for that host in skill or docs; `post` restores the workflow path's pre-state; backstop is the control |
| O4 `PreToolUse` absent | No hook entries for that host; add `pre --root <abs>` payload-free mode the skill instructs the agent to run before `openwiki_begin` |
| O5 different stable name | Use the observed name as that host's matcher |

Verified upstream facts (checked in the installed package): `repository-run.js:51` is the only
host-path call to `ensureCodeModeRepoSetup` and `finish` does not touch the adapters; insertion
is `content.trimEnd() + "\n\n" + snippet + "\n"`, so byte-exact restore needs a pre-snapshot;
`openwiki_begin` accepts `mode: "init" | "update"` and `force`; `init` creates
`.github/workflows/openwiki-update.yml` and replaces the wiki; `openwiki mcp --host claude`
answers MCP `initialize` with `serverInfo.version` and lists six tools;
`openwiki integrations list --project .` works without a TTY.

## Steps

### Step G1 — Add the `openwiki-guard` hook and wire it per the spike evidence

- [x] **Owner:** `coder`
- **Target files:**
  - create `shared/hooks/scripts/openwiki-guard.py` (Python 3.9-compatible; stdlib only)
  - create `shared/hooks/scripts/openwiki-guard.sh` (conventions of `protect-files.sh`: stdin
    payload, `payload_parseable`/`fail_closed`/`deny_pretool` from `_lib-frontmatter.sh`,
    invoked through `run-hook.sh`)
  - modify `scripts/generate_targets.py`: Claude settings renderer (near line 1055) and Codex
    hooks renderer (near line 1143): one `PreToolUse` and one `PostToolUse` entry per host with
    the matcher the spike observed (expected `mcp__openwiki__openwiki_begin`), invoking
    `openwiki-guard.sh pre` / `post`; apply O2/O4/O5 adaptations per host. Not Copilot, not
    Antigravity.
  - modify `scripts/validate_targets.py`: hook script inventory (near line 218) and the
    matcher-to-script map (near line 1416)
  - create `tests/test_openwiki_guard.py`
- **Required Skills:** `shared/skills/create-feature/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` in `full` mode, `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`
- **Contract:**
  - `openwiki-guard.py <pre|post>`; payload JSON on stdin (`tool_name`, `tool_input`, …). For
    `post`, empty stdin means manual recovery: restore from any existing snapshot.
  - Constants: `MANAGED_START = "<!-- OPENWIKI:START -->"`, `MANAGED_END = "<!-- OPENWIKI:END -->"`,
    `ADAPTERS = ("AGENTS.md", "CLAUDE.md")`, `WORKFLOW = ".github/workflows/openwiki-update.yml"`,
    snapshot directory `.claude/.cache/openwiki-guard/` (consumer state; ignored by the nested
    repository; excluded from drift).
  - `pre`: deny when `tool_input.mode == "init"` (reason names `update` as the only allowed
    mode); deny when `tool_input.root` is missing or its realpath is not this repository's
    top-level; deny when `<root>/openwiki/INSTRUCTIONS.md` is absent. Otherwise heal any stale
    snapshot with the `post` rules, then snapshot each adapter (bytes or an explicit absent
    marker) and whether `WORKFLOW` exists; write the manifest atomically; allow.
  - Deny output: `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}`
    on stdout, exit 0 (the form both hosts document and the spike confirmed). Internal errors
    and unparseable payloads fail closed: exit 2, reason on stderr.
  - `post`: per adapter, current equals snapshot → nothing; differs and contains exactly one
    managed block → write the snapshot bytes (unlink when the snapshot says absent); differs
    with no managed block → leave it and record a mismatch. Restore `WORKFLOW`'s pre-state the
    same way (remove it only if `pre` recorded it absent). Exit 2 with a reason on any mismatch.
    On success delete the snapshot and print one line naming what was restored. With no
    snapshot, strip the block region and one preceding blank line and say
    `restored_from: marker-strip`.
  - Must not: run `openwiki`, take locks, fingerprint anything beyond the two adapters and the
    workflow path, or write outside the snapshot directory.
  - Module docstring carries the residual-limits reasoning inherited from Phase A that still
    applies (a write outside the repository is invisible to repository checks; the guard covers
    only the two adapters and the workflow path; the agent's own writes are governed by the
    existing `protect-files` hooks).
- **Test scenarios (deterministic; payloads shaped exactly like the spike's observed
  payloads; temporary Git repos; no OpenWiki):** `pre` denies `init`, foreign root, missing
  marker; allows and snapshots otherwise; `post` restores byte-for-byte after a simulated
  insertion that mirrors `code-mode.js` including trailing-newline loss; removes an adapter
  absent before; leaves a concurrently edited adapter alone and exits 2 naming it; removes a
  workflow file that appeared; strips as fallback with no snapshot and says so; `pre` heals a
  stale snapshot; unparseable payload fails closed; `py_compile` under the 3.9 check; generated
  `.claude/settings.json` and `.codex/hooks.json` carry the entries the spike decision calls for.
- **Verification:** `uv run pytest tests/test_openwiki_guard.py tests/test_hook_gates.py tests/test_validate_targets.py -q --tb=short`;
  `uv run python scripts/generate_targets.py --all && uv run python scripts/validate_targets.py`

### Step G2 — Fold the deterministic commit backstop into the existing gates

- [x] **Owner:** `coder`
- **Target files:** `shared/scripts/verify.py` (extend `VFY-GEN-001` in `phase_checks`; extend
  `gate_receipt_errors`), its tests, `docs/runtime-checks.md` (one row)
- **Required Skills:** `shared/skills/ponytail/SKILL.md` in `full` mode,
  `shared/skills/code-style/SKILL.md`, `shared/skills/testing-patterns/SKILL.md`
- **Behavior:** this adds no check ID. `VFY-GEN-001`'s `phase` remit additionally FAILs when
  root `AGENTS.md` or `CLAUDE.md` contains `MANAGED_START`; when
  `.github/workflows/openwiki-update.yml` is untracked or staged as new; or when
  `openwiki/.run.json` is tracked or staged. File reads and
  `git ls-files`/`git diff --cached --name-only` only; never model-backed. At commit time,
  `gate_receipt_errors` raises one closeout-evidence error per violated condition, under the
  `exact` head relation only, message prefix `openwiki-managed-state:`, naming the file and the
  fix — the same path Phase C's stale-claims gate already uses. `CHECK_IDS` and
  `SCHEMA_VERSION` are unchanged, so every earlier phase's receipt still loads.
- **Verification:** focused verifier tests; `uv run python .claude/scripts/verify.py phase --format json`

### Step G3 — Retire the subprocess runner

- [x] **Owner:** `coder`
- **Target files:** delete `shared/scripts/openwiki_refresh.py` and
  `tests/test_openwiki_refresh.py`; `scripts/generate_targets.py` (remove the copy at lines
  297-301); `scripts/validate_targets.py` (remove `.claude/scripts/openwiki_refresh.py` near
  line 8845); after `generate_targets.py --all` and the local self-install, remove the
  now-obsolete nested `.claude/scripts/openwiki_refresh.py` that `scripts/check_runtime.py`
  reports
- **Required Skills:** `shared/skills/ponytail/SKILL.md` in `full` mode
- **Keep from Phase A:** Dockerfile pins for `openwiki`, `mermaid`, `jsdom`; the `~/.openwiki`
  bind mount; the `containerEnv` allowlist; the installer-managed `.gitignore` entry
  `openwiki/.run.json` and its test.
- **Carry forward:** one `[LEARN]` entry with the runner's security reasoning (fail closed on
  ordinary activity gets bypassed; allowlist the surface you own; detection is not prevention)
  so nine review rounds survive as design, not dead code.
- **Verification:** `uv run python scripts/check_runtime.py`; `uv run python scripts/validate_targets.py`

### Step G4 — Fix the devcontainer smoke line and add the real-binary MCP handshake test

- [x] **Owner:** `coder`
- **Target files:** `shared/devcontainer/Dockerfile:36-37`, `scripts/validate_targets.py:8685-8689`,
  new `tests/test_openwiki_cli_smoke.py`
- **Required Skills:** `shared/skills/ponytail/SKILL.md` in `full` mode,
  `shared/skills/testing-patterns/SKILL.md`, `shared/skills/add-dependency/SKILL.md` (pin
  handling only)
- **Behavior:** replace `openwiki --version` (exit 1: "Unknown option") with a check that fails
  the build when the installed version differs from the pin and when the CLI cannot start
  non-interactively, for example
  `test "$(node -p "require('$(npm root -g)/openwiki/package.json').version")" = "0.5.2"` and
  `openwiki integrations list </dev/null >/dev/null`; keep `command -v openwiki`; update the
  validator to assert the working check. The smoke test does not use `skipif`: when
  `shutil.which("openwiki")` is `None` it fails with a message naming the missing binary,
  because the devcontainer image installs the pinned CLI and this required item must prove the
  handshake ran, not report a pass it never attempted. In a temporary Git repo it spawns
  `openwiki mcp --host claude` with `DO_NOT_TRACK=1`, sends `initialize` and `tools/list` over
  stdio with a timeout, asserts `serverInfo.version == OPENWIKI_PINNED_VERSION` (imported from
  `scripts.validate_targets`) and the six tool names, and asserts the temporary repo is
  unchanged.
- **Verification:** `uv run pytest tests/test_openwiki_cli_smoke.py -q`; `uv run python scripts/validate_targets.py`

### Step G5 — Make OpenWiki-installed skill bundles third-party-owned

- [x] **Owner:** `coder`
- **Target files:** `scripts/runtime_ownership.py` (one small constant and predicate, for
  example `THIRD_PARTY_SKILL_PATHS = ("skills/openwiki",)`), `scripts/check_runtime.py`
  (neither `.claude/skills/openwiki/**` nor `.agents/skills/openwiki/**` is obsolete drift or
  parity-compared), `scripts/install_bootstrap.py` (refresh preserves both), tests
- **Required Skills:** `shared/skills/ponytail/SKILL.md` in `full` mode,
  `shared/skills/code-style/SKILL.md`, `shared/skills/testing-patterns/SKILL.md`
- **Behavior:** OpenWiki's installer writes `SKILL.md`, `.openwiki-install.json`, and
  `agents/*.yaml` into those two directories in Phase I; the bootstrap never generates or edits
  them afterwards.
- **Marker rule (decided 2026-09-21 during implementation):** a directory under
  `THIRD_PARTY_SKILL_PATHS` is third-party-owned only when it contains
  `.openwiki-install.json`, the file OpenWiki's installer writes. Without the marker it stays
  ordinary generated content: refresh overwrites and prunes it, and `check_runtime.py`
  compares it. Reason: the bootstrap still ships `shared/skills/openwiki/SKILL.md` into that
  path until Phase H renames it; an unconditional preserve-on-refresh would have kept every
  installed copy, including this repository's own, on the pre-G6 text.
- **Verification:** `uv run pytest tests/test_install_bootstrap.py -q` plus runtime-check tests;
  `uv run python scripts/check_runtime.py`

### Step G6 — Remove every runner mention and describe the host-driven mechanism

- [x] **Owner:** `coder` for generator strings, `documenter` for prose
- **Target files:** `shared/policies/workflow.instructions.md` ("OpenWiki Refresh" lines
  173-180; Knowledge-Refresh "Shape" lines 215-216: drop "and its runner");
  `shared/agents/orchestrator/prompt.md:56`; authoring `AGENTS.md:9`, `CLAUDE.md:14`, and
  `render_root_guidance` at `scripts/generate_targets.py:1287` (drop
  `.claude/scripts/openwiki_refresh.py`); `shared/skills/openwiki/SKILL.md` "Running a refresh"
  and "Reading the result" (minimal truthful rewrite: MCP tools, `mode: "update"` only, the
  guard restores adapters on the hosts the spike confirmed, manual `openwiki-guard.sh post`
  recovery; Phase H renames and expands this skill — do not rename here);
  `docs/architecture.md:162-183` (guard and backstop replace the runner paragraph; state the
  per-host guard coverage the spike found); `README.md:330,433` (soften the `~/.openwiki`
  claim: optional, not required in host-driven mode)
- **Required Skills:** `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`
- **Acceptance criteria:** `grep -rn 'openwiki_refresh' shared scripts docs README.md AGENTS.md CLAUDE.md tests`
  returns nothing; every statement about OpenWiki execution is true at this commit and matches
  the spike evidence.
- **Verification:** `uv run python scripts/generate_targets.py --all && uv run python scripts/validate_targets.py`

### Step G7 — Review

- [x] **Owner:** `reviewer`
- **Review Profiles:** `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`
- **Review focus:** every guard behavior maps to a line of spike evidence (skill Step 3
  verification); the guard cannot be bypassed by a different `mode` spelling or non-object
  payload; `post` never deletes a file it did not snapshot as absent; no hook runs OpenWiki;
  the backstop is cheap and host-independent; the Dockerfile check really fails on a mismatch;
  the ownership exemption is narrow; 3.9 compatibility.

## Verification

```bash
uv run pytest tests/test_openwiki_guard.py tests/test_openwiki_cli_smoke.py tests/test_hook_gates.py tests/test_install_bootstrap.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json               # during IMPLEMENT
uv run python .claude/scripts/verify.py phase --format json --persist    # before REVIEW
```

## Optional Verification

- Build the devcontainer image (`docker build` of `shared/devcontainer/Dockerfile`) to prove
  the new smoke line in Step G4 passes inside the image. This is optional because it needs a
  Docker host, which is not available in every execution environment. Record the outcome in the
  closeout session log as `- optional 1: PASS|FAIL|NOT RUN — <detail>`.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`.

- [x] Spike decision was GO or GO-with-adaptations; adaptations applied are named in the session log
- [x] Documentation updated (`docs/architecture.md`, `docs/runtime-checks.md`, README bullets)
- [x] LEARN entries saved (including the runner's carried-forward security reasoning)
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` then `verify closeout` PASS)
- [x] No runner reference remains; nested `.claude/scripts/openwiki_refresh.py` removed
- [x] No hook, verifier, installer, state-sync, or CI path runs OpenWiki

## Pause Checkpoint

(template text, identical to Phase F)
