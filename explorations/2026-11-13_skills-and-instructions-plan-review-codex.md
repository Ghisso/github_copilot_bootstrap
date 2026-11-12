# Devil's Advocate Report

Date: 2026-11-13, Asia/Tokyo. Repository: `/home/ghisso/work/github_copilot_bootstrap`.
Reviewed on `dev`, outer HEAD `cfde280`. The outer working tree was clean.

**Verdict: CHANGE before implementation.** Keep the four phases and the decided
skill cuts. The main gaps concern filesystem safety, competing closeout advice,
the existing root validator, and evidence that can report success without
proving the claimed result.

I read the requested exploration, all five plan files, both plan templates,
the workflow policy, and the devil's advocate and ponytail skills in full.
I checked source, tests, generated output already on disk, and official OpenAI
documentation. I did not run a generator, installer, validator, verifier,
pytest, client spike, or Git command that changes state. I did not read another
reviewer's plan-review exploration. This report is the only requested write.

## Concerns

In this table, A, B, C, and D mean the four small plans in the big plan's
`phases:` list. Each action below names the full plan path.

| # | concern | risk (LOW/MED/HIGH) | alternative | ACCEPT RISK / CHANGE / INVESTIGATE | evidence (file:line) |
|---|---|---|---|---|---|
| 1 | The proposed marker predicate uses `Path.is_file()`. That follows symlinks. Rejecting links *inside* a skill does not explicitly reject a symlinked skill directory, marker, `SKILL.md`, or ancestor. Validation could read an external file before the mirror decides to skip the folder. | HIGH | Check containment and file types without following links before reading names or copying. Treat unsafe destinations as errors before writes. Keep the existing small helpers. | CHANGE | `.claude/plans/2026-11-12_phase-A-project-owned-skills.md:69`, `:73`, `:74`; `scripts/sidecar_overlay.py:3304`; `scripts/install_bootstrap.py:255` |
| 2 | The clash check reserves only folders in the incoming bootstrap. It does not reserve an existing third-party destination or prevent two project folders declaring the same skill name. In this tree OpenWiki is third-party content, absent from the generated skill set. A project mirror named `openwiki` could overwrite its destination. | HIGH | Refuse third-party destination clashes. Require a valid project name matching its directory, or check all declared project names for duplicates. Use directory entries, never frontmatter values, as destination paths. | CHANGE | `.claude/plans/2026-11-12_phase-A-project-owned-skills.md:73`; `scripts/install_bootstrap.py:264`, `:656`; `scripts/runtime_ownership.py:85`; `shared/skills/learn/SKILL.md:70` |
| 3 | A's real-run test creates a project skill only *after* a fresh install. It does not test a marked skill present before the first full install, a marker planted in a shipped skill, or an old project name becoming a later bootstrap name. Sidecar preservation is asserted without a new focused case. | MED | Extend the existing installer and sidecar tests with these transitions. Assert file bytes and link identities survive a refusal. Keep sidecar implementation unchanged. | CHANGE | `.claude/plans/2026-11-12_phase-A-project-owned-skills.md:47`, `:57`; `scripts/install_bootstrap.py:1833`, `:1837`; `scripts/sidecar_overlay.py:1465`, `:1504` |
| 4 | Replacing Claude's 200-line validator limit with a byte limit drops an existing invariant. A file can fit in 5 KiB and exceed 200 lines. That contradicts the binding instruction not to loosen the root validator. | HIGH | Keep the 200-line check and add a 5 KiB check. Tighten the existing AGENTS byte limit separately. | CHANGE | `.claude/plans/2026-11-12_phase-B-instructions.md:104`; `scripts/validate_targets.py:394`, `:654` |
| 5 | Moving pointers does not fix the other closeout procedures. The commit skill says never checkpoint after persisted receipts, which conflicts with the required second checkpoint after the phase receipt. README's six-step recovery list omits the dry run and second checkpoint. Authoring CLAUDE also puts findings before final learning/log state. | HIGH | Delete the competing procedural summaries. Point to the new numbered procedure. Preserve only explanations that do not create another order. | CHANGE | `shared/skills/commit/SKILL.md:45`, `:47`; `README.md:302`, `:316`, `:329`; `CLAUDE.md:32`; `shared/policies/workflow.instructions.md:195`, `:197` |
| 6 | The spike has useful questions and a retry limit, but its commands do not fully establish isolation or trustworthy entry counts. S1 copies project hooks. S5 excludes project settings but still uses personal settings. Counting every matching path in raw JSON can count prose references as listings. The scratch path is fixed rather than created uniquely. | HIGH | Use a new directory outside this checkout. Copy only required fixtures. Establish supported per-run hook isolation first. Parse actual skill entries. Abort a probe when isolation or the output contract cannot be established. | CHANGE | `.claude/plans/skills-and-instructions-trim.md:151`, `:160`, `:162`, `:169`, `:174`; `.codex/hooks.json:3`; `shared/hooks/scripts/state-sync.sh:283` |
| 7 | A failed S1 or S5 is recorded, but the outcome table does not say whether implementation may continue with unproved assumptions. S3 has no outcome row. The S5 no-warning result is treated as proof that every description loaded, including when the baseline also has no warning. | MED | Define unsupported/error/no-entry outcomes. Separate a measured entry list from the absence of a log warning. | INVESTIGATE | `.claude/plans/skills-and-instructions-trim.md:185`, `:191`, `:193`, `:201`; `.claude/plans/2026-11-12_phase-C-skill-set.md:172` |
| 8 | Several required absence checks hide search errors behind `wc -l`. A missing directory or failed read can become zero matches and exit 0. Some checks test only a phrase, rather than the promised behavior. | MED | Check input existence and distinguish grep exit 1 from exit 2. Prefer a short Python assertion for compound invariants. Keep existing diagnostic checks where they are useful. | CHANGE | `.claude/plans/2026-11-12_phase-B-instructions.md:248`; `.claude/plans/2026-11-12_phase-C-skill-set.md:156`; `.claude/plans/2026-11-12_phase-D-knowledge-refresh.md:93`; `shared/scripts/verify.py:611` |
| 9 | C expects exactly 14 initial cap errors against the unchanged 55-skill library. There are 24 non-exempt descriptions over 300 characters today. Fourteen applies only to the 35 kept skills. Its total-length command also omits the `when_to_use` text that Step 1 says counts. | MED | Expect 24 before removal and 14 among kept skills. Use one length definition in the cap and aggregate check. | CHANGE | `.claude/plans/2026-11-12_phase-C-skill-set.md:60`, `:63`, `:155`; `scripts/validate_targets.py:8325`, `:8587` |
| 10 | The current session cannot prove the generated bundle's duplication behavior. The tracked working config has zero skill-config entries; the generated config has 55. Antigravity's pointer and Claude's complete description listing also remain unobserved here. | MED | Keep a bounded native check and label each result by client, configuration, and evidence type. Do not claim a description-budget fix from this session alone. | INVESTIGATE | `.codex/config.toml:1`; `scripts/generate_targets.py:1058`; `docs/sidecar-provider-contract.md:523`, `:526`; `.claude/plans/2026-11-12_phase-B-instructions.md:73` |
| 11 | S2 tests hiding even though no allowed outcome changes the plan. B also says every file is edited in one step, while its validator step explicitly requires tests to fail before later source edits. That bookkeeping rule can force awkward work without improving review. | LOW | Remove S2. Treat the file list as phase ownership, not a prohibition on revisiting a file after failing tests or review. | CHANGE | `.claude/plans/skills-and-instructions-trim.md:81`, `:170`, `:202`; `.claude/plans/2026-11-12_phase-B-instructions.md:78`, `:111` |
| 12 | The marker is opt-in and mirrors are refreshed only during install. Existing unmarked skills remain vulnerable. A project skill created in only `.claude/skills/` in a sidecar repository does not become visible to Codex through this mechanism. | MED | Keep the chosen design. State that the discovery/mirror promise is for full installs. Put the unmarked-skill inventory before every documented full-refresh path. | ACCEPT RISK | `.claude/plans/skills-and-instructions-trim.md:139`, `:144`; `.claude/plans/2026-11-12_phase-A-project-owned-skills.md:96`; `scripts/install_bootstrap.py:1806` |
| 13 | Four phases are enough. A then B then C then D has no demonstrated reverse dependency. Required control-plane review adds work, but is a binding constraint. A reference bundle does not itself break the sidecar allowlist. | LOW | Keep the four phases and review profiles. Do not add a phase or redesign sidecar packaging without a concrete failure. | ACCEPT RISK | `.claude/plans/skills-and-instructions-trim.md:88`; `scripts/runtime_ownership.py:331`; `scripts/generate_targets.py:1917` |
| 14 | The 37-skill target, exact removals, merges, and two hash-pinned exemptions are internally consistent. The measured baseline is accurate. Shorter descriptions do not by themselves prove better skill matching. | LOW | Keep these decisions. Treat host listing quality as separate evidence. | ACCEPT RISK | `.claude/plans/2026-11-12_phase-C-skill-set.md:27`; `scripts/validate_targets.py:8325`; `.claude/explorations/2026-11-12_skills-and-instructions-review.md:102` |

