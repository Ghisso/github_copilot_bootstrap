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
- [LEARN:security] Automated recovery must distinguish state that existed at
  entry from state created by the current operation. Auto-clean only an exact,
  observed orphan shape; preserve valid or unknown pre-existing state without
  mutation, and reserve broader abort/fallback cleanup for state the operation
  can prove it owns.
- [LEARN:testing] A regression test for a bug fix must FAIL if the fix is
  reverted. When the buggy code was "harmless" only because a lower layer
  already blocked the bad outcome (e.g. git rejecting a non-fast-forward push
  either way), assert on a marker unique to the fixed path (a new warning
  string) and on the absence of the old path's marker — outcome-only
  assertions can pass under both old and new code and prove nothing.
- [LEARN:testing] Recovery and control-flow regressions must also record the
  actual command invocations in a side channel or trace and assert their exact
  order. A successful outcome or shared diagnostic can pass when the old path
  still runs or when required fallback steps never execute.
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
- [LEARN:testing] Native acceptance needs three distinct evidence tiers:
  structural validation, executed native run, and unavailable/untrusted.
  Collapsing the third tier into a pass reports confidence never measured;
  keep it a `WARN` by default and non-zero only under `--require`.
- [LEARN:testing] Model prose cannot prove client routing metadata. Assert on
  client-reported agent type/model/effort fields, never on the model's own
  description of which agent or model it is.
- [LEARN:security] Trusted-project probes need a stable, operator-inspected
  workspace. Throwaway temp dirs cannot be manually trusted, and a probe must
  never approve project hooks or mutate user trust settings to make itself
  pass.
- [LEARN:testing] A/B acceptance must parse and compare control and candidate
  independently; one combined run cannot distinguish a real difference from a
  shared failure. Compatibility shims stay until repeated native PASS across
  supported client versions, not on documentation silence.
- [LEARN:testing] A probe that has never executed against its real target is
  untested code with a reassuring name. Phase I scored 100/100 offline while
  carrying three defects its first real run found immediately. Require at least
  one genuine execution before claiming an acceptance surface works.
- [LEARN:testing] Mapping every non-zero exit to a single diagnosis makes a
  tool assert what it never measured (a CLI argv bug reported as `untrusted`).
  Classify the failure precisely or report it as unclassified.
- [LEARN:tooling] Verify client provenance and version before trusting native
  results. An outdated third-party repackage (snap `codex` 0.114.0, publisher
  `jcat-nysasounds`, vs official 0.147.0) surfaced as `invalid type: map,
  expected a boolean` and looked like a repo config defect.
- [LEARN:tooling] Variadic CLI options silently consume positional arguments;
  pass prompts after `--`. Claude's `--disallowedTools` ate the probe prompt.
- [LEARN:testing] A check that asks every target the same question measures the
  targets' differences, not their correctness. Codex scopes instructions by
  directory (nested `AGENTS.md`, root -> cwd, one file per directory,
  `project_doc_max_bytes` 32 KiB); Claude and Copilot scope by glob. One shared
  question made a working system look intermittently broken.
- [LEARN:testing] Non-deterministic model output is a symptom to trace, not a
  flake to retry. Here it pointed at a scoped surface the generator never
  produced for Codex.
- [LEARN:testing] "Cannot be measured" is a finding, not a failure to deliver.
  Record why a gate is unmet with reproducible evidence rather than leaving it
  reporting a generic `unexercised` forever.
- [LEARN:testing] Never write a parser for an event shape you have not
  captured. When the payload is unobserved, write less code and document the
  gap; guessing is how a probe ships broken.
- [LEARN:config] A config key can be silently inert. Codex 0.147.0 exposes
  `collaboration.*` tools, so the MultiAgent V2 shim's
  `tool_namespace = "agents"` has no observable effect. Config presence is not
  config effect - verify against the running client.
- [LEARN:tooling] Least-privilege flags can preclude the behavior under test:
  Codex `--ephemeral` makes agent spawning structurally impossible
  ("collab spawn failed: no thread with id").
