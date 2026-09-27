# Session: Workflow profile Phase A — evidence and relaxed content

**Date:** 2026-09-27
**Plan:** `.claude/plans/2026-09-27_phase-A-workflow-profile-evidence-and-content.md`
**Status:** IN PROGRESS

## Goal

Record per client whether Git-ignored agent files, several rules files,
and an instructions file are discovered inside a repository whose
`.claude/` is team-tracked; freeze the workflow profile's write roots,
read roots, and client coverage; then, past the decision gate, author the
relaxed instruction set, the agent supplements, the skill denylist, and
the state seeds under `shared/sidecar/workflow/`.

## Work Log

- PRE-FLIGHT on `dev` at `094f1f0` (PR #41 merged): outer and nested
  trees clean, `check_runtime.py` PASS, plans valid, `verify.py fast`
  NOT_APPLICABLE (no changed Python path).
- BRANCH: `sidecar-workflow-profile_implementation` created from `dev`;
  the branch hook activated Phase A.
- Clients on this host: Claude Code 2.1.226 (CLI), Codex CLI 0.147.0,
  VS Code 1.139.1 (Copilot runs need the editor).
- Steps 1 and 2 (documented starting point, fixture recipe) delegated to
  `documenter`, appending `## Workflow profile evidence` to
  `docs/sidecar-provider-contract.md`.
- Step 3, fixture built by a scratch script exactly as the plan's step 2
  describes: seven tracked files (`.claude/settings.json`, a team skill,
  `.claude/agents/team-agent.md`, `.claude/rules/team.md`,
  `.github/instructions/team.instructions.md`, code, README) and six
  untracked probe files hidden by anchored `info/exclude` lines inside the
  sidecar's own marker block; `git status --porcelain --untracked-files=all`
  empty after placement.
- Step 3, Claude Code 2.1.226, 2026-09-27, `claude -p` from the fixture
  root, `--model claude-haiku-4-5-20251001` because 2.1.226 refuses the
  default model (`API Error: 400 Claude Code 2.1.226 does not support this
  model; version 2.1.251 or newer is required`):
  - the `system`/`init` event lists `agents:` `probe-agent` and
    `team-agent` beside the built-in ones, so the ignored
    `.claude/agents/probe-agent.md` is discovered next to the team's;
  - the plain prompt answered `2+2 is 4. WORKFLOW-RULE-A-OK
    WORKFLOW-RULE-B-OK TEAM-RULE-OK`: both ignored rule files without
    `paths` loaded, and the team rule still loaded;
  - delegation returned `probe-agent: WORKFLOW-PROBE-AGENT-OK ...` and
    `team-agent: TEAM-AGENT-OK`: both agents run;
  - `WORKFLOW-INSTRUCTIONS-OK` and `TEAM-INSTRUCTIONS-OK` absent, as
    expected: Claude Code does not read `.github/instructions/`.
  Result: `native-run` for Claude Code agents and rules. The gate passes.
- Step 3, Codex CLI 0.147.0, 2026-09-27, `codex exec --skip-git-repo-check
  --sandbox read-only` from the fixture root, with and without
  `-c features.multi_agent_v2=true`: the agent listing answered `NONE`, so
  `.codex/agents/probe-agent.toml` is not discovered without a
  `.codex/config.toml` entry; no rule or instructions token appeared, as
  expected, since Codex reads `AGENTS.md` only. Result: Codex gets skills
  and state only (Decision 7).
- Step 3, Copilot in VS Code: needs the editor; the operator runs the
  fixture in a Local agent session and an Agent Host session and reports
  the tokens seen. Antigravity: not installed on this host; unverified.
- Content steps 5 to 8 delegated to a second `documenter` after the gate.
- Steps 1 and 2 done by `documenter`: `## Workflow profile evidence`
  appended to `docs/sidecar-provider-contract.md` (documented starting
  point, questions per client, fixture recipe, operator checklist, empty
  frozen matrix and coverage table). Two vendor claims could not be
  confirmed online: Antigravity's agents page returned 404 (recorded at
  the `source` tier from this repository's generator), and Codex's docs do
  not say whether `.codex/config.toml` gates agent discovery (settled by
  the native run above). The recipe's rule and instructions token names
  were aligned with the tokens the runs used (`-OK`).
- Step 4, partial: the matrix rows for Claude Code and Codex and the
  coverage table are filled; `.codex/agents` is dropped; `.github/agents`
  and the workflow instructions file wait for the Copilot run; the read
  roots for collision checks are frozen.
- Steps 5 to 8 done by the second `documenter`: 15 files under
  `shared/sidecar/workflow/` (three rules, the Copilot body, `skills.txt`,
  the `MEMORY.md` seed, four state READMEs) and five
  `shared/agents/<id>/workflow-supplement.md`; a grep for every forbidden
  token and for `hook`, `receipt`, `checkpoint`, and `findings json` over
  all 15 files found nothing, and every `.claude/` path named is under
  `.claude/ai-bootstrap/` or `.claude/templates/`. Denylist: 12 skills
  (`commit`, `context-status`, `knowledge-refresh`,
  `safe-consumer-bootstrap-refresh`, `setup-project`, `deep-audit`,
  `code-review`, `run-tests`, `code-style`, `onboard`,
  `plan-decomposition`, `refactor`), each with its reason; 29 of the 40
  public skills are eligible (the documenter's report said 43; recounted
  by script). Follow-up sent: the planner supplement must also replace the
  canonical prompt's mandatory `plan-decomposition` rule with the
  templates.
- Note for Phase B: `code-style`, `refactor`, and `run-tests` are denied
  only because their text names `verify.py`; a profile text replacement
  could rescue them. Decide there, not here.
- Required items on the current tree: `validate_targets.py` PASS with the
  new files present, `verify.py fast` NOT_APPLICABLE (no Python changed),
  plans valid.
- Planner supplement corrected by the same `documenter`: it now replaces
  the canonical prompt's mandatory `plan-decomposition` rule with the two
  templates (38 lines, grep clean).
- Step 3, Copilot: the user could not run Copilot today and asked to skip
  it. Recorded as `unverified` in every Copilot row. Step 4 final: Copilot
  gets no agent file from the workflow profile; the workflow instructions
  file ships on the 2026-09-25 `native-run` for the same unit kind (the
  skills-profile bridge); `.github/agents` stays a read root only.
  Antigravity unverified (no client). Frozen coverage: Claude Code gets
  agents, rules, review profiles, templates, skills, and state; Copilot
  gets the instructions file and skills; Codex gets skills and state.
- REVIEW round 1 (`reviewer`, `documentation`, `architecture`,
  `security`): FAIL. Two CRITICAL: the agent supplements left the
  canonical `## Retrieval` and `## Communication Style` sections in place,
  which name Context Mode, Semble, and `.claude/instructions/` paths the
  profile does not ship; and the orchestrator's `## Quality Gates` and the
  reviewer's Review Flow step 5 were not replaced, so the merged prompts
  would still say a receipt blocks a commit. Two MAJOR: `documentation`
  and `learn` were eligible although their text names OpenWiki and
  `.claude/instructions/`; the state READMEs and `workflow.md` did not
  disclose the `git clean -x` risk and `--backup-state`. One MINOR: the
  planner supplement's opening sentence mischaracterized the section it
  replaces. The evidence section, the tables, the tier labels, and every
  `.claude/` path were found consistent. All five sent back to the same
  `documenter` in the FIX LOOP.
- FIX LOOP: the `documenter` redirected `## Retrieval` and
  `## Communication Style` in every supplement to the profile's own rule
  files, replaced the orchestrator's `## Quality Gates` and the reviewer's
  Review Flow step 5 with no-gate text, denied `documentation` and
  `learn`, added the `git clean -x` and `--backup-state` sentence to the
  four state READMEs and `workflow.md`, and reworded the planner
  supplement's opening sentence. Its grep over all 15 files: no matches.
- Orchestrator check with a stricter token list that adds
  `.claude/instructions/` (the reasoning the reviewer applied to
  `documentation` and `learn`): the 15 authored files are clean and name
  only paths under `.claude/ai-bootstrap/`, `.claude/rules/`, and
  `.claude/templates/`; three more eligible skills name
  `.claude/instructions/` (`deploy-service`, `bentoml-service`,
  `create-feature`) and were denied for the same reason, leaving 24
  eligible skills. Phase B may rescue any denied skill whose only problem
  is a path or verifier mention through a profile text replacement.
- REVIEW round 2 (fresh `reviewer`, same three profiles): the five
  round-1 findings confirmed fixed; FAIL again with six CRITICAL of one
  kind, references the supplements left in place to denied skills
  (`code-style`, `create-feature`, `bentoml-service`, `documentation`)
  and to `.claude/instructions/` files (the reporting policy and the
  routing table in the orchestrator, planner, and reviewer prompts); one
  MAJOR: the evidence section had no explicit gate-result statement; one
  MINOR: the coder's control-plane route bullet.
- Decision (orchestrator, material-impact check): a supplement that
  replaces a closed list of canonical sections cannot be made complete,
  because the canonical prompts name full-install files and skills in
  many places. Big plan Decision 6 amended: each agent gets a complete,
  self-contained `workflow-prompt.md`, never merged with the canonical
  prompt, naming only the profile's rules, templates, state paths, and
  the 24 shipped skills; the validator will reject any other reference.
  Small plan step 7 updated to match. The MAJOR was fixed by adding
  `### Decision gate result, 2026-09-27` to the evidence section. The
  MINOR disappears with the rewrite. Rewrite delegated to the same
  `documenter`.

## [LEARN] Entries

(pending)

## Verification

(pending)

## Documentation

(pending)

## Open Questions / Next Steps

(pending)
