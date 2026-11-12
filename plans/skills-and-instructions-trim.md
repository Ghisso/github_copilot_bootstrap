---
name: skills-and-instructions-trim
type: big-plan
# status must occur exactly once: planning | in-progress | complete | cancelled
status: planning
originating_branch: dev
implementation_branch: skills-and-instructions-trim_implementation
started_at:
phases:
  - 2026-11-12_phase-A-project-owned-skills
  - 2026-11-12_phase-B-closeout-and-wording-defects
  - 2026-11-12_phase-C-skill-removals-and-merges
  - 2026-11-12_phase-D-skill-description-cap
  - 2026-11-12_phase-E-workflow-split
  - 2026-11-12_phase-F-guidance-trims
  - 2026-11-12_phase-G-knowledge-refresh
current_phase:
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Big Plan: skills-and-instructions-trim

## Context

The user said the shipped instructions and skills "are too much now and just bloat the context". The decided review is `.claude/explorations/2026-11-12_skills-and-instructions-review.md`. Its sections 4 and 5 are the verdicts. Section 6 lists cuts that must not come back. Section 7 lists defects. Section 8 records the user's decisions.

Approved by the user on 2026-11-12:
- skills go from 55 to 37 as section 4 says;
- instructions change as section 5 says, including a CLOSEOUT file with a validator pin, a targeted MEMORY search, no loosening of the root-guidance validator, and a one-line Antigravity pointer in `AGENTS.md`;
- defects 1 to 6 are fixed;
- a project-owned skills mechanism comes first;
- a short Codex evidence check runs before any step relies on Codex behavior.

### Open decision (confirm at approval)

The user rejected `disable-model-invocation: true` ("manual-only"). The proposal:
- every kept skill stays visible to the model;
- every description is at most 300 characters, with key trigger words first;
- the hash-pinned `ponytail` and `ponytail-review` are exempt;
- `scripts/validate_targets.py` gets a check that enforces the cap.

Measured result: 37 skills and about 10,100 description characters instead of 19,579. 14 descriptions need new text. Phase D is written for this option.

If the user rejects it, there are two alternatives:
- rewrite the 14 descriptions without a cap, which leaves nothing to stop them growing again;
- use a looser cap, such as 400 characters (a total of about 11,000).

### Measured baseline (2026-11-12)

| Surface | Bytes or characters |
|---|---|
| `dist/multi-agent/CLAUDE.md` | 6,507 |
| `dist/multi-agent/AGENTS.md` | 9,467 (Antigravity contract 2,786) |
| `dist/multi-agent/.github/copilot-instructions.md` | 1,393 |
| `shared/policies/workflow.instructions.md` | 40,797 |
| Skill descriptions (validator extractor) | 55 skills, 19,579; the 35 kept skills 13,391 |
| `workspace` / `quality-and-testing` / `tool-routing` policies | 11,707 / 10,287 / 5,545 |
| Orchestrator / documenter prompts | 16,178 / 7,626 |

## Goals

- Protect skills a consumer project writes itself from bootstrap refreshes, for every client (Phase A).
- Fix defects 2 to 6 from section 7 before the later closeouts use them (Phase B).
- Reach 37 model-visible skills with short, trigger-first descriptions, and enforce the cap (Phases C and D).
- Split the workflow policy, so CLOSEOUT is read only at the closeout step, and trim the always-read guidance (Phases E and F).
- Refresh the derived wiki and audit live advice for stale claims (Phase G).

## Non-Goals and Constraints (optional)

- Out of scope:
  - the personal `opik*` skills;
  - splitting `.claude/MEMORY.md` (declined on 2026-10-20; only the reading rule changes);
  - recovering RAG's deleted skills;
  - the sidecar's own MEMORY rule.
