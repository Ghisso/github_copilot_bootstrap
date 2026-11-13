---
name: skills-and-instructions-trim
type: big-plan
# status must occur exactly once: planning | in-progress | complete | cancelled
status: in-progress
originating_branch: dev
implementation_branch: skills-and-instructions-trim_implementation
started_at: 2026-11-13T11:54:23Z
phases:
  - 2026-11-12_phase-A-project-owned-skills
  - 2026-11-12_phase-B-instructions
  - 2026-11-12_phase-C-skill-set
  - 2026-11-12_phase-D-knowledge-refresh
current_phase: 2026-11-12_phase-D-knowledge-refresh
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

On 2026-11-12 the user asked for three work phases plus the required knowledge-refresh phase.

On 2026-11-13, two independent plan reviews were folded in:
- `.claude/explorations/2026-11-13_skills-and-instructions-plan-review-codex.md`;
- `.claude/explorations/2026-11-13_skills-and-instructions-plan-review-claude.md`.

### Decisions for the user (made 2026-11-13 while the user was away; confirm or overturn at approval)

1. **Description cap** (proposed 2026-11-12).
   - The user rejected `disable-model-invocation: true` ("manual-only").
   - Instead, every kept skill stays visible to the model, and every description is at most 300 characters, with key trigger words first.
   - The hash-pinned `ponytail` and `ponytail-review` are exempt. `scripts/validate_targets.py` enforces the cap.
   - Measured result: 37 skills and about 10,100 description characters instead of 19,579. Today 24 non-exempt descriptions exceed 300 characters; 14 of them belong to kept skills.
   - To overturn: rewrite the 14 descriptions without a cap, or use a looser cap such as 400 characters (a total of about 11,000).
2. **Unmarked project skills.**
   - A full install or refresh refuses, before any write, when a folder `.claude/skills/<name>/` meets all four conditions: it has an entry named `SKILL.md`; it has no `.project-skill`; the new source does not ship `<name>`; and the bootstrap did not ship `<name>` before.
   - "Shipped before" means `<name>` is listed in `.claude/bootstrap-root/.agents/skills/`. The live `.agents/skills/` is used only when that copy is absent. This is the most reliable record that already exists:
     - the installer writes it at every install;
     - it is tracked in the nested ai-state repository;
     - `validate_agents_takeover` refuses to run when it differs from the live tree.
   - The other records are weaker:
     - the live `.agents/` is git-ignored and absent on a fresh clone until the restorer runs;
     - the bootstrap's own Git history needs the installer to run from a full clone;
     - the nested `.claude` history also holds skills the project created.
   - Folders without `SKILL.md` are ignored. RAG has two such empty folders.
   - The message tells the operator to add `.project-skill` or remove the folder.
   - To overturn: drop the refusal. The marker then stays opt-in, and the refresh skill's listing step is the only guard.
3. **Root budgets.**
   - `CLAUDE.md` keeps its 200-line check and gains a 5 KiB byte check.
   - `AGENTS.md`'s byte limit drops from 16 KiB to 5 KiB.
   - No existing root invariant is dropped.
4. **Spike shape.**
   - S2 (hiding) is removed.
   - Each tree holds only the files it needs, with no hook configuration and with `[mcp_servers.*]` stripped. Trees live in a fresh `mktemp -d` folder outside the checkout.
   - Codex entries are parsed, not grep-counted.
   - S5 runs `claude --bare -p --add-dir <tree> --debug-file ...`, plus a positive-control run with a low `SLASH_COMMAND_TOOL_CHAR_BUDGET`.
   - `--bare` never reads OAuth or the keychain, so its fallback is `--setting-sources project`.
   - Every check has success, error, unsupported, and no-entry outcomes.
   - There is no `skillOverrides "name-only"` option, because the user rejected hiding descriptions.
5. **File ownership.** Each phase lists the files it owns. A file may be revisited after a failing-first test or a review finding.
6. **Absence checks.** They use `test "$(grep -c -F '<text>' <file>)" = "0"` on one named file, or a short `uv run python -I -c` assertion that fails when a root is missing or unreadable. Never `| wc -l`.
7. **Phases.** Four phases. If Phase B is too large to review as one commit, it splits into B1 and B2 (see Design Overview).

