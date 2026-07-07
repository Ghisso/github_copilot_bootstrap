---
name: integration-gate-spike
visibility: background
description: |
  Design and gate unknown external contract validation before adapter implementation.
  Use when integrating with APIs, external services, or third-party systems where the
  endpoint contract (schema, rate-limits, error behavior) is unknown or not fully
  specified. Prevents runtime failures from invented assumptions and over-complex
  fallback logic.
  
  Triggers:
  - "We need to integrate with API X, but don't know the exact contract yet"
  - "Unknown response schema from external service"
  - "Rate limits and timeout behavior not documented"
  - "Plan mentions external service but can't verify the endpoint exists"
  - Planning adapter code where contract uncertainty blocks implementation decision-making
user-invocable: false
---

## Problem

When planning integrations with external APIs or services, teams often face a contract uncertainty gap:
- Endpoint exists but schema is undocumented (e.g., legacy APIs, third-party services)
- Response structure, error format, or rate-limit behavior unknown
- API availability at integration time cannot be verified until code runs

Common anti-patterns:
1. **Invented assumptions**: Plan implementation based on guessed contract → breaks at runtime
2. **Over-engineered fallback**: Add defensive error handling for every possible failure → bloats code, adds untestable paths
3. **Late discovery**: Build adapter, then discover endpoint requires auth/rate-limiting during testing → rework required

## Context / Trigger Conditions

**When to use this skill:**
- Planning integrations with external APIs in multi-day implementation plans
- Unknown endpoint schema, response format, or rate-limit behavior
- Contract uncertainty affects downstream implementation decisions (retry policy, caching, layering)
- Uncertain whether external service will be available in production environment

**Exact symptoms:**
- Plan says "Integrate with UN metadata API" but query response format not documented
- Reviewer comment: "What if the endpoint is rate-limited? The plan doesn't specify retry behavior"
- Design question: "Where should fallback logic go — in the provider, the aggregator, or the enrichment orchestrator?"
- Implementation blocker: "We can't finalize the `MetadataProvider.get_metadata()` signature until we know the API response schema"

## Solution

### Step 1: Define the Integration Gate (Before Building Adapter)

In your plan document, add a **numbered gate step** (e.g., "Phase N.0: Integration Spike") that **validates** the external contract.

Gate pass criteria (documentation required, not implementation):
```markdown
## Step N.0: Integration Spike — Validate External Contract

**Goal:** Confirm external service contract before building adapter.

**Pass Criteria:** All of the following must be documented:
1. **Reachability** — Endpoint responds (curl test or docs confirm URL/port)
2. **Response Schema** — Example response body and documented field names
3. **Rate-limit Behavior** — Max requests/second/hour, retry-after header, backoff strategy
4. **Error Responses** — How service signals errors (HTTP status codes, error field format)
5. **Authentication** — Required headers, API keys, tokens, or none
6. **Fallback Trigger** — Define exactly when adapter reverts to fallback (e.g., "HTTP 429 or timeout >5s")

**Failure Fallback:** If gate fails (endpoint unreachable, schema differs from assumption),
continue implementation with secondary sources only. Keep adapter behind feature flag.
```

### Step 2: Document Assumptions Explicitly in Plan

For each unknown aspect, add an `[ASSUME: ...]` block:

```markdown
[ASSUME: UN metadata API endpoint is `https://un-api.org/metadata/{resolution_id}`]
[ASSUME: Response contains fields `title`, `vote_summary`, `topics` (array of strings)]
[ASSUME: Rate limit is ≥100 req/min (reasonable for batch processing)]
[ASSUME: No API key required (public endpoint)]
```

These get validated in Step N.0. If reality differs, update the assumption and design fallback.

### Step 3: Isolate Adapter Behind Abstraction

In implementation plan, specify that the adapter goes behind an existing abstraction (e.g., `MetadataProvider` protocol, not directly in business logic):

```markdown
## E.1: Create UN Metadata Provider

- **Module:** `src/pipeline/un_metadata_provider.py` (implements `MetadataProvider` protocol)
- **Interface:**
  ```python
  class UnMetadataProvider(MetadataProvider):
      def get_metadata(self, resolution_id: str) -> dict[str, Any]: ...
  ```
- **Dependency:** Enrichment layer depends on `MetadataProvider`, not `UnMetadataProvider`
  → Allows mock/stub provider for testing or fallback at startup
```

This isolation means:
- If gate N.0 fails, you can substitute a stub provider or CSV-based provider without refactoring
- Tests can mock the provider without hitting the real API
- Feature flag can disable external adapter at runtime

### Step 4: Design Source Priority & Fallback Chain

Document explicit fallback order:

```markdown
## E.2: Metadata Enrichment Orchestration

Source priority (try each in order):
1. UN API (if gate N.0 passed + currently available)
2. Secondary provider (CSV or HF Dataset)
3. Text extraction (existing fallback)

Conditions triggering fallback:
- UN API unreachable after 3 retries + 30s timeout → try secondary
- Secondary source returns null/empty → try text extraction
- Feature flag `enable_external_metadata=false` → skip to secondary

Cache behavior:
- Cache UN API responses for 24h (hits save bandwidth + time)
- Cache failures too (4h negative cache) to avoid retry storms
```

### Step 5: Plan Gate Verification Step

Add a verification step after the gate (before adapter implementation):

```markdown
## Step N.0.5: Document Gate Validation Results

