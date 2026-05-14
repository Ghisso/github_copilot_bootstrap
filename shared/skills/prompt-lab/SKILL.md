---
name: prompt-lab
description: |
  Systematic LLM prompt engineering: analyzes existing prompts for failure
  modes, generates structured variants (direct, few-shot, chain-of-thought),
  designs evaluation rubrics with weighted criteria, and produces test case
  suites for comparing prompt performance. Use when:
  - "prompt engineering", "prompt lab", "generate prompt variants"
  - "A/B test prompts", "evaluate prompt", "optimize prompt"
  - "write a better prompt", "prompt design", "prompt iteration"
  - "few-shot examples", "chain-of-thought prompt", "prompt failure modes"
  - "improve this prompt"
  NOT for evaluating agent skills or configuration files.
---

# Prompt Lab

Replaces trial-and-error prompt engineering with structured methodology: objective definition, current prompt analysis, variant generation (instruction clarity, example strategies, output format specification), evaluation rubric design, test case creation, and failure mode identification.

## Prerequisites

- Clear objective: what should the prompt accomplish?
- Target model (GPT-4, Claude, open-source) — prompting techniques vary by model
- Current prompt (if improving) or task description (if creating)

## Workflow

### Phase 1: Define Objective

1. **Task specification** — What should the LLM produce? Be specific: "Classify customer support tickets into 5 categories" not "Handle support tickets."
2. **Success criteria** — How do you know the output is correct? Define measurable criteria before writing any prompt.
3. **Failure modes** — What does a bad output look like? Missing information? Wrong format? Hallucinated content? Refusal to answer?

### Phase 2: Analyze Current Prompt

If an existing prompt is provided:

1. **Structure assessment** — Is the instruction clear? Are examples provided? Is the output format specified?
2. **Ambiguity detection** — Where could the model misinterpret the instruction?
3. **Missing components** — What's not specified that should be? (output format, tone, length constraints, edge case handling)
4. **Failure mode mapping** — Which known failure patterns apply to this prompt?

#### Common failure modes

| Category | Pattern | Symptom |
|---|---|---|
| Instruction | Ambiguous directive | Model interprets differently than intended |
| Instruction | Missing constraints | Output too long/short/formal/casual |
| Examples | No examples for complex format | Inconsistent output structure |
| Examples | Examples contradict instruction | Model follows examples, ignores instructions |
| Format | No output schema specified | Unparseable or inconsistent output |
| Format | Overly rigid format | Model refuses or produces degenerate output |
| Context | Irrelevant context included | Model distracted by noise |
| Context | Critical context missing | Hallucinated facts fill the gap |
| Safety | No refusal handling | Model refuses valid requests |
| Safety | No boundary specification | Model answers out-of-scope queries |

### Phase 3: Generate Variants

Create 2-4 prompt variants, each testing a different hypothesis:

| Variant Type | Hypothesis | When to Use |
|---|---|---|
| Direct instruction | Clear instruction is sufficient | Simple tasks, capable models |
| Few-shot | Examples improve output consistency | Pattern-following tasks |
| Chain-of-thought | Reasoning improves accuracy | Multi-step logic, math, analysis |
| Persona/role | Role framing improves tone/expertise | Domain-specific tasks |
| Structured output | Format specification prevents errors | JSON, CSV, specific templates |

For each variant:

- State the hypothesis (why this variant might work)
- Identify the risk (what could go wrong)
- Provide the complete prompt text

### Phase 4: Design Evaluation

1. **Rubric** — Define weighted criteria:

   | Criterion | What It Measures | Typical Weight |
   |---|---|---|
   | Correctness | Output matches expected answer | 30-50% |
   | Format compliance | Follows specified structure | 15-25% |
   | Completeness | All required elements present | 15-25% |
   | Conciseness | No unnecessary content | 5-15% |
   | Tone/style | Matches requested voice | 5-10% |

2. **Test cases** — Minimum 5 cases covering:
   - Happy path (standard input)
   - Edge cases (unusual but valid input)
   - Adversarial cases (inputs designed to confuse)
   - Boundary cases (minimum/maximum input)

### Phase 5: Output

Present variants, rubric, and test cases in a structured format ready for execution.

## Output Format