## Action items: exact edits to the plans

These are edits to make later. This review did not change the plans.

1. **CHANGE 1 — A, Step 2.** In
   `.claude/plans/2026-11-12_phase-A-project-owned-skills.md`, replace the
   `Path.is_file()` definition at line 69 with a requirement for a real
   directory and a regular marker checked with `lstat`, without following
   links. Before reading `SKILL.md`, validate the containing roots and the
   file itself. Require source and destination containment under the intended
   roots. Explicitly reject a symlinked skill root, marker, `SKILL.md`, and
   source/destination ancestor. Preserve the chosen warning-and-skip behavior
   for an unsafe entry found inside an otherwise valid project folder.
   Check the complete folder before copying any of it. Do not parse a name
   from an unsafe file. Add these cases to Step 1, including an external
   sentinel whose bytes and location must not change.

2. **CHANGE 2 — A, Steps 1 and 2.** Extend
   `validate_project_skills` in the same plan to refuse a project destination
   already claimed by a third-party skill. Include `.agents/skills/openwiki`
   in the test. Require `name` to match the directory, as learn already says,
   and reject duplicate identities. Use the directory name for the mirror
   destination. Reject separators and special path segments in any value
   accepted as a path component. Define case handling for filesystems where
   case differs only in spelling. Add a refusal test for a marker planted in
   a shipped bootstrap folder. Do not change OpenWiki's ownership rule or
   introduce a second ownership registry.

