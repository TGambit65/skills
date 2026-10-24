# Traps and recovery

Everything here was hit live, and each one fails quietly rather than loudly. Read
this with `SKILL.md`, which holds the hard rules and the control loop, and with
`driving-agents.md`, which holds the per-OS first-run setup.

- [Traps](#traps)
- [When it goes wrong](#when-it-goes-wrong)
- [Recovering a text box](#recovering-a-text-box)

---

## Traps

**1. A shell that rewrites arguments starting with `/`.** Under Git Bash on
Windows (MSYS), sending `/exit` delivers `C:/Program Files/Git/exit`. Every slash
command has this shape, so `/compact`, `/context` and `/usage` are corrupted by
default. Prefix the send with `MSYS_NO_PATHCONV=1`. The tell is a character count
that does not match what you sent, which is why `type` and `paste` both report
their length. Other shells do not do this.

**2. A nested agent session that writes no transcript.** A terminal spawned from
inside a Claude Code session inherits `CLAUDE_CODE_CHILD_SESSION`, `CLAUDECODE` and
`CLAUDE_CODE_ENTRYPOINT`. The child then either writes no transcript at all while
looking completely normal, so every readback silently returns nothing, or hangs at
startup with a rendered banner and no input box, which looks exactly like a broken
install. Clear all three before launching:

```bash
# bash, zsh, Git Bash
env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_CHILD_SESSION claude
```

```powershell
# PowerShell has no `env -u`; clear them in the launching shell instead
Remove-Item Env:CLAUDECODE, Env:CLAUDE_CODE_ENTRYPOINT, Env:CLAUDE_CODE_CHILD_SESSION -ErrorAction SilentlyContinue; claude
```

The variable names were observed on one Claude Code version; verify against your
installed version if the child still writes nothing.

**3. Two driven sessions in one worktree collide.** Two of them edited the same
test file, one invalidating the other's baseline. It was only caught because the
second noticed the file change mid-run and corrected itself. Give each session its
own worktree, or make sure their tasks touch disjoint files.

**4. A fullscreen application can refuse to give up focus.** Windows may decline a
foreground request outright, and a game in exclusive fullscreen will hold it
against every attempt. `screenctl.py` retries once and then stops rather than
typing into whatever is actually in front. The only fix is to close that app or put
it in windowed mode; there is no clever way around it, by design.

**5. Do not bulk-select in a terminal tab list.** Clicking a tab puts focus on the
list, not the terminal, and a select-all followed by a delete there once destroyed
six live sessions at once. Switch terminals with the keyboard instead, which never
focuses the list: `Ctrl+PageUp`/`Ctrl+PageDown` in VS Code on Windows and Linux
(macOS uses a different chord; verify in your editor's keybindings). Sessions
survive on disk either way and come back with `claude --resume <uuid>`, but the
terminals do not.

**6. `key --keys win` opens something this tool cannot close** (Windows). The Start
menu is a `CoreWindow`: it does not appear in `list`, so no action can target it,
and every action focuses a named window first, which is not how you dismiss it. The
machine is then stuck behind an open Start menu. There is almost never a reason to
press it alone - launch things with `start`, `code`, `open` or `wt.exe` instead.
Chords like `win+left` are fine; it is the bare key that traps you.

**7. An always-on-top window is in your screenshot and takes your clicks.** A
capture is a grab of that screen region, not of the window's own content, so an
overlay sitting on top of the target appears in the image. Focusing the target
does not push a topmost window behind it. This is the right trade-off and worth
understanding: the screenshot shows exactly what a click at those coordinates
will hit. Measured live, a click computed from such an image landed in the
overlay and the target recorded nothing. Notice the overlay in the image rather
than trusting the geometry.

**8. A window hanging off the edge of the desktop captures blank there.** Same
cause. The off-screen part of the image is not the window's content, it is
whatever the compositor had. Move the window fully on-screen before reading it.

**9. A secret passed as `--text` is in your shell history.** `type --text` and
`paste --text` take the payload as a command-line argument, which lands in shell
history and is visible in the process list while the command runs. The action log
records only character counts, never the text. For a token or password, write it
to a file, `paste --file` it, and delete the file.

---

## When it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| Text landed in the wrong place | Focus stolen mid-run | Screenshot, send `esc`, re-focus, retry. Do not blind-send more keys |
| `AMBIGUOUS` | Title matches several windows | Longer title, or `--id`. Two windows of one app often share a title exactly, and then only `--id` can separate them |
| `FOCUS_FAILED` | Another app holds the foreground | Retry once; if it is fullscreen, ask the user to close it |
| `FOCUS_LOST_MIDSEND` | Focus moved while a long `type` was still going out | The message says how many characters landed. Screenshot before retrying: re-sending the whole string duplicates the part that arrived. Prefer `paste` |
| `CLIPBOARD_MISMATCH` | Clipboard write failed | Retry. Nothing was pasted |
| Garbled typed text | `type` used for special characters | Use `paste` |
| Screenshot is one flat colour | On macOS, Screen Recording not granted | `doctor` says so. Grant it to the terminal app, not to python |
| Clicks land consistently offset | Image scale ignored | Use `IMAGE_SCALE` from the `shot` output |
| `wait` returns 2 | Turn open and quiet: a prompt, a slow command, or thinking | Screenshot, read the command, answer deliberately |
| `NO_SESSION_DIR` | Session never started, or started elsewhere | Check the terminal's working directory |
| `WAYLAND_UNSUPPORTED` | Wayland forbids cross-app control | Use an X11 session, or tmux for terminal work |
| `MISSING_TOOL` | A required binary is absent | The message names the install command. Run `doctor` to see everything missing at once |
| `autodrive` exits 2 on every prompt | The window cannot be photographed (focus, permissions) | Fix what `screenctl.py shot` reports first; it refuses to approve what it cannot see |

Exit codes: `screenctl.py` exits 0 on success and 1 on any refusal, with the
reason as the first token of the first line. `session_watch.py wait` exits 0, 1
(not found or timed out) or 2 (quiet, turn open). `autodrive.py` exits 0 (turn
complete), 1 (timed out), 2 (approvals not landing, prompt not photographable, or
cap hit) or 3 (stopped for a human: prompt unread, refuse list, or `--dry-run`).

---

## Recovering a text box

To recover a text box in an unknown state: `esc` to dismiss dialogs, then `ctrl+a`
(`cmd+a` on macOS) and `delete`. Blind backspaces are a last resort and have made
things worse. Screenshot after the clear and before typing anything new.
