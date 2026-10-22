#!/usr/bin/env python3
"""Contract checker for this skills repo.

Skills reference each other by name, by the files they write, and by the sections those
files contain. Every one of those is a contract, and a contract that lives only in prose
drifts the first time one side is edited. This script makes them mechanical.

    python3 tools/check_contracts.py            # human report, exit 1 on any failure
    python3 tools/check_contracts.py --json     # machine-readable
    python3 tools/check_contracts.py --tokens   # also print the always-loaded budget table

Zero dependencies. Python 3.8+.

What it checks
--------------
 1. frontmatter      every skill dir has SKILL.md; `name` equals the dir name; `description`
                     present and within Claude Code's 1024-char limit; `name` <= 64 chars.
 2. arguments        every `arguments:` entry is used as `$name` in the body and vice versa.
 3. bundled-files    every `references/`, `templates/`, `scripts/` path a SKILL.md mentions exists
                     in that skill's folder (project-level `.claude/references/...` is exempt:
                     those are optional files the user's project may provide).
 4. skill-refs       every `/skill-name` or `skill-name` that looks like one of ours exists.
 5. no-abs-paths     no body hardcodes `.claude/skills/<existing-skill>/...`: that path does
                     not exist under a plugin or global install.
 6. dynamic-lines    `!`...`` lines (run at load time) contain no `[placeholder]`.
 7. no-prefilled     fenced output templates contain no pre-filled pass marks (a template that
                     ships with "all passing" already typed invites reporting checks never run).
 8. handoffs         declared producer/consumer pairs share the literal they hand off
                     (path prefixes, file names, section names). See HANDOFFS below.
 9. readme           README lists every skill and states the right count.
10. manifests        plugin.json and marketplace.json agree on version.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
README = ROOT / "README.md"
MANIFESTS = [ROOT / ".claude-plugin" / "plugin.json", ROOT / ".claude-plugin" / "marketplace.json"]

DESC_LIMIT = 1024
NAME_LIMIT = 64

# Producer -> consumer handoffs. Each entry: the two skills and the literal both must contain.
# Add a row whenever one skill starts reading something another one writes.
HANDOFFS = [
    ("piv-plan-implementation", "piv-implement", ".claude/plans/"),
    ("piv-plan-implementation", "piv-run-full-loop", ".claude/plans/"),
    ("piv-implement", "piv-create-pr", ".claude/reports/"),
    ("piv-implement", "piv-review-pr", ".claude/reports/"),
    ("piv-review-changes", "piv-fix-review-findings", ".claude/code-reviews/"),
    ("piv-review-pr", "piv-fix-review-findings", ".claude/code-reviews/"),
    ("piv-investigate-issue", "piv-implement-issue", "docs/issues/issue-"),
    ("second-brain-audit", "second-brain-fix", "second-brain-audit.md"),
    ("worktree-create", "worktree-merge", "worktrees/"),
    ("piv-commit", "piv-create-pr", ".claude/references/conventions.md"),
    ("system-execution-report", "system-evolution-review", ".claude/execution-reports/"),
    ("piv-slice-epic", "piv-plan-implementation", "docs/tickets/"),
    ("piv-implement-issue", "piv-create-pr", ".claude/reports/"),
    ("piv-implement-issue", "piv-review-pr", ".claude/reports/"),
    ("piv-investigate-issue", "piv-commit", "docs/issues/"),
]

# Sections a consumer requires in a producer's output template. The producer's SKILL.md must
# contain each heading literally (so the template actually emits it).
REQUIRED_SECTIONS = [
    ("plan-create-prd", "plan-create-stories", ["Problem Statement", "Target User", "MVP", "Success Metrics", "Non-goals"]),
    ("piv-implement", "piv-review-pr", ["Deviations from the plan"]),
    ("piv-implement", "piv-create-pr", ["Deviations from the plan", "Validation results"]),
    ("piv-investigate-issue", "piv-implement-issue", ["Proposed Fix", "Testing Requirements", "Reproduction"]),
]

SKILL_PREFIXES = (
    "piv-", "plan-", "prime-", "rules-", "worktree-", "system-", "second-brain-", "build-",
    "skills-", "hooks-", "opportunity-", "ablate-", "drive-", "agent-", "ast-", "setup-",
)

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
FENCE_RE = re.compile(r"```.*?```", re.S)
# A result mark followed by a result word, or a bracketed placeholder that already asserts a
# result ("[Show test results - all passing]"). Legend lines like "a ✅ or ❌" are excluded.
PREFILLED_RE = re.compile(
    r"^\s*(?:[-*]|\d+\.)?\s*(?:✅|✓)\s+[^\n]*?\b(pass|passed|passing|resolved|complete|completed|no new issues|preserved|verified|loaded|created|implemented|committed)\b"
    r"|\[[^\]\n]*\b(all passing|all pass|passing)\b[^\]\n]*\]",
    re.I,
)


class Report:
    def __init__(self) -> None:
        self.failures: list[dict] = []
        self.warnings: list[dict] = []

    def fail(self, check: str, where: str, msg: str) -> None:
        self.failures.append({"check": check, "where": where, "msg": msg})

    def warn(self, check: str, where: str, msg: str) -> None:
        self.warnings.append({"check": check, "where": where, "msg": msg})


def parse_frontmatter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    fm: dict = {}
    key = None
    for line in m.group(1).splitlines():
        km = re.match(r"^([\w-]+):\s*(.*)$", line)
        if km:
            key = km.group(1)
            fm[key] = km.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm


def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def load_skills() -> dict[str, dict]:
    skills: dict[str, dict] = {}
    for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        md = d / "SKILL.md"
        text = md.read_text(encoding="utf-8") if md.exists() else ""
        skills[d.name] = {"dir": d, "path": md, "text": text, "fm": parse_frontmatter(text)}
    return skills


def body_without_fences(text: str) -> str:
    return FENCE_RE.sub("", text)


def check_frontmatter(skills: dict, rep: Report) -> None:
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        if not s["text"]:
            rep.fail("frontmatter", where, "missing SKILL.md")
            continue
        fm = s["fm"]
        if not fm:
            rep.fail("frontmatter", where, "no YAML frontmatter")
            continue
        if strip_quotes(fm.get("name", "")) != name:
            rep.fail("frontmatter", where, f"name '{fm.get('name')}' != dir '{name}'")
        if len(name) > NAME_LIMIT:
            rep.fail("frontmatter", where, f"name longer than {NAME_LIMIT} chars")
        desc = strip_quotes(fm.get("description", ""))
        if not desc:
            rep.fail("frontmatter", where, "empty description")
        elif len(desc) > DESC_LIMIT:
            rep.fail("frontmatter", where, f"description {len(desc)} chars > {DESC_LIMIT}")


def check_arguments(skills: dict, rep: Report) -> None:
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        raw = s["fm"].get("arguments", "")
        declared = [a.strip() for a in raw.strip("[]").split(",") if a.strip()] if raw else []
        used = set(re.findall(r"\$([A-Za-z][\w-]*)", s["text"]))
        used.discard("ARGUMENTS")
        for a in declared:
            if a not in used:
                rep.fail("arguments", where, f"declared argument '{a}' never used as ${a}")
        for u in sorted(used):
            if declared and u not in declared and not u.isupper():
                # `$notes` / `$review` style variables must be declared; shell vars like $PATH are fine
                if not re.search(rf"\$\{{?{re.escape(u)}\b", body_without_fences(s["text"])):
                    continue
                rep.fail("arguments", where, f"${u} used in body but not declared in arguments:")


def check_bundled_files(skills: dict, rep: Report) -> None:
    pat = re.compile(r"(?<![\w./-])((?:references|templates|scripts)/[\w./()-]+)")
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        for m in pat.finditer(s["text"]):
            rel = m.group(1).rstrip(".,:;)")
            # exempt project-level files and obvious placeholders
            start = m.start()
            prefix = s["text"][max(0, start - 8):start]
            if prefix.endswith(".claude/") or "<" in rel or "[" in rel or "*" in rel or rel.endswith("/"):
                continue
            if not (s["dir"] / rel).exists():
                rep.fail("bundled-files", where, f"references '{rel}' which does not exist in the skill folder")


def check_skill_refs(skills: dict, rep: Report) -> None:
    names = set(skills)
    pat = re.compile(r"(?:^|[\s(`/])/?((?:%s)[a-z0-9-]+)" % "|".join(re.escape(p) for p in SKILL_PREFIXES))
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        for m in pat.finditer(s["text"]):
            ref = m.group(1).rstrip("-")
            if ref in names:
                continue
            # tolerate our own file names and known non-skill words
            if ref in {"skills-create", "second-brain"} or ref.startswith(("agent-browser", "ast-grep")):
                continue
            if ref in NON_SKILL_WORDS or any(ref.startswith(w) for w in NON_SKILL_WORDS):
                continue
            rep.fail("skill-refs", where, f"references unknown skill '{ref}'")


NON_SKILL_WORDS = {
    "plan-first", "plan-", "system-reviews", "worktree-setup", "hooks-guide", "build-vs-buy",
    "build-and-test", "drive-screen", "setup-ai-tutor", "rules-file", "piv-sized", "piv-loop",
    "skills-create", "plan-slug", "second-brain-audit.md", "build-", "prime-", "piv-", "agent-",
    "agent-agnostic", "agent-read", "agent-steering", "system-level", "system-wide", "build-test",
    "plan-vs", "piv-shaped", "prime-dependent", "skills-", "system-", "rules-", "plan-and",
    "prime-codebase.md", "build-time", "build-only", "setup-", "ast-", "drive-", "agent-browser",
    "agent-side", "plan-create", "build-implement", "plan-implement", "build-validate",
}


def check_abs_paths(skills: dict, rep: Report) -> None:
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        for lineno, line in enumerate(s["text"].splitlines(), 1):
            for m in re.finditer(r"\.claude/skills/([a-z0-9-]+)/", line):
                if m.group(1) in skills:
                    rep.fail("no-abs-paths", f"{where}:{lineno}", f"hardcoded path to skill '{m.group(1)}' (breaks under plugin/global install); refer to it by name")


def check_dynamic_lines(skills: dict, rep: Report) -> None:
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        for lineno, line in enumerate(s["text"].splitlines(), 1):
            if line.lstrip().startswith("!`") and re.search(r"[\[<][^\]>]+[\]>]", line):
                rep.fail("dynamic-lines", f"{where}:{lineno}", "load-time command contains an unfilled placeholder")


def check_prefilled(skills: dict, rep: Report) -> None:
    for name, s in skills.items():
        where = f".claude/skills/{name}/SKILL.md"
        for lineno, line in enumerate(s["text"].splitlines(), 1):
            if "✅ or ❌" in line or "✅/❌" in line:
                continue
            if PREFILLED_RE.search(line):
                rep.fail("no-prefilled", f"{where}:{lineno}", f"ships a pre-filled result: {line.strip()[:70]}")


def check_handoffs(skills: dict, rep: Report) -> None:
    for producer, consumer, literal in HANDOFFS:
        for side in (producer, consumer):
            if side not in skills:
                rep.fail("handoffs", side, f"handoff declared for unknown skill (literal '{literal}')")
                continue
            if literal not in skills[side]["text"]:
                rep.fail("handoffs", f".claude/skills/{side}/SKILL.md", f"handoff literal '{literal}' missing ({producer} -> {consumer})")
    for producer, consumer, sections in REQUIRED_SECTIONS:
        if producer not in skills or consumer not in skills:
            continue
        for sec in sections:
            if sec.lower() not in skills[producer]["text"].lower():
                rep.fail("handoffs", f".claude/skills/{producer}/SKILL.md", f"{consumer} requires section '{sec}' which {producer}'s output template never writes")
            if sec.lower() not in skills[consumer]["text"].lower():
                rep.fail("handoffs", f".claude/skills/{consumer}/SKILL.md", f"declared to require section '{sec}' but never mentions it")


def check_readme(skills: dict, rep: Report) -> None:
    text = README.read_text(encoding="utf-8")
    listed = set(re.findall(r"`([a-z0-9-]+)`", text))
    for name in skills:
        if name not in listed:
            rep.fail("readme", "README.md", f"skill '{name}' not listed")
    counts = {int(n) for n in re.findall(r"\b(\d{2})\s+skills\b", text)}
    if counts and counts != {len(skills)}:
        rep.fail("readme", "README.md", f"states {sorted(counts)} skills, directory has {len(skills)}")


def check_manifests(rep: Report) -> None:
    versions = {}
    for p in MANIFESTS:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            rep.fail("manifests", str(p.relative_to(ROOT)), f"unreadable: {e}")
            continue
        v = data.get("version") or (data.get("plugins") or [{}])[0].get("version")
        versions[p.name] = v
    if len(set(versions.values())) > 1:
        rep.fail("manifests", ".claude-plugin/", f"version mismatch: {versions}")


def token_table(skills: dict) -> list[dict]:
    rows = []
    for name, s in skills.items():
        desc = strip_quotes(s["fm"].get("description", ""))
        body = s["text"][FM_RE.match(s["text"]).end():] if FM_RE.match(s["text"]) else s["text"]
        rows.append({
            "skill": name,
            "desc_chars": len(desc),
            "desc_words": len(desc.split()),
            "body_lines": body.count("\n") + 1,
            "body_words": len(body.split()),
        })
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tokens", action="store_true", help="print the always-loaded budget table")
    args = ap.parse_args(argv)

    if not SKILLS.is_dir():
        print(f"no skills dir at {SKILLS}", file=sys.stderr)
        return 2
    skills = load_skills()
    rep = Report()
    for fn in (check_frontmatter, check_arguments, check_bundled_files, check_skill_refs,
               check_abs_paths, check_dynamic_lines, check_prefilled, check_handoffs, check_readme):
        fn(skills, rep)
    check_manifests(rep)

    rows = token_table(skills)
    totals = {
        "skills": len(skills),
        "desc_chars": sum(r["desc_chars"] for r in rows),
        "desc_words": sum(r["desc_words"] for r in rows),
        "body_words": sum(r["body_words"] for r in rows),
        # chars/4 is a rough, model-independent proxy. Stated as such wherever it is quoted.
        "desc_tokens_approx": sum(r["desc_chars"] for r in rows) // 4,
    }

    if args.json:
        print(json.dumps({"failures": rep.failures, "warnings": rep.warnings, "totals": totals,
                          "rows": rows if args.tokens else None}, indent=2))
    else:
        for f in rep.failures:
            print(f"FAIL  [{f['check']}] {f['where']}: {f['msg']}")
        for w in rep.warnings:
            print(f"WARN  [{w['check']}] {w['where']}: {w['msg']}")
        if args.tokens:
            print(f"\n{'skill':28} {'desc':>5} {'words':>5} {'lines':>5} {'bwords':>6}")
            for r in rows:
                print(f"{r['skill']:28} {r['desc_chars']:>5} {r['desc_words']:>5} {r['body_lines']:>5} {r['body_words']:>6}")
        print(f"\n{len(skills)} skills · descriptions {totals['desc_chars']} chars (~{totals['desc_tokens_approx']} tokens, chars/4) "
              f"· bodies {totals['body_words']} words · {len(rep.failures)} failure(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
