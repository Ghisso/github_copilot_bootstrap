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

## Workflow profile evidence

This section is the evidence record for Phase A of the second sidecar plan,
`.claude/plans/sidecar-workflow-profile.md`, small plan
`.claude/plans/2026-09-27_phase-A-workflow-profile-evidence-and-content.md`.
It answers one further question, for the same four clients, about three new
unit kinds the workflow profile wants to ship as Git-ignored files inside a
team-tracked `.claude/`: a custom agent file (Decision 6), several rules
files at once (Decision 5), and one `applyTo: "**"` instructions file
(Decision 5). It reuses the evidence tiers defined above. Everything in the
sections that already exist stays unchanged; this section only adds to them.

### Documented starting point, checked 2026-09-27

| Client | Where a custom agent is discovered | Needs a config entry to discover it? | Do several rules files without `paths`/`applyTo` all load? | Does `applyTo: "**"` load? | Does being Git-ignored change any of this? | Tier | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | `.claude/agents/` (project scope, priority 3 of 5 named locations; discovered by walking up from the working directory) | No. Placing the file is enough; no `settings.json` entry is documented as required for project-scope discovery. | Yes. `.claude/rules/` is scanned recursively for every `.md` file; a rule with no `paths` frontmatter "is loaded at launch with the same priority as `.claude/CLAUDE.md`," with no stated cap on how many such files load. | Not applicable. `applyTo` is a Copilot `.github/instructions/` field; Claude Code reads only `paths` from a rule's frontmatter. | Undocumented for agents and rules specifically. The existing "Documented starting point" section above already found this undocumented for skills too; the earlier native run (Step 4) showed an ignored rule loading, which is evidence, not a documentation claim. | `documented` | `code.claude.com/docs/en/sub-agents`, `code.claude.com/docs/en/memory`, both checked 2026-09-27 |
| OpenAI Codex | `.codex/agents/<name>.toml`. The agent's `name` field, not the filename, is what Codex uses; only `name`, `description`, and `developer_instructions` are required. | Unresolved by documentation. The page's own worked example ships a `.codex/config.toml` with `[agents]` `max_concurrent_threads_per_session = 6` next to three custom agent `.toml` files, but never states that key is required for the agent files to be recognized — it reads as an optional concurrency limit, not a gate. This repository's own generator (`scripts/generate_targets.py`, `render_codex_config`, lines 989-1048) always writes both `[agents]` and `[features.multi_agent_v2]` unconditionally and comments that this is "the MultiAgent V2 routing shim" kept "until trusted native probes prove removal" — this codebase's own state is that the requirement is still unverified, which matches the silence in the vendor page. | Not applicable. Codex does not read `.claude/rules/` at any documented path. | Not applicable. Codex does not read `.github/instructions/`. | Undocumented; carried over from the existing skills section, not re-tested this cycle. | `documented` for the folder and schema; `source` for the config-entry question (this repository's own generator code, not a vendor claim) | `learn.chatgpt.com/docs/agent-configuration/subagents`, checked 2026-09-27; `scripts/generate_targets.py` lines 989-1048, this repository |
| GitHub Copilot in VS Code | `.github/agents/` (workspace default). A Claude-format session instead reads `.claude/agents/`, matching Claude Code's own folder. | No stated config entry for the default workspace folder. (`chat.agentFilesLocations` is documented as "deprecated and only used by the Local agent," and only for *extra* locations, not the default one.) | Yes, for a Claude-format session: the same page that documents `.github/instructions` `applyTo` also says "for `.claude/rules` instructions files, use a `paths` property instead of `applyTo`... `paths` accepts an array of glob patterns and defaults to `**` when omitted," so a rules file with no `paths` loads everywhere, the same as Claude Code, and nothing caps how many such files load. | Yes. `applyTo` is documented as "a glob pattern that automatically applies the instructions to matching files, relative to the workspace root. Use `**` to match all files." | Undocumented. | `documented` | `code.visualstudio.com/docs/copilot/customization/custom-agents`, `code.visualstudio.com/docs/copilot/customization/custom-instructions`, both checked 2026-09-27 |
| Google Antigravity | `.agents/agents/`, per this bootstrap's own generated comment (`scripts/generate_targets.py`, line 1308: "Google Antigravity uses `.agents/agents/`, `.agents/skills/`"). `antigravity.google/docs/agents` returned HTTP 404 today, so no vendor page could be checked for the custom-agent folder; this row is `source`-tier from a local file, not a vendor claim. | Unknown; no vendor page reached. | No, and this is the opposite of Claude Code and Copilot: `antigravity.google/docs/rules` (checked 2026-09-27) states every file in `.agents/rules/` "must start with YAML frontmatter declaring a valid `trigger`," and "if a file... omits frontmatter or specifies an unrecognized `trigger` value... Antigravity silently discards the rule." So a rules file only loads when its frontmatter names a recognized `trigger`, not merely by being present. | Not applicable. Antigravity does not read `.github/instructions/`. | Undocumented for `.agents/rules/`; carried over that Strict mode alone documents respecting `.gitignore`, from the existing skills section above. | `source` for the agent folder (vendor page unreachable); `documented` for the rules-trigger behavior | `antigravity.google/docs/rules`, checked 2026-09-27; agent-folder claim from `scripts/generate_targets.py` line 1308, this repository, not a vendor page |

One vendor claim could not be confirmed: Google Antigravity's dedicated
custom-agent documentation page could not be reached today
(`antigravity.google/docs/agents` returned HTTP 404). The `.agents/agents/`
folder in the table above is this repository's own prior understanding, not
a vendor-confirmed fact, and stays at the `source` tier until a working page
is found or a native run shows the folder in use.

### Questions per client

These are the answers for the three new unit kinds, from documentation and
source code alone, in the style of the existing "Questions Per Client"
section above. Step 3 (native runs) wins where it differs.

**6. Does a client load a custom agent file that Git ignores through
`info/exclude`?**

Undocumented for all four clients. No vendor page states an agent-file
scan skips or includes ignored paths; the existing skills section already
found the same gap for skill folders, and it stays open here.

**7. Do several rules or instructions files, each hidden by a separate
`info/exclude` line, all load together, or does only one win?**

- Claude Code: yes for rules — every `.md` file under `.claude/rules/` is
  scanned, and a file without `paths` loads at `CLAUDE.md` priority; the
  documentation states no limit on how many such files load at once
  (`documented`).
- Copilot in VS Code, Claude-format session: same mechanism, because this
  session type reads `.claude/rules/` with the same `paths`-defaults-to-`**`
  rule (`documented`).
- Copilot in VS Code, Copilot-format session: `.github/instructions/*.instructions.md`
  files are described as additive within one harness in the existing skills
  section above; nothing in today's fetch says two `applyTo: "**"` files
  conflict rather than both firing (`documented` for "additive", not
  independently re-confirmed for exactly two files this cycle).
- Codex: not applicable; no bridge or rules mechanism reads
  `.claude/rules/` or `.github/instructions/`.
- Antigravity: not applicable in the same way — multiple `.agents/rules/`
  files with `trigger: always_on` are each independently injected, but a
  file without a recognized `trigger` is discarded rather than loaded
  (`documented`).

**8. Does a client's custom-agent schema reject or warn about an extra
field the bootstrap might ship?**

- Claude Code: undocumented this cycle; the subagent frontmatter fields
  fetched today (`description`, `tools`, model fields, hook fields) did not
  include a statement about an unrecognized field.
- Codex: no. The custom agent file schema names `name`, `description`, and
  `developer_instructions` as required, and separately allows "other
  supported `config.toml` keys... such as `model`, `model_reasoning_effort`,
  `sandbox_mode`, `mcp_servers`, and `skills.config`" — an unsupported key's
  handling is not stated (`documented` for the allowed-keys list;
  undocumented for an unsupported one).
- Copilot in VS Code and Antigravity: not found in today's fetch, carried
  over as undocumented from the existing skills section's answer to
  Question 5.

### Fixture recipe

This is a second, separate throwaway repository from the one in "Step 2 —
the fixture recipe" above. That fixture proves skill and bridge discovery;
this one proves agent, multi-rule, and instructions discovery, plus the
Codex config-free case. Keep both fixtures until every native run in the
next section is complete.

**Run this in your own shell, not through an agent session**, for the same
reason as the recipe above: this repository's commit-gate hook blocks a
`git commit` a coding-agent session runs through its own tool calls, even
in a different, throwaway repository. Save the block to a file and run it
with `bash`; do not paste it into an interactive shell, because its `set -e`
and `exit 1` lines would close that shell on the first error.

```bash
set -euo pipefail

DIR="$HOME/sidecar-workflow-fixture-$(date +%Y%m%d-%H%M%S)"
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
mkdir -p .claude/skills/team-skill .claude/agents .claude/rules .github/instructions

cat > .claude/settings.json <<'EOF'
{
  "outputStyle": "concise"
}
EOF

cat > .claude/skills/team-skill/SKILL.md <<'EOF'
---
name: team-skill
description: Team-owned skill tracked for the workflow-profile fixture.
---
If asked to identify yourself, reply exactly: TEAM-SKILL-REPLY
EOF

cat > .claude/agents/team-agent.md <<'EOF'
---
name: team-agent
description: Team-owned subagent tracked for the workflow-profile fixture. Use it when asked to identify the team agent.
---
If invoked, reply exactly: TEAM-AGENT-REPLY
EOF

cat > .claude/rules/team.md <<'EOF'
TEAM-RULE-OK
EOF

cat > .github/instructions/team.instructions.md <<'EOF'
---
applyTo: "**"
---
TEAM-INSTRUCTIONS-OK
EOF

mkdir -p src
cat > src/hello.py <<'EOF'
def hello() -> str:
    """Return a fixed greeting for the workflow-profile fixture."""
    return "hello from the workflow-profile fixture"
EOF

# --- sidecar-owned files: untracked, must end up Git-ignored -------------------
mkdir -p .github/agents .codex/agents

cat > .claude/agents/probe-agent.md <<'EOF'
---
name: probe-agent
description: Sidecar probe subagent for the workflow-profile fixture. Use it when asked to identify the probe agent.
---
If invoked, reply exactly: WORKFLOW-PROBE-AGENT-OK
EOF

cat > .claude/rules/ai-bootstrap-a.md <<'EOF'
WORKFLOW-RULE-A-OK
EOF

cat > .claude/rules/ai-bootstrap-b.md <<'EOF'
WORKFLOW-RULE-B-OK
EOF

cat > .github/agents/probe-agent.agent.md <<'EOF'
---
name: probe-agent
description: Sidecar probe subagent for the workflow-profile fixture. Use it when asked to identify the probe agent.
---
If invoked, reply exactly: WORKFLOW-PROBE-AGENT-OK
EOF

cat > .github/instructions/ai-bootstrap-workflow.instructions.md <<'EOF'
---
applyTo: "**"
---
WORKFLOW-INSTRUCTIONS-OK
EOF

cat > .codex/agents/probe-agent.toml <<'EOF'
name = "probe_agent"
description = "Sidecar probe subagent for the workflow-profile fixture."
developer_instructions = "If invoked, reply exactly: WORKFLOW-PROBE-AGENT-OK"
EOF

# --- hide every sidecar path, and nothing else ---------------------------------
EXCLUDE_FILE="$(git rev-parse --path-format=absolute --git-path info/exclude)"
cat >> "$EXCLUDE_FILE" <<'EOF'
# BEGIN ai-bootstrap sidecar
/.claude/agents/probe-agent.md
/.claude/rules/ai-bootstrap-a.md
/.claude/rules/ai-bootstrap-b.md
/.github/agents/probe-agent.agent.md
/.github/instructions/ai-bootstrap-workflow.instructions.md
/.codex/agents/probe-agent.toml
# END ai-bootstrap sidecar
EOF

# --- stage and commit the team files only --------------------------------------
git add .claude/settings.json .claude/skills/team-skill .claude/agents/team-agent.md \
        .claude/rules/team.md .github/instructions/team.instructions.md src/hello.py
git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "team fixture"

# --- verify ----------------------------------------------------------------------
FAILED=0
for path in \
  .claude/agents/probe-agent.md \
  .claude/rules/ai-bootstrap-a.md \
  .claude/rules/ai-bootstrap-b.md \
  .github/agents/probe-agent.agent.md \
  .github/instructions/ai-bootstrap-workflow.instructions.md \
  .codex/agents/probe-agent.toml
do
  if ! git check-ignore -q -- "$path"; then
    echo "NOT IGNORED: $path" >&2
    FAILED=1
  fi
done

if [ -e .codex/config.toml ]; then
  echo "NOT EXPECTED: .codex/config.toml exists" >&2
  FAILED=1
fi

STATUS="$(git status --porcelain --untracked-files=all)"
echo "$STATUS"
if [ -z "$STATUS" ] && [ "$FAILED" -eq 0 ]; then
  echo "FIXTURE OK"
else
  echo "FIXTURE FAILED" >&2
  exit 1
fi
```

After a successful run, `$DIR` holds the fixture repository, with no
`.codex/config.toml` present anywhere in it, by design: the fixture tests
whether Codex discovers `.codex/agents/probe-agent.toml` with no config
file at all. Keep it, next to the skills-profile fixture, until every
planned native run in the next section is complete.

### Operator checklist

For every client, follow the same conventions as "Step 3 — operator
checklist" above: use a workspace you trust manually, give explicit
authorization when a client asks, change no client trust or user setting,
and store no raw transcript — record only the fields listed below.

For every client, record:

- Whether `probe-agent` is listed as an available agent or subagent, and
  whether invoking it replies `WORKFLOW-PROBE-AGENT-OK`.
- Whether both `WORKFLOW-RULE-A-OK` and `WORKFLOW-RULE-B-OK` appear
  (Claude Code and a Claude-format Copilot session), or whether
  `WORKFLOW-INSTRUCTIONS-OK` appears (a Copilot-format session).
- Whether `team-agent` still replies `TEAM-AGENT-REPLY`, `team-skill` still
  replies `TEAM-SKILL-REPLY`, and `TEAM-RULE-OK` or
  `TEAM-INSTRUCTIONS-OK` still appears alongside the sidecar markers.
- The client's version string and today's date.

**Claude Code.** From the fixture root:

```bash
claude -p "List every subagent you can see, including its source folder, and quote any rule text you have loaded that contains the text WORKFLOW or TEAM." \
  --output-format stream-json --verbose --no-session-persistence --tools "" --strict-mcp-config
```

Then, to force an invocation of each named agent directly:

```bash
claude -p --agent probe-agent "Identify yourself." --output-format stream-json --verbose --no-session-persistence --tools "" --strict-mcp-config
claude -p --agent team-agent "Identify yourself." --output-format stream-json --verbose --no-session-persistence --tools "" --strict-mcp-config
```

Read the `system`/`init` event for the listed subagents, and the reply text
for the marker tokens, the same way Step 4 above reads it for skills.

**OpenAI Codex.** From the fixture root:

```bash
codex debug prompt-input
codex exec --json --ephemeral -s read-only "List every custom agent you can see and quote any developer instructions containing the text WORKFLOW or TEAM."
```

`codex debug prompt-input` prints the model-visible prompt as JSON with no
model call, which shows whether `probe-agent` and `team-agent` are in the
agent registry before any reply is trusted. Then, to force an invocation:

```bash
codex exec --json --ephemeral -s read-only --agent probe_agent "Identify yourself."
codex exec --json --ephemeral -s read-only --agent team_agent "Identify yourself."
```

Check the exact current flag name for selecting an agent in the installed
Codex CLI version's `--help` output before running these, since Codex
agent-selection flags can change between releases.

**GitHub Copilot in VS Code.**

1. Open the fixture directory as the workspace root.
2. Open the chat panel, and confirm the session type (Local agent, or
   Agent Host with the Copilot or Claude harness), the same way Step 3
   above records it.
3. Open the Agents dropdown and confirm `probe-agent` and `team-agent`
   appear; select `probe-agent` and ask it to identify itself; repeat for
   `team-agent`.
4. Ask, in the same or a new chat: "Quote any instruction text you have
   loaded that contains the text WORKFLOW or TEAM."
5. Use the chat response's **References** panel to see which instruction
   and agent files were actually sent, the way Step 3 above does for
   skills.
6. Record which format the session used (`.github/agents` and
   `.github/instructions`, or `.claude/agents` and `.claude/rules`), because
   the documented starting point above found this changes which files load.

**Google Antigravity.** Unavailable on this host: `agy` is not installed
(carried over from Step 3 above). Record `unavailable` for every workflow
unit kind unless a run happens on a different machine, in which case follow
the same `agy --new-project --sandbox` procedure as Step 3 above, once in
default mode and once in Strict mode, and record the same fields listed at
the top of this checklist.

### Frozen matrix (native runs, 2026-09-27)

The orchestrator fills this table after running the fixture above against
each installed client. Until then, every cell reads `pending`.

| Client | Session type | Agent (`probe-agent`) | Rules (`ai-bootstrap-a`/`-b`, or Claude-format Copilot) | Instructions (`ai-bootstrap-workflow`, Copilot-format) | Team unit still works | Client version | Date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude Code | Print mode (`claude -p`, `--model claude-haiku-4-5-20251001` because 2.1.226 refuses the default model) | `native-run`: the `system`/`init` event lists `probe-agent` beside `team-agent`, and delegation returned the probe token | `native-run`: both ignored rule tokens and the team rule token in one answer | not applicable | `native-run`: team rule and team agent both answered | 2.1.226 | 2026-09-27 |
| OpenAI Codex | `codex exec --skip-git-repo-check --sandbox read-only`, with and without `-c features.multi_agent_v2=true` | `native-run`, negative: the agent listing answered `NONE` with no `.codex/config.toml`, so `.codex/agents/*.toml` is not discovered config-free | not applicable | not applicable | not applicable (Codex reads only `AGENTS.md`; no instruction token appeared, as expected) | codex-cli 0.147.0 | 2026-09-27 |
| Copilot in VS Code | Local agent | unverified: the operator could not run Copilot on 2026-09-27 | unverified | not run for the workflow file; the same unit kind (`.github/instructions/*.instructions.md`, `applyTo: "**"`) is `native-run` for the skills-profile bridge in Step 4 above (2026-09-25) | unverified | 1.139.1 host, session not run | 2026-09-27 |
| Copilot in VS Code | Agent Host, Copilot harness | unverified | not applicable | as above | unverified | not run | 2026-09-27 |
| Copilot in VS Code | Agent Host, Claude harness | unverified | unverified | not applicable | unverified | not run | 2026-09-27 |
| Google Antigravity | Default mode | unverified: no client on this host | unverified | not applicable | unverified | not installed | 2026-09-27 |
| Google Antigravity | Strict mode | unverified: no client on this host | unverified | not applicable | unverified | not installed | 2026-09-27 |

An `unverified` cell is not a support claim. The profile ships a unit kind
to a client only from a `native-run` cell, so Copilot receives no agent
file from the workflow profile until this fixture is run against it; the
Copilot instructions file ships on the 2026-09-25 evidence for its unit
kind. Rerunning the operator checklist above against Copilot and filling
these rows is the only step needed to add Copilot agents later.

### Decision gate result, 2026-09-27

The gate passes. Claude Code 2.1.226 loaded both ignored rule files and
discovered and ran the ignored agent file from a repository whose
`.claude/` is team-tracked, which is the condition the big plan sets for
the profile to have a client. The profile therefore ships agents, rules,
review profiles, templates, skills, and the state folder for Claude Code;
the instructions file and skills for Copilot in VS Code; and skills and
the state folder for Codex. Antigravity receives nothing new until a
native run exists.

**Frozen write roots, read roots, and client coverage** (candidate rows
from the big plan's Decision 9; each stays a candidate until a native run
confirms or drops it):

| Write root | Unit kind | Candidate client coverage | Status |
| --- | --- | --- | --- |
| `.claude/agents` | agent | Claude Code (`native-run` 2026-09-27); Copilot unverified | frozen write root; joins the read list for collision checks |
| `.claude/rules` | rules (several files) | Claude Code (`native-run` 2026-09-27); Copilot unverified | frozen write root; joins the read list |
| `.claude/review-profiles` | single file | not a client-discovery path; read by the agents the profile ships | frozen write root; joins the read list |
| `.claude/templates` | single file | not a client-discovery path; read by the agents the profile ships | frozen write root; joins the read list |
| `.github/agents` | agent | none yet: Copilot unverified on 2026-09-27 | not a write root in this profile version; joins the read list so a team agent there still takes the name; add it when the Copilot rows above become `native-run` |
| `.github/instructions` | instructions | Copilot, on the 2026-09-25 `native-run` for the same unit kind (the skills-profile bridge) | frozen write root (existing bridge parent); ships the workflow instructions file |
| `.codex/agents` | agent | none | dropped: Codex 0.147.0 discovers no `.codex/agents/*.toml` without a `.codex/config.toml` entry, and the sidecar never writes a file the team may track (Decision 7); Codex gets skills and state only |
| state folder (`.claude/ai-bootstrap/`) | state | not a client-discovery path; created by the installer, read by the agents the profile ships | frozen; hidden by one exclude line |

Read roots for collision checks, frozen 2026-09-27: every write root above,
plus today's skill read roots (`.github/skills`, `.agent/skills`,
`.codex/skills`) for skills, and `.codex/agents` and `.agents/agents` for
agents, so a team agent at any of those paths takes the sidecar's agent of
the same name even where the sidecar does not write.