### Measured baseline (2026-11-12, re-checked 2026-11-13)

| Surface | Bytes or characters |
|---|---|
| `dist/multi-agent/CLAUDE.md` | 6,507 |
| `dist/multi-agent/AGENTS.md` | 9,467 (Antigravity contract 2,786) |
| `dist/multi-agent/.github/copilot-instructions.md` | 1,393 |
| `shared/policies/workflow.instructions.md` | 40,797 |
| Skill descriptions (validator extractor) | 55 skills, 19,579; the 35 kept skills 13,391; 24 non-exempt over 300, 14 of them kept |
| `workspace` / `quality-and-testing` / `tool-routing` policies | 11,707 / 10,287 / 5,545 |
| Orchestrator / documenter prompts | 16,178 / 7,626 |

## Goals

- Protect skills a consumer project writes itself from full-install refreshes, and make them visible to every client (Phase A).
- Fix defects 2 to 6 from section 7. Split the workflow policy, so CLOSEOUT is read only at the closeout step. Remove the competing closeout procedures. Trim the always-read guidance (Phase B).
- Reach 37 model-visible skills with short, trigger-first descriptions, and enforce the cap (Phase C).
- Refresh the derived wiki and audit live advice for stale claims (Phase D).

## Non-Goals and Constraints (optional)

- Out of scope:
  - the personal `opik*` skills;
  - splitting `.claude/MEMORY.md` (declined on 2026-10-20; only the reading rule changes);
  - recovering RAG's deleted skills;
  - the sidecar's own MEMORY rule;
  - mirroring skills in sidecar repositories.
- Do not re-propose section 6's rejected cuts. Stack-specific content (Hydra, BentoML, Haystack, Gradio) stays.
- Never edit `shared/skills/ponytail/SKILL.md` or `shared/skills/ponytail-review/SKILL.md`.
- Never loosen the root-guidance validator. Phase B only adds checks and lowers limits.
- Regenerate `dist/` only with `uv run python scripts/generate_targets.py --all`. Refresh this repository with `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Only one agent runs generation or the validators at a time.
- Every phase is control-plane/high-risk: a full small plan and the `code`, `architecture`, `security`, `tests`, and `ponytail` review profiles, plus `documentation` when docs change.
- Each phase owns the files its steps list (Decision 5).
- A repeated procedural mistake is fixed by a numbered procedure in canonical instructions, not a memory note.

## Design Overview

### Phase order and done criteria

| Order | Phase | Content |
|---|---|---|
| Before the branch | Evidence spike | Codex skill listing for the generated bundle; Claude Code listing budget (below) |
| A | `2026-11-12_phase-A-project-owned-skills` | Project skill marker, safety refusals, `.agents/skills/` mirror, learn and refresh-skill guidance |
| B | `2026-11-12_phase-B-instructions` | Defects 2 to 6; CLOSEOUT and plan-lifecycle files; competing procedures replaced by pointers; MEMORY rule; root guidance, policy, and prompt trims |
| C | `2026-11-12_phase-C-skill-set` | 55 to 37 skills; 300-character cap and validator check; loading rules; Codex spike result |
| D | `2026-11-12_phase-D-knowledge-refresh` | Regenerate, OpenWiki refresh, and stale-claims audit |

Why this order:
- A comes first by user decision.
- B before C: the corrected closeout procedure then governs the closeouts of C and D.
- The workspace trim in B rewrites that policy's Skills section once, so C never edits the workspace policy.
- C builds on all three earlier pieces of work:
  - A's ownership code: C's self-refresh must pass A's refusals, which works because the 20 retired names are in this repository's `bootstrap-root` record;
  - B's closeout file;
  - the spike results.

Split fallback: if Phase B is too large to review as one commit, split it into B1 and B2:
- B1: defects 2 to 6, the workflow split, and the procedure pointers, including all orchestrator prompt edits;
- B2: the size trims (root guidance, workspace, quality, tool-routing, config-first, documenter).

Done criteria:
- Phases A to D are `complete`, with passing receipts and findings that show zero CRITICAL and MAJOR and gate result `PASS`.
- A marked project skill survives a real install and refresh and is mirrored to `.agents/skills/`. These are refused before any write:
  - a name clash with a shipped skill;
  - a third-party destination;
  - an invalid or mismatched name;
  - a symlink;
  - an unmarked skill the bootstrap never shipped.
- Defects 2 to 6 are fixed. README, the commit skill, and the authoring `CLAUDE.md` point to the closeout file instead of restating it.
- The workflow core is 16,000 bytes or less.
- CLOSEOUT lives in `closeout.instructions.md` as 8 numbered steps, each with a reason. Its step 2 names the learn skill. A validator pin protects it.
- `plan-lifecycle.instructions.md` exists. The MEMORY rule is a targeted search.
- The generated `CLAUDE.md` is 4,500 bytes or less and at most 200 lines. `AGENTS.md` is 4,800 bytes or less. Both name the closeout file.
- `dist` holds 37 skills. The total listing length (description plus `when_to_use`) is 10,500 characters or less. Only the two Ponytail skills exceed 300 characters. The validator enforces the cap.
- OpenWiki is refreshed, and `## Stale-claims surfaces checked` is recorded.
- The optional host check records whether a fresh Claude Code session lists every skill with its description, or records that the evidence was inconclusive.

