# Sidecar Provider Contract

This document is the evidence record for Phase A of the sidecar bootstrap
overlay plan (`.claude/plans/consumer-sidecar-bootstrap-overlay.md`, small
plan `.claude/plans/2026-09-24_phase-A-sidecar-provider-contract.md`). It
answers one question for four coding-agent clients — Claude Code, OpenAI
Codex, GitHub Copilot in VS Code, and Google Antigravity: which repository
folders does each client read for skills and instructions, and does a small
per-client bridge file stay active in every session?

Per the big plan's Decision 14, a folder or bridge ships only once at least
one client has been run against the fixture below and shown the expected
result (a **native-run** result). The first sections record what the
clients' documentation and, in a few places, their published source code
say. Step 4 at the end records the native runs of 2026-09-25 and the frozen
read list, write list, and bridge paths that the later phases use.

## Evidence tiers

| Tier | Meaning |
| --- | --- |
| `documented` | A vendor documentation page states the behavior. Cited with its exact URL and the date it was checked. |
| `source` | Only the client's published source code shows the behavior; no documentation page states it. |
| `native-run` | The real client ran against the fixture in Step 2 below and the result was observed directly. See Step 4. |
| `unavailable` | The client is not installed, cannot be run, or a session type does not exist on the current host. |

A claim below `native-run` is not a support claim. It only says what the
client's maker asserts, or what its code appears to do.

## Documented starting point, re-checked 2026-09-25

The 2026-09-24 plan review read one set of pages for each client. This
section re-reads every one of those pages and records what changed.
Everything below was checked today, 2026-09-25, unless a row says otherwise.

