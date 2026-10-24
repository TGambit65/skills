#!/usr/bin/env python3
"""Find stale and contradictory facts in a folder of markdown notes.

The counting lives here, in code, rather than in the skill's prompt. That is the
whole point of the technique this audits: if something has to be right every time,
an instruction is the wrong mechanism for it. A model asked to count 600 bullets
will produce a confident wrong number, and a different one tomorrow.

Nothing here is written. This script only reads and reports.

    python audit.py <notes-dir>
    python audit.py <notes-dir> --always-loaded MEMORY.md --always-loaded CLAUDE.md
    python audit.py <notes-dir> --subject acme --subject rate
    python audit.py <notes-dir> --json
    python audit.py --version          # version plus the heuristics below

requires-python: >=3.8. Zero dependencies.

Exit codes: 0 = scan completed (findings or not; this is a report, not a gate),
2 = the notes path is not a directory or an argument is invalid.

HEURISTICS (exactly what is counted, so a reader can predict a zero)
--------------------------------------------------------------------
1. CROSS-FILE VALUE CONFLICT. A subject whose dollar amounts disagree across
   **more than one file** (one file is enough when the folder holds <= 2 files).
   A single page listing "$2,800 in May, $3,200 in June" is history, and history
   is supposed to look like that. Amounts are compared like with like: /mo, /yr,
   /hr and one-time sums are separate buckets, and "$22k" equals "$22,000".
   A subject is the page's own name (per-subject pages), a bolded lead
   ("- **Retainer**: ..."), or a --subject term found in the line.
2. SAME-KEY CONFLICT ON ONE PAGE. On a per-subject page, a `Key: value` bullet
   whose key appears again with a different value under the same heading (and,
   for nested bullets, the same parent bullet). Keys are matched after
   lowercasing; a leading date or bold is ignored ("- 2026-03-01 Status: active"
   and "- **Status**: prospect" share the key "status"). Values are compared
   after lowercasing, collapsing whitespace, stripping markdown emphasis and
   trailing punctuation, and canonicalising dollar amounts. Free-text keys are
   ignored (see IGNORED_KEYS: notes, summary, context, todo, update ...), as are
   bullets under a Log/History/Timeline/Archive heading, dated-journal files,
   pages where >= 70% of bullets carry a date, and keys longer than 32 chars.
3. FINISHED BUT OPEN. A bullet containing done/shipped/paid/complete(d)/
   delivered/signed/cancelled/closed/launched under a heading whose text
   contains active/open/current/todo/in progress/now/doing/pending/backlog.
   A heading that starts exactly `## Current State` is exempt.
4. DATING. Share of bullets on non-journal pages that carry a YYYY-MM-DD or
   "Mon D" date.
5. NEAR-MISS SUBJECTS. Page-named subjects whose names are >= 86% similar
   (difflib ratio). Reported only, never merged.

Status words on their own are deliberately NOT a contradiction: "migration
COMPLETE" and "20 active deals" on one topic page read as a conflict to a regex
and as obviously unrelated to a human. Lifecycle conflicts need judgment, so
the skill hands those to the model. Every rule above exists because a checker
that cries wolf trains you to ignore it.
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

__version__ = "1.1.0"

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MONEY = re.compile(r"\$\s?\d(?:[\d,]*\d)?(?:\.\d+)?\s*k?(?:\s*/\s*(?:mo|month|yr|year|hr|hour))?",
                   re.I)
RECURRING = re.compile(r"/\s*(?:mo|month|yr|year|hr|hour)", re.I)


UNIT = {"mo": "/mo", "month": "/mo", "yr": "/yr", "year": "/yr", "hr": "/hr", "hour": "/hr"}


def money_value(raw: str) -> tuple[float, str] | None:
    """Canonical (amount, unit). '$22k' and '$22,000' are one value; unit is
    '' for a one-time sum or the normalised period ('/mo', '/yr', '/hr').

    Without this the audit reports a contradiction between two spellings of the
    same number, which is the fastest way to teach someone to ignore it. Keeping
    the real unit matters too: an hourly rate printed as '/mo' is a wrong answer
    dressed as a finding.
    """
    m = re.match(r"\$\s?([\d,]*\d)(\.\d+)?\s*(k?)", raw, re.I)
    if not m:
        return None
    amount = float(m.group(1).replace(",", "") + (m.group(2) or ""))
    if m.group(3).lower() == "k":
        amount *= 1000
    u = RECURRING.search(raw)
    unit = UNIT.get(u.group(0).strip("/ ").lower(), "") if u else ""
    return amount, unit


def fmt_money(amount: float, unit: str) -> str:
    s = f"${amount:,.0f}" if amount == int(amount) else f"${amount:,.2f}"
    return s + unit
STATUS = re.compile(
    r"\b(active|paused|cancell?ed|churned|shipped|launched|live|signed|closed|"
    r"won|lost|on hold|in progress|completed?|delivered|paid|pending|blocked)\b", re.I)
CONFLICTING_STATUS = {"active", "paused", "cancelled", "canceled", "churned",
                      "completed", "complete", "closed", "lost", "on hold", "live"}

FINISHED = re.compile(r"\b(done|shipped|paid|complete[d]?|delivered|signed|"
                      r"cancell?ed|closed|launched)\b", re.I)
OPEN_HEADING = re.compile(r"^#{1,4}\s+.*\b(active|open|current|todo|to do|in progress|"
                          r"now|doing|pending|backlog)\b", re.I)

DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|"
                  r"Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}\b")
LOG_HEADING = re.compile(r"^##+\s+(Log|History|Timeline|Archive)\b", re.I)
DATE_NAMED = re.compile(r"^\d{4}[-_]\d{2}([-_]\d{2})?$")

KEY = re.compile(r"^-\s*(?:\(?[^)]{0,24}\)?\s*)?\*\*(.+?)\*\*")
BULLET = re.compile(r"^\s*-\s+\S")
FENCE = re.compile(r"^\s*```")
SCHEMA_STATE = re.compile(r"^##\s+Current State\b", re.M | re.I)
SCHEMA_LOG = re.compile(r"^##\s+Log\b", re.M | re.I)

# A bolded lead that is an ACTION, not a subject. Heartbeat and session logs open bullets
# with these ("**Drafted 2 replies**", "**Meeting in 15min**"), and on a real vault they
# clustered every dollar amount in the daily logs under a verb instead of under the deal.
GENERIC_LEAD = re.compile(
    r"^(drafted|sent|replied|reviewed|created|updated|checked|posted|scheduled|completed|"
    r"meeting|reminder|heartbeat|summary|session|due|new|urgent|note|todo|error|warning|"
    r"\d+\s+(new\s+)?(reply|replies|emails?|tasks?|messages?|items?))\b",
    re.I,
)

# Pages that are indexes or config, not per-subject pages.
NOT_A_SUBJECT = {"index", "readme", "memory", "claude", "soul", "user", "schema",
                 "heartbeat", "repositories", "core-memories", "todo", "inbox"}

# `- [date] [**]Key[**] [(date)]: value`. The key must start with a letter, hold no
# colon, and stay short: a long "key" is a sentence with a colon in it.
KV = re.compile(
    r"^(\s*)-\s+(?:\(?(?:\d{4}-\d{2}-\d{2})\)?\s*)?"
    r"(?:\*\*)?([A-Za-z][A-Za-z0-9 /&'().-]{0,31}?)(?:\*\*)?"
    r"\s*(?:\((?:\d{4}-\d{2}-\d{2}|[^)]{0,24})\))?\s*:\s+(.+?)\s*$")

# Keys whose value is prose, a running commentary, or an event. Two different
# values under one of these is normal writing, not two answers to one question.
IGNORED_KEYS = {
    "note", "notes", "summary", "context", "background", "description", "details",
    "detail", "comment", "comments", "todo", "to do", "next", "next step", "next steps",
    "action", "actions", "action item", "action items", "update", "updates", "log",
    "history", "link", "links", "tag", "tags", "see also", "related", "source",
    "sources", "ref", "refs", "reference", "references", "quote", "example",
    "examples", "idea", "ideas", "question", "questions", "meeting", "call", "email",
    "task", "tasks", "decision", "lesson", "lessons", "why", "how", "what", "when",
    "where", "http", "https", "re", "aka", "e.g", "eg", "i.e", "ie", "tl;dr", "tldr",
}


def norm(s: str) -> str:
    s = MONEY.sub(" ", s)
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def page_subject(stem: str) -> str | None:
    """A per-subject page lends its name to every value on it.

    Without this, a line like "- Retainer is **$6,000/mo** as of March" is
    unattributable: the bolded key is the value itself and the client is never
    named, because the filename already says it.
    """
    s = stem.lower()
    # Notion and similar exporters append a 32-char hex id to every filename.
    # Left in place it makes the subject "acme corp 1a2b3c..." which matches
    # nothing in the prose, so the whole vault becomes unattributable.
    s = re.sub(r"[\s_-]+[0-9a-f]{8,32}$", "", s)
    if DATE_NAMED.match(s) or s in NOT_A_SUBJECT or len(s) < 3:
        return None
    return norm(s.replace("-", " ").replace("_", " "))


def norm_key(s: str) -> str:
    """Normalise a bullet key for comparison: lowercase, no emphasis marks, single spaces."""
    return re.sub(r"\s+", " ", s.strip().lower().strip("*_` "))


def norm_value(s: str) -> str:
    """Lowercase, de-emphasise, canonicalise money, collapse whitespace, drop
    trailing punctuation. "$22k" and "$22,000." become one value."""
    def _money(m):
        """Replace a money match with its canonical form, or leave it as written."""
        mv = money_value(m.group(0))
        return fmt_money(*mv) if mv else m.group(0)
    s = MONEY.sub(_money, s)
    s = re.sub(r"[*_`]+", "", s.lower())
    s = re.sub(r"\s+", " ", s).strip().rstrip(".;,")
    return s


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def iter_lines(text: str):
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield i, line


def scan(root: Path, extra: list[str]):
    # The skill's own report (phase 8) quotes stale claims verbatim, so a later run
    # would read them as live values and contradict itself. Skip it by name.
    """Read every markdown note under root and collect the raw material every heuristic needs."""
    files = sorted(p for p in root.rglob("*.md")
                   if ".git" not in p.parts and not p.name.startswith("second-brain-audit"))

    # Pass 1: the subject vocabulary, taken from the names of per-subject pages.
    vocab: dict[str, str] = {}
    for p in files:
        subj = page_subject(p.stem)
        if subj and len(subj) >= 4:
            vocab[subj] = p.stem
    named: set[str] = set()
    for t in extra:
        vocab[norm(t)] = t
        named.add(norm(t))

    subjects: dict[str, list] = defaultdict(list)
    # (file, heading path, parent bullet, key) -> [{line, value, raw}]
    kv_seen: dict[tuple, list] = defaultdict(list)
    money_seen = 0
    journal_files = 0
    bullets = dated = 0
    durable_bullets = durable_dated = 0
    finished_open: list[tuple[str, int, str]] = []
    schema_pages: list[str] = []
    words = 0

    for p in files:
        text = read(p)
        words += len(text.split())
        rel = str(p.relative_to(root)).replace("\\", "/")
        own = page_subject(p.stem)
        # A daily/journal file carries its date in its name; its bullets do not
        # each need one, so they are excluded from the dating metric.
        is_journal = bool(DATE_NAMED.match(p.stem.lower()))
        journal_files += is_journal
        if SCHEMA_STATE.search(text) and SCHEMA_LOG.search(text):
            schema_pages.append(rel)

        # A page that dates nearly every bullet is a chronological record. Its
        # values are history laid out in order, not rival claims about now, so
        # it is read for dating stats but never used as a current answer.
        page_bullets = [l for _, l in iter_lines(text) if BULLET.match(l)]
        n_dated = sum(1 for l in page_bullets if DATE.search(l))
        is_chronological = len(page_bullets) >= 5 and n_dated / len(page_bullets) >= 0.7

        under_open = under_log = False
        heading = ""
        parent_bullet = ""
        # (level, text, is_log) for every heading still open above this line. A child
        # heading inherits its parents' Log exclusion: a `### 2025` under `## Log` is
        # still history, not two rival `Status:` claims about now.
        heading_stack: list[tuple[int, str, bool]] = []
        for lineno, line in iter_lines(text):
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, line.strip("# ").strip().lower(),
                                      bool(LOG_HEADING.match(line))))
                under_open = bool(OPEN_HEADING.match(line))
                under_log = any(is_log for _, _, is_log in heading_stack)
                heading = " > ".join(t for _, t, _ in heading_stack)
                parent_bullet = ""
                # A `## Current State` section holds values, not to-dos. "PAID" there is
                # a state, not a finished item forgotten in an open list.
                if SCHEMA_STATE.match(line):
                    under_open = False
                continue
            if not BULLET.match(line):
                continue
            bullets += 1

            # Same key, different value, one page: the appended-state bug itself.
            # Scoped by heading and, for nested bullets, by the parent bullet, so a
            # page listing several tasks each with its own "Status:" is not flagged.
            kv = KV.match(line)
            if kv and own and not is_journal and not (under_log or is_chronological):
                indent, key, value = kv.group(1), norm_key(kv.group(2)), kv.group(3)
                if key not in IGNORED_KEYS and value.strip():
                    scope = (rel, heading, parent_bullet if indent else "", key)
                    kv_seen[scope].append({"line": lineno, "value": norm_value(value),
                                           "text": line.strip()[:108]})
            if not line.startswith((" ", "\t")):
                parent_bullet = line.strip()[:60]
            has_date = bool(DATE.search(line))
            dated += has_date
            if not is_journal:
                durable_bullets += 1
                durable_dated += has_date
            if under_open and FINISHED.search(line):
                finished_open.append((rel, lineno, line.strip()[:110]))

            # A `## Log` section is history by declaration. Respecting that is
            # what makes a page stop being flagged once it has been fixed.
            if under_log or is_chronological:
                continue

            money = MONEY.findall(line)
            money_seen += len(money)
            status = [s.lower() for s in STATUS.findall(line)]
            if not (money or status):
                continue

            keys = set()
            m = KEY.match(line.strip())
            if m and not GENERIC_LEAD.match(m.group(1).strip()):
                k = norm(m.group(1))
                if len(k) >= 4:
                    keys.add(k)
            if own:
                keys.add(own)
            low = " " + norm(line) + " "
            for v in vocab:
                # a named --subject matches as a word prefix ("tax" finds "taxes");
                # a page-derived subject must match whole, or "ai" would match everything.
                if f" {v} " in low or (v in named and re.search(rf"\b{re.escape(v)}\w*", low)):
                    keys.add(v)

            for k in keys:
                subjects[k].append(
                    {"file": rel, "line": lineno, "money": money, "status": status,
                     "text": line.strip()[:108]})

    return (files, subjects, bullets, dated, durable_bullets, durable_dated,
            finished_open, schema_pages, words, vocab, money_seen, journal_files,
            kv_seen)


def key_conflicts(kv_seen: dict) -> list[dict]:
    """One key, two or more distinct values, on one page under one heading.

    This is the detector the money rule cannot be: "Status: prospect" followed
    by "2026-03-01 Status: active customer" has no number in it and is exactly
    the appended state the skill exists to find. Identical repeated values are
    not reported; neither is anything under a Log heading.
    """
    out = []
    for (rel, heading, parent, key), hits in kv_seen.items():
        values = {}
        for h in hits:
            values.setdefault(h["value"], h)
        if len(values) < 2:
            continue
        out.append({"file": rel, "heading": heading, "key": key,
                    "values": [h["value"] for h in values.values()],
                    "hits": list(values.values())})
    out.sort(key=lambda c: (-len(c["values"]), c["file"], c["hits"][0]["line"]))
    return out


def contradictions(subjects: dict, min_files: int = 2) -> list[dict]:
    """min_files is normally 2: a disagreement inside one page is usually history.

    A vault that IS one or two files has no cross-file option, so that rule would
    silently make it unauditable. There, one file is enough.
    """
    out = []
    for subj, hits in subjects.items():
        seen = set()
        uniq = []
        for h in hits:
            k = (h["file"], h["line"])
            if k not in seen:
                seen.add(k)
                uniq.append(h)
        if len(uniq) < 2:
            continue

        # Compare like with like: recurring rates and one-time amounts are
        # different facts, not two versions of the same one.
        for bucket in ("/mo", "/yr", "/hr", ""):   # each rate unit, then one-time sums
            vals: dict[str, list] = {}
            for h in uniq:
                for v in h["money"]:
                    mv = money_value(v)
                    if mv is None or mv[1] != bucket:
                        continue
                    vals.setdefault(fmt_money(*mv), []).append(h)
            files = {h["file"] for g in vals.values() for h in g}
            if len(vals) >= 2 and len(files) >= min_files:
                out.append({"subject": subj,
                            "kind": "recurring" if bucket else "onetime",
                            "values": sorted(vals),
                            "hits": [h for g in vals.values() for h in g]})
                break
        # Status words are deliberately NOT used to claim a contradiction.
        # Tried it; "migration COMPLETE" and "20 active deals" on one topic page
        # read as a conflict to a regex and as obviously unrelated to a human.
        # Lifecycle conflicts ("page says launching, log says cancelled") need
        # judgment, so the skill hands that to the model instead. This script
        # only reports what it can count without being wrong.
    out.sort(key=lambda c: (-len({h["file"] for h in c["hits"]}), -len(c["hits"])))
    return out


def near_misses(subjects: dict, vocab: dict) -> list[tuple[str, str]]:
    """Keys that may be the same subject. REPORTED, never merged: a duplicate
    key is a cheap mistake, a wrong merge destroys information.

    Restricted to subjects that own a page. Arbitrary bolded leads produce pairs
    like '10 active drafts' ~ '17 active drafts', which is noise."""
    keys = sorted(k for k in subjects if len(subjects[k]) > 1 and k in vocab)
    pairs = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if abs(len(a) - len(b)) > 12:
                continue
            if 0.86 <= difflib.SequenceMatcher(None, a, b).ratio() < 1.0:
                pairs.append((a, b))
    return pairs[:10]


def main() -> int:
    """Audit a notes folder (read only) and print the report or --json."""
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes", type=Path, help="folder of markdown notes (read only)")
    ap.add_argument("--always-loaded", action="append", default=[], metavar="PATH",
                    help="a file your agent reads every session, as a name or a path "
                         "relative to the notes folder (repeatable)")
    ap.add_argument("--subject", action="append", default=[], metavar="TERM",
                    help="a subject to attribute values to, one stem per flag "
                         "(`rate`, not `\"Hourly rate\"`); repeatable")
    ap.add_argument("--json", action="store_true", help="structured output instead of the report")
    ap.add_argument("--version", action="version",
                    version=f"audit.py {__version__}: heuristics = cross-file money conflict, "
                            "same-key conflict on one page, finished-but-open, dating share, "
                            "near-miss subjects. See --help for the exact rules.")
    a = ap.parse_args()

    root = a.notes.expanduser().resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    (files, subjects, bullets, dated, dur_b, dur_d,
     fin_open, schema, words, vocab, money_seen, journals, kv_seen) = scan(root, a.subject)
    conts = contradictions(subjects, min_files=1 if len(files) <= 2 else 2)
    kconf = key_conflicts(kv_seen)
    always = [s.replace("\\", "/").lower().lstrip("./") for s in a.always_loaded]

    def in_always(h):
        # Match whole path components: `MEMORY.md` names memory.md anywhere in the
        # tree, not `archive/OLDMEMORY.md`.
        """True when a hit's file is one of the --always-loaded names, matched by whole path components."""
        f = h["file"].lower()
        return any(f == al or f.endswith("/" + al) for al in always)

    hot = [c for c in conts if any(in_always(h) for h in c["hits"])]
    hot_keys = [c for c in kconf if in_always(c)]
    always_money = sum(
        len(h["money"]) for hits in subjects.values() for h in hits if in_always(h)
    ) if always else 0
    pct = round(100 * dur_d / dur_b) if dur_b else 0
    rels = [str(p.relative_to(root)).replace("\\", "/").lower() for p in files]
    # Names that point at no scanned file. Computed before the JSON branch so a JSON
    # consumer can tell "always-loaded file has no conflicts" from "never looked at it".
    unmatched = [al for al in always if not any(f == al or f.endswith("/" + al) for f in rels)]

    if a.json:
        print(json.dumps({
            "version": __version__,
            "files": len(files), "words": words, "durable_bullets": dur_b,
            "dated_pct": pct, "contradicted_subjects": len(conts),
            "contradictions_in_always_loaded": len(hot),
            "key_conflicts": len(kconf),
            "key_conflicts_in_always_loaded": len(hot_keys),
            "finished_but_open": len(fin_open), "schema_pages": len(schema),
            "always_loaded_unmatched": unmatched,
            "coverage_warnings": (
                [{"code": "always_loaded_unmatched", "names": unmatched,
                  "meaning": "these --always-loaded names matched no scanned file, so the "
                             "*_in_always_loaded counts do not cover them"}]
                if unmatched else []),
            "detail": [dict({k: c[k] for k in ("subject", "kind", "values")},
                            files=sorted({h["file"] for h in c["hits"]})) for c in conts[:25]],
            "key_conflict_detail": [
                {"file": c["file"], "heading": c["heading"], "key": c["key"],
                 "values": c["values"], "lines": [h["line"] for h in c["hits"]]}
                for c in kconf[:25]],
        }, indent=1))
        return 0

    W = 76
    print("=" * W)
    print(f"SECOND BRAIN AUDIT  ·  {root}")
    print("=" * W)
    print(f"  {len(files):,} files · {words:,} words · {dur_b:,} bullets on durable pages")
    if schema:
        print(f"  {len(schema)} page(s) already use Current State / Log")

    print(f"\n{'-' * W}\n1. ONE SUBJECT, TWO PLACES, DIFFERENT ANSWERS\n{'-' * W}")
    if not conts:
        print("  None found.")
    for c in conts[:6]:
        star = "  ***" if any(in_always(h) for h in c["hits"]) else ""
        print(f"\n  {c['subject']}  ->  {len(c['values'])} answers: "
              f"{', '.join(c['values'][:6])}{star}")
        for h in sorted(c["hits"], key=lambda x: x["file"])[:5]:
            flag = "   <-- ALWAYS LOADED" if in_always(h) else ""
            print(f"      {h['file']}:{h['line']}{flag}")
            print(f"        {h['text']}")
    if len(conts) > 6:
        print(f"\n  ... and {len(conts) - 6} more.")

    print(f"\n{'-' * W}\n2. ONE KEY, TWO VALUES, SAME PAGE  (appended state)\n{'-' * W}")
    if not kconf:
        print("  None found.")
    for c in kconf[:8]:
        flag = "   <-- ALWAYS LOADED" if in_always(c) else ""
        where = f" under '{c['heading']}'" if c["heading"] else ""
        print(f"\n  {c['file']}{where}: '{c['key']}' has {len(c['values'])} values{flag}")
        for h in c["hits"][:4]:
            print(f"      :{h['line']}  {h['text']}")
    if len(kconf) > 8:
        print(f"\n  ... and {len(kconf) - 8} more.")

    print(f"\n{'-' * W}\n3. CAN YOU RESOLVE A CONFLICT BY DATE?\n{'-' * W}")
    print(f"  {dur_d:,} of {dur_b:,} bullets on durable pages carry a date  ({pct}%)")
    if pct < 60:
        print("  Under ~60%, \"just use the newest one\" is not available to you or")
        print("  to your agent, because most entries never say when they were written.")

    print(f"\n{'-' * W}\n4. FINISHED, BUT STILL IN AN OPEN LIST\n{'-' * W}")
    if not fin_open:
        print("  None found.")
    for f, ln, txt in fin_open[:6]:
        print(f"  {f}:{ln}\n    {txt}")
    if len(fin_open) > 6:
        print(f"  ... and {len(fin_open) - 6} more.")

    nm = near_misses(subjects, vocab)
    if nm:
        print(f"\n{'-' * W}\n5. POSSIBLY THE SAME SUBJECT  (reported, never merged)\n{'-' * W}")
        for x, y in nm:
            print(f"  {x!r}  ~  {y!r}")

    print(f"\n{'=' * W}\nVERDICT\n{'=' * W}")
    print(f"  {len(conts)} subject(s) answered differently in more than one file.")
    print(f"  {len(kconf)} key(s) given two or more values on one page.")
    if always:
        print(f"  {len(hot) + len(hot_keys)} of those touch a file your agent loads every session. ***")
        print("  (dollar amounts and repeated `Key: value` lines only: a status that changed")
        print("   inside prose is invisible to this count. Phase 2 is the audit of the")
        print("   always-loaded file.)")
    else:
        print("  Re-run with --always-loaded <file> to find which of these your")
        print("  agent reads on every session. Those are the ones that bite.")
    print(f"  {len(fin_open)} finished item(s) still sitting in an open list.")
    print(f"  {pct}% of durable bullets are dated.")

    # A zero here means one of two very different things, and saying "clean" when
    # the scan simply could not see is the worst failure this tool has available.
    blind = []
    if not money_seen and not kv_seen:
        blind.append("No dollar amounts and no `Key: value` bullets anywhere. Those are\n"
                     "    the only things this scan can compare without guessing, so it\n"
                     "    has checked almost nothing. Name the facts that matter with\n"
                     "    --subject, and read the notes directly.")
    if journals and journals == len(files):
        blind.append("Every file is a dated journal. That is an event log, and events\n"
                     "    are supposed to accumulate. The question is not whether these\n"
                     "    are messy, it is whether any file anywhere holds the CURRENT\n"
                     "    value. If not, the missing piece is a state layer, not a fix.")
    if not vocab:
        blind.append("No per-subject pages found, so values could not be attributed to\n"
                     "    a subject across files. Pass --subject to name them.")
    if always and not hot and not hot_keys and always_money:
        blind.append(f"The always-loaded file(s) carry {always_money} line(s) with a dollar\n"
                     "    amount and none matched a flagged subject. Either every value there\n"
                     "    agrees with the rest of the notes, or the disagreement is in prose\n"
                     "    (paid, on hold, cancelled), which this scan cannot see. Read that file\n"
                     "    claim by claim (phase 2) before calling it clean.")
    if unmatched:
        which = "None of the --always-loaded names" if len(unmatched) == len(always) \
            else f"{len(unmatched)} --always-loaded name(s) ({', '.join(unmatched)})"
        blind.append(f"{which} matched a file under the notes\n"
                     "    folder, so the ALWAYS LOADED marks above are absent for them. Check\n"
                     "    the spelling, or pass the path relative to the notes folder.")
    if blind:
        print(f"\n{'-' * W}\n  COVERAGE WARNING: a low count above may mean 'not visible',\n"
              f"  not 'not present'.\n{'-' * W}")
        for b in blind:
            print(f"  *  {b}")

    print("\n  Nothing was modified. This script only reads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