3. **CHANGE 3 — A, Step 1 and Review.** Add a real CLI case with a marked
   skill present *before* the initial full install. Exercise its legacy
   migration path. Add refresh transitions where the source later ships the
   project's name: refusal while the marked original remains, and successful
   bootstrap replacement after deliberate project removal. Check both the
   live `.agents` tree and `bootstrap-root`. Add focused cases in
   `tests/test_sidecar_install.py` and `tests/test_sidecar_update.py` for an
   existing foreign project skill on initial install and refresh, and a
   locally modified recorded skill with an added marker. Keep sidecar code
   unchanged unless these cases reveal a real defect.

4. **CHANGE 4 — B, Step 1, Budgets.** In
   `.claude/plans/2026-11-12_phase-B-instructions.md`, replace line 104's
   metric replacement with: keep `CLAUDE.md`'s 200-line check and add a
   5 KiB maximum; reduce AGENTS' existing maximum to 5 KiB. Add a negative
   test for a structurally valid root file over 200 lines but under 5 KiB.
   Keep the existing required headers, fragments, and inventory checks.

5. **CHANGE 5 — B, Steps 3 and 7.** Explicitly replace the procedure in
   `shared/skills/commit/SKILL.md:45-47` with the new closeout-file pointer.
   Keep the own-command commit rule. Say that the second checkpoint follows
   the phase receipt and dry run, and that nested state must stay unchanged
   only between the final closeout receipt and commit. Replace README's
   competing list at `README.md:302-333` with a pointer and its useful
   recovery explanation. Merely changing the link at line 326 is insufficient.
   Fix authoring `CLAUDE.md:32` as part of Step 3. Add negative assertions
   against the old conflicting checkpoint sentence and six-step procedure.
   Keep eight numbered steps and reasons in the new canonical file.

