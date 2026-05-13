# Semble + context-mode integration plan

**Date:** 2026-05-13
**Scope:** Integrate Semble and context-mode into this bootstrap without replacing the existing workflow, hooks, skills, or quality gates.

## Goal and constraints

### Goal

Add Semble and context-mode as first-class, optional retrieval/runtime helpers for VS Code Copilot while preserving the bootstrap's current plan/verify/review/score loop, hook guardrails, and skill structure.

### Grounded current state

- `.vscode/mcp.json` already exists and currently registers `semble` via `uvx --from "semble[mcp]" semble`.
- `.github/hooks/hooks.json` already exists and currently contains `SessionStart`, `Stop`, and `PreToolUse` hooks for session logging plus file/git protection.
- `.github/copilot-instructions.md` is the main always-on instruction file.
- Root `AGENTS.md` does not exist yet.
- The current README bootstrap install flow copies only `.github/`, so adding `.vscode/mcp.json` and root `AGENTS.md` requires an explicit distribution/update note in `README.md`.
- There is no project test suite or `pyproject.toml`, so validation must rely on JSON validation, shell/Python syntax checks, hook self-checks, and explicit smoke-test notes.

### Hard constraints

- Preserve existing hooks and guardrails.
- Do not hardcode user-specific paths.
- Do not add secrets.
- Do not make Semble/context-mode mandatory for every target repo.
- Keep routing policy centralized instead of duplicating long rules across multiple files.
- Validate all JSON files.
- Missing optional local binaries must produce warnings, not hard failures.

## Phase breakdown

### Phase 1: Baseline audit and routing contract

Capture the current control-plane state, upstream reference points, the bootstrap distribution gap, and the intended division of labor between Semble, context-mode, grep, and direct file reads. This phase produces the audit report and locks the non-replacement requirement before any merge work starts.

### Phase 2: Safe runtime primitives

Add the safety layer before any hook rewiring. This phase introduces a small wrapper hook script that can resolve or skip context-mode safely, plus a repo-local runtime checker that validates file presence, JSON shape, and optional binary availability.

### Phase 3: Control-plane wiring

Merge VS Code MCP and hook configuration so both tools are available without removing the existing safety hooks. Add one centralized routing instruction file, then keep `copilot-instructions.md`, `AGENTS.md`, the retrieval-routing skill, and `README.md` as thin entry points that defer to that single routing source.

### Phase 4: Validation and smoke reporting

Run the runtime checker, validate both JSON files, run the wrapper self-checks, and write a short smoke-test report that records the exact routing checks performed and any expected warnings from missing local binaries.

## Step table

