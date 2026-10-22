# ast-grep Rule Reference

Rule syntax for ast-grep, condensed from the official docs (`https://ast-grep.github.io/reference/rule.html` and
`/reference/yaml.html`). Checked against those pages at time of writing; the tool evolves, so when something here
disagrees with `ast-grep --help` or the docs, the docs win.

## Rule Categories

A rule object is a YAML map whose keys fall into three categories:

* **Atomic rules** match a node by its own properties: `pattern`, `kind`, `regex`, `nthChild`, `range`.
* **Relational rules** match a node by its position relative to other nodes: `inside`, `has`, `precedes`, `follows`.
* **Composite rules** combine rules with logic: `all`, `any`, `not`, `matches`.

Every key is optional, but at least one **positive** key must be present. A rule is positive if it only matches
nodes of specific kinds: `kind` and `pattern` are positive; `regex` is not (it can match a node of any kind), so
`regex` alone is not a valid rule.

All keys in one rule object are ANDed. When later keys depend on metavariables captured by earlier ones, use an
explicit `all` list so the matching order is guaranteed.

## Rule Object Properties

| Property | Type | Category | Purpose | Example |
| :--- | :--- | :--- | :--- | :--- |
| `pattern` | String or Object | Atomic | Matches by code pattern. | `pattern: console.log($ARG)` |
| `kind` | String | Atomic | Matches by tree-sitter node kind. | `kind: call_expression` |
| `regex` | String | Atomic | Rust regex against the node's full text. | `regex: ^[a-z]+$` |
| `nthChild` | number, string, Object | Atomic | Matches by index among the parent's named children. | `nthChild: 1` |
| `range` | RangeObject | Atomic | Matches by start/end position. | `range: { start: { line: 0, column: 0 }, end: { line: 0, column: 10 } }` |
| `inside` | Object | Relational | Target must be inside a node matching the sub-rule. | `inside: { pattern: class $C { $$$ }, stopBy: end }` |
| `has` | Object | Relational | Target must have a descendant matching the sub-rule. | `has: { pattern: await $EXPR, stopBy: end }` |
| `precedes` | Object | Relational | Target must appear before a node matching the sub-rule. | `precedes: { pattern: return $VAL }` |
| `follows` | Object | Relational | Target must appear after a node matching the sub-rule. | `follows: { pattern: import $M from '$P' }` |
| `all` | Array<Rule> | Composite | Matches if all sub-rules match. | `all: [ { kind: call_expression }, { pattern: foo($A) } ]` |
| `any` | Array<Rule> | Composite | Matches if any sub-rule matches. | `any: [ { pattern: foo() }, { pattern: bar() } ]` |
| `not` | Object | Composite | Matches if the sub-rule does not match. | `not: { pattern: console.log($ARG) }` |
| `matches` | String | Composite | Matches if the named `utils` rule matches. | `matches: my-utility-rule-id` |

## Atomic Rules

### pattern: String and Object Forms

**String pattern** - code with metavariables, matched structurally. Pattern code must itself parse as valid code
in the target language.

```yaml
pattern: console.log($ARG)
```

**Object pattern** - for code that does not parse on its own, or to pin down which node of the parsed pattern is
the matcher:

* `context`: surrounding code so the fragment parses.
* `selector`: the node kind within `context` that is the actual matcher.
  ```yaml
  pattern:
    selector: field_definition
    context: class { $F }
  ```
* `strictness`: the matching algorithm - `cst`, `smart` (default), `ast`, `relaxed`, `signature`.
  ```yaml
  pattern:
    context: foo($BAR)
    strictness: relaxed
  ```

### kind: Matching by Node Type

The node's kind name from the language's tree-sitter grammar (`call_expression`, `function_declaration`, …).
Find the right name with `ast-grep run --pattern '<code>' --lang <lang> --debug-query=cst`, or in the playground.

```yaml
kind: call_expression
```

ast-grep 0.39+ also accepts a limited ESQuery-style selector here, e.g. `kind: call_expression > identifier`.

### regex: Text-Based Node Matching

A Rust regular expression matched against the node's full text, children included. A match **anywhere** in the
text satisfies the rule; anchor with `^` and `$` to require the entire text. Rust regex has no look-around or
backreferences. Not positive - pair it with `kind` or `pattern`.

### nthChild: Positional Node Matching

1-based index among the parent's **named** children.

* `number`: the exact nth child - `nthChild: 1`
* `string`: An+B formula - `nthChild: 2n+1`
* `Object`: `position` (number or An+B), `reverse: true` to count from the end, `ofRule` to filter the sibling
  list with a rule before counting.

### range: Position-Based Node Matching

`start` and `end`, each with 0-based, character-based `line` and `column`. `start` is inclusive, `end` exclusive.

## Relational Rules

A relational rule is a rule object plus `stopBy` (all four) and `field` (`inside` and `has` only).

```yaml
inside:            # target is inside a node matching this
  pattern: class $C { $$$ }
  stopBy: end
has:               # target has a descendant matching this
  pattern: await $EXPR
  stopBy: end
precedes:          # target appears before a node matching this
  pattern: return $VAL
follows:           # target appears after a node matching this
  pattern: import $M from '$P'
```

**stopBy** controls how far the search goes:

* `neighbor` (default): stop as soon as the immediate surrounding node does not match. This is why a bare `has`
  often finds nothing - the first child is not the `await`, so the search ends.
* `end`: search to the end of the direction (root for `inside`, leaves for `has`).
* a rule object: stop when a surrounding node matches that rule (inclusive).

