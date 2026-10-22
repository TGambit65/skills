---
name: piv-plan-implementation
description: Turns a ticket (Jira/Linear/GitHub key or URL, or docs/tickets/) or a free-form feature request into a one-pass-ready implementation plan via codebase analysis, a clarifying interview and research. Use before writing code.
argument-hint: "[ticket key/URL (fetched from your tracker), or a free-form feature description]"
---

# Plan a new task

## Feature: $ARGUMENTS

## Resolve the input first

`$ARGUMENTS` is one of three things. Tell them apart and handle each:

- **A tracker ticket** (a key such as `ABC-123`, or a Jira / Linear / GitHub issue URL): **fetch it before you
  plan** (Jira via the Atlassian MCP, GitHub via `gh issue view`, etc.). Read its summary, acceptance criteria,
  and per-ticket context. Then **follow its links up to the epic and the epic's linked architecture page**
  (Confluence via the Atlassian MCP) and inherit those decisions (see "Inherit, don't re-decide"). Never plan
  from the bare key.
- **A local ticket** from `piv-slice-epic` — a `TICKET-n` in `docs/tickets/<epic-slug>.md`: read that ticket's
  section, the epic summary at the top of the file, and its `Depends on:` line. Treat it like a tracker ticket.
- **A free-form description**: plan directly from it (greenfield or ad-hoc), asking clarifying questions as
  needed.

## Mission

Produce a **context-rich implementation plan** — we do NOT write code in this phase. The plan must contain ALL
information needed for implementation (patterns, mandatory reading, documentation, validation commands) so the
execution agent succeeds on the first attempt.

