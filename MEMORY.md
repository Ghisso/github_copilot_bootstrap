# MEMORY.md — Cross-Session Learning Notes

<!-- Project-specific state for this bootstrap repository. -->

## Domain-Specific

- [LEARN:domain] This repository is a source-of-truth multi-target agent
  bootstrap, not a Hydra/BentoML/Haystack/Gradio application. Generated output
  is `dist/multi-agent/`; durable project findings are in
  `.claude/instructions/project-context.instructions.md`.

## Workflow

- [LEARN:workflow] An implementation branch named `<slug>_implementation`
  requires a matching `.claude/plans/<slug>.md` big plan; a governing design
  under top-level `plans/` does not satisfy the commit lifecycle gate.
- [LEARN:workflow] Configuration and validator allow-list migrations should be
  one atomic phase when the previous validator rejects the new contract, so
  every phase boundary remains green.
- [LEARN:quality] The authoring repository uses `scripts/validate_targets.py`
  as its adversarial suite. Keep `tests/test_validate_targets.py` as the
  pytest integration entrypoint so the canonical quality scorer exercises that
  real suite instead of reporting a false no-tests failure.
- [LEARN:runtime] Codex 0.144.x MultiAgent V2 hides custom-agent spawn routing
  metadata by default. Set
  `[features.multi_agent_v2].hide_spawn_agent_metadata = false` and
  `tool_namespace = "agents"` so named `.codex/agents/*.toml` model and effort
  overrides reach child threads instead of inheriting the parent session.
- [LEARN:installer] Generated seeds for consumer-owned mutable state must be
  copy-if-absent. State migration and git history cannot protect content that
  the installer overwrites before synchronization begins.