## Workflow state write gate, 2026-10-02

The 2026-09-27 matrix above only proves that clients *load* files from
ignored paths. It never tests whether a client can *write* to one. This
section is a separate gate for writes, run before any production code
change.

### Why this gate exists

The 2026-10-02 hands-on review
(`.claude/explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md`,
finding 1) found that Claude Code refuses to write under
`.claude/ai-bootstrap/`. It treats the path as "a sensitive file" and
blocks the write even with `--permission-mode acceptEdits` and an
`Edit(...)` allow rule. The repair plan proposes moving sidecar state out
of `.claude/` entirely, to a new hidden folder at the repository root,
`.ai-bootstrap/`. Before changing any installer or template code, this gate
tests whether that new root actually accepts the writes the workflow needs.

This supersedes the row above, "state folder (`.claude/ai-bootstrap/`) ...
frozen", for future releases. That row is left as written; it is historical
evidence of the old root, not a current recommendation.

### Reproducible recipe

Two scripts build the fixture and run the probe. Run the fixture build
first, from the bootstrap repository root, with one argument: an empty
throwaway directory. Then run the probe script yourself, in your own shell.
The orchestrating agent could not start the probe directly: on 2026-10-02
the agent session's auto-mode safety classifier denied starting a nested
`claude -p` call from an agent tool call, so the user ran it instead.

