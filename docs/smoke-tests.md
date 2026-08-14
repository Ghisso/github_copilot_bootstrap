# Smoke Tests

## Deterministic Generation

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

Expected:

- Validator prints `PASS generated target is structurally valid`.
- Re-running generation does not change generated output.

## Custom Agent Portability

Expected:

- GitHub Copilot has exactly the 6 universal `.github/agents/*.agent.md` files.
- Claude Code has exactly the same 6 universal `.claude/agents/*.md` files.
- OpenAI Codex has exactly 8 `.codex/agents/*.toml` files: the 6 universal
  agents plus Codex-only `luna_coder` and `sol_coder`.
- Neither Codex-only agent appears in `.claude/agents/` or `.github/agents/`,
  and omitting either one from `.codex/agents/` fails validation.
- Each Codex `developer_instructions` field has exactly one generated delimiter
  and embeds its exact target-transformed role body; it must not instruct the
  agent to read `.claude/agents/<id>.md`.
- A normal agent's Codex supplement is appended once to its own prompt. A
  derived coder prompt is exactly the transformed `coder` base, one literal
  role-supplement delimiter, and the transformed specialist supplement. Missing
  or duplicate supplements, copied complete bases, recursive or multi-level
  composition, cycles, and delimiter drift fail validation.
- `agent.yaml` remains the source of model/effort metadata. Codex agent TOMLs omit per-agent MCP and skill overrides and therefore use the trusted project's `.codex/config.toml` registrations.
- Structural checks record actual instruction sizes for all eight Codex roles.
  These values are observability, not an official Codex size limit or a static
  delivery claim. Native probes are the only delivery evidence.
- Codex leaves the interactive session model and effort unpinned; every custom agent emits the exact model and effort from its canonical `model_intent.openai-codex` object.
- The generated Codex matrix is orchestrator Sol/xhigh, planner Sol/xhigh,
  reviewer Sol/high, coder Terra/high, documenter Luna/medium, verifier
  Luna/low, `luna_coder` Luna/xhigh, and `sol_coder` Sol/xhigh. Claude and
  GitHub Copilot keep their existing six-agent model declarations.
- The named escalation graph is exactly
  `luna_coder -> coder -> sol_coder`, with no successor for `sol_coder`.
  Missing or ineligible successors, cycles, self-retries, Luna-to-Sol skips,
  Luna/max, model/effort drift, and spawn-time model or effort override wording
  fail validation.
- The Codex orchestrator prompt contains its supplement exactly once. It
  requires the bounded packet and all five Luna-selection conditions, the exact
  five-field escalation object and six-value `reason` enum, preservation of a
  prior diff, one named recovery per tier, and a final stop after Sol.
- Failure attribution has exactly four categories. Only `implementation`
  advances automatically; `environment` and `baseline` stop model escalation,
  and `indeterminate` returns to orchestrator judgment. Extra categories,
  alternate list markers, unmatched prose, missing stop behavior, and invented
  attribution fail validation.
- `reviewer` runs its own passes with no helper agents: a primary pass, then a verification pass that receives the primary findings and refutes each (dropping any that do not survive re-verification, converging when a pass yields nothing new twice or after 3 rounds). An orchestrated review therefore completes and can PASS a PR gate identically on GitHub Copilot, Claude Code, and OpenAI Codex (no dependence on subagent nesting depth).
- The generated output mirrors every repository skill under `.claude/skills/`.
- Every agent prompt points to the [canonical audience-aware reporting policy](../shared/policies/agent-reporting.instructions.md);
  prompts do not duplicate its Caveman or human-facing prose rules. The policy
  keeps exact technical material unchanged and treats any rewrite stage as
  optional.
