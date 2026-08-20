# Google Antigravity Coder Routing Supplement

Apply this supplement only to Google Antigravity implementation delegation. For
each approved small-plan implementation step, build a bounded packet from the
plan and evidence already gathered by the planner or orchestrator. Do not run
extra discovery solely to qualify a packet for Flash.

The packet contains only:

- Goal and plan-step identity.
- Relevant files, symbols, entry points, patterns, or failing checks.
- Approved constraints and must-not-change behavior.
- Rejected approaches when relevant.
- Required skills.
- Acceptance criteria and verification commands.
- Freedom for the coder to choose the smallest maintainable local
  implementation.

Choose `antigravity_flash_coder` only when the desired outcome, relevant
implementation surface, constraints, acceptance criteria, and verification are
known and there is no unresolved architecture, interface, root-cause,
migration, security, or ownership decision. Otherwise choose `coder` directly.
Decide independently for every implementation step.

Before editing where possible, `antigravity_flash_coder` validates the packet.
If it cannot proceed safely, it returns only its prompt-enforced escalation
object. A Flash implementation blocker or failure routes once to `coder` with
the original packet, evidence, and current diff state. If Flash changed the
workspace, Pro inspects and takes ownership of the existing diff; it does not
assume a clean workspace or blindly restart.

## Failure Attribution

Before automatic escalation, classify existing verifier commands and results
and reviewer findings as exactly one of:

- `implementation`: the current implementation caused the failure; advance
  exactly one tier automatically.
- `environment`: a missing dependency, service, credential, sandbox
  restriction, unavailable tool, or other execution-environment blocker; stop
  model escalation and report it.
- `baseline`: evidence shows the failure existed on the originating branch or
  outside the changed scope; stop model escalation and report it.
- `indeterminate`: the evidence cannot reliably attribute the failure; return
  to orchestrator judgment with no automatic escalation.

Only `implementation` routes once from Flash to Pro. Never retry Flash, add a
third tier, or let a subagent choose its successor. A Pro failure stops
automatic escalation and returns control to the orchestrator.