6. **CHANGE 6 — big plan, Pre-branch evidence spike.** In
   `.claude/plans/skills-and-instructions-trim.md`, replace the fixed scratch
   path with a unique directory outside this repository. Define the exact
   trusted and untrusted fixtures, the minimal files each probe needs, and
   how personal as well as project hooks are prevented from running.
   Establish that mechanism from supported CLI behavior before launching
   either client. Never weaken hooks in this checkout or commit in any
   scratch repository. For each client call add a bounded runtime and treat
   hook-isolation failure as a stop. Replace path-occurrence grep at line
   169 with parsing of actual listing entries. Save a small entry sample
   with the report. A list of paths mentioned anywhere in a prompt is not
   an entry count.

7. **CHANGE 8 — verification blocks.** Edit
   `.claude/plans/2026-11-12_phase-B-instructions.md`,
   `.claude/plans/2026-11-12_phase-C-skill-set.md`, and
   `.claude/plans/2026-11-12_phase-D-knowledge-refresh.md`. Replace the recursive
   `grep ... | wc -l` absence assertions with checks that first establish
   that their input roots exist and that reads succeeded. Preserve the
   distinction between grep's no-match exit 1 and error exit 2. A short
   `python -I -c` assertion using `Path` is sufficient. Each required command
   runs in a separate `bash -c`, so a preceding `set -o pipefail` line would
   not apply to later items. Do not change the verifier for this.

   In C replace the description-only total with the same description plus
   `when_to_use` calculation used by the new validator. In D add an assertion
   that the expected refreshed pages exist and describe the new skill set;
   the absence of the exact lowercase phrase `there are 55` does not prove
   this. Keep human inspection under Optional Verification.

8. **CHANGE 9 — C, Steps 1 and 6.** In
   `.claude/plans/2026-11-12_phase-C-skill-set.md:63`, change the initial
   expected count from 14 to 24. State that 14 survive among the kept
   skills. Add a shared length definition for the cap and aggregate check,
   including `when_to_use`. The existing temporary-library cases already
   cover the 300/301 boundary and exemptions; retain them. The changed
   baseline is not a reason to change the chosen cuts or exemptions.

9. **CHANGE 11 — big plan, Constraints and spike.** Remove S2 and its outcome
   row. It cannot change an allowed implementation decision. Replace
   "Inside a phase, each file is edited in one step" with a phase ownership
   rule that permits fixes after verification and review. Keep the
   three work phases and the knowledge-refresh phase.

## Action items: open questions

- **INVESTIGATE 7:** Does the installed `codex debug prompt-input` expose
  separately identifiable skill entries, and can it run without lifecycle
  hooks? What exact field is counted? Does a config-only result of zero
  entries reflect discovery behavior, an ignored selector, an untrusted
  config, or a failed command? Record the CLI version and warnings. Add an
  explicit stop row for failure or no usable entries before relying on S1.
- **INVESTIGATE 7:** What observable Claude output proves that all 37
  descriptions reached the model? Does the selected debug mode log the
  relevant warning at all? If the baseline has no warning, no warning in
  the after run is inconclusive. Amend the outcome table and C's Optional
  Verification to record `NOT RUN` or inconclusive evidence honestly.
- **INVESTIGATE 10:** Does a trusted run of the *generated* bundle list each
  shipped skill once? This session uses a different config. Does Antigravity
  follow the new orchestrator pointer at the intended step? Keep the latter
  documented-only until a native run exists. Do not delay unrelated source
  review to pretend that unavailable client evidence has been obtained.

The table has no unassigned CHANGE recommendation. These edits fit the
existing phases; none needs another implementation phase.

## Project-skill ownership assessment

The core design can fix the deletion bug. `owned_files()` currently collects
unrecognized files under `.claude/` and deletes those missing from the source.
Pruning a marked directory from that walk prevents the deletion. The new
pre-flight can prevent bootstrap overwrite if it runs before migration and
copying, as planned. Current `main()` places that validation point before
`migrate_pre_existing_state` and `copy_generated_tree`.