| Step | Owner | Files | Required Skills | Verification |
|---|---|---|---|---|
| 1. Write baseline audit report | `coder` | `.github/reports/semble-contextmode-integration-audit.md` | `VS Code built-in agent-customization/SKILL.md`, `.github/skills/documentation/SKILL.md` | `grep -q "Semble" .github/reports/semble-contextmode-integration-audit.md && grep -q "context-mode" .github/reports/semble-contextmode-integration-audit.md && grep -q ".vscode/mcp.json" .github/reports/semble-contextmode-integration-audit.md` |
| 2. Add safe wrapper and runtime checker primitives | `coder` | `.github/hooks/scripts/context-mode-dispatch.sh`, `.github/scripts/check_agent_runtime.py` | `VS Code built-in agent-customization/SKILL.md`, `.github/skills/code-style/SKILL.md` | `bash -n .github/hooks/scripts/context-mode-dispatch.sh && bash .github/hooks/scripts/context-mode-dispatch.sh --self-check && python -m py_compile .github/scripts/check_agent_runtime.py` |
| 3. Merge workspace MCP config | `coder` | `.vscode/mcp.json` | `VS Code built-in agent-customization/SKILL.md` | `python -m json.tool .vscode/mcp.json >/dev/null` |
| 4. Add authoritative routing instruction with explicit frontmatter and minimal bootstrap reference | `coder` | `.github/instructions/tool-routing.instructions.md`, `.github/copilot-instructions.md` | `VS Code built-in agent-customization/SKILL.md`, `.github/skills/documentation/SKILL.md` | `grep -q '^description:' .github/instructions/tool-routing.instructions.md && grep -q 'tool-routing.instructions.md' .github/copilot-instructions.md` |
| 5. Add root AGENTS and update bootstrap distribution docs | `coder` | `AGENTS.md`, `README.md` | `VS Code built-in agent-customization/SKILL.md`, `.github/skills/documentation/SKILL.md` | `grep -q '.vscode/mcp.json' README.md && grep -q 'AGENTS.md' README.md && grep -q 'tool-routing.instructions.md' AGENTS.md` |
| 6. Merge context-mode hooks through the safe wrapper without dropping existing protections | `coder` | `.github/hooks/hooks.json`, `.github/hooks/scripts/context-mode-dispatch.sh` | `VS Code built-in agent-customization/SKILL.md` | `python -m json.tool .github/hooks/hooks.json >/dev/null && bash .github/hooks/scripts/context-mode-dispatch.sh --self-check` |
| 7. Add retrieval-routing skill as a thin pointer, not a second routing authority | `coder` | `.github/skills/retrieval-routing/SKILL.md` | `VS Code built-in agent-customization/SKILL.md`, `.github/skills/documentation/SKILL.md` | `grep -q 'name: retrieval-routing' .github/skills/retrieval-routing/SKILL.md && grep -q 'tool-routing.instructions.md' .github/skills/retrieval-routing/SKILL.md` |
| 8. Write smoke-test report with installed and missing-binary scenarios | `coder` | `.github/reports/tool-routing-smoke-tests.md` | `.github/skills/documentation/SKILL.md` | `grep -q 'WARN' .github/reports/tool-routing-smoke-tests.md && grep -q 'PASS' .github/reports/tool-routing-smoke-tests.md` |
| 9. Final validation and changed-file summary | `verifier` | `.vscode/mcp.json`, `.github/hooks/hooks.json`, `.github/hooks/scripts/context-mode-dispatch.sh`, `.github/scripts/check_agent_runtime.py`, `README.md`, `.github/reports/*`, `.github/instructions/tool-routing.instructions.md`, `AGENTS.md`, `.github/skills/retrieval-routing/SKILL.md` | `.github/skills/documentation/SKILL.md` | `python -m json.tool .vscode/mcp.json >/dev/null && python -m json.tool .github/hooks/hooks.json >/dev/null && bash -n .github/hooks/scripts/context-mode-dispatch.sh && bash .github/hooks/scripts/context-mode-dispatch.sh --self-check && python -m py_compile .github/scripts/check_agent_runtime.py && python .github/scripts/check_agent_runtime.py` |

## Implementation notes by step

### Step 1: Audit report

- Document the current state of `.vscode/mcp.json`, `.github/hooks/hooks.json`, `.github/copilot-instructions.md`, `.github/skills/`, root-level agent compatibility files, and the current README copy/install contract.
- Capture the upstream merge targets:
  - Semble MCP and bash guidance.
  - context-mode VS Code Copilot MCP and hook guidance.
  - VS Code MCP config schema expectations.
- Record the final routing contract in prose:
  - Semble for semantic repo discovery, behavior ownership, related-code lookup.
  - context-mode for large outputs, logs, prose/markdown artifacts, session continuity, and compaction-safe retrieval.
  - grep/ripgrep for exact literals.
  - direct file reads for known paths.
  - avoid duplicate broad retrieval across multiple systems.

### Step 2: Safe wrapper and checker primitives

- Add `.github/hooks/scripts/context-mode-dispatch.sh` as the live hook target for context-mode-related hook entries.
- The wrapper should:
  - resolve `context-mode` from `PATH`,
  - optionally fall back to `npx -y context-mode` when `npx` exists,
  - print `WARN` and exit `0` when neither command is available,
  - pass through normal hook arguments such as `vscode-copilot pretooluse`,
  - support `--self-check` so the repo can validate the wrapper without firing a real hook event.
