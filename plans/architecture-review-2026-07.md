# Architecture Review — July 2026

**Review date:** 2026-07-03
**Reviewed commit:** `9b80b3d8b5f9dd9f85dc6d70298e10f38d1417ee` (branch `dev`, clean tree)
**Method:** four independent research passes (agent system; hook layer; lifecycle/policies/generator/sync; upstream benchmark + platform documentation), followed by first-hand spot verification of every load-bearing citation. All `path:line` references are valid at the reviewed commit.
**Scope:** review only. Recommendations are formatted to map directly onto this repo's big-plan/small-plan templates; no code changes accompany this document.

**Boundary conditions set by the author:**

1. The orchestrator handles non-trivial work only. This review proposes no trivial-task fast paths and no orchestrator bypasses.
2. The bootstrap is personal, not generic. Stack-specific policies (Hydra, BentoML, Haystack, Gradio, GPU devcontainer) and library-specific micro-skills are deliberate assets and are not treated as defects. The one configuration item the author has flagged for change is the hardcoded Hugging Face bucket name.

---

## 0. Post-implementation verification — 2026-07-07

All 31 recommendations were implemented (one commit each) and independently re-verified on 2026-07-07 at commit `e3054e6` (branch `debloat-and-drift`). Verification was adversarial: each acceptance command was run first-hand, and the hook fixes were exercised at runtime rather than trusted through the repo's own validator. **26 of 31 are fully solid.** The remainder plus one cross-cutting defect are recorded here; all listed items were **fixed on 2026-07-07** in a follow-up commit (see the checkmarks).

**Cross-cutting blocker**

- ✅ **Fixed — validator not runnable from a clean regenerate.** `generate_targets.py` only `ensure_executable`d `run-hook.sh`; every other hook script was copied mode-preserved as `0644` (git tracks them `100644`; `dist/` is gitignored, so it is always freshly generated). `validate_targets.py.run_hook` execs scripts by path, so `generate_targets.py --all && validate_targets.py` died with `PermissionError` on `protect-files.sh` before asserting anything — meaning *every* "validator asserts X" acceptance was unverifiable on a fresh checkout. Production was unaffected (`run-hook.sh` uses `exec /bin/bash`). Fix: the generator now marks all `hooks/scripts/*.sh` executable.

**Correctness bugs in the shipped hook layer**

- ✅ **Fixed — quoted-space git-flag evasion (makes R-HOOKS-01 fail-open).** The classifier tokenized with `read -ra`, which word-splits ignoring shell quotes, so `git -C "some dir" commit` and `git -c user.name="A B" commit` were **not** detected — the same evasion class R-HOOKS-01 set out to close, and it also defeated the destructive-git guard (`git -C "some dir" reset --hard`). Fix: `_lib-frontmatter.sh` now tokenizes with a quote-aware splitter; a validator case covers the quoted-space form.
- ✅ **Fixed — empty payload polluted `dist/` and produced a spurious `ask` (R-HOOKS-03 robustness).** An empty/whitespace stdin passed `payload_parseable`, reached the Python precision pass, which `sys.exit(3)` → `fail_safe` wrote `hooks-errors.log` under `REPO_ROOT/.claude/session_logs` (= inside `dist/` during validation) and emitted `ask`; the polluted `dist/` then failed the validator's own determinism check. Fix: `protect-files.sh` and `git-protection.sh` now `exit 0` on an empty payload (nothing to inspect); a validator case asserts no pollution.

**Minor / acceptance-vs-reality gaps**

- ✅ **Fixed — R-LIB-01 uv-guard not fully single-homed.** `protect-files.sh` and `enforce-commit-gate.sh` still hand-rolled `command -v uv` despite the `uv_available()` helper; both now call the helper.
- ✅ **Fixed (doc) — R-AGENTS-04 stale count.** The acceptance below reads "agent count 8"; the correct post-implementation count is **6** (R-AGENTS-02 folded away two review-helper agents in addition to designer). The validator checks agent count by *parity* (generated == shared), so the code was always correct — only this document was stale. Corrected in place below.
- ✅ **Fixed (doc) — R-PROMPTS-01 overstated benefit.** The extraction is correct (full duplicated blocks removed, replaced by one-line pointers into a single `agent-reporting.instructions.md`), but the claimed "~25–30% prompt shrink" did not occur (~0%, ≈15 lines) — the repeated blocks were smaller than estimated. No code defect. The recommendation text now states the real goal (one source of truth, not a size reduction) and records the corrected estimate.
- ⚠️ **Noted — R-AGENTS-05 literal grep.** `grep -r "review-profiles" shared/ | grep -v .claude/` is not empty (2 hits in `caveman-compress`), but those are authoring-repo *source-protection* path lists, not routing tables. Single-table intent is met.
- ✅ **Fixed — R-CODEX-01 comment.** The relative-skill-path comment in `generate_targets.py` now cites the enforcing tests (the two `validate_targets.py` assertions that pin the `../.claude/skills/<name>/SKILL.md` form) and the documented Codex relative-path behavior, rather than only explaining why the relative form is used.

**Known residual (out of committed scope):** user-defined git *aliases* (e.g. `git ci` → `commit`) still bypass the classifier; detecting them requires reading git config and was never in R-HOOKS-01's scope.

---

## 1. Executive Summary

**1. The file-layer architecture genuinely works and is worth keeping.** All three runtimes execute the same guardrail scripts through one dispatcher; the generated `dist/` copies were verified drift-free against `shared/`; generation is deterministic; and the validator actually executes hook gates in throwaway git repos rather than merely asserting file shapes. This is a stronger foundation than the upstream project this repo descends from ever built. (§2)

**2. The two load-bearing runtime behaviors cannot execute as designed on at least one target, and are constrained on the others.** The reviewer's dual-pass (`reviewer` → `review-pass-primary` + `review-pass-adversarial`) is a second nesting level: OpenAI Codex documentation confirms the repo's own `max_depth = 1` (`scripts/generate_targets.py:292`) prevents it, and VS Code Copilot subagent nesting is off by default behind an experimental flag. The `agents:` frontmatter the generator emits is documented for VS Code only — not for Copilot CLI or cloud agents. The orchestrator's verify/review/fix/score loop is prompt-described choreography that no target runtime provides as a primitive. (§3.4, §4.1)

**3. The enforcement layer is inverted: strict and brittle on ceremony, permissive on substance.** The commit gate performs ~12 exacting checks (SHA equality, merge-base equality, report-vs-file mtimes, byte-equal frontmatter) — and is skipped entirely by prefixing a commit message with `chore(typo):` (`shared/hooks/scripts/enforce-commit-gate.sh:22`), or silently by writing `git -C . commit` instead of `git commit`. Every hook exits `0`; blocking happens only via stdout JSON; missing `uv` disables the two most safety-critical guards with no signal (`protect-files.sh:12-14`, `git-protection.sh:12-14`). The agent under test authors its own gate inputs: the score JSON, the small-plan `status: complete`, and the `bypass_acknowledged` flag. (§3.4, §4.2)

**4. The quality score does not implement its documented rubric.** `quality-and-testing.instructions.md` describes deductions for missing tests, type hints, docstrings, security issues, and validation gaps. `shared/scripts/quality_score.py:145-174` computes exactly three things: mypy errors −20 (binary), pytest suite failure −15 (binary), ruff violations −1…−5 each. Clean lint plus a green (or skipped: `--skip-tests` sets `tests_passed=True` with no penalty, `quality_score.py:200-201`) suite scores 100 regardless of what the change contains. The git-metadata *binding* of the report is rigorous; the *number* it binds is weak. (§3.4, §4.3)

**5. Semantic single-sourcing fails even where file single-sourcing succeeds.** The review-profile routing table lives in five places with drift; the `commit` skill instructs a workflow (`feature/*` off `main`, self-merge) that the repo's own hooks block; `plan-decomposition` prescribes a two-files-per-phase model the templates and validator don't recognize; the scorer diverges from its rubric; `docs/target-mapping.md` describes an agent renaming the generator doesn't perform. The upstream project solved exactly this class of drift with mechanical parity-check scripts after being burned three times. (§3.4, §4.3)

**6. The sync layer needs configuration and safety work.** The personal bucket `Ghisso/vscode_mounts` is hardcoded in the installer, the sync helper, the devcontainer, and asserted as mandatory by the validator; the author has endorsed moving it to config/env. Independently: every consumer re-mirrors the bootstrap bundle to the bucket with `delete=True` on every session Stop (`shared/devcontainer/hf-ai-sync.py:374`), state pushes never delete (monotonic bucket drift), backups live inside the git-ignored, container-ephemeral `.claude/`, and the CLI fallback passes the token on argv (`hf-ai-sync.py:233`). One newly confirmed platform fact compounds this: Copilot cloud agents load agent files and hooks **only from the default branch**, but the installer gitignores `.github/agents/`, `.github/hooks/`, and instructions in consumer repos (`scripts/install_bootstrap.py:20-32`) — the Copilot cloud surface is silently unconfigured in every consumer. (§3.4, §4.3)