The probe script looks for the fixture at `fixture-write-gate/` in its own
directory. So save both scripts in one directory, and pass
`<that directory>/fixture-write-gate` as the build script's argument. The
build script writes its snapshot files (`snap-*.txt`) next to the fixture.

```bash
#!/usr/bin/env bash
# Exact fixture build used for the 2026-10-02 write gate (run from the
# bootstrap repository root). Team files are staged, not committed, because
# this repository's commit-gate hook blocks agent-run commits in any repo.
set -euo pipefail
F="$1"   # empty throwaway directory, no remote
test ! -e "$F" || { echo "refusing: $F exists" >&2; exit 1; }
mkdir -p "$F" && cd "$F" && git init -q
mkdir -p .claude/rules src
printf '{\n  "outputStyle": "concise"\n}\n' > .claude/settings.json
printf 'TEAM-RULE-OK\n' > .claude/rules/team.md
cat > src/hello.py <<'EOF'
def hello() -> str:
    """Return a fixed greeting for the write-gate fixture."""
    return "hello from the write-gate fixture"
EOF
git add .claude/settings.json .claude/rules/team.md src/hello.py
cd - >/dev/null
uv run python scripts/install_bootstrap.py "$F" --mode sidecar --profile workflow
cd "$F"
# Fixture-only candidate root: copy seeded state, repoint installed copies.
cp -a .claude/ai-bootstrap .ai-bootstrap
grep -rl --exclude-dir=.git --exclude-dir=.ai-bootstrap --exclude-dir=ai-bootstrap \
  '\.claude/ai-bootstrap' . | xargs sed -i 's#\.claude/ai-bootstrap#.ai-bootstrap#g'
printf '/.ai-bootstrap\n' >> "$(git rev-parse --path-format=absolute --git-path info/exclude)"
git check-ignore -q .ai-bootstrap/MEMORY.md
git ls-files -s | sha256sum > ../snap-index.txt
sha256sum .claude/settings.json .claude/rules/team.md src/hello.py > ../snap-team.txt
git status --porcelain --untracked-files=all > ../snap-status.txt
```