- [LEARN:installer] A warn-never-fail sync hook cannot prove an installer
  preserved state; the installer must verify nested Git postconditions before
  copying generated files. Local-only promises also need Git Trace2 coverage,
  because unchanged remote refs prove no push but not no remote read. See
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`.
- [LEARN:testing] Cover state-sync entry points directly from the generated
  `.devcontainer` copy: installer coverage cannot prove that `pull
  --local-only` initializes a fresh nested repository or that an invalid
  `AI_STATE_REPO_ROOT` falls back to the consumer root.
- [LEARN:quality] The commit gate's `content_hash` is `git hash-object` of
  `git diff <base>`, which excludes untracked files. Stage every file destined
  for the commit BEFORE running `quality_score.py`/`record_findings.py`, or the
  report's hash and `changed_files` will not match what the gate recomputes at
  commit time (and `dirty` will be `true`, which the gate rejects).
- [LEARN:domain] `state-sync.sh` `cmd_pull` must return non-zero on a rebase
  conflict and `cmd_push` must guard its push on that result; otherwise a push
  is attempted after an aborted rebase and rejected non-fast-forward. The
  top-level dispatch still converts the non-zero return into a warning +
  `exit 0` so hooks never block Codex shutdown. The same guard now applies to
  `cmd_migrate` via `commit_and_reconcile` returning non-zero on merge abort
  (phase-3); `cmd_setup` keeps ignoring that result since it never pushes.
- [LEARN:testing] A regression test for a bug fix must FAIL if the fix is
  reverted. When the buggy code was "harmless" only because a lower layer
  already blocked the bad outcome (e.g. git rejecting a non-fast-forward push
  either way), assert on a marker unique to the fixed path (a new warning
  string) and on the absence of the old path's marker — outcome-only
  assertions can pass under both old and new code and prove nothing.
- [LEARN:domain] AI-state durability must not depend on a `Stop` event: browser/
  editor tab closure does not guarantee Stop fires. The durable checkpoints are
  the `post-commit` git hook (best-effort push after every outer commit) and the
  explicit "AI state: push" VS Code task; Stop stays a best-effort checkpoint.
- [LEARN:quality] Structural checks over generated text must assert the literal
  invocation (e.g. `'"$STATE_SYNC" push'`), not loose independent substrings — a
  stray word in a comment (`cmd_push`) can satisfy `"push" in text` and mask a
  regression. Guard any unconditional `read()` of a required-but-maybe-missing
  file so a miss is a clean accumulated failure, not an uncaught exception.
- [LEARN:workflow] Never create a tracked worktree diagnostic before
  reconciling unrelated histories: the diagnostic itself can cause a merge
  conflict or dirty-tree refusal. Capture the evidence externally, reconcile,
  then append and checkpoint the diagnostic afterward.
- [LEARN:testing] A no-I/O Git Trace2 test must first assert that the trace
  exists and contains parseable start events before checking that forbidden
  remote commands are absent; otherwise an empty or unreadable trace can make
  the absence assertion pass vacuously.
- [LEARN:workflow] A clean-only publication retry can deadlock behind its own
  tracked failure diagnostics. Prompt/retry boundaries must checkpoint and
  then publish (`push`), or store diagnostics outside tracked state. This is
  required whenever a failed publication writes its diagnostics into a tracked
  file before the next retry boundary.
- [LEARN:testing] Exact generated hook-schema validation must check handler
  types and reject extra fields, not only command text. Shared test mechanics
  may be parameterized, but production wrappers remain platform-specific where
  their output contracts differ.
- [LEARN:installer] Dry-run output is part of the safety contract: preview
  paths must never claim that files, hooks, or trust state were applied.
  Distinguish "would install or update" from completion wording in direct and
  batch installer flows.
- [LEARN:quality] Generator verification must run after concurrent source and
  documentation edits settle. A stale ignored `dist/` tree can create a false
  determinism failure even when two fresh generations are byte-identical.
- [LEARN:workflow] Phase closeout gates read the small-plan frontmatter status
  as well as checklist prose; set `status: complete` only after verification,
  review, score, documentation, and learning evidence are recorded.
- [LEARN:workflow] After an atomic phase commit lands, reconcile the phase
  checklist, session log, and big-plan checklist from the actual commit SHAs;
  do not infer completion from a clean outer worktree alone.
- [LEARN:installer] Runtime ownership metadata must be inert, mode-aware, and
  single-sourced. Persist the active install mode, remove paths that become
  inactive during migrations, and generate restoration allowlists from the
  same Python contract instead of duplicating them in shell.
- [LEARN:testing] Ownership/pruning suites must cover equal or overlapping
  installer roots and nested `.git` in both directory and gitfile forms. Normal
  generated-target tests do not expose recursive self-copy or worktree metadata
  deletion failures.
- [LEARN:architecture] Generated root guidance should be a compact discovery
  entrypoint, not a concatenated policy mirror. Keep lifecycle and safety gates
  explicit, then route conditional detail to the canonical scoped policies.
- [LEARN:testing] Context-budget work needs structural regression checks, not
  only size assertions: enforce unique sections, one canonical phase sequence,
  installer substitutions, and deterministic regeneration together.
- [LEARN:architecture] Cross-client policy portability needs neutral authoring
  metadata plus target-native projections. Claude can express glob-scoped rules;
  Codex must use its documented directory hierarchy or skills instead of a
  fabricated glob surface.
- [LEARN:documentation] Describe structural adapter parity separately from
  native-client loading evidence. Generation tests prove shape and scope data;
  authenticated client probes belong in a later acceptance phase.
- [LEARN:codex] Treat documented configuration syntax, parse success, and
  observed named-agent routing as separate evidence classes. A current schema
  cannot by itself retire a compatibility shim that fixed a historical runtime
  routing failure.
- [LEARN:testing] Routing-shim removal and nesting-limit removal need different
  native probes: exact role/model metadata does not prove that child agents
  cannot spawn grandchildren.
- [LEARN:codex] Project custom-agent `developer_instructions` should embed the
  canonical transformed role contract directly. Requiring a spawned agent to
  read a Claude-native agent file adds avoidable tool dependence and can leave
  the role under-specified before its first read.
- [LEARN:config] Omit per-agent MCP and skill tables when Codex's documented
  parent inheritance is intended; duplicating them creates shadow configuration
  and another drift surface.
- [LEARN:security] Phase F confirmed protected-file shell guards should classify proven read-only
  operations and concrete mutation targets, then fail closed for opaque syntax
  containing any protected literal. Cover wrappers, interpreters, combined
  flags, newlines, and protected-source copies as explicit regressions.
- [LEARN:testing] A sequential safety wrapper needs two acceptance layers:
  structural validation of the exact child order and isolated fixture guards
  that prove ordering, first-decision short-circuiting, and malformed-output
  fail-closed behavior.
- [LEARN:workflow] Keep one normative task-lane table in the workflow policy.
  A low-risk one-file edit can stay in the main thread only when no commit or
  PR is requested; commit-bound work and every high-risk trigger upgrade to the
  orchestrated lifecycle regardless of apparent simplicity.
- [LEARN:architecture] Target-native path projection must preserve shared
  control-plane surfaces that coexist in every consumer, such as
  `.github/hooks/`; validate them in both root and scoped workspace guidance.
- [LEARN:security] Portable project memory is curated, synced, and visible to
  every reader of its state remote; native client memory is local advisory
  scratch. Sensitive material belongs in approved protected-data systems,
  never either memory layer.
- [LEARN:testing] Consumer-owned memory preservation needs binary byte-for-byte
  coverage across refresh and legacy migration, including the nested Git
  object, not only text markers in a broad installer scenario.
