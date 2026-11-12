# Exploration — Review of the Shipped Skills and Instructions

**Date:** 2026-11-12
**Status:** DECIDED on 2026-11-12. Feeds the big plan
`.claude/plans/skills-and-instructions-trim.md`.
**Trigger:** the user said the shipped instructions and skills "are too much
now and just bloat the context", and asked for a devil's-advocate review that
decides what to keep, update, and remove.
**Method:** sizes measured from `shared/`; skill use counted in Codex session
logs (`~/.codex/sessions`, 2026-05-13 to 2026-11-12) and Claude Code transcripts
(about four weeks) for this repository, RAG, and industrial-inspection. The
devil's advocate ran as two separate read-only Opus subagents at `xhigh` effort
with `.claude/skills/devils-advocate/SKILL.md`, one for skills and one for
instructions. The main agent re-checked their high-risk claims against the
files before accepting them (marked **re-checked**).

---

## 1. Read this first

- The biggest cost is not the skills. It is what agents are told to read before
  real work: all of `.claude/MEMORY.md` (125,594 bytes, 367 entries, here) and
  `workflow.instructions.md` (40,797 bytes).
- The skill list does cause a real failure: in Claude Code the descriptions of
  55 shipped skills (19,579 characters) overflow the skill-listing budget, so
  some skills are listed by name only and cannot be matched to a task.
- The user **rejected** the "manual-only" idea (`disable-model-invocation:
  true`). Every kept skill stays model-visible. The replacement is a short
  description for every skill plus a validator cap (section 4).
- Several verdicts were reversed by the devil's advocate because a validator,
  the Codex fallback map, or the sidecar default set depends on them (section 6).
  Do not re-propose those cuts without reading that section.

## 2. How context is spent (verified)

From the Claude Code skills documentation (read 2026-11-12):

- Every skill name and description is listed to the model on every turn;
  bodies load only when used.
- The listing has a character budget that scales at 1% of the model's context
  window. On overflow, Claude Code drops descriptions, starting with the skills
  invoked least. Our agents mostly read `SKILL.md` files by path, so the
  invocation counter sees almost nothing; in this session the dropped ones were
  the alphabetical tail of the shipped set (prompt-lab through
  text-to-sql-safety).
- Each description (plus `when_to_use`) is capped at 1,536 characters.
- `user-invocable: false` and our own `visibility: background` do **not** remove
  a description from context.
- `CLAUDE.md` loads every turn. `AGENTS.md` loads every turn in Codex and
  Antigravity. `.claude/rules/*.md` with `paths:` load only when matching files
  are touched.

Per-task reads today (bytes):

| When | What | Size |
| --- | --- | --- |
| every turn | `CLAUDE.md` / `AGENTS.md` / `copilot-instructions.md` | 6,507 / 9,467 / 1,393 |
| every turn | 55 skill descriptions | 19,579 characters |
| every non-trivial task | `.claude/MEMORY.md` | 125,594 here; RAG 60,110; industrial 30,613 |
| every non-trivial task | `workflow.instructions.md` | 40,797 |
| every standard task | orchestrator prompt | 16,178 |
| every coding task | ponytail + code-style + code-standards + testing-patterns | about 9,850 |
| every plan, one-step too | plan-decomposition | 7,718 |

User-level, not shipped: 10 `opik*` skills (6,135 description characters),
installed 2026-10-02 from `comet-ml/opik-skills` into `~/.agents/skills/` with
links in `~/.claude/skills/` (record: `~/.agents/skills/.opik-skills.json`).
They are not added by the Opik MCP server, and they load in every project.

## 3. Skill use (Codex logs, calls naming `skills/<name>/SKILL.md`)

RAG (85 sessions) / industrial-inspection (25) / this repository (573,
inflated by maintenance). Zero means zero in all three unless noted.

