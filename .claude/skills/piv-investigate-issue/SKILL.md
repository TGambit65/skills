---
name: piv-investigate-issue
description: Investigates a GitHub issue into an evidence-backed RCA (reproduce, parallel exploration, 5 Whys) under docs/issues/, before piv-implement-issue. Use to investigate, diagnose or find the root cause of a bug before fixing it.
argument-hint: [github-issue-id]
---

# Investigate Issue #$ARGUMENTS (Root-Cause Analysis)

## Objective

Investigate GitHub issue #$ARGUMENTS from this repository, identify the root cause, and document findings for future implementation. This skill changes no source code and switches no branches — investigate the checkout you are on and record which commit that was.

**Prerequisites:**
- Working in a local Git repository with GitHub origin
- GitHub CLI installed and authenticated (`gh auth status`)
- Valid GitHub issue ID from this repository (given a URL, use its trailing number as the id throughout)

## Investigation Process

### 1. Fetch GitHub Issue Details

**Use GitHub CLI to retrieve the issue, including its discussion:**

```bash
gh issue view $ARGUMENTS --comments
```

This fetches title, description, reporter, date, labels, status — and, only with `--comments`, the comments, which often hold the real reproduction steps.

### 2. Explore the Codebase — fan out in parallel

Dispatch two explorers **in parallel** (one message, multiple Task calls) so exploration is fast and the noisy
search stays out of your main context:
- **Analyst** — trace HOW the affected code works end-to-end: integration points, data flow,
  state/side effects, error handling. Return precise `file:line` references, no suggestions.
- **Researcher** — find WHERE the relevant code lives + patterns to mirror: the error
  strings from the issue, related functions/modules, similar implementations, existing test patterns.

Use the project's `codebase-analyst` / `research-agent` subagents if `.claude/agents/` defines them; this repo does
not ship them, so otherwise dispatch two built-in general-purpose subagents with the briefs above. With no subagents
at all, run both briefs yourself, in sequence, with the same `file:line` discipline.

Merge their findings into a short map (`file:line` + why each matters) before forming the root cause. *(This is
the parallel-subagent fan-out, applied to diagnosis.)*

### 3. Review Recent History — when was it introduced?

With the relevant paths now known, check recent changes to them and pin down when the bug entered:
```bash
git log --oneline -20 -- <relevant-paths>
git blame -L <start>,<end> <affected-file>   # who/when introduced the suspect lines
```
Decide: a recent **regression** vs a **long-standing** bug vs **original** behavior — it changes both the fix and the risk.

### 4. Reproduce First

Don't explain a bug you haven't seen. From the issue's steps and the Step 2 map, reproduce it the cheapest reliable
way — the closest existing test, a throwaway script or failing test, or exercising the code path directly — against
local/test state only, nothing destructive. Record the **exact command(s) and output**, plus `git rev-parse --short HEAD`.

Outcome is one of **Reproduced** (output shows the symptom) · **Not reproduced** (what you tried, what happened) ·
**Not attempted** (why: credentials, hardware, dataset…). Only **Reproduced** supports **Confidence: High**; a
reporter's screenshot or log is evidence, not verification.

### 5. Investigate Root Cause — the 5 Whys, with evidence

Don't stop at the symptom. Chain **why → because** until you reach the specific, fixable code, and back **every link
with `file:line` evidence**:
```
WHY does <symptom> happen? → because <cause A>   (evidence: file.ts:123 — <snippet>)
WHY <cause A>?             → because <cause B>   (evidence: file.ts:456 — <snippet>)
… ROOT CAUSE: <the exact code/logic to change>  (evidence: file.ts:789 — <snippet>)
```
Watch for: input-validation gaps, unhandled edge cases, race/timing issues, wrong assumptions, missing error
handling, integration mismatches.

### 6. Assess Impact

**Determine:**
- How widespread is this issue?
- What features are affected?
- Are there workarounds?
- What is the severity?
- Could this cause data corruption or security issues?

### 7. Propose Fix Approach

**Design the solution:**
- What needs to be changed?
- Which files will be modified?
- What is the fix strategy?
- Are there alternative approaches?
- What testing is needed? Give the validation commands this project actually uses (`package.json` scripts,
  `pyproject.toml`, `Makefile`, CI config) — the implementer runs them verbatim.
- Are there any risks or side effects?

## Output: Create RCA Document

Save analysis as: `docs/issues/issue-$ARGUMENTS.md` (create the directory if needed).

