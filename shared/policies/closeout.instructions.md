---
description: "Always-on: the CLOSEOUT procedure. Read and follow it step by step when entering CLOSEOUT: eight ordered steps, two hard rules, the completion-commit gate, closeout session-log rules, and stale-receipt recovery."
applicability: always
---

# Closeout

Read this file in full when you enter CLOSEOUT, and follow it step by step. The
workflow policy (`.claude/instructions/workflow.instructions.md`) says when
CLOSEOUT starts. This file is the only place that lists the order. The
orchestrator prompt, the `commit` skill, the `code-review` skill, README, and
the small-plan and session-log templates point here and do not restate it.

## CLOSEOUT procedure

Do these steps in this order. Each step's position exists because the step after
it reads what it produced. Skipping ahead produces receipts or reports that the
commit gate rejects, and the only recovery is to redo every step from the one
skipped.

1. **Documentation.** Update `README.md` and `docs/` for changed public behaviour (delegate to `documenter` unless the change is pure-internal; then record the reason and pass it to step 6). When the phase is the big plan's last entry in `phases:`, also run the standing final-phase audit below. *Why first:* findings and receipts bind the final code and docs.
2. **Final AI state.** Read `.claude/skills/learn/SKILL.md` and route each lesson from this phase: to a project skill (a `.claude/skills/<name>/` folder with an empty `.project-skill` file), to a `.claude/MEMORY.md` entry, or to none. Record each lesson as a `[LEARN:category]` entry in the session log, or write the exact no-lessons marker. Then set the small plan to `status: complete` with `closeout_session_log:` filled in and every step box ticked; tick the phase in the big plan; write the `.claude/MEMORY.md` entries; write the session log's `## Verification` section for optional items. Leave the required-items summary lines for step 4. *Why here:* the receipts bind the plan files, the session log, and the `.claude/` runtime files, including any skill you create now, so none of them may change after this step except the log's `## Verification` lines and `**Status:**` at step 4.
3. **First nested checkpoint.** `git -C .claude add -A && git -C .claude commit -m "checkpoint: <reason>"`. Use this form: the file-protection hook denies `bash .claude/hooks/scripts/state-sync.sh checkpoint` from an agent's Bash tool. *Why here:* `verify closeout` refuses to produce a passing receipt while the big plan's bytes are not retrievable from nested Git, and the push gate later re-derives the plan digest from the bytes Git holds.
4. **Stage, findings, phase receipt, closeout dry run.** In one Bash command that contains no `git commit`:
   - `git add` the intended outer files (never `git add -A`; never `openwiki/.run.json`) and inspect `git diff --cached`. *Why before findings:* the findings report records `dirty: true` when any tracked change is unstaged, and receipts bind `git write-tree` on the index.
   - Give every surviving MINOR an explicit `disposition` and non-empty `reason`, then `uv run python .claude/scripts/record_findings.py . --findings-json - --phase <current_phase> --profile <name>... --gate-result <PASS|WARN|FAIL> [--open-request "<text>" ...] --out .claude/quality_reports/findings-<current_phase>.json`, one `--profile` per reviewed profile, the reviewer's Gate Result as `--gate-result`, and one `--open-request` per open request. The recorder refuses `PASS` with an open request, and the commit gate accepts only `PASS` with no open request. When the findings text names a protected path, write the findings JSON with the Write tool to a scratch file and pass `--findings-json <file>`, because the guard denies heredoc text that names a protected path.
   - `uv run python .claude/scripts/verify.py phase --format json --persist`.
   - `uv run python .claude/scripts/verify.py closeout --format text` **without** `--persist`. It needs the findings report and the phase receipt to exist, runs the plan's required `## Verification` items, and prints one summary line per item. Paste those lines into the session log's `## Verification` section and set `**Status:** COMPLETED`. If any item is not `PASS`, return to IMPLEMENT.
5. **Second nested checkpoint.** Same command as step 3. *Why here:* the closeout receipt hashes the session log, so the log must be final and checkpointed before the receipt exists. Findings and receipt files are not provenance-bound, so having them in this checkpoint is expected.
6. **Closeout receipt.** `uv run python .claude/scripts/verify.py closeout --format json --persist` (add `--documentation-na "<reason>"` only when documentation is explicitly not applicable). A receipt made before staging is rejected at commit with `closeout receipt final tracked state is stale`. *Why after steps 2 to 5:* the receipt binds the staged tree, the phase receipt, the findings report, the session log, and the governing control-plane state, so everything it covers must be final first.
7. **Commit.** `git commit` in its **own** Bash command, after step 6 has finished. The `post-commit` hook checkpoints and publishes nested state; do not do that yourself. *Why alone:* the commit gate reads the Bash command's text before it runs and checks the receipts that exist at that moment.
8. **Push.** One normal non-force push: `GIT_TERMINAL_PROMPT=0 git push` when the branch has an upstream, otherwise `GIT_TERMINAL_PROMPT=0 git push -u origin HEAD` when `origin` exists. A missing remote or an authentication or network failure is a warning, not a failure: keep the local commit and do not retry interactively. *Why after the commit:* the push gate checks the pushed commit against the receipt and findings made before it (the receipt's `head_sha` must be that commit's direct parent), so nothing can be pushed until step 7 has made the commit. This push is separate from the nested `ai-state` sync that the `post-commit` hook runs. PR creation and merge stay the user's decision.

