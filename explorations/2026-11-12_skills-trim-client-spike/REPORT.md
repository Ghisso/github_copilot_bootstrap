# Pre-branch client spike: skills-and-instructions-trim

**Date:** 2026-11-13 (UTC run times 11:53)
**Plan:** `.claude/plans/skills-and-instructions-trim.md` (Pre-branch evidence spike)
**Method:** `.claude/skills/integration-gate-spike/SKILL.md`. Evidence only: no repository edit except this file, no generator or installer run, no `git commit`, no edit to `~/.codex/` or `~/.claude/`.

## Environment

| Item | Value |
|---|---|
| Codex CLI | `codex-cli 0.147.0` (`codex debug prompt-input` makes no model call) |
| Claude Code | `2.1.226 (Claude Code)`; S5 runs used `model=claude-opus-5[1m]` (debug log) |
| Source bundle | `dist/multi-agent/` as present on `dev` at `cfde280` (55 skills in `.claude/skills/` and `.agents/skills/`; 55 `[[skills.config]]` entries) |
| Spike folder | a fresh `mktemp -d` folder in the session scratchpad, outside the checkout |
| Personal skills | `~/.claude/skills`: `opik`, `opik-compare`, `opik-diagnose`, `opik-evaluate`, `opik-explain`, `opik-instrument`, `opik-online-eval`, `opik-optimize`, `opik-test`, `opik-verify`, `synced`. `~/.agents/skills`: the same ten `opik*` folders. |

Tree rules followed: each tree held only `AGENTS.md`, the skill folders, and a `.codex/config.toml` with every `[mcp_servers.*]` table stripped (0 `mcp_servers` lines left, 0 `hooks.json` files). Codex ran with an isolated `HOME` and `CODEX_HOME`; the trusted home listed the three trees as trusted, the untrusted home had an empty config. Every client call had a `timeout`. Tool scripts ran with `python3 -I`. Each probe ran once, except S5, which ran twice (the `--bare` attempt and its fallback).

## Results

### S1: does Codex list the shipped skills, and from where?

Parsed from the `## Skills` section of the rendered prompt. Codex prints a root table (`r0` = `$CODEX_HOME/skills/.system`, `r1` = `<tree>/.agents/skills`) and lists each entry as `- <name>: <description> (file: rN/<name>/SKILL.md)`.

| Run | Exit | Entries | Unique names | Listed twice | Source folders |
|---|---|---|---|---|---|
| `s1-trusted` (full tree, trusted home) | 0 | 60 | 60 | none | 55 from `r1` (`.agents/skills`), 5 Codex system skills from `r0` |
| `s1-untrusted` (full tree, empty home config) | 0 | 60 | 60 | none | same as trusted |
| `s1-config-only` (no `.agents/`, 55 `[[skills.config]]` entries pointing at `../.claude/skills/`) | 0 | 5 | 5 | none | only the 5 system skills |

The 55 `r1` names equal the 55 folder names in `dist/multi-agent/.agents/skills/` exactly.

Every `.err` file holds one line, the same harmless warning, then `exit 0`:
`WARNING: proceeding, even though we could not create PATH aliases: Refusing to create helper binaries under temporary dir "/tmp" ...`

Sample entries (verbatim, `s1-trusted`, cut at 260 characters here):

```text
- imagegen: Generate or edit raster images when the task benefits from AI-created bitmap visuals such as photos, illustrations, textures, sprites, mockups, or transparent-background cutouts. Use when Codex should create a brand-new image, transform an existing
- openai-docs: Use for Codex models/pricing, scheduled tasks, skills, settings, setup, troubleshooting, customization, automations, and self-knowledge—including 'you,' 'your,' 'this app,' or 'this coding agent' when they refer to Codex—and for OpenAI APIs/
- skill-creator: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Codex's capabilities with specialized knowledge, workflows, or tool integrations. (file: r0/skill-c
```