The fixture is a real sidecar-workflow install from current `dev`. Only the
12 files it installed that referenced the old root
(`.claude/ai-bootstrap/`) were repointed to the candidate root
(`.ai-bootstrap/`), and only inside the throwaway fixture. No production
source and no `dist/` file was changed.

```bash
#!/usr/bin/env bash
# Phase A native write-gate probe (sidecar-workflow-repair).
# Run this yourself, in your own shell:  bash run-write-gate-probe.sh
# It starts two Claude Code print-mode sessions inside the throwaway fixture.
# It uses ordinary permissions (acceptEdits), changes no settings, and gives
# the sessions no shell tool, so every file must come from native Write/Edit.
set -uo pipefail

S="$(cd "$(dirname "$0")" && pwd)"
F="$S/fixture-write-gate"
cd "$F" || { echo "fixture missing: $F" >&2; exit 1; }

echo "claude version: $(claude --version)"
echo "working dir: $(pwd)"

# Step 2: direct writes by the main session.
claude -p --model sonnet --permission-mode acceptEdits \
  --tools Read,Write,Edit \
  --output-format stream-json --verbose --no-session-persistence --strict-mcp-config \
  "This is a write-permission probe. Use only the Write and Edit tools; do not ask questions. Do these in order and keep going even if one is refused:
1. Write .ai-bootstrap/plans/probe-plan.md with exactly the line: PROBE-PLAN-CREATED
2. Write .ai-bootstrap/session_logs/probe-log.md with exactly the line: PROBE-LOG-CREATED
3. Write .ai-bootstrap/quality_reports/probe-report.md with exactly the line: PROBE-REPORT-CREATED
4. Write .ai-bootstrap/explorations/probe-exploration.md with exactly the line: PROBE-EXPLORATION-CREATED
5. Edit each of the four files above, replacing CREATED with EDITED.
6. Edit .ai-bootstrap/MEMORY.md: append a new final line: PROBE-MEMORY-EDITED
7. Control A: Write .claude/ai-bootstrap/plans/control-old-root.md with exactly the line: CONTROL-OLD-ROOT
8. Control B: Write notes-probe.md with exactly the line: CONTROL-ROOT-FILE
Finally, list each step with OK or REFUSED." \
  > "$S/probe-direct.jsonl" 2> "$S/probe-direct.err"
echo "step 2 exit=$?"

# Step 3: delegated work through the installed workflow agents.
claude -p --model sonnet --permission-mode acceptEdits \
  --tools Read,Write,Edit,Grep,Glob,Agent \
  --output-format stream-json --verbose --no-session-persistence --strict-mcp-config \
  "Follow the workflow rule in .claude/rules/ai-bootstrap-workflow.md for this small task, and do not ask questions.
Task: in src/hello.py, add a module docstring and change the greeting text to \"hello from the repaired fixture\". Change no other source file.
Required steps, in order:
1. Delegate planning to the planner subagent. Save the plan it produces to .ai-bootstrap/plans/hello-greeting.md. If the planner cannot save the file itself, save its returned text yourself with Write.
2. Delegate the edit to the coder subagent. Tell it to use only Edit or Write, not a shell.
3. Delegate review to the reviewer subagent. Give it this exact diff text for src/hello.py, which you build from the before and after contents. Save its report to .ai-bootstrap/quality_reports/hello-greeting-review.md. If the reviewer cannot save the file itself, save its returned text yourself with Write.
4. Delegate to the documenter subagent: tell it to write .ai-bootstrap/session_logs/hello-greeting.md with a three-line summary of the task, using its own Write tool.
5. Yourself: append a final line to .ai-bootstrap/MEMORY.md: PROBE-DELEGATED-MEMORY-EDITED
Finally, for each step say which agent wrote which file, or what was refused." \
  > "$S/probe-delegated.jsonl" 2> "$S/probe-delegated.err"
echo "step 3 exit=$?"
echo "done; tell the orchestrator session to inspect the results"
```

