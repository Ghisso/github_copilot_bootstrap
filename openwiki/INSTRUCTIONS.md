# Repository Brief for OpenWiki

## What this repository is

`github_copilot_bootstrap` is a reusable multi-target bootstrap for AI
coding agents, not an application. It packages the hooks, agents, skills,
and instruction files a Python AI engineering project wants available
across GitHub Copilot, Claude Code, OpenAI Codex, and Google Antigravity,
and keeps them consistent through one deterministic build-and-install
pipeline.

Four places hold different parts of the system. Keep them distinct:

- **Authoring source** (`shared/`) is what a maintainer edits: policies,
  agent prompts, skills, hooks, MCP config, templates, and scripts. Every
  real behavior change originates here.
- **Generated build output**, produced by `scripts/generate_targets.py`,
  has two targets: `dist/multi-agent/`, the rendered, installable copy of
  `shared/` for a full install, and `dist/sidecar/`, a small personal
  overlay (four skills and two instruction bridges). It is never
  hand-edited, and it is gitignored in this repository.
- **A consumer's outer repository** is any project that installs the
  generated bootstrap, in one of two modes. A full install owns the agent
  harness: it writes root entrypoint files (`AGENTS.md`, `CLAUDE.md`,
  `.mcp.json`, `.codex/**`) and a `.claude/` directory. A sidecar install
  (`--mode sidecar`) adds only Git-ignored skill and bridge files inside a
  team-owned repository, keeps its manifest in the Git directory, and never
  changes a tracked file.
- **The nested `.claude` ai-state repository** is its own separate Git
  repository living inside `.claude/`, on a branch named `ai-state`. It
  tracks both the installed bootstrap files and mutable AI state
  (`MEMORY.md`, plans, session logs, quality reports). The outer
  repository's own Git history never shows these commits; inspect them
  with `git -C .claude <command>`.

This repository also installs its own generated output into itself, to
develop and test the bootstrap end to end (`scripts/install_bootstrap.py
--allow-self`). Do not describe that self-install as how a normal consumer
project works — a normal consumer only ever receives the generated copy,
never `shared/`.

## What to prioritize

Ground every page in what the current code and tests actually do, in this
order of authority:

1. `shared/`, `scripts/`, and `tests/` — the real source and its test
   coverage.
2. `README.md` and `docs/architecture.md` — maintained, current
   human-authored explanation.
3. `shared/policies/*.instructions.md` and `shared/skills/*/SKILL.md` — the
   normative rules and reusable workflows agents follow.

Cover, at minimum:

- the lifecycle: PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT ->
  VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH;
- the agent roster (orchestrator, planner, coder, reviewer, documenter, and
  the target-specific extras) and how each specialist gets its prompt;
- the skill library and the contract `scripts/validate_targets.py`
  enforces on it;
- the hook dispatcher and guardrail scripts under `shared/hooks/`;
- how `scripts/generate_targets.py` renders `shared/` into a target;
- how `scripts/install_bootstrap.py` and `scripts/check_runtime.py`
  establish and check consumer ownership (which files are
  bootstrap-controlled versus consumer-owned);
- the two install modes: mode detection and its refusals in
  `scripts/install_bootstrap.py`, the sidecar planner and apply step in
  `scripts/sidecar_overlay.py` (manifest, `info/exclude` block, ignore
  gate, atomic moves, team precedence, the preserved-copy folder, and
  `--uninstall`), and batch updates in `scripts/update_consumers.py`,
  which finish every target and report failures at the end;
- the Git-backed AI-state sync described above
  (`shared/hooks/scripts/state-sync.sh`);
- the Context Mode dispatcher's security model: cache quarantine by the
  provenance secret, `CONTEXT_MODE_DIR` containment, and the version-pin
  self-check (`shared/hooks/scripts/context-mode-dispatch.sh`, README's
  "Optional Retrieval Helpers").

## Page style

Write every page in plain, direct prose. A new maintainer should be able to
read a page once and act on it.

**Structure**

- Open every page with one sentence naming its authority: source, tests, and
  the policies under `shared/policies/` outrank the page.
- Lead with the answer or the mechanism first, then add detail. Do not build
  up to the point.
- Define an uncommon term the first time you use it. A short parenthetical
  is enough.
- Close every page with a short "Related pages" list linking pages that cover
  a neighboring topic.

**Sentences and words**

- Write one idea per sentence. Aim for about 20 words per sentence.
- Keep paragraphs to two or three sentences. Start a new paragraph for a new
  idea.
- Use common words. Avoid idioms and invented labels; if the source uses a
  specific term, use that exact term instead of a paraphrase.
- Do not use em-dashes, except inside a backtick-quoted exact required string, where the
  literal character must be reproduced.
- Do not hard-wrap prose at a fixed column. Let one sentence run as long as
  it needs to; the renderer wraps it for the reader.

**Lists and tables**

- Use a bulleted list when you state several facts that are parallel, such as
  a set of guards or a set of log files.
- Use a numbered list when the order matters, such as steps in a sequence.
- Keep each list item to one or two sentences.
- Use a table only for genuinely tabular data, such as a mapping of targets
  to files. Do not hard-wrap text inside a table cell; keep each cell on one
  line.

**Diagrams**

- Add one Mermaid diagram, in a fenced ```` ```mermaid ```` block, when the page
  covers a flow, a lifecycle, an ownership boundary, or a call sequence. Add it
  only if the diagram is clearer than prose.
- Write one plain sentence right before the diagram that says what it shows.
- Keep node labels short, a few words at most. Prefer `flowchart` for a
  pipeline or a boundary and `sequenceDiagram` for a call sequence between
  components.
- Example, at the size a page diagram should be:

  ```mermaid
  flowchart LR
      A[Request] --> B[Guard]
      B --> C[Handler]
      C --> D[Response]
  ```

**Code, paths, and enforcement**

- Put every command, exact error message, and path the reader must open in a
  fenced code block or in backticks.
- Name a specific file only when the reader needs to go open it. Do not name
  every file that happens to be involved.
- When a rule you state is enforced by a hook, a validator, or a test, say so
  in the same sentence. This lets the reader tell an enforced rule from a
  written policy. For example: "A new branch must be named
  `<plan_name>_implementation`, which `enforce-branch-state.sh` checks before
  allowing the branch to be created."

## Historical records are not current behavior

Treat the following as evidence of past decisions only, never as a
description of what the code currently does. Re-derive current behavior
from `shared/`, `scripts/`, and `tests/` instead:

- `.claude/plans/` and `.claude/session_logs/` — this checkout's own
  completed and in-progress plans and session logs;
- files under `docs/` named `docs/2026-*` — dated, point-in-time spikes and
  review records;
- the root-level `plans/` directory — architecture decision records and
  historical phase plans.

A plan or session log can describe a decision a later phase reversed or
refined. Only the current source and tests are authoritative.

## Do not do

- Do not treat this brief, or anything generated under `openwiki/`, as more
  authoritative than `shared/`, `scripts/`, `tests/`, or the policies under
  `shared/policies/`.
- Do not describe the devcontainer or CI as something every consumer runs;
  both are optional.