**Outcome:** Success, first S1 row. Every shipped skill is listed once, from `.agents/skills/`; the config-only run lists none of them. The `[[skills.config]]` entries add no skill on their own, and project trust does not change the listing. Plan change: none before the branch. Phase C Step 5 corrects the false comment in `render_codex_config` (`scripts/generate_targets.py:1024`, "Skills are sourced from the shared .claude basis; project trust is required."). Removing the inert entries is a user follow-up.

### S3: how Codex shows a long description

- `integration-gate-spike` (891-character source description) is shown cut to 404 characters, mid-word: `... Triggers: - "We need to integrate with API X, but don't know the exact contr (file: r1/integration-gate-spike/SKILL.md)`.
- No omitted-skill warning appears in the prompt JSON or in stderr.
- With 60 skills, the longest shown description is 404 characters, and 20 entries are 390 characters or more. With only 5 skills (`s1-config-only`), `imagegen` is shown at 570 characters instead of 394. Codex therefore shortens descriptions more when more skills are listed. A 300-character cap keeps every shipped description whole in this listing.

### S4: does Codex list a project skill placed in `.agents/skills/`?

`s4` (full tree plus `.agents/skills/spike-project-skill/SKILL.md`), exit 0: 61 entries, 61 unique names, none listed twice. `spike-project-skill` is listed once from `r1/spike-project-skill/SKILL.md` with its 88-character description.

**Outcome:** Success, expected row. Phase A's mirror to `.agents/skills/<name>/` is what Codex reads.

### S5: Claude Code skill-listing budget

`--bare` was tried first. All three runs exited 1 with `Not logged in · Please run /login`, because `--bare` reads only `ANTHROPIC_API_KEY` (not set) and never OAuth. The three runs were repeated with `--setting-sources project` in place of `--bare`, from an empty working folder with no settings and no `CLAUDE.md`. All three exited 0 and replied `OK`.

| Run | Skills from `--add-dir` | Skills sent | Listing warning |
|---|---|---|---|
| control (`claude-before`, `SLASH_COMMAND_TOOL_CHAR_BUDGET=1000`) | 55 | 69 | yes (below) |
| before (`claude-before`, 55 shipped skills) | 55 | 69 | none |
| after (`claude-after`: 35 kept skills, listing text cut to 300 characters, Ponytail unchanged, plus 2 placeholders at 280 characters) | 37 | 51 | none |

Positive-control warning text (exact):

```text
[WARN] Skill listing over budget: 69 skills, 25999 chars > 1000 budget — descriptions will be truncated. Run /skills to disable some, or raise skillListingBudgetFraction in settings.
```

The debug log reports the loaded set as `Loaded 55 unique skills (55 unconditional, 0 conditional, managed: 0, user: 0, project: 0, additional: 55, legacy commands: 0)`. With `--setting-sources project`, the personal `opik*` skills were not loaded (`user: 0`), unlike the plan's expectation. The listing therefore held the shipped skills plus 14 built-in entries.

**Outcome:** Working control, and the baseline also shows no warning. There is no overflow in this environment today with the shipped skills alone. Record it; the 300-character cap stands for size. Phase C's Optional Verification greps for `Skill listing over budget`.

## Exit codes

| File | Last line |
|---|---|
| `s1-trusted.json.err`, `s1-untrusted.json.err`, `s1-config-only.json.err`, `s4.json.err` | `exit 0` |
| `s1-*.entries`, `s4.entries` (parser) | `exit 0` |
| `s5-bare-control.log.out`, `s5-bare-before.log.out`, `s5-bare-after.log.out` | `exit 1` (`Not logged in`) |
| `s5-proj-control.log.out`, `s5-proj-before.log.out`, `s5-proj-after.log.out` | `exit 0` |

## Decisions applied

| Check | Row | Plan change | Implementation may continue |
|---|---|---|---|
| S1 | Success, listed once from `.agents/skills/`, config-only lists none | none before the branch; Phase C Step 5 rewrites the comment | yes |
| S3 | record only | none | yes |
| S4 | Success, listed once | none | yes |
| S5 | Working control; baseline shows no warning (fallback mode `--setting-sources project`) | none; the cap stands | yes |