Results were checked outside the model: parsing the `stream-json` output's
`tool_use`/`tool_result` events and the final `permission_denials` list,
then independently reading the actual file contents on disk, the Git index
hash, the team-file hashes, and `git status`.

### Evidence table, 2026-10-02

Client: Claude Code 2.1.226, print mode, `--model sonnet` (the `init` event
reported model `claude-sonnet-5`), `--permission-mode acceptEdits`,
`--no-session-persistence --strict-mcp-config`. No settings change and no
permission bypass.

| Check | Tools available | Result |
| --- | --- | --- |
| Direct writes at `.ai-bootstrap/` (plans, session_logs, quality_reports, explorations) | `Read,Write,Edit` | native-run pass: Write then Edit succeeded for all four marker files; each reads `PROBE-*-EDITED` on disk; no approval needed |
| Direct edit of `.ai-bootstrap/MEMORY.md` | `Read,Write,Edit` | native-run pass: file ends with `PROBE-MEMORY-EDITED` |
| Control A, write `.claude/ai-bootstrap/plans/control-old-root.md` | `Read,Write,Edit` | reproduces the known defect: refused as "a sensitive file", listed in `permission_denials`; file absent on disk |
| Control B, write `notes-probe.md` at the fixture root | `Read,Write,Edit` | written successfully, then removed before the status comparison; rules out a general Write denial |
| Delegated run: planner, coder, reviewer, documenter subagents | `Read,Write,Edit,Grep,Glob,Agent` (listed as tool `Task` in the `init` event; agents include coder, documenter, orchestrator, planner, reviewer) | native-run pass overall, `permission_denials` empty; see breakdown below |