After spike, create `docs/INTEGRATION_GATE_RESULTS.md`:

```markdown
# UN Metadata API — Integration Gate Results

**Gate Date:** [date]
**Endpoint:** https://un-api.org/metadata/{resolution_id}
**Status:** PASS ✅ (or FAIL ❌)

| Criteria | Result | Notes |
|----------|--------|-------|
| Reachability | PASS | Endpoint responds 200 to curl https://... |
| Response Schema | PASS | Returns {title, vote_summary, topics} |
| Rate-limit | PASS | 1000 req/hour (‖ 16.7 req/min), Retry-After: 60 |
| Error Responses | PASS | 429 on rate-limit, 404 on unknown ID |
| Auth | PASS | Public endpoint, no key required |
| Fallback Trigger | PASS | Will use HTTP 429 or timeout >5s as trigger |

**Decision:** Proceed to Step E.1 (Implement adapter)
```
```

If FAIL, the gate document becomes the design contract for the fallback-only path.

### Step 6: Implement with Gate Results as Source of Truth

Use gate results to finalize adapter signature and error handling:

```python
# src/pipeline/un_metadata_provider.py

from src.pipeline.metadata_provider import MetadataProvider

class UnMetadataProvider(MetadataProvider):
    """Provider for UN metadata API (gated by integration spike)."""
    
    def __init__(self, base_url: str, timeout_sec: int = 5, max_retries: int = 3):
        # Gate results (gate.md) told us: PASS on all criteria
        # Rate-limit from gate: 1000/hr → safe batch window
        # Error codes from gate: 429 for rate-limit, 404 for unknown
        # Timeout assumption validated: 5s is safe
        self.base_url = base_url
        self.timeout = timeout_sec
        self.max_retries = max_retries
    
    def get_metadata(self, resolution_id: str) -> dict[str, Any]:
        """Fetch metadata; raise UnmetadataError on known failure modes (from gate).
        
        Raises:
            ConnectionError: If endpoint unreachable (no retry budget left)
            TimeoutError: If response >timeout (after 3 retries)
            ValueError: If resolution_id not found (gate showed 404 on unknown IDs)
        
        Not caught internally; caller's enrichment layer decides fallback.
        """
        # Implementation validated against gate results
        ...
```

Enrichment layer (external to provider) decides when to switch to fallback:

```python
# src/csv_generation/metadata_enrichment.py

def enrich_with_metadata(extraction: ResolutionExtraction, 
                         providers: ProviderChain) -> EnrichedExtraction:
    """Apply source priority from design doc (Step E.2)."""
    
    try:
        # Step 1: Try UN API (per gate results, should work for ~90% of IDs)
        meta = providers.un_api.get_metadata(extraction.resolution_id)
        return EnrichedExtraction(extraction, source="un_api", metadata=meta)
    except (ConnectionError, TimeoutError):
        # Gate showed: These errors trigger fallback
        pass
    
    # Step 2: Fallback to secondary (per gate results, should handle ~80% of remaining)
    try:
        meta = providers.csv.get_metadata(extraction.resolution_id)
        return EnrichedExtraction(extraction, source="csv", metadata=meta)
    except KeyError:
        pass
    
    # Step 3: Final fallback to text extraction
    return EnrichedExtraction(extraction, source="text_extraction", metadata=None)
```

## Verification

After implementation completes, verify:

1. ✅ Integration gate step (N.0) executed and documented in `.claude/quality_reports/` or `docs/INTEGRATION_GATE_RESULTS.md`
2. ✅ Gate pass/fail criteria met before adapter coding started
3. ✅ Adapter isolated behind abstraction (protocol/interface, not direct import)
4. ✅ Fallback chain matches source priority from gate documentation
5. ✅ Error handling only covers failure modes documented in gate (no invented error scenarios)
6. ✅ Tests for adapter use gate results as input (fixture data matches documented schema/error codes)

## Example

**Scenario:** Phase E planning for UNSC CSV enrichment via UN metadata API.

**Before this skill:** 
- Plan assumed UN API contract without validation
- Implementation started with incomplete error handling
- Runtime: API response shape differed → parsing errors, slow discovery of issue

**After applying skill:**
1. Plan includes explicit Step E.0 integration spike with pass/fail criteria
2. Assumptions documented: endpoint URL, response schema, rate-limit, error codes
3. Gate spike runs: endpoint confirmed reachable, response schema matches, rate-limit 1000/hr documented
4. Pass/fail results saved to `docs/INTEGRATION_GATE_RESULTS.md`
5. Adapter implementation uses gate results: only handles documented error codes (429, 404), ignores invented ones
6. Fallback to CSV provider defined based on gate coverage estimate (UN API ~90%, CSV ~80% of remainder)
7. Tests fixture data from gate response examples → schema matches at test time
8. **Outcome:** Zero runtime surprises; adapter integrates cleanly with documented fallback

---

## Related Patterns

- `.claude/skills/plan-decomposition/SKILL.md` — Structuring multi-phase plans where gates are needed (also covers the design-review-gate workflow)
- `.claude/skills/text-to-sql-safety/SKILL.md` — Similar gated defense-in-depth for unknown SQL query shapes
