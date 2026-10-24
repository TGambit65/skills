---
name: ast-grep
description: Writes and tests ast-grep rules for structural code search - matching code by its syntax tree (AST) instead of text. Use when the user asks to find code patterns, specific language constructs, or structural queries that grep cannot express ("async functions without try/catch", "calls to X inside class methods").
---

# ast-grep Code Search

## Overview

Rule syntax is in `references/rule_reference.md`; load it when you need more than `pattern` / `kind` / `has` /
`inside`. Confirm `ast-grep --version` is installed before promising results.

## General Workflow

### Step 1: Understand the Query

Ask clarifying questions if needed:
- What specific code pattern or structure are they looking for?
- Which programming language?
- Are there specific edge cases or variations to consider?
- What should be included or excluded from matches?

### Step 2: Create Example Code

Write a simple code snippet that represents what the user wants to match, and save it to a temporary file for
testing - e.g. for "async functions that use await":

```javascript
// test_example.js
async function example() {
  const result = await fetchData();
  return result;
}
```

### Step 3: Write the ast-grep Rule

Translate the pattern into an ast-grep rule. Start simple and add complexity as needed:
1. Try a `pattern` first (simple, direct code matching)
2. If that doesn't work, try `kind` to match the node type
3. Add relational rules (`has`, `inside`) as needed - and give them `stopBy: end`, otherwise the search stops at
   the immediate neighbour (the default) and misses deeper matches
4. Combine with composite rules (`all`, `any`, `not`) for logic like "has await but no try/catch"

```yaml
# test_rule.yml
id: async-with-await
language: javascript
rule:
  kind: function_declaration
  has:
    pattern: await $EXPR
    stopBy: end
```

### Step 4: Test the Rule

Verify the rule matches the example code before touching the codebase:

```bash
# rule file (recommended for anything non-trivial)
ast-grep scan --rule test_rule.yml test_example.js

# inline rule against stdin (quick iterations; note the escaped \$)
echo "async function test() { await fetch(); }" | ast-grep scan --inline-rules "id: test
language: javascript
rule:
  kind: function_declaration
  has:
    pattern: await \$EXPR
    stopBy: end" --stdin
```

**Debugging if no matches:**
1. Simplify the rule (remove sub-rules) until something matches, then add them back one at a time
2. Add `stopBy: end` to relational rules if not present
3. Dump the tree with `--debug-query` (below) and check the `kind` names and metavariable placement
4. A metavariable must be the *entire* text of one node: `obj.on$EVENT` and `"Hello $WORLD"` never match

### Step 5: Search the Codebase

Once the rule matches the example code correctly, run it on the real code (add `--json` for structured output):

```bash
ast-grep scan --rule my_rule.yml /path/to/project          # rule file
ast-grep run --pattern 'console.log($ARG)' --lang javascript /path/to/project   # simple single-node pattern
```

## CLI quick reference

| Need | Command |
|---|---|
| Simple single-node pattern, no relational logic | `ast-grep run --pattern '<code>' --lang <lang> [paths]` |
| Full YAML rule from a file | `ast-grep scan --rule rule.yml [paths]` |
| Full YAML rule inline | `ast-grep scan --inline-rules "<yaml>" [paths]` |
| Feed code on stdin instead of files | add `--stdin` and pipe the code in |
| Machine-readable output | add `--json` |
| Inspect how code parses | `ast-grep run --pattern '<code>' --lang <lang> --debug-query=cst` |

`--debug-query` formats (requires `--lang`): `cst` (all nodes incl. punctuation - use this to find `kind`
names), `ast` (named nodes only), `pattern` (how ast-grep interprets your pattern and where it sees
metavariables), `sexp` (S-expression).

```bash
# See how ast-grep interprets your pattern
ast-grep run --pattern 'class $NAME { $$$BODY }' --lang javascript --debug-query=pattern
```

### Escaping in Inline Rules

The shell expands `$VAR` inside double quotes. Either escape it (`\$VAR`) or wrap the whole rule in single quotes.
`id` and `language` are required keys, even inline:

```bash
ast-grep scan --inline-rules "id: t
language: javascript
rule: {pattern: 'console.log(\$ARG)'}" .

ast-grep scan --inline-rules 'id: t
language: javascript
rule: {pattern: "console.log($ARG)"}' .
```

## Resources

`references/rule_reference.md` - every rule key (`pattern`, `kind`, `regex`, `nthChild`, `range`, `inside`,
`has`, `precedes`, `follows`, `all`, `any`, `not`, `matches`), the top-level YAML keys (`utils`, `constraints`,
`transform`, `fix`), metavariable syntax, and worked examples (functions with await, code inside a context,
missing try/catch, alternatives).
