---
name: 2026-09-24_phase-A-sidecar-provider-contract
type: small-plan
parent_plan: consumer-sidecar-bootstrap-overlay
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: Phase A — Sidecar Provider Contract

## Scope

An evidence-gathering spike before any implementation. The single output is
`docs/sidecar-provider-contract.md`. For each client it freezes three lists,
with an evidence tier for every claim:

- the read list: every repository skill folder the client reads, which the
  collision check uses (big plan, Decision 8);
- the write list: the skill folders the sidecar writes;
- the bridge file and its frontmatter.

This phase changes no installer, generator, validator, or test code.

Clients in scope: Claude Code, OpenAI Codex, Google Antigravity, and GitHub
Copilot in VS Code. Copilot CLI and cloud agents are out of scope, which
matches the README's Copilot claim.

### Required Skills

- `shared/skills/integration-gate-spike/SKILL.md`
- `shared/skills/documentation/SKILL.md`

## Documented Starting Point

The 2026-09-24 plan review read each client's documentation. Step 1
re-checks every row and cites the page and date. None of these rows is
`native-run` evidence yet. A `source` note means the behavior was read in the
client's source code but is not documented.

| Client | Repository skill folders read | Bridge mechanism | Duplicate names | Git-ignored files | Sources |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `.claude/skills/` only; not `.agents/skills/` or `.github/skills/` | `.claude/rules/*.md` loads in addition to `CLAUDE.md`; `paths` scopes a rule, and a rule without `paths` is undocumented; `CLAUDE.local.md` is supported and additive | Enterprise, then personal, then project | Undocumented. This repository's own sessions load `.claude/skills/` and `.claude/rules/` files that `.gitignore` ignores; `info/exclude` is untested | code.claude.com/docs/en/skills, /claude-directory, /large-codebases |
| OpenAI Codex | `.agents/skills/` in every folder from the working directory up to the repository root; `source`: also `.codex/skills/` | None additive: `AGENTS.override.md` replaces `AGENTS.md`, fallback names apply only when `AGENTS.md` is missing, and `developer_instructions` needs a trusted project config | Both copies appear; Codex does not merge them | Undocumented; `source`: plain folder read, no `.gitignore` check | learn.chatgpt.com/docs/build-skills, /docs/agent-configuration/agents-md, /docs/config-file/config-reference |
| Copilot in VS Code | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | `.github/instructions/*.instructions.md` with `applyTo`; instruction sources are additive; loading with no attached file is undocumented (`source`: the Local agent adds `**` patterns while `chat.includeApplyingInstructions` is on) | Undocumented; `source`: the Local agent keeps the first skill it finds | Undocumented; `source`: plain folder read | code.visualstudio.com/docs/agent-customization/agent-skills, /custom-instructions |
| Google Antigravity | `.agents/skills/`; legacy `.agent/skills/` still read | `.agents/rules/*.md` (legacy `.agent/rules/`); each file needs frontmatter with a valid `trigger`, or it is silently discarded; `always_on` adds the rule to every turn; rules are cumulative | Undocumented | Undocumented; Strict mode "respects `.gitignore`", which may hide sidecar files | antigravity.google/docs/rules, /docs/skills, /docs/settings |

Two more documented facts shape the tests:

- VS Code runs two session types: the Local agent, which is marked for
  removal, and Agent Host sessions, which follow the discovery rules of the
  selected harness (Copilot, Claude, or Codex). Evidence from the Local agent
  alone may expire (code.visualstudio.com/docs/agents/run/agent-harnesses).
- Worktrees that VS Code or the Codex app create for background sessions
  copy git-ignored files only when they are listed (`git.worktreeIncludeFiles`,
  `.worktreeinclude`), so they contain no sidecar files. Phase D documents
  this; no test is needed.

## Questions Per Client

1. Which repository skill folders does it read? Record every folder,
   including ones the sidecar will not write, because the collision check
   needs the full read list.
2. Does it discover a skill or bridge file that Git ignores through
   `info/exclude`? For Antigravity, answer for the default mode and for
   Strict mode.
3. When the same skill name is in two folders it reads, does it show one
   copy, both copies, or an error? For Copilot, cover the sidecar's two
   identical copies (`.claude/skills/` and `.agents/skills/`), and a tracked
   team skill in `.github/skills/` that has the same name as a sidecar skill.
4. Does the candidate bridge load in every session while tracked team
   guidance stays active?
   - Claude Code: `.claude/rules/ai-bootstrap-sidecar.md` with no `paths`
     frontmatter. Second candidate: `CLAUDE.local.md`, used only when absent.
   - Google Antigravity: `.agents/rules/ai-bootstrap-sidecar.md` with
     `trigger: always_on`. Record the exact frontmatter that loads it.
   - Copilot VS Code: `.github/instructions/ai-bootstrap-sidecar.instructions.md`
     with `applyTo: "**"`. Record whether it loads in a chat that attaches no
     file, and whether `.github/copilot-instructions.md` stays active.
   - Codex: confirm that the tracked `AGENTS.md` loads and that the sidecar
     skills are listed. No Codex bridge is planned (big plan, Decision 7).
