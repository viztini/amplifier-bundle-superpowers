---
name: sdd-walkthrough
description: Use when about to orchestrate a subagent-driven-development execute-plan session — provides 5 realistic task scenarios with Amplifier delegate() patterns, model_role selection, status handling (DONE, DONE_WITH_CONCERNS, NEEDS_CONTEXT), and fix loops for spec and quality issues
---

# SDD Walkthrough

**Purpose:** Load this when about to orchestrate an execute-plan session. Provides concrete worked examples of all five common task outcomes so you know exactly what delegate() calls to make and how to respond to each reviewer verdict.

## Why This Skill Exists

The subagent-driven-development skill describes the process. This skill shows it in action — real delegate() call syntax, realistic reviewer responses, and the decisions an orchestrator makes at each step. Reference it before you start so the patterns are fresh when edge cases appear.

## Scenarios Covered

| # | Task | Outcome Pattern | Key Technique |
|---|------|-----------------|---------------|
| 1 | Validate email format | Happy path: DONE → spec PASS → quality PASS | context_depth='none', model_role='coding' |
| 2 | Domain reachability check | Spec gap caught: impl raises instead of returns False | Re-delegate with specific gap description |
| 3 | In-memory rate limiter | DONE_WITH_CONCERNS: multi-worker incompatibility | Note concern, proceed to review, surface to user |
| 4 | Validation endpoint wiring | Quality issues: magic number + missing error handling | Fix loop with attempt counter in instruction |
| 5 | Error response handler | NEEDS_CONTEXT: can't find error format | Grep investigation, re-delegate with discovery |

## Companion File

See `five-task-example.md` for the complete worked example — all five tasks with full delegate() calls, implementer/reviewer responses, fix loops, and a completion summary.

## Quick Reference: delegate() Call Shapes

```python
# Implementer — always fresh context, coding model
delegate(
    agent="superpowers:implementer",
    instruction="...",   # full task spec + scene-setting context
    context_depth="none",
    model_role="coding",
)

# Spec reviewer — needs recent agent results to see what was built
delegate(
    agent="superpowers:spec-reviewer",
    instruction="...",   # task spec + commit refs
    context_depth="recent",
    context_scope="agents",
)

# Code quality reviewer — same context shape as spec reviewer
delegate(
    agent="superpowers:code-quality-reviewer",
    instruction="...",   # commit refs + what was changed
    context_depth="recent",
    context_scope="agents",
)
```

## Status Handling Cheat Sheet

| Status | Meaning | Orchestrator Action |
|--------|---------|---------------------|
| `DONE` | Task complete, tests pass | Proceed to spec review |
| `DONE_WITH_CONCERNS` | Complete but flagged an issue | Read concern, note it, proceed to review |
| `NEEDS_CONTEXT` | Missing info to proceed | Investigate (grep/read), re-delegate with context |
| `BLOCKED` | Cannot complete at all | Assess blocker, provide context or escalate |