```text
## Prompt Lab: {Task Name}

### Objective
{What the prompt should achieve — specific and measurable}

### Success Criteria
- [ ] {Criterion 1 — measurable}
- [ ] {Criterion 2 — measurable}

### Current Prompt Analysis
{If existing prompt provided}
- **Strengths:** {what works}
- **Weaknesses:** {what fails or is ambiguous}
- **Missing:** {what's not specified}

### Variants

#### Variant A: {Strategy Name}
{Complete prompt text}

**Hypothesis:** {Why this approach might work}
**Risk:** {What could go wrong}

#### Variant B: {Strategy Name}
{Complete prompt text}

**Hypothesis:** {Why this approach might work}
**Risk:** {What could go wrong}

#### Variant C: {Strategy Name}
{Complete prompt text}

**Hypothesis:** {Why this approach might work}
**Risk:** {What could go wrong}

### Evaluation Rubric

| Criterion | Weight | Scoring |
|-----------|--------|---------|
| {criterion} | {%} | {how to score: 0-3 scale or pass/fail} |

### Test Cases

| # | Input | Expected Output | Tests Criteria |
|---|-------|-----------------|----------------|
| 1 | {standard input} | {expected} | Correctness, Format |
| 2 | {edge case} | {expected} | Completeness |
| 3 | {adversarial} | {expected} | Robustness |

### Failure Modes to Monitor
- {Failure mode 1}: {detection method}
- {Failure mode 2}: {detection method}

### Recommended Next Steps
1. Run all variants against the test suite
2. Score using the rubric
3. Select the highest-scoring variant
4. Iterate on the winner with targeted improvements
```

## Prompt structure catalog

### Zero-shot

Direct instruction with no examples. Best for simple, well-defined tasks on capable models.

```text
{Role/context}
{Task instruction}
{Output format specification}
{Constraints}
```

### Few-shot

Provide 2-5 examples that demonstrate the desired input→output mapping. Examples should cover variety, not just the happy path.

```text
{Role/context}
{Task instruction}

Example 1:
Input: {input_1}
Output: {output_1}

Example 2:
Input: {input_2}
Output: {output_2}

Now process:
Input: {actual_input}
Output:
```

### Chain-of-thought (CoT)

Ask the model to reason step-by-step before giving the final answer. Best for multi-step logic, math, and analysis tasks.

```text
{Task instruction}

Think through this step by step:
1. First, {reasoning step 1}
2. Then, {reasoning step 2}
3. Finally, {conclusion step}

Provide your reasoning, then your final answer.
```

### Persona/role

Frame the model in a specific expert role. Improves domain-specific output quality and tone.

```text
You are a {specific role} with expertise in {domain}.
Your task is to {specific task}.
{Constraints and format}
```

### Structured output

Specify exact output schema. Use with JSON mode or function calling when available.

```text
{Task instruction}

Return your response as JSON matching this schema:
{
  "field_1": "description of field_1",
  "field_2": ["description of array items"],
  "field_3": {
    "nested_field": "description"
  }
}
```

## Output format constraints

Techniques for controlling LLM output format:

| Technique | Reliability | Use When |
|---|---|---|
| JSON mode (API parameter) | High | Model supports it natively |
| Function calling / tool use | High | Structured extraction with schema validation |
| Few-shot with format examples | Medium | Moderate format control needed |
| Explicit schema in prompt | Medium | Complex nested structures |
| "Return ONLY X, nothing else" | Low-Medium | Simple single-value outputs |
| XML tags in prompt | Medium | Claude-family models |

## Calibration Rules

1. **One variable per variant.** Each variant should change ONE thing from the baseline. Changing instruction style AND examples AND format simultaneously makes results uninterpretable.
2. **Test before declaring success.** A prompt that works on 3 examples may fail on the 4th. Minimum 5 diverse test cases before concluding a variant works.
3. **Failure modes are more valuable than successes.** Understanding WHY a prompt fails guides improvement more than confirming it works.
4. **Model-specific optimization.** A prompt optimized for GPT-4 may not work for Claude or Llama. Always note the target model.
5. **Simplest effective prompt wins.** If a zero-shot prompt scores as well as a few-shot prompt, use the zero-shot. Fewer tokens = lower cost + latency.

## Error Handling

| Problem | Resolution |
|---|---|
| No clear objective | Ask the user to define what "good output" looks like with 2-3 examples. |
| Prompt is for a task LLMs are bad at (math, counting) | Flag the limitation. Suggest tool-augmented approaches or pre/post-processing. |
| Too many variables to test | Focus on the highest-impact variable first. Iterative refinement beats combinatorial testing. |
| No existing prompt to analyze | Start with the simplest possible prompt. The first variant IS the baseline. |
| Output format requirements are strict | Use structured output mode (JSON mode, function calling) instead of prompt-only constraints. |

## When NOT to Use

Push back if:

- The task doesn't need an LLM (deterministic rules, regex, SQL) — use the right tool
- The user wants prompt execution, not design — this skill designs and evaluates, it doesn't run prompts
- The prompt is for safety-critical decisions without human review — LLM output should not be the sole input
