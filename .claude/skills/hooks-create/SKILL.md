---
name: hooks-create
description: Turns a plain-English guarantee ("never let the agent edit my migrations", "don't stop until the tests pass", "log every command") into a working Claude Code hook - picks the lifecycle event, writes the script, wires .claude/settings.json, and tests it. Use when the user wants a deterministic guarantee or automation in their AI Layer without writing the hook by hand.
argument-hint: [what-the-hook-should-do]
---

# Create Hook: Turn an Idea Into a Working Claude Code Hook

**What the user wants the hook to do**: $ARGUMENTS

If that is filled in, treat it as the behavior spec and start from it. Don't re-ask what they already told you;
only ask to pin down the gaps (the exact paths / commands / patterns, and whether it must *block*). If it is
blank, start by asking what the hook should guarantee or do (Workflow step 1).

## The one thing to get right: which event, and can it block?

The behavior the user wants maps to **one** lifecycle event. Pick by *when* it should fire and *whether it must
stop something*:

| The user wants to… | Event | Can it block? |
|---|---|---|
| **Stop the agent from doing something** (read a secret, edit a protected path, run a destructive command) | **PreToolUse** ⭐ | **Yes** - block the tool before it runs |
| **React after an action** (auto-format an edited file, log a command, inject context) | **PostToolUse** | No - the tool already ran; observe / format / inject only |
| **Guarantee work isn't "done" until a check passes** (don't stop until tests/lint/types are green) | **Stop** (or **SubagentStop**) | **Yes** - block the stop and send the agent back to work |
| **Gate or scan the user's prompt** before the model sees it | **UserPromptSubmit** | **Yes** - block the prompt; can also inject context |
| **Load context every time a session starts** | **SessionStart** | No - inject context only |
| **Get notified when the agent needs you / finishes** | **Notification** (or **Stop**) | No - side-effect only (desktop/Slack/sound) |
| **Snapshot state before context compaction** | **PreCompact** | No |

## The execution protocol (how a hook talks to Claude Code)

- **Input:** Claude Code passes a JSON object on **stdin** - always includes `session_id`, `cwd`,
  `hook_event_name`; event-specific fields like `tool_name` + `tool_input` (tool events), `prompt`
  (UserPromptSubmit), `source` (SessionStart).
- **Output / control:**
  - **`exit 0`** - allow / success. For `UserPromptSubmit` and `SessionStart`, anything printed to **stdout** is
    injected into the agent's context.
  - **`exit 2`** - **block.** The action is prevented and whatever you print to **stderr** is fed back to the
    agent as the reason, so it adapts. (Only blocking-capable events honor this - see the table.)
  - **any other exit code** - non-blocking error; shown to the user, execution continues. `exit 1` does **not**
    block.
  - **Advanced (optional):** exit 0 and print a JSON object on stdout instead - e.g. `{"decision":"block",
    "reason":"…"}` (Stop), or `{"hookSpecificOutput":{"hookEventName":"PreToolUse",
    "permissionDecision":"deny","permissionDecisionReason":"…"}}`. Prefer exit codes unless the user needs to
    *modify* input/output or inject `additionalContext` (nested inside `hookSpecificOutput`, never top-level).
    Confirm field names against the fetched docs.

## Workflow