The mirror-before-`populate_bootstrap_root` order is correct. The current
takeover check compares the old live `.agents` tree with its old backup.
After the install, recording the new mirror in both trees gives the verifier
matching bytes. The verifier need not learn a project-skill exemption: the
mirror remains ordinary runtime content. Removing a project skill lets the
existing obsolete-file pruning remove its old mirror. If a later bootstrap
ships the same name while the project original still exists, pre-flight must
refuse before that pruning. These are source-based conclusions, not executed
installer results.

No traversal is demonstrated merely by a frontmatter value such as
`../../outside`: the plan says it is an identity used for comparison. It
becomes a path risk if implementation uses it for the destination. State
that boundary explicitly. Do not build a generalized path framework.

The warning-and-skip rule protects the mirror only if the *entire* source
folder is inspected first, including its root and marker. It does not mean
that all project content stays out of the AI-state remote. The canonical
skill lives under `.claude/`, and state sync stages that tree. Keep learn's
existing no-sensitive-information check. Do not promise that mirror filtering
is a general privacy boundary.

Sidecar handling is different and already conservative. It exits through
`install_sidecar` before the full-install path. It checks tracked, foreign,
and locally modified content using its manifest and hashes. A marker is not
a sidecar ownership claim. Leaving sidecar code unchanged is appropriate.
It preserves existing project skills; it does not add the full install's
project-to-Codex mirror feature.

The smaller viable design is the one already proposed: one marker, one
pre-flight, the existing pruning, and one mirror step. Use existing safe
enumeration patterns and the existing frontmatter parser. No extra state
folder, registry, client abstraction, or new verifier exemption is justified.

## Removed and merged skill reference audit

I searched `scripts/`, `tests/`, `shared/`, `docs/`, and README for all 20
retired identifiers and skill paths. The nine removals and decided merges
stay binding. Most references are already assigned correctly in C.

| retired skills | current references and planned handling |
|---|---|
| `review-api`, `run-tests`, `refactor` | `README.md:1258`, `:1259`, `:1266`; `shared/policies/workspace.instructions.md:157`; workflow prompts at `shared/agents/coder/workflow-prompt.md:23` and `shared/agents/planner/workflow-prompt.md:54`; `shared/agents/coder/prompt.md:70`; `docs/smoke-tests.md:276`; `shared/sidecar/workflow/skills.txt:8`, `:11`; `tests/test_validate_targets.py:3356`, `:3381`. B removes the workspace list. C covers the rest. |
| `pdf`, `caveman-compress` | `shared/agents/planner/workflow-prompt.md:49`, `:53`; `shared/agents/coder/workflow-prompt.md:19`; `scripts/runtime_ownership.py:146`, `:160`; `README.md:1273`; `scripts/validate_targets.py:9371`; `tests/test_caveman_compress_detect.py:18`; the run-tests test's detector explanation at `tests/test_validate_targets.py:3364`. C assigns the removals and test deletion. |
| `dataclass-classvar-constant`, `domain-type-placement`, `graph-schema-compat-migration` | Definitions in their own `shared/skills/<name>/SKILL.md:2`. No additional live reference appeared in the searched scope. The existing ClassVar policy is at `shared/policies/code-standards.instructions.md:46`. |
| `extraction-metadata-sourcing` | Its own folder, including its link to CSV integration tests at `shared/skills/extraction-metadata-sourcing/SKILL.md:282`. Deleting that folder removes the link. |
| `pipeline-patterns`, `haystack-conditional-router`, `docling-haystack`, `ollama-chat-generator` | Their source folders; `shared/agents/documenter/prompt.md:13`; `scripts/runtime_ownership.py:161`; the coder/planner workflow prompts at `shared/agents/coder/workflow-prompt.md:22` and `shared/agents/planner/workflow-prompt.md:53`. C assigns the replacements. |
| `pandas-nan-bool-coercion`, `networkx-igraph-graphml-interop`, `pyvis-xss-testing`, `csv-driven-integration-tests` | Their source folders; `tests/test_validate_targets.py:3350`, `:3607`; `scripts/runtime_ownership.py:148`; `scripts/validate_targets.py:9372`; workflow prompts at `shared/agents/coder/workflow-prompt.md:16` and `shared/agents/planner/workflow-prompt.md:50`. C assigns the moves. |
| `deploy-service` | `scripts/validate_targets.py:623`; `shared/skills/setup-project/SKILL.md:32`; `shared/skills/bentoml-service/SKILL.md:30`, `:104`; `shared/sidecar/workflow/skills.txt:14`; `README.md:1279`. C explicitly covers all these. |
| `context-manager-testing`, `test-helper-public-api` | Their source folders and the cross-reference at `shared/skills/context-manager-testing/SKILL.md:109`. C replaces them with tests-policy rules and deletes the folders. |