- [LEARN:testing] Twelve Codex child agents each misreported their own model as
  "GPT-5" while client session records showed all six routing correctly to
  sol/terra/luna at the configured efforts. Self-report is least reliable
  exactly where routing verification needs it most; read `payload.model` and
  `payload.effort` from `~/.codex/sessions` instead.
- [LEARN:tooling] A diagnostic that prints an inapplicable repair command makes
  a real failure unactionable. `check_runtime.py` flagged the dogfood drift
  correctly while its printed `install_bootstrap.py <consumer-repo>` fix can
  never target this repo (installer refuses overlapping source/target).
- [LEARN:architecture] `codex exec` has no persistent thread and cannot spawn
  agents at all; interactive CLI and the VS Code extension can. Interface
  choice, not client capability, decided what the probe could observe.
- [LEARN:documentation] Appending phases to a plan's frontmatter does not update
  the plan. Narrative sections are what a reader actually reads; a checklist
  entry explains nothing about why the plan grew or what it found.
- [LEARN:documentation] A wrong mechanism claim propagates across files ("spawn
  metadata through the `agents` namespace" appeared in three). Single-home
  volatile status in one dated record and point at it from everywhere else.
- [LEARN:tooling] `install_bootstrap.py --allow-self` refreshes this repo's own
  dogfood overlay (generated source inside the target); every other
  overlapping-root case stays rejected. Without it the bootstrap's own drift was
  permanently unfixable while `check_runtime.py` printed a repair command that
  could never work here.
- [LEARN:security] Check the nested `.claude/.gitignore` before treating a file
  as obsolete. `settings.local.json` is deliberately never synced, so removing
  it as an "obsolete owned file" was unrecoverable data loss in every consumer;
  it now belongs to `CONSUMER_STATE_PATHS`.
- [LEARN:testing] Running the installer once exposed three bugs a green suite
  missed: unrecoverable deletion, drift no refresh could clear (normalization
  applied to one filename only), and a freshly generated tree failing its own
  validator (the chmod loop globbed `*.sh`, skipping required
  `protect-files.py`).
- [LEARN:tooling] The refreshed fail-closed shell guard denies process
  substitution, heredocs piped into an interpreter, and write targets built from
  shell variables. Use literal paths and plain commands, or run a script file.
- [LEARN:architecture] A file living only in the generated `.claude/` overlay is
  not content, it is pending deletion. Authored material belongs in `shared/`,
  where it regenerates; `check_runtime.py` naming a path "absent from generated
  target" is the signal to promote it, not to restore it again. Shared skills
  must declare `visibility: public|background`.
- [LEARN:testing] Authoring-adapter preservation needs separate regressions for
  installer refresh and state restoration. A passing copy/update test does not
  prove the real restore script honors tracked root ownership.
- [LEARN:security] Native probes need explicit human authorization plus
  marker-owned writable HOME/XDG/client/tmp state around read-only generated
  inputs. Cleanup must unlink symlinks without chmod-following external auth.
- [LEARN:testing] Structured output is only transport validity. A planner
  workload passes only when every checklist item is true, artifacts match an
  exact frozen allowlist, and invented, duplicate, and expanded scope are zero.
- [LEARN:architecture] Audience-aware writing rules need one canonical policy
  with prompt pointers. Duplicating Caveman, exact-content, or documenter rules
  in workflow or agent prompts recreates contradictory authority.
- [LEARN:testing] Semantic prose validators should normalize whitespace and
  distinguish contradictory defaults from explicit prohibitions; literal line
  wrapping and broad keyword regexes create both false failures and false passes.
- [LEARN:security] Optional review metadata requires structural top-level JSON
  parsing. Flat text scans let nested finding fields forge or shadow gated
  metadata and counts.
- [LEARN:architecture] Conditional review routing needs deterministic hook
  triggers for control-plane paths, scripts/generators, dependencies, renames,
  nested manifests, and every multi-file diff; semantic complexity remains a
  reviewer decision.
- [LEARN:testing] Exemption tests must start from a clean fixture. A leftover
  documentation edit can silently turn an intended single-file ordinary case
  into the multi-file high-risk case it was supposed to distinguish.
- [LEARN:architecture] An AST symbol graph answers structural questions only
  where the relationship is a static call or import between named symbols. It
  cannot represent string-keyed pipeline wiring
  (`pipeline.add_component("result_joiner", ...)`), `import_module()` shims with
  `sys.modules[__name__]` rebinding, or identities built inside f-strings. Judge
  such a tool against the idioms the target repositories actually use, not
  against a generic call graph.
- [LEARN:quality] Score a candidate tool per question at its best reasonable
  effort, not at its default. Graphify returned zero edges on every
  mid-sized-repo question at the default `--budget 2000`; a 15x budget produced
  250+ edges. Applying escalation to one project but not another silently
  biases the comparison, which is exactly what review caught here.
- [LEARN:quality] A gate result is stronger when it states its own robustness.
  Recording that the decision is unchanged even if the single borderline
  question were scored the other way removes the incentive to argue that
  question and keeps the conclusion falsifiable.
- [LEARN:security] Prove a sandbox boundary with a positive control, not with
  an exit code. `--network none` plus a successful run only shows the tool never
  needed the network; a deliberate connect attempt failing with
  `OSError [Errno -3]`, and a deliberate `touch` refused with
  `Read-only file system`, are the actual evidence.
- [LEARN:workflow] Never write a cleanup or completion claim before performing
  the action. Ordering the write first creates false provenance even when the
  action follows immediately, and this artifact had already been corrected once
  for exactly that defect.
- [LEARN:tooling] The fail-closed Bash guard rejects multi-line shell with
  `for`/`while`/`{ }`/heredocs by raising `AmbiguousCommand` (exit 2). That is
  the classifier working as designed, not a broken hook. Put complex logic in a
  script file and invoke it as `bash script.sh`, which stays classifiable and
  keeps the guard active rather than routing around it.
- [LEARN:shell] Bash `errexit` is not reliable inside a function invoked from a
  status-tested context such as `if ! function_name`; explicitly guard each
  fallible command and return its failure so a later successful command cannot
  mask it.
- [LEARN:testing] When a fix moves an operation past an old control-flow
  boundary, arm fault injection only after a marker at that former boundary.
  Otherwise the test can fail an earlier invocation and never prove the timing
  change; also assert the marker precedes the fault and no downstream action ran.
- [LEARN:diagnostics] Follow-on warnings must describe the broad failure class
  accurately. Preserve cause-specific diagnostics instead of overwriting them
  with a generic message that falsely claims a conflict.
- [LEARN:security] Hand-parsed YAML-like lifecycle frontmatter needs semantic
  validation after syntax parsing. Validate real calendar/time values, reject
  multiline and YAML collection/list/comment/block-header shapes for prose,
  and pair adversarial rejects with accepted lookalike prose to prevent
  overblocking.
- [LEARN:quality] Treat cancellation evidence as an untrusted artifact chain:
  path construction, resolution, containment, symlink targets, file type,
  UTF-8 decoding, and exact same-line markers must all fail closed as
  accumulated validation errors rather than escaping as exceptions.
- [LEARN:documentation] Lifecycle templates and policies must state the exact
  constraints enforced by their validator; run DOCUMENT after review to
  reconcile the final hardened contract before score and closeout.
- [LEARN:security] Action-time gates must revalidate mutable lifecycle evidence
  immediately before granting commit, push, closeout, or branch actions; an
  earlier validator pass is not authorization for frontmatter or artifacts
  that can change afterward.
- [LEARN:security] When lifecycle state crosses multiple parsers, ambiguous
  duplicate gate keys must be rejected everywhere rather than resolved by
  first-wins versus last-wins behavior; one unique-key contract prevents a
  parser differential from bypassing obligations or advancing state.
- [LEARN:security] A gate that delegates validation to a runtime helper must
  fail closed on a missing runtime, exceptions, nonzero exits, and malformed
  protocol output, with a distinct regression test for every failure mode.
- [LEARN:recovery] A recovery that swallows its own failure converts a
  transient fault into a permanent one. `git rebase --abort 2>/dev/null ||
  true` cannot clear a half-initialized rebase; `--quit` can because it clears
  state without moving `HEAD`.
- [LEARN:recovery] `--autostash` is not free insurance. It can write the
  autostash commit and rebase directory before discovering new dirty state, so
  a self-writing repository can manufacture the latch it meant to avoid.
- [LEARN:observability] A warn-never-fail subsystem needs a health surface.
  Otherwise failure can remain invisible while unpublished work accumulates;
  `state-sync.sh status` now exposes the condition. See the dated incident
  record at `docs/2026-08-09-state-sync-rebase-recovery.md`.
- [LEARN:workflow] A lifecycle vocabulary gap forces falsification. Without
  `cancelled`, clearing a stopped plan required fabricated closeouts or an
  inaccurate `complete`; the Graphify record used the inaccurate status.
- [LEARN:security] Relaxing a gate is safe only when paired with a new
  requirement. Cancellation exempts commit, score, findings, and closeout only
  when an artifact-backed reason records the decision.
- [LEARN:planning] A NO-GO gate is a valid final result. Low measured value is
  a reason to stop, not a reason to add integration machinery or schedule
  another trial.
- [LEARN:documentation] Reconstruct incident duration from durable timestamped
  logs or reflogs, not planning estimates. Keep the exact volatile timeline in
  its dated incident record rather than portable MEMORY.
- [LEARN:security] A protocol allowlist must key on the method alone, never on
  `method && has(id)`. Gating on request shape leaves notifications and batch
  arrays falling through to the unvalidated forward path: a `tools/call`
  notification reached upstream with no allowlist and no version gate at all.
  Default-deny on message shape first, then dispatch on method.
- [LEARN:security] Bounding a security-relevant tracking map by evicting the
  oldest entry is fail-open: eviction untracks a still-pending request, so its
  later response bypasses the filter that entry existed to apply. Refuse new
  entries at capacity instead. I introduced exactly this regression while
  fixing an unbounded-growth note, and review caught it.
- [LEARN:security] Anti-forgery state must live outside every channel that can
  restore it. A provenance marker made only of public constants and a
  predictable path, stored inside the synced working tree, is forgeable by a
  hostile remote; bind it to a locally generated secret kept outside that tree,
  and ignore the secret's temp-file glob too, not just its final name.
- [LEARN:tests] An assertion that cannot fail is worse than no assertion,
  because it advertises coverage. `process.stderr.read(0)` always returns `""`,
  so a "must not be logged" check passed unconditionally. Prove a new guard by
  running its test against the pre-fix code and watching it fail.
- [LEARN:tests] When a regression's failure mode is a silent hang, assert with
  a bounded wait rather than a blocking read, so a future regression fails
  cleanly instead of stalling the suite.
- [LEARN:verification] Reconcile agent claims against the artifact, not the
  report. A subagent described this phase's own changed files as "pre-existing
  unrelated drift"; `check_runtime.py` disagreed, and it was a required gate.
- [LEARN:security] `trap ... RETURN INT TERM` in one bash call is not uniformly
  scoped: `RETURN` is function-local but `INT`/`TERM` are process-wide, so a
  handler referencing a function `local` survives the frame and aborts under
  `set -u`. Reset signal traps on every exit path, including early returns.
- [LEARN:tests] A comment asserting that a test guards an invariant is a claim
  that must be made true. When documenting deliberate duplication, add the
  equality test in the same change and prove it fails when one copy drifts.
- [LEARN:architecture] Duplication between shipped and authoring-only code is
  legitimate when the shipped copy must run without dependencies, but it needs
  both a recorded rationale and a test pinning the shared rules; otherwise it is
  indistinguishable from drift waiting to happen.
- [LEARN:security] Enforcing a version pin on one transport does not pin the
  dependency. A stdio `serverInfo.version` handshake made the Context Mode pin
  look complete while hook mode still executed whatever was on `PATH`. Enumerate
  every path that launches a pinned dependency, not just the one with the
  obvious handshake.
- [LEARN:security] A self-check that restates configuration proves nothing. It
  reported the required version as a PASS without ever observing the installed
  binary. Report the observed value alongside an explicit contract result, so the
  two can visibly disagree.
- [LEARN:architecture] Ownership follows the destructive operation. Accepting an
  arbitrary external cache path was harmless until quarantine started renaming
  directories; the remediation mechanism defines how far ownership may extend.
  Scope a renameable/writable location to what the tool created itself.