### 1. Understand the idea (ask only to fill gaps)
Pin down two things in plain language:
- **What** should happen or be prevented, and **when** (before/after an action, at finish, at session start)?
- **How precisely** should it match? ("any `.env` file", "the `migrations/` folder", "`rm -rf`", "my test
  command exits non-zero"). Get the concrete file paths / commands / patterns; don't guess. If the ask is vague,
  propose a concrete interpretation and confirm.

### 2. Read the current docs
`WebFetch` these (current at time of writing - verify they still resolve) and confirm the target event's name,
stdin fields, and control protocol before writing a line:
- Hooks reference: https://code.claude.com/docs/en/hooks
- Hooks guide (examples): https://code.claude.com/docs/en/hooks-guide

If the fetch fails, proceed from the table and protocol above and **say so** in your report so the user can
double-check.

### 3. Pick the event (and matcher)
Use the table to choose the single event. Choose a **matcher** that scopes it tightly - for tool events, the
tool name(s) (e.g. `"Bash"`, `"Edit|Write"`, `"mcp__.*"`); empty/`"*"` means every occurrence.

### 4. Write the hook script
- Default to a **`uv` single-file Python script** at `.claude/hooks/<event>_<purpose>.py` (e.g.
  `pre_tool_use_secrets.py`, `stop_tests_must_pass.py`) - a `uv run --script` shebang plus inline `# /// script`
  metadata. Use another language only if the user asks.
- Read the JSON from stdin, do the check, and:
  - to **block**: print a clear reason to `stderr` and `sys.exit(2)`;
  - to **allow**: `sys.exit(0)` (optionally print context to stdout for the injecting events).
- **Fail open by default.** Wrap the body so any unexpected error exits `0`. The only intentional non-zero exit
  is the deliberate `exit 2` block.
- **Exception - guards must fail closed.** For a `PreToolUse` guard whose entire purpose is to stop something
  (secrets, protected paths, destructive commands): catch the exception, print it to stderr, and
  `sys.exit(2)`; and set `"onFailure": "block"` on the handler in `settings.json` so a hook that cannot start or
  times out also blocks (newer Claude Code versions only - confirm the field in the fetched docs). Tell the user
  which way their hook fails and why. A fail-closed guard that crashes is a bricked session: every matching tool
  call is blocked until the script is fixed — so keep its matcher as narrow as the guarantee allows, and tell the
  user the recovery is to edit or temporarily remove the hook entry in `.claude/settings.json`. Never fail closed
  on `Stop` / `SubagentStop` (Claude Code ignores `onFailure` there anyway).
- Keep it lean and readable.
- If a hook already exists for that event, **extend it** rather than overwrite (add your check; keep theirs).
- **`Stop` / `SubagentStop` only:** check `stop_hook_active` first and `sys.exit(0)` when it is true. Without
  that guard the hook blocks the stop, the agent works, tries to stop again, is blocked again - a loop.

> ### ⚠️ Running a project command from a hook (read this before writing one)
>
> The hook itself runs under **`uv run`, in an isolated ephemeral environment**. Its interpreter is NOT the
> project's interpreter and does NOT have the project's dependencies. So:
>
> - **NEVER** rebuild the command with `sys.executable` or a bare `["python", "-m", "pytest", ...]` list. That
>   runs the *hook's* throwaway python, which has no pytest, no project packages, nothing. The command fails with
>   `No module named …` **every single time** - so a "don't finish until tests pass" hook blocks on green as
>   readily as on red, and reports a nonsense reason. It looks like it works. It does not.
> - **DO** run the user's command **verbatim, as a shell string, in the project directory - with uv's ephemeral
>   venv stripped AND the project's own venv put first.** Both steps are required. `shell=True` alone is not
>   enough: `uv run` puts its throwaway interpreter first on `PATH` and sets `VIRTUAL_ENV`. But **removing uv's
>   venv does not activate the project's** - a hook is not the user's shell, so `.venv` was never on `PATH` to
>   begin with, and `python` falls through to whatever global interpreter the machine has. That global one has a
>   different (often broken) set of packages, so the hook exits 2 on a perfectly green suite and blames some
>   unrelated module. Copy this helper as-is:
>   ```python
>   TEST_COMMAND = "python -m pytest -q"   # exactly what the user typed; the one line they'll edit
>
>   def _project_env(project_root: Path) -> dict:
>       """os.environ with uv's ephemeral venv removed and the PROJECT's venv first."""
>       env = os.environ.copy()
>       ephemeral = env.pop("VIRTUAL_ENV", None)
>       parts = env.get("PATH", "").split(os.pathsep)
>       if ephemeral:                                    # 1. uv's throwaway venv, out
>           drop = {os.path.join(ephemeral, "Scripts"), os.path.join(ephemeral, "bin")}
>           parts = [p for p in parts if p not in drop]
>       for candidate in (".venv", "venv"):              # 2. the project's own venv, first
>           for bindir in ("Scripts", "bin"):
>               venv_bin = project_root / candidate / bindir
>               if venv_bin.is_dir():
>                   env["VIRTUAL_ENV"] = str(project_root / candidate)
>                   parts.insert(0, str(venv_bin))
>                   env["PATH"] = os.pathsep.join(parts)
>                   return env
>       env["PATH"] = os.pathsep.join(parts)
>       return env
>
>   root = Path(hook_input["cwd"])          # the project root Claude Code passes in
>   result = subprocess.run(
>       TEST_COMMAND, shell=True, capture_output=True, text=True,
>       cwd=str(root), env=_project_env(root),
>   )
>   ```
>   Put the command in a single named constant at the top of the file so the user can edit one obvious line.
> - If the command must run from a **subdirectory** (a monorepo, or a project whose test config lives deeper -
>   e.g. `app/backend/`), ask for that, and pass it: `cwd=Path(hook_input["cwd"]) / "app/backend"`. Getting this
>   wrong produces a hook that always blocks, which the user will read as "hooks are broken."
> - Hooks run in a **non-interactive shell** (no `~/.zshrc` / `~/.bashrc`), so a tool that is only on `PATH`
>   via the user's shell profile works when tested by hand and fails inside the hook. Give it a `timeout` in
>   settings so a hanging command cannot freeze the session.

### 5. Wire it into settings.json
Edit `.claude/settings.json` (create it if absent). **Merge** into any existing `hooks` block - never clobber
other events or other hooks on the same event. Use `${CLAUDE_PROJECT_DIR}` in the path. Shape:
```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit|Write|Read|Bash",
        "hooks": [ { "type": "command",
                     "command": "uv run ${CLAUDE_PROJECT_DIR}/.claude/hooks/pre_tool_use_secrets.py",
                     "onFailure": "block",
                     "timeout": 15 } ] }
    ]
  }
}
```

### 6. Prove it yourself, then explain and warn

**Run the hook before you hand it over, in both directions.** Feed it a sample event on stdin and check the exit
code - do not ship a hook you have only read.

```bash
# should ALLOW (exit 0)
echo '{"session_id":"t","cwd":"<project-root>","hook_event_name":"Stop","stop_hook_active":false}' | uv run .claude/hooks/stop_tests_must_pass.py; echo "exit=$?"
```

- For a **blocking guard**, feed it one payload that should be blocked (expect 2) and one that should pass
  (expect 0). If you made it fail closed, also feed it malformed JSON and confirm it exits 2.
- For a **command-running hook** (tests/lint/types), this is mandatory in both directions: it exits 0 while the
  command passes, and exits 2 once it genuinely fails. If it exits 2 in both states, the command is not resolving
  - re-read the warning in step 4 about `sys.executable`.
- If a check comes back wrong, fix the script and re-run before reporting success.

Then tell the user, in plain words:
- **What you built**: which event, what it guarantees, which way it fails (open or closed), and the one line
  they'd change to adjust it.
- **How to prove it** in the agent: for a blocking hook, an action that *should* be blocked ("ask me to read the
  env file - watch it refuse"); for an observe hook, where the output lands (the log, the notification).
- **What you verified**, and plainly what you could not.
- **Security note (always):** a hook runs arbitrary code automatically, with your credentials, on every matching
  event. Review hooks like you review CI config; only run hooks you trust. (Same caution as MCP servers.)

## Quality checks

Before you report done, confirm each of these is actually true - not just read:

- [ ] Right **event**; a blocking goal uses a blocking-capable one (PreToolUse / Stop / UserPromptSubmit), not PostToolUse.
- [ ] **Matcher scoped** to what the user meant, not firing on everything by accident.
- [ ] Failure direction deliberate: **open** (errors exit 0) for most hooks, **closed** (errors exit 2 +
  `onFailure: "block"`) for a PreToolUse guard. Every intended block has a clear stderr reason.
- [ ] Project command runs **verbatim, `shell=True`, project `cwd`, `_project_env()`** - never `sys.executable`.
- [ ] `Stop` / `SubagentStop` honors **`stop_hook_active`**.
- [ ] `settings.json` **merged**, not overwritten; existing hooks still present.
- [ ] **You ran it** both directions: exit 0 to allow, exit 2 to block.
- [ ] The user got the plain-English explanation, a way to prove it, and the security note.

## Notes

- Hooks are the deterministic floor of the AI Layer - use them for the non-negotiables (secrets, protected paths,
  "don't finish until green"), not for things a rule or skill handles well enough.
- A blocking hook's *coverage* is only as good as its matcher. Be honest with the user about the edges (e.g. a `.env` matcher won't catch a base64'd read,
  and `@file` mentions in the prompt attach the file without any tool call, so no PreToolUse hook fires).
- Keep hooks fast - they run on the matched event every time. Heavy work belongs in an async hook or a skill.