The CSV body currently names `references/case-study.md` at lines 152 and 170.
C renames the target to `references/csv-case-study.md`. Step 2's requirement
to fix reference paths must cover these two links; unchanged prose alone will
not suffice. This is already within the planned reference-path exception.

The sidecar permits extra files inside shipped skill folders
(`scripts/runtime_ownership.py:331`). I checked the two merge groups' current
Markdown for the existing forbidden full-install tokens. Neither contains
one. There is no present reason to exclude either new bundle merely because
it has `references/`. The generator only rewrites `SKILL.md`; add a broader
rewrite only if moved reference content actually needs it.

The missing work is primarily moved-instruction advice, not a forgotten
retired-skill caller: the competing procedures in Concern 5, and the
generator missing from A's importer inventory. Future validator tests may
legitimately name retired skills to assert their absence. Historical evidence
and closed plans should retain their original names, as the plan says.

## CLOSEOUT discovery and remaining restatements

| client | route to the new procedure | assessment |
|---|---|---|
| Claude Code | Root guidance -> workflow -> CLOSEOUT step -> `closeout.instructions.md`; the orchestrator prompt and plan template also point there. | The planned route is coherent. `applicability: always` does not itself auto-load this file: the generator makes Claude rules only for path-scoped policies (`scripts/generate_targets.py:1554`). Keep an explicit instruction to read it on entering CLOSEOUT. |
| Codex | `AGENTS.md` -> workflow -> CLOSEOUT step; native orchestrator instructions and the commit skill provide additional pointers. | Structurally supported. The main-session role must follow the pointer; Codex does not discover arbitrary instruction files solely from their names. |
| Copilot | The new root-adapter sentence explicitly names the file before commit. Workflow and orchestrator adapters add pointers. | Covered by B Step 3. The generator already emits a canonical-policy pointer for each policy (`scripts/generate_targets.py:1523`). Native loading remains a separate observation. |
| Antigravity | `AGENTS.md` -> `.agents/agents/orchestrator/agent.md` -> its transformed canonical workflow/CLOSEOUT pointer. | The generated role includes the supplement through `provider_agent_prompt_body` (`scripts/generate_targets.py:950`). Following the new short pointer is inferred, not observed. Retain B's pointer and supplement tests. |

README's six-step procedure, commit's checkpoint paragraph, and authoring
CLAUDE's lifecycle summary still need explicit replacement. B currently names
these files but does not clearly require deleting the conflicting content.
The template's two boxes are suitable: they record early state, then defer
the real gates to the numbered procedure. Do not add receipt or commit boxes
that would require editing the plan after its bytes have been bound.

## Verification review

I extracted the fenced shell commands under the actual `## Verification`
headings and ran syntax-only `bash -n -c` checks. No command was executed.

| plan | required commands | shell syntax | contains `rg` |
|---|---:|---|---|
| A: project-owned skills | 12 | valid | no |
| B: instructions | 41 | valid | no |
| C: skill set | 21 | valid | no |
| D: knowledge refresh | 10 | valid | no |

They use the required fenced format and do not list `verify.py closeout`.
The optional host checks are in the correct section. Full small-plan
frontmatter, phase order, owner/skill assignments, and the required five
control-plane profiles are present in every phase. D has the required
`-knowledge-refresh` suffix and final-phase audit. No later-phase dependency
was found in A. B closes under its newly installed procedure. C uses the
policies and procedure from B. D consumes their final behavior.

Checks that need stronger interpretation:

- B lines 248-249, C line 156, and D lines 93-94/97 use a search-to-count
  pipeline. A failed search can yield zero and pass. `bash -c` does not
  enable `pipefail` automatically.
- D line 94 rejects only the exact lowercase substring `there are 55`.
  `55 skills`, `There are 55`, a wrong count of 36, or missing relevant
   pages can pass. The later marker/path searches prove two strings exist
  somewhere, not that all named pages were refreshed correctly.
- C lines 159-161 prove that old loading phrases disappeared. They do not
  prove the replacement rules exist. The planned review is useful, but add
   focused positive assertions for the full-plan-only route, micro-plan
  template reads, and conditional tests-policy read to Step 6's existing
  prompt checks. Put this addition under CHANGE 8.
- A's `cmp`, existing OpenWiki marker, and broad legacy suites can pass
  before this feature exists. They remain useful compatibility checks.
  The new failing `project_skill` cases supply the behavioral proof.
- B's `wc -c` line prints measurements. Its following `test` commands
  enforce the budgets. Do not describe the printout alone as validation.
- C's count checks prove 37 folders, not the exact retained set. Its planned
  `test_retired_skills_stay_removed` and validator checks should assert the
  exact identities and reference files, as already specified.
- The Claude optional no-warning check does not establish complete
  descriptions. Keep its outcome separate from the size-cap acceptance.

The required commands are executable in form. Their actual success and
runtime were not tested. The verifier gives each item 600 seconds
(`shared/scripts/verify.py:616`); the combined suite commands still need to
fit that limit during implementation. There is no evidence here that they
currently exceed it.

## Wrong, stale, or overstated claims

I rechecked the numeric source anchors against the current tree. The main
anchors are still accurate: the OpenWiki installer test at 1409 and fresh
install test at 1475; generator 969-988, 1024, 1405, and 1517-1519; validator
619-625, 651-720, 8199-8221, and required-file list at 8783; the pandas/pyvis
tests at 3350/3607; template checklist at 54-67; workflow closeout at 185-207;
and the two verifier error strings at 2148/2174. Most references are not stale.

| plan location | claim | correction or qualification |
|---|---|---|
| A `:25` | A refresh deletes every ungenerated file under `.claude/`. | Too broad. Consumer state and marker-owned third-party bundles are already excluded. Say "unmarked project skill files outside the existing ownership exceptions". See `scripts/install_bootstrap.py:583`. |
| A `:69` | `Path.is_file()` establishes a regular marker suitable for ownership. | It also succeeds through a symlink to a regular file. Use a no-follow type check. |
| A `:78` | The listed modules are every importer of `runtime_ownership`. | It omits `scripts/generate_targets.py:16`. Add the generator and explain that its shared-copy and sidecar-set behavior remains appropriate. |
| A `:79` | `verify.py` sees only the unmarked mirror. | False as a general statement. It also binds canonical nested runtime paths (`shared/scripts/verify.py:1217`). Its root-adapter comparison sees the mirror. Keep the explanation limited to that comparison. |
| B `:28` | The existing checklist sets the log to COMPLETED and its boxes are ticked early. | The file contains checkbox instructions; it performs no mutation. Its recorded order is wrong. It does not currently set the small plan's frontmatter to complete. See `shared/templates/plan-small.md:60`. |
| B `:104` | Replacing the root budgets only tightens the validator. | False for Claude's existing line invariant. Retain it and add the byte bound. |
| B `:187` | Commit lines 46 and 57 are enough to repoint the moved content. | Line 47 also contains the conflicting checkpoint procedure. Line 57 is still a valid Verification Evidence Contract pointer to the core. Do not blindly change both pointers to the closeout file. |
| C `:63` | The unchanged library yields 14 cap errors. | It yields 24 non-exempt descriptions over 300 characters. Fourteen are in the kept set. |
| C `:155` | The aggregate command measures the proposed listing-length definition. | It measures description only, whereas Step 1 also counts `when_to_use`. They agree today only because this extra field is not contributing to the measured baseline. |
| big plan `:127` | Skipping unsafe mirrors keeps files outside the folder out of the AI-state remote. | Too broad. Canonical skill content is synced separately. Mirror safety does not establish remote-content privacy. |
| big plan `:199` and C `:172` | No after-run listing-budget warning proves the listing target. | Inconclusive without a working logging signal or direct entry/description evidence. |
| D `:39` | Only the main session has OpenWiki MCP tools. | Not established by this review. The current host says spawned agents inherit tools. Keep main-session ownership as the operational rule; avoid claiming universal host capability. No subagent was launched to test it. |

