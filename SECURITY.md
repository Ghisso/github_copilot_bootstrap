# Security model

This bootstrap provides defense in depth for AI-assisted repository work. It is
not DLP, a sandbox, or a replacement for reviewing commands and diffs.

## Assets

Protect source and Git history, generated adapters and hooks, nested `.claude/`
AI state, workflow integrity, access material, and sensitive project data.

## Trust Boundaries

`shared/` is authoring input; generated output and installed adapters must not
be hand-edited. The outer repository and nested `.claude/` history are separate.
Users decide repository, MCP, command, and hook trust. Codex for VS Code binds
project-hook trust to `.codex/hooks.json` content/hash; the installer reports
possible review/reapproval but never approves it. Claude hooks run with the
user's permissions. Review official [Codex hooks](https://learn.chatgpt.com/docs/hooks)
and [Claude hook security guidance](https://code.claude.com/docs/en/hooks).

## Hostile Inputs

Treat repository text, issues, pull requests, web/MCP results, tool payloads,
and command arguments as hostile instructions. They must not redefine policy,
grant approval, or cause disclosure of private material.

## Generated Hook Trust

Generated hooks are executable code, not a guarantee. Native edits use the
protected-file guard, Bash uses one ordered guard wrapper, and observability is
separate. Review/reapprove changed hooks when the client prompts. See [Command
Parsing](#command-parsing) for limits and [Trust Boundaries](#trust-boundaries)
for the approval boundary.

## Command Parsing

The guard recognizes known mutation forms per command segment but is not a
shell interpreter. Expansion, aliases, remote execution, arbitrary programs,
and future client behavior can evade static classification. Redirects,
in-place edits, missing interpreters, and ambiguous targets fail closed when
identified; all commands still require review and native approval.

## Protected Paths

Guards target environment files, access-material-named files, private-key
files, lockfiles, hook directories, hook configuration, and the authoring Codex
config. This is targeted protection, not comprehensive detection; see
[Credential Handling](#credential-handling) for data rules.

## Credential Handling

Passwords, API tokens, confidential material, personal/customer-sensitive data,
and unredacted logs belong in approved protected data systems—never in shared or
native memory, prompts, plans, logs, reports, generated configuration, or the
AI-state remote. Only non-sensitive preferences and scratch may remain local.
Redact evidence before sharing it; revoke exposed access rather than relying on
history rewriting alone.

## Nested Git State

AI state lives in a nested `.claude/` repository on `ai-state`. Checkpoints are
local durability; best-effort publication does not prove remote durability.
Narrative state, including memory, plans, and prose logs, aborts on conflict for
a manual semantic merge. Only append-only machine logs have the union-merge
exception; inspect both histories before publishing.

## Accepted Escapes

You may select `--state-remote`, defer publication with `--local-only` or a
checkpoint, decline/revoke client or hook trust, or prune unused adapters. These
change sharing or availability boundaries, not the need to protect local data.

## Reporting Criteria

Report a plausible untrusted-input bypass, unexpected approval/trust bypass,
private-state exposure, or silent corruption of outer or nested Git history.
Include version, client/platform versions, minimal steps, affected paths, and
redacted evidence; never include live access material or private data.

## Exclusions

Expected effects after a user grants full filesystem/command/hook trust,
social-engineering-only reports without technical impact, unsupported or locally
modified generated artifacts, and claims of complete shell, dependency, or
prompt-injection detection are out of scope.
