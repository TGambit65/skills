#!/usr/bin/env python3
"""Fail when a change ships plugin content without raising the plugin version.

    python3 tools/check_version_bump.py                 # against origin/main
    python3 tools/check_version_bump.py origin/main     # against any base ref

An installed plugin only updates when its version changes: `claude plugin update`
answers "already at the latest version" for new content under an old number. So a
change to anything the plugin ships (.claude/skills/ or .claude-plugin/) must raise
`version` in .claude-plugin/plugin.json above the base's. A change to anything else
(README, tools, hooks, docs) needs no bump. check_contracts.py already makes both
manifests agree, so plugin.json speaks for both.

Exit 0 pass, 1 fail, 2 when the base cannot be read. Zero dependencies; Python 3.8+.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

SHIPPED = (".claude/skills/", ".claude-plugin/")
MANIFEST = ".claude-plugin/plugin.json"
VERSION_RE = re.compile(r"^\d+(\.\d+)*$")


def git(*args: str) -> "tuple[int, str]":
    """Run git; return (exit code, stdout)."""
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def version_at(ref: "str | None") -> "str | None":
    """The plugin.json version at `ref`, or in the working tree when ref is None."""
    if ref is None:
        try:
            with open(MANIFEST, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return None
    else:
        rc, text = git("show", f"{ref}:{MANIFEST}")
        if rc != 0:
            return None
    try:
        return str(json.loads(text).get("version") or "") or None
    except (json.JSONDecodeError, AttributeError):
        return None


def parse(version: str) -> "tuple[int, ...] | None":
    """'1.5.1' -> (1, 5, 1); None for anything that is not plain dotted numbers."""
    if not VERSION_RE.match(version):
        return None
    parts = tuple(int(p) for p in version.split("."))
    return parts + (0,) * (3 - len(parts)) if len(parts) < 3 else parts


def main(argv: "list[str]") -> int:
    """Compare the shipped paths and the version against the base ref."""
    base = argv[0] if argv else "origin/main"
    rc, top = git("rev-parse", "--show-toplevel")
    if rc != 0:
        print("ERROR  not inside a git repository")
        return 2
    os.chdir(top.strip())   # diff paths and the manifest are both repo-root relative
    rc, _ = git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if rc != 0:
        print(f"ERROR  base ref {base!r} not found. In CI, check out with fetch-depth: 0.")
        return 2
    # --no-renames: a rename otherwise lists only its new path, so moving a skill out of
    # .claude/skills/ would read as "nothing shipped changed".
    rc, out = git("diff", "--name-only", "--no-renames", f"{base}...HEAD")
    if rc != 0:
        print(f"ERROR  could not diff {base}...HEAD")
        return 2
    shipped = sorted(p for p in out.splitlines() if p.startswith(SHIPPED))
    if not shipped:
        print(f"PASS   nothing the plugin ships changed since {base}; no version bump needed")
        return 0

    old, new = version_at(base), version_at(None)
    listing = "\n".join(f"         {p}" for p in shipped[:20])
    more = f"\n         … and {len(shipped) - 20} more" if len(shipped) > 20 else ""
    if new is None or parse(new) is None:
        print(f"FAIL   {MANIFEST} has no plain numeric version ({new!r}); cannot compare")
        return 1
    if old is None:
        print(f"PASS   {base} has no readable plugin version; {new} is the first release")
        return 0
    if parse(old) is None:
        print(f"FAIL   {base} has a non-numeric plugin version ({old!r}); cannot compare")
        return 1
    if parse(new) <= parse(old):
        print(f"FAIL   {len(shipped)} shipped file(s) changed since {base}, but the plugin "
              f"version is {new} (base: {old}).\n"
              f"       Existing installs will not receive them. Raise \"version\" in both "
              f".claude-plugin/plugin.json\n       and .claude-plugin/marketplace.json above "
              f"{old}. Changed:\n{listing}{more}")
        return 1
    print(f"PASS   {len(shipped)} shipped file(s) changed and the version went {old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
