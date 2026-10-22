#!/usr/bin/env python3
"""
Run a driven Claude Code session to the end of a turn, answering its permission
prompts, and stop the moment anything looks like it needs a human.

This answers prompts inside the DRIVEN SESSION'S OWN terminal UI. It has nothing
to do with operating-system dialogs and cannot answer one: every keystroke it
sends goes to the editor window you name.

What it does differently from a naive approval loop
---------------------------------------------------
The obvious version watches for the driven session to go quiet and assumes
silence means a prompt is waiting. Silence does not mean that. A finished turn
and a waiting prompt are identical from outside, so that version answers prompts
that are not there, and types into a session that has already stopped.

This one reads the transcript to decide whether the turn is still open, which
is the part the transcript can actually answer.

What it cannot answer: whether a quiet, open turn is a permission prompt, a
slow command or thinking. Records are flushed asynchronously and lag the
conversation. Watched live against v2.1.266, the same on-screen prompt once
left an unanswered tool_use naming the command in the transcript and once left
nothing at all, with the tool_use appearing only after approval. So an
unanswered tool_use is a HINT about what is being asked, never proof of the
session's state, and the refuse list below often cannot see the command it is
meant to filter.

That leaves the screen as the only reliable place a pending prompt exists. So
on a quiet, still-open turn this screenshots the window and stops, and a human
or a vision-capable agent reads the image and approves. --approve-blind will
press Enter without that step, and is off by default because it approves a
command nobody has read.

Every decision (stop, refuse, approve, send failure) is appended to
~/.screenctl/actions.log, the same file screenctl.py writes, so an unattended
run can be audited afterwards. The log records WHICH tool and WHY, never the
command text itself, because a command can carry a secret. The screenshot is
the record of what was on screen.

It also presses Enter rather than typing a digit. Enter accepts the highlighted
option, which is approve-once. Typing "2" selects the variant that stops asking,
and for a Bash command that writes a permanent rule into the repository's
settings, unattended, which is not a thing to do while nobody is watching.

  autodrive.py --title "<window>" --repo <path> [--session <uuid>]
               [--max 25] [--timeout 900] [--idle 45]
               [--shot-dir <dir>] [--dry-run] [--approve-blind]

Screenshots of every prompt it stopped on or answered go to --shot-dir, or by
default to ~/.screenctl/prompts/<run-timestamp>/. Never into the skill folder:
under a plugin or global install that folder is read-only.

Exit codes
  0  the turn completed
  1  timed out with the agent still working
  2  approvals are not reaching the session, the prompt could not be
     photographed, or the cap was hit
  3  stopped deliberately for a human: a prompt is waiting and needs reading,
     a command matched the refuse list, or --dry-run
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import session_watch as sw  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", newline="\n")
    except Exception:
        pass

# Same file screenctl.py appends to, so one log holds the keystrokes and the
# decisions that caused them, in order.
LOG = os.path.join(os.path.expanduser("~"), ".screenctl", "actions.log")
DEFAULT_SHOT_ROOT = os.path.join(os.path.expanduser("~"), ".screenctl", "prompts")


def audit(msg: str) -> None:
    """Append one decision line to the shared action log. Never the command text."""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{stamp}\tAUTODRIVE {msg}\n")
    except Exception:
        pass  # logging must never be the reason a stop does not happen


# Commands this will never approve on its own. The point is not to be a security
# boundary, because a determined mistake can be spelled around any regex. The
# point is that the class of thing you most regret approving while away is small,
# well known, and cheap to stop on. Anything matching hands control back with the
# command printed, and you approve it yourself or you do not.
REFUSE = [
    # Deletes. SKILL.md hard rule 6 names "deleting" as something to confirm, so
    # a plain `rm file` stops too; the recursive/forced forms get their own line
    # because the reason printed should say how bad it is.
    (r"\brm\s+(-\w*\s+)*-\w*[rf]|\brm\b.*--(recursive|force)\b",
     "recursive or forced delete"),
    (r"\b(rm|unlink|shred)\b", "deletes files"),
    (r"\b(rmdir|rd)\s+/s", "recursive delete"),
    (r"\b(Remove-Item|del|erase)\b.*(-Recurse|/s\b|/q\b)", "recursive delete"),
    (r"\b(Remove-Item|del|erase)\b", "deletes files"),
    (r"\bfind\b.*\s-delete\b", "deletes files"),
    # Git. Pushing is outward-facing (SKILL.md hard rule 6), so every push stops,
    # not just a forced one; the forced form is listed first for the message.
    (r"\bgit\s+push\b.*(--force|-f\b|\s\+\w)", "force push"),
    (r"\bgit\s+push\b", "pushes to a remote (outward-facing: confirm it yourself)"),
    (r"\bgit\s+reset\s+--hard\b", "discards working tree"),
    (r"\bgit\s+clean\b.*-\w*[fdx]", "deletes untracked files"),
    (r"\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)", "discards working tree"),
    (r"\bgit\s+branch\s+(-D|--delete\s+--force)\b", "force-deletes a branch"),
    (r"\bgit\s+stash\s+(drop|clear)\b", "discards stashed work"),
    # Privilege, network-to-shell, disks, machine.
    (r"\b(sudo|doas)\b|\bRunAs\b", "privilege escalation"),
    (r"\b(curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b[^|]*\|\s*(sudo\s+)?"
     r"((ba|z|)sh|python[23]?|node|iex|Invoke-Expression)\b",
     "pipes the network into a shell"),
    (r"\b(ba|z|)sh\s+<\(\s*(curl|wget)\b", "pipes the network into a shell"),
    (r"\bdd\s+if=", "raw disk write"),
    # `format` only as the Windows command on a drive letter: a bare \bformat\b
    # also matched `git log --format=...` and `echo 'format on save'`.
    (r"\b(mkfs(\.\w+)?|diskpart)\b|\bformat(\.com)?\s+[A-Za-z]:", "formats a volume"),
    (r"\b(shutdown|reboot|Restart-Computer|Stop-Computer)\b", "restarts the machine"),
    # Publishing and outward-facing GitHub actions.
    (r"\b(npm|pnpm|yarn)\s+publish\b", "publishes a package"),
    (r"\bgh\s+release\s+create\b", "publishes a release"),
    (r"\bgh\s+(pr\s+merge|repo\s+delete)\b", "outward-facing GitHub action"),
    # Data.
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA|COLUMN)\b", "destructive SQL"),
    (r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)", "unfiltered DELETE"),
    (r"\btruncate\b", "truncates data"),
    # Processes and permissions.
    (r"\b(p?kill(all)?|taskkill|Stop-Process)\b", "kills processes"),
    (r"\bchmod\s+(-R\s+)?[0-7]*777\b", "world-writable permissions"),
]

# These never carry a destructive command, so they are approved without matching.
SAFE_TOOLS = {"Read", "Grep", "Glob", "NotebookRead", "TodoWrite"}


def refuses(tool: str, detail: str) -> str | None:
    if tool in SAFE_TOOLS:
        return None
    for pattern, why in REFUSE:
        if re.search(pattern, detail, re.IGNORECASE):
            return why
    return None


def _target(a) -> list:
    return ["--id", a.id] if a.id else ["--title", a.title]


def screenctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(HERE, "screenctl.py"), *args],
                          capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", help="window holding the driven session")
    # Prefer --id for a driven agent. Claude Code renames its own terminal window
    # as it works: launched as "DRIVE-TEST" it became "claude", then
    # "* Claude Code". A title captured at launch stops matching mid-run, and a
    # generic one collides with whatever else is open.
    ap.add_argument("--id", help="target the window by handle from `screenctl.py list`")
    ap.add_argument("--repo", required=True, help="repo the driven session runs in")
    ap.add_argument("--session", default=None, help="pin one session uuid (prefix ok)")
    ap.add_argument("--max", type=int, default=25, help="approval cap")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--idle", type=int, default=45)
    ap.add_argument("--poll", type=float, default=3.0)
    ap.add_argument("--shot-dir", default=None,
                    help="screenshot before every approval, into this directory")
    # The transcript cannot say what a prompt is asking, so this approves
    # commands nobody has read. Off by default for that reason.
    ap.add_argument("--approve-blind", action="store_true",
                    help="press Enter on a detected prompt without reading it")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the first prompt and what it would do, approve nothing")
    a = ap.parse_args()

    if not (a.title or a.id):
        print("NO_TARGET: pass --title or --id")
        return 3

    sw.PIN = a.session
    path = sw.latest(a.repo)
    base_turns = len(sw.turn_ends(sw.records(path)))
    print(f"Driving {path.name} in {(a.id or a.title)!r} (baseline {base_turns} turns, "
          f"cap {a.max} approvals)")
    audit(f"START session={path.name} target={(a.id or a.title)!r} "
          f"blind={a.approve_blind} dry_run={a.dry_run} cap={a.max}")
    if a.dry_run:
        print("DRY RUN: nothing will be sent.")

    # One directory per run. Reusing one directory across runs makes a stale
    # prompt-01.png look like this run's prompt, and the skill folder itself is
    # read-only under a plugin install, so the default is under the user's home.
    shot_dir = a.shot_dir or os.path.join(
        DEFAULT_SHOT_ROOT, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    screenctl_path = os.path.join(HERE, "screenctl.py")

    approvals = 0
    last_count = len(sw.records(path))
    last_change = time.time()
    deadline = time.time() + a.timeout

    while time.time() < deadline:
        path = sw.latest(a.repo)
        recs = sw.records(path)

        if len(sw.turn_ends(recs)) > base_turns:
            print(f"TURN_COMPLETE after {approvals} approval(s)")
            audit(f"TURN_COMPLETE approvals={approvals}")
            if texts := sw.assistant_texts(recs):
                print("\n--- final assistant message ---")
                print(texts[-1][:2000])
            return 0

        if len(recs) != last_count:
            last_count = len(recs)
            last_change = time.time()
            time.sleep(a.poll)
            continue

        idle = time.time() - last_change
        if idle < a.idle:
            time.sleep(a.poll)
            continue

        if not sw.turn_in_flight(recs):
            print(f"TURN_COMPLETE (quiet, turn closed) after {approvals} approval(s)")
            audit(f"TURN_COMPLETE quiet approvals={approvals}")
            if texts := sw.assistant_texts(recs):
                print("\n--- final assistant message ---")
                print(texts[-1][:2000])
            return 0

        # Turn open and quiet: waiting at a permission prompt, running a slow
        # command, or thinking. The transcript cannot tell these apart, and the
        # reason is worth stating because two rounds of testing got it wrong in
        # opposite directions.
        #
        # Records are flushed asynchronously and the flush lags the conversation
        # (Anthropic's hook docs say the transcript "may lag the in-memory
        # conversation"). Measured against v2.1.266 with a prompt visibly on
        # screen: once the transcript held an unanswered tool_use naming the exact
        # command, and once it held nothing at all and the tool_use only appeared
        # after approval. Same on-screen state, two different transcript shapes.
        #
        # So an unanswered tool_use is a HINT about what is being asked, never
        # proof of which state we are in. The screen decides.
        hint = sw.pending_tool_details(recs)
        if approvals >= a.max:
            print(f"CAP: {a.max} approvals reached. Stopping deliberately.")
            audit(f"CAP approvals={approvals}")
            return 2

        # Always photograph the prompt, blind or not. In blind mode the image is
        # the only record of what was approved; without it an unattended run
        # leaves no evidence at all.
        try:
            os.makedirs(shot_dir, exist_ok=True)
        except OSError as e:
            print(f"\nCANNOT WRITE SCREENSHOTS to {shot_dir}: {e}")
            print("Pass --shot-dir pointing at a writable directory.")
            audit(f"STOP shot_dir_unwritable={shot_dir!r}")
            return 2
        shot = os.path.join(shot_dir, f"prompt-{approvals + 1:02d}.png")
        # The capture can fail - most often FOCUS_FAILED, which is exactly
        # the situation where a human is about to be told "read this image".
        # Naming a path that was never written is bad; naming one left over
        # from an earlier prompt in the same --shot-dir is worse, because it
        # looks valid and describes a different question. Say it failed.
        before = os.path.getmtime(shot) if os.path.exists(shot) else None
        rs = screenctl("shot", *_target(a), "--out", shot)
        fresh = os.path.exists(shot) and os.path.getmtime(shot) != before
        if rs.returncode != 0 or not fresh:
            print("\nSCREENSHOT FAILED, so there is nothing to read:")
            print("   ", (rs.stdout + rs.stderr).strip()[:300] or "no new file")
            print("Refusing to approve something that cannot be seen.")
            audit(f"STOP screenshot_failed rc={rs.returncode}")
            return 2

        print(f"\n--- quiet {int(idle)}s, turn still open "
              f"(records {len(recs)}, approvals so far {approvals}) ---")
        hint_tools = ",".join(t for t, _ in hint) if hint else "none"
        if hint:
            for tool, detail in hint:
                print(f"    transcript hint: {tool}: {detail[:300]}")
                if why := refuses(tool, detail):
                    print(f"\nREFUSING: {why}. Answer this one yourself.")
                    print(f"    screenshot: {shot}")
                    audit(f"REFUSE tool={tool} why={why!r} shot={shot}")
                    return 3
        else:
            print("    transcript says nothing about what is being asked")

        if not a.approve_blind:
            print(f"\nScreenshot: {shot}")
            print("Read it. This is a permission prompt, a slow command, or thinking,")
            print("and only the image separates them. If it is a prompt, approve with:")
            print(f"  python {screenctl_path} key {' '.join(_target(a))} --keys enter")
            print("Re-run with --approve-blind only if you accept pressing Enter on")
            print("something nobody has read.")
            audit(f"STOP_FOR_HUMAN hint={hint_tools} shot={shot}")
            return 3

        if a.dry_run:
            print("\nDRY RUN: would press Enter to approve. Stopping here.")
            audit(f"DRY_RUN would_approve hint={hint_tools} shot={shot}")
            return 3
        print(f"    approving blind (--approve-blind). Screenshot: {shot}")

        # Enter, not a digit: it accepts the highlighted option, which is
        # approve-once. screenctl verifies the foreground window by identity and
        # exits non-zero rather than sending, so a stolen focus stops the run
        # instead of typing an approval into whatever is actually in front.
        r = screenctl("key", *_target(a), "--keys", "enter")
        if r.returncode != 0:
            print("\nSEND FAILED, stopping rather than pretending it landed:")
            print("   ", (r.stdout + r.stderr).strip()[:300])
            audit(f"STOP send_failed rc={r.returncode} shot={shot}")
            return 2
        approvals += 1
        print("    approved (Enter)")
        audit(f"APPROVE blind #{approvals} hint={hint_tools} shot={shot}")

        # Give the session a moment to act, then require evidence that it did.
        # An approval that changes nothing means the keystroke is not reaching the
        # prompt, and looping harder has never once fixed that.
        grew_by = time.time() + 30
        while time.time() < grew_by:
            time.sleep(a.poll)
            if len(sw.records(sw.latest(a.repo))) != last_count:
                break
        else:
            print("\nNo new transcript records after that approval.")
            print("The keystroke is not reaching the prompt. Stopping for a human.")
            audit(f"STOP no_progress_after_approval approvals={approvals}")
            return 2

        last_count = len(sw.records(sw.latest(a.repo)))
        last_change = time.time()

    print(f"TIMEOUT after {a.timeout}s with {approvals} approval(s) given.")
    print("The agent may still be working. Screenshot before concluding anything.")
    audit(f"TIMEOUT approvals={approvals}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