- Do not re-propose section 6's rejected cuts. Stack-specific content (Hydra, BentoML, Haystack, Gradio) stays.
- Never edit `shared/skills/ponytail/SKILL.md` or `shared/skills/ponytail-review/SKILL.md`.
- Never loosen the root-guidance validator. Phase F only tightens it.
- Regenerate `dist/` only with `uv run python scripts/generate_targets.py --all`. Refresh this repository with `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Only one agent runs generation or the validators at a time.
- Every phase is control-plane/high-risk: a full small plan and the `code`, `architecture`, `security`, `tests`, and `ponytail` review profiles, plus `documentation` when docs change.
- A repeated procedural mistake is fixed by a numbered procedure in canonical instructions, not a memory note.

## Design Overview

### Project-owned skills (Phase A)

**Mechanism.** No client reads skills from a custom repository folder, so there is no new folder.

- A skill folder `.claude/skills/<name>/` that contains a file named `.project-skill` belongs to the project.
- `scripts/runtime_ownership.py` gains `PROJECT_SKILL_MARKER` and `is_project_skill_dir()`, beside the OpenWiki marker (`THIRD_PARTY_SKILL_MARKER`).
- `scripts/install_bootstrap.py` changes in three places:
  - `owned_files()` skips a marked folder, so a refresh neither deletes nor overwrites it;
  - a pre-flight check refuses the install, before any write, when a marked folder's name or its frontmatter `name:` equals a skill the bootstrap ships;
  - after copying, it mirrors each marked folder, without the marker, to `.agents/skills/<name>/`. This runs before `populate_bootstrap_root`, so the `bootstrap-root/.agents` copy, `validate_agents_takeover`, and `verify.py`'s root fingerprint all see the same tree.
- The mirror is unmarked, so it is ordinary generated content: the next refresh prunes it and writes it again.
- A folder that holds a symlink or a non-regular file is not mirrored. The installer warns instead. This keeps files outside the folder out of `.agents/` and out of the ai-state remote.

**Why not a state folder.** A `CONSUMER_STATE_PATHS` entry (for example `project-skills/`) would survive refreshes, but no client lists skills from it.

| Client | Reads repository skills from | Sees a marked project skill | Evidence |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` (start folder up to the repository root; nested folders on demand; `--add-dir`) | Yes, directly | code.claude.com/docs/en/skills, read 2026-11-12 |
| Copilot in VS Code | `.github/skills/`, `.claude/skills/`, `.agents/skills/`; one entry per name | Yes, directly; it keeps one entry when the mirror shares the name | `docs/sidecar-provider-contract.md:524-525` (native run, 2026-09-25) |
| Codex | `.agents/skills/` from the working folder up to the repository root, and `$HOME/.agents/skills` | Yes, through the mirror, as of the last refresh | `docs/sidecar-provider-contract.md:523` (codex-cli 0.147.0, native run); learn.chatgpt.com/docs/build-skills, read 2026-11-12; spike S4 |
| Google Antigravity | `.agents/skills/` (legacy `.agent/skills/`) | Yes, through the mirror (documented only; not installed here) | `docs/sidecar-provider-contract.md:41, 526` |

**Trade-offs:**
- The marker is opt-in. A folder without it is still bootstrap-owned and is deleted when the bootstrap does not ship it, as today. The learn skill adds the marker, and `safe-consumer-bootstrap-refresh` lists unmarked folders before a refresh.
- Codex, Antigravity, and possibly Copilot see edits only after the next refresh.
- A name clash blocks that consumer's refresh until the project renames its skill.
- A project skill is runtime guidance that `verify.py` binds into the receipts. Create or edit it no later than CLOSEOUT step 2.

**Sidecar consistency.**
- The sidecar owns only the units its manifest records. It never touches team skills, and it skips a skill whose name is taken. The marker is inert in a sidecar repository, and sidecar code is unchanged.
- The full install refuses a clash instead of skipping. Its agents and the Codex fallback map name bootstrap skills by path, so it cannot run with one of them missing.
- Both rules keep the same promise: a project skill is never overwritten or hidden.

### Pre-branch evidence spike

The orchestrator runs this before branch creation, reads `.claude/skills/integration-gate-spike/SKILL.md` first, and writes `.claude/explorations/2026-11-12_skills-trim-client-spike/REPORT.md`. It is evidence only:
- no repository edit other than REPORT.md;
- no generator or installer run;
- every tree lives in a new empty folder under the runner's scratchpad;
- no `git commit`;
- no edit to `~/.codex/config.toml` or `~/.claude/`.

The planner then writes the results into Phase D (and A, when a stop row fires) before the branch.

