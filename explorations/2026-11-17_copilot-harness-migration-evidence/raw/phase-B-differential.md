# Phase B differential battery

Old guard: `git show dev:shared/hooks/scripts/protect-files.py` (dev at `2e8c7bb`).
New guard: the working copy `shared/hooks/scripts/protect-files.py`.
Compared: the parsed `permissionDecision` (`allow` means no output) and the exit code.

Cases: 1158 payloads x 4 clients = 4632 runs per guard.
Identical: 4318. Different: 314. Unexplained: 0.

## Cases by group

| Group | Payloads |
| --- | --- |
| readers x targets | 50 |
| writers x targets | 40 |
| shell helpers | 13 |
| evidence patches | 10 |
| header shapes | 16 |
| header kinds | 18 |
| patch edge | 24 |
| text inputs | 34 |
| search tools | 13 |
| no-decision tools | 22 |
| workflow tools | 6 |
| shell shapes | 912 |

## Differences by decision-change row

| Row | Differences |
| --- | --- |
| L1 | 16 |
| L2 | 20 |
| L3 | 148 |
| T1 | 48 |
| T1 (the key `paths` is global) | 12 |
| T2 | 64 |
| T4 | 6 |

## Notes on the rows

- **L1.** The `Read` rows changed for all four clients, because the guard reads the client id, not the tool's origin. In a real session only `github-copilot` sends `Read` to this guard (the Claude and Codex matchers are `Edit|Write` and `Bash`). A secret-shaped file stays denied (the `.env` rows are identical).
- **L2.** `read_bash`, `list_bash`, and `stop_bash` with no `command`: a stop (exit 2) became no decision. With a path key (`path: .env`) the input is judged like a native tool and is denied. With a `command` key (or a null or number `command`) nothing changed: those rows are identical.
- **L3.** Patch text (a string input) was a stop (exit 2) for every row. It now gets the decision of its targets: the same as the same patch as an object input (`header shapes`, `header kinds`, `patch edge`).
- **T1.** A secret-shaped entry in `paths` of `grep`, `rg`, `glob` (any casing) is now denied. A folder, a glob filter, and a content pattern are identical. `PATH_KEYS` is one set, so any tool with a `paths` list is now judged by path (`multi_edit`, `some_tool` rows): a tool that is not read-only asks or is denied on a hook file, and is denied on a secret-shaped file.
- **T2.** An object input with an indented, lowercase, or extra-blank header is now judged. A hunk context line that spells a header, such as ` *** Add File: .env`, is judged too, because it cannot be told from an indented header. It only matters when the spelled target is protected. These rows are the `patch edge` rows with `.env`.
- **T4.** Only `github-copilot`, by name. The same call for the other three clients is identical (no decision).
- **Identical.** All 45 shell-command shapes (redirects, heredocs, interpreters, `git -C`, `cd`, `&&`, `apply_patch` heredocs) x 5 targets x 4 shell tool names x 4 clients; every fail-closed text row; every no-decision tool; every writer row except the patch text row.

## Every difference

Outcome is `decision/exit code`; `allow` is no decision; exit 2 is a fail-closed stop (the shell wrapper turns it into a deny).

