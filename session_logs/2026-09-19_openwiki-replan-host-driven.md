# OpenWiki Re-plan: From Subprocess Runner to Host-Driven Mode

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-19_openwiki-knowledge-layer-integration.md`
**Outcome:** Phases D and E cancelled; phases F, G, H, I, J, K created.
**Cancellation evidence:** `.claude/session_logs/2026-09-19_openwiki-phase-D-E-cancellation.md`

## Summary

Phases A, B, and C shipped an OpenWiki integration built on a wrong model of how OpenWiki 0.5.2
works. The error was not a detail. It was the central assumption: that the bootstrap would spawn
OpenWiki as a child process which calls a model provider using credentials in `~/.openwiki`.

OpenWiki 0.5.2 also supports **host-driven mode**, where the coding agent already running — Claude
Code or Codex — *is* the model, calling OpenWiki's MCP tools directly. No provider credentials, no
child process. That is the mode this repository will use.

Phases A, B, and C remain committed and are not reverted. Phase B's ownership contract and Phase
C's lifecycle rule are mode-independent and survive intact. What does not survive is Phase A's
runner and the rules written around it.

## How this surfaced

The user asked to enable OpenWiki for Claude Code and Codex, with this session as the model. I
replied that this was not possible, because OpenWiki is a separate process that makes its own API
calls, and asked them to choose a provider for `~/.openwiki`.

The user pushed back, quoting the project README: *"Coding-agent integrations for IBM Bob, Codex,
Claude Code, OpenCode, Cursor, and Kiro, using the host's model and repository tools."*

They were right. I had stated a limitation as fact without checking it, and had already asked them
to make a decision resting on it.

## Verified findings

All verified by running the installed `openwiki@0.5.2`, not by reading documentation.

### 1. Host-driven mode is real and needs no credentials

`openwiki integrations install claude --project .` writes:

```
.claude/skills/openwiki/SKILL.md   (+ .openwiki-install.json, agents/bob.yaml, agents/openai.yaml)
.mcp.json   ->  "openwiki": {"command": "openwiki", "args": ["mcp", "--host", "claude"]}
```

The Codex variant writes `.agents/skills/openwiki` and a `.codex/config.toml` block wrapped in
`# OPENWIKI:MCP:START/END` markers.

From the README: *"Host-driven runs currently support repository code wikis, not personal brains.
They use the coding agent's authenticated model session, so OpenWiki provider credentials are not
required. OpenWiki owns the durable queue, Claims validation and persistence, source-drift
handling, and deterministic finalization; the coding agent owns repository research, planning, and
factual authoring."*

The lifecycle is exposed as MCP tools: `openwiki_begin`, `openwiki_submit_plan`,
`openwiki_next_page`, `openwiki_inspect_page_claims`, `openwiki_submit_page`, `openwiki_finish`.

### 2. The Phase A runner cannot pass its own preflight

```
$ openwiki --version
Unknown option: --version
exit=1
```

`_version()` in `shared/scripts/openwiki_refresh.py` returns `None` on a non-zero exit, so preflight
returns `required command unavailable: openwiki`. The runner can never reach the subprocess it
exists to wrap.

Every Phase A test used a fake `openwiki` executable that answered `--version`. The fakes were
internally consistent and proved nothing about the real binary.

### 3. The devcontainer image cannot build

`shared/devcontainer/Dockerfile` ends its install chain with:

```
    && command -v openwiki \
    && openwiki --version
```

Because that command exits 1, the `RUN` layer fails and the image build fails. Worse,
`scripts/validate_targets.py` asserts `"openwiki --version" in dockerfile`, so the validator
actively enforced the broken command — fixing the Dockerfile alone would fail validation.

This is a more severe consequence of the same defect as finding 2, and it means nobody had built
the devcontainer since Phase A.

### 4. Host-driven mode still rewrites the root adapters

Traced through the installed package:

`openwiki_begin` → `dist/integrations/core/session-manager.js` → `beginRepositoryRun` →
`dist/generation/repository-run.js:51` → `ensureCodeModeRepoSetup` → writes the
`<!-- OPENWIKI:START -->` managed block into `AGENTS.md` and `CLAUDE.md`
(`dist/ingestion/code-mode.js`, `CODE_MODE_AGENT_FILES = ["AGENTS.md", "CLAUDE.md"]`).

