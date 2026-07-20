---
name: devils-advocate
visibility: public
description: |
  Challenge design decisions with structured critique. Questions architecture
  choices, technology selection, error handling strategy, testing adequacy,
  and configuration design. Use before committing to a major design, or when
  user says "challenge this design" or "devil's advocate".
---

# devils-advocate — Challenge Design

## Structured Critique Areas

### 1. Architecture
- "Why this module boundary? What if it needs to change?"
- "What happens if this component fails?"
- "Is this the simplest decomposition for current needs?"

### 2. Technology Selection
- "Why this library over alternatives?"
- "What if this dependency is deprecated or abandoned?"
- "What's the migration cost if we need to switch?"

### 3. Error Handling
- "What happens when [external service] is down?"
- "Is this error recoverable? Should it be?"
- "Does the user get useful, actionable error messages?"

### 4. Testing
- "What edge case is NOT tested?"
- "Would this test catch a real regression?"
- "Are we testing behavior or implementation details?"

### 5. Configuration
- "Should this be configurable or hardcoded?"
- "What happens with invalid config values?"
- "Can we reduce the config surface area?"

## For Each Critique

1. State the concern clearly
2. Estimate the risk (low/medium/high)
3. Propose at least one alternative
4. Recommend: **ACCEPT RISK** / **CHANGE** / **INVESTIGATE**

## Output

```
Devil's Advocate Report

| Concern | Risk | Alternative | Recommendation |
|---------|------|-------------|----------------|
| [concern] | LOW/MED/HIGH | [alternative] | ACCEPT/CHANGE/INVESTIGATE |

Action Items:
- CHANGE: [specific changes to make]
- INVESTIGATE: [open questions to answer]
```