5. Does it reject or warn about any skill frontmatter field the bootstrap
   ships, such as `visibility` or a multi-line `description`? Claude Code
   documents that it ignores unknown fields.
6. Client name, version, session type (for VS Code: Local agent, or Agent
   Host with the Copilot harness), and observation date.

## Steps

- [ ] **1. Re-check the documented starting point.**
  - **Owner:** `coder`
  - Re-read each source in the table above, update any row that changed,
    and record the link and the date. Mark each answer `documented`, or
    `source` when only the client's code shows it.
  - Undocumented behavior is not a claim.

- [ ] **2. Write the fixture recipe.**
  - **Owner:** `coder`
  - In the contract document, write the exact shell commands that create a
    throwaway Git repository outside this repository, containing:
    - tracked team `CLAUDE.md`, `AGENTS.md`, and
      `.github/copilot-instructions.md`, each with a unique team marker phrase;
    - one tracked team skill in each of `.claude/skills/`, `.agents/skills/`,
      and `.github/skills/`;
    - two sidecar marker skills in `.claude/skills/` and `.agents/skills/`,
      `sidecar-marker-a` and `sidecar-marker-b`, each with a unique reply
      phrase;
    - a tracked team skill named `sidecar-marker-b` in `.github/skills/`,
      with its own reply phrase, for the collision question;
    - the three bridge files with their frontmatter, each with a unique
      sidecar marker phrase;
    - an `info/exclude` block that ignores every sidecar file.
  - The recipe starts with `mkdir -p "$DIR" && cd "$DIR" || exit 1` and stops
    unless `git rev-parse --show-toplevel` prints that folder, so it can never
    write inside another repository.
  - The operator runs the recipe in their own shell. The commit gate in agent
    sessions blocks `git commit` even in other repositories.
  - The recipe ends by printing `git status --porcelain --untracked-files=all`,
    which must list nothing.

- [ ] **3. Run each client against the fixture.**
  - **Owner:** user (operator); `coder` records the results.
  - Follow the `check_native_clients.py` conventions: a stable workspace that
    the operator trusts manually, explicit user authorization, and no change
    to trust or user settings.
  - Antigravity: use the `agy` CLI with `--new-project --sandbox`. A run
    that reuses a persisted project is invalid (`docs/runtime-checks.md`,
    Google Antigravity evidence boundary). Repeat once in Strict mode.
  - VS Code: record the Local agent and an Agent Host session with the
    Copilot harness separately. A session type that the installed VS Code
    lacks is recorded as `unavailable`.
  - Ask the client to list its skills and to quote its active instructions.
    Where a client exposes structured data (an init event or a skills list),
    record that data. A model's description of itself is not proof.
  - Record only whether each marker phrase appeared (yes or no), which copy
    of `sidecar-marker-b` answered, and the client version. Do not store raw
    transcripts: `check_native_clients.py` discards native output by design.

- [ ] **4. Freeze the matrix.**
  - **Owner:** `coder`
  - One table row per client and session type: skill folders read,
    ignored-file discovery (including Antigravity Strict mode), duplicate
    behavior, which `sidecar-marker-b` copy won, bridge path and frontmatter,
    evidence tier (`native-run`, `documented`, `source`, or `unavailable`),
    client version, and date.
  - State the resulting read list, write list, and bridge paths. A write root
    or bridge path ships only when at least one client has `native-run`
    evidence for it (big plan, Decision 14). The read list may include
    folders known only at `documented` or `source`, because checking more
    folders for collisions is always safe.

- [ ] **5. Apply the decision gate.**
  - **Owner:** `orchestrator`
  - If no client reaches `native-run` evidence, cancel Phases B-E.
  - If the matrix differs from the big plan's expected layout, revise Phases
    B-D before Phase B starts.

## Acceptance Criteria

- Every matrix row has an evidence tier. Nothing below `native-run` is
  described as supported.
- The read list and the write list are stated separately.
- The Codex row names the rejected mechanisms and the result.
- Copilot is covered for VS Code only, and every Copilot row names its
  session type.
- The Antigravity rows cover the default mode and Strict mode.
- Phase B can copy its path constants directly from the matrix.

## Verification

```bash
test -s docs/sidecar-provider-contract.md
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code native run against the fixture, done by the operator.
- OpenAI Codex native run against the fixture, done by the operator.
- Google Antigravity native run against the fixture, in the default mode and in Strict mode, done by the operator.
- GitHub Copilot VS Code native run against the fixture, in a Local agent session and an Agent Host session, done by the operator.

## Review Profiles

- `documentation`
- `architecture`
- `security`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
