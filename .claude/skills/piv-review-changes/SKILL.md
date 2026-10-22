---
name: piv-review-changes
description: Code review of uncommitted changes (or a git range) for bugs, security issues, and standards; writes a report. Use before committing, as the pre-commit gate.
argument-hint: "[git-range] (default: uncommitted changes vs HEAD)"
---

# Code Review

Perform a technical code review of what changed. This skill **reports; it does not fix** — fixing is
`piv-fix-review-findings`.

## Core Principles

Simplicity is the ultimate sophistication — every line should justify its existence. Code is read far more often
than it's written, and the best code is often the code you don't write. Review for clarity of intent and economy
of expression, but **report only what is actually wrong** (see Severity and Important below).

## What to Review

**Scope.** Default is the **uncommitted work**: staged + unstaged changes vs `HEAD`, plus untracked files. If
`$ARGUMENTS` names a git range or commit (e.g. `main..HEAD`, `HEAD~3`, `abc123`), review that instead.

Start by gathering codebase context to understand the codebase standards and patterns. Examine:

- CLAUDE.md
- README.md
- Key files in the core module
- Documented standards in the docs directory (and any `.claude/references/` docs)

After you have a good understanding, run:

```bash
# default (uncommitted)
git status
git diff HEAD
git diff --stat HEAD
git ls-files --others --exclude-standard      # new, untracked files
# range mode: replace `HEAD` above with the given range; untracked files don't apply
```

Read each new file in its entirety. Read each changed file in its entirety (not just the diff) to understand full context.

For each changed or new file, analyze for:

1. **Logic Errors**
   - Off-by-one errors
   - Incorrect conditionals
   - Missing error handling
   - Race conditions

2. **Security Issues**
   - SQL injection vulnerabilities
   - XSS vulnerabilities
   - Insecure data handling
   - Exposed secrets or API keys

3. **Performance Problems**
   - N+1 queries
   - Inefficient algorithms
   - Memory leaks
   - Unnecessary computations

4. **Code Quality** (report when it hides a bug or violates a documented project standard; otherwise Low or omit)
   - Violations of DRY principle
   - Overly complex functions
   - Poor naming
   - Missing or wrong types where the project enforces them (a type-checker failure, not a style preference)

5. **Adherence to Codebase Standards and Existing Patterns**
   - Adherence to standards documented in the docs directory
   - Linting, typing, and formatting standards
   - Logging standards
   - Testing standards

## Verify Issues Are Real

- Run specific tests for issues found
- Confirm type errors are legitimate (run the project's type-checker if it has one)
- Validate security concerns with context
- **Report only high-confidence issues.** Anything you could not confirm goes in the report marked
  `verification: Unverified` and does not count toward the verdict.

## Severity

Same table `piv-review-pr` uses, so findings carry the same meaning in both reviews:

| Severity | Meaning |
|----------|---------|
| **Critical** | Blocking — exploitable security flaw, data loss, crashes |
| **High** | Should fix before merge — type-safety holes, missing error handling, logic errors |
| **Medium** | Pattern inconsistencies, missing edge cases, hardening gaps, *undocumented* deviations from the plan |
| **Low** | Suggestions, minor polish |

Security findings take the severity of their impact: exploitable → Critical; a hardening gap → Medium/Low.

## Output Format

Save a new file to `.claude/code-reviews/<branch-or-topic>-<YYYY-MM-DD>.md` (create the folder if needed).
This file is what `piv-fix-review-findings` reads next.

**Stats** (from `git diff --shortstat` and the untracked list — fill in the real numbers):

- Files Modified: {n}
- Files Added: {n}
- Files Deleted: {n}
- New lines: {n}
- Deleted lines: {n}

**For each issue found:**

```
severity: critical|high|medium|low
file: path/to/file.ext
line: {n}
issue: [one-line description]
detail: [explanation of why this is a problem]
suggestion: [how to fix it]
verification: [how you confirmed it — test run / traced / reproduced — or Unverified]
```

**Verdict:** `PASS` (no Critical/High), `FAIL` (any Critical/High), and `NOT RUN` for any check you did not
perform (e.g. the type-checker wasn't available). If no issues found: "Code review passed. No technical issues
detected."

## Important

- Be specific (line numbers, not vague complaints)
- Focus on real bugs and documented-standard violations, not personal style
- Suggest fixes, don't just complain
- Don't fix anything here — hand the report to `piv-fix-review-findings`
