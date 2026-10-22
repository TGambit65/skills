---
name: second-brain-audit
description: Audits a second brain, notes folder, vault, or agent memory for facts that quietly stopped being true: checks each current-sounding claim the agent loads every session against the freshest evidence, then fixes the worst location so it stops recurring. Use when an assistant gives an outdated answer, when notes or memory files may be stale, when a vault needs checking for contradictions, or when someone mentions memory rot or state versus event.
argument-hint: "[path-to-notes-folder]"
arguments: [notes]
---

# Second Brain Audit

Notes rot in a specific way. Nothing is corrupted and nothing goes missing: a fact
simply stops being true, the note keeps saying it, and nothing raises a hand. The cause
is almost always the same. **The write path can only append.** New information becomes
a new line under the old line, which is correct for some facts and ruinous for others.

## The one idea

Every stored fact is one of two kinds.

| | Meaning | Correct update |
|---|---|---|
| **State** | one current value, and it **changes** | **replace** it |
| **Event** | a timestamped thing that **happened** | **append** it |

A price, a status, an owner, a deadline: state. A payment, a signature, a decision, a
lesson learned: event. The update rules are **opposites**. Replacing an event destroys
history. Appending a state creates two answers to one question, and the stale copy
usually sits higher in the file, so it is read first.

**Structure carries this rule, not an instruction.** Asking a model, or a person, to
remember to update the old entry fails quietly and constantly. Give the page two
sections and the rule follows from where a fact lands.

## Phase 1: establish the shape

**Do not assume a wiki, a vault, or pages.** Most people have none of those. Look at what
exists first, because it changes what the audit can see and what the fix should be.

| Shape | Looks like | Where state should live |
|---|---|---|
| **Page per subject** | `clients/acme.md`, `projects/x.md` | two sections on each page |
| **One big file** | a single `notes.md` or `CLAUDE.md` | a `## Current State` block at the top |
| **Daily notes only** | `2026-06-01.md`, and nothing else | **nothing to convert.** A state layer is missing entirely |
| **Not markdown** | Notion, Apple Notes, a chat assistant's memory | the idea still applies; the tooling does not |

The notes folder this run was invoked with is `$notes`, and it is optional
(`/second-brain-audit ~/notes`). Use it when it is a real path. When nothing was passed,
so the line above still reads `\$notes`, use the working directory and confirm it with the
user. When it is a path that does not exist, say so and stop rather than auditing the
wrong folder.

Then establish two things:

1. **Where the notes live.** A folder of markdown, for the scan.
2. **What the agent reads on every session.** `CLAUDE.md`, a `MEMORY.md`, a system prompt
   file, whatever loads automatically. This matters more than anything else: a stale fact
   in an archive is harmless, the same fact in the always-loaded file is the bug. If the
   user does not know, say so and run without it.

Name daily-notes-only out loud. Dated notes are an **event log**, and events are supposed
to accumulate; what is missing is any place that says what is true *now*. Telling someone
to restructure their journal would be actively wrong.

## Phase 2: audit the always-loaded surface

**This works on every second brain**, in any tool, in any domain, with or without the
script. Run it always, even when the scan found plenty. Whatever the agent reads on every
session is small enough to read in full and check claim by claim.

1. **Read that surface completely.** Then check it actually arrives in full: hooks and
   context budgets truncate, usually from the bottom, and a file that is "always loaded"
   on disk can reach the agent as its oldest third. Audit what arrives, and treat the cut
   itself as a finding.
2. **Extract every state-shaped claim.** Anything phrased as a current fact: a status, an
   owner, a rate, a version, a deadline, a "currently", a "we use", a "lives at". Ignore
   anything phrased as an event, since events stay true.
3. **For each claim, find the freshest evidence anywhere in the notes.** Grep the subject.
   Read the newest file that mentions it.
4. **Sort each claim into three piles:**
   - **Confirmed.** The detail agrees.
   - **Contradicted.** Something newer disagrees. This is rot, and it is the headline.
   - **Unsupported.** Nothing anywhere backs it up. Often the claim was true once and the
     evidence was never written, which is worth saying out loud.

A few dozen claims is typical and is a few minutes of reading. Report the contradicted
pile first, then the unsupported pile. Both are findings.

## Phase 3: run the scan, if the notes suit it

An accelerator, not the audit. It applies to markdown folders where facts carry dollar
amounts or sit on `Key: value` bullets. Skip it otherwise; phase 2 already did the work.

```bash
python <skill>/scripts/audit.py <notes-dir> \
    --always-loaded MEMORY.md --always-loaded CLAUDE.md \
    --subject rate --subject <one word per subject that matters>
```

Pass `--subject` for every subject you care about, one word each (`rate`, not
`"Hourly rate"`): on a small folder the script attributes values by page name and bold
key only, so without it a real cross-file contradiction can come back as a clean zero
with no warning. `--json` gives structured output; `--help` states the exact heuristics.
It only reads; it never writes.