**Inherit, don't re-decide**: This is a **per-ticket** plan. If the ticket belongs to an epic that already has
architecture decisions — a **linked architecture page** (e.g. a Confluence page from the `plan-architecture`
skill, reached from the ticket's epic), an `## Architecture` / `## Engineering` section on the epic, or a local
`architecture.md` / `engineering-plan.md` — **read it first** and treat its cross-cutting calls (stack & versions,
data model, security boundaries, the seams new code plugs into) as **already decided**. Plan only what's left at
the ticket level: the specific files, the local patterns to mirror, the tests. If a ticket genuinely needs to
break an epic-level decision, flag it in Open Questions rather than silently diverging.

**Non-interactive mode**: the default is interactive — Phase 2 has a hard GATE. If the caller says the run is
unattended (e.g. invoked by `piv-run-full-loop`), the GATE does not stop; see "If they decline" in Phase 2 for
what happens to every open question instead. Never guess silently in either mode.

## Planning Process

Use subagents and parallel analysis where they help (Phases 2 and 3 especially).

### Phase 1: Feature Understanding

- Extract the core problem being solved
- Identify user value and business impact
- Determine feature type: New Capability / Enhancement / Refactor / Bug Fix
- Assess complexity: Low / Medium / High
- Map affected systems and components
- Write the user story (`As a <type of user> / I want to <action/goal> / So that <benefit/value>`), or refine the
  one the user provided

### Phase 2: Codebase Intelligence Gathering

**1. Project Structure Analysis**

- Detect primary language(s), frameworks, and runtime versions
- Map directory structure and architectural patterns
- Identify service/component boundaries and integration points
- Locate configuration files (pyproject.toml, package.json, etc.)
- Find environment setup and build processes

**2. Pattern Recognition**

- Search for similar implementations in codebase
- Identify coding conventions: naming (CamelCase, snake_case, kebab-case), file organization and module
  structure, error handling, logging patterns and standards
- Extract common patterns for the feature's domain
- Document anti-patterns to avoid
- Check CLAUDE.md for project-specific rules and conventions

**3. Dependency Analysis**

- Catalog external libraries relevant to feature
- Understand how libraries are integrated (check imports, configs)
- Find relevant documentation in docs/, ai_docs/, .claude/references or ai-wiki if available
- Note library versions and compatibility requirements

**4. Testing Patterns**

- Identify test framework and structure (pytest, jest, etc.)
- Find similar test examples for reference
- Understand test organization (unit vs integration)
- Note coverage requirements and testing standards

**5. Integration Points**

- Identify existing files that need updates
- Determine new files that need creation and their locations
- Map router/API registration patterns
- Understand database/model patterns if applicable
- Identify authentication/authorization patterns if relevant

**Clarify Ambiguities — GATE:**

**GATE** means: post the questions, then stop. End the turn and wait for the answers. Do not ask and answer in
the same breath, and do not roll into Phase 3.

Ask in **one cluster**, numbered, 3-6 questions max, each carrying a **recommended default** so answering is
cheap ("I'll mirror the first unless you say otherwise"). Draw them only from what the analysis actually left
open:

1. **Scope boundary** — the adjacent thing a reasonable reader would assume is in scope. Confirm it is out.
2. **Pattern fork** — two existing patterns both fit. Name both with `file:line` and ask which to mirror.
3. **Contract shape** — the API surface, payload, or data-model change the ticket implies but never states.
4. **Failure behavior** — what happens on the error path the ticket is silent about.
5. **Preference** — a library or trade-off with no precedent in this codebase to inherit.
6. **Done** — an acceptance criterion that is missing, or written so that it cannot be checked.

Skip any category with nothing genuinely open; never manufacture questions to fill the list. If the ticket, its
epic and the architecture doc genuinely settle everything, say so in one line and proceed. Silence is not the
same as clearance.

**Thin answers:** reflect a vague answer back as the concrete choice it leaves open ("'handle errors gracefully'
— a 4xx with a message, or retry then 503?") and ask once more. Never upgrade a vague answer into a confident plan.

**If they decline** ("just write it"), **or the run is non-interactive**: honour it, but name what you are
guessing. Post the cluster anyway so it is on the record, take each recommended default, and turn every
unanswered item into an `Assumed — <the assumption>, confirm before execution` line in
`OPEN QUESTIONS / ASSUMPTIONS`; the task it affects carries a `**GOTCHA**` naming it.

### Phase 3: External Research & Documentation

**Documentation Gathering:**

- Research latest library versions and best practices
- Find official documentation with specific section anchors
- Locate implementation examples and tutorials
- Identify common gotchas and known issues
- Check for breaking changes and migration guides

**Technology Trends:**

- Find relevant blog posts, guides, or case studies
- Identify performance optimization patterns
- Document security considerations

Compile what you find in the shape of the plan's `Relevant Documentation` section: link with a section anchor,
the specific section, and *why* it is needed.

### Phase 4: Deep Strategic Thinking

**Think Harder About:**

- How does this feature fit into the existing architecture?
- What are the critical dependencies and order of operations?
- What could go wrong? (Edge cases, race conditions, errors)
- How will this be tested comprehensively?
- What performance implications exist?
- Are there security considerations?
- How maintainable is this approach?

**Design Decisions:**

- Choose between alternative approaches with clear rationale
- Design for extensibility and future modifications
- Plan for backward compatibility if needed
- Consider scalability implications

### Phase 5: Plan Structure Generation

Fill this template for the implementation agent. Keep every heading (other skills read them); "Template
guidance" below covers the sections that need more than their placeholder.

```markdown
# Feature: <feature-name>

The following plan should be complete, but validate documentation, codebase patterns and task sanity before you
start implementing. Pay special attention to naming of existing utils, types and models — import from the right
files.

## Feature Description

<Detailed description of the feature, its purpose, and value to users>

## User Story

As a <type of user>
I want to <action/goal>
So that <benefit/value>

## Problem Statement

<The specific problem or opportunity this feature addresses>

## Solution Statement

<The proposed solution approach and how it solves the problem>

## Out of Scope / Non-Goals

- Not included: <thing> (defer to <later / separate ticket>)
- Not changing: <existing behavior to leave alone>

## Feature Metadata

**Feature Type**: [New Capability/Enhancement/Refactor/Bug Fix]
**Estimated Complexity**: [Low/Medium/High]
**Primary Systems Affected**: [List of main components/services]
**Dependencies**: [External libraries or services required]

## Related Work

**Implements**: <ticket id / link>   ·   **Epic**: <engineering-plan.md path or epic link, if inherited>

**Back-references** (plans this builds on or inherits decisions from):

- `.claude/plans/<prior-plan>.md` - Why: <shares the auth seam / reuses the X service>

**Forward-references** (plans that extend or supersede this — append as follow-ups get created):

- (none yet)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `path/to/file.py` (lines 15-45) - Why: Contains pattern for X that we'll mirror
- `path/to/test.py` - Why: Test pattern example

### New Files to Create

- `path/to/new_service.py` - Service implementation for X functionality
- `tests/path/to/test_new_service.py` - Unit tests for new service

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Documentation Link](https://example.com/doc1#section)
  - Specific section: <e.g. Authentication setup>
  - Why: <e.g. Required for implementing secure endpoints>

### Patterns to Follow

<Specific patterns extracted from codebase — include actual code examples from the project>

**Naming Conventions:** / **Error Handling:** / **Logging Pattern:** / **Other Relevant Patterns:**

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

<Base structures (schemas, types, interfaces), dependencies, foundational utilities>

### Phase 2: Core Implementation

**Depends on:** Phase 1 (needs the base schemas/types)

<Core business logic, service layer, API endpoints or interfaces, data models>

### Phase 3: Integration

<Connect to existing routers/handlers, register components, update configuration, middleware if needed>

### Phase 4: Testing & Validation

<Unit tests per component, integration tests for the workflow, edge cases, validation against acceptance criteria>

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### {ACTION} {target_file}

- **IMPLEMENT**: {Specific implementation detail}
- **PATTERN**: {Reference to existing pattern - file:line}
- **IMPORTS**: {Required imports and dependencies}
- **GOTCHA**: {Known issues or constraints to avoid, including any `Assumed —` item this task depends on}
- **VALIDATE**: `{executable, non-interactive validation command}`
- **SATISFIES**: {which acceptance criterion this task advances — e.g. AC #2}

<Continue with all tasks in dependency order...>

---

## TESTING STRATEGY

<Testing approach based on the project's test framework and patterns discovered during research>

### Unit Tests

<Scope and requirements per project standards; fixtures and assertions follow the existing approach>

### Integration Tests

<Scope and requirements per project standards>

### Edge Cases

<Specific edge cases that must be tested for this feature>

---

## VALIDATION COMMANDS

<Commands from the project's tools discovered in Phase 2.> Execute every command to ensure zero regressions and
100% feature correctness.

### Level 1: Syntax & Style
<Project-specific linting and formatting commands>
### Level 2: Unit Tests
<Project-specific unit test commands>
### Level 3: Integration Tests
<Project-specific integration test commands>
### Level 4: Manual Validation
<Feature-specific manual testing steps - API calls, UI testing, etc.>
### Level 5: Additional Validation (Optional)
<MCP servers or additional CLI tools if available>

---

## ACCEPTANCE CRITERIA

<Specific, measurable, feature-level criteria. Numbered so tasks can cite them in SATISFIES.>

- [ ] AC #1: <functionality the feature must implement>
- [ ] AC #2: <...>

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order, each task's VALIDATE passed immediately
- [ ] All validation commands executed successfully — full suite (unit + integration), no lint or type errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met; no regressions in existing functionality
- [ ] Code follows project conventions; reviewed for quality and maintainability
- [ ] Unit test coverage meets the project's requirement (<threshold>; 80%+ if the project states none)
- [ ] Documentation updated · performance requirements met · security considerations addressed (each if applicable)

---

## OPEN QUESTIONS / ASSUMPTIONS

<Assumptions this plan makes, each as `Assumed — <assumption>, confirm before execution`, and any question that —
if answered differently — would change the plan.>

## NOTES (open canvas)

<Your *reasoning*, unconstrained: alternatives weighed and rejected and why, tradeoff matrix, sequencing or
rollout risk, data-flow sketch, open threads, links.>

## AMENDMENTS

<Append-only history of changes made AFTER this plan was first approved/executed; newest at the bottom; empty at
creation.>

- <ISO date> — <what changed and why, e.g. "scope cut: deferred bulk-import to a follow-up ticket after AC review">
```

**Template guidance**:

- **Out of Scope / Non-Goals** — bound the work explicitly. Name the things a reasonable reader might assume are
  in scope but aren't.
- **Related Work** — the plan's place in the larger graph, distinct from CONTEXT REFERENCES (files/docs to read
  for *this* implementation).
- **IMPLEMENTATION PLAN phases** run **top to bottom by default** — each assumes the one above it is done.
  Where that is NOT the true dependency, add a `**Depends on:**` line under the phase header, and an
  `**Independent of:**` line where two phases don't block each other. Independent phases are candidates to run
  in **parallel** (separate worktrees / parallel loops). Only annotate where it changes execution order or
  unlocks parallelism — skip the obvious sequential case.
- **STEP-BY-STEP TASKS** use information-dense action keywords: **CREATE** (new files or components),
  **UPDATE** (modify existing files), **ADD** (insert new functionality into existing code), **REMOVE** (delete
  deprecated code), **REFACTOR** (restructure without changing behavior), **MIRROR** (copy a pattern from
  elsewhere in the codebase). Every task carries a VALIDATE command and a SATISFIES criterion.
- **OPEN QUESTIONS / ASSUMPTIONS** — flag unresolved critical questions for the user before execution; in
  non-interactive mode this list is what the caller surfaces for confirmation.

## Output Format

**Filename**: `.claude/plans/{kebab-case-descriptive-name}.md` — a short, descriptive feature name, e.g.
`add-user-authentication.md`. Create `.claude/plans/` if it doesn't exist. The basename is the plan slug `piv-implement` uses for its branch and report.

## Quality Criteria

The goal is **one-pass implementation**: the execution agent finishes without additional research or
clarification. Check before reporting:

**Context Completeness**

- [ ] All necessary patterns identified and documented
- [ ] External library usage documented with links
- [ ] Integration points clearly mapped
- [ ] Gotchas and anti-patterns captured
- [ ] Every task has at least one executable, non-interactive validation command
- [ ] Phase 2's clarifying cluster was asked and answered, explicitly recorded as nothing open, or (declined /
      non-interactive) recorded as `Assumed —` lines

**Implementation Ready**

- [ ] Passes the "No Prior Knowledge Test": someone unfamiliar with the codebase could execute using only the
      plan's content
- [ ] Tasks ordered by dependency (can execute top-to-bottom)
- [ ] Each task is atomic and independently testable
- [ ] Pattern references include specific file:line numbers

**Pattern Consistency**

- [ ] Tasks follow existing codebase conventions
- [ ] New patterns justified with clear rationale
- [ ] No reinvention of existing patterns or utils
- [ ] Testing approach matches project standards

**Information Density**

- [ ] No generic references (all specific and actionable)
- [ ] URLs include section anchors when applicable
- [ ] Task descriptions use codebase keywords

## Report

After creating the plan, provide:

- Summary of feature and approach
- Full path to the created plan file
- Complexity assessment
- Key implementation risks or considerations
- Every `Assumed —` line from OPEN QUESTIONS / ASSUMPTIONS (or "none")
- Confidence score: #/10 that execution succeeds on the first attempt
