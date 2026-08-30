# Codex Coder Routing Supplement

Apply this supplement only to Codex implementation delegation. For each
approved small-plan implementation step, build a bounded packet from the plan
and evidence already gathered by the planner or orchestrator. Do not run extra
discovery solely to qualify a packet for Luna.

The packet contains only:

- Goal and plan-step identity.
- Relevant files, symbols, entry points, patterns, or failing checks.
- Approved constraints and must-not-change behavior.
- Rejected approaches when relevant.
- Required skills.
- Acceptance criteria and verification commands.
- Freedom for the coder to choose the smallest maintainable local
  implementation.

Exclude broad conversation history and raw discovery output. Choose
`luna_coder` for that step only when all of the following are established:

1. A clear desired outcome.
2. Known relevant files, symbols, entry points, or failing checks.
3. Known constraints and must-not-change behavior.
4. Objective acceptance criteria and verification commands.
5. No unresolved architecture, interface, root-cause, migration, security, or
   ownership decision.

Otherwise choose `coder` directly. Decide independently for every
implementation step.

Before editing where possible, `luna_coder` validates the packet. If it cannot
proceed safely, it returns only this prompt-enforced escalation object; this is
not a native typed protocol:

```json
{
  "status": "escalate",
  "reason": "unknown-root-cause",
  "workspace_changed": false,
  "evidence": ["..."],
  "needed": ["..."]
}
```

`reason` is exactly one of `unresolved-design-decision`,
`unknown-root-cause`, `scope-not-bounded`, `missing-interface-contract`,
`security-or-migration-decision`, or `ownership-unclear`.
`workspace_changed` accurately reports whether Luna changed the workspace.

Use the named recovery path once per tier. A Luna structured blocker or
implementation failure routes to `coder` with the original packet, blocker or
failure evidence, and current diff state. If Luna changed the workspace,
`coder` inspects and takes ownership of the existing diff; it does not assume a
clean workspace or blindly restart.

## Failure Attribution

Before automatic escalation, the orchestrator classifies existing deterministic
verification commands and results and reviewer findings as exactly one of:

- `implementation`: the current implementation caused the failure; advance
  exactly one tier automatically.
- `environment`: a missing dependency, service, credential, sandbox
  restriction, unavailable tool, or other execution-environment blocker; stop
  model escalation and report it.
- `baseline`: evidence shows the failure existed on the originating branch or
  outside the changed scope; stop model escalation and report it.
- `indeterminate`: the evidence cannot reliably attribute the failure; return
  to orchestrator judgment with no automatic escalation.

A deterministic verification failure alone is not sufficient for `implementation`. A reviewer
CRITICAL or MAJOR finding advances a tier only when it applies to the current
implementation diff. Infrastructure errors, flaky or unreproduced failures,
and unrelated baseline findings must not spend a stronger model automatically.
The orchestrator may request focused evidence using existing agents or tools;
it must not invent attribution. Only `implementation` routes once to
`sol_coder` with all prior evidence and the current diff, after an attributable
Terra-produced failure. A Sol failure stops the loop and reports to the user.
Never retry the same tier, jump from Luna directly to Sol, introduce Luna/max,
or let a subagent choose its successor.

Optional route evidence belongs only in the existing closeout or session log as
concise `initial-coder`, `fallback`, and `reason` facts. Do not create a routing
database, telemetry file, cost tracker, or merge gate.