So the protection Phase A built is still *needed* — but Phase A wraps a subprocess, and here the
write happens inside an MCP tool call the agent makes. There is no subprocess to wrap.

Insertion is `content.trimEnd() + "\n\n" + snippet + "\n"`, so removing the block afterwards is not
byte-exact. Restoring correctly requires a snapshot taken before the call.

### 5. Skill name collision on both hosts

Phase B created `shared/skills/openwiki/SKILL.md`, which installs to `.claude/skills/openwiki/` and
`.agents/skills/openwiki/`. OpenWiki's own integration wants exactly those paths, on both hosts.

Tested behavior: the installer **refuses** rather than clobbering —
`An unmanaged or modified skill already exists at ...`. `--force` exists but moves the old
directory to a backup sibling *inside* the skills tree, which hides a stale copy and would recur on
every bootstrap refresh.

So Phase B's skill currently blocks the integration from installing at all.

### 6. Three committed rules forbid what is now required

- Phase A plan, runner "Must not" list: "install a host-specific OpenWiki integration"
- Phase A plan, Step A1: "Do not install OpenWiki host integrations during bootstrap image creation"
- `shared/skills/openwiki/SKILL.md`: "never install host-specific OpenWiki integrations as part of
  ordinary execution"

All three were written from the wrong model. Host-driven mode has no other entry point.

### 7. Incidental: `.mcp.json` behaves well

The integration **merges** rather than overwriting — `semble` and `context-mode` were preserved.
`.mcp.json` is in `ROOT_ADAPTER_PATHS` and tracked here, so `should_preserve` keeps it across a
bootstrap refresh. No work needed.

## Root cause: why nine review rounds missed it

Phase A went through nine review rounds. They were not superficial — they found and fixed real
defects, including a decoy-directory bypass and two false-failure classes, several through live
experiments. And every one of them examined the diff and the deterministic tests.

Not one ran the real binary.

Phase A's own plan required it: *"when a devcontainer build environment is available, run one smoke
check for Node and OpenWiki versions."* Phase A's session log records the outcome:
*"Devcontainer Node/OpenWiki smoke build: not run because no build environment was used."*

I read that line during Phase A closeout and accepted it as a non-blocker. That was the error. Deep
review of a wrapper cannot discover that the wrapped program rejects the flag being passed to it,
because the wrapper, its tests, and its fakes are all consistent with each other. Only contact with
the real thing breaks that consistency.

The fakes were not wrong as fakes. They were wrong as *evidence*, and nothing in the process
distinguished the two.

## Decisions taken

| Decision | Who | Reasoning |
| --- | --- | --- |
| Re-plan D and E from scratch rather than patch | User | The remaining plan was written against a wrong model; patching toward reality accumulates contradictions |
| Delete the Phase A runner entirely | User | It cannot pass its own preflight, provider credentials are ruled out, and a broken unused path invites use. Its security reasoning moves into the guard docstring and a MEMORY lesson |
| Probe host hook behavior **before** building the guard | User | The guard design rests on hook semantics that were documented but never observed. Building on an unobserved assumption is the exact mistake that caused this re-plan |
| Rename the bootstrap skill `openwiki` → `knowledge-refresh` | User | Skill names are unique per host, so two `openwiki` skills cannot coexist. The two have different jobs: OpenWiki's is the authoring and claims contract, the bootstrap's is the lifecycle policy around it. The new name matches the `-knowledge-refresh` phase suffix |
| Phase E is obsolete | Planner | It existed to sandbox a bootstrap-spawned child process. Host-driven mode spawns none. Prevention moves to the guard's deny of `init`, a `verify.py` backstop, and OpenWiki's own root resolution |
| Cancel D and E in place rather than delete | Planner | Keeps the audit trail; `record-commit-closeout.sh` skips cancelled entries when scanning forward |

## New phase structure