- Heavy: ponytail 56/45/338, testing-patterns 31/21/165, code-review
  34/15/103, code-style 28/5/120, documentation 16/11/115, onboard 15/6/109,
  plan-decomposition 13/6/106.
- Moderate: learn 9/1/41, commit 8/3/106, integration-gate-spike 7/9/54,
  humanize 3/11/84, ponytail-review 3/13/89, safe-consumer-bootstrap-refresh
  2/20/47, draw-io 1/9/0, hydra-config 6/0/3, pyvis-xss-testing 6/0/11.
- Light (1 to 5 in consumers): context-status, knowledge-refresh,
  create-feature, add-dependency, run-tests, deep-audit, caveman-compress,
  devils-advocate, caveman, bentoml-service, setup-project,
  pandas-nan-bool-coercion, md-to-pdf, docling-haystack, ollama-chat-generator,
  text-to-sql-safety.
- None in either consumer: refactor, debug-investigator,
  context-manager-testing, review-api, deploy-service, prompt-lab, rag-auditor,
  test-helper-public-api, data-analysis, haystack-conditional-router,
  dataclass-classvar-constant, domain-type-placement, pipeline-patterns,
  concept-to-image, csv-driven-integration-tests, extraction-metadata-sourcing,
  gradio-streamlit, graph-schema-compat-migration, html-presentation,
  literature-review, networkx-igraph-graphml-interop, pdf, research-critique.
  (RAG is a Haystack RAG project, yet the Haystack and RAG skills show no use.)

## 4. Decided skill verdicts (55 → 37, all model-visible)

**Keep (35).** Every description at most 300 characters, key trigger words
first; the hash-pinned `ponytail` and `ponytail-review` are exempt. With the
cap, 14 descriptions need shorter text and the total drops to about 10,100
characters (measured), about half of today.

- Workflow core: ponytail, ponytail-review, code-review, commit,
  devils-advocate, humanize, add-dependency, caveman, learn, onboard,
  plan-decomposition, integration-gate-spike, knowledge-refresh,
  create-feature (remove its repeated Hydra section), debug-investigator (one
  of the four default sidecar skills), text-to-sql-safety (a security pattern,
  kept on its own), draw-io.
- Codex fallback skills (Codex has no path-scoped rules, so
  `CODEX_POLICY_SKILL_FALLBACKS` in `scripts/validate_targets.py` requires them):
  code-style and testing-patterns (become short pointers; their content moves
  into `code-standards` and `tests` policies), hydra-config, bentoml-service
  (absorbs deploy-service; update the deployment fallback mapping).
- Previously proposed as manual-only, now kept as normal skills with short
  descriptions: documentation, setup-project, context-status,
  safe-consumer-bootstrap-refresh, deep-audit, md-to-pdf, html-presentation,
  concept-to-image, literature-review, research-critique, prompt-lab,
  rag-auditor, gradio-streamlit, data-analysis.

**Merge.**

- pipeline-patterns + haystack-conditional-router + docling-haystack +
  ollama-chat-generator → one `haystack` skill with one `references/` file per
  topic. Update `shared/agents/documenter/prompt.md`'s pipeline-patterns path.
- pandas-nan-bool-coercion + networkx-igraph-graphml-interop +
  pyvis-xss-testing + csv-driven-integration-tests → one data-and-graph
  pitfalls skill with `references/`. Move the tests that pin two of them.
- deploy-service → bentoml-service.
- context-manager-testing, test-helper-public-api → one rule line each in
  `shared/policies/tests.instructions.md`.