It reports two kinds of contradiction: the same subject with different dollar amounts in
more than one file, and the same `Key:` given two values on one page (`Status: prospect`
followed by `2026-03-01 Status: active customer`). **A zero is not a clean bill of
health.** A status that changed inside prose ("$32,300 due" versus "$32,300 on hold") is
invisible to it, and its "touch a file your agent loads" count covers only what it can
see; the always-loaded file is audited in phase 2, never by that count. When it prints a
COVERAGE WARNING, read it out rather than reporting "no problems found".

Why a script at all: the count has to be the same twice, and a model asked to tally 600
bullets returns a confident number and a different one tomorrow. The script counts; the
agent judges.

## Phase 4: read what neither can see

Open a few flagged pages and look for what no regex will catch:

- **Lifecycle conflicts.** A page saying "launching next week" while a log entry from
  three months ago records the project being cancelled. No number disagrees, so nothing
  is flagged, and it is completely wrong.
- **Facts never written down at all.** The most common cause of a wrong answer: the true
  value only ever existed in a conversation or a daily note, and reorganizing cannot reach
  it. Say so plainly rather than implying the restructure will help; the audit's real
  value is identifying *which* of the two problems is in play.
- **Pages that must not be touched.** Checklists, reference lists, packing lists are lists
  on purpose. Converting one destroys what makes it useful, and every structural check
  still passes.
- **Two true lines, one impossible schedule.** Nothing checks two Current State lines
  against each other. Two deliverables "live 9/23" on two keys is either a real conflict
  or a shared host video, and the lines should say which. Grep the block for repeated
  dates.
- **A fresh date on a value nobody checked.** A rewrite that re-dates lines it merely
  moved, or a "rows verified today" note over a table seeded months ago, gives stale values
  the one thing that would have exposed them. Check `git blame` on a freshly dated line
  before trusting it; a date claims the value was verified, not that the line was touched.