### Required RCA Document Structure

```markdown
# Root Cause Analysis: GitHub Issue #$ARGUMENTS

## Issue Summary

- **GitHub Issue ID**: #$ARGUMENTS
- **Issue URL**: [Link to GitHub issue]
- **Title**: [Issue title from GitHub]
- **Reporter**: [GitHub username]
- **Status**: [Current GitHub issue status]
- **Investigated at commit**: [short SHA + branch, from Step 4]

## Assessment

Each value needs a one-line reason grounded in the investigation (not a guess):

| Metric | Value | Reasoning |
|--------|-------|-----------|
| Severity | Critical/High/Medium/Low | user impact · workaround · scope of failure |
| Complexity | Low/Medium/High | files touched · integration points · risk |
| Confidence | High/Medium/Low | evidence quality · unknowns · assumptions · reproduced? |

> **Confidence is the human-attention signal:** LOW confidence = a human should look before the fix runs. Say it honestly. HIGH requires a reproduction you performed.

## Problem Description

[Clear description of the issue]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Symptoms:**
- [List observable symptoms]

## Reproduction

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Observe issue]

**Reproduction Verified:** [Reproduced / Not reproduced / Not attempted — with reason]

**Reproduction Command and Output:**
```
[exact command(s) from Step 4]
[trimmed output showing the symptom — or what happened instead]
```

## Root Cause

### Affected Components

- **Files**: [List of affected files with paths]
- **Functions/Classes**: [Specific code locations]
- **Dependencies**: [Any external deps involved]

### Analysis

[Detailed explanation of the root cause]

**Evidence Chain (5 Whys):**
```
WHY <symptom> → because <cause>          (evidence: file:line — snippet)
… ROOT CAUSE: <the exact fixable thing>  (evidence: file:line — snippet)
```

**Why This Occurs:**
[Explanation of the underlying issue]

**Code Location:**
```
[File path:line number]
[Relevant code snippet showing the issue — the implementer diffs against this to detect drift]
```

### Related Issues

- [Any related issues or patterns]

## Impact Assessment

**Scope:**
- [How widespread is this?]

**Affected Features:**
- [List affected features]

**Severity Justification:**
[Why this severity level]

**Data/Security Concerns:**
[Any data corruption or security implications]

## Proposed Fix

### Fix Strategy

[High-level approach to fixing]

### Files to Modify

1. **[file-path]**
   - Changes: [What needs to change]
   - Reason: [Why this change fixes it]

2. **[file-path]**
   - Changes: [What needs to change]
   - Reason: [Why this change fixes it]

### Alternative Approaches

[Other possible solutions and why the proposed approach is better]

### Risks and Considerations

- [Any risks with this fix]
- [Side effects to watch for]
- [Breaking changes if any]

### Testing Requirements

**Test Cases Needed:**
1. [Test case 1 - verify fix works; must fail on the current code]
2. [Test case 2 - verify no regression]
3. [Test case 3 - edge cases]

**Validation Commands:**
```bash
[Exact lint / type-check / test commands this project uses, with the working directory if it matters]
```

## Implementation Plan

[Brief overview of implementation steps]

This RCA document should be used by the `piv-implement-issue` skill.

## Next Steps

1. Review this RCA document
2. Run the `piv-implement-issue` skill with issue #$ARGUMENTS to implement the fix
3. Run the `piv-commit` skill after implementation complete
```

## Post the summary to the issue

After writing the doc, post a short version as a GitHub comment — an audit trail, and so the fix can be
triggered/tracked from the issue itself:
```bash
gh issue comment $ARGUMENTS --body "<title · the Assessment table (severity/complexity/confidence + one-line reasons) · root cause in 1–2 lines · reproduction status · files to change · next: /piv-implement-issue $ARGUMENTS>"
```
Ask first if the repo is public and the RCA describes a security weakness, or if the user asked for a local-only
investigation. If `gh` is not authenticated, skip and say so.

## Edge cases

- **Already closed** → report it; still write the RCA if analysis is wanted.
- **Already has a linked PR** → warn; confirm before continuing.
- **Can't pin the root cause** → set **Confidence: LOW**, document the best hypothesis + what's uncertain, and flag it for a human before any fix.
- **Can't reproduce** → still write the RCA with Reproduction Verified = Not reproduced, Confidence at most Medium, and what a reproduction would need.
- **Scope too large** → suggest splitting into smaller issues; focus this RCA on the core problem and list the rest as out-of-scope.