**Remove (9).** review-api (alias of code-review), run-tests (the verifier is
canonical), refactor (tells the coder to persist receipts, which
`shared/agents/coder/prompt.md` forbids), pdf (generic, trigger too broad),
caveman-compress (1.2% measured gain on its main target), and four niche
lessons the user agreed to drop: dataclass-classvar-constant (already
`code-standards.instructions.md` line 46), domain-type-placement (prescribes
`src/domain/`, a layout the 2026-09-12 plan said not to impose),
graph-schema-compat-migration (obvious advice plus one project's keys),
extraction-metadata-sourcing (one project's history). This reverses the
July 2026 "keep niche skills" choice for those four only.

**Other skill changes.** The planner skips plan-decomposition in micro-plan
mode (−7.7 KB per one-step plan). The coder stops loading code-style and
testing-patterns on every task and reads the tests policy only when test
files change (about −2.9 KB per coding task). Fix
`workspace.instructions.md`'s claim that background skills are "hidden".

## 5. Decided instruction verdicts

| File | Verdict | Change |
| --- | --- | --- |
| `CLAUDE.md` | trim to about 4.3 KB | Drop repeated rules; keep validator-pinned wording (`scripts/validate_targets.py` lines 385-436, 651-700). The user chose **not** to loosen that validator to reach 3 KB. |
| `AGENTS.md` | trim to about 4.3 KB | Replace the ~3.5 KB Antigravity orchestrator supplement with a one-line pointer to `.agents/agents/orchestrator/agent.md`, which already contains it (`scripts/generate_targets.py` 969-988, 1405). Update `validate_targets.py` 703-708 and `tests/test_validate_targets.py` 460-462. |
| `copilot-instructions.md` | fix | Add the plain-language reporting pointer, fix the outdated lifecycle (no push), stop telling Copilot to load three policies before every task (`generate_targets.py` 1517-1519). |
| `workflow.instructions.md` | split, core about 15 KB | Keep task lanes, plan-first, branch, main loop. CLOSEOUT moves to its own file read at the closeout step, with a new validator pin. Pause, cancel, reopen, future phases, and the knowledge-refresh final phase move to a plan-lifecycle file with one trigger line each in the core. OpenWiki refresh merges into the knowledge-refresh skill. Remove the recovery checklist, file-protection section, and operator troubleshooting lines. Cut verification-format parse rules that the checker explains in its own errors, but keep the explanation of the two stale-receipt errors (`verify.py` 2148, 2174), whose messages do not say how to fix. |
| `workspace.instructions.md` | keep, trim to about 7 KB | Cannot merge: the validator requires the file and it owns the review-routing table. Remove repeated lists; move the hooks runtime contract to this repository's project context (consumers lack the test it cites). |
| `quality-and-testing.instructions.md` | trim to about 2.5 KB | Move the path-to-review-profile rule into workspace's routing table; delete the parts that repeat the tests policy; fix the `record_findings.py src/ …` command that differs from CLOSEOUT. Do not merge into the reviewer prompt: a validator rule allows `record_findings.py … --out` only in the orchestrator prompt. |
| `tool-routing.instructions.md` | trim to about 2.5 KB | Keep pinned sentences; move server details to docs. |
| `agent-reporting.instructions.md` | keep | Plain-language rules; heavily pinned. |
| five path-scoped policies | keep | Absorb merged skill content; cut repeated Hydra text in `config-first-design`. |
| orchestrator prompt | trim to about 12 KB, fix | Remove the conflicting Completion Protocol (section 7, item 3); stop hiding CLOSEOUT, COMMIT, and PUSH inside optional subsections. |
| documenter prompt | trim about 1.2 KB | Repeats itself and the documentation skill. |
| planner, reviewer, review profiles, templates | keep | Except the plan-small Closeout Checklist (section 7, item 2). |
| MEMORY reading rule | change wording | From "read `.claude/MEMORY.md`" to: search it for the task's area tag and keywords and read the matches; read the whole file only for a memory audit. Not a split, so the 2026-10-20 decision stands. |

Estimated effect (devil's-advocate estimates, not yet measured): the main
agent's up-front reading for a non-trivial task here drops from about 173 KB to
about 30 KB; the orchestrator path without MEMORY from about 85 KB to about 51 KB.

## 6. Cuts the devil's advocate stopped (do not re-propose without new evidence)

- Removing code-style or testing-patterns, or merging deploy-service without
  rewiring, fails `CODEX_POLICY_SKILL_FALLBACKS` and leaves Codex with no route
  to the path-scoped policies. **Re-checked** (`validate_targets.py` 619-625,
  1249-1254).
- Removing debug-investigator breaks the four-skill default sidecar set
  (`SIDECAR_SKILLS` in `scripts/runtime_ownership.py`). **Re-checked.**
- Merging `workspace` or `quality-and-testing` away breaks validator pins.
- Folding domain-type-placement into a policy would push `src/domain/` on
  every consumer.
- Removing gradio-streamlit would leave routes in the orchestrator, coder, and
  workspace files.

## 7. Defects found during the review

1. **A bootstrap refresh deletes skills a project created itself.**
   `owned_files()` in `scripts/install_bootstrap.py` treats everything under
   `.claude/` except `CONSUMER_STATE_PATHS` and marker-claimed third-party
   skills as owned, and removes owned files with no generated source.
   **Re-checked with evidence:** RAG's own `retrieval-routing` and
   `iterative-plan-review` skills were added in nested commit `8dc7085` and
   deleted by the bootstrap update in nested commit `9015859` (2026-08-09);
   empty folders remain. The learn skill still tells projects to save skills
   there. Recovery is possible from `8dc7085` in RAG's `.claude` repository.
2. **The plan-small Closeout Checklist is wrong.** It says it mirrors CLOSEOUT
   but sets `**Status:** COMPLETED` before the first checkpoint and staging,
   and omits the second checkpoint, the closeout receipt, and the
   own-command commit. No script reads it. **Re-checked**
   (`shared/templates/plan-small.md` 53-66 against
   `workflow.instructions.md` 185-206).
3. **The orchestrator's Completion Protocol conflicts with CLOSEOUT.** It says
   to create or update the session log before returning, after the closeout
   receipt has locked that log. **Re-checked**
   (`shared/agents/orchestrator/prompt.md` 159-174).
4. **Four control-plane lists disagree** with each other and with the commit
   gate (`CONTROL_PLANE_PREFIXES` in `shared/scripts/verify.py` treats all of
   `.claude/`, `.codex/`, `.agents/`, `.github/`, `.devcontainer/` as control
   plane). **Re-checked** (CLAUDE.md, AGENTS.md, workspace line 94, coder
   line 23).
5. **Two files say MEMORY.md is "loaded into every session".** Nothing loads it.
   **Re-checked** (workflow line 450, documenter line 98).
6. **Copilot root file** has an outdated lifecycle and no plain-language rule.
   **Re-checked.**
7. **Unverified: Codex may list every skill twice.** `.codex/config.toml`
   enables all 55 `../.claude/skills/<name>/SKILL.md` paths, and Codex also
   reads `.agents/skills/`; `docs/sidecar-provider-contract.md` says duplicate
   names "both appear". Needs a short Codex check.

## 8. Decisions recorded (user, 2026-11-12)

- No manual-only flag. The replacement (keep the skills model-visible with
  descriptions of at most 300 characters, enforced by a validator cap) is the
  main agent's proposal, to be confirmed when the plan is approved.
- Remove the four niche lessons; merge the other niche skills.
- Switch the MEMORY reading rule to a targeted search.
- Move CLOSEOUT to its own file read at the closeout step.
- Do not loosen the root-guidance validator.
- Add a project-owned skills folder that refreshes never touch, first.
- Run a short Codex check before counting on Codex savings.
- Opik skills: still open, and outside this plan because they are personal
  setup. The user asked whether they come from the Opik MCP server; they come
  from the separate `comet-ml/opik-skills` pack (section 2). One option is to
  keep them only in the two projects that use Opik (RAG, industrial-inspection);
  that needs the project-owned skills folder first.