### Project-owned skills (Phase A)

**Mechanism.** No client reads skills from a custom repository folder, so there is no new folder.

- A real (non-symlink) folder `.claude/skills/<name>/` that holds a regular, non-symlink file named `.project-skill` belongs to the project.
- `scripts/runtime_ownership.py` gains `PROJECT_SKILL_MARKER` and `is_project_skill_dir()`, beside the OpenWiki marker (`THIRD_PARTY_SKILL_MARKER`). Every type check uses `lstat` and follows no link.
- `scripts/install_bootstrap.py` changes in three places:
  - `owned_files()` skips a marked folder, so a refresh neither deletes nor overwrites it.
  - `validate_project_skills()` runs before any write. It reads nothing through a link. It collects every problem and refuses once, listing them all. It refuses:
    - a symlink as `.claude/skills/` or as an entry directly under it;
    - a symlinked marker or `SKILL.md`;
    - a project folder name that is not lowercase kebab case;
    - a frontmatter `name:` that differs from the folder name;
    - a name the new source ships (this covers a marker planted in a shipped folder);
    - a name held by a third-party bundle (for example `openwiki`);
    - an unmarked skill the bootstrap never shipped (Decision 2).

    Folder names, never frontmatter values, are used for comparisons and destinations.
  - After copying, it mirrors each marked folder, marker included (see the scope change below), to `.agents/skills/<name>/`.
    - This runs before `populate_bootstrap_root`, so the `bootstrap-root/.agents` copy, `validate_agents_takeover`, and `verify.py`'s root-adapter comparison all see the same tree.
    - A folder holding a symlink or non-regular entry deeper inside is checked whole first and skipped with a warning.
- The mirror grants no ownership, so it is ordinary generated content: the next refresh prunes it and writes it again.
- **Scope change (2026-11-13, orchestrator, Phase A implementation):** the mirror keeps the marker. The coder found that an unmarked mirror lands in `bootstrap-root/.agents/skills/`, the shipped-before record, so a project skill whose `.claude` marker went missing would count as retired and be deleted without a refusal. With the marker in the mirror (and so in the record), `validate_project_skills()` refuses an unmarked `.claude/skills/<name>/` whose record copy holds `.project-skill`, whether or not the new source ships `<name>`. The marker under `.agents/skills/` grants no ownership (`is_project_skill_dir()` requires a `.claude/skills` parent), so the mirror is still pruned and rewritten each refresh.

**Why not a state folder.** A `CONSUMER_STATE_PATHS` entry (for example `project-skills/`) would survive refreshes, but no client lists skills from it.

These promises cover the full install. In a sidecar repository, team skills are already never touched, the marker is inert, and nothing mirrors them.