**7. The upstream project this repo forked from has already walked the path this evidence points toward.** `claude-code-my-workflow` (v2.1.0, June 2026, actively maintained) formally retracted its "daemon" orchestrator framing, reframed in-session quality gates as advisory, moved hard enforcement to a single deterministic git pre-commit hook with documented bypasses, replaced its 0–100 score with a severity-count predicate plus a re-verification gate on the judge's own findings, and keeps 18 agents that are all reviewers/verifiers — none writers. Every one of those moves is adoptable here without violating the author's no-fast-paths constraint. (§3.2)

### Verdict tally

| Component class | KEEP | KEEP-FIX | SIMPLIFY | MERGE | REWORK | DELETE |
| --- | --- | --- | --- | --- | --- | --- |
| Agents (9) | 1 | 4 | — | 2 | 2 | — |
| Hook scripts (14) | 4 | 7 | 2 | — | 1 | — |
| Policies (9) | 6 | 3 | — | — | — | — |
| Skills (52) | 47 | 3 | — | 1 | — | 1 |
| Generator / validator / installer+sync | — | 2 | — | — | 1 | — |
| Root files (`download.py`, `upload.py`, `improvement.md`) | — | — | — | — | — | 3 |

---

## 2. What Is Genuinely Good

Credit precedes criticism, and it is specific:

- **Single-sourced guardrail logic.** All three runtimes invoke the *same* scripts under `shared/hooks/scripts/` through `run-hook.sh`; only the config wrappers differ. `diff -rq shared/hooks/scripts dist/multi-agent/.claude/hooks/scripts` is clean; `quality_score.py` and `hooks.json` are byte-identical between source and generated output. There is exactly one implementation of every rule.
- **`run-hook.sh` root resolution** (`shared/hooks/scripts/run-hook.sh`, 41 lines) fixes two *documented real-world* failure modes — empty `$CLAUDE_PROJECT_DIR` producing `/.claude/...` paths, and `git rev-parse` resolving the wrong directory — with a clean fallback chain. Small, correct, load-bearing.
- **Behavioral validation.** `scripts/validate_targets.py` does not just assert file shapes: `validate_lifecycle_hook_guardrails` (`:619-814`) creates a temp git repo, writes synthetic plans and score reports, and *executes* the branch/commit/PR gates against real payloads, asserting deny/ask decisions. Roughly 375 lines of genuine end-to-end tests, plus an installer round-trip and a regeneration determinism check. This is rare in personal tooling and among the most valuable assets in the repo.
- **Score-report metadata binding.** `quality_score.py:55-99` stamps branch, HEAD SHA, merge-base, base ref, phase, target, dirty flag, and changed files into every report, and the commit gate verifies all of them. The *idea* — a quality artifact cryptographically-adjacent-bound to the exact tree state it describes — is right, and ahead of most practice. (The number inside the artifact is the weak part; see §4.3.)
- **Deterministic, dependency-free generation.** `generate_targets.py` is stdlib-only, uses sorted globs throughout, and regenerating produces identical output. No template engine, no supply chain.
- **Review profiles as data.** Nine checklists in `shared/review-profiles/` consumed by one `reviewer` agent is the correct factoring — review criteria are content, not agent identity. The unified-reviewer-plus-profiles design is better than the upstream's 18 hardcoded reviewer agents.
- **The Copilot-native hooks format is correct.** `shared/hooks/hooks.json` uses the documented flat-handler schema (`"version": 1`, per-entry `bash`/`linux`/`osx`/`cwd`/`timeoutSec`) — verified against the July-2026 GitHub reference. The generator's Codex output likewise matches Codex's documented nested-group format. Someone did the homework per-runtime.
- **Runtime-honest touches exist.** The orchestrator prompt explicitly accommodates targets lacking TodoWrite (`shared/agents/orchestrator/prompt.md:15`); protect-files deliberately downgrades deny→ask on runtimes that can prompt and deny on Codex which cannot (`protect-files.sh:235`) — a distinction the official Codex docs (no `ask` decision documented) validate.

---

## 3. Strategic Assessment

### 3.1 The core bet

The design bets that **consistency beats improvisation**: a mandatory pipeline (PRE-FLIGHT → BRANCH → PLAN → IMPLEMENT → VERIFY → REVIEW → SCORE → DOCUMENT → LEARN → SESSION LOG → COMMIT) enforced by hooks, executed by specialised agents, producing durable artifacts (plans, score reports, session logs, memory) that survive across sessions and machines via HF sync.

What the bet buys:

- **Auditability.** Every commit is traceable to a plan phase, a score report, a closeout log, and a learning entry.
- **Forced decomposition.** Big-plan → small-plan tiering makes commit-sized units of work a structural requirement, not a discipline.
- **Cross-session/cross-machine continuity** that no native feature fully provides across three different AI tools.
- **Transferable lessons.** Skills and memory capture library-specific fixes once and ship them to every project.

What the bet costs:

- **~5–6 bookkeeping artifacts per commit** beyond the code: big-plan cursor update, small-plan completion, score JSON, closeout log containing the literal `**Status:** COMPLETED`, LEARN evidence (MEMORY.md mtime or literal marker), optional docs/review artifacts (`enforce-commit-gate.sh:34-156`).
- **Latency and token cost** of a six-agent relay for work a single context could hold.
- **A gaming incentive**: when a brittle ceremony check false-positives (see §4.2 on SHA/mtime correlation), the documented escape is a bypass prefix — i.e. the system's own answer to friction is the hole in its fence.

This ledger is not an argument against the bet. It is the price list, and the author should re-confirm the prices consciously — especially given what the two benchmarks below show.

### 3.2 Benchmark 1: what the upstream learned after this repo forked

`pedrohcgs/claude-code-my-workflow` (the acknowledged starting point, README:9) is now v2.1.0 (June 2026), ~1.3k stars, actively maintained — and pivoted to an academic content pipeline, so its agent roster is no longer comparable. Its *process history*, however, is a controlled experiment on this repo's exact design ideas, run by its original author for eighteen months. Four results transfer directly [external; sourced from its changelog and rules files, accessed 2026-07-03]:

1. **The enforcement-honesty retreat (v1.6.1, April 2026).** The project formally removed its "daemon" orchestrator framing — admitting the orchestrator was "a pattern-in-skills, not a repo-wide daemon" — and reframed all in-session quality gates as advisory except the one at `/commit`. This repo's orchestrator prompt makes the same over-claim today (§4.1): it narrates a loop it has neither the tools nor the runtime support to run.
2. **Blocking in-session hooks did not survive contact.** Compaction-blocking was made default-on and reverted in the same release cycle; a blocking log-reminder became stderr-only because it broke looped execution. The only hard gate that survived is a **real git pre-commit hook**: deterministic, outside the model loop, with explicit auditable bypasses. This repo's equivalent enforcement lives inside PreToolUse hooks whose blocking depends on runtime stdout conventions and which fail open on timeout, missing `uv`, or unmatched tool names (§4.2).
3. **The judge got a judge.** The 0–100 score was replaced by a severity-count predicate (`CRITICAL>0 → BLOCK, MAJOR>0 → REVISE, else PASS`) plus a hallucination gate: new CRITICAL findings must survive re-verification in a fresh fork. Convergence is bounded (two consecutive dry rounds, five-round cap). This repo's dual-pass review has no convergence rule and its "adversarial" pass never sees what it is nominally challenging (§4.1).
4. **Drift got mechanical policing.** After README/inventory counts drifted from disk three separate times, they added `check-surface-sync.py` and `check-skill-integrity.py`. This repo has the same disease (five routing tables, rubric≠scorer, doc≠generator — §3.4) and already owns the right medicine: `validate_targets.py` is the natural home for parity assertions.

### 3.3 Benchmark 2: what the platforms now provide natively

Verified against official documentation, July 2026:

- **Claude Code** now ships native plan mode with persistent plan files, built-in Plan/Explore agents, `/goal` end-state verification, checkpointing/rewind across sessions, auto-memory, and plugins/marketplaces as the sanctioned cross-repo packaging. Generic planner/verifier/reviewer *prompt bodies* are increasingly redundant there; domain-specific review criteria, read-only research agents, and deterministic guardrail hooks remain clearly valuable.
- **Copilot** (docs.github.com + VS Code, both updated 2026-07-01): custom agents at `.github/agents/*.agent.md` are current; `user-invocable`/`disable-model-invocation` are the current visibility fields (the repo already uses the current form); **`agents:` delegation lists are documented for VS Code only**; subagent nesting is off by default (experimental flag, max depth 5); VS Code currently **ignores hook matchers** (all hooks fire on every tool); `preToolUse` honors stdout `permissionDecision` (top-level key; the Claude-style `hookSpecificOutput` wrapper is also accepted in VS Code); **non-zero exit on preToolUse fails closed**; timeout fails open; default `timeoutSec` is 30 (the repo pins 10 — `hooks.json:11`); cloud agents read agent files and hooks **only from the default branch** and treat `ask` as `deny`. Notably, VS Code also reads `.claude/agents/` and `.claude/settings.json` natively, making the thin `.github` adapters partially redundant on that surface (still required for CLI/cloud/JetBrains).
- **Codex** (developers.openai.com): `[features] hooks = true` is now redundant (on by default); `[agents] max_depth = 1` — the repo's own setting — explicitly "allows a direct child agent to spawn but prevents deeper nesting", which forbids `reviewer` → `review-pass-*`; hooks use the Claude-style nested schema the generator emits (correct), deny via `hookSpecificOutput.permissionDecision` **or exit 2** (no `ask` documented); `PreCompact` and `PostCompact` both exist (the generator emits no Codex PreCompact — an available event unused); skill registration documents **absolute paths to a `SKILL.md` file**, while the generator emits relative directory paths (`path = "../.claude/skills/<name>"`, `dist/multi-agent/.codex/config.toml:20`) — undocumented territory that may silently no-op; project docs are capped at 32 KiB (generated `AGENTS.md` is ~18.9 KB — fine, but four copies of the same pipeline prose spend that headroom).
- **Multi-agent consensus** (Anthropic context-engineering guidance, Sept 2025; Cognition, June 2025): parallel *reading* agents are the win (context isolation, summaries back); parallel or delegated *writing* agents are the risk (implicit-decision divergence between the planner's context and the writer's context). This repo's `coder` and `designer` are writer subagents; its `verifier` and review agents are exactly the read-only pattern the consensus endorses.

One deliberate consequence of the multi-target design deserves explicit acknowledgment rather than drift: supporting Copilot + Claude + Codex forces lowest-common-denominator design and forgoes native packaging (plugins) on the Claude side. That trade may well be correct — Copilot and Codex have no plugin equivalent — but it should be a recorded decision, revisited annually, not an inheritance.

### 3.4 Four structural fault lines

**Fault line 1 — Enforcement inversion.** The gates check what is easy to check exactly, and cannot check what matters. Strict: HEAD SHA, merge-base SHA, report mtime vs every changed file's mtime, byte-equal commit subject, literal `**Status:** COMPLETED`. Unenforceable and unverified: whether tests exercise the change (`--skip-tests` scores 100), whether the review happened meaningfully (agent writes its own inputs), whether the commit even went through the gate (`chore(typo):` prefix or `git -C .` shape skips it; `_lib-frontmatter.sh:276-281` plus subcommand-position-only classifiers at `:247-257` — the `git -C` evasion was verified by execution during this review). Meanwhile every failure mode of the hooks themselves — missing `uv`, awk mis-parse, 10-second timeout, unrecognized tool name, macOS `stat -c` (`enforce-commit-gate.sh:131-149`) — resolves to *allow, silently*. Two design changes would rotate this: (a) exploit the fail-closed semantics the platforms already give (Copilot non-zero-exit deny; Codex exit-2 deny) instead of universal `exit 0`; (b) move what must never be bypassed into a git `pre-commit`/`pre-push` hook, where no tool-payload parsing exists to evade — the upstream's surviving pattern.

**Fault line 2 — Designed-but-unexecutable behaviors.** The orchestrator owns branch creation, commits, PR creation, memory writes, and session logs (`orchestrator/prompt.md:23-34,77-83`) with a toolset of `Task, Read, Grep, Glob, TodoWrite` (`orchestrator/agent.yaml:6-11`) — no Bash, no Write. The planner's full-plan mode mandates a user interview, "minimum 2 rounds" (`planner/prompt.md:45-49`), which a delegated subagent on any of the three runtimes cannot conduct. The reviewer's dual-pass needs nesting depth the Codex config forbids and VS Code disables by default. On Codex, the reviewer therefore always lands in Degraded Mode, whose own rules say "Do not mark a PR gate as passed" (`reviewer/prompt.md:48`) — the PR gate cannot legitimately pass through the orchestrated path on that runtime, and nothing reconciles this. These are not prompt-polish issues; they are contract mismatches between what the YAML grants, what the prompt commands, and what the runtimes execute.

**Fault line 3 — Semantic drift across copies.** Verified instances: profile-routing guidance in five locations (orchestrator prompt `:40-50`, reviewer prompt `:20-28`, planner prompt `:71`, `workspace.instructions.md:80-93`, README) with the orchestrator and reviewer tables already unequal; planner and README pointing at `shared/review-profiles/` — a directory that does not exist in consumer repos (`dist/multi-agent/.claude/agents/planner.md:77` ships the bad path); the `commit` skill contradicting the enforced branch model (§4.3); `plan-decomposition` prescribing a plan-file shape the templates don't define; rubric≠scorer; `docs/target-mapping.md:47-51` describing a `review-pass-claude-*` renaming that `generate_targets.py` does not perform. Each copy was presumably correct when written. The cure is the upstream's: parity checks in `validate_targets.py`, and one authoritative home per fact with references elsewhere.

**Fault line 4 — Sync configuration and state safety.** Per the author's direction, stack-specificity is out of scope; what remains is real: the bucket name hardcoded in four places including as a *validator requirement* (`validate_targets.py:1117,1150,1193`); `upload-bootstrap` mirroring with `delete=True` from every consumer on every Stop (`hf-ai-sync.py:374`, wired in `dist/multi-agent/.claude/settings.json:122`) so any consumer's stale copy can clobber the canonical bundle [inferred: mechanism verified, incident not observed]; `push-state` never deleting, so the bucket accumulates forever; recovery backups stored inside the git-ignored `.claude/.state_backups/` that a container rebuild erases; `MEMORY.md` dual-homed between bootstrap and state prefixes with order-dependent restoration (`hf-ai-sync.py:21-53,489-491`); the token on argv in the CLI fallback (`:233`). Add the newly confirmed Copilot fact — cloud agents only read `.github/agents//hooks/` from the default branch, which consumers gitignore (`install_bootstrap.py:20-32`) — and the cross-surface story needs one deliberate decision: which surfaces are actually supported in consumers, enforced by the installer, documented in the README.

### 3.5 Proportionality, within the author's constraint

The evidence that uniform heavyweight process carries real cost is consistent across sources: the platform vendor's own guidance ("if you could describe the diff in one sentence, skip the plan" [external]), the upstream's trivial-task exemption, and this repo's own bypass-prefix design — which exists precisely because some commits do not merit the full ceremony, and which is currently the *least* controlled path through the system.

The author's standing decision is that the orchestrator serves non-trivial work only, with no fast paths or escape hatches — this review honors that and proposes none. The cost accounting above instead points at two compliant pressure valves that are already part of the design's own vocabulary:

1. **Tier the closeout artifacts, not the workflow.** The big-plan/micro-plan distinction already exists in the planner (`planner/prompt.md` micro-plan mode: load skills → draft → done). The commit gate, however, demands the identical artifact set for every phase regardless of tier. Letting the *small-plan tier itself* declare a reduced closeout contract (e.g. score + closeout log, with LEARN and docs required only where the plan frontmatter says so) keeps every commit gated through the same hooks — no bypasses — while pricing ceremony proportionally to the plan tier that the planner (not the moment's convenience) assigned.
2. **Make the sanctioned bypass narrower than the gate, not wider.** Today the bypass prefixes skip *everything* including secret-file protection ordering and score presence. A bypass commit could still be required to pass a minimal deterministic subset (branch shape, protected files) while skipping only the plan-completion ceremony. That preserves the recovery use-case the prefixes exist for, and removes the perverse fact that the system's weakest path is also its documented escape.

---

## 4. Systematic Component Verdicts

Verdict vocabulary — exactly one per component:

| Verdict | Meaning |
| --- | --- |
| **KEEP** | Sound as designed and implemented; optional nits only. |
| **KEEP-FIX** | Right component, right role; enumerated defects fixable in place. |
| **SIMPLIFY** | Function needed; implementation mass is not. |
| **MERGE** | Fold into a named sibling; the distinction costs more than it earns. |
| **REWORK** | Right problem, wrong mechanism; needs redesign, not patches. |
| **DELETE** | Remove; function unnecessary or served elsewhere. |

Priorities attach to findings: **P0** = a guarantee the author believes holds, silently doesn't. **P1** = mechanism runs but produces weak signal or gaming-inducing friction. **P2** = hygiene.

### 4.1 Agents (9)

| Agent | Verdict | Worst finding |
| --- | --- | --- |
| orchestrator | REWORK | P0 — cannot execute its own mandate |
| planner | KEEP-FIX | P1 — unexecutable interview; dead grant; bad path |
| coder | KEEP-FIX | P1 — control-plane guard never fires in consumers |
| designer | MERGE → coder | P1 — weaker-discipline duplicate |
| reviewer | KEEP-FIX | P1 — depends on impossible nesting; see orchestrator |
| review-pass-primary | MERGE → reviewer | P2 — scaffold duplicate |
| review-pass-adversarial | REWORK | P1 — cannot do what its name claims |
| verifier | KEEP | — |
| documenter | KEEP-FIX | P1 — diffs against the wrong base |

**orchestrator — REWORK.** *Intent (steelman):* one accountable coordinator that owns the lifecycle end-to-end and never touches code itself — least-privilege by design. *What it gets right:* the routing table concept, the complexity gate, explicit TodoWrite fallbacks for runtimes without it (`prompt.md:15`). *Findings:* (P0, verified) capabilities `delegate, read, search, todo` (`agent.yaml:6-11`) cannot perform PRE-FLIGHT branch checks, BRANCH creation, COMMIT, PR (`prompt.md:23-34`), or the Completion Protocol's MEMORY.md/session-log writes (`prompt.md:77-83`); the Codex adapter is additionally sandboxed read-only. (P0, doc-verified) The loop it narrates — delegate, await, re-delegate until score ≥ 90 — is not a primitive any of the three runtimes provides to a *custom agent*; it works only when the orchestrator is the main interactive thread, which the design does not state. (P1) The 91-line prompt restates the pipeline that also lives in `workflow.instructions.md`, `CLAUDE.md`, and README. *Rework direction:* pick one honest identity. Either (a) the orchestrator is the **main-thread persona** — grant `execute`+`edit`, state that it is not itself delegatable, and let it truly own branch/commit/log duties; or (b) it is a **coordinator pattern documented in instructions**, and the lifecycle mechanics belong to the main session guided by hooks. What it must not remain is a subagent commanded to do things its toolset forbids. (Its non-trivial-only scope is a settled design decision and stays.)

**planner — KEEP-FIX.** *Steelman:* planning quality is the highest-leverage step; an interview-driven full-plan mode is the right instinct. *Gets right:* micro/full mode split; per-step Required Skills and Review Profiles; devil's-advocate option. *Findings:* (P1, verified) full-plan mode mandates a user interview "minimum 2 rounds" (`prompt.md:45-49`) that a delegated subagent has no channel to conduct — when reached via the orchestrator, the instruction is dead on all three runtimes; the mode should either be marked main-thread-only or restructured to emit *questions as output* for the orchestrator/user to relay. (P2, verified) `delegates: []` yet the `delegate` capability grants a `Task` tool with nobody to call (`agent.yaml`, rendered `dist/.../planner.md:4`). (P1, verified) Points writers at `shared/review-profiles/` (`prompt.md:71`), a path that exists only in this authoring repo; consumers need `.claude/review-profiles/` (`dist/.../planner.md:77` ships the wrong path today).

**coder — KEEP-FIX.** *Steelman:* a disciplined implementer with tiered skill loading and a mandatory simplification pass is a genuinely good pattern. *Gets right:* two-tier skills; verification commands inline; simplification pass; control-plane pause-and-ask. *Findings:* (P1, verified) the control-plane guard enumerates `shared/`, `dist/` (`prompt.md:21`) — paths that don't exist in consumer repos, so the guard silently never matches where it matters most; it should express control-plane in consumer terms (`.claude/`, hook configs, native adapter files). (P2) ~30% of the prompt is the Retrieval/caveman boilerplate repeated across all nine agents (all nine reference `tool-routing.instructions` — verified count); extract to one shared instruction. (P2) It re-runs `quality_score.py` that verifier and the SCORE step also run — three invocations writing timestamped reports, with the commit gate selecting by *lexical filename order* (`enforce-commit-gate.sh:72-80`), making report selection ambiguous. One owner (verifier) should produce the canonical report.

**designer — MERGE → coder.** *Steelman:* UI work benefits from a distinct aesthetic sensibility and a preloaded `gradio-streamlit` skill. *Findings:* (verified capability diff) designer = coder minus `todo`, minus `web` (`designer/agent.yaml` vs `coder/agent.yaml`); its 36-line prompt carries no verification-command suite, no simplification pass, and no control-plane guard — the same class of work with strictly weaker discipline. The differentiation that matters (the skill, the design vocabulary) fits in coder's existing Tier-2 skill loading (`gradio-streamlit` loads for UI tasks). Merging removes a weaker-gated write path; nothing of value is lost that a conditional skill load doesn't preserve.

**reviewer — KEEP-FIX.** *Steelman:* one reviewer consuming profile checklists as data is the right architecture (better than upstream's 18 bespoke reviewers). *Gets right:* profile merging, severity reconciliation rules, an explicit Degraded Mode. *Findings:* (P0, resolved with orchestrator/delegation decision) its two-helper fan-out is the second nesting level that Codex config forbids and VS Code gates behind an experimental flag; on Codex it permanently degrades, and Degraded Mode's "do not mark a PR gate as passed" (`prompt.md:48`) means the orchestrated PR path cannot succeed there — either raise `max_depth` to 2 for Codex and enable/verify VS Code nesting, or fold the two passes into sequential work the reviewer itself performs (see next two verdicts, which recommend the fold). (P1) Its input contract says the caller provides severity definitions, but its own flow forwards only the "merged profile checklist" (`prompt.md:31-34`) — forward the profiles' `## Severity` sections explicitly. (P2) Its file-type→profile inference table duplicates the orchestrator's routing table, un-identically; keep exactly one (§4.3, R-AGENTS-05).

**review-pass-primary — MERGE → reviewer.** Same capabilities, same scaffold, same output contract as its adversarial twin, differing in a header string. As a separate *agent* it exists only to give the dual-pass two spawnable bodies — the thing the runtimes resist. As a *sequential first pass run by the reviewer itself* (or a forked-context skill on runtimes that support it), nothing is lost.

**review-pass-adversarial — REWORK.** *Steelman:* adversarial review is officially good practice, and using a different model for it (GPT vs Claude, per Copilot model intents) is a legitimate de-correlation trick. *Finding:* (P1, verified) it is instructed to "Challenge assumptions made by the primary pass" (`prompt.md:32`) but the reviewer runs both passes independently on the same scope (`reviewer/prompt.md:31-34`) — it never receives the primary's findings, so the instruction is unsatisfiable; what actually runs is a two-model ensemble mislabeled as adversarial. *Rework direction (upstream-tested):* make the second pass a **verification pass that receives the first pass's findings** and attempts to refute each (the hallucination-gate pattern: findings that don't survive re-verification are dropped, not merged as "disputed"). That is both honest to the name and directly targets the documented failure mode of LLM reviewers — confidently fabricated findings [external: reviewer-bias literature; see Appendix B].

**verifier — KEEP.** Mechanical, read-plus-execute, literal commands, table output — exactly the shape that both the 2026 consensus and this review endorse. Its one wrinkle is shared, not its own: it is one of three producers of score reports (fix via R-AGENTS-08 single-owner rule). Nit (P2): its deprecation-grep and import-loop checks silently assume `src/` layout; fine for the author's stack, worth a one-line note in the prompt.

**documenter — KEEP-FIX.** *Gets right:* diff-driven scope table, explicit writing rules, the only agent sensibly exempted from caveman output (`prompt.md:21`). *Findings:* (P1, verified) diffs `main...HEAD` (`prompt.md:28-29`) while the entire lifecycle bases on `dev` — in consumer repos with long-lived `dev`, the scan range is wrong; parameterize to the plan's `originating_branch`. (P2, verified) References `.claude/skills/api-service-standards/SKILL.md` (`prompt.md:11`), which does not exist (0 matches in `shared/skills/`) — the guard "if present" makes it a silent no-op; point at the real `review-api` skill or the `api-service-standards` *instructions*. (P2) 28 of its 129 lines are Mermaid authoring rules — more than the entire designer prompt; move to a `documentation` skill it already loads.

### 4.2 Hook scripts (14)

Layer totals (verified): 1,334 lines of scripts + 168 lines `hooks.json` = 1,502.

| Script | Lines | Verdict | Worst finding |
| --- | --- | --- | --- |
| run-hook.sh | 41 | KEEP | fail-open on missing arg (P2) |
| _lib-frontmatter.sh | 287 | SIMPLIFY | P0 — classifier gaps; parser fragility |
| protect-files.sh | 266 | SIMPLIFY | P0 — no-ops without `uv` |
| git-protection.sh | 66 | KEEP-FIX | P0 — no-ops without `uv` |
| enforce-branch-state.sh | 67 | KEEP-FIX | P2 |
| enforce-commit-gate.sh | 163 | REWORK | P0 — bypassable + brittle |
| enforce-pr-gate.sh | 78 | KEEP-FIX | P1 — self-served acknowledgment |
| record-branch-state.sh | 48 | KEEP-FIX | P2 |
| record-commit-closeout.sh | 77 | KEEP-FIX | P1 — silent state stall |
| session-start-state.sh | 52 | KEEP | P2 — second bespoke JSON parser |
| stop-session-log-check.sh | 25 | KEEP-FIX | P1 — GNU-only `find -newermt` |
| session-log.sh | 65 | KEEP | — |
| hf-ai-sync.sh | 46 | KEEP-FIX | (issues live in `hf-ai-sync.py`, §4.3) |
| context-mode-dispatch.sh | 53 | KEEP | — |

**run-hook.sh — KEEP.** The dispatcher earns its place (§2). One P2: a missing script name/target exits 0; exiting non-zero would fail closed on Copilot preToolUse for free.

**_lib-frontmatter.sh — SIMPLIFY.** 287 lines (19% of the layer) of hand-rolled awk JSON scanning and YAML frontmatter parsing. Findings: (P0, verified by execution) the git classifiers require the subcommand immediately after `git` (`:247-257`), so `git -C . commit`, `git -c key=val commit`, and aliases skip the commit/PR gates *silently* — a stronger bypass than the sanctioned prefixes, with no log entry; (P1) `json_string_value` (`:25-63`) is a flat regex scan that takes the first `"command"` match at any nesting depth — mis-parse resolves to fail-open; (P1) `fm_read` handles only plain `key: value` — a plan written `phases: [a, b]` silently yields an empty phase list; (P2, verified) `fm_has` (`:176`) and `hook_tool_name` (`:66`) have zero callers; (P2) the `*_implementation` branch regex is duplicated in five scripts despite this library existing. Simplification direction: classifiers tokenize past global git flags; unknown tool names → `ask` (or deny on Codex) instead of skip; delete dead functions; single home for the branch regex. The parser need not be rewritten in Python (the bash gates' independence from `uv` is a strength — see next entry) but it must be honest about its subset and fail toward `ask`.

**protect-files.sh — SIMPLIFY.** 266 lines, ~180 of them embedded Python (shlex tokenization, redirection regexes, patch-prefix scanning) to answer "does this touch `.env`/keys/lockfiles/hook configs" — and the entire script `exit 0`s if `uv` is absent (`:12-14`, verified). The two most safety-critical guards in the repo are the only ones with a hard dependency the guarded environments may lack, while the ceremony gates run on pure awk anywhere. Invert: a pure-bash pattern check covers ≥90% of the real risk (path substring/glob match on the extracted candidate paths); keep the Python precision pass as an *enhancement* when `uv` exists; when neither works, emit `ask`, never silent allow. Also (P1): under Claude's generated matcher `Edit|MultiEdit|Write|Bash` (`dist/.../settings.json:34`), the script's `apply_patch` handling is dead code and `NotebookEdit` is ungated — align matchers with the tools each runtime actually exposes.

**git-protection.sh — KEEP-FIX.** The denylist (force-push, `reset --hard`, `clean -fd`, branch-delete-main) is sound. Same P0 as above: `uv` absent → silent allow (`:12-14`); this one is ~15 lines of bash regex away from having no dependency at all. Fix there rather than in Python.

**enforce-branch-state.sh — KEEP-FIX.** Solid coverage of `checkout -b/-B`, `switch -c/-C/--create` forms. Inherits the classifier-position gap (fix in `_lib`). P2: duplicated branch regex.

**enforce-commit-gate.sh — REWORK.** The most complex gate (163 lines, ~12 checks) and the least effective per line. Verified findings: (P0) `is_bypass_subject` short-circuits *before any check* (`:22`) — `chore(typo): x` skips score, closeout, LEARN, everything; (P0) inherits the `git -C` classifier gap — the strictest gate in the repo is opt-in; (P1) report selection is first-match in reverse-lexical filename order for the branch+phase (`:72-80`) — not newest by `generated_at`, not best score — so a stale matching report shadows a fresh one; (P1) exact `head_sha`/`merge_base` equality plus report-mtime ≥ every-changed-file-mtime (`:131-137`) means any amend, rebase, stash cycle, or editor touch produces an opaque block whose documented way out is… the bypass prefix; (P1, verified `osx` keys in `hooks.json`) on macOS, GNU `stat -c` fails and both the freshness and LEARN checks silently pass (`:131-149`); (P1) ~6 git calls + `find` + N×`stat` under the self-imposed 10s `timeoutSec` (`hooks.json:11`), where Copilot timeout = fail-open. Rework direction: (a) narrow the bypass to skip only plan-ceremony checks, never branch-shape or protected-file logic (§3.5); (b) select reports by `generated_at`, newest matching; (c) tolerance on mtime (or content-hash the changed files into the report and compare hashes, which the score script could stamp cheaply); (d) portable mtime probe; (e) exit non-zero on *internal error* so Copilot fails closed instead of open. And the strategic option that obsoletes half of this: mirror the must-never-skip subset into a plain git `pre-commit` hook the installer writes, where there is no payload to mis-parse and no prefix to game.

**enforce-pr-gate.sh — KEEP-FIX.** Reasonable size and checks (base `dev`, all phases complete, ≥1 commit per phase). (P1) The bypass-acknowledgment it enforces reads `bypass_acknowledged` from the big plan — which the agent writes; pair it with the bypass *ledger* (`hooks-bypass.log`) count so acknowledgment at least has to name the count it acknowledges. Inherits classifier gaps for `git push`/`gh pr create` shapes.

**record-branch-state.sh — KEEP-FIX / record-commit-closeout.sh — KEEP-FIX.** The write side of the state machine, correctly separated from validation. (P1, record-commit-closeout) phase advance requires the parsed `-m` subject to byte-equal `git log -1 --format=%s` (`:28-32`); shell-expanded or multi-line messages miss, the phase silently fails to advance, and the *next* commit blocks on a phase the author believes is done — with recovery only via hand-editing frontmatter. Loosen to prefix/normalized match and emit an explicit `additional_context` warning when correlation fails, plus a documented recovery command.

**session-start-state.sh — KEEP.** Useful reminders, correct read-only posture. P2: parses score JSON with a third inline awk variant (`:37`) — use the `_lib` helper.

**stop-session-log-check.sh — KEEP-FIX.** Right idea, warn-only is correct. (P1) `find -newermt` is GNU-only — on macOS the check errors into silence; use a portable `-mtime`-based approximation or a `python3` one-liner (python3 without `uv` is a fair dependency for a warn-only path).

**session-log.sh — KEEP.** Handles snake/camelCase payloads, synthesizes timestamps bash-side because Claude payloads carry none — correct cross-runtime engineering.

**hf-ai-sync.sh — KEEP-FIX.** The 2-second stdin drain (`:31`) solving the never-closing-stdin hang is documented and correct. The substantive issues (what it *triggers*) are in `hf-ai-sync.py` — see §4.3. One P1 here: it is the only Stop-path script writing to `hooks-errors.log`; the enforce-* gates should adopt the same error-trail habit.

**context-mode-dispatch.sh — KEEP.** Graceful degradation (context-mode → npx → warn), `exec` semantics, exits successfully when absent — the right shape for an optional dependency. (P2, generator-side) Codex gets no PreCompact wiring even though Codex documents the event — one loop entry in `generate_targets.py:383-439` away.

**Cross-runtime divergence table (verified against generated configs):**

| Concern | Copilot (`.github/hooks/hooks.json`) | Claude (`.claude/settings.json`) | Codex (`.codex/hooks.json`) |
| --- | --- | --- | --- |
| PreToolUse matcher | none in file; VS Code ignores matchers anyway → all hooks on all tools | `Edit\|MultiEdit\|Write\|Bash` → `NotebookEdit` etc. ungated; `apply_patch` branch dead | `*` |
| PreCompact | yes | yes | **missing** (event exists in Codex) |
| Blocking channel | stdout `permissionDecision`; non-zero exit = deny; timeout = allow | stdout `hookSpecificOutput` | stdout `hookSpecificOutput` or exit 2; no `ask` |
| Timeout | 10s pinned (default 30) | runtime default | 10s pinned (default 600) |
| Hook-file edit decision | ask | ask | deny (correct — no `ask` exists) |

### 4.3 Group verdicts

**Policies (9 files, 953 lines) — KEEP ×6, KEEP-FIX ×3 (workspace, quality-and-testing, code-standards).** The stack-specific content (config-first-design/Hydra 141 lines, api-service-standards/BentoML 92, deployment/BentoML 67, and the framework list in workspace) **stays by design** — it is the author's standard stack, and encoding it is the point of a personal bootstrap. Fixes: (P1) `quality-and-testing.instructions.md:49-94` documents a scoring rubric the scorer does not implement — rewrite the rubric to describe the real arithmetic (and its planned evolution), because a false spec is worse than a modest one; (P2, verified) `workspace.instructions.md:128` ships the unfilled `**Project:** [TODO: project name and one-liner description]` to every consumer — have `install_bootstrap.py` substitute the target repo name at install time; (P2, verified against this repo's own scripts) `code-standards.instructions.md:42` bans `from __future__ import annotations` absolutely while every script in `scripts/` uses it — scope the ban to its actual rationale (Hydra-managed modules); (P2) `tool-routing.instructions.md` is good and should become the *only* home of retrieval guidance (see skills).

**Skills (52: 36 public / 16 background) — KEEP the fleet, with targeted actions.** The ~12 library-specific micro-skills (pyvis-xss, pandas-nan-bool-coercion, networkx-igraph-graphml-interop, haystack-*, docling-haystack, ollama-chat-generator, extraction-metadata-sourcing, rag-auditor, text-to-sql-safety, csv-driven-integration-tests, graph-schema-compat-migration) **stay by the author's decision** — same libraries recur across his projects, and shipping the lessons everywhere is the bootstrap's job. Actions elsewhere:

- **DELETE `iterative-plan-review`** — its own body says "This workflow is now part of `plan-decomposition`; keep this skill as a background trigger for older prompts" (`SKILL.md:12`, verified). The "older prompts" it serves are all generated by this repo and can be regenerated without the reference.
- **MERGE `retrieval-routing`** into `tool-routing.instructions.md` — near-verbatim duplicate of the policy.
- **KEEP-FIX `commit`** (P1, verified): Phases 2–6 instruct `git checkout -b feature/description` off `main`, `gh pr merge --merge`, `git checkout main` — every step of which `enforce-branch-state.sh`/`enforce-commit-gate.sh`/`enforce-pr-gate.sh` blocks (`*_implementation` off `dev`, PR to `dev`, human merge). A public skill that walks the agent into its own hooks' deny messages. Rewrite around the enforced lifecycle. Same staleness in `templates/quality-report.md:16` (`**Branch:** feature/...`).
- **KEEP-FIX `plan-decomposition`** (P1): prescribes two files per phase (overview + detail) while `plan-small.md` and `validate_plan_frontmatter.py` define one — align to the single-file model.
- **Policy-duplicating skills** (`code-style`, `hydra-config`, `bentoml-service`, `deploy-service`, `testing-patterns`, `run-tests`): keep the *skills* as the actionable playbooks, and slim the corresponding policy sections to principles + a pointer, so each fact has one home. No deletions required.
- (P2) The profile-routing table appears a third time in `code-review/SKILL.md:14-25` — replace with a reference to the single authoritative table (R-AGENTS-05).

**Templates & schemas — KEEP.** Consistent with hooks' parsing expectations, except the `feature/` remnant above.

**Generator (`scripts/generate_targets.py`, 711 lines) — KEEP-FIX.** Deterministic, stdlib-only, single-file: right size for the job. Fixes, all P2 and verified: the `transform_agent_text` model-name replacement branches (`:201-212`) never fire (those strings exist only in `agent.yaml` `model_intent`, consumed directly at `:565`); `mapped_agent_name` (`:193`) is an identity function feeding a doc claim (`docs/target-mapping.md:47-51`) that isn't true; multi-target conditionals survive from the pre-fusion era while `TARGETS = ("multi-agent",)` (`:15`); `load_json_yaml` (`:59-60`) parses only JSON, making `manifest.yaml`/`servers.yaml` misleadingly named — rename to `.json` or parse real YAML; the `vscode` capability maps to a Copilot tool but silently vanishes for Claude/Codex (`:20-38`) — drop it or document it as Copilot-only. One newly doc-sourced item (P1): emit Codex `[[skills.config]]` paths in the documented form (absolute path to `SKILL.md`) or verify the relative-directory form actually registers — today it is undocumented territory (`dist/.../config.toml:20`); also stop emitting the now-redundant `[features] hooks = true` and add the missing Codex PreCompact group.

**Validator (`scripts/validate_targets.py`, 1,238 lines) — KEEP-FIX.** The behavioral tests are the crown jewels; keep every one. Fixes: (P1) dozens of exact-literal prose assertions (e.g. `:929` requiring a specific English sentence in generated text) make every wording change a two-file edit — assert structure (frontmatter fields, file presence, executable bits, hook decisions) rather than sentences where possible; (P1, author-endorsed direction) `Ghisso/vscode_mounts` is asserted as *required* (`:1117,1150,1193`) — validate "a bucket is configured", not which one; (P2) `COPILOT_MODEL_PINS` is a hand-maintained allow-list — the pinned names are *currently valid* July-2026 Copilot picker names (verified against the official supported-models reference; an earlier draft of this review wrongly called them speculative), but the list will rot silently; add a comment dating the last check against the reference; (P2) determinism check uses shallow `filecmp` — pass `shallow=False`.

**Installer + HF sync (`install_bootstrap.py` 220, `update_consumers.py` 125, `hf-ai-sync.py` 504) — REWORK.** The gitignore-AI-content-and-restore-from-bucket design is coherent and the docstrings honestly document their own fragilities (e.g. `update_consumers.py:10-16`). The rework items, most author-endorsed or platform-forced:

- (P0, author-endorsed) Bucket name → configuration: one source (env var `HF_AI_SYNC_BUCKET` / `.devcontainer` config already half-exists as the resolution chain in `hf-ai-sync.py`) with the *default* removed from installer (`install_bootstrap.py:49`), Dockerfile-adjacent config, and validator. No personal namespace baked into code.
- (P0, doc-verified) Decide the Copilot cloud story: cloud agents read `.github/agents//hooks/` only from the default branch, which `IGNORE_PATTERNS` (`install_bootstrap.py:20-32`) gitignores in consumers. Either offer an installer mode that commits the Copilot surface, or document that consumers get local-IDE Copilot only. Today the surface silently half-exists.
- (P1) `upload-bootstrap` on every Stop with `delete=True` (`hf-ai-sync.py:374`; wired at `dist/.../settings.json:122`) lets any consumer mirror its possibly-stale copy over the canonical bundle [inferred risk — mechanism verified]. Make bootstrap upload an explicit installer/updater action; consumers push *state* only.
- (P1) `push-state` never deletes (`:385-421`) → the bucket accumulates deleted plans/logs forever; add a `--prune` path or periodic reconciliation.
- (P1) `MEMORY.md` dual-homed in `BOOTSTRAP_PATHS` and `STATE_INCLUDES` (`:21-53`) with order-dependent restore (`:489-491`) — remove it from the bootstrap bundle (template lives in `dist/`, content lives in state) so no ordering can clobber memory.
- (P2) `.state_backups/` recovery lives inside the ephemeral, git-ignored `.claude/` — fine as a convenience, but say so in the docs; the durable copy is the bucket.
- (P2) CLI fallback passes `--token` on argv (`:233`) — visible in process listings; prefer env inheritance.

**Root files — DELETE ×3.** (Verified) `download.py`/`upload.py` implement the pre-migration `.github`-as-source sync against a hardcoded `.../tree/RAG` bucket and preserve an agent (`domain-reviewer.agent.md`) that no longer exists; the layout they manage is actively forbidden by `validate_targets.py`'s obsolete-dirs check. `improvement.md` (86 KB) is a *completed* big plan living at the repo root; its content is historical record — move it to `.claude/plans/` (its natural slot) or `docs/history/`, then remove from root.

**Docs — KEEP-FIX.** `docs/` is accurate and unusually honest overall. Fix the `review-pass-claude-*` renaming claim in `target-mapping.md:47-51` (generator performs no renaming), and reconcile `check_runtime.py`'s "optional" framing of `uv`/`context-mode` with the Dockerfile/validator treating them as required — after R-HOOKS-03, `uv` genuinely becomes optional for guardrails, resolving the split in `check_runtime.py`'s favor.

---

## 5. Prioritized Recommendations

Format: each block maps onto one small plan; §6 clusters them into big plans.

### P0 — integrity (believed enforced, isn't)

**R-HOOKS-01: Close the git-command classifier gaps** `[REWORK: enforce-commit-gate; SIMPLIFY: _lib]`
*Problem:* Classifiers match subcommands only in position 2, so `git -C . commit`, `git -c k=v commit`, and aliases bypass commit/branch/PR gates silently (`_lib-frontmatter.sh:247-257`; verified by execution).
*Change:* Tokenize past global git flags (`-C <path>`, `-c <k=v>`, `--git-dir`, `--work-tree`) before subcommand detection; add validator cases for each evasion shape.
*Acceptance:* `validate_targets.py` gains payloads `git -C . commit -m x`, `git -c a=b commit -m x` asserting deny without plan artifacts.
*Depends:* none. *Effort:* S.

**R-HOOKS-02: Narrow the bypass-prefix skip** `[REWORK: enforce-commit-gate]`
*Problem:* `fixup!`/`squash!`/`chore(typo):`/`docs(typo):` subjects skip the entire gate before any check (`enforce-commit-gate.sh:22`, `_lib:276-281`) — the strictest gate is opt-in.
*Change:* Bypass subjects skip only plan-ceremony checks (small-plan/closeout/score/LEARN); branch-shape validation still runs; bypass is still ledgered. Keeps the recovery use-case, removes the blank check. (No new bypasses introduced; the existing ones get narrower.)
*Acceptance:* validator case: `git commit -m "chore(typo): x"` on a non-`*_implementation` branch → deny.
*Depends:* R-HOOKS-01. *Effort:* S.

**R-HOOKS-03: Make protect-files/git-protection survive without `uv`, and fail toward `ask`** `[SIMPLIFY / KEEP-FIX]`
*Problem:* Both `exit 0` when `uv` is missing (`protect-files.sh:12-14`, `git-protection.sh:12-14`) — the two most safety-critical guards vanish silently exactly in minimal environments.
*Change:* Pure-bash primary check (pattern match on candidate paths / git-command regex); Python precision pass only as enhancement; on internal failure emit `permissionDecision: ask` (deny on Codex), never silent allow; log to `hooks-errors.log`.
*Acceptance:* validator runs both scripts with `uv` masked from PATH; `.env` write payload still denied.
*Depends:* none. *Effort:* M.

**R-HOOKS-04: Use fail-closed exit codes where platforms provide them** `[layer-wide]`
*Problem:* Every script exits 0; blocking rides solely on stdout JSON. Copilot preToolUse treats non-zero exit as deny; Codex accepts exit 2 — free fail-closed semantics unused.
*Change:* On *internal error paths* (unparseable payload, missing repo root, awk failure) exit non-zero (2 for Codex targets) instead of silently allowing; keep exit 0 for genuine allow.
*Acceptance:* corrupted-JSON payload test → non-zero exit → deny on Copilot/Codex runners.
*Depends:* R-HOOKS-03. *Effort:* M.

**R-SYNC-01: Bucket name to configuration** `[REWORK: installer/sync — author-endorsed]`
*Problem:* `Ghisso/vscode_mounts` hardcoded as default/required in `install_bootstrap.py:49`, `hf-ai-sync.py:19`, `devcontainer.json`, `validate_targets.py:1117,1150,1193`.
*Change:* Require `--bucket` or `HF_AI_SYNC_BUCKET` (installer errors without one); sync helper keeps its resolution chain minus the hardcoded default; validator asserts "bucket configured", not its value.
*Acceptance:* `grep -r "Ghisso/vscode_mounts" scripts/ shared/` → only docs/examples; installer without bucket exits with instruction.
*Depends:* none. *Effort:* S.

**R-SYNC-02: Stop re-mirroring the bootstrap from consumers** `[REWORK: sync]`
*Problem:* Every consumer Stop runs `upload-bootstrap` with `delete=True` (`hf-ai-sync.py:374`; `settings.json:122`) — any consumer can overwrite the canonical bundle with its stale copy.
*Change:* Remove `upload-bootstrap` from generated Stop hooks; bootstrap uploads happen only from `install_bootstrap.py`/`update_consumers.py`. Consumers push state only.
*Acceptance:* generated `settings.json`/`.codex/hooks.json`/`hooks.json` contain `push-state` but not `upload-bootstrap`; validator asserts it.
*Depends:* none. *Effort:* S.

**R-AGENTS-01: Reconcile the orchestrator's contract** `[REWORK: orchestrator]`
*Problem:* Prompt mandates branch/commit/PR/memory/log actions (`prompt.md:23-34,77-83`); capabilities grant none of them (`agent.yaml:6-11`); Codex adapter is read-only.
*Change:* Decide identity (main-thread persona with `execute`+`edit`, not delegatable | coordinator-pattern documented in instructions with mechanics owned by the main session). Update agent.yaml + prompt + Codex sandbox to match. Non-trivial-only scope unchanged.
*Acceptance:* every imperative in the prompt is executable with the granted tool list (manual audit noted in the small plan); validator checks orchestrator toolset ⊇ prompt-declared actions where machine-checkable.
*Depends:* R-AGENTS-02 (same decision). *Effort:* M.

**R-AGENTS-02: Resolve review-delegation depth per runtime** `[KEEP-FIX: reviewer; MERGE: review-pass-primary]`
*Problem:* reviewer→helpers is nesting level 2: Codex `max_depth=1` forbids it (doc-verified); VS Code nesting off by default; on Codex the PR gate can never pass via Degraded Mode rules (`reviewer/prompt.md:48`).
*Change:* Preferred (runtime-independent): fold both passes into the reviewer as sequential phases — pass 1 findings, then a refutation pass per R-AGENTS-03 — deleting the two helper agents. Alternative: raise Codex `max_depth` to 2 and gate VS Code docs on the experimental flag; keep helpers.
*Acceptance:* orchestrated review completes and can PASS a PR gate on all three targets (smoke-test doc updated with the per-runtime expectation).
*Depends:* none. *Effort:* M.

**R-SYNC-03: Decide and implement the Copilot-cloud surface** `[REWORK: installer]`
*Problem:* Cloud agents load `.github/agents//hooks/` only from the default branch [doc-verified]; installer gitignores them (`install_bootstrap.py:20-32`) — cloud surface silently unconfigured in every consumer.
*Change:* Installer flag `--commit-copilot-surface` that omits those paths from the ignore block (they are generated-but-committable, like `.devcontainer/`); README states the default is local-IDE-only.
*Acceptance:* install with flag → `.github/agents/` not in the ignore block and `git status` shows them trackable; without flag → README section documents the limitation.
*Depends:* none. *Effort:* S.

### P1 — effectiveness (weak signal, gaming-inducing friction)

**R-SCORE-01: Make the score honest — rubric ↔ scorer alignment plus gate hardening**
*Problem:* Documented rubric unimplemented; `--skip-tests` yields `tests_passed=True` at score 100 (`quality_score.py:200-201`); gate reads only `score` (`enforce-commit-gate.sh:85`); `dirty` presence-checked, not false; scored `target` need not overlap changed files.
*Change:* (a) Gate additionally requires `tests_passed == true` and `dirty == false`; (b) scorer records `tests_skipped` explicitly and the gate rejects it; (c) rewrite the rubric section of `quality-and-testing.instructions.md` to describe the real arithmetic; (d) direction for the next iteration: severity-count predicate over review findings (upstream-tested) rather than deeper numeric rubric — numeric self-grading is the documented gamed setup [external].
*Acceptance:* validator case: report with `tests_passed: false` or missing → commit denied even at score 100.
*Depends:* none. *Effort:* M.

**R-SCORE-02: Deterministic report selection and diagnosable failures**
*Problem:* First reverse-lexical filename match per branch+phase (`enforce-commit-gate.sh:72-80`); stale report shadows fresh; mtime-vs-changed-files check breaks on amend/rebase/editor-touch with opaque messages that push users toward bypass prefixes.
*Change:* Select newest matching report by `generated_at`; replace mtime comparison with content-hash of changed files stamped into the report by the scorer; failure messages name the exact mismatched field and the command to regenerate.
*Acceptance:* validator: two reports for same branch/phase (older passing, newer failing) → gate uses newer; amended-HEAD scenario produces a message containing "re-run quality_score".
*Depends:* R-SCORE-01. *Effort:* M.

**R-AGENTS-03: Turn the adversarial pass into a verification pass**
*Problem:* Told to challenge a primary pass it never receives (`review-pass-adversarial/prompt.md:32` vs `reviewer/prompt.md:31-34`) — mislabeled independent ensemble.
*Change:* Second pass receives pass-1 findings and attempts to refute each (drop findings that fail re-verification; keep genuinely new criticals it finds). Convergence rule: stop when a pass yields nothing new twice, cap at 3 rounds.
*Acceptance:* reviewer prompt shows pass-2 input contract includes pass-1 findings; smoke-test doc updated.
*Depends:* R-AGENTS-02. *Effort:* S.

**R-AGENTS-04: Merge designer into coder**
*Problem:* Verified strict-subset capabilities (minus `todo`, `web`), 36-line prompt with no verification suite/simplification/control-plane guard — weaker-gated write path for the same class of work.
*Change:* Delete `shared/agents/designer/`; coder's Tier-2 loads `gradio-streamlit` for UI tasks (already its pattern); orchestrator routing table updated.
*Acceptance:* agent count consistent across all three adapter sets (checked by parity, not a fixed number; the post-implementation count is 6 after R-AGENTS-02 also removed two review helpers — see §0); validator counts updated; routing table has no designer row.
*Depends:* R-AGENTS-05. *Effort:* S.

**R-AGENTS-05: One authoritative profile-routing table**
*Problem:* Five drifting copies (orchestrator `:40-50`, reviewer `:20-28`, planner `:71`, `workspace.instructions.md:80-93`, `code-review/SKILL.md:14-25`), already unequal; planner/README point at nonexistent-in-consumers `shared/review-profiles/`.
*Change:* Table lives once in `workspace.instructions.md` (or a dedicated `review-routing.instructions.md`); agents/skills reference it by path; all profile paths become `.claude/review-profiles/`; add a validator parity check that no second copy of the table's rows exists.
*Acceptance:* `grep -r "review-profiles" shared/ | grep -v .claude/` → only the source dir itself; single table location.
*Depends:* none. *Effort:* S.

**R-AGENTS-06: Consumer-correct control-plane paths**
*Problem:* coder/orchestrator control-plane guards enumerate `shared/`, `dist/` (`coder/prompt.md:21`) — nonexistent in consumers; guard never fires where installed.
*Change:* Express control-plane as consumer paths (`.claude/hooks/`, `.claude/settings.json`, `.github/hooks/`, `.codex/`, `CLAUDE.md`, `AGENTS.md`, `.mcp.json`), with the authoring-repo paths listed only in this repo's own copy via a generator substitution.
*Acceptance:* `grep -rn "shared/\|dist/" dist/multi-agent/.claude/agents/` → no matches.
*Depends:* none. *Effort:* S.

**R-AGENTS-07: Documenter fixes** — diff base `originating_branch` (default `dev`) instead of `main` (`documenter/prompt.md:28-29`); drop the nonexistent `api-service-standards` skill reference (`:11`); move Mermaid rules into the `documentation` skill. *Acceptance:* grep for `main...HEAD` in agents → none. *Effort:* S.

**R-AGENTS-08: Single score-report owner** — verifier produces the canonical report; coder runs checks but writes no `--out`; orchestrator SCORE step consumes verifier's path. Removes ambiguous multi-report selection pressure. *Depends:* R-SCORE-02. *Effort:* S.

**R-HOOKS-05: Tolerant commit-subject correlation** — normalized prefix match + explicit warning and documented recovery command on miss (`record-commit-closeout.sh:28-32`). *Effort:* S.

**R-HOOKS-06: Portable mtime/find** — replace `stat -c` and `find -newermt` with portable probes (`enforce-commit-gate.sh:131-149`, `stop-session-log-check.sh:20`); on failure warn, don't silently pass. *Effort:* S.

**R-CODEX-01: Align Codex adapters with current docs** — skills paths in documented absolute-`SKILL.md` form (or verified working relative form with a comment citing the test), drop redundant `[features] hooks = true`, add PreCompact group (`generate_targets.py:383-439`). *Acceptance:* validator asserts the three properties. *Effort:* S.

**R-SYNC-04: MEMORY.md single-homing + push-state prune option** — remove MEMORY.md from `BOOTSTRAP_PATHS` (`hf-ai-sync.py:39`); add `push-state --prune` reconciliation; document `.state_backups/` ephemerality. *Effort:* M.

**R-SKILLS-01: Rewrite the `commit` skill around the enforced lifecycle** — `*_implementation` off `dev`, PR to `dev`, human merge; fix `templates/quality-report.md:16`. *Acceptance:* skill contains no `feature/` or `gh pr merge`; validator literal check acceptable here. *Effort:* S.

### P2 — hygiene

**R-DEBLOAT-01:** Delete `download.py`, `upload.py`; move `improvement.md` → `.claude/plans/` (or `docs/history/`). *Acceptance:* repo root contains no orphan scripts; `git log` records the move.
**R-DEBLOAT-02:** Delete `iterative-plan-review` skill; merge `retrieval-routing` into tool-routing policy; regenerate. *Acceptance:* skill count 50; Codex `[[skills.config]]` count matches.
**R-GEN-01:** Prune dead generator code (model transforms `:201-212`, identity `mapped_agent_name`, unused multi-target branches); rename `manifest.yaml`/`servers.yaml` → `.json` or parse real YAML; drop or Copilot-scope the `vscode` capability. *Acceptance:* `validate_targets.py` still passes; determinism check with `shallow=False`.
**R-LIB-01:** Delete `fm_has`/`hook_tool_name`; single home for the `*_implementation` regex and the `uv`-guard block; one JSON-number parser (session-start-state `:37` → `_lib`).
**R-POLICY-01:** Scope the `__future__` ban to Hydra modules; installer substitutes the workspace `[TODO]` placeholder with the target project name.
**R-DOCS-01:** Fix `target-mapping.md:47-51` renaming claim; reconcile `check_runtime.py` optional-vs-required framing after R-HOOKS-03 lands.
**R-PROMPTS-01:** Extract the repeated Retrieval block and the caveman-reporting block into one instruction file included by reference; agents keep a one-line pointer. Goal: one source of truth for the shared blocks, not a size reduction. (Post-implementation note, 2026-07-07: the earlier "~25–30% prompt shrink" estimate did not hold — the repeated blocks were smaller than estimated, so the net change to prompt bodies is ≈0%. The single-homing benefit stands; see §0.)
**R-VALID-01:** Convert brittle exact-sentence assertions to structural checks; date-stamp the Copilot model allow-list against the official supported-models page.
**R-SKILLS-02:** Align `plan-decomposition` with the single small-plan file model.

---

## 6. Suggested Plan Clustering

Four big plans, phased so each phase is one R-item (= one small plan, one commit):

**`gate-integrity`** — *Context:* the hook layer's blocking guarantees have verified silent-bypass and fail-open paths; this plan makes every gate either genuinely enforce or honestly warn. *Phases:* R-HOOKS-01 → R-HOOKS-02 → R-HOOKS-03 → R-HOOKS-04 → R-HOOKS-05 → R-HOOKS-06 → R-SCORE-01 → R-SCORE-02. *Success:* validator's adversarial payload suite passes; no silent-allow path on classifier miss or missing dependency.

**`agent-contract-repair`** — *Context:* three agent contracts (orchestrator capabilities, review nesting, adversarial input) cannot execute as written on the target runtimes; this plan makes every agent's promise executable. *Phases:* R-AGENTS-02 → R-AGENTS-01 → R-AGENTS-03 → R-AGENTS-04 → R-AGENTS-05 → R-AGENTS-06 → R-AGENTS-07 → R-AGENTS-08. *Success:* orchestrated flow completes end-to-end (branch → PR-gate PASS) on all three runtimes, or documented per-runtime scope where a surface is unsupported.

**`sync-config-hardening`** — *Context:* the bucket is hardcoded and the sync topology lets consumers mutate the canonical bundle; this plan makes sync configurable, one-directional for bootstrap content, and durable for state. *Phases:* R-SYNC-01 → R-SYNC-02 → R-SYNC-03 → R-SYNC-04 → R-CODEX-01. *Success:* fresh install with only `--bucket`; Stop hooks push state only; Copilot-cloud decision recorded in README.

**`debloat-and-drift`** — *Context:* accumulated drift (dead scripts, contradicting skill, five routing tables, doc≠generator) taxes every future change; this plan removes the dead weight and gives each fact one home with validator parity checks. *Phases:* R-SKILLS-01 → R-DEBLOAT-01 → R-DEBLOAT-02 → R-GEN-01 → R-LIB-01 → R-POLICY-01 → R-DOCS-01 → R-PROMPTS-01 → R-VALID-01 → R-SKILLS-02. *Success:* validator gains parity checks; regeneration idempotent; no contradiction between any skill and any hook.

Suggested order: `gate-integrity` first (it protects the work that follows), then `agent-contract-repair`, `sync-config-hardening`, `debloat-and-drift` in any order.

---

## 7. Appendices

### A. Method

Four independent research passes (agent system; hook layer; lifecycle/policies/generator/sync; upstream + platform documentation) produced a findings dossier; a fifth pass designed this report's structure. Every P0 citation and every count was then re-verified first-hand at the reviewed commit; the upstream and platform claims were sourced from official documentation accessed 2026-07-03. Citation convention: `path:line` at commit `9b80b3d8`.

### B. Epistemic status of non-verified claims

- **External (documentation-sourced, accessed 2026-07-03):** all Copilot/Codex platform behaviors (§3.3, R-SYNC-03, R-CODEX-01) — sourced from docs.github.com, code.visualstudio.com, developers.openai.com reference pages; upstream project history — sourced from its repository changelog and rules files. These reflect documentation at access time; platforms move.
- **External (literature):** the claim that numeric LLM self-grading invites reward hacking and self-preference bias is well-supported in 2025–2026 evaluation literature; specific figures circulating (e.g. ~25% self-preference win-rate inflation) were not independently re-verified for this report and are cited generically. Note its correct scope here: today's scorer is deterministic arithmetic; the bias risk applies to the review passes and to agent-controlled scorer *inputs* (`--skip-tests`, target selection), and to any future rubric implemented via LLM judgment.
- **Inferred (mechanism verified, incident not observed):** consumer-clobbers-canonical-bootstrap via `delete=True` Stop mirroring; commit-gate false-block → bypass-prefix incentive loop; Codex relative-path skills wiring possibly no-oping.
- **Taste (defensible disagreement):** caveman-format mandates on 8 of 9 agents; the Mermaid section's weight in documenter; the multi-target LCD trade-off itself (§3.3).

### C. Count derivations (at `9b80b3d8`)

```bash
git rev-parse HEAD                                    # 9b80b3d8b5f9...
ls -d shared/agents/*/ | wc -l                        # 9
ls shared/hooks/scripts/*.sh | wc -l                  # 14
ls shared/policies/*.instructions.md | wc -l          # 9
ls shared/review-profiles/*.md | wc -l                # 9
ls -d shared/skills/*/ | wc -l                        # 52
grep -l "visibility: public" shared/skills/*/SKILL.md | wc -l      # 36
grep -l "visibility: background" shared/skills/*/SKILL.md | wc -l  # 16
wc -l shared/hooks/scripts/*.sh shared/hooks/hooks.json            # 1,334 + 168 = 1,502
grep -l "tool-routing.instructions" shared/agents/*/prompt.md | wc -l  # 9 (Retrieval boilerplate)
grep -l "caveman" shared/agents/*/prompt.md | wc -l                    # 8
ls shared/skills/ | grep -c "api-service-standards"                    # 0 (referenced, absent)
```

Line-count note: "1,502 lines" for the hook layer includes `hooks.json` (168); scripts alone are 1,334.