```bash
SPIKE="<runner scratchpad>/skills-trim-spike"; mkdir -p "$SPIKE/tools"
cp -a dist/multi-agent "$SPIKE/full" && git -C "$SPIKE/full" init -q
# S1: does Codex list a shipped skill twice? Trusted through a one-run override.
(cd "$SPIKE/full" && codex debug prompt-input -c "projects.\"$SPIKE/full\".trust_level=\"trusted\"" > "$SPIKE/s1-trusted.json")
(cd "$SPIKE/full" && codex debug prompt-input > "$SPIKE/s1-untrusted.json")
mv "$SPIKE/full/.agents" "$SPIKE/agents.off"
(cd "$SPIKE/full" && codex debug prompt-input -c "projects.\"$SPIKE/full\".trust_level=\"trusted\"" > "$SPIKE/s1-config-only.json")
mv "$SPIKE/agents.off" "$SPIKE/full/.agents"
for f in s1-trusted s1-untrusted s1-config-only; do grep -o -E '[^" ]*/skills/[a-z0-9-]+/SKILL\.md' "$SPIKE/$f.json" | sort | uniq -c > "$SPIKE/$f.paths"; done
# S2: hiding. Add agents/openai.yaml (policy.allow_implicit_invocation: false) to .agents/skills/caveman/ and
# disable-model-invocation: true to .agents/skills/humanize/SKILL.md in a copy "$SPIKE/full-hide", then rerun S1's trusted command there.
# S3: from s1-trusted.json, record how Codex shows the longest description (integration-gate-spike, 891 chars) and any omitted-skill warning.
# S4: add "$SPIKE/full/.agents/skills/spike-project-skill/SKILL.md" (name + description), rerun S1's trusted command, and check it is listed once.
# S5: Claude Code listing budget, in folders with no settings.json, so no project hooks run.
mkdir -p "$SPIKE/claude-before/.claude" && cp -a dist/multi-agent/.claude/skills "$SPIKE/claude-before/.claude/skills" && git -C "$SPIKE/claude-before" init -q
(cd "$SPIKE/claude-before" && claude -p --debug-file "$SPIKE/claude-before.log" "Reply with OK.")
# Build "$SPIKE/claude-after/.claude/skills" with a script in "$SPIKE/tools" (run with python3 -I):
# the 35 kept skills, each description cut to its first 300 characters (both Ponytail skills unchanged),
# plus two placeholder skills whose descriptions are 280 characters. Then:
(cd "$SPIKE/claude-after" && claude -p --debug-file "$SPIKE/claude-after.log" "Reply with OK.")
grep -n -i -E 'budget|skill listing|descriptions? (dropped|omitted|truncated)' "$SPIKE/claude-before.log" "$SPIKE/claude-after.log"
ls ~/.claude/skills ~/.agents/skills
```

REPORT.md records:
- the CLI versions (`claude --version`, `codex --version`) and the model in use;
- per skill name, the count and paths of each listing entry;
- the exact listing-budget warning text and any numbers it prints;
- the personal skills present.

Stop conditions: each S-check runs at most twice. A failing command is recorded with its error, not worked around.

| Result | Plan change before the branch |
|---|---|
| S1: every shipped skill listed once from `.agents/skills/`; the config-only run lists none | Expected. Phase D Step 4 corrects the false comment in `render_codex_config` (`scripts/generate_targets.py:1024`) and any doc that repeats it. Removing the entries is a user follow-up. |
| S1: any shipped skill listed twice | The planner revises Phase D Step 4: stop emitting `[[skills.config]]`; update the two validator assertions, the comment, and this repository's tracked `.codex/config.toml`. |
| S1: the config-only run lists skills, and the full run lists each once | The planner revises Phase D Step 4 to record which copy Codex keeps. No config change. |
| S4: `spike-project-skill` not listed | Stop and re-plan Phase A's mirror step. |
| S5: the after run shows no listing-budget warning | Expected. Phase D's Optional Verification greps for the warning text that S5 recorded. |
| S5: the after run still warns | Ask the user before the branch: (a) cap at 200 characters; (b) also set `skillListingBudgetFraction` in the generated `.claude/settings.json` (needs an S5 rerun); (c) move the personal `opik*` skills; (d) accept description loss for the least-used tail. |
| S5: the baseline run shows no warning either | Record it. The cap stands (approved for size), and Phase D keeps the debug-log check. |
| S2 | Record only. Manual-only was rejected. |

### Before and after

| Surface | Before | After (acceptance) | Phase |
|---|---|---|---|
| `dist/multi-agent/CLAUDE.md` | 6,507 B | ≤ 4,500 B (about 4.3 KB); validator budget 5 KiB | F |
| `dist/multi-agent/AGENTS.md` | 9,467 B | ≤ 4,800 B; validator budget 5 KiB | F |
| `shared/policies/workflow.instructions.md` (core) | 40,797 B | ≤ 16,000 B (about 15 KB); validator budget 16 KiB | E |
| Skill descriptions | 55 skills, 19,579 chars | 37 skills, ≤ 10,500 chars (about 10,100) | C, D |
| `workspace` / `quality-and-testing` / `tool-routing` | 11,707 / 10,287 / 5,545 B | ≤ 7,500 / 3,000 / 3,000 B | F |
| Orchestrator / documenter prompts | 16,178 / 7,626 B | ≤ 12,500 / 6,500 B | F |