Delegation was confirmed by `Agent` tool_use events and subagent events
carrying `parent_tool_use_id`, not by reply text claiming a role.

Delegated-run breakdown:

- **planner** subagent: read `.claude/templates/plan-small.md` and
  `.ai-bootstrap/MEMORY.md`, then returned plan text. It has no Write or
  Edit tool, so the main session saved the result to
  `.ai-bootstrap/plans/hello-greeting.md` (58 lines, small-plan
  frontmatter).
- **coder** subagent: made the only allowed source change, a native Edit of
  `src/hello.py`.
- **reviewer** subagent (`Read,Grep,Glob` only): read
  `.claude/review-profiles/code.md` and returned a Markdown report (PASS,
  one minor note); the main session saved it to
  `.ai-bootstrap/quality_reports/hello-greeting-review.md`.
- **documenter** subagent: wrote
  `.ai-bootstrap/session_logs/hello-greeting.md` with its own Write tool —
  a delegated write at the new root, not a main-session save.
- **main session**: Edit appended `PROBE-DELEGATED-MEMORY-EDITED` to
  `.ai-bootstrap/MEMORY.md`.

The old root, `.claude/ai-bootstrap/`, held only its five originally seeded
files after both sessions; nothing new was written there.

Integrity: `.claude/settings.json` and `.claude/rules/team.md` hashes stayed
unchanged; the Git index hash stayed unchanged; `git status` differed from
the pre-probe snapshot only by `AM src/hello.py`, the intended task edit.

### Capabilities recorded separately

| Capability | Result |
| --- | --- |
| Discovery (agents listed in the `init` event) | native-run pass |
| Direct writing at `.ai-bootstrap/` | native-run pass |
| Delegated writing at `.ai-bootstrap/` | native-run pass for the coder and documenter subagents, which have a write tool; the planner and reviewer have no write tool by design, so the main session saves their output |

### Side finding, carried into Phase B

The shipped sidecar `planner` and `reviewer` prompts tell those agents to
save their own plan or report, but their tool lists — rendered from the
shared `shared/agents/{planner,reviewer}/agent.yaml` capabilities, the same
list the full install uses — give neither agent a file-write tool. Decision
(user, 2026-10-02): "caller saves" — the planner and reviewer return text,
and the requesting agent saves it, matching how the full install's
read-only reviewer already works.

### Unverified

Copilot in VS Code, Codex, and Antigravity were not run for this gate; they
stay unverified. Do not expand any support claim beyond Claude Code on this
evidence. An interactive, non-print session was also not tested.

### Decision gate result, 2026-10-02

Pass, for Claude Code. Phase B may relocate sidecar state to
`.ai-bootstrap/`.
