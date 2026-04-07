# Spec Document Review Prompt

Use this template when dispatching an antagonistic spec document reviewer.

**Purpose:** Verify the spec is complete, consistent, and ready for implementation planning.

## When to Use

Dispatch this reviewer after:
1. The brainstormer writes the spec document
2. The orchestrator's self-review passes (no obvious gaps)

## Dispatch Pattern

```python
delegate(
    agent=None,
    instruction=REVIEW_PROMPT,
    context_depth="none",
    model_role="critique",
)
```

## The Review Prompt

```
You are an antagonistic spec reviewer. Verify this spec is complete and ready for planning.

**Spec to review:** [SPEC_FILE_PATH]

## What to Check

| Category     | What to Look For                                                         |
|--------------|--------------------------------------------------------------------------|
| Completeness | TODOs, placeholders, "TBD", incomplete sections, missing requirements    |
| Consistency  | Internal contradictions, conflicting requirements, scope drift           |
| Clarity      | Ambiguities that could cause two engineers to build different things     |
| Scope        | Focused enough for one plan — not covering multiple independent systems  |
| YAGNI        | Unrequested features, over-engineering, speculative additions            |

## Calibration

**Only flag issues that would cause real problems during implementation planning.**
A missing section, a contradiction, or a requirement so ambiguous it causes
misimplementation — those are real issues. Minor wording improvements, stylistic
preferences, and sections that are less detailed than others are not issues.

Approve unless there are genuine gaps that would lead to a flawed or incomplete plan.

## Output Format

## Spec Review

**Status:** Approved | Issues Found

**Issues (if any):**
- [Section X]: [specific issue] — [why it causes an implementation problem]

**Recommendations (advisory, do not block approval):**
- [suggestions for improvement that are not blockers]
```

## Processing the Result

| Status       | Action                                                              |
|--------------|---------------------------------------------------------------------|
| Approved     | Proceed to Phase 7 (write implementation plan)                      |
| Issues Found | Delegate back to brainstormer with issues list, then re-run review  |

**Maximum 3 review cycles.** If issues persist after 3 cycles, escalate to the
user with a summary of the unresolved issues rather than continuing to loop.