| Client | Reads repository skills from | Sees a marked project skill | Evidence |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` (start folder up to the repository root; nested folders on demand; `--add-dir`) | Yes, directly | code.claude.com/docs/en/skills, read 2026-11-12 |
| Copilot in VS Code | `.github/skills/`, `.claude/skills/`, `.agents/skills/`; one entry per name | Yes, through the mirror. With copies in both `.claude/skills/` and `.agents/skills/`, it listed the `.agents/skills/` copy, so it sees edits as of the last refresh | `docs/sidecar-provider-contract.md:524-525` (native run, 2026-09-25) |
| Codex | `.agents/skills/` from the working folder up to the repository root, and `$HOME/.agents/skills` | Yes, through the mirror, as of the last refresh | `docs/sidecar-provider-contract.md:523` (codex-cli 0.147.0, native run); learn.chatgpt.com/docs/build-skills, read 2026-11-12; spike S4 |
| Google Antigravity | `.agents/skills/` (legacy `.agent/skills/`) | Yes, through the mirror (documented only; not installed here) | `docs/sidecar-provider-contract.md:41, 526` |

**Trade-offs:**
- An unmarked skill folder that the bootstrap never shipped makes the installer refuse (Decision 2). An unmarked folder whose name the bootstrap shipped before is a retired skill and is deleted, as today.
- A consumer with no shipped-before record gets a refusal for every unmarked skill folder its new source lacks. The operator marks or removes each.
- Codex, Antigravity, and Copilot see edits only after the next refresh.
- Never create or edit `.agents/skills/<name>/` by hand. A hand edit makes the next refresh refuse through the takeover check, and it breaks the receipt fingerprint.
- A name clash blocks that consumer's refresh until the project renames its skill.
- A project skill is runtime guidance: `verify.py`'s nested-runtime fingerprint binds it. Create or edit it no later than CLOSEOUT step 2.
- Skipping a mirror that holds links keeps content reached through links out of `.agents/` and its `bootstrap-root` copy. It is not a privacy boundary: the project skill itself is synced with `.claude/`, so the learn skill's "no sensitive information" gate still applies.

**Sidecar consistency.**
- The sidecar owns only the units its manifest records. It never touches team skills, and it skips a skill whose name is taken. Sidecar code is unchanged. Phase A adds tests showing that the marker changes nothing in sidecar mode.
- The full install refuses a clash instead of skipping. Its agents and the Codex fallback map name bootstrap skills by path, so it cannot run with one of them missing.
- Both rules keep the same promise: a project skill is never overwritten or hidden.

### Pre-branch evidence spike

The orchestrator runs this before branch creation, reads `.claude/skills/integration-gate-spike/SKILL.md` first, and writes `.claude/explorations/2026-11-12_skills-trim-client-spike/REPORT.md`. It is evidence only:
- no repository edit other than REPORT.md;
- no generator or installer run;
- no `git commit` anywhere;
- no edit to `~/.codex/` or `~/.claude/`.

Rules for the probes:
- Every tree lives in a fresh `mktemp -d` folder outside the checkout.
- Each tree holds only the files its probe needs, with no hook configuration and with `[mcp_servers.*]` stripped.
- Each client call has a `timeout`.
- Tool scripts live in `"$SPIKE/tools"` and run with `python3 -I`.
- S2 (hiding) was removed; the labels S1, S3, S4, and S5 are kept.

Prior observation (Codex review, 2026-11-13): a main Codex session in this checkout listed 76 skill entries with 76 unique names, all with descriptions. That session used the tracked `.codex/config.toml`, which has 0 `[[skills.config]]` entries; the generated one has 55. It therefore does not answer S1.

```bash
SPIKE="$(mktemp -d -p '<runner scratchpad, outside the checkout>')"; mkdir -p "$SPIKE/tools" "$SPIKE/home/.codex" "$SPIKE/home-untrusted/.codex"
CODEX="$(command -v codex)"; CLAUDE="$(command -v claude)"
# S1/S3/S4 tree: AGENTS.md, both skill folders, and a stripped config. No hooks file, no MCP servers.
mkdir -p "$SPIKE/full/.agents" "$SPIKE/full/.claude" "$SPIKE/full/.codex"
cp -a dist/multi-agent/AGENTS.md "$SPIKE/full/" && cp -a dist/multi-agent/.agents/skills "$SPIKE/full/.agents/skills" && cp -a dist/multi-agent/.claude/skills "$SPIKE/full/.claude/skills"
python3 -I "$SPIKE/tools/strip_mcp.py" dist/multi-agent/.codex/config.toml "$SPIKE/full/.codex/config.toml"
git -C "$SPIKE/full" init -q
cp -a "$SPIKE/full" "$SPIKE/config-only" && rm -rf "$SPIKE/config-only/.agents"
cp -a "$SPIKE/full" "$SPIKE/with-project" && mkdir -p "$SPIKE/with-project/.agents/skills/spike-project-skill"
# write a two-field SKILL.md (name: spike-project-skill, description) into that folder
# Isolated Codex homes: no hooks file, no personal skills. The trusted home trusts the three trees.
printf '[projects."%s"]\ntrust_level = "trusted"\n\n' "$SPIKE/full" "$SPIKE/config-only" "$SPIKE/with-project" > "$SPIKE/home/.codex/config.toml"
: > "$SPIKE/home-untrusted/.codex/config.toml"
run_codex() { (cd "$2" && HOME="$1" CODEX_HOME="$1/.codex" timeout 120 "$CODEX" debug prompt-input) > "$3" 2> "$3.err"; echo "exit $?" >> "$3.err"; }
run_codex "$SPIKE/home" "$SPIKE/full" "$SPIKE/s1-trusted.json"
run_codex "$SPIKE/home-untrusted" "$SPIKE/full" "$SPIKE/s1-untrusted.json"
run_codex "$SPIKE/home" "$SPIKE/config-only" "$SPIKE/s1-config-only.json"
run_codex "$SPIKE/home" "$SPIKE/with-project" "$SPIKE/s4.json"
# Parse the real listing: find the skills section in the rendered prompt items and read each "- <name>: <description> (file: <path>)" line.
# parse_entries.py prints per-name count, path, and description length, saves five entries verbatim, and exits 3 when no listing is found.
for f in s1-trusted s1-untrusted s1-config-only s4; do python3 -I "$SPIKE/tools/parse_entries.py" "$SPIKE/$f.json" > "$SPIKE/$f.entries" 2>&1; echo "exit $?" >> "$SPIKE/$f.entries"; done
# S5: Claude Code listing budget. The working folder and both trees hold no settings and no CLAUDE.md.
mkdir -p "$SPIKE/empty" "$SPIKE/claude-before/.claude" && cp -a dist/multi-agent/.claude/skills "$SPIKE/claude-before/.claude/skills"
python3 -I "$SPIKE/tools/make_after_set.py" dist/multi-agent/.claude/skills "$SPIKE/claude-after/.claude/skills"
# make_after_set.py: the 35 kept skills, each description cut to 300 characters (both Ponytail skills unchanged), plus two placeholder skills with 280-character descriptions.
run_claude() { (cd "$SPIKE/empty" && env $4 timeout 180 "$CLAUDE" $1 -p --add-dir "$2" --debug-file "$3" "Reply with OK.") > "$3.out" 2>&1; echo "exit $?" >> "$3.out"; }
run_claude --bare "$SPIKE/claude-before" "$SPIKE/s5-control.log" SLASH_COMMAND_TOOL_CHAR_BUDGET=1000
run_claude --bare "$SPIKE/claude-before" "$SPIKE/s5-before.log"
run_claude --bare "$SPIKE/claude-after" "$SPIKE/s5-after.log"
# --bare never reads OAuth or the keychain. When it cannot authenticate, repeat the three runs with "--setting-sources project" in place of "--bare" (no user hooks; personal skills still load and are recorded).
grep -n -i -E 'skill|budget' "$SPIKE/s5-control.log" "$SPIKE/s5-before.log" "$SPIKE/s5-after.log"
```

REPORT.md records:
- the CLI versions and the model in use;
- the parsed entries for each run, with a sample;
- the exact warning text from the positive control;
- which S5 mode ran;
- the personal skills present (`ls ~/.claude/skills ~/.agents/skills`);
- every `.err` and `.out` file's exit code.

Each probe runs at most twice. A failing command is recorded with its error, not worked around.

| Check | Result | Plan change before the branch | May implementation continue? |
|---|---|---|---|
| S1 | Success: every shipped skill listed once from `.agents/skills/`; the config-only run lists none | Expected. Phase C Step 5 corrects the false comment in `render_codex_config` (`scripts/generate_targets.py:1024`). Removing the inert entries is a user follow-up. | Yes |
| S1 | Success: any shipped skill listed twice | The planner revises Phase C Steps 1 and 5: stop emitting `[[skills.config]]`, and update the two validator assertions and the comment | Yes, after the revision |
| S1 | Success: the config-only run lists skills, and the full run lists each once | The planner revises Phase C Step 5 to record which copy Codex keeps; no config change | Yes |
| S1 | Error, unsupported (for example the isolated home lacks needed authentication), or no-entry (exit 3) | Phase C Step 5 writes a neutral comment ("not observed; see REPORT.md") and changes no configuration. REQ-006 is recorded as not proven. | Yes |
| S3 | Any result, including error, unsupported, or no-entry | Record only: how Codex shows the 891-character `integration-gate-spike` description, and any omitted-skill warning | Yes |
| S4 | Success: `spike-project-skill` listed once | Expected | Yes |
| S4 | Success for S1, but `spike-project-skill` missing | Stop. Re-plan Phase A's mirror step | A waits for the re-plan; B may start |
| S4 | Error, unsupported, or no-entry | Phase A relies on the frozen native run (`docs/sidecar-provider-contract.md:523`, the same CLI version); record the limit | Yes |
| S5 | The positive control shows a listing-budget warning | Logging works. Record the exact text; Phase C's Optional Verification greps for it | Yes |
| S5 | The positive control shows no warning, or every mode fails (error, unsupported, timeout) | S5 is inconclusive. Phase C's Optional Verification records `NOT RUN` or inconclusive. REQ-009 stays unproven; the cap stands for size. | Yes |
| S5 | Working control; the after run shows no warning | Expected | Yes |
| S5 | Working control; the after run still warns | Ask the user before Phase C: (a) cap at 200 characters; (b) also set `skillListingBudgetFraction` in the generated `.claude/settings.json` (needs an S5 rerun); (c) move the personal `opik*` skills; (d) accept description loss for the least-used tail | A and B may start; C waits for the user |
| S5 | Working control; the baseline also shows no warning | No overflow in this environment today. Record it; the cap stands | Yes |

### Before and after

| Surface | Before | After (acceptance) | Phase |
|---|---|---|---|
| `dist/multi-agent/CLAUDE.md` | 6,507 B | ≤ 4,500 B (about 4.3 KB); validator: 200 lines and 5 KiB | B |
| `dist/multi-agent/AGENTS.md` | 9,467 B | ≤ 4,800 B; validator 5 KiB (was 16 KiB) | B |
| `shared/policies/workflow.instructions.md` (core) | 40,797 B | ≤ 16,000 B (about 15 KB); validator budget 16 KiB | B |
| `workspace` / `quality-and-testing` / `tool-routing` | 11,707 / 10,287 / 5,545 B | ≤ 7,500 / 3,000 / 3,000 B | B |
| Orchestrator / documenter prompts | 16,178 / 7,626 B | ≤ 12,500 / 6,500 B | B |
| Skill listing text (description plus `when_to_use`) | 55 skills, 19,579 chars | 37 skills, ≤ 10,500 chars (about 10,100) | C |

## Requirement Map (optional)

| Requirement | Acceptance and existing contract | Owning phase | Evidence |
|---|---|---|---|
| REQ-001 | A marked `.claude/skills/<name>/` survives install and refresh and is mirrored to `.agents/skills/<name>/`. Clashes, third-party destinations, invalid names, symlinks, and unmarked never-shipped skills are refused before any write. Learn and the refresh skill point there (`owned_files()`, `validate_agents_takeover`, `is_third_party_skill_dir`). | `2026-11-12_phase-A-project-owned-skills` | `-k project_skill` tests, including real CLI transition runs and sidecar tests |
| REQ-002 | Defects 2 to 6 fixed: plan-small checklist; Completion Protocol, with the learn-skill read moved to CLOSEOUT step 2; one control-plane list; "loaded into every session"; Copilot root file. Competing README, commit-skill, and authoring `CLAUDE.md` procedures replaced by pointers. | `2026-11-12_phase-B-instructions` | validator and test pins; grep checks |
| REQ-007 | CLOSEOUT in `closeout.instructions.md` as 8 numbered steps with reasons (step 2 names learn), plus a validator pin; root guidance names it; `plan-lifecycle.instructions.md`; core ≤ 16 KB; targeted MEMORY search | `2026-11-12_phase-B-instructions` | `-k closeout_procedure`; size checks |
| REQ-008 | Root guidance, policy, and prompt trims within budget; Antigravity pointer; validator only tightened (200 lines kept, bytes added) | `2026-11-12_phase-B-instructions` | `-k root_guidance_budget`; byte checks; validators |
| REQ-003 | 37 skills: 9 removed, 4 + 4 merged, deploy-service into bentoml-service, 2 rules into the tests policy, every list updated, section 6 cuts kept | `2026-11-12_phase-C-skill-set` | count check, absence check, sidecar set test, merged-skill test |
| REQ-004 | Listing length ≤ 300 characters except Ponytail, enforced by `shared_skill_integrity_errors` through one length function; total ≤ 10,500 (Decision 1) | `2026-11-12_phase-C-skill-set` | `-k description_cap`; total one-liner |
| REQ-005 | The planner reads plan-decomposition only in full-plan mode; the coder's always-load tier is Ponytail only | `2026-11-12_phase-C-skill-set` | `-k loading_rules`; grep checks |
| REQ-006 | The Codex check runs before any step relies on it, and its result is applied | pre-branch spike, `2026-11-12_phase-C-skill-set` | REPORT.md; Phase C Steps 1 and 5 |
| REQ-009 | A fresh Claude Code session lists every shipped skill with its description | `2026-11-12_phase-C-skill-set` | Optional Verification using S5's method and positive-control text; an inconclusive result is recorded as such |
| REQ-010 | Wiki refreshed; stale-claims audit recorded | `2026-11-12_phase-D-knowledge-refresh` | page-specific wiki checks; closeout log heading |

## Phases

- [x] `2026-11-12_phase-A-project-owned-skills` — project skill marker, safety refusals, and `.agents/skills/` mirror
- [x] `2026-11-12_phase-B-instructions` — defects 2 to 6, workflow split, procedure pointers, root guidance and policy and prompt trims
- [x] `2026-11-12_phase-C-skill-set` — 55 to 37 skills, 300-character cap, loading rules, spike result
- [ ] `2026-11-12_phase-D-knowledge-refresh` — regenerate, OpenWiki refresh, and stale-claims audit

## Verification

```bash
uv run python .claude/scripts/verify.py fast --format json
```

## Completion Evidence

The final phase listed under `phases:` (`2026-11-12_phase-D-knowledge-refresh`) must also run a documentation, memory, and LEARN audit:
- sweep every live-advice surface for claims that this plan or earlier work invalidated;
- correct or supersede each one;
- leave dated records (archived plans, dated design narratives, closed session logs) unchanged;
- record the audited surfaces and each one's outcome under a `## Stale-claims surfaces checked` heading in that phase's closeout session log.

`verify.py`'s closeout gate requires that exact heading, non-empty, whenever the phase it is closing out is this list's last entry.

In a repository where `openwiki/INSTRUCTIONS.md` exists, that final phase may also need to be a dedicated knowledge-refresh phase. See the canonical Knowledge-Refresh Final Phase rule for when and how, including its recursion guard. The rule is in `.claude/instructions/workflow.instructions.md` until Phase B moves it to `.claude/instructions/plan-lifecycle.instructions.md`.
