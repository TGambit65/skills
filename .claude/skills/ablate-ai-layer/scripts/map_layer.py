#!/usr/bin/env python3
"""Map a repository's AI layer. Read-only. Agent-agnostic.

Finds every instruction/context artifact any mainstream coding agent would load,
classifies each by WHEN it loads, and estimates what the always-loaded set costs
on every single session.

  always-loaded : enters context every session whether the task needs it or not
  on-demand     : the BODY loads only when invoked or when its path matches.
                  A skill's frontmatter `description` is NOT on demand: the agent
                  lists every skill's name and description in context on every
                  session so it can decide what to invoke. That line is counted
                  as always-loaded below, separately from the body.
  enforcement   : deterministic, executes as code, spends no attention budget

Token figures are an approximation: characters / 4. Real tokenisers vary by
model and by content; use the numbers to compare before/after, not as a bill.

Usage:
  python map_layer.py [repo_root] [--json]

requires-python: >=3.8. Zero dependencies.
Exit codes: 0 = ran (including "nothing found"), 2 = repo_root is not a directory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ALWAYS, ONDEMAND, ENFORCE = "always-loaded", "on-demand", "enforcement"

# (glob, agent, default classification, note)
PATTERNS: list[tuple[str, str, str, str]] = [
    # --- Claude Code
    ("CLAUDE.md",                        "Claude Code", ALWAYS,   "root project instructions"),
    ("CLAUDE.local.md",                  "Claude Code", ALWAYS,   "personal, gitignored"),
    (".claude/CLAUDE.md",                "Claude Code", ALWAYS,   "alt project instructions"),
    (".claude/rules/**/*.md",            "Claude Code", ALWAYS,   "path-scoped if it has paths: frontmatter"),
    (".claude/skills/*/SKILL.md",        "Claude Code", ONDEMAND, "loads when invoked or matched"),
    (".claude/agents/*.md",              "Claude Code", ONDEMAND, "loads only inside a subagent"),
    (".claude/commands/**/*.md",         "Claude Code", ONDEMAND, "loads when the command runs"),
    (".claude/settings.json",            "Claude Code", ENFORCE,  "hooks and permissions"),
    (".claude/settings.local.json",      "Claude Code", ENFORCE,  "hooks and permissions"),
    # --- open standard / Codex / Amp / Gemini CLI / Zed
    ("AGENTS.md",                        "AGENTS.md",   ALWAYS,   "open standard, read by most agents"),
    (".agents/skills/*/SKILL.md",        "Codex",       ONDEMAND, "filesystem-discovered skills"),
    (".agents/rules/**/*.md",            "AGENTS.md",   ALWAYS,   "proposed rules dir"),
    # --- Cursor
    (".cursorrules",                     "Cursor",      ALWAYS,   "legacy single-file rules"),
    (".cursor/rules/**/*.mdc",           "Cursor",      ALWAYS,   "alwaysApply decides; parsed below"),
    # --- Windsurf
    (".windsurfrules",                   "Windsurf",    ALWAYS,   "root rules file"),
    (".windsurf/rules/**/*.md",          "Windsurf",    ALWAYS,   "rules dir"),
    # --- Cline
    (".clinerules",                      "Cline",       ALWAYS,   "root rules file"),
    (".clinerules/**/*.md",              "Cline",       ALWAYS,   "rules dir"),
    # --- GitHub Copilot
    (".github/copilot-instructions.md",  "Copilot",     ALWAYS,   "repo-wide instructions"),
    (".github/instructions/**/*.md",     "Copilot",     ONDEMAND, "applyTo-scoped"),
    # --- Aider
    ("CONVENTIONS.md",                   "Aider",       ALWAYS,   "conventions file"),
    (".aider.conf.yml",                  "Aider",       ENFORCE,  "config"),
]

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build",
             "__pycache__", ".next", "target", ".ablation"}

# Files whose frontmatter `description` is listed in context every session even
# though the body is on demand. Skills are the documented case for Claude Code
# and Codex. Subagents and commands are also listed by name in some agents; they
# are not counted here, so the always-loaded figure is a floor, not a ceiling.
DESCRIPTION_LISTED = re.compile(r"(^|/)\.(claude|agents)/skills/[^/]+/SKILL\.md$")


def est_tokens(chars: int) -> int:
    """chars / 4, the usual rough English-prose approximation. Stated, not hidden."""
    return chars // 4


def frontmatter(path: Path) -> dict:
    """Parse leading YAML frontmatter shallowly. No yaml dependency. Handles the
    common shapes: `key: value`, quoted values, and a folded/continued value
    whose following lines are indented (`description: >` or plain wrapping)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict = {}
    key = None
    for line in text[3:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line[:1] not in (" ", "\t") and ":" in line:
            key, _, v = line.partition(":")
            key = key.strip()
            v = v.strip()
            if v in (">", "|", ">-", "|-"):
                v = ""
            out[key] = v
        elif key is not None:
            out[key] = (out[key] + " " + line.strip()).strip()
    for k, v in out.items():
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            out[k] = v[1:-1]
    return out


def classify(path: Path, default: str) -> tuple[str, str]:
    """Refine classification using the file's own frontmatter."""
    name = path.name
    # Key PRESENCE, not truthiness: a YAML list renders as an empty value here
    # ("paths:\n  - src/**") and would otherwise read as absent.
    if name.endswith(".mdc"):                       # Cursor
        fm = frontmatter(path)
        if str(fm.get("alwaysApply", "")).lower() == "true":
            return ALWAYS, "alwaysApply: true"
        if "globs" in fm:
            return ONDEMAND, "glob-scoped"
        return ONDEMAND, "manual / description-matched"
    if "/.claude/rules/" in path.as_posix():
        fm = frontmatter(path)
        if "paths" in fm:
            return ONDEMAND, "path-scoped rule"
        return ALWAYS, "unscoped rule, loads every session"
    return default, ""


def iter_matches(root: Path):
    """Yield one record per AI-layer artifact under root: path, agent, kind, size, and listed description cost."""
    seen = set()
    for pattern, agent, default, note in PATTERNS:
        for p in root.glob(pattern):
            if not p.is_file():
                continue
            rp = p.relative_to(root)
            # Skip on the path INSIDE the repo. Checking the absolute path would
            # hide a whole repo that merely lives under a folder named `build`.
            if any(part in SKIP_DIRS for part in rp.parts):
                continue
            if rp in seen:
                continue
            seen.add(rp)
            kind, why = classify(p, default)
            text = p.read_text(encoding="utf-8", errors="replace")
            item = {
                "path": rp.as_posix(),
                "agent": agent,
                "kind": kind,
                "note": why or note,
                "bytes": p.stat().st_size,
                # The token estimate is characters / 4; bytes overstate it for non-ASCII text.
                "chars": len(text),
                "lines": len(text.splitlines()),
            }
            if DESCRIPTION_LISTED.search(rp.as_posix()):
                fm = frontmatter(p)
                # `disable-model-invocation: true` keeps the description out of the
                # model's context (the skill loads only on /name), so it costs nothing
                # until invoked and is not counted as always-loaded.
                if str(fm.get("disable-model-invocation", "")).strip().strip("'\"").lower() == "true":
                    item["description_listed"] = False
                else:
                    desc = fm.get("description", "")
                    item["description_chars"] = len(desc)
                    item["description_tokens_est"] = est_tokens(len(desc))
            yield item


def main() -> int:
    """Map the repository's AI layer and print it (or --json) with always-loaded token estimates."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo_root", nargs="?", default=".", help="repository to map (default: cwd)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    root = Path(args.repo_root).expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    items = sorted(iter_matches(root), key=lambda d: (d["kind"], d["path"]))
    always = [i for i in items if i["kind"] == ALWAYS]
    listed = [i for i in items if "description_chars" in i]
    file_tokens = est_tokens(sum(i["chars"] for i in always))
    desc_tokens = sum(i["description_tokens_est"] for i in listed)
    summary = {
        "always_loaded_files": len(always),
        "always_loaded_lines": sum(i["lines"] for i in always),
        "always_loaded_file_tokens_est": file_tokens,
        "skills_listed": len(listed),
        "skill_description_chars": sum(i["description_chars"] for i in listed),
        "skill_description_tokens_est": desc_tokens,
        "always_loaded_total_tokens_est": file_tokens + desc_tokens,
        "token_estimate": "chars / 4",
    }

    if args.json:
        print(json.dumps({"root": str(root), "summary": summary, "artifacts": items}, indent=2))
        return 0

    if not items:
        print(f"No AI layer artifacts found under {root}")
        print("Nothing to ablate. This repo has no agent instructions committed.")
        return 0

    agents = sorted({i["agent"] for i in items})
    print(f"AI layer under {root}")
    print(f"Agents detected: {', '.join(agents)}\n")

    for kind, header in ((ALWAYS, "ALWAYS LOADED  (paid on every session)"),
                         (ONDEMAND, "ON DEMAND  (body loads when it fires; a skill's "
                                    "description is still listed every session)"),
                         (ENFORCE, "ENFORCEMENT  (deterministic, no attention cost)")):
        group = [i for i in items if i["kind"] == kind]
        if not group:
            continue
        print(f"  {header}")
        for i in group:
            extra = ""
            if "description_chars" in i:
                extra = f"  [description ~{i['description_tokens_est']} tok, always listed]"
            elif i.get("description_listed") is False:
                extra = "  [disable-model-invocation: description not listed]"
            print(f"    {i['lines']:>5} ln  {i['path']:<52} {i['note']}{extra}")
        print()

    print(f"  Always-loaded files:        {summary['always_loaded_lines']} lines, "
          f"roughly {file_tokens:,} tokens")
    if listed:
        print(f"  Skill descriptions listed:  {len(listed)} skills, "
              f"{summary['skill_description_chars']:,} chars, roughly {desc_tokens:,} tokens")
    print(f"  Always-loaded total:        roughly {file_tokens + desc_tokens:,} tokens on every "
          f"session before you type anything  (estimate: chars / 4)")
    print()
    print("  Ablate the always-loaded files first. Skill BODIES are free until a skill")
    print("  fires, but every skill description is paid for on every session, so a")
    print("  long skill list is not free: shorten descriptions, or drop skills nobody")
    print("  invokes. Subagent and command descriptions may be listed too, depending")
    print("  on the agent; they are not counted here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
