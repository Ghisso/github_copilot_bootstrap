---
name: integration-gate-spike
visibility: background
description: |
  Minimal evidence spike for an external contract (API, service, third-party
  system) that is unknown or underspecified, run before writing adapter code.
  Verifies only the specific unknowns that materially change the
  implementation — it does not prescribe feature flags, multi-provider
  abstraction, retries, or caching by default.

  Triggers:
  - "We need to integrate with API X, but don't know the exact contract yet"
  - "Unknown response schema from external service"
  - "Rate limits and timeout behavior not documented"
  - "Plan mentions external service but can't verify the endpoint exists"
  - Planning adapter code where contract uncertainty blocks an
    implementation decision
user-invocable: false
---

## Problem

Planning an integration with an external API or service sometimes has a real
contract-uncertainty gap: schema, error format, or rate-limit behavior isn't
documented and can't be confirmed without touching the live endpoint.

Anti-patterns this skill avoids in both directions:

1. **Invented assumptions** — implementation proceeds on a guessed contract
   and breaks at runtime.
2. **Over-verification** — spending the spike confirming facts that don't
   change any implementation decision.
3. **Over-engineering ahead of evidence** — adding retries, caching,
   multi-provider abstraction, or a feature flag because "integrations
   usually need this," not because the gathered evidence requires it.

## When to use this skill

Only when contract uncertainty would otherwise force an implementation
decision to be guessed. If the schema, auth, and error behavior are already
documented (official API docs, an existing working client in this repo, an
OpenAPI spec), skip this skill and implement directly.

## Step 1: List the Unknowns That Matter

Before touching the endpoint, list only the facts that would actually
change what gets built. Typical candidates — verify only the ones relevant
to this integration:

- **Reachability** — does the endpoint exist and respond?
- **Response schema** — field names and types the adapter must parse.
- **Error signaling** — how the service reports failure (status codes,
  error body shape) — needed only if error handling would otherwise differ
  by cause.
- **Auth** — required headers/tokens, if unknown.
- **Rate limits** — needed only if this plan's call volume could plausibly
  hit them.

Do not add feature flags, retry policy, or caching to this list unless a
concrete requirement (for example, "this runs in a batch of 10,000") already
justifies it.

## Step 2: Run the Minimal Spike

Verify each listed unknown with the smallest check that answers it: a single
`curl`/HTTP call, a documented example response, or a one-off script. Record
what was actually observed, not what was hoped for.

```markdown
## Integration Spike — {Service Name}

**Unknowns checked:** {list from Step 1}

| Unknown | Result | Evidence |
|---|---|---|
| Reachability | Confirmed / Not confirmed | curl output, docs link |
| Response schema | {fields observed} | example response body |
| Error signaling | {status codes / error shape observed} | example error response |

**Decision:** Proceed to implementation with the above as ground truth, or:
endpoint unreachable/undocumented as assumed — {describe the fallback this
specific evidence requires, if any}.
```

## Step 3: Implement Only What the Evidence Requires

- Build the adapter against the schema and error shapes actually observed,
  not invented ones.
- Add a retry, cache, feature flag, or provider abstraction only if the
  spike surfaced a concrete reason for it (an observed rate limit, observed
  intermittent failures, an explicit multi-provider requirement already in
  the plan). Do not add these speculatively.
- If the plan already calls for a `Protocol`/interface for this dependency
  for testability, keep using it; don't introduce one solely because of
  this skill.

## Verification

After implementation, confirm:

1. The spike's evidence table exists and matches what the adapter code
   actually relies on.
2. No adapter behavior (retry count, cache TTL, error-handling branch)
   exists without a corresponding line of evidence from Step 2.
3. Tests use fixture data matching the observed schema/error shapes, not
   invented ones.

## Related Patterns

- `.claude/skills/plan-decomposition/SKILL.md` — structuring multi-phase
  plans where a gate step is needed.
- `.claude/skills/text-to-sql-safety/SKILL.md` — a similar gated
  defense-in-depth pattern for unknown SQL query shapes.