## Requirement Map (optional)

| Requirement | Acceptance and existing contract | Owning phase | Evidence |
|---|---|---|---|
| REQ-001 | A marked `.claude/skills/<name>/` survives install and refresh, a clash is refused before any write, the folder is mirrored to `.agents/skills/<name>/`, and learn points there (`owned_files()`, `copy_ignore`, `is_third_party_skill_dir`) | `2026-11-12_phase-A-project-owned-skills` | `-k project_skill` tests, including a real CLI install run three times |
| REQ-002 | Defects 2 to 6 fixed: plan-small checklist, Completion Protocol, one control-plane list, "loaded into every session", Copilot root file | `2026-11-12_phase-B-closeout-and-wording-defects` | validator and test pins; grep checks |
| REQ-003 | 37 skills: 9 removed, 4 + 4 merged, deploy-service into bentoml-service, 2 rules into the tests policy, every list updated, section 6 cuts kept | `2026-11-12_phase-C-skill-removals-and-merges` | count checks, absence grep, sidecar set test |
| REQ-004 | Description ≤ 300 characters except Ponytail, enforced by `shared_skill_integrity_errors`; total ≤ 10,500 (open decision) | `2026-11-12_phase-D-skill-description-cap` | `-k description_cap`; total one-liner |
| REQ-005 | The planner skips plan-decomposition in micro-plan mode; the coder's always-load tier is Ponytail only | `2026-11-12_phase-D-skill-description-cap` | grep checks |
| REQ-006 | The Codex duplication and hiding check runs before any step relies on it, and its result is applied | pre-branch spike, `2026-11-12_phase-D-skill-description-cap` | REPORT.md, Phase D Step 4 |
| REQ-007 | CLOSEOUT in `closeout.instructions.md` as 8 numbered steps with reasons, plus a validator pin; `plan-lifecycle.instructions.md`; core ≤ 16 KB; targeted MEMORY search | `2026-11-12_phase-E-workflow-split` | `-k closeout_procedure`, size checks |
| REQ-008 | Root guidance and policy trims within budget; Antigravity pointer; validator only tightened | `2026-11-12_phase-F-guidance-trims` | byte checks, validators |
| REQ-009 | A fresh Claude Code session lists every shipped skill with its description | `2026-11-12_phase-D-skill-description-cap` | Optional Verification: debug log has no listing-budget warning; `/context` |
| REQ-010 | Wiki refreshed; stale-claims audit recorded | `2026-11-12_phase-G-knowledge-refresh` | wiki grep checks; closeout log heading |

## Phases

- [ ] `2026-11-12_phase-A-project-owned-skills` — project skill marker, clash refusal, and `.agents/skills/` mirror
- [ ] `2026-11-12_phase-B-closeout-and-wording-defects` — exploration section 7 defects 2 to 6
- [ ] `2026-11-12_phase-C-skill-removals-and-merges` — 55 to 37 skills
- [ ] `2026-11-12_phase-D-skill-description-cap` — 300-character cap, loading rules, spike result
- [ ] `2026-11-12_phase-E-workflow-split` — CLOSEOUT and plan-lifecycle files, core trim, MEMORY rule
- [ ] `2026-11-12_phase-F-guidance-trims` — root guidance and policy trims
- [ ] `2026-11-12_phase-G-knowledge-refresh` — OpenWiki refresh and stale-claims audit

## Verification

```bash
uv run python .claude/scripts/verify.py fast --format json
```

## Completion Evidence

The final phase listed under `phases:` (`2026-11-12_phase-G-knowledge-refresh`) must also run a documentation, memory, and LEARN audit:
- sweep every live-advice surface for claims that this plan or earlier work invalidated;
- correct or supersede each one;
- leave dated records (archived plans, dated design narratives, closed session logs) unchanged;
- record the audited surfaces and each one's outcome under a `## Stale-claims surfaces checked` heading in that phase's closeout session log.

`verify.py`'s closeout gate requires that exact heading, non-empty, whenever the phase it is closing out is this list's last entry.

In a repository where `openwiki/INSTRUCTIONS.md` exists, that final phase may also need to be a dedicated knowledge-refresh phase. See the canonical Knowledge-Refresh Final Phase rule for when and how, including its recursion guard. The rule is in `.claude/instructions/workflow.instructions.md` until Phase E moves it to `.claude/instructions/plan-lifecycle.instructions.md`.