**field**: restrict the relational check to one named field of the target node (e.g. `field: body`), for `inside`
and `has` only.

Best practice: use `stopBy: end` unless you specifically want the neighbour-only behaviour.

## Composite Rules

```yaml
all:                              # AND - also fixes evaluation order for metavariables
  - kind: call_expression
  - pattern: console.log($ARG)

any:                              # OR - captures come only from the sub-rule that matched
  - pattern: console.log($ARG)
  - pattern: console.warn($ARG)

not:                              # NOT - one sub-rule
  pattern: console.log($ARG)
```

`all` and `any` compose *rules*, not *nodes*: `all` never matches several nodes at once, even combined with
`has`/`inside`.

### matches: Rule Reuse and Utility Rules

`matches` takes the id of a rule declared under the top-level `utils` key (below) and matches if that rule
matches. Utility rules may reference each other, which allows recursive rules.

```yaml
utils:
  isFunction:
    any:
      - kind: function_declaration
      - kind: arrow_function
rule:
  matches: isFunction
```

## Top-level YAML keys beyond `rule`

A rule *file* is a YAML document (several may be separated by `---`). `id`, `language`, and `rule` are required;
these optional keys sit beside them:

| Key | Purpose |
| :--- | :--- |
| `utils` | Map of named rule objects usable via `matches`. |
| `constraints` | Map of metavariable name (without `$`) → rule. Applied *after* `rule` to filter matches. Only for single metavariables (`$ARG`), not `$$$ARGS`. Constrained metavariables usually do not work inside `not`. |
| `transform` | Map of new variable name → transformation (e.g. `replace` with `source`/`replace`/`by`) applied to a captured metavariable, for use in `fix`/`message`. See the docs' transformation reference for the full set. |
| `fix` | Replacement pattern (may use metavariables; `""` deletes the match) or a fix-config object. Applied with `scan --update-all` / `-U`, or interactively with `-i`. |
| `files` / `ignores` | Globs limiting which files the rule applies to (no leading `./`). |
| `severity`, `message` | Lint presentation: severity is `hint`, `info`, `warning`, `error`, or `off` (disables the rule); `message` may use metavariables. |

```yaml
id: no-console-log
language: javascript
rule:
  pattern: console.log($ARG)
constraints:
  ARG:
    kind: string
fix: logger.log($ARG)
severity: warning
message: use the logger
```

## Metavariables

Metavariables are placeholders in patterns that match dynamic content.

### $VAR: Single Named Node

Matches exactly one named AST node. The name is upper-case letters, digits, and underscores.

* **Valid**: `$META`, `$META_VAR`, `$META_VAR1`, `$_`
* **Invalid**: `$invalid`, `$123`, `$KEBAB-CASE`
* `console.log($GREETING)` matches `console.log('Hello World')` but not `console.log()` or `console.log(a, b)`.
* **Reuse**: the same name must match the same content - `$A == $A` matches `a == a` but not `a == b`.

### $$VAR: Single Unnamed Node

Captures a single unnamed node (operators, punctuation), which `$VAR` skips. To match the operator in `a + b`:

```yaml
rule:
  kind: binary_expression
  has:
    field: operator
    pattern: $$OP
```

### $$$MULTI: Zero or More Nodes

Matches zero or more nodes (arguments, parameters, statements). May be named: `$$$ARGS`.

* `console.log($$$)` matches `console.log()`, `console.log('hello')`, `console.log('debug:', key, value)`, and spread calls.
* `function $FUNC($$$ARGS) { $$$ }` matches functions with any parameters and any body.

### Non-Capturing ($_VAR)

A name starting with `_` is matched but not captured, so repeated occurrences may differ: `$_FUNC($_FUNC)`
matches `test(a)` and `testFunc(1 + 1)`. Slightly faster, since nothing is recorded.

### Detection rules

* Only exact syntax counts: `$A`, `$$B`, `$$$C`.
* The metavariable must be the **entire text of one node**. These never match: `obj.on$EVENT`, `"Hello $WORLD"`,
  `a $OP b`, `$jq`.

Use `--debug-query=pattern` (or the playground) to see where ast-grep recognised metavariables.

## Common Patterns and Examples

### Functions containing await

```yaml
rule:
  kind: function_declaration
  has:
    pattern: await $EXPR
    stopBy: end
```

### Code inside a specific context

```yaml
rule:
  pattern: console.log($$$)
  inside:
    kind: method_definition
    stopBy: end
```

### Has one thing but not another

Async functions that use await but have no try/catch:

```yaml
rule:
  all:
    - kind: function_declaration
    - has:
        pattern: await $EXPR
        stopBy: end
    - not:
        has:
          pattern: try { $$$ } catch ($E) { $$$ }
          stopBy: end
```

### Any of several alternatives

```yaml
rule:
  any:
    - pattern: console.log($$$)
    - pattern: console.warn($$$)
    - pattern: console.error($$$)
    - pattern: console.debug($$$)
```

## Troubleshooting

1. **Rule doesn't match**: dump the tree with `--debug-query=cst` and compare `kind` names and nesting to the rule.
2. **Relational rule finds nothing**: add `stopBy: end`.
3. **Wrong node kind**: kind names differ per language grammar - check the dump, not memory.
4. **Metavariable not recognised**: it must be the whole text of one node; check with `--debug-query=pattern`.
5. **Pattern too complex**: break it into sub-rules under `all`, test each alone, then recombine.
6. **Pattern won't parse**: use the object form with `context` and `selector`.
