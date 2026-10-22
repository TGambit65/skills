# Hooks

Six hooks I actually run, as copy-in files, plus the test corpus that keeps them honest.

A rule *asks* the agent to behave. A hook **guarantees** it. Your rules file is guidance the model reads,
weighs against everything else in context, and follows most of the time. A hook is code the harness runs on a
lifecycle event, whether the model remembers it or not. The agent never chooses to invoke a hook, which is
precisely why a hook can guarantee anything at all.

The decision is one line:

> **If the consequence of the agent ignoring it is a minor annoyance, write a rule.
> If the consequence is a production incident, a leaked secret, or a broken deploy, write a hook.**

Most people's AI Layer is 90% rules and 0% hooks. That is backwards for the handful of things that must be
true every single time.

One honesty note before the table, because the first version of this README got it wrong: a hook guarantees
that it **runs**. What it **catches** is a deny-list, and a deny-list is a strong speed bump, not a wall. The
section [What the secrets hook can and cannot do](#what-the-secrets-hook-can-and-cannot-do) says exactly where
the wall is, and it is not in this directory.

## Why this matters more than it sounds

There is a measurement behind this, not just a preference. In [Agentic Harness
Engineering](https://arxiv.org/abs/2604.25850) a research team let an agent rewrite its own harness for ten
rounds and measured which layer earned the gain. The system prompt it wrote for itself was genuinely good, 9 KB
of well-reasoned rules. Swapped into the baseline **on its own it scored below doing nothing** (67.4% against a
69.7% seed). Every point of the improvement came from the other layers: memory, tools, and middleware, which is
to say, from enforcement rather than instruction.

The arc inside that repo is the whole argument. The prompt already said "do not destroy verified state." The
agent ignored it. So at iteration 5 the loop wrote a guard into the shell tool that intercepted the destructive
command. It gave itself an override token. Three rounds later it took the override away from itself.

Rules got ignored. Guards did not.

## What ships here

| File | Event | What it does | Blocks? | On its own crash |
|---|---|---|---|---|
| `pre_tool_use_secrets.py` | **PreToolUse** | Refuses the routes to a credential it can see: env files, ssh keys, `.pem`/`.key`, `.aws`, `.netrc`, `.npmrc`, dumping the process environment, credential CLIs (`gh auth token`, `vault read`), and the obvious ways of hiding the filename (globs, braces, `$VAR`, `$(...)`, `base64 -d`, `xargs cat`, `eval`). Refuses irreversible mass deletes: `rm -rf`, `find -delete`, `git clean -f`, `git reset --hard`, `git push --force`. Committed `.env.example` and `rm -rf node_modules` are allowed. | **Yes** | **Fails closed** |
| `pre_tool_use_dependencies.py` | **PreToolUse** | Declared file coupling, enforced. The agent cannot edit a file until it has read that file's dependencies this session. | **Yes** (or injects) | Fails open |
| `post_tool_use_log.py` | **PostToolUse** | Appends one JSONL line per tool call to `logs/agent-actions.jsonl`, with credential-shaped values scrubbed. A greppable audit trail of everything the agent did. | No | Fails open |
| `session_start_context.py` | **SessionStart** | Injects what is true *today*: branch, uncommitted files, recent commits, plus any working-notes file. | No | Fails open |
| `stop_tests_must_pass.py` | **Stop** | Runs your test command when the agent tries to finish. Red, and it blocks the stop and hands back the failures. Green-because-the-tests-changed (or vanished) also blocks. | **Yes** | Fails open, **loudly** (exit 1) |
| `stop_notify.py` | **Stop** | Native desktop notification when the turn ends, so you can walk away. | No | Fails open |
| `_test_hooks.py` | - | 400 payloads with the exit code each hook must produce. Run it after every edit. | - | - |

That split is the mental model: **pre = gate, post = log.** Pre-hooks fire before the action, so they can stop
it. Post-hooks fire after, so all they can do is observe and react.

The last column is a deliberate choice per hook. Every hook used to fail open - swallow the exception, exit 0 -
on the theory that a broken hook must never brick a session. That is right for a logger and a notifier. It is
wrong for a secrets guard: an exception in the guard becomes a silent allow, which is the one outcome the guard
exists to prevent. So `pre_tool_use_secrets.py` now exits 2 with a "hook crashed" reason when it hits a bug.
You will notice, which is the point. `FAIL_CLOSED = False` at the top of the file turns it back if you need to.
The test gate sits in between: it still lets the agent finish on a crash, but exits 1 with a message so you can
see that the suite did not actually run. A silent exit 0 on a crash looks exactly like green.

## Install

```bash
# from your project root
mkdir -p .claude/hooks
cp path/to/skills/hooks/*.py .claude/hooks/          # includes _test_hooks.py
cp path/to/skills/hooks/settings.json.example .claude/settings.json   # or merge the "hooks" and "permissions" blocks
python3 .claude/hooks/_test_hooks.py                 # must say 0 failed before you trust anything
```

If you already have a `.claude/settings.json`, **merge** the `hooks` and `permissions` blocks rather than
replacing the file. Hooks from different settings files merge; they do not overwrite each other.

Then pick your two edits:

- `stop_tests_must_pass.py` → set `TEST_COMMAND`. Two ways, and the precedence matters: the **`TEST_COMMAND`
  environment variable wins** if it is set and non-empty; otherwise the `TEST_COMMAND` constant at the top of
  the file is used. Same for `TEST_SUBDIR`. Set the env var in the shell you launch Claude Code from, or under
  `"env"` in `settings.json`, when the file is shared across projects with different test commands.
- `pre_tool_use_dependencies.py` → copy `dependencies.example.json` to `.claude/hooks/dependencies.json` and
  declare your own couplings. **Until that file exists this hook allows everything**, so it is safe to install
  before you have configured it.

Commit `.claude/settings.json`. That is how the whole team inherits the same guarantees. Add `logs/` to
`.gitignore`, because the audit log records commands and a command can contain a value.

## Prove they work

Never trust a hook you have only read. A hook that always blocks and a hook that never blocks look identical
until the moment one of them fires wrong. The corpus does this for you:

```bash
python3 .claude/hooks/_test_hooks.py        # every hook, 400 payloads, expected exit code per payload
python3 .claude/hooks/_test_hooks.py -v     # show what each hook said on stderr
```

It is zero-dependency Python, so it runs anywhere the hooks run. It also runs against *any* hooks directory
(`--hooks-dir`), which is how I know the previous version of the secrets hook passes 210 of the 400 cases. Every
case carries a one-line reason, and the ones marked `[decision]` are judgment calls documented below rather than
bugs - change the decision, change the expected value, and you have a record of why.

To poke one by hand:

```bash
# should BLOCK (exit 2)
echo '{"session_id":"t","cwd":".","tool_name":"Read","tool_input":{"file_path":".env"}}' \
  | uv run .claude/hooks/pre_tool_use_secrets.py; echo "exit=$?"

# should ALLOW (exit 0)
echo '{"session_id":"t","cwd":".","tool_name":"Read","tool_input":{"file_path":"README.md"}}' \
  | uv run .claude/hooks/pre_tool_use_secrets.py; echo "exit=$?"
```

For `stop_tests_must_pass.py` you must check **both** directions: exit 0 while the suite is green, exit 2 once
you deliberately break a test. If it exits 2 in both states your test command is not resolving - see the venv
note below, which is the cause roughly every time.

## What the secrets hook can and cannot do

Read this section before you rely on the hook. It is the part the first version of this README overclaimed.

### The layers, in order of how much you can trust them

1. **The sandbox.** OS-level. Blocks every process, including the script the agent wrote and ran. If you are
   guarding something that matters, turn it on. Nothing below replaces it.
2. **`permissions.deny` in `settings.json`.** Enforced by Claude Code itself, not by a script you maintain. It
   covers the file tools, `@file` mentions in your prompt (which no PreToolUse hook ever sees), the Grep/Glob
   tools, and the file commands Claude Code recognises inside Bash (`cat .env`, `< .env`). It does **not**
   cover a `grep -r` over a directory that happens to contain the file, or a subprocess that opens the file
   itself. The paste-ready block is in `settings.json.example`; the core of it:

   ```json
   {
     "permissions": {
       "deny": [
         "Read(.env)",
         "Read(.env.*)",
         "Read(!.env.example)",
         "Read(**/*.pem)",
         "Read(**/*.key)",
         "Read(**/id_rsa*)",
         "Read(~/.ssh/**)",
         "Read(~/.aws/credentials)",
         "Read(~/.netrc)",
         "Edit(.env)",
         "Edit(.env.*)",
         "Bash(git push --force *)",
         "Bash(git reset --hard *)"
       ]
     }
   }
   ```

   Bare filenames match at any depth (`Read(.env)` is `Read(**/.env)`), `~/` is your home directory, `//` is
   the filesystem root, and a `!` entry after a rule carves out the template. The `Bash(...)` rules match the
   command as the agent writes it and nothing else - `git -C . push --force` walks past them - which is exactly
   the gap the hook is for.
3. **This hook.** Everything the deny rules do not reach: environment dumps, credential CLIs, glob and brace
   spellings, variables and substitutions, `xargs`/`eval`/`base64` indirection, the destructive commands, and
   `git -C . push --force`. It is a deny-list with a normaliser in front of it. It is good. It is not complete,
   and no deny-list can be.

Run all three. Each one catches what the others miss, and the combination is what the word "guarantee" in the
table above actually rests on.

### What the hook does with a Bash command

It builds two views of the command - a POSIX view with quotes folded, `\` escapes resolved, `$'...'` decoded,
`~`/`$HOME` expanded and whitespace collapsed, and a Windows view with `\` as a path separator - and checks both.
Then, per pipeline stage, it finds the real verb (past `sudo`, `timeout 5`, `VAR=x`, `sh -c "..."`, `do`, `(`)
and applies the policy that verb deserves:

- **Literal secret paths**, matched per word, so `cat .env.example; cat .env` is not laundered by the template.
  `ls`, `test`, `stat`, `find`, `git ls-files` are exempt: they only see names.
- **Globs and braces** are expanded and tested against secret basenames: `.e*`, `.en?`, `.{env}`, `*.pem`,
  `.[e]nv` all block; `*`, `src/*.py`, `tests/*` do not, because they also match ordinary files.
- **Opaque reads** block when a reader's *filename* is built at runtime: `cat $F`, `cat $x$y`, `cat ${F}nv`,
  `cat .e$(echo n)v`, `head -1 "$f"`. A variable in the *directory* is fine: `cat $DIR/README.md` and
  `cat $(git rev-parse --show-toplevel)/README.md` pass. This matters because the Bash tool is a persistent
  shell - `F=$(echo LmVudg== | base64 -d)` in one call and `cat $F` in the next is a real route, and both
  halves are blocked.
- **Indirection** blocks: `xargs cat`, `find -exec cat`, `eval`, `curl ... | bash`, `sh -c "$CMD"`,
  `base64 -d` captured into a variable, and code that assembles a filename from pieces before opening it
  (`open('.en'+'v')`, `chr(46)`, `Buffer.from(..., 'base64')`).
- **Environment dumps** block on the verb, not the spelling: `env`, `\env`, `/usr/bin/env`, `env | grep`,
  `env > f`, `(cd x && env)`, `timeout 5 env`, `set`, `export -p`, `declare -x`, `printenv`, `/proc/self/environ`,
  `os.environ`, `process.env`, `$env:`, `Get-ChildItem Env:`, `docker exec c env`. `env FOO=1 cmd` is a launcher
  and passes. `echo $OPENAI_API_KEY` blocks; `curl -H "Bearer $TOKEN"` passes, because using a secret is how
  work gets done and printing it is not.
- **Credential CLIs** block at the start of a stage: `gh auth token`, `aws configure get/list/export-credentials`,
  `vault read`, `op read`, `kubectl get secret -o yaml`, `docker inspect` (unless `--format` asks for something
  other than Env), `sops -d`, `git config --list`, `npx dotenv -p`. A commit message that *mentions* one does not.
- **Credential-shaped searches** block when recursive and unscoped: `grep -r KEY .`, `rg token`, `git grep
  SECRET`, and the match-everything forms `grep -r . .`. Scope it (`--include=*.py`, `-g '*.ts'`, a single
  file) or exclude env files (`--exclude='.env*'`) and it passes. `grep -r TODO .` and `grep -rn KeyError src/`
  were never affected.

### Decisions you may want to change

Each of these is a line in the `EDIT THESE` block and a `[decision]` case in the corpus.

- **`rm -rf` has an allowlist.** A flat "never" blocks `rm -rf node_modules` in every JS repo and teaches people
  to disable the hook. So `rm -rf` passes when *every* target is relative, has no `..`, no variable, and its
  first or last path component is a regenerable name: `node_modules`, `dist`, `build`, `coverage`,
  `__pycache__`, `.pytest_cache`, `*.egg-info`, `package-lock.json`, and a few more (`RM_SAFE_TARGETS`).
  `rm -rf /`, `~`, `*`, `src`, `$DIR`, `node_modules/../src` and `rm -rf dist src` all still block. If you have
  a source directory literally called `build` or `out`, remove it from the tuple.
- **Which destructive commands belong in a secrets guard.** The rule I used: anything that irreversibly
  destroys work or history without a prompt. In: `rm -rf` and its spellings (`-fr`, `-r -f`, `--recursive
  --force`, `yes | rm -r`, `sh -c "rm -rf"`), `find -delete`, `find -exec rm`, `xargs rm`, `git clean -f`
  (it deletes ignored files, which is where `.env` lives), `git reset --hard`, `git checkout -- .` /
  `git restore .`, `git push --force` / `+ref` / `--delete`, `git reflog expire`, `shutil.rmtree`, `DROP TABLE`.
  Out, deliberately: `git branch -D` and `git stash drop` (the reflog recovers them), single-file
  `git checkout -- path`, `git restore --staged .` (only unstages), `git push --force-with-lease` (the safe
  form), `rm -r` without `-f` (it prompts).
- **`.pem` blocks public certificates too.** `openssl x509 -in cert.pem` is a known false positive; the
  extension does not say which half it is. Rename public certs `.crt` or drop `pem` from `_KEY_EXTS` (in the
  "POLICY TABLES" section of the hook, not the `EDIT THESE` block).
- **A reader with a bare variable blocks even in a loop.** `for f in src/*.py; do wc -l $f; done` is refused;
  `wc -l src/*.py` is not. The agent rephrases in one turn. The alternative is leaving `cat $F` open.
- **`cat script.py | python3`** is refused as "script on stdin"; `python3 script.py` is not.
- **A virtualenv named `.env/`** is allowed under `.env/bin/` and friends. Rename it `.venv` and delete the line.

### What it fundamentally cannot close

These are not bugs in the regex. They are the reasons layers 1 and 2 exist.

- **The two-step.** The agent writes `read.py` containing `print(open('.env').read())`, then runs
  `python read.py`. The run looks innocent. Closing this means inspecting the *content* of every Write and
  Edit, which is a different and much larger hook, and even that cannot follow `read.py` importing `helper.py`.
- **Sweeps that never name the file.** `grep -r . .`, `tar cf - .`, `find . -type f -exec cat {} +` are
  blocked, but `grep -rn "=" .` or `cat */*` over a tree that contains `.env` is just reading files, and the
  only way to block that is to block reading files.
- **Any Turing-complete one-liner.** `python -c`, `perl -e`, `awk`, `node -e` can build a filename from
  arithmetic. The obvious shapes (`chr()`, concatenation, base64) are caught; the next shape is not.
- **Values already in context.** If a secret reached the model through any route, nothing here stops it being
  sent somewhere. Network exfiltration (`curl -d "$TOKEN"`) is out of scope on purpose: the same command is
  how secrets are legitimately *used*.
- **Harness-level fail-open.** If `uv` is not installed, if the hook times out (15s in the example settings), or
  if the hook's command line fails to parse, Claude Code treats it as a non-blocking error and the call goes
  through, unless the handler sets `"onFailure": "block"` (Claude Code v2.1.295 or later; the example settings
  set it on the secrets hook). On an older version the field does nothing. The `FAIL_CLOSED` switch only covers
  exceptions *inside* the script. This is the strongest argument for `permissions.deny`: it has no process to
  fail.
- **Committed secrets in history.** `git log -p` over a repo that once committed `.env` prints it. Rotate them.

## The seven things that will bite you

**1. The venv trap.** This is the one that wastes an afternoon. A hook runs under `uv run` in a throwaway
environment that has none of your project's packages, and it is not your shell, so your project's `.venv` was
never on `PATH` either. Strip uv's venv and `python` falls through to some global interpreter with the wrong
packages. Either way the hook exits 2 on a green suite and blames an unrelated module - it looks like a real
failure. `stop_tests_must_pass.py` handles both halves in `_project_env()`; steal it.

**2. `@file` mentions bypass PreToolUse entirely.** When you type `@config/secrets.yml` in your prompt, the file
is attached without a tool call, so no PreToolUse hook fires. Your guard covers what the *agent* reaches for,
not what *you* hand it. `permissions.deny` does cover `@file` mentions, which is one more reason to set it.

**3. `additionalContext` must be nested.** It goes inside `hookSpecificOutput`, never at the top level. Put it
at the top level and Claude Code silently ignores it. No error, no warning, it just does not arrive.

**4. Exit code 1 does not block. Exit code 2 does.** This is backwards from every other CLI you use, where 1
means failure. In a hook, 1 is a non-blocking error: it is logged and the agent carries straight on. Only 2
blocks, and only on events that can block at all. Get it the wrong way round and you believe you are protected
when you are not, with nothing on screen to tell you otherwise.

**5. A `Stop` hook without a loop guard will spin.** It blocks the stop, the agent works, tries to stop, gets
blocked again. Claude Code caps this at **eight consecutive blocks** and then overrides the hook and ends the
turn with a warning, so it is a bounded spin rather than a true infinite loop, but you have still burned eight
turns going nowhere. Read `stop_hook_active` from the payload and stand down when it is true. Both `Stop` hooks
here do.

**6. Hooks run in a non-interactive shell.** No `~/.zshrc`, no `~/.bashrc`. A tool that is only on `PATH`
because of your shell profile works when you test by hand and fails when the hook runs it. And if your profile
prints anything at startup, that text mixes into the hook's stdout and breaks JSON parsing.

**7. A space in your project path breaks every hook, silently.** `uv run ${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py`
splits on the space, the command fails, and because a failed hook command is a *non-blocking* error, the agent
carries on with no guard at all. Quote it: `uv run "${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"`. The example
settings do. The same silent-allow happens if `uv` is missing - run `claude --debug` once after installing and
look for your hooks actually executing.

Debugging: `claude --debug` shows hook execution, and `CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose` shows matcher
counts, which answers "did my matcher actually match."

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Allow. stdout is parsed for JSON on the events that accept it. |
| `2` | **Block.** stderr goes back to the agent as the reason, so it adapts. |
| anything else | Non-blocking error. Shown to you, execution continues. |

Exit `1` is the trap: it means "error," and Claude Code logs it and carries on. If you meant to block and you
exit 1, nothing is blocked and you will not be told. The flip side is useful: `stop_tests_must_pass.py` exits 1
on purpose when it *crashes*, so the message reaches you instead of vanishing into a silent 0.

Only some events honor a block: `PreToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`,
`PostToolBatch`, and a few others. `PostToolUse` cannot block, because the tool already ran.

## Beyond command hooks

Every hook here is a `command` hook, a script that gets JSON on stdin. There are four other handler types worth
knowing about, configured the same way in `settings.json`:

- **`prompt`** - send the event to a fast model and get an allow/deny back. For judgments a regex cannot make
  ("does this commit message describe what actually changed?").
- **`agent`** - spawn a subagent with real tools that can read the codebase before deciding. Expensive and
  slow; reserve it for gates worth a minute.
- **`http`** - POST the event to a server. This is how you enforce one policy across a whole org from one place.
- **`mcp_tool`** - call a tool on an MCP server you already have connected.

Command hooks are still the right default: they are instant, free, and you can read them.

## Two things to know

**Hooks run real code, automatically, with your credentials, with no sandbox.** Review a hook the way you
review a CI script. Only run hooks you have read and trust. Same caution as an MCP server.

**Coverage is yours.** The hook is guaranteed to *run*. What it *catches* is only as good as the check you
wrote, and the check you wrote is only as good as the last time you tested it against someone trying to get
past it. That is what `_test_hooks.py` is for. When you add a path or a command to the policy, add the payload
that proves it, and add the innocent neighbour that proves you did not break anything else.

## Write your own without writing Python

Use the [`hooks-create`](../.claude/skills/hooks-create/SKILL.md) skill. Describe the guarantee in plain
English and it picks the event, writes the script, wires `settings.json`, and tests it:

```
/hooks-create "never let the agent edit anything under db/migrations/"
/hooks-create "run ruff on every python file the moment it's edited"
/hooks-create "ping me on Slack when the agent needs my input"
```

## Portability

Not a Claude Code party trick. Codex and Cursor use the same shape (a script, JSON on stdin, exit 2 to block);
Gemini CLI does the same job by reading a structured JSON decision instead of the exit code; Pi and opencode
run hooks in-process as plugins. Learn it once and it transfers, the same way `AGENTS.md` became the shared
rules file.
