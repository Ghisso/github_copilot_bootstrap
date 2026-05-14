---
name: designer
description: "Design and UX specialist for Python interfaces, with focus on Gradio and Streamlit apps. Produces clear, usable, and maintainable UI updates aligned with project conventions. Invoked by orchestrator for UI-focused tasks."
model: Claude Sonnet 4.6
tools:
	- edit
	- execute
	- read
	- search
user-invocable: false
---

# designer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/designer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