- The generated output contains the pinned Ponytail coding/review skills plus its MIT license and `v4.8.4` provenance.
- The generated output mirrors every review profile under `.claude/review-profiles/`.
- OpenAI Codex has one enabled `[[skills.config]]` entry per `.claude/skills/<name>`.
- Codex config sets `agents.max_concurrent_threads_per_session = 6`, omits legacy `agents.max_threads` and redundant `agents.enabled`, retains `max_depth = 1`, and retains both required `[features.multi_agent_v2]` metadata-routing values.
- `dist/` contains `multi-agent/` and no obsolete `github-copilot/`, `claude-code/`, or `openai-codex/` generated target directories.
- The generated output has no obsolete `.github/skills/`, `.agents/skills/`, `.codex/skills/`, or target-local state directories.
- Claude and Codex outputs do not contain Copilot model pins.
- Codex does not generate deprecated `.codex/rules/` output.
- Generated output contains `MEMORY.md`, workflow directories, templates, prompts, hook scripts, and `quality_score.py` in the shared `.claude/` basis.
- A fresh install seeds `.claude/MEMORY.md`; repeat installs and legacy pre-git migration preserve an existing consumer `MEMORY.md` byte-for-byte.
- Generated output contains `templates/plan-big.md`, `templates/plan-small.md`, and `templates/session-log.md`.
- Generated output contains `.devcontainer/devcontainer.json`, `.devcontainer/Dockerfile`, `.devcontainer/post-start.sh`, `.devcontainer/state-sync.sh`, and `.devcontainer/restore-root-adapters.sh`.

## MCP Routing

Expected:

- GitHub and Claude JSON MCP files include `semble`, `context7`, and `context-mode` (routed through `bash .claude/hooks/scripts/context-mode-dispatch.sh server`).
- Codex config includes `[mcp_servers.semble]`, `[mcp_servers.context7]`, and `[mcp_servers.context-mode]`, all three targets sharing the same dispatcher route.
- The filtered Context Mode MCP surface advertises exactly `ctx_index`, `ctx_search`, `ctx_stats`, and `ctx_doctor`; every other tool (`ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`, `ctx_fetch_and_index`, `ctx_upgrade`, `ctx_purge`, `ctx_insight`, and any unknown tool) is filtered out of `tools/list` and rejected locally before reaching upstream.
- Tool-routing policy preserves:
  - direct reads for known paths
  - `rg` for exact literals
  - Semble for semantic discovery
  - the four guarded Context Mode MCP tools alongside its lifecycle hooks, both routed through the dispatcher and pinned to `1.0.169`
  - context7 for current external library API documentation
  - no duplicate broad searches

## Scoped Policy Adapters

Expected:

- Every `shared/policies/*.instructions.md` policy declares scope with the
  target-neutral `applicability` schema: `always` or an explicit list of
  repository-relative patterns; `applyTo` never appears in shared authoring.
- Every policy is installed canonically under `.claude/instructions/`.
- Conditional policies generate equivalent Claude `.claude/rules/` `paths` and
  Copilot `.github/instructions/` `applyTo` scopes; always-on policies consume
  neither a Claude conditional rule nor a Copilot `applyTo` field.
- Codex generates no `.codex/rules/` and no nested `AGENTS.md` for the current
  mixed/glob/file-specific policy scopes. Their non-widening fallback is the
  corresponding enabled `.claude/skills/` workflow.
- The root `AGENTS.md` remains below Codex's default 32 KiB combined project
  guidance limit, and `CLAUDE.md` remains at or below 200 lines.
- These are structural generation checks. Real Claude, Codex, and Copilot
  adapter-loading probes are covered by `scripts/check_native_clients.py`.
- In particular, these checks do not prove current native Codex routing for all
  eight declared roles. The [dated compatibility record](2026-08-08-codex-routing-compatibility.md)
  preserves the historical six-role observation and defines the native-evidence
  boundary and removal gates; `max_depth` has a separate gate.

## Native Client Acceptance (Opt-In)

As of 2026-08-09, `--planner-workloads` records PASS for Codex 0.147.0
Sol/xhigh micro 23.514s (exact 2/2), bounded-full first result-schema 28.519s
and same-workload manual rerun 33.771s (exact 3/3), and Claude Code 2.1.226
Opus/xhigh micro 15.912s (exact 2/2), full 13.341s (exact 3/3). Both are 4/4
with zero invented, duplicate, or scope expansion findings. Aggregate-only
strict-schema event fields are `null` when unobservable. Marker-owned
preparation never changes project trust or hooks. The Codex rerun followed a
concrete transport/schema variance and argv fix; it is not an automatic retry.
Known `compact_resume`/role-matrix WARNs can make `--require` nonzero without
invalidating these independent workload PASS results.

