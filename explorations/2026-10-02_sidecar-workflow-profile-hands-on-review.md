# Hands-on review: sidecar workflow profile

**Date:** 2026-10-02
**Author:** agent session (Claude Opus 5.5), read-only review requested by the maintainer
**Status:** OPEN. Nothing below is fixed yet.
**Code state:** branch `dev` at `a2c68b3` (merge of PR #42, `sidecar-workflow-profile_implementation`).
**Plan under review:** `.claude/plans/sidecar-workflow-profile.md` and its phases
`2026-09-27_phase-{A,B,C}-workflow-profile-*.md`.

## Summary

The install engine works. Install, rerun, update, profile switching, backup,
uninstall, `--purge-state`, and reinstall all behaved as documented. `git status`
and the Git index never changed, and team files were never touched. All 699
sidecar tests pass. Claude Code loads every shipped agent, skill, and rule from
the Git-ignored files.

Two problems stop the workflow profile from working in real use:

1. Claude Code refuses agent writes under `.claude/`, so the agents cannot save
   plans, session logs, or `MEMORY.md` lessons in `.claude/ai-bootstrap/`
   without a manual approval for each write.
2. The installer does not recognize older full installs. On such a repository,
   `--mode sidecar` mixes the sidecar into the full install.

The rest are minor.

## Method

- Scratch copies only. Each copy was made with `git clone` from
  `/home/ghisso/work/git_projects/<repo>`. Its `origin` remote was removed so
  nothing could push back. Untracked bootstrap files (`.claude/`, `CLAUDE.md`,
  `AGENTS.md`, `.codex/`, `.github/`, and so on) were copied with `tar`, leaving
  out `.git`, `.venv`, data, and cache folders. No real repository was changed.
- This repository's commit-gate hook blocks `git commit` even in scratch
  repositories. So "team-tracked" files were made by staging them with
  `git add`, which Git treats as tracked.
- After every step: `git status --porcelain --untracked-files=all` and a hash
  of `git ls-files -s` were compared with the snapshot taken before install.
- Client check: Claude Code 2.1.226 in print mode (`claude -p`), started inside
  the copy.
- Tests: `uv run pytest tests/test_validate_targets.py tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_uninstall.py tests/test_install_bootstrap.py tests/test_sidecar_workflow_scenario.py -q`
  gave `699 passed in 147.98s`.
- A reviewer subagent read the diff `094f1f0..a2c68b3` for profiles `code`,
  `security`, and `tests`. Its findings are merged into the list below after
  they were checked against the code.

## Results by scenario

| Copy | Situation | Result |
| --- | --- | --- |
| `Pycaret-Price-Prediction` | No bootstrap, no `.claude/` | Every step passed (details below). |
| `clearml_tutorials` | Staged team files: `.claude/settings.json`, skill `humanize`, agent `.claude/agents/planner.md`, rule `team-style.md`, review profile `security.md`, Copilot agent `.github/agents/coder.agent.md`, `CLAUDE.md`. One untracked stray `.claude/templates/plan-big.md`. | Passed. All 8 team and stray files stayed byte-identical. Status and index were unchanged. The dry-run report matched the real run. |
| `schema-bootstrap-llm-wiki` | Current full install (nested `.claude/.git` and `bootstrap-ownership.env`) | Passed. Install, dry run, and `--uninstall` refused, and nothing was written. |
| `img-classification` | Older full install (HF-sync era, no nested repo) | **Failed.** See finding 2. |

### Scenario 1: plain repository (Pycaret copy)

| Step | Output | Check |
| --- | --- | --- |
| Install `--profile workflow` | `installed 72, updated 0, removed 0, adopted 0, unchanged 0, preserved 0, seeded 0` | Manifest `schema_version: 2`, `profile: workflow`, 71 unit records. The exclude block is 74 lines including the markers. State folder seeded. |
| Rerun with no `--profile` | `unchanged 71` | Profile kept. |
| Edit `MEMORY.md`, add `plans/my-plan.md`, rerun | `unchanged 71` | Both state edits untouched. |
| `--profile skills` | `installed 2, updated 0, removed 63, adopted 0, unchanged 8, preserved 0, seeded 0` | Only the 4 skills and the bridge rule remain. State folder kept and still ignored. Manifest profile is `skills`. |
| Rerun with no `--profile` | `unchanged 10` | Profile `skills` kept. |
| `--profile workflow` | All units back | `MEMORY.md` still holds the edit. |
| `--backup-state` (dry run, then real) | `would back up ...`, then `backed up ... -> .git/ai-bootstrap-sidecar-preserved/state--20261002T021303Z` | The copy holds `my-plan.md`. |
| Delete the state folder by hand (stands in for `git clean -x`), rerun | `installed 1, ... unchanged 71` | Reseeded. The backup in `.git/` survived. |
| Two `--backup-state` runs in the same second | `state--20261002T021315Z` and `state--20261002T021315Z-2` | No name clash. |
| `--uninstall` | `RETAINED .claude/ai-bootstrap: kept .claude/ai-bootstrap and its exclude line; pass --purge-state to remove it` | The exclude block holds only `/.claude/ai-bootstrap`. |
| `--uninstall` again | Same `RETAINED` line | No-op. |
| `--uninstall --purge-state` | `PRESERVED .claude/ai-bootstrap -> <git dir>/ai-bootstrap-sidecar-preserved/state--20261002T021316Z` | No `ai-bootstrap` line is left in the exclude file. |
| Reinstall | `installed 72` | Reseeded. |

`git status` and the index were unchanged after every step.

### Scenario 2: team-tracked `.claude/` (clearml copy)

The install printed `installed 66` and these reports:

```text
SKIPPED .claude/agents/planner.md: the repository tracks `.claude/agents/planner.md`; the sidecar skips the agent `planner` at every root
SKIPPED .claude/review-profiles/security.md: the repository tracks `.claude/review-profiles/security.md`; the sidecar skips the review profile `security` at every root
SKIPPED .claude/skills/humanize: the repository tracks `.claude/skills/humanize/SKILL.md`; the sidecar skips `humanize` at every root
SKIPPED .claude/templates/plan-big.md: the sidecar will not replace `.claude/templates/plan-big.md` and skips the template `plan-big` at every root; rename or remove `.claude/templates/plan-big.md` only if you do not need it
SKIPPED .github/agents/coder.agent.md: the repository has `.github/agents/coder.agent.md`; the sidecar skips the agent `coder` at every root
```

### Scenario 3: current full install (wiki copy)

```text
Refusing --mode sidecar: <T> already has full-install evidence (nested AI-state repository <T>/.claude/.git; full-install manifest <T>/.claude/bootstrap-ownership.env). This consumer is already managed by a full install; refresh it with --mode full, or no --mode at all, instead.
```

`--uninstall` refused the same way. `--backup-state` printed
`no state folder found; nothing to back up`.

### Scenario 4: Claude Code loads the ignored files

`claude -p` in the Pycaret copy listed:

- agents `coder`, `documenter`, `orchestrator`, `planner`, `reviewer`;
- all 24 shipped skills;
- the rules `.claude/rules/ai-bootstrap-workflow.md` (`# Personal Workflow Rule`),
  `ai-bootstrap-tool-routing.md` (`# Tool Routing`), and
  `ai-bootstrap-reporting.md` (`# Plain-Language Reporting`).

`~/.claude/agents` and `~/.claude/rules` do not exist, so the agents and rules
came from the sidecar.

### Scenario 5: a real task through the workflow

Claude Code (`--model sonnet --permission-mode acceptEdits`, with `Write` and
`Edit` allowed, and `uv`, `python`, and installs forbidden) was asked to add
type hints to `src/config.py` and `src/hpo.py` and to follow the workflow
rules. It changed `src/hpo.py` correctly, and `git status` showed only that
file. It could not save its session log:

```text
I can't write to `.claude/ai-bootstrap/session_logs/` — the permission request to create/edit that path was denied.
```

The task was small, so no plan was written. Whether it delegated to the
`reviewer` agent was not checked.

## Findings

### 1. MAJOR: Claude Code refuses agent writes into `.claude/ai-bootstrap/`

**Evidence.** Probes in the Pycaret copy with `--permission-mode acceptEdits`:

| Write target | Extra setting | Result |
| --- | --- | --- |
| `.claude/ai-bootstrap/session_logs/probe-a.md` | `--allowedTools Write` | `Claude requested permissions to edit the file which is a sensitive file.` |
| `.claude/ai-bootstrap/session_logs/probe-b.md` | `--settings` with allow rules `Write(.claude/ai-bootstrap/**)` and `Edit(.claude/ai-bootstrap/**)` | Same "sensitive file" refusal. Claude Code also warned that only `Edit(path)` rules apply to file writes; the `Edit` rule was present and did not help. |
| `<T>/.claude/ai-bootstrap/plans/probe-c.md` (absolute path) | none | `Claude requested permissions to edit <T>/.claude/ai-bootstrap/plans/probe-c.md which is a sensitive file.` |
| `<T>/notes-probe.md` | none | Written. |
| `<T>/.ai-bootstrap-probe/plans/probe.md` (a hidden folder at the root) | none | Written. |

The user-level `~/.claude/settings.json` has no hooks and no deny rules, so the
refusal comes from Claude Code's built-in protection of `.claude/`.

**Effect.** Every plan, session log, quality report, and `MEMORY.md` write
needs a manual approval in an interactive session, and fails in print mode or
background runs. That is most of what the state folder is for.

**Cause.** Big plan Decision 2 put the state at `.claude/ai-bootstrap/`
(`SIDECAR_STATE_ROOT` at `scripts/runtime_ownership.py:205`). Phase A's
`native-run` evidence (`docs/sidecar-provider-contract.md`) only proved that the
ignored files load. No step tested that an agent can write to the state folder.

**Fix options.**

- **A (recommended): move the state root out of `.claude/`**, for example to
  `.ai-bootstrap/` at the repository root. The probe shows writes there go
  through. It still needs only one exclude line. Cost: one more hidden folder
  at the root, every rendered path changes (agent prompts, rules, templates,
  README), and existing installs need the old folder moved, or a one-time
  "found old state folder" message. Add a `native-run` write probe to the
  provider contract.
- B: keep the location and document the approval prompt. Weak, because headless
  and background runs still fail.
- C: an allow rule in a settings file. Excluded by Decision 4, and the probe
  shows an allow rule does not lift the protection anyway.

**Open questions.**

- In an interactive session, does the approval prompt offer a session-wide
  "allow" for `.claude/` edits? Not tested.
- How does the full install's own state under `.claude/` get past this check?
  Not investigated. The answer may matter for option B.

### 2. MAJOR: older full installs are not detected, and the sidecar mixes into them

**Evidence.** The real `img-classification` has neither `.claude/.git` nor
`.claude/bootstrap-ownership.env`. Its `.claude/` (with `settings.json`, hooks,
scripts, plans, and `MEMORY.md`) is ignored through `.gitignore`. It tracks
`.devcontainer/hf-ai-sync.py` and the other devcontainer files.

On a fresh copy, the plain installer refuses and points toward the sidecar:

```text
Refusing a plain install with no --mode: <T> already tracks bootstrap-owned paths (.devcontainer/Dockerfile, .devcontainer/devcontainer.json, .devcontainer/hf-ai-sync.py, .devcontainer/post-start.sh) and carries no bootstrap or sidecar evidence. Pass --mode sidecar for a private per-clone overlay that never changes tracked files, or --mode full for today's takeover.
```

Following that advice, `--mode sidecar --profile workflow` exits 0. It skips 6
agents because the full install already has `.github/agents/*.agent.md` and
`.codex/agents/*.toml`, then records 12 units:

- the `ponytail` and `ponytail-review` skills, at both roots;
- `.claude/agents/documenter.md`;
- the three `ai-bootstrap-*` rules;
- `.claude/review-profiles/ponytail.md`;
- `.claude/templates/plan-big.md` and `plan-small.md`;
- the Copilot instructions file;
- plus the state folder.

No full-install byte changed, but:

- the repository now has two memory and plan stores: `.claude/MEMORY.md` with
  `.claude/plans/`, and `.claude/ai-bootstrap/`;
- the relaxed rules ("no step blocks a commit") load next to the full install's
  strict guidance;
- afterwards, the plain installer picks **sidecar** mode for this repository
  (its dry run printed `would keep ...` sidecar lines), so it will never be
  refreshed as a full install again.

The current full install (`schema-bootstrap-llm-wiki`) is refused correctly.

**Cause.** `_full_install_evidence` (`scripts/install_bootstrap.py:1315`)
counts only `.claude/.git` and `.claude/bootstrap-ownership.env`. This came
from the first sidecar plan, but the workflow profile makes the mix much worse.

**Fix options.**

- Add older-install evidence under the same `claude_tracked` guard (so a
  team-tracked `.claude/` still counts as team config). Candidates: an
  untracked `.claude/hooks/scripts/` or `.claude/scripts/verify.py`, or a
  tracked `.devcontainer/hf-ai-sync.py` or `.devcontainer/state-sync.sh` next
  to an untracked `.claude/`.
- Change the plain installer's refusal message: do not suggest `--mode sidecar`
  when tracked bootstrap devcontainer files sit next to an untracked `.claude/`.
- Maintainer action, independent of the code: refresh `img-classification`
  with `--mode full` so it gains the current markers.

### 3. MINOR: a dry run also prints real-run wording

`_install_sidecar_dry_run` calls `_describe_dry_run_actions` and then
`_print_report` (`scripts/sidecar_overlay.py:3826-3827`). After the
`would remove <unit>` lines and the summary, it prints `removed <unit>` for
every unit, and also `deleted`, `seeded`, and `PRESERVED` lines, as if they had
happened. Nothing is deleted: a file-tree hash before and after the dry run
matched. This came from the first sidecar plan (`8d153c3`). Fix: print only the
summary and the `SKIPPED`/`RETAINED` reports in a dry run, or give
`_print_report` a dry-run flag.

### 4. MINOR: `--backup-state` takes no run lock and has no filesystem-error handling

`backup_sidecar_state` (`scripts/sidecar_overlay.py:4709`) never calls
`_acquire_run_lock`, which install (line 4208) and uninstall (line 4577) both
take. `shutil.copytree` has no `try/except`, and `_run_backup_state` in
`scripts/install_bootstrap.py` catches only `CalledProcessError`. If an
`--uninstall --purge-state` runs in another terminal at the same time, or a
disk error happens, the result is a raw Python traceback and possibly a partial
`state--<timestamp>` copy. That breaks the README's promise of
`ABORT: filesystem error at <path>: <reason>`. The race needs two commands
running at once, so the risk is low.

### 5. MINOR: the Copilot instructions file names agents Copilot does not get

`shared/sidecar/workflow/instructions.md:15` says "ask the planner agent", and
line 23 says "ask the reviewer agent". No `.github/agents` unit ships (Decision
7, Phase A evidence), so a Copilot user has no such agent. Fix: tell Copilot to
write the plan itself using `.claude/templates/plan-*.md`, and to review the
diff itself against `.claude/review-profiles/`.

### 6. MINOR (design effect): a team agent for any client removes the Claude Code agent

In scenario 2, the team's Copilot agent `.github/agents/coder.agent.md` made the
sidecar skip `coder` "at every root". Claude Code then had no `coder` agent, and
the `orchestrator` workflow prompt delegates coding to `coder`. This follows
Decision 9 (team wins by name across every read folder). Options: accept it and
document it, or have the orchestrator prompt handle a missing specialist by
doing that step itself.

### 7. MINOR (test gap): no automated test for team precedence on review profiles and templates

`tests/test_sidecar_workflow_scenario.py` covers team precedence for rules and
agents, but not for `.claude/review-profiles/<name>.md` or `.claude/templates/<name>`.
Scenario 2 shows both work by hand.

## Not tested

- A real `git clean -x`. This repository's hook blocks `git clean` even in
  scratch, so deleting the state folder by hand stood in for it.
- The interactive approval prompt for `.claude/` writes (finding 1).
- Copilot in VS Code, Codex, and Antigravity with the workflow profile.
- Whether the `planner` and `reviewer` agents write their plan and quality
  report files when delegated to. Blocked by finding 1 in any case.

## Suggested next step

Fix findings 1 and 2 in one big plan, with findings 3 to 5 as one small
follow-up phase. It touches `scripts/`, the generator, and multiple files, so
it is control-plane/high-risk: full plan plus the `code`, `architecture`,
`security`, `tests`, and `ponytail` review profiles. Start finding 1 with a
`native-run` write probe for the chosen state root before any code changes.