| Phase | Purpose |
| --- | --- |
| F | Evidence-only spike: do `PreToolUse`/`PostToolUse` fire on MCP tool calls in Claude Code and Codex, is the tool name `mcp__<server>__<tool>`, is a deny honored, what is the payload shape. Throwaway MCP server in a scratch repository; OpenWiki not required. Outcome recorded as GO, GO-with-adaptations, or RE-PLAN |
| G | Built only against F's evidence: the `openwiki-guard` hook on `openwiki_begin` (deny `init`, snapshot adapters before, restore byte-for-byte after), the `VFY-OPENWIKI-001` commit backstop, the Dockerfile fix, a real-binary MCP handshake test, retire the runner, make OpenWiki-installed skills third-party-owned |
| H | Rename the bootstrap skill, rewrite it for host-driven operation, sweep every reference |
| I | Enable here, install both integrations, re-probe the guard against the real server, run one generation, commit. **Stops** |
| J | Migration, gated on recorded user confirmation as step J1 |
| K | Knowledge refresh: one update, diff inspection, stale-claims audit. Last phase, satisfies Phase C's own rule |

Ordering is forced, not stylistic: G cannot precede F without repeating the original mistake; H must
precede I because the bootstrap skill blocks the integration; I stops before J by phase boundary
rather than by remembering to pause.

## Defence-in-depth after the runner is gone

The runner's protection is replaced by three independent layers, because the first depends on host
behavior this repository does not control:

1. **The guard hook** denies `mode: init` and restores the adapters from a snapshot. Depends on
   host hook semantics — hence Phase F.
2. **`VFY-OPENWIKI-001` in `verify.py`** refuses a commit carrying a managed block in the adapters,
   an untracked `openwiki-update.yml`, or a tracked `openwiki/.run.json`. Host-independent, and the
   real backstop if a hook fails to fire.
3. **OpenWiki's own `resolveRepositoryRoot`**, which requires an absolute path inside a Git
   repository and refuses `/` and `$HOME`.

Phase A's whole-control-plane fingerprinting is deliberately **not** carried over. It assumed a
bounded child-process window. In an interactive session that window is minutes to hours of
legitimate agent writes, so it would fail on every run. This was already Phase A's residual limit 5,
which host-driven mode makes permanent rather than occasional.

## Files changed in this session

- Created `.claude/session_logs/2026-09-19_openwiki-phase-D-E-cancellation.md` (cancellation evidence)
- `2026-09-19_phase-D-...md` and `2026-09-19_phase-E-...md`: `status: cancelled` plus `cancelled_at`,
  `cancelled_reason`, `cancelled_evidence`
- Created six plan files, `2026-09-19_phase-F-...` through `2026-09-19_phase-K-knowledge-refresh.md`
- Big plan: frontmatter `phases:` and `current_phase`, the `## Phases` checklist, the Step Summary
  table (including a pre-existing broken row), and the Risks table
- Big plan prose: Goal 2, Non-Goal 4, and the Devil's Advocate row "Why not use OpenWiki's native
  host integrations?", which had concluded ACCEPT from the wrong model and is now marked REVERSED
  with its reasoning rather than deleted

No outer-repository files changed. `validate_plan_frontmatter.py` and `check_runtime.py` pass.

## [LEARN] Entries

- [LEARN:review] A wrapper, its tests, and its fakes can be perfectly consistent with each other and
  still wrong about the program being wrapped. Nine review rounds hardened a runner whose very first
  real command, `openwiki --version`, exits 1. Before a wrapper is considered done, run the real
  thing once. One invocation would have caught what nine rounds could not.
- [LEARN:workflow] A plan step that says "run this check when an environment is available" will be
  skipped, and the skip will be recorded and accepted. If a check is load-bearing, it blocks the
  phase; if it does not block, do not pretend it is required. Phase A's smoke check was written as
  the former and treated as the latter.
- [LEARN:quality] State a tool's limitations only from something you ran. I told the user that
  OpenWiki could not use this session as its model and asked them to pick a provider on that basis.
  The project README's feature list contradicted me. Check before asserting, and especially before
  asking someone to decide on the assertion.
- [LEARN:review] When a decision record argues its way to a conclusion from a wrong premise, mark it
  reversed with the reasoning rather than deleting it. The Devil's Advocate row on host integrations
  is more useful as a visible reversal than as a gap.