Also clarify big-plan `:100`: C has dependencies on A and B as well as the
spike. It edits A's modified runtime-ownership module and uses B's moved
closeout/policy files. The table order is correct; "depends only on the
pre-branch spike" is wrong if read as an implementation dependency statement.

The source baseline was independently reproduced with the validator's two
pure extraction functions, selected through Python's abstract syntax tree.
The validator module and its executable checks were not run:

- 55 shipped skills; 19,579 description characters.
- 35 kept original skills; 13,391 characters before shortening.
- 24 non-exempt originals exceed 300 characters; 14 of them are kept.
- Capping the kept descriptions at 300 and adding two 280-character
  placeholders gives 10,094 characters. The plan's "about 10,100" estimate
  is correct for that fixture, not a measured final merged library.
- Every byte baseline in the big plan's table matches the current files,
  including workflow 40,797, workspace 11,707, quality 10,287, tool-routing
  5,545, and generated roots 6,507/9,467.

## Codex observations

**Observed — session role.** I am `/root`, the primary Codex session for this
request. I am not a spawned reviewer. I did not spawn agents.

**Observed — startup catalog.** The supplied Available skills catalog has
**76 entries and 76 unique names**. The local repository group has 56
entries: the 55 shipped skills plus OpenWiki. The other entries are 10
personal Opik skills, four system skills, and six plugin skills.
`devils-advocate` appears **once**. No listed skill name appears twice.

**Observed — descriptions.** All 76 entries have descriptions. I see no
name-only entry or omitted-description warning in my startup catalog. The
`integration-gate-spike` description is present, including its invocation
contract and third-party CLI/SDK trigger text.

Two entries quoted exactly from that startup catalog:

> - devils-advocate: Challenge design decisions with structured critique. Questions architecture choices, technology selection, error handling strategy, testing adequacy, and configuration design. Use before committing to a major design, or when user says "challenge this design" or "devil's advocate". (file: r5/devils-advocate/SKILL.md)

> - code-style: Python implementation style reminders. Use when writing or reviewing code that must follow the repository code standards. (file: r5/code-style/SKILL.md)

Here `r5` is the supplied alias for this repository's `.agents/skills`.
The catalog does not present a second `../.claude/skills/devils-advocate/`
entry.

**Observed — current and generated configs differ.** The current tracked
`.codex/config.toml` has **zero** `[[skills.config]]` blocks. The existing
`dist/multi-agent/.codex/config.toml` has **55**, including:

```toml
[[skills.config]]
path = "../.claude/skills/devils-advocate/SKILL.md"
enabled = true
```

Therefore this session cannot test the claim that those generated entries
cause duplication. It does show that the working setup exposes the local
skills once, with descriptions. The exploration's claim that this checkout's
working config enables all 55 paths is stale for the tree observed here.

**Inferred from official documentation — discovery versus configuration.**
Official OpenAI documentation describes repository discovery through
`.agents/skills` and describes `[[skills.config]]` as selectors for enabling
or disabling skills. That supports the plan's expected discovery model. It
does not replace the proposed native test of this generated relative-path
configuration. The documentation also says separately discovered skills with
the same name can both appear; that does not prove these config entries
create a second discovered skill. [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills)

**Inferred limitation.** These observations apply to this main session and
its supplied catalog. They establish neither another client's budget nor a
spawned agent's catalog. No claim about either was tested here.

## Smallest acceptable revision

Keep A -> B -> C -> D. Keep the marker, the exact cuts and merges, the
targeted MEMORY rule, the numbered closeout move, and all required review
profiles. Add the missing safety cases and destination checks. Retain the
old root line limit. Remove competing closeout procedures. Make the spike
and negative checks produce evidence that can be distinguished from failure.
No implementation change was made by this review.