- Add `.github/scripts/check_agent_runtime.py` as a dependency-free checker that validates required files, JSON structure, and expected server/hook entries, and reports optional binary availability without failing the build on missing local binaries.

### Step 3: `.vscode/mcp.json`

- Preserve the existing `semble` entry.
- Add a second server entry for `context-mode` using a VS Code-compatible `servers` object.
- Prefer a portable command form with no user-specific path. Current assumption: `"command": "context-mode"` with README fallback guidance for users who prefer `npx -y context-mode`.
- Do not introduce secrets or `inputs` unless later required.

### Step 4: Centralized routing instruction

- Create `.github/instructions/tool-routing.instructions.md` as the single authoritative routing policy.
- Use explicit instruction frontmatter with a `description:` trigger such as "load when choosing between Semble, context-mode, grep, and direct file reads".
- Do not use `applyTo: "**"`; this is routing guidance, not an always-on broad file-scope rule.
- Keep the file short enough to be maintainable, but explicit about:
  - preferred tool by task shape,
  - fallback order,
  - when not to use Semble/context-mode,
  - avoiding duplicate broad searches.
- Update `.github/copilot-instructions.md` with only a minimal pointer in the instructions table and a short note in the retrieval guidance section.

### Step 5: Root `AGENTS.md` and README distribution contract

- Provide CLI/sub-agent compatibility for tools that only read root agent guidance.
- Keep `AGENTS.md` short and aligned with the centralized routing file.
- Include enough Semble bash guidance to be useful when MCP tools are unavailable, but avoid copying the full routing policy block.
- Update `README.md` so the bootstrap install instructions explicitly describe the checked-in root surfaces:
  - `.github/` remains the main scaffold,
  - `.vscode/mcp.json` and `AGENTS.md` are optional but recommended add-ons,
  - target repos can skip them and still keep the bootstrap functional.

### Step 6: Hook merge

- Preserve the existing `protect-files.sh`, `git-protection.sh`, and `session-log.sh` hooks.
- Point context-mode hook entries at `.github/hooks/scripts/context-mode-dispatch.sh` rather than `context-mode` directly.
- Merge context-mode hook commands into the existing file rather than splitting to a second hook file, because the user explicitly requested a merge.
- PreToolUse ordering should keep existing protection hooks first, then add the context-mode wrapper.
- Add `PostToolUse` and `PreCompact` through the wrapper.
- Add the wrapper to `SessionStart` without removing the existing session log hook.
- Keep the existing `Stop` hook intact.

### Step 7: Retrieval-routing skill

- Create `.github/skills/retrieval-routing/SKILL.md` as a thin, reusable routing aid.
- The skill should point back to `.github/instructions/tool-routing.instructions.md` as the authority instead of re-embedding the full policy.
- Keep it focused on triggers and short dispatch reminders rather than long theory.

### Step 8: Smoke-test report

- Add `.github/reports/tool-routing-smoke-tests.md` with executed checks and expected outcomes.
- Cover at least these scenarios:
  - valid JSON and expected server/hook keys present,
  - wrapper self-check passes when binaries exist,
  - wrapper warns and exits successfully when context-mode is unavailable,
  - runtime checker warns on missing optional binaries and fails only on broken config,
  - routing guidance is consistent across the instruction file, AGENTS, skill, and README.

### Step 9: Final validation

- Run JSON validation on both config files.
- Run the wrapper self-check and the runtime checker.
- Summarize changed files in the final handoff.
- If the runtime checker exposes a structural config miss, fix it before touching adjacent docs.

## Risk and fallback paths

