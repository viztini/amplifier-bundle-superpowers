# Superpowers Behavioral Parity Design

## Goal

Close 7 major behavioral gaps between amplifier-bundle-superpowers and the upstream obra/superpowers, bringing the Amplifier version to full behavioral parity.

## Background

amplifier-bundle-superpowers ports obra/superpowers into the Amplifier ecosystem, layering modes, agents, recipes, and context files on top of obra's 14 skills (which are pulled at runtime via tool-skills config). The port faithfully replicates the core behavioral rules but has gaps in several areas:

1. **Visual Companion for brainstorming** — completely absent
2. **Standalone holistic code reviewer agent** — only pipeline-scoped reviewers exist
3. **Spec self-review + antagonistic spec document review** — missing from brainstorm flow
4. **SDD worked example** — no concrete exemplar for agents to learn from
5. **Verification failure memories** — emotional grounding dropped
6. **Missing content in existing files** — TDD Iron Law, Red Flags, rationalization rows, model selection
7. **Wiring updates** — behavior YAML, mode tool policies

These gaps were identified through a comprehensive deep-dive comparison of both codebases. This design covers only the net behavioral effect differences — not structural/mechanical differences (modes vs skills, recipes, etc.) which are intentional adaptations.

## Approach

Port obra's proven implementations where they exist (visual companion scripts). Create Amplifier-native equivalents where adaptation is needed (code-reviewer agent, SDD walkthrough). Restore dropped content to existing files. Wire everything together through behavior YAML and mode updates.

## Architecture

