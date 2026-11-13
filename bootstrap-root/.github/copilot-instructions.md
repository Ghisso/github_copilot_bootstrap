# GitHub Copilot Workspace Adapter

This target is generated from `shared/`. Do not edit generated files manually.

`.claude/` is the canonical shared project space for all AI systems in this repo. Use it for skills, plans, explorations, session logs, quality reports, memory, templates, prompts, shared agent bodies, and hook scripts.

Native Copilot files under `.github/` are adapters:

- `.github/instructions/*.instructions.md` preserves Copilot discovery and points to `.claude/instructions/`.
- `.github/agents/*.agent.md` preserves Copilot agent metadata and points to `.claude/agents/`.
- `.github/hooks/hooks.json` invokes shared hook scripts in `.claude/hooks/scripts/`.

Classify each request with the Task Lanes table in `.claude/instructions/workflow.instructions.md`, and read other files in `.claude/instructions/` only when the task needs them. Before every coding action, load `.claude/skills/ponytail/SKILL.md` in `full` mode.

Preserve the lifecycle `PRE-FLIGHT -> BRANCH -> PLAN WHEN NEEDED -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH`, and follow `.claude/instructions/closeout.instructions.md` before commit. Write all plans, session logs, exploration notes, memory updates, and quality reports under `.claude/`, not target-local `.github/` or `.codex/` state directories.

Follow `.claude/instructions/agent-reporting.instructions.md` for human-facing communication. For every user-facing message, use clear, direct language with short sentences and common precise words. Avoid unnecessary jargon, buzzwords, and idioms. Define uncommon terms when needed, retain precise technical terms, and do not use `caveman full` with the user.