The deterministic checks above do not start native clients or need their
credentials. The probe's default temporary mode is also only a structure and
missing-client smoke: it intentionally does not launch a client and reports an
installed client as unresolved `WARN`/`untrusted`. For real native evidence,
prepare and manually trust a dedicated stable workspace before running:

```bash
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe --prepare-only --json
# Inspect the workspace and trust it manually in the client, then:
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe \
  --client codex --require --json
```

Without `--require`, a missing, unavailable, timed-out, or untrusted requested
client is `WARN`; with it, that result is `FAIL`. The probe uses a temporary
read-only control/candidate consumer pair, never approves hooks or mutates
project trust, and emits only fixed schema-v2 sentinels and event-backed check
state. `--require` also promotes unresolved `WARN` evidence to a nonzero
result. Exact Codex routing can PASS only from explicit client JSONL
agent/thread/subagent metadata; model prose or an absent event is not proof.
The current declared matrix contains eight roles, while the dated 2026-08-09
observation contains six. Future optional persistent-thread runs may exercise
all eight without becoming required verification for this feature.
Compact/resume and coder escalation currently remain unexercised WARNs. See
[Native Client Acceptance](native-client-acceptance.md). Preparation refuses
broad or nonempty unmarked paths and refreshes only marker-owned inputs; it
never approves or changes trust.

## Hooks

Expected:

- Guardrail scripts exist under `.claude/hooks/scripts/`.
- Claude `PreToolUse` has native mutation (`Edit|MultiEdit|Write`), ordered `Bash`, and wildcard observability matcher groups; Codex has the equivalent `Edit|Write`, `Bash`, and wildcard groups. `Read` and MCP tools do not invoke mutation guards.
- `protect-files.sh` requires direct `python3` classification (not `uv run`) and denies protected files through structured write tools and per-segment Bash writes such as `touch .env`; absence of Python, malformed input, or classifier ambiguity fails closed. A read-only `cat`/`git diff` inspection of a protected configuration remains allowed.
- Copy/install/move commands that resolve to a protected source as well as a destination are denied, including sources selected through shell-expanded wildcards, `cd`, Git `-C`, or symlinks, preventing protected-source exfiltration through a write-bearing command.
- Unknown, archive, and interpreter-style commands are denied only when they carry a high-confidence protected path literal: `.env*`, `uv.lock`, `credentials*`, `.pem`/`.key`, a hook path, or protected hook configuration. Prose and ordinary source filenames containing `secret` remain allowed. Their safe parsing failure still fails closed; the explicit read-only command set remains allowed.
- `pretool-bash-guard.sh` runs protected-file, dangerous-Git, branch, commit, then PR guards in that exact order and returns the first safety decision. A guard failure or malformed safety output fails closed.
- Hook config edits through native tools, Bash redirection, or in-place edits are protected, with Codex denying and Claude asking for approval. Missing redirect targets and ambiguous commands fail closed.
- Wildcard context-mode observability is separate from the safety lane and makes no safety decision or mutation.
- Hook configs invoke `.claude/hooks/scripts/` and pass an explicit target id.
- Generated `run-hook.sh` is executable because Claude and Codex hook commands call it directly.
- Branch creation is allowed only from clean `dev` into `<plan_name>_implementation`, including `checkout -b`/`-B` and `switch -c`/`-C`/`--create`/`--create=<branch>` forms.
- Normal commits are blocked until the current small plan is complete, the session closeout log is completed, `[LEARN]` evidence exists, and a fresh score >= 90 report matches the branch, phase, base ref, merge-base SHA, HEAD SHA, target, dirty flag, and changed-files metadata.
- Commit closeout advances plan state only when the intercepted commit subject can be correlated with `HEAD`.
- PR creation uses `--base dev`, and implementation-branch pushes are blocked until every phase is complete or fully evidenced as cancelled and at least one phase is complete.
- SessionStart hooks in a configured consumer retain `state-sync.sh pull` for mutable AI state on the git-backed `ai-state` branch. Codex and Claude Stop each use one sequential wrapper: session log, session-log check, `checkpoint`, then best-effort `publish`; no event uses concurrent checkpoint/publish handlers. Codex emits one valid JSON response with no child stdout; Claude emits no wrapper stdout.
- Codex and Claude `UserPromptSubmit` use compatible `push` as a 60-second checkpoint-and-publish retry. Codex delayed, best-effort `SessionEnd` uses only network-free `checkpoint` with timeout `3`; Claude `StopFailure` also checkpoints locally, while Claude `SessionEnd` uses compatible `push` with timeout `60`. Failed publication preserves the local commit for a later retry.
- The generated `post-commit` git hook retains `state-sync.sh push` after every successful outer-repo commit; git ignores its exit status, so a sync failure never blocks or fails the commit. `checkpoint` is the explicit network-free local durability operation.
- Missing `context-mode`, `npx`, or `uvx` reports warnings only.
- `context-mode-dispatch.sh --self-check` reports `required-version=1.0.169`, `resolved-path`, `observed-version` when it can be determined, and a `version-contract` result. A `context-mode` on `PATH` that is not provably `1.0.169` is reported as a failing contract and is never executed; hook mode then uses the pinned `npx context-mode@1.0.169` fallback, or warns and fails open when that is unavailable too.
- `CONTEXT_MODE_DIR` is honoured only at or beneath `.claude/.cache/context-mode`. Any other absolute path — inside the repository or external — warns and falls back to the project-local cache, and the refused path is never created, stamped with a provenance marker, or renamed to a `.untrusted.*` sibling.
- GitHub Copilot hook config remains native at `.github/hooks/hooks.json` but calls shared `.claude` scripts.
- `.claude/hooks/git-hooks/commit-msg` exists and is executable in generated output.
- With `core.hooksPath` set to the generated `git-hooks` directory, on a `<plan_name>_implementation` branch: a `git commit` with no score report, a score below 90, a stale `content_hash`, an incomplete small plan, a closeout log missing `**Status:** COMPLETED`, or missing `[LEARN]` evidence is each rejected by git; a fully valid commit succeeds.
- The `git ci` alias (`git config alias.ci commit`) and `git -C <path> commit` invoked from outside the repo are rejected identically to a bare invalid `git commit` — there is no command string for either to evade.
- Commits on `dev`/`main` pass through the `commit-msg` hook regardless of ceremony state.
- `git commit --no-verify` bypasses the `commit-msg` hook on an implementation branch — the documented, sanctioned escape.
- `.claude/hooks/git-hooks/pre-push` exists and is executable in generated output; it shares `assert_push_invariants` with `enforce-pr-gate.sh`.
- With `core.hooksPath` set to the generated `git-hooks` directory, pushing a `<plan_name>_implementation` ref with an incomplete or invalidly cancelled small plan, no completed phase, too few commits for completed phases, or an unacknowledged bypass log is rejected by git and names the phase; a push with at least one completed phase and full evidence for every cancelled phase succeeds, and findings bind to the last completed phase.
- Pushing `dev`/`main`, or deleting a branch (`git push origin :foo_implementation`), passes through `pre-push` regardless of ceremony state.
- `git push --no-verify` bypasses `pre-push` on an implementation branch — the same sanctioned escape as the commit layer.
- `gh pr create --base dev` is checked only at the `PreToolUse` layer; `pre-push` has no PR-creation concept.
- A valid score report with no matching `findings-*.json` report blocks the commit.
- The coder's implementation path applies Ponytail `full` once, then performs a
  changed-scope simplification and re-verification; lifecycle output has no
  standalone Ponytail phase.
- The `ponytail` review profile is required for deterministic control-plane or
  other high-risk/multi-file/dependency/script/generator work, and for
  reviewer-selected complexity. An exemption is exactly one documentation OR
  one mutable workflow-state file, only when no control-plane/high-risk
  condition applies; every multi-file diff is high-risk.
- Selecting the profile always emits `ponytail_reviewed: true` and a numeric
  `ponytail_findings` count. New unselected reports omit both fields; optional
  diffs can read compatible legacy `false`/`0` reports, while high-risk routing
  requires true evidence.