The changes span seven areas that together close the behavioral gap. Each section is self-contained and can be implemented independently, though the wiring in Section 7 ties them all together.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Behavior YAML (Section 7)                    │
│  Registers new agent, updates tool policies, wires @mentions    │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│  Visual  │   Spec   │  Code    │   SDD    │ Verify   │ Content  │
│ Companion│  Review  │ Reviewer │ Walkthru │ Memories │ Restore  │
│ (Sec 1)  │ (Sec 2)  │ (Sec 3)  │ (Sec 4)  │ (Sec 5)  │ (Sec 6)  │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
```

## Components

### Section 1: Visual Companion

**Problem:** Brainstorming about visual topics (UI mockups, architecture diagrams, design comparisons) is limited to terminal text. obra has a browser-based visual companion that makes these conversations dramatically more effective.

#### New files: `scripts/`

Port 5 files verbatim from `obra-superpowers/skills/brainstorming/scripts/`:

| File | Purpose |
|------|---------|
| `scripts/server.cjs` | Zero-dependency Node.js HTTP + WebSocket server (~300 lines). Hand-rolled RFC 6455 WebSocket, fs.watch for content directory, auto-reload on new screens, idle timeout (30 min), owner-PID lifecycle tracking. |
| `scripts/start-server.sh` | Platform-aware launcher with `--project-dir`, `--host`, `--url-host`, `--foreground` flags. Auto-detects Windows/Codex/environments that reap background processes and switches to foreground mode. |
| `scripts/stop-server.sh` | Graceful shutdown with SIGTERM → SIGKILL escalation. Preserves persistent session directories, deletes `/tmp` sessions. |
| `scripts/frame-template.html` | Polished HTML/CSS frame with OS-aware light/dark theming, option cards (`.option` with `.letter` + `.content`), mockup containers, split views, pros/cons layout, selection indicator bar. |
| `scripts/helper.js` | Client-side WebSocket auto-reconnect, click capture on `[data-choice]` elements, `toggleSelect` for single/multi-select, selection indicator updates, `window.brainstorm.send()` API. |

These are proven, zero-dependency, platform-aware scripts with ~20+ iterative commits of refinement in obra.

#### New file: `context/visual-companion-guide.md`

Adapted from obra's visual-companion.md with Amplifier-specific patterns:

- **Platform section**: Uses Amplifier's `bash` tool for launching with `run_in_background` for server persistence across turns
- **The loop**: Adapted for Amplifier's delegate pattern — the brainstormer agent or orchestrator uses bash to write HTML content fragments to the content directory
- **Supplementary visuals**: Notes that if ecosystem tools like nano-banana or dot_graph are available, they can supplement the HTML companion (e.g., generating actual UI mockup images vs wireframe HTML). Framed as "consider the tools/skills/capabilities/agents available to you" rather than hard dependencies, since these tools may or may not be present.
- **Path resolution**: Scripts referenced via bundle path, resolved at runtime
- **Decision criteria**: When to use browser vs terminal:
  - **Browser**: UI mockups, architecture diagrams, side-by-side comparisons, design polish, spatial relationships
  - **Terminal**: Requirements, conceptual choices, tradeoff lists, technical decisions, clarifying questions
- **Content fragment authoring**: CSS classes available (`.options`, `.cards`, `.mockup`, `.split`, `.pros-cons`, mock elements), file naming conventions, the write→view→respond loop

#### Mode update: `modes/brainstorm.md`

- Add **Phase 1.5: Offer Visual Companion** — after understanding context, before asking questions. Decision: "Would the user understand this better by seeing it?" If visual questions ahead → offer with consent prompt, launch via bash. If purely conceptual → stay in terminal. Include obra's criteria for when browser vs terminal is appropriate.
- Add `bash` to safe tools (needed for launching/stopping the visual companion server)
- Add visual companion cleanup guidance — stop server when brainstorming ends or transitions
- Update the todo checklist at mode entry to include the new phase

#### Agent update: `agents/brainstormer.md`

- Add `@superpowers:context/visual-companion-guide.md` to @mentions
- Add `bash` tool declaration (for writing HTML content fragments to the companion server directory)

---

### Section 2: Spec Self-Review + Antagonistic Spec Review

**Problem:** The brainstorm flow produces a spec document but doesn't verify its quality before handing off to planning. obra has both self-review and antagonistic review (fresh agent with zero context) that catch placeholders, contradictions, and ambiguity.

#### New file: `context/spec-document-review-prompt.md`

A subagent prompt template for antagonistic spec review. After the brainstormer writes the design doc, the orchestrator dispatches a fresh agent (zero context) with ONLY the spec file.

**Review dimensions:**
- **Completeness** — TODOs, placeholders, "TBD", incomplete sections
- **Consistency** — internal contradictions, conflicting requirements
- **Clarity** — ambiguous requirements that could be interpreted two ways
- **Scope** — focused enough for a single plan or needs decomposition
- **YAGNI** — unrequested features, over-engineering

**Calibration:** "Only flag issues that would cause real problems during implementation planning." Minor wording improvements and stylistic preferences are NOT issues.

**Output format:**
- Status: Approved / Issues Found
- Issues list with section references and why it matters for planning
- Advisory recommendations (do not block approval)

#### Mode update: `modes/brainstorm.md`

- Add **Phase 6: Spec Self-Review** — after brainstormer writes the doc, orchestrator reviews for: (1) Placeholder scan, (2) Internal consistency, (3) Scope check, (4) Ambiguity check. Delegate back to brainstormer to fix any issues found.
- Add **Phase 7: User Review Gate** — explicit ask: "Spec written and reviewed. Please review and let me know if you want changes before we start the implementation plan." Wait for approval before transitioning to `/write-plan`.
- Update todo checklist to include Phases 6 and 7

#### Agent update: `agents/brainstormer.md`

- Add `@superpowers:context/spec-document-review-prompt.md` to @mentions

---

### Section 3: Standalone Code Reviewer Agent

**Problem:** The existing pipeline reviewers (spec-reviewer, code-quality-reviewer) are narrow, per-task reviewers that explicitly say "You do NOT make workflow decisions." There's no holistic reviewer that can flag cross-task integration issues, architectural concerns, and production readiness gaps across the full implementation.

#### New file: `agents/code-reviewer.md`

**Configuration:**
- **model_role**: `[critique, reasoning, general]` — evaluative work, not coding
- **Tools**: filesystem, bash, search, plus whatever code quality tools are available
- **Context @mentions**: `@superpowers:context/philosophy.md` for shared principles, `@foundation:context/LANGUAGE_PHILOSOPHY.md` if available

**Review dimensions:**
1. **Plan/Spec alignment** — does implementation match original design? Deviations justified or problematic?
2. **Code quality** — patterns, error handling, type safety, naming, maintainability
3. **Architecture** — SOLID, separation of concerns, coupling, integration with existing systems
4. **Test quality** — coverage, real behavior vs mock behavior, edge cases
5. **Documentation** — comments, function docs, file headers
6. **Production readiness** — logging, monitoring hooks, error recovery, security

**Output format:** Strengths → Critical issues (must fix) → Important (should fix) → Suggestions (nice to have), with `file:line` references.

**Wiring:**
- Registered in `behaviors/superpowers-methodology.yaml` agents include list
- Referenced from `modes/verify.md`: "For holistic code review of the complete implementation, delegate to superpowers:code-reviewer"
- Referenced from `modes/finish.md` as optional pre-merge step
- The `receiving-code-review` skill (already available from obra) handles processing this agent's feedback

---

### Section 4: SDD Worked Example

**Problem:** Agents learn best from concrete exemplars, not abstract rules. The subagent-driven development flow is complex (implementer returns statuses, reviewers catch issues, orchestrator manages loops) but has no worked example showing the realistic conversational flow with Amplifier-specific patterns.

#### New skill: `skills/sdd-walkthrough/`

| File | Purpose |
|------|---------|
| `SKILL.md` | Metadata, loadable via `load_skill("sdd-walkthrough")` |
| `five-task-example.md` | Complete worked example |

**Content:** A realistic 5-task scenario showing the full subagent-driven development conversational flow:

1. **Task 1 — Happy path**: Implementer returns DONE, spec review passes, code quality passes. Shows normal flow.
2. **Task 2 — Spec reviewer catches gap**: Missing requirement found. Shows fix loop: delegate back to implementer with specific gap, re-review passes.
3. **Task 3 — DONE_WITH_CONCERNS**: Implementer has doubts. Shows orchestrator noting concern and proceeding to review.
4. **Task 4 — Code quality issue**: Reviewer flags magic number, missing error handling. Shows quality fix loop.
5. **Task 5 — NEEDS_CONTEXT**: Implementer stuck. Shows orchestrator stopping, providing info, re-delegating.

Each task shows actual `delegate()` calls with realistic `instruction` text, `model_role`, and `context_scope` parameters — Amplifier-specific patterns, not generic.

**Referenced from:** `modes/execute-plan.md` adds note: "For a complete worked example of the SDD flow, `load_skill(skill_name='sdd-walkthrough')`"

---

### Section 5: Verification Failure Memories

**Problem:** The verification rules in verify mode are abstract ("always verify before claiming done"). obra grounds these rules with emotional urgency — concrete past incidents that create the visceral understanding of *why* verification matters. This emotional grounding was dropped in the port.

#### New file: `context/verification-failure-memories.md`

Short, punchy document (~30 lines) with 4-5 concrete failure scenarios framed as things that actually happen when verification is skipped:

- **"I don't believe you"** — Human partner lost trust after false completion claim. Trust, once broken, takes many sessions to rebuild.
- **Undefined functions shipped** — "Should work" turned into runtime crash because nobody ran the command.
- **Missing requirements discovered post-merge** — Tests passed, but spec had requirements tests didn't cover. Revert and redo.
- **Hours wasted on false completion** — "Done!" → "Wait, this doesn't work" → rework. The "shortcut" doubled total time.
- **Silent regression** — New feature worked, but existing feature broke. Nobody ran full suite.

These aren't hypotheticals — they're framed as things that actually happen.

#### Mode update: `modes/verify.md`

- Add `@superpowers:context/verification-failure-memories.md` — loads into context whenever verify mode is active, providing the emotional grounding that abstract rules lack.
- Add obra's **"When to Apply" trigger list**: ANY variation of success claims, ANY expression of satisfaction before running commands, ANY positive statement about work state, before commits, before PRs, before moving to next task.

---

### Section 6: Content Restoration in Existing Files

**Problem:** Several pieces of obra content were lost in the original port. These are proven behavioral anchors that make the difference between rules that get followed and rules that get rationalized away.

#### `context/tdd-depth.md` — restore 3 missing pieces

1. **The Iron Law** — add at the very top:
   ```
   NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
   ```
   This is the anchor statement that obra leads with. Currently `tdd-depth.md` jumps straight into anti-patterns without establishing the governing rule.

2. **Red Flags list (13 items)** — self-check thoughts that mean "STOP, you're rationalizing":
   - Writing code before the test
   - Test passes immediately on first run
   - "Just this once"
   - "This is different because..."
   - Keeping code as reference
   - Exploring before committing to TDD
   - etc.

   These are distinct from the rationalization *table* (which we have) — they're quick-scan self-checks.

3. **Bug Fix worked example** — concrete email validation example showing the full TDD cycle for a bug fix: write regression test → watch it fail → fix → watch it pass. Makes the abstract rules concrete.

#### `context/philosophy.md` — restore 6 missing rationalization rows

Add to the existing rationalization table:

| Rationalization | Reality |
|----------------|---------|
| "TDD is dogmatic, I'm being pragmatic" | TDD IS pragmatic. Shortcuts = debugging in production = slower. |
| "Tests after achieve the same thing" | Tests-first = "what should this do?" Tests-after = "what does this do?" Different questions. |
| "This is different because..." | It's not different. |
| "I'll add tests later" | Write them now or delete the code. |
| "Deleting working code is wasteful" | Sunk cost fallacy. Keeping unverified code is debt. |
| "Test is hard to write" | Hard to test = hard to use. Listen to the test. |

#### `modes/execute-plan.md` — add model selection guidance

Heuristic: "Use the appropriate model role for each task's complexity." Framed using Amplifier's `model_role` parameter:

| Complexity | Signal | model_role |
|-----------|--------|------------|
| Simple mechanical tasks | 1-2 files, clear spec | `"fast"` |
| Multi-file integration | Moderate complexity | `"coding"` |
| Architecture decisions, design review | High complexity | `"reasoning"` |

#### `modes/execute-plan.md` — add SDD walkthrough reference

Add note: "For a complete worked example of the SDD flow, `load_skill(skill_name='sdd-walkthrough')`"

---

### Section 7: Behavior YAML & Mode Tool Policy Updates

**Problem:** The new components need to be wired into the existing behavior system — registered in YAML, referenced from modes, connected via @mentions.

#### `behaviors/superpowers-methodology.yaml`

- Register `superpowers:code-reviewer` in agents include list
- Add `bash` to brainstorm mode safe tools (needed for visual companion server)

#### Consolidated mode updates

| Mode | Changes |
|------|---------|
| `brainstorm.md` | Phase 1.5 (visual companion offer), Phase 6 (spec self-review), Phase 7 (user review gate), `bash` in safe tools, updated todo checklist, visual companion cleanup |
| `verify.md` | @mention failure memories, "When to Apply" trigger list |
| `execute-plan.md` | Model selection guidance, SDD walkthrough reference |
| `finish.md` | Optional code-reviewer reference as pre-merge step |

#### Consolidated agent updates

| Agent | Changes |
|-------|---------|
| `brainstormer.md` | @mention `visual-companion-guide.md` and `spec-document-review-prompt.md`, add `bash` tool |

## Data Flow

### Visual Companion Flow

```
Orchestrator → brainstormer agent (with visual-companion-guide.md in context)
  → brainstormer decides: visual topic? → offers visual companion
  → user accepts → bash(start-server.sh, run_in_background)
  → brainstormer writes HTML fragments to content directory
  → server.cjs detects new files via fs.watch → pushes to browser via WebSocket
  → user clicks choices in browser → helper.js writes event file
  → brainstormer reads event file → incorporates choice → next question
  → brainstorm ends → bash(stop-server.sh)
