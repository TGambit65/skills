#!/usr/bin/env python3
"""Tests for tools/check_version_bump.py, each against a throwaway git repo.

    python3 tools/_test_version_bump.py

Every case builds a base commit, makes a change on a branch, and asserts the exit code.
Zero dependencies; Python 3.8+.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_version_bump.py"
PASS, FAIL, ERROR = 0, 1, 2


def run(cwd: Path, *args: str) -> None:
    """Run a git command in the fixture, failing loudly."""
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


def write(root: Path, rel: str, text: str) -> None:
    """Write a file relative to the fixture root."""
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def manifest(version: "str | None", description: str = "skills") -> str:
    """A plugin.json body with the given version (omitted when None)."""
    data = {"name": "skills", "description": description}
    if version is not None:
        data["version"] = version
    return json.dumps(data, indent=2)


def fixture(base_version: "str | None" = "1.5.0", with_manifest: bool = True) -> Path:
    """A repo whose main branch is the base, checked out on a new branch `pr`."""
    root = Path(tempfile.mkdtemp(prefix="vbump-"))
    run(root, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@t.t"), ("user.name", "t"), ("commit.gpgsign", "false")):
        run(root, "config", k, v)
    write(root, ".claude/skills/demo/SKILL.md", "---\nname: demo\n---\nbody\n")
    write(root, "README.md", "readme\n")
    if with_manifest:
        write(root, ".claude-plugin/plugin.json", manifest(base_version))
    run(root, "add", "-A")
    run(root, "commit", "-qm", "base")
    run(root, "checkout", "-qb", "pr")
    return root


def check(root: Path, *args: str) -> "tuple[int, str]":
    """Run the script in the fixture against `main` (or the given args)."""
    p = subprocess.run([sys.executable, str(SCRIPT), *(args or ("main",))], cwd=str(root),
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def commit(root: Path, msg: str = "change") -> None:
    """Commit everything in the fixture."""
    run(root, "add", "-A")
    run(root, "commit", "-qm", msg)


def case_skill_changed_no_bump(root: Path) -> int:
    write(root, ".claude/skills/demo/SKILL.md", "---\nname: demo\n---\nnew body\n")
    commit(root)
    return FAIL


def case_skill_changed_with_bump(root: Path) -> int:
    write(root, ".claude/skills/demo/SKILL.md", "---\nname: demo\n---\nnew body\n")
    write(root, ".claude-plugin/plugin.json", manifest("1.5.1"))
    commit(root)
    return PASS


def case_new_skill_no_bump(root: Path) -> int:
    write(root, ".claude/skills/other/SKILL.md", "---\nname: other\n---\nbody\n")
    commit(root)
    return FAIL


def case_deleted_skill_no_bump(root: Path) -> int:
    run(root, "rm", "-q", ".claude/skills/demo/SKILL.md")
    commit(root)
    return FAIL


def case_docs_only(root: Path) -> int:
    write(root, "README.md", "readme, edited\n")
    write(root, "tools/x.py", "print(1)\n")
    commit(root)
    return PASS


def case_manifest_metadata_no_bump(root: Path) -> int:
    write(root, ".claude-plugin/plugin.json", manifest("1.5.0", description="new words"))
    commit(root)
    return FAIL


def case_version_lowered(root: Path) -> int:
    write(root, ".claude/skills/demo/SKILL.md", "changed\n")
    write(root, ".claude-plugin/plugin.json", manifest("1.4.9"))
    commit(root)
    return FAIL


def case_numeric_not_lexical(root: Path) -> int:
    # 1.10.0 > 1.9.0 numerically, though "1.10.0" < "1.9.0" as strings.
    write(root, ".claude-plugin/plugin.json", manifest("1.9.0"))
    commit(root, "to 1.9.0")
    run(root, "branch", "-f", "main", "HEAD")
    write(root, ".claude/skills/demo/SKILL.md", "changed\n")
    write(root, ".claude-plugin/plugin.json", manifest("1.10.0"))
    commit(root)
    return PASS


def case_non_numeric_version(root: Path) -> int:
    write(root, ".claude/skills/demo/SKILL.md", "changed\n")
    write(root, ".claude-plugin/plugin.json", manifest("1.6.0-beta"))
    commit(root)
    return FAIL


def case_uncommitted_bump_counts(root: Path) -> int:
    # The version is read from the working tree, so a local run sees a bump you have not committed yet.
    write(root, ".claude/skills/demo/SKILL.md", "changed\n")
    commit(root)
    write(root, ".claude-plugin/plugin.json", manifest("1.6.0"))
    return PASS


def case_run_from_subdirectory(root: Path) -> int:
    write(root, ".claude/skills/demo/SKILL.md", "changed\n")
    write(root, ".claude-plugin/plugin.json", manifest("1.5.1"))
    commit(root)
    return PASS


def case_skill_moved_out(root: Path) -> int:
    # A rename shows only its new path unless renames are off, so a move out of .claude/skills/
    # would read as "nothing shipped changed".
    (root / "attic").mkdir()
    run(root, "mv", ".claude/skills/demo/SKILL.md", "attic/SKILL.md")
    commit(root)
    return FAIL


def case_unknown_base(root: Path) -> "tuple[int, tuple[str, ...]]":
    return ERROR, ("no-such-ref",)


def case_base_without_manifest(_root: Path) -> int:
    return PASS


CASES = [
    ("a skill changed and the version did not", case_skill_changed_no_bump, {}),
    ("a skill changed and the version went up", case_skill_changed_with_bump, {}),
    ("a new skill was added without a bump", case_new_skill_no_bump, {}),
    ("a skill was deleted without a bump", case_deleted_skill_no_bump, {}),
    ("only README and tools changed", case_docs_only, {}),
    ("manifest metadata changed without a bump", case_manifest_metadata_no_bump, {}),
    ("the version went down", case_version_lowered, {}),
    ("1.9.0 -> 1.10.0 compares numerically", case_numeric_not_lexical, {}),
    ("a pre-release suffix is refused", case_non_numeric_version, {}),
    ("an uncommitted bump in the working tree counts", case_uncommitted_bump_counts, {}),
    ("it works when run from a subdirectory", case_run_from_subdirectory, {"cwd": "tools"}),
    ("moving a skill out of .claude/skills/ still counts", case_skill_moved_out, {}),
    ("an unknown base ref is an error, not a pass", case_unknown_base, {}),
    ("a base with no manifest is a first release", case_base_without_manifest, {"with_manifest": False}),
]


def main() -> int:
    """Run every case and print one line each."""
    failed = 0
    for name, fn, opts in CASES:
        cwd = opts.get("cwd")
        root = fixture(**{k: v for k, v in opts.items() if k != "cwd"})
        try:
            if fn is case_base_without_manifest:
                write(root, ".claude-plugin/plugin.json", manifest("1.0.0"))
                write(root, ".claude/skills/demo/SKILL.md", "changed\n")
                commit(root)
            result = fn(root)
            expect, args = result if isinstance(result, tuple) else (result, ())
            if cwd:
                (root / cwd).mkdir(parents=True, exist_ok=True)
            got, out = check(root / cwd if cwd else root, *args)
            ok = got == expect
            failed += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {name}  (exit {got}, wanted {expect})")
            if not ok:
                print("      " + out.strip().replace("\n", "\n      "))
        finally:
            shutil.rmtree(root, ignore_errors=True)
    print(f"\n{len(CASES) - failed}/{len(CASES)} version-bump cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