- Ponytail findings follow ordinary severity gates: `CRITICAL` blocks commit,
  `MAJOR` blocks push/PR, and `MINOR` is advisory. There is no zero-Ponytail
  gate.
- A findings report with any `CRITICAL` finding blocks the commit, and the failure message names the finding's title.
- A stale findings `content_hash` (edited since the reviewer generated it) blocks the commit, mirroring the score report's freshness check.
- Two findings reports for the same branch/phase select the newest by `generated_at`, not filename — a lexically-later but older clean report loses to a lexically-earlier but newer report containing a `CRITICAL` finding.
- A findings report with `counts.critical == 0` but `counts.major > 0` allows the commit (the commit gate only checks `critical`) but blocks the push, naming a `MAJOR` finding.
- A findings report generated pre-commit (its `head_sha` is the certified commit's parent) still satisfies the push gate, since `pre-push` accepts any ancestor of the pushed commit, not only an exact match.
- All-zero findings counts (`critical`, `major`, `minor` all `0`) allow both the commit and the push.

## Devcontainer And Git-Backed State Sync

Expected:

- `.devcontainer/` is trackable and generated AI content is ignored by the installer.
- The generated devcontainer forwards `HF_TOKEN` and `HUGGING_FACE_HUB_TOKEN` (for the projects' own Hugging Face use, not AI state sync).
- The generated devcontainer does not require `/dev/fuse` or apparmor overrides, and still includes the `SYS_ADMIN`/`seccomp=unconfined` run args needed by `bubblewrap`.
- `state-sync.sh` resolves the nested `.claude/` repo's remote from `AI_STATE_REMOTE` / `--state-remote` at install time / the outer repo's own `origin` (no separate credential), warns and stays local-only when none is configured, and never fails a hook or session on a sync problem.
- `state-sync.sh` accepts `setup`, `pull`, `checkpoint`, `publish`, `push`, `status`, and `migrate-from-hf`. `checkpoint` commits locally without remote Git I/O; `publish` sends only clean, already committed state and refuses a dirty worktree; `push` remains checkpoint then publish.
- Operational commands write no plain stdout; diagnostics remain on stderr and failures continue to `.claude/session_logs/hooks-errors.log`. `status` is the exception: it is read-only and network-free, reports local/cached state and the error-log path, and never exposes a remote URL or credentials.
- `install_bootstrap.py <repo>` (no bucket flag needed) sets `git -C <repo> config core.hooksPath` to `.claude/hooks/git-hooks`, leaves `commit-msg` executable, and creates+pushes the nested `.claude/` ai-state repo with a `bootstrap:`-prefixed commit; `--state-remote <url>` pushes to that remote instead of `origin` and persists it into `.devcontainer/devcontainer.json`.
- `install_bootstrap.py <repo> --local-only` and `update_consumers.py --local-only <repo>` refresh every bootstrap-controlled file and leave nested `ai-state` committed and clean without fetch, `ls-remote`, pull, merge, or push. For pre-git state, history contains `migrate: import pre-git state` before the bootstrap commit; output includes nested status and a shell-safe manual publish command.
- The default installer and updater retain their human-operated commit-and-push behavior; legacy migration is initiated by the installer, not by a separate updater migration step.
- Direct installs and per-consumer batch updates identify `.codex/hooks.json` and Codex for VS Code project-hook trust as content/hash-bound, instruct users to reopen/reload and review/reapprove when prompted, and never approve hooks or mutate user trust settings. This applies to default and `--local-only` paths; dry-run output previews the potential trust action without claiming hook content changed.
- A root `.github/` self-install overlay passes source-layout validation only when ignored and byte-identical to generated output. Tracked, unignored, and stale overlays fail.
- `post-start.sh` runs `state-sync.sh setup` before setting `core.hooksPath`, then `state-sync.sh pull` and `restore-root-adapters.sh`; the checkout inside `setup` already carries the correct executable bits for `.claude/hooks/git-hooks/*` (git preserves them, unlike the retired HF bucket sync).