```

### Spec Review Flow

```
Brainstormer writes spec document
  → Orchestrator runs Phase 6: self-review (placeholder scan, consistency, scope, ambiguity)
  → Issues found? → delegate back to brainstormer to fix → re-check
  → Clean? → dispatch fresh agent with spec-document-review-prompt.md (antagonistic review)
  → Issues found? → delegate back to brainstormer to fix → re-review
  → Phase 7: present to user for approval
  → User approves → transition to /write-plan
```

### Code Review Flow

```
Implementation complete → enter verify mode
  → Standard verification (tests pass, commands run)
  → Delegate to superpowers:code-reviewer (holistic review)
  → Reviewer returns: strengths, critical issues, important issues, suggestions
  → Process via receiving-code-review skill
  → Fix critical/important issues → re-verify
  → Enter finish mode → optional final review before merge/PR
```

## Error Handling

- **Visual companion server fails to start**: Guide includes Node.js prerequisite check. If unavailable, brainstormer falls back to terminal-only mode gracefully.
- **Spec review finds issues**: Loop back to brainstormer with specific gaps. Maximum review cycles should be bounded (recommend 3 iterations before escalating to user).
- **Code reviewer finds critical issues**: Issues are categorized by severity. Only "critical" blocks completion; "important" and "suggestions" are advisory.
- **SDD walkthrough skill fails to load**: Non-blocking — the execute-plan mode works without it, the walkthrough is supplementary learning material.
- **Verification failure memories not loaded**: Non-blocking — verify mode still has its rules, the memories add emotional grounding but aren't required for correct behavior.

## Testing Strategy

Each change should be validated:

| Component | Validation |
|-----------|------------|
| Visual companion | Launch server manually, verify HTML rendering, click capture, and event file writing |
| Code reviewer agent | Delegate a test review, verify output covers all 6 dimensions |
| Spec review flow | Run a brainstorm session, verify self-review and antagonistic review trigger correctly |
| SDD walkthrough | Load skill, verify content is coherent and Amplifier-specific |
| Failure memories | Enter verify mode, confirm the memories load into context |
| Content restoration | Verify `tdd-depth.md` has Iron Law at top, `philosophy.md` has all rows, `execute-plan.md` has model guidance |

## Open Questions

1. **DOT process flowcharts in mode files** — obra has them. Deferred — nice to have but not a behavioral gap.
2. **Pressure-testing recipe** — for validating modes/skills resist rationalization. Deferred — the writing-skills meta-skill is available from obra upstream, and a pressure-testing recipe is a separate initiative.
3. **Node.js prerequisite** — the visual companion scripts assume Node.js is available. Recommendation: add a note in the guide that Node.js is required, and the orchestrator should check before offering.