| Risk | Impact | Fallback / mitigation |
|---|---|---|
| The bootstrap README still implies `.github/` is the only shipped surface | High | Update README copy/install docs so `.vscode/mcp.json` and `AGENTS.md` are explicitly called out as optional bootstrap artifacts. |
| `context-mode` global binary is missing on a target machine | High | Route hook calls through the wrapper so missing binaries warn and exit `0`; document `npm install -g context-mode` and `npx -y context-mode` as setup options in `README.md`. |
| Hook merge changes `PreToolUse` ordering and weakens guardrails | High | Keep `protect-files.sh` and `git-protection.sh` ahead of the wrapper in the same array; verify existing hooks remain present after merge. |
| Routing policy gets duplicated across instruction, AGENTS, README, and skill files | High | Keep `.github/instructions/tool-routing.instructions.md` authoritative; other files should point to it and only carry short summaries. |
| VS Code hook/MCP schema drift breaks future installs | Medium | Keep checked-in JSON minimal, schema-compatible, and validated with `json.tool`; let the runtime checker verify only stable structural expectations. |

## Done criteria

- `.github/reports/semble-contextmode-integration-audit.md` exists and documents current state, routing policy, and the bootstrap distribution contract.
- `.github/hooks/scripts/context-mode-dispatch.sh` exists, passes `bash -n`, and warns instead of failing when optional binaries are missing.
- `.github/scripts/check_agent_runtime.py` exists, runs successfully, and treats missing optional binaries as warnings.
- `.vscode/mcp.json` contains both `semble` and `context-mode` servers in valid JSON.
- `.github/instructions/tool-routing.instructions.md` exists with explicit frontmatter and is the authoritative routing policy.
- `.github/copilot-instructions.md` contains a minimal reference to the routing file instead of duplicating long routing rules.
- Root `AGENTS.md` exists for CLI/sub-agent compatibility.
- `README.md` documents the optional root surfaces and install/verification flow.
- `.github/hooks/hooks.json` keeps existing protection/session hooks and adds context-mode hook coverage through the wrapper.
- `.github/skills/retrieval-routing/SKILL.md` exists as a thin pointer skill.
- `.github/reports/tool-routing-smoke-tests.md` records installed and missing-binary scenarios.
- Final handoff includes the runtime-check result and a changed-file summary.

## Devil's Advocate Report

| Concern | Risk | Alternative | Recommendation |
|---|---|---|---|
| Importing context-mode's routing block verbatim would make it feel like a replacement for the bootstrap workflow rather than an addition | High | Write a repo-local routing instruction that adopts the useful dispatch rules but keeps bootstrap priorities and quality gates unchanged | CHANGE |
| Pointing hooks straight at `context-mode` contradicts the warning-only requirement when the binary is missing | High | Route all context-mode hook events through a repo-local wrapper that can warn and exit `0` | CHANGE |
| Adding `.vscode/mcp.json` and `AGENTS.md` without updating the bootstrap copy contract would leave target repos behind | High | Treat those files as optional bootstrap surfaces and document them explicitly in `README.md` | CHANGE |
| Duplicating Semble/context-mode guidance in multiple files will drift quickly | High | Put the full routing policy in one instruction file and keep AGENTS/README/skill/copilot instructions intentionally short | CHANGE |
| Choosing `command: "context-mode"` may be less portable than `npx -y context-mode` on a fresh machine | Medium | Keep checked-in config simple and probe availability with warnings; document `npx` fallback explicitly | ACCEPT RISK |

## Working assumptions

- Use `.vscode/mcp.json` `servers` syntax, matching the existing file and current VS Code MCP docs.
- Keep Semble configured through `uvx --from "semble[mcp]" semble`.
- Add context-mode through `command: "context-mode"` in checked-in config, with README fallback guidance for `npx -y context-mode` rather than hardcoding one user's local path.
- The retrieval-routing skill remains intentionally thin and defers all detailed routing logic to `.github/instructions/tool-routing.instructions.md`.
- No automated pytest suite will be added in this task unless the runtime checker grows enough logic to justify dedicated tests.