Two hard rules:

- **Never put `git commit` in the same Bash command as steps 4 or 6.** The commit gate hook inspects the *text* of every Bash command before it runs; a chain such as `record_findings ... && verify.py closeout --persist && git commit` is judged on the receipts that exist *before* the chain runs, is denied in full, and none of the steps execute.
- **Never checkpoint, publish, or push nested state between step 6 and step 7.** That changes what the receipts bind to and fails the commit with `closeout receipt governing control-plane provenance is stale`.

The reviewer does not persist findings; the coder does not create receipts; the orchestrator does steps 2 to 8 itself. An open CRITICAL or MAJOR finding blocks step 7; resolve it in the FIX LOOP (see the workflow policy) rather than deferring it to push or PR.

## Completion-commit gate

A normal completion commit needs all of these review conditions:

- a passing `verify phase`/`verify closeout` receipt;
- a matching findings report with `counts.critical == 0` and `counts.major == 0`;
- an explicit disposition and a non-empty reason on every surviving MINOR;
- the reviewer's recorded `gate_result` of `PASS` with no open request;
- every review profile the changed paths require.

The gate also checks that the small plan is `complete` with `closeout_session_log`, the log's status and `## [LEARN] Entries` section, the final-phase audit section, the plan frontmatter checks, and every optional item's outcome.

Severity contract: CRITICAL and MAJOR both block the phase-completion commit,
not only push or PR. A surviving MINOR needs a disposition and a reason, and is
otherwise advisory. Ponytail findings use the same severity gates; there is no
separate zero-Ponytail gate. When the conditional `ponytail` profile ran, its
metadata is recorded; when it did not run, metadata is optional and legacy
reports remain compatible.

An intermediate commit while the phase is still in progress is not blocked
merely because an unresolved MAJOR exists. An explicitly evidenced paused
checkpoint follows its separate non-final path (see
`.claude/instructions/plan-lifecycle.instructions.md`).

### Push and PR gates

A completed-phase commit may be pushed after the `post-commit` hook advances
`current_phase`, but only when its receipt and findings directly certify that
exact commit; later in-progress work cannot publish under that authority. PR
creation and final push closeout also require:

- every small plan complete, or fully evidenced as cancelled;
- at least one completed phase, and one commit per completed phase;
- bypass acknowledgement;
- required Ponytail review evidence where applicable;
- a valid historical receipt chain across every completed phase, each with
  `counts.critical == 0` and `counts.major == 0`.

The one exception is a plan's leading run of phases whose slug and closeout log
are dated before 2026-08-29 and that have no receipt file: closeout receipts did
not exist then, so that run is skipped, and the skip ends at the first phase
that does not qualify. The recorded `gate_result` and the required review
profiles apply at these push gates to schema-2 findings reports only.

## Closeout session log

A completed small plan's session log carries:

- `**Status:** COMPLETED`, set at step 4 once the dry run passes;
- `**Plan:** <small-plan path>`;
- `[LEARN:category]` entries, or the exact no-lessons marker `[LEARN] none - no new lessons this session`, under `## [LEARN] Entries`;
- a `## Verification` section: the summary lines `verify closeout --format text` printed for the required items, then every optional item's outcome, one line per item, in this grammar:

```
- optional <n>: PASS|FAIL|NOT RUN — <detail>
```

A `NOT RUN` line needs a non-empty `<detail>` explaining why. The commit gate
refuses an optional item with no outcome line (`G4 optional-verification-unaccounted`).

**Immutability:** A session log already bound by a completed phase's closeout
receipt must not be edited afterward; the receipt hashes its exact bytes, and
historical receipt-chain validation depends on that byte stability. Write a
correction to a sibling `<log-name>.errata.md` file next to the closed log
instead. An erratum discovered and written during a later active phase is
evidence of that later phase and may be bound by its own receipt; the earlier
phase's receipt is never edited or regenerated. An erratum written outside an
active plan may remain unbound until a later phase reviews or changes it.

## Standing final-phase audit