- **Key sprawl.** One subject across many Current State keys ("Brief 10050 draft", "Brief
  10050 review pass", "Brief 10050 record day"). Every key is unique, so the duplicate
  check passes, and the freshest can still be stale. Same fix as the duplicate-key bug:
  one key per thing that has one status. Report it; collapsing is the owner's call.

## Phase 5: report

Lead with the single most damaging finding, not a summary of the tool's output:

> Three different answers for what Acme pays, and the oldest one is in the file the agent
> reads every session.

Where an agent already runs over these notes, **demonstrate it**: ask the question the
notes should answer and read the reply out. Point out the common case where it is
*diligent and still wrong*: it checks a page, warns that another file looks stale, and
still misses the true value because that value was never promoted anywhere durable. On a
small folder a capable agent will read everything and find the truth, so confine the
demonstration to what the agent is actually handed every session (paste the always-loaded
file alone, or run with read tools off). The gap between the two answers is the finding.

## Phase 6: fix one place

Never bulk-convert, and never convert a page the user did not agree to. Fix the single
worst *location*, which depends on the shape found in phase 1:

- **Page per subject** → give that one page the two sections below.
- **An index the agent loads every session** (a `MEMORY.md`, a pinned summary) → it is
  state, whatever it calls itself. Put a dated `## Current State` block at the TOP so it
  survives any truncation, key each line on the deal, and move superseded lines verbatim
  to a `## Log` at the bottom. Leave the to-do list in between.
- **One big file** → add a `## Current State` block at the top and leave everything else
  beneath it. No new files, no folder structure. If the file already has a block that
  claims to be current ("Current status", "Now", "Active"), its lines move into the new
  block or into the Log by rule 2. Two sections claiming now is the bug you are removing,
  so never leave the old block in place.
- **Daily notes only** → create **one** file holding current values, and leave every
  journal entry untouched. The journal was already correct.
- **Not markdown** → do not restructure anything. Explain where the current value should
  live in the tool they already use, and stop there.

The shape below is the page-per-subject version; adapt the same two ideas to the others.
What has to be true in every case: **one place says what is true now, and it gets replaced
rather than added to.**

```markdown
## Current State
<!-- One entry per subject. Dated. REPLACED on update, never appended to. -->

- **Retainer** (2026-08-01): $3,200/mo, renewed through February 2027
- **Main contact** (2026-05-02): Curtis Ilo

## Log
<!-- Append-only. Never edit or delete an entry. -->

- (2026-04-30) Delivered and paid, $21,000
- (2026-05-02) Retainer started at $2,800/mo
- (2026-06-15) Added reply drafting, retainer to $3,200/mo
```

Conversion rules, in order of importance:

1. **Lose nothing.** Every existing line lands in one of the two sections, verbatim. This
   is sorting, not rewriting. Improving the prose is how information disappears without
   anyone noticing.
2. **One entry per subject in Current State.** Where two lines describe the same current
   value, the newer wins and the older moves to the Log. Where the order is unclear, ask.
   Never guess.
3. **Date every Current State entry.** Ask for a missing date or take it from file history.
   The date on a line you moved is the line's own date, never today's: dating is a claim
   that the value was checked, and a move checks nothing.
4. **Never merge two subjects that merely look similar.** "Acme (May)" and "Acme Corp
   renewal" may be genuinely different things. A duplicate entry is a cheap mistake; a
   wrong merge destroys information. Report near-misses and let the user decide.
5. **Show a diff and get approval** before writing.

Re-ask the earlier question afterwards so the correct answer is visible. Then record what
is still outstanding (phase 8), or the next run starts from nothing.

## Phase 7: change the write path

Converting pages fixes today; changing how facts get written is what stops the
recurrence. Add to whatever file instructs the agent (`CLAUDE.md`, `AGENTS.md`, a system
prompt):

```markdown
## Writing to these notes

Every fact is state or event.

- **State** (one current value that changes: price, status, owner, date):
  find the matching line in `## Current State` and REPLACE it. Always date it.
  Never add a second line for the same subject.
- **Event** (a thing that happened): append to `## Log`. Never edit or delete
  an existing Log entry.

If unsure, append to the Log and say so. A missing state update is recoverable;
a rewritten history is not.
```

Then state the honest part: this instruction gets followed most of the time, not all of
the time. Anything that must happen every time needs a mechanism. Cheap ones worth more
than the instruction:

- Re-run this audit on a schedule and watch whether the contradicted count from phase 2
  climbs; phase 8 makes that comparison possible. The script's "finished but open" total
  can rise after a correct fix if the block is headed "Current status" or "Active" rather
  than exactly `## Current State`, because "paid" and "complete" under those headings
  match its open-list regex.
- Stamp dates with a script after the fact instead of asking for them.
- Regenerate any column that can be regenerated (a repo's visibility from the forge, a
  version from the package file) instead of typing it. A value nobody checks is wrong
  within a quarter.

## Phase 8: leave the findings somewhere durable

Everything above exists only in a conversation. Close the window and the audit is gone,
which is the same failure this skill is about, committed by the skill itself. So write it
down, in the shape being taught. **One file** in the notes folder, called
`second-brain-audit.md`:

```markdown
# Second brain audit

## Current State
<!-- One entry per location. REPLACED when that location changes. -->

- **MEMORY.md** (2026-09-18): the always-loaded file. 6 contradicted, 3 unsupported.
  FIXED this run, `## Current State` block added at the top, 9 superseded lines to `## Log`.
- **clients/acme.md** (2026-09-18): 4 contradicted, all about the retainer. NEXT.
- **notes/tools.md** (2026-09-18): 2 unsupported, no trail, low value. Leave it.
- **write path** (2026-09-18): rule added to `CLAUDE.md`.

## Log
<!-- Append-only. One entry per audit run. -->

- (2026-09-18) First run. 24 claims in the always-loaded file: 13 confirmed,
  6 contradicted, 5 unsupported. Fixed MEMORY.md. Asked "what do we charge Acme?"
  before and after, and got $4,000 then $9,500.
```

Four rules for that file:

1. **Each location is a key.** Fixing it REPLACES its line. Never a second line for one
   location.
2. **Each run is one Log entry**, carrying the contradicted count. If it climbs over time,
   the write path is not holding.
3. **Keep it out of what loads every session.** It is a work queue, not a fact about the
   business, and it quotes stale claims verbatim. `audit.py` skips any file whose name
   starts with `second-brain-audit`, so the report never comes back as evidence.
4. **Something else reads it next.** `/second-brain-fix` works the queue in batches, and a
   later audit reads the Log to see whether the count moved. Fixing starts at whatever is
   marked NEXT, unless a later run turns up something worse.

### Then hand it to the fixer

Say this out loud at the end, because it is the question every user has and the answer
is not "run this again":

> The audit fixed one location so you could see the shape. To work through the rest, run
> `/second-brain-fix`, or `/second-brain-fix <path to this file>` from anywhere else. It
> reads this same file, batches the findings, and updates the ledger as it goes.

One location at a time is correct for this skill and useless as a plan. The batch job is a
separate skill with a different contract: this one never bulk-converts and gates every
write behind a diff; that one writes many files at once and requires a branch or a copy
before it starts.

### Stop when the surface is clean

There is no version of this where every page gets converted, and chasing that is how
people quit in week two. The finish line is narrow: **nothing contradicted in what the
agent loads every session.** An archive full of old pages is history, not rot. Convert a
deeper page only when it has a trail (several entries about one subject over time) or
keeps producing wrong answers. Restructuring alone often moves the number less than
people expect; when it does not move, the usual reason is a fact nobody ever wrote down.
Say so when it applies.

## Resources

- `scripts/audit.py`: the deterministic scan. `--help` lists all flags and the exact
  heuristics, `--json` returns structured findings. Never read it into context; only
  its output.
