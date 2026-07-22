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