| Row | Group | Tool | Client | Old | New | Input |
| --- | --- | --- | --- | --- | --- | --- |
| L1 | readers x targets | `Read` | github-copilot | ask/0 | allow/0 | `pascal: {"path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | claude-code | ask/0 | allow/0 | `pascal: {"path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | openai-codex | deny/0 | allow/0 | `pascal: {"path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | google-antigravity | deny/0 | allow/0 | `pascal: {"path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | github-copilot | ask/0 | allow/0 | `pascal: {"path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | claude-code | ask/0 | allow/0 | `pascal: {"path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | openai-codex | deny/0 | allow/0 | `pascal: {"path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | google-antigravity | deny/0 | allow/0 | `pascal: {"path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | github-copilot | ask/0 | allow/0 | `pascal: {"file_path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | claude-code | ask/0 | allow/0 | `pascal: {"file_path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | openai-codex | deny/0 | allow/0 | `pascal: {"file_path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | google-antigravity | deny/0 | allow/0 | `pascal: {"file_path": ".github/hooks/hooks.json"}` |
| L1 | readers x targets | `Read` | github-copilot | ask/0 | allow/0 | `pascal: {"file_path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | claude-code | ask/0 | allow/0 | `pascal: {"file_path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | openai-codex | deny/0 | allow/0 | `pascal: {"file_path": ".claude/agents/coder.md"}` |
| L1 | readers x targets | `Read` | google-antigravity | deny/0 | allow/0 | `pascal: {"file_path": ".claude/agents/coder.md"}` |
| T1 | readers x targets | `Grep` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `Grep` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `Grep` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `Grep` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `Grep` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Grep` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Grep` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Grep` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Glob` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `Glob` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `Glob` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `Glob` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `Glob` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Glob` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Glob` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `Glob` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `grep` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `grep` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `grep` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `grep` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `grep` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `grep` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `grep` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `grep` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `rg` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `rg` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `rg` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `rg` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env"]}` |
| T1 | readers x targets | `rg` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `rg` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `rg` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `rg` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `glob` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `glob` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `glob` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `glob` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".env"]}` |
| T1 | readers x targets | `glob` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `glob` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `glob` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| T1 | readers x targets | `glob` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "*", "paths": [".claude/agents/.env"]}` |
| L3 | writers x targets | `Edit` | github-copilot | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | claude-code | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | openai-codex | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | google-antigravity | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/hooks.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/hooks.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/hooks.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/hooks.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/coder.md\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/coder.md\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/coder.md\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/coder.md\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/.env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/.env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/.env\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | writers x targets | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .claude/agents/.env\n@@\n-a\n+b\n*** End Patch\n` |
| L2 | shell helpers | `read_bash` | github-copilot | allow/2 | allow/0 | `pascal: {"shellId": "0", "delay": 1}` |
| L2 | shell helpers | `read_bash` | claude-code | allow/2 | allow/0 | `pascal: {"shellId": "0", "delay": 1}` |
| L2 | shell helpers | `read_bash` | openai-codex | allow/2 | allow/0 | `pascal: {"shellId": "0", "delay": 1}` |
| L2 | shell helpers | `read_bash` | google-antigravity | allow/2 | allow/0 | `pascal: {"shellId": "0", "delay": 1}` |
| L2 | shell helpers | `list_bash` | github-copilot | allow/2 | allow/0 | `pascal: {}` |
| L2 | shell helpers | `list_bash` | claude-code | allow/2 | allow/0 | `pascal: {}` |
| L2 | shell helpers | `list_bash` | openai-codex | allow/2 | allow/0 | `pascal: {}` |
| L2 | shell helpers | `list_bash` | google-antigravity | allow/2 | allow/0 | `pascal: {}` |
| L2 | shell helpers | `stop_bash` | github-copilot | allow/2 | allow/0 | `pascal: {"shellId": "0"}` |
| L2 | shell helpers | `stop_bash` | claude-code | allow/2 | allow/0 | `pascal: {"shellId": "0"}` |
| L2 | shell helpers | `stop_bash` | openai-codex | allow/2 | allow/0 | `pascal: {"shellId": "0"}` |
| L2 | shell helpers | `stop_bash` | google-antigravity | allow/2 | allow/0 | `pascal: {"shellId": "0"}` |
| L2 | shell helpers | `read_bash` | github-copilot | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `read_bash` | claude-code | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `read_bash` | openai-codex | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `read_bash` | google-antigravity | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `list_bash` | github-copilot | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `list_bash` | claude-code | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `list_bash` | openai-codex | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L2 | shell helpers | `list_bash` | google-antigravity | allow/2 | deny/0 | `pascal: {"shellId": "0", "path": ".env"}` |
| L3 | evidence patches | `Edit` | github-copilot | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | claude-code | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | openai-codex | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | google-antigravity | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | github-copilot | allow/2 | allow/0 | `camel: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | claude-code | allow/2 | allow/0 | `camel: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | openai-codex | allow/2 | allow/0 | `camel: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | google-antigravity | allow/2 | allow/0 | `camel: *** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | github-copilot | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | claude-code | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | openai-codex | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | google-antigravity | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | github-copilot | allow/2 | ask/0 | `camel: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | claude-code | allow/2 | ask/0 | `camel: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | openai-codex | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | google-antigravity | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | github-copilot | allow/2 | ask/0 | `camel: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | claude-code | allow/2 | ask/0 | `camel: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | openai-codex | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | google-antigravity | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n` |
| L3 | evidence patches | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | github-copilot | allow/2 | ask/0 | `camel: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | claude-code | allow/2 | ask/0 | `camel: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | openai-codex | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | evidence patches | `apply_patch` | google-antigravity | allow/2 | deny/0 | `camel: *** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n` |
| L3 | header shapes | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| T2 | header shapes | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | github-copilot | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | claude-code | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | openai-codex | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| L3 | header shapes | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| T2 | header shapes | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | github-copilot | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | claude-code | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | openai-codex | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n*** add file: .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| L3 | header shapes | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | header shapes | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| T2 | header shapes | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | github-copilot | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | claude-code | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | openai-codex | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| T2 | header shapes | `Edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n***  Add  File:  .github/hooks/evil.json\n+{}\n*** End Patch\n"}` |
| L3 | header kinds | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Delete File: .github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Delete File: .github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Delete File: .github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Delete File: .github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n*** Move to: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n*** Move to: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n*** Move to: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n*** Move to: .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| L3 | header kinds | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n` |
| T2 | header kinds | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n  *** UPDATE FILE : .github/hooks/evil.json\n@@\n-a\n+b\n*** End Patch\n"}` |
| L3 | header kinds | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n***	Delete	File:	.github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n***	Delete	File:	.github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n***	Delete	File:	.github/hooks/evil.json\n*** End Patch\n` |
| L3 | header kinds | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n***	Delete	File:	.github/hooks/evil.json\n*** End Patch\n` |
| T2 | header kinds | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| T2 | header kinds | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n***\tDelete\tFile:\t.github/hooks/evil.json\n*** End Patch\n"}` |
| L3 | header kinds | `Edit` | github-copilot | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n+b\n*** End` |
| L3 | header kinds | `Edit` | claude-code | allow/2 | ask/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n+b\n*** End` |
| L3 | header kinds | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n+b\n*** End` |
| L3 | header kinds | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n+b\n*** End` |
| T2 | header kinds | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n` |
| T2 | header kinds | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n` |
| T2 | header kinds | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n` |
| T2 | header kinds | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a\n` |
| T2 | header kinds | `apply_patch` | github-copilot | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a` |
| T2 | header kinds | `apply_patch` | claude-code | allow/0 | ask/0 | `pascal: {"command": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a` |
| T2 | header kinds | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a` |
| T2 | header kinds | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"command": "*** Begin Patch\n*** Update File: notes.txt\n  ***   move   to :  .github/hooks/evil.json\n@@\n-a` |
| L3 | patch edge | `Edit` | github-copilot | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | claude-code | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | openai-codex | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | google-antigravity | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | github-copilot | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | claude-code | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | openai-codex | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | google-antigravity | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | github-copilot | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | claude-code | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | openai-codex | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | google-antigravity | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | github-copilot | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | claude-code | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | openai-codex | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | google-antigravity | allow/2 | allow/0 | `pascal: *** Begin Patch\n*** Add File: notes.txt\n+*** Add File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | github-copilot | allow/2 | ask/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `Edit` | claude-code | allow/2 | ask/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `Edit` | openai-codex | allow/2 | deny/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | github-copilot | allow/2 | ask/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | claude-code | allow/2 | ask/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | openai-codex | allow/2 | deny/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | google-antigravity | allow/2 | deny/0 | `pascal:   \n*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n` |
| L3 | patch edge | `Edit` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** Delete File: .env\n*** End Patch\n` |
| L3 | patch edge | `Edit` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| T2 | patch edge | `Edit` | github-copilot | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `Edit` | claude-code | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `Edit` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `Edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| L3 | patch edge | `apply_patch` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| T2 | patch edge | `apply_patch` | github-copilot | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `apply_patch` | claude-code | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| L3 | patch edge | `Edit` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `Edit` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| T2 | patch edge | `Edit` | github-copilot | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `Edit` | claude-code | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `Edit` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `Edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| L3 | patch edge | `apply_patch` | github-copilot | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | claude-code | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | openai-codex | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| L3 | patch edge | `apply_patch` | google-antigravity | allow/2 | deny/0 | `pascal: *** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n` |
| T2 | patch edge | `apply_patch` | github-copilot | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `apply_patch` | claude-code | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `apply_patch` | openai-codex | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T2 | patch edge | `apply_patch` | google-antigravity | allow/0 | deny/0 | `pascal: {"input": "*** Begin Patch\n*** Update File: notes.txt\n@@\n   *** Add File: .env\n-a\n+b\n*** End Patch\n"}` |
| T1 | search tools | `grep` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": ["src", ".claude/agents/.env", "docs"]}` |
| T1 | search tools | `grep` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": ["src", ".claude/agents/.env", "docs"]}` |
| T1 | search tools | `grep` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": ["src", ".claude/agents/.env", "docs"]}` |
| T1 | search tools | `grep` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": ["src", ".claude/agents/.env", "docs"]}` |
| T1 | search tools | `rg` | github-copilot | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env.local", "credentials.json", "id.pem"]}` |
| T1 | search tools | `rg` | claude-code | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env.local", "credentials.json", "id.pem"]}` |
| T1 | search tools | `rg` | openai-codex | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env.local", "credentials.json", "id.pem"]}` |
| T1 | search tools | `rg` | google-antigravity | allow/0 | deny/0 | `pascal: {"pattern": "x", "paths": [".env.local", "credentials.json", "id.pem"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | github-copilot | allow/0 | deny/0 | `pascal: {"paths": [".env"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | claude-code | allow/0 | deny/0 | `pascal: {"paths": [".env"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | openai-codex | allow/0 | deny/0 | `pascal: {"paths": [".env"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"paths": [".env"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | github-copilot | allow/0 | ask/0 | `pascal: {"paths": [".github/hooks/hooks.json"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | claude-code | allow/0 | ask/0 | `pascal: {"paths": [".github/hooks/hooks.json"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | openai-codex | allow/0 | deny/0 | `pascal: {"paths": [".github/hooks/hooks.json"]}` |
| T1 (the key `paths` is global) | search tools | `multi_edit` | google-antigravity | allow/0 | deny/0 | `pascal: {"paths": [".github/hooks/hooks.json"]}` |
| T1 (the key `paths` is global) | search tools | `some_tool` | github-copilot | allow/0 | ask/0 | `pascal: {"paths": [".claude/agents/coder.md"]}` |
| T1 (the key `paths` is global) | search tools | `some_tool` | claude-code | allow/0 | ask/0 | `pascal: {"paths": [".claude/agents/coder.md"]}` |
| T1 (the key `paths` is global) | search tools | `some_tool` | openai-codex | allow/0 | deny/0 | `pascal: {"paths": [".claude/agents/coder.md"]}` |
| T1 (the key `paths` is global) | search tools | `some_tool` | google-antigravity | allow/0 | deny/0 | `pascal: {"paths": [".claude/agents/coder.md"]}` |
| T4 | workflow tools | `run_dynamic_workflow` | github-copilot | allow/0 | deny/0 | `pascal: {"name": "probe-wf", "args": null}` |
| T4 | workflow tools | `run_dynamic_workflow` | github-copilot | allow/0 | deny/0 | `camel: {"name": "probe-wf", "args": null}` |
| T4 | workflow tools | `dynamic_workflows_manage` | github-copilot | allow/0 | deny/0 | `pascal: {"operation": "list"}` |
| T4 | workflow tools | `dynamic_workflows_manage` | github-copilot | allow/0 | deny/0 | `camel: {"operation": "list"}` |
| T4 | workflow tools | `dynamic_workflows_manage` | github-copilot | allow/0 | deny/0 | `pascal: {"operation": "author", "meta": {"name": "probe-wf", "description": "x", "phases": []}, "run": "async ({ args,` |
| T4 | workflow tools | `dynamic_workflows_manage` | github-copilot | allow/0 | deny/0 | `camel: {"operation": "author", "meta": {"name": "probe-wf", "description": "x", "phases": []}, "run": "async ({ args,` |