The final phase of every big plan must run a documentation, memory, and LEARN
audit: sweep the live-advice surfaces for claims that this plan or earlier work
invalidated (not only this plan's own changes), and correct or supersede each
one. The live-advice surfaces are root guidance (`CLAUDE.md`, `AGENTS.md`,
`README.md`), active plans, `docs/` except dated documents, the canonical
policy, skill, template, agent, and review-profile source, the state READMEs,
`.claude/MEMORY.md`, the project context file
(`.claude/instructions/project-context.instructions.md`), `.github/`, and
`openwiki/` (fix a generated page only through OpenWiki's tools). Archived
plans, dated design narratives, and closed session logs are dated records and
stay unchanged. Where a closed log's entry would actively mislead a reader,
write a sibling `<log-name>.errata.md`, whether or not a closeout receipt binds
that log; the closed log itself never changes. Record the audited surfaces and each one's outcome
under a `## Stale-claims surfaces checked` heading in that phase's closeout
session log, the same heading the conditional review uses.

This evidence is a deterministic gate, not only documented process. The
`verify.py` closeout check derives "final phase" from the big plan's own
`phases:` frontmatter list. It requires a non-empty
`## Stale-claims surfaces checked` section only when the phase being closed out
is that list's last entry, and never on an earlier phase. It checks that the
section exists and is not empty, not the correctness of its judgement, like the
`## [LEARN] Entries` requirement next to it.

## Recovering from a stale receipt

Use this only before step 7 succeeds. After the completion commit, never
re-persist that phase's receipts. A new passing receipt replaces the old one
for the same phase, so repeating a step is safe. Never edit a receipt by hand.
When only receipt state went stale and no code changed, these recoveries are
the exception to the FIX LOOP rule in the workflow policy.

**`closeout receipt final tracked state is stale`**

- What changed: the receipt records the Git tree of the staged index (`git write-tree`) as it stood at step 6. The commit gate computes it again and refuses the commit when the two differ. Any change to the index after step 6 (staging, unstaging, or restaging a file) does this, even for a documentation file. An unstaged working-tree edit does not change the index, so it does not stale this receipt; it does stale the findings report (see the third entry). A receipt made before staging finished does the same. The push gate gives the same error when the pushed commit's tree differs from the receipt's.
- What to repeat: stage the intended files again as in step 4 (`git add` them and inspect `git diff --cached`).
  - If the late change is documentation only (`README.md`, `docs/`, or another `.md` or `.rst` file outside `shared/` and the control-plane paths), the phase receipt stays valid, because its content hash skips ordinary documentation. The findings report does not: its `content_hash` covers every tracked change from the merge base, documentation and unstaged edits included. Re-record the findings with the step 4 recorder command, repeat step 5 only if the session log changed, then repeat step 6. Do not rerun the closeout dry run: the gate never compares the log's summary lines, and step 6 runs every required item again.
  - If it touched anything else (code, tests, scripts, `shared/`, configuration), the findings report and the phase receipt are stale too. Return to the FIX LOOP so verification and review restart, then repeat steps 4, 5, and 6.

**`closeout receipt governing control-plane provenance is stale`**

- What changed: the receipt records the governing state as it stood at step 6: the `.claude/` runtime files (hooks, scripts, instructions, skills, agents, templates), the root adapters, the big plan, every small plan the big plan lists in `phases:` (a future phase's plan included), and the nested Git state of those files. It does not cover `MEMORY.md`, `explorations/`, `session_logs/`, `quality_reports/`, `settings.local.json`, or `instructions/project-context.instructions.md`. The gate computes the state again at commit, and any difference stales the receipt. A nested commit that changes only those uncovered files does not, because the nested HEAD is not compared. Breaking the second hard rule can cause it, and so can a plan, skill, runtime file, or root adapter changed after the receipt. Revise a future phase's plan before step 3 or after the commit, not between them. Find the change with `git -C .claude status` and `git -C .claude log -3 --stat`.
- What to repeat: make the change final first (go back to step 2 for a plan or lesson file, or to the FIX LOOP for a runtime change), then repeat steps 3, 4, 5, and 6 in order. The phase receipt records the same state, and `verify closeout` fails while the phase receipt differs from the current state, so step 4 must run again.

**`findings report content_hash is stale`**

- What changed: the findings report records a hash of the tracked changes from the merge base (`git diff <merge base>`, working tree included) as they stood when step 4 recorded it. The commit gate computes it again. Any tracked change after that, staged or not, documentation or code, makes the two differ.
- What to repeat: inspect `git diff` and `git diff --cached`. If the change was not intended, undo it (for example `git restore <path>` for an unstaged edit); nothing needs redoing. If it was intended, follow the first entry's documentation-only or code branch.