| Client | Repository skill folders read | Bridge mechanism | Duplicate skill names | Git-ignored files |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/skills/` only (project scope, plus the user's `~/.claude/skills/` and an enterprise-managed copy — none of these are `.agents/skills/` or `.github/skills/`) | `.claude/rules/*.md` files load in addition to `CLAUDE.md`. `paths` is the only frontmatter field Claude Code reads from a rule; every other field is ignored without an error. **A rule with no `paths` frontmatter loads at launch with the same priority as `.claude/CLAUDE.md`.** `CLAUDE.local.md` is still supported and loads alongside `CLAUDE.md`. | Enterprise wins over personal, and personal wins over project | Undocumented. Carried over from the 2026-09-24 review: this repository's own sessions load `.claude/skills/` and `.claude/rules/` files that `.gitignore` ignores, but `info/exclude` specifically was not re-tested this cycle |
| OpenAI Codex | `.agents/skills/` in the current directory, in every parent directory up to the repository root, and at the repository root itself. `.codex/skills/` is not documented anywhere found this cycle; that claim stays at the `source` tier, carried over from the 2026-09-24 review (not independently re-checked against Codex's code this cycle) | None additive. `AGENTS.override.md` fully replaces `AGENTS.md` in a directory. Fallback names (`project_doc_fallback_filenames`) are used only in a directory that has neither file. `developer_instructions` is a `config.toml` key; a *project*-level `.codex/config.toml` loads only when the project is marked trusted | Both copies appear; Codex does not merge them | Undocumented. Carried over: plain folder scan, no `.gitignore` check found in documentation |
| Copilot in VS Code | `.github/skills/`, `.claude/skills/`, `.agents/skills/` | `.github/instructions/*.instructions.md` with `applyTo`. Instruction sources are additive within one harness. **New this cycle:** the file location that actually loads depends on the session type and the format the harness uses — an Agent Host session using the Copilot format reads `.github/instructions`, but an Agent Host session using the Claude format reads `.claude/rules` instead. **Also new:** the Copilot harness's documented "recommended project instructions" are `.github/copilot-instructions.md` **or** `AGENTS.md` — a session can be configured to read either one, not necessarily both | Undocumented. Carried over: the Local agent keeps the first skill it finds (not re-confirmed by a documentation page this cycle) | Undocumented. Carried over: plain folder read, no `.gitignore` check found in documentation |
| Google Antigravity | `<workspace-root>/.agents/skills/<name>/`; legacy `<workspace-root>/.agent/skills/<name>/` is still read for backward compatibility | `.agents/rules/*.md` (and legacy `.agent/rules/*.md`), discovered at every directory from the file being edited up to the workspace root, alongside root or nested `AGENTS.md`/`GEMINI.md`. Every rule file must declare a `trigger`; a file that omits frontmatter or names an unrecognized `trigger` value is silently discarded. `always_on` injects the rule's full content into the system prompt on every turn | Undocumented | Strict mode explicitly respects `.gitignore` and denies file access outside the workspace. Default mode's behavior is undocumented |

### What changed since the 2026-09-24 review

- **Claude Code — the bridge candidate is now `documented`, not undocumented.**
  `code.claude.com/docs/en/memory` (checked 2026-09-25) states: "Rules without
  `paths` frontmatter are loaded at launch with the same priority as
  `.claude/CLAUDE.md`." The 2026-09-24 review could not find this and called
  it undocumented. This page was not one of the three the earlier review
  read (`/skills`, `/claude-directory`, `/large-codebases`); it is the
  correct page for rule-loading behavior, and this re-check adds it to the
  source list.
- **Claude Code — the full skill frontmatter field list is now known.**
  `code.claude.com/docs/en/claude-directory` (checked 2026-09-25) lists every
  field Claude Code reads from `SKILL.md`: `name`, `description`,
  `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`,
  `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`,
  `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`,
  `license`, `compatibility`. `visibility` — the field this bootstrap's own
  skills use — is not on that list, so Claude Code silently ignores it, per
  the same page's general rule that an unrecognized field is "ignored
  without an error." This is a documented answer to Question 5 below, not
  new behavior.
- **Copilot in VS Code — two new facts about the bridge file's competition.**
  `code.visualstudio.com/docs/copilot/customization/custom-instructions`
  (checked 2026-09-25) documents that the *effective* instruction-file
  location depends on which harness format a session uses (Copilot format
  reads `.github/instructions`; Claude format reads `.claude/rules` even
  inside a Copilot-branded Agent Host session), and that a Copilot session's
  recommended project instructions are `.github/copilot-instructions.md` or
  `AGENTS.md`, not necessarily both together. Record which format a Copilot
  session actually used during Step 3.
- **Google Antigravity — confirmed with an exact quote, not just an assumption.**
  `antigravity.google/docs/skills` (checked 2026-09-25) states outright:
  "Antigravity defaults to `.agents/skills`, but still maintains backward
  compatibility for `.agent/skills`." `antigravity.google/docs/rules`
  confirms the silent-discard behavior for a missing or invalid `trigger`
  with the same wording as the 2026-09-24 review recorded.
- **No row needed to be reversed.** Every duplicate-name and git-ignore cell
  that was undocumented on 2026-09-24 is still undocumented today; nothing
  new was found for those cells this cycle.

### Sources checked 2026-09-25

- Claude Code: `code.claude.com/docs/en/skills`, `/docs/en/claude-directory`,
  `/docs/en/large-codebases`, `/docs/en/memory` (new this cycle).
- OpenAI Codex: `learn.chatgpt.com/docs/build-skills`,
  `/docs/agent-configuration/agents-md`, `/docs/config-file/config-reference`,
  `/docs/config-file/config-advanced` (new this cycle — it is the page that
  documents the project-trust gate on `.codex/config.toml`).
- Copilot in VS Code: `code.visualstudio.com/docs/agent-customization/agent-skills`,
  `/docs/copilot/customization/custom-instructions`,
  `/docs/agents/run/agent-harnesses` (new this cycle — session-type detail).
- Google Antigravity: `antigravity.google/docs/rules`, `/docs/skills`,
  `/docs/settings`.

All of the above pages were fetched and read today. None failed to load.

## Questions Per Client — answered at the documented/source tier

These are the answers from documentation and source code alone, written
before the native runs. Step 4 records the native answers. Where the two
differ, Step 4 wins.

**1. Which repository skill folders does each client read?**

- Claude Code: `.claude/skills/` only (`documented`).
- Codex: `.agents/skills/` from the working directory up through the
  repository root (`documented`); `.codex/skills/` (`source`, not
  re-verified this cycle).
- Copilot in VS Code: `.github/skills/`, `.claude/skills/`, `.agents/skills/`
  (`documented`).
- Antigravity: `.agents/skills/` at the workspace root, and legacy
  `.agent/skills/` (`documented`).

**2. Does a client discover a skill or bridge file that Git ignores through
`info/exclude`?**

Undocumented for every client except one case: Antigravity's Strict mode
documents that it "respects `.gitignore` rules, preventing it from accessing
ignored files" (`documented`, `antigravity.google/docs/settings`). Whether
that also covers the local, per-clone `info/exclude` file specifically —
rather than a tracked `.gitignore` — was not stated on that page and stays
unverified until Step 3's native run. Antigravity's default (non-Strict)
mode, and every other client, remain undocumented on this point; this is
carried over from the 2026-09-24 review, not resolved this cycle.

**3. When the same skill name is in two folders a client reads, does it show
one copy, both copies, or an error?**

- Codex: both copies appear; Codex does not merge them (`documented`).
- Claude Code: not directly the collision case this plan needs (Claude Code
  does not read `.agents/skills/` or `.github/skills/` at all — see Question
  1), but its own documented precedence rule, for completeness, is enterprise
  over personal, personal over project (`documented`).
- Copilot in VS Code and Antigravity: undocumented. Copilot's Local agent is
  reported (`source`, carried over) to keep the first skill it finds; this
  was not confirmed by a documentation page this cycle. This is exactly the
  fixture's collision case (`sidecar-marker-b` present in `.claude/skills/`,
  `.agents/skills/`, and, as a different, team-owned skill, in
  `.github/skills/`) and needs a native run to answer for these two clients.

**4. Does the candidate bridge load in every session while tracked team
guidance stays active?**

- Claude Code: yes, `documented` this cycle (see "What changed" above).
  `.claude/rules/ai-bootstrap-sidecar.md` with no `paths` frontmatter loads
  at launch, with the same priority as `CLAUDE.md`, and `CLAUDE.md` keeps
  loading too — the mechanism is additive, not a replacement.
- Antigravity: yes, `documented`. `.agents/rules/ai-bootstrap-sidecar.md`
  with `trigger: always_on` injects its full content on every turn; a rule
  with no `trigger`, or an invalid one, is silently discarded, so the exact
  frontmatter is required, not optional.
- Copilot in VS Code: `applyTo: "**"` on
  `.github/instructions/ai-bootstrap-sidecar.instructions.md` is documented
  to auto-attach to every file the agent creates or modifies. Whether it also
  fires in a turn that touches no file at all is undocumented (`source`,
  carried over: the Local agent's `chat.includeApplyingInstructions` setting
  gates this, and that setting is itself documented today as "deprecated and
  only used by the Local agent"). Whether `.github/copilot-instructions.md`
  stays active alongside it is undocumented at the `documented` tier for the
  general case, though the same-format case (Copilot format reading both
  files) is a reasonable reading of the "additive" language — Step 3 needs to
  confirm it directly.
- Codex: no bridge is planned. `AGENTS.md` is confirmed to load normally
  (`documented`), and `.agents/skills/` discovery is confirmed (`documented`,
  Question 1); Step 3 still needs to confirm the sidecar skills are listed in
  a live session, because a documentation page cannot prove a live listing.

**5. Does a client reject or warn about a skill frontmatter field the
bootstrap ships, such as `visibility`?**

- Claude Code: no. It documents that "Claude Code ignores a field it doesn't
  recognize without reporting an error," and its full field list (see "What
  changed" above) does not include `visibility` (`documented`).
- Codex, Copilot in VS Code, and Antigravity: not found in today's fetch.
  Copilot in VS Code documents that an invalid `name` — wrong characters, or
  a name that does not match the skill's folder — causes the skill to
  "silently fail to load," but that page does not say what happens to an
  extra, unrecognized field such as `visibility` (`documented` for the `name`
  rule; undocumented for unrecognized fields). Antigravity's skill frontmatter
  table lists only `name` and `description`; it does not say whether an
  extra field is rejected, warned about, or ignored (undocumented).

## Step 2 — the fixture recipe

The block below creates a throwaway Git repository outside this repository,
with tracked team files, one tracked team skill per read-list folder, two
untracked sidecar marker skills duplicated across `.claude/skills/` and
`.agents/skills/`, a team skill in `.github/skills/` that collides by name
with one of them, and the three candidate bridge files — then hides every
sidecar-owned path with a local, untracked `info/exclude` block and commits
only the team files.

**Run this in your own shell, not through an agent session.** This
repository's own commit-gate hook blocks any `git commit` a coding agent
runs through its own tool calls, even in a different, throwaway repository,
so an agent cannot complete this recipe on your behalf.

Save the block to a file and run it with `bash`, for example
`bash sidecar-fixture.sh`. Do not paste it into an interactive shell: its
`set -e` and `exit 1` lines would close that shell on the first error.

```bash
set -euo pipefail

DIR="$HOME/sidecar-fixture-$(date +%Y%m%d-%H%M%S)"
if [ -e "$DIR" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
  echo "refusing: $DIR already exists and is not empty" >&2
  exit 1
fi
mkdir -p "$DIR" && cd "$DIR" || exit 1

git init -q

TOPLEVEL="$(git rev-parse --show-toplevel)"
if [ "$(cd "$TOPLEVEL" && pwd -P)" != "$(pwd -P)" ]; then
  echo "refusing: git toplevel ($TOPLEVEL) does not match \$DIR ($DIR)" >&2
  exit 1
fi

# --- team-owned files that will be tracked and committed ----------------------
mkdir -p .github/skills .claude/skills .agents/skills .github/instructions .claude/rules .agents/rules

cat > CLAUDE.md <<'EOF'
# Team project instructions
TEAM-CLAUDE-MD-MARKER
EOF

cat > AGENTS.md <<'EOF'
# Team project instructions
TEAM-AGENTS-MD-MARKER
EOF

cat > .github/copilot-instructions.md <<'EOF'
# Team Copilot instructions
TEAM-COPILOT-INSTRUCTIONS-MARKER
EOF

mkdir -p .claude/skills/team-claude-skill .agents/skills/team-agents-skill .github/skills/team-github-skill

cat > .claude/skills/team-claude-skill/SKILL.md <<'EOF'
---
name: team-claude-skill
description: Team-owned skill tracked in .claude/skills for the fixture.
---
If asked to identify yourself, reply exactly: TEAM-CLAUDE-SKILL-REPLY
EOF

cat > .agents/skills/team-agents-skill/SKILL.md <<'EOF'
---
name: team-agents-skill
description: Team-owned skill tracked in .agents/skills for the fixture.
---
If asked to identify yourself, reply exactly: TEAM-AGENTS-SKILL-REPLY
EOF

cat > .github/skills/team-github-skill/SKILL.md <<'EOF'
---
name: team-github-skill
description: Team-owned skill tracked in .github/skills for the fixture.
---
If asked to identify yourself, reply exactly: TEAM-GITHUB-SKILL-REPLY
EOF

# A team-owned skill in .github/skills/ whose name collides with a sidecar skill.
mkdir -p .github/skills/sidecar-marker-b
cat > .github/skills/sidecar-marker-b/SKILL.md <<'EOF'
---
name: sidecar-marker-b
description: Team-owned skill that collides in name with a sidecar skill.
---
If asked to identify yourself, reply exactly: SIDECAR-MARKER-B-GITHUB-TEAM
EOF

# --- sidecar-owned files: untracked, must end up Git-ignored -------------------
mkdir -p .claude/skills/sidecar-marker-a .claude/skills/sidecar-marker-b \
         .agents/skills/sidecar-marker-a .agents/skills/sidecar-marker-b

cat > .claude/skills/sidecar-marker-a/SKILL.md <<'EOF'
---
name: sidecar-marker-a
description: Sidecar marker skill A, copy under .claude/skills.
---
If asked to identify yourself, reply exactly: SIDECAR-MARKER-A-CLAUDE
EOF

cat > .agents/skills/sidecar-marker-a/SKILL.md <<'EOF'
---
name: sidecar-marker-a
description: Sidecar marker skill A, copy under .agents/skills.
---
If asked to identify yourself, reply exactly: SIDECAR-MARKER-A-AGENTS
EOF

cat > .claude/skills/sidecar-marker-b/SKILL.md <<'EOF'
---
name: sidecar-marker-b
description: Sidecar marker skill B, copy under .claude/skills.
---
If asked to identify yourself, reply exactly: SIDECAR-MARKER-B-CLAUDE
EOF

cat > .agents/skills/sidecar-marker-b/SKILL.md <<'EOF'
---
name: sidecar-marker-b
description: Sidecar marker skill B, copy under .agents/skills.
---
If asked to identify yourself, reply exactly: SIDECAR-MARKER-B-AGENTS
EOF

cat > .claude/rules/ai-bootstrap-sidecar.md <<'EOF'
BRIDGE-CLAUDE-RULE-MARKER
Apply the sidecar's coding and review skills to every task in this repository.
EOF

cat > .agents/rules/ai-bootstrap-sidecar.md <<'EOF'
---
trigger: always_on
---
BRIDGE-AGENTS-RULE-MARKER
Apply the sidecar's coding and review skills to every task in this repository.
EOF

cat > .github/instructions/ai-bootstrap-sidecar.instructions.md <<'EOF'
---
applyTo: "**"
---
BRIDGE-GITHUB-INSTRUCTIONS-MARKER
Apply the sidecar's coding and review skills to every task in this repository.
EOF

# --- hide every sidecar path, and nothing else ---------------------------------
EXCLUDE_FILE="$(git rev-parse --path-format=absolute --git-path info/exclude)"
cat >> "$EXCLUDE_FILE" <<'EOF'
# BEGIN ai-bootstrap sidecar
/.claude/skills/sidecar-marker-a/
/.claude/skills/sidecar-marker-b/
/.agents/skills/sidecar-marker-a/
/.agents/skills/sidecar-marker-b/
/.claude/rules/ai-bootstrap-sidecar.md
/.agents/rules/ai-bootstrap-sidecar.md
/.github/instructions/ai-bootstrap-sidecar.instructions.md
# END ai-bootstrap sidecar
EOF

# --- stage and commit the team files only --------------------------------------
git add CLAUDE.md AGENTS.md .github/copilot-instructions.md \
        .claude/skills/team-claude-skill \
        .agents/skills/team-agents-skill \
        .github/skills/team-github-skill \
        .github/skills/sidecar-marker-b
git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "team fixture"

# --- verify ----------------------------------------------------------------------
FAILED=0
for path in \
  .claude/skills/sidecar-marker-a \
  .claude/skills/sidecar-marker-b \
  .agents/skills/sidecar-marker-a \
  .agents/skills/sidecar-marker-b \
  .claude/rules/ai-bootstrap-sidecar.md \
  .agents/rules/ai-bootstrap-sidecar.md \
  .github/instructions/ai-bootstrap-sidecar.instructions.md
do
  if ! git check-ignore -q -- "$path"; then
    echo "NOT IGNORED: $path" >&2
    FAILED=1
  fi
done

STATUS="$(git status --porcelain --untracked-files=all)"
echo "$STATUS"
if [ -z "$STATUS" ] && [ "$FAILED" -eq 0 ]; then
  echo "FIXTURE OK"
else
  echo "FIXTURE FAILED" >&2
  exit 1
fi
```

After a successful run, `$DIR` holds the fixture repository. Keep it, and
point each client at it for Step 3. Do not delete it until every planned
native run is complete.

### Recipe self-test (done during this phase, no `git commit` run)

The commit-gate hook blocks a `git commit` Bash call from this coding-agent
session, even against a scratch repository, so the commit line above could
not be executed here. Instead, a copy of the block with only the `git commit`
line removed was run in this session's own scratch directory, with `$DIR`
pointed at that scratch directory instead of `$HOME`. Three things were
confirmed directly:

1. The toplevel guard passed: `git rev-parse --show-toplevel` and `pwd -P`
   both resolved to the fixture directory, so the script would have stopped
   if they had not matched.
2. `git status --porcelain --untracked-files=all` listed exactly the seven
   staged team paths as added (`A`) entries (`CLAUDE.md`, `AGENTS.md`,
   `.github/copilot-instructions.md`, the three team skills, and the
   `.github/skills/sidecar-marker-b` collision skill) and no sidecar path —
   the expected result for a run stopped one command short of the commit.
3. `git check-ignore` reported all seven sidecar-owned paths as ignored:
   both marker skills under both `.claude/skills/` and `.agents/skills/`,
   and all three bridge files.

The scratch fixture was deleted after this check. When you run the real
block above, including the commit, `git status --porcelain
--untracked-files=all` will print nothing at all, and the script prints
`FIXTURE OK`.

## Step 3 — operator checklist for running the fixture against each client

This is the procedure used for the 2026-09-25 runs recorded in Step 4, and
for any repeat run. Follow the conventions of `scripts/check_native_clients.py` and
`docs/runtime-checks.md`: use a workspace you trust manually, give explicit
authorization when a client asks, and change no client trust or user
setting. Store no raw transcript — record only the fields listed below.

Host versions on record from the orchestrator's 2026-09-25 check: Claude
Code 2.1.226, `codex-cli` 0.147.0, VS Code 1.139.0 (WSL remote server), Git
2.43.0. The Antigravity CLI (`agy`) is not installed on this host, so an
Antigravity run needs a different machine.

For every client:

1. Open the fixture directory from Step 2 as the workspace root.
2. Paste one prompt that asks the client to list its skills with their
   source folders, and to quote any instruction marker phrase it has loaded.
   For example: "List every skill you can see, including which folder each
   one comes from, and quote any project instruction text you have loaded
   that contains the word MARKER."
3. Where the client offers structured output, capture that instead of
   trusting the model's prose description of itself:
   - Claude Code: run `claude -p --output-format stream-json --verbose` and
     read the `system`/`init` event, which lists loaded skills and slash
     commands.
   - Codex: run `codex exec --json` and read the emitted events for
     instruction-source and skill-selector data (check the current Codex
     docs for the exact event shape at run time, since this changes between
     releases).
   - VS Code: use the chat response's **References** panel, and the request
     inspector described in VS Code's troubleshooting docs, to see which
     instruction files were actually sent.
4. Record, and nothing more:
   - Yes/no for each marker phrase (`TEAM-CLAUDE-MD-MARKER`,
     `TEAM-AGENTS-MD-MARKER`, `TEAM-COPILOT-INSTRUCTIONS-MARKER`,
     `TEAM-CLAUDE-SKILL-REPLY`, `TEAM-AGENTS-SKILL-REPLY`,
     `TEAM-GITHUB-SKILL-REPLY`, `SIDECAR-MARKER-A-CLAUDE`,
     `SIDECAR-MARKER-A-AGENTS`, `SIDECAR-MARKER-B-CLAUDE`,
     `SIDECAR-MARKER-B-AGENTS`, `SIDECAR-MARKER-B-GITHUB-TEAM`,
     `BRIDGE-CLAUDE-RULE-MARKER`, `BRIDGE-AGENTS-RULE-MARKER`,
     `BRIDGE-GITHUB-INSTRUCTIONS-MARKER`).
   - Which skill names and source folders the client's structured output
     (or its references panel) showed.
   - Which `sidecar-marker-b` copy answered when the client was asked to
     invoke it (the `.claude/skills/` copy, the `.agents/skills/` copy, the
     `.github/skills/` team copy, more than one, or none).
   - The client's version string.
   - The session type: for VS Code, record "Local agent" or "Agent Host
     with the Copilot harness" specifically, and also record which
     instruction *format* the Agent Host session used
     (`.github/copilot-instructions.md`/`.github/instructions`, or
     `CLAUDE.md`/`.claude/rules`), because Step 1 found that this changes
     which bridge file actually loads. If a session type does not exist on
     the installed VS Code, record `unavailable`.
   - Today's date.

Google Antigravity needs its own procedure, because a persisted project
would reuse earlier state and invalidate the run
(`docs/runtime-checks.md`, "Google Antigravity evidence boundary"; also
recorded in this project's memory). Run:

```bash
agy --new-project --sandbox
```

Before pasting the prompt, verify the workspace root the CLI reports is a
fresh path, not a path reused from an earlier run. Then repeat the entire
run once more with Strict mode turned on (see `docs/runtime-checks.md`,
"Google Antigravity evidence boundary"), because Step 1 found that only
Strict mode documents respecting `.gitignore`.

## Step 4 — frozen matrix (native runs, 2026-09-25)

All runs used one fixture built with the Step 2 recipe on 2026-09-25. Before
the runs, `git status --porcelain --untracked-files=all` was empty and the
seven sidecar paths were ignored through `info/exclude`. The status was
still empty after the Claude Code and Codex runs. Every sidecar skill and
bridge in the fixture is ignored, so any sidecar file that a client loaded
is also evidence that the client reads Git-ignored files.

How each client was run:

- **Claude Code 2.1.226.** The orchestrator agent ran it with the user's
  authorization, from the fixture root, with a filtered environment:
  `claude -p <prompt> --output-format stream-json --verbose
  --no-session-persistence --tools "" --strict-mcp-config`. With
  `--tools ""` the model has no tool, so it cannot read a file from disk.
  Any marker phrase it quotes must come from context that Claude Code
  loaded. Evidence: the `skills` and `slash_commands` lists in the
  `system`/`init` event, the reply to the Step 3 prompt (zero tool uses),
  and the replies to `/sidecar-marker-b` and `/sidecar-marker-a`.
- **OpenAI Codex, `codex-cli` 0.147.0.** The orchestrator agent ran
  `codex debug prompt-input` from the fixture root. It prints the
  model-visible prompt as JSON and makes no model call. It then ran
  `codex exec --json --ephemeral -s read-only <prompt>`. That run emitted
  zero `command_execution` items, so the reply did not come from reading
  files.
- **GitHub Copilot in VS Code 1.139.0 (built-in Copilot Chat 0.67.0, WSL
  remote).** The operator ran the Step 3 prompts in the chat panel: one
  Local agent session and one Agent Host session with the Copilot harness.
  The Step 3 prompt runs showed no tool steps.
- **Google Antigravity.** `unavailable`: `agy` is not installed on this
  host, and the operator chose not to run it elsewhere for v1.

Only the phrases printed by the clients and the listed skill names were
recorded. No transcript is stored.

| Client | Session type | Skill folders read | Ignored-file discovery | Duplicate-name behavior | `sidecar-marker-b` copy that answered | Bridge path and frontmatter | Evidence tier | Client version | Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | Print mode (`claude -p`) | `.claude/skills/` only. The init event listed `sidecar-marker-a`, `sidecar-marker-b`, and `team-claude-skill`, and not `team-agents-skill` or `team-github-skill`. | Yes: the ignored skills and the ignored rules file loaded. | Not exercised: Claude Code reads one project skill folder. | The `.claude/skills/` copy (`SIDECAR-MARKER-B-CLAUDE`). `/sidecar-marker-a` gave `SIDECAR-MARKER-A-CLAUDE`. | `.claude/rules/ai-bootstrap-sidecar.md` with no frontmatter loaded next to `CLAUDE.md`: the reply quoted `BRIDGE-CLAUDE-RULE-MARKER` and `TEAM-CLAUDE-MD-MARKER` with zero tool uses. It did not quote the `AGENTS.md`, Copilot, or Antigravity markers. | `native-run` | 2.1.226 | 2026-09-25 |
| OpenAI Codex | `codex debug prompt-input`, then `codex exec` | `.agents/skills/` only. The prompt listed `team-agents-skill`, `sidecar-marker-a`, and `sidecar-marker-b`, each at `.agents/skills/<name>/SKILL.md`, and no `.claude/` or `.github/` skill. | Yes: the ignored `.agents/skills/` copies were listed. | Not exercised: the fixture has no duplicate inside Codex's read folders. Documented: both copies appear. | Not invoked. Only the `.agents/skills/` copy is in the prompt. | None, by design (big plan, Decision 7). `AGENTS.md` loaded (`TEAM-AGENTS-MD-MARKER`). No bridge marker appeared, so `.agents/rules/` is not read as instructions. | `native-run` | `codex-cli` 0.147.0 | 2026-09-25 |
| Copilot in VS Code | Local agent | `.agents/skills/`, `.github/skills/`, `.claude/skills/`: all three team skills were listed. | Yes: the ignored skills and both ignored bridge files loaded. | One entry per name. Both sidecar skills were listed once, from `.agents/skills/`. **The `.agents/skills/` sidecar copy hid the team's `.github/skills/sidecar-marker-b`.** | The `.agents/skills/` sidecar copy (`SIDECAR-MARKER-B-AGENTS`). This is a real case of the shadowing that Decision 8 prevents. The `/sidecar-marker-a` reply was not captured. | `.github/instructions/ai-bootstrap-sidecar.instructions.md` with `applyTo: "**"` loaded in a chat with no attached file. `.claude/rules/ai-bootstrap-sidecar.md` also loaded, so this session type sees the bridge text twice. Team `copilot-instructions.md`, `AGENTS.md`, and `CLAUDE.md` stayed active. | `native-run` | VS Code 1.139.0, Copilot Chat 0.67.0 | 2026-09-25 |
| Copilot in VS Code | Agent Host, Copilot harness (Copilot instruction format) | All three project folders: `team-claude-skill`, `team-agents-skill`, `team-github-skill`, `sidecar-marker-a`, and `sidecar-marker-b` were listed as project skills. | Yes: the ignored skills and the ignored `.github/instructions/` bridge loaded. | One entry per name. `/sidecar-marker-a` resolved to the `.agents/skills/` copy (`SIDECAR-MARKER-A-AGENTS`). | Reply `SIDECAR-MARKER-B-GITHUB-TEAM` (the team copy). Weak evidence: before it answered, the agent ran terminal commands and read all three copies. | `.github/instructions/ai-bootstrap-sidecar.instructions.md` with `applyTo: "**"` loaded in a chat with no attached file. `.claude/rules/ai-bootstrap-sidecar.md` did not load. Team `copilot-instructions.md`, `AGENTS.md`, and `CLAUDE.md` stayed active. | `native-run` (the `sidecar-marker-b` cell is weak) | VS Code 1.139.0, Copilot Chat 0.67.0 | 2026-09-25 |
| Google Antigravity | Default mode | Documented only: `.agents/skills/`, legacy `.agent/skills/`. | Not run. | Not run. | Not run. | Candidate `.agents/rules/ai-bootstrap-sidecar.md` with `trigger: always_on` was not run. | `unavailable` | Not installed | 2026-09-25 |
| Google Antigravity | Strict mode | Documented only, as above. | Not run. Documented: Strict mode respects `.gitignore`. | Not run. | Not run. | Not run. | `unavailable` | Not installed | 2026-09-25 |

### Frozen lists for Phases B-D

**Read list** (the folders the collision check scans, big plan Decision 8).
Checking more folders is always safe, so this list may include folders
below `native-run`:

| Folder | Read by | Tier |
| --- | --- | --- |
| `.claude/skills/` | Claude Code; Copilot (both session types) | `native-run` |
| `.agents/skills/` | Codex; Copilot (both session types); Antigravity | `native-run` (Antigravity: `documented`) |
| `.github/skills/` | Copilot (both session types) | `native-run` |
| `.agent/skills/` | Antigravity (legacy) | `documented` |
| `.codex/skills/` | Codex | `source` |

**Write list** (the skill folders the sidecar writes):

| Folder | Native-run evidence |
| --- | --- |
| `.claude/skills/<skill>/` | Claude Code; Copilot (both session types) |
| `.agents/skills/<skill>/` | Codex; Copilot (both session types) |

**Bridges that ship:**

| Client | Path | Frontmatter | Native-run evidence |
| --- | --- | --- | --- |
| Claude Code | `.claude/rules/ai-bootstrap-sidecar.md` | none | Claude Code print mode. Copilot's Local agent also loads it. |
| Copilot in VS Code | `.github/instructions/ai-bootstrap-sidecar.instructions.md` | `applyTo: "**"` | Copilot Local agent and Agent Host (Copilot harness) |

**Not shipped in v1:**

- `.agents/rules/ai-bootstrap-sidecar.md` (Antigravity): no native run
  (Decision 14). Antigravity is unverified for sidecar v1. No tested client
  loaded this file, so leaving it out costs the tested clients nothing.
- A Codex bridge: none exists by design (Decision 7). Codex is skill-only.
- `CLAUDE.local.md`: not needed, because the rules file loaded.

### What the native runs change for later phases

1. **Anti-shadowing is required, not a precaution.** Copilot's Local agent
   let the sidecar's `.agents/skills/sidecar-marker-b` hide the team's
   `.github/skills/sidecar-marker-b`. The sidecar must skip a skill at
   every write root when any read-list folder holds a skill of that name
   that the sidecar does not own (Decision 8). Phase C's test "skill name
   taken only in `.github/skills/`" covers this case.
2. **The two identical sidecar copies are safe.** Both Copilot session types
   listed each sidecar skill once and reported no error. The write list
   stays at two folders.
3. **Copilot's Local agent loads both bridges.** It reads
   `.github/instructions/` and `.claude/rules/`, so the one bridge body
   appears twice in that session type. The text is identical, so this is
   harmless. Document it; no change is needed.
4. **Every client loaded Git-ignored files.** Claude Code, Codex, and both
   Copilot session types loaded skills and bridges that only
   `info/exclude` hides. Antigravity's Strict mode, which documents that it
   respects `.gitignore`, was not tested.
5. **Residual risk: extra frontmatter fields.** The fixture skills used only
   `name` and `description`. The four sidecar skills also carry
   `visibility`, and two carry `license` (plus `argument-hint` on
   `ponytail`). Claude Code documents that it ignores unknown fields. The
   full install already ships these same four skills to `.claude/skills/`
   and `.agents/skills/`. Phase C's optional check, a native client run
   against a real sidecar install, covers the real files.

### Decision gate result

At least one client reached `native-run` evidence, so Phases B-E proceed
(Decision 14). The read list, the two write folders, the Claude Code and
Copilot bridges, and the duplicate-discovery assumption match the big plan.
One thing changed: the Antigravity bridge does not ship, because Antigravity
is `unavailable`. The plan already made that bridge conditional ("if
proven"), so Phases B-D need only a note that the sidecar renders two
bridges, not three.
