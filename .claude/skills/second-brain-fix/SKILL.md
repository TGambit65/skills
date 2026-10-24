---
name: second-brain-fix
description: Works through a second-brain audit's findings file in batches, correcting stale facts and converting pages onto the state/event schema. Use after second-brain-audit, when someone wants to fix the rest of their notes rather than one page, asks how to take the audit forward, has contradicted or unsupported claims to work through, or needs a notes folder converted in bulk.
argument-hint: "[path-to-audit-findings.md]"
arguments: [audit-results]
---

# Second Brain Fix

This works through the audit's findings in batches. Every fact is still **state** (one
current value: replace it) or **event** (a thing that happened: append it), and every edit
below is one of those two moves.

## This skill writes in bulk. Settle backups before it does.

Nothing is written until this is settled. Resolve the findings path (next section) to learn
where the notes live, then, in that folder, run `git rev-parse --show-toplevel`.

- **Already in git**, either its own repo or tracked by a parent one. A repo that merely
  *contains* the folder is not a backup: check that the notes themselves are tracked
  (`git ls-files -- <notes-folder> | head` lists them, and
  `git ls-files --others --exclude-standard -- <notes-folder>` (untracked) plus
  `git ls-files --others --ignored --exclude-standard -- <notes-folder>` (ignored, which the
  first command hides, even inside a tracked folder) list no file a batch could edit; an
  ignored app cache such as `.obsidian/` is fine, an ignored note is not). If they are tracked,
  commit or stash anything outstanding so the baseline is committed, then
  `git checkout -b second-brain-fix`, and commit after every batch. Say which repo you are in
  and what the branch covers. If some or all of the notes are untracked or ignored, the
  branch gives no rollback for them: offer to add and commit them as the baseline, and if the
  user declines, treat it as **Not in git** below and take the informed no-backup
  confirmation.
- **Not in git.** Ask, in these words or close to them:

  > Your notes are not in git, so there is no way to undo a batch. Want me to run `git init`
  > here first? It stays on your machine, nothing gets pushed anywhere, and every batch becomes
  > a checkpoint you can roll back to.

  If they agree: `git init`, `git add -A`, one baseline commit, then the branch. Never add a
  remote and never push.

  If they decline, ask once more and take the answer:

  > Understood. To be clear, this rewrites many files at once and there will be no way to undo
  > it. Go ahead anyway?

  On a clear yes, proceed and do not raise it again. On silence or anything ambiguous, stop.
  An unanswered question is not permission.

Never resolve this by copying the notes folder somewhere else (rule 6).

**Then check the write path.** If `CLAUDE.md` (or `AGENTS.md`, or the system prompt) does not
yet carry the state/event rule from the audit's phase 7, add it before the first batch and say
why: fixing four hundred lines under a write path that can only append buys about a month.

## The argument

The findings file this run was invoked with is `$audit-results`, and it is optional:

```
/second-brain-fix                                   nothing passed
/second-brain-fix ~/notes                           a folder to look in
/second-brain-fix ~/notes/second-brain-audit.md     the findings file itself
```

`$audit-results` is **a path to one markdown file of findings**, usually the
`second-brain-audit.md` that `/second-brain-audit` wrote, but the name is not the contract:
whatever the user points at is the one to use. Resolve it before anything else:

| What you were given | Do |
|---|---|
| a path to a **file** | that is the findings. The notes folder is its parent, unless the file names a different one |
| a path to a **folder** | look inside it for the findings, `second-brain-audit.md` first |
| nothing, so the line above still reads `\$audit-results` | look in the current folder, then one level down |
| **a path that does not exist** | say so and stop. Do not fall back to searching, or a typo silently works on the wrong folder |
| **more than one candidate** when searching | list them with their newest `## Log` dates and ask which |
| **no candidate** when searching | stop. Say to run `/second-brain-audit` first, since there is nothing to work from |

Never invent a queue from scratch when there are no findings. `$audit-results` is both the
queue and the record: one keyed line per location in `## Current State`, one dated line per
run in `## Log`.

## The three piles are three different jobs

| Pile | What the finding contains | What to do |
|---|---|---|
| **Contradicted** | the stale claim AND the newer evidence | fix in batch, no questions |
| **Unsupported** | the claim, and nothing backing it up | never guess. One batch of questions for the user |
| **Locations not yet converted** | a page that has no `## Current State` / `## Log` | convert in batch, verbatim |

## How much to take on

Ask how large the notes are, or count the markdown files, and scale the ambition:

| Size | Do this |
|---|---|
| **Under ~50 files** | everything in one session. Two or three batches |
| **~50 to 500** | the always-loaded surface first, then one folder per batch, committing between |
| **500+** | the always-loaded surface, plus only the pages with a trail (several entries about one subject over time). Everything else stays as it is, permanently |

## Step 1: build the batch list

Read `$audit-results`. Take the `## Current State` entries that are not marked as fixed, plus
any pile the audit reported but did not enumerate. Group them into batches of roughly 5 to 15
locations, keeping a folder together where you can.

Show the user the batch list and the order before writing anything. Ordering is always:

1. Whatever loads every session.
2. The pages the agent gets wrong most often.
3. Pages with a trail.
4. Nothing else.

## Step 2: the contradicted pile, in batch

For each finding, the newer evidence is already named. So:

- Replace the stale line in `## Current State`.
- Move the superseded line, **verbatim**, to `## Log`.
- Date the new line with the date of the evidence, not today (rule 5).

Work the whole batch, then show one summary: how many lines replaced, in which files, and the
three or four that were least obvious. Do not show a diff per line, and do not ask per line.

## Step 3: convert the locations, in batch

Give each page the two sections. Adapt to the shape the audit found:

```markdown
## Current State
<!-- One entry per subject. Dated. REPLACED on update, never appended to. -->

- **Retainer** (2026-08-01): $3,200/mo, renewed through February 2027
- **Main contact** (2026-05-02): Curtis Ilo

## Log
<!-- Append-only. Never edit or delete an entry. -->

- (2026-04-30) Delivered and paid, $21,000
- (2026-06-15) Added reply drafting, retainer to $3,200/mo
```

One big file gets a `## Current State` block at the top and everything else beneath it, no new
files. Daily notes get one new file of current values and the journal untouched. Notes that are
not markdown do not get converted at all.

**This is sorting, not rewriting.** Every existing line lands in one of the two sections,
verbatim, at most with a date prepended.

**When a bullet has no date and none can be recovered**, do not invent one and do not quietly
leave the entry bare. Take the date from the evidence if the bullet cites any, otherwise write
`(date unknown)` in the date's place.

Two kinds of page to leave alone, and say so rather than converting them:

- **Reference checklists.** Packing lists, hospital-bag lists, standard operating steps. Few
  bolded keys, few dates, and the order is the content. Converting one destroys the thing that
  made it useful.
- **Pages where the freshest status lives inside prose**, under a heading that owns the bullets
  below it. Dissolving that section leaves the newest status outside `## Current State` and the
  oldest inside it, which is the exact failure being removed, rebuilt one level up.

## Step 4: the unsupported pile, one pass of questions

Collect them all and ask once, as a numbered list. Not one at a time, and never silently.
For each, three outcomes:

- **Still true** goes into `## Current State` with the date the user gives, and say plainly that
  the evidence was missing, not just misfiled.
- **No longer true** gets replaced, old line verbatim to `## Log`.
- **Cannot tell** comes out of the always-loaded file entirely.

If the user does not answer, leave every one of them exactly as it is. An unanswered question is
not permission.

### Anything you leave for the owner gets annotated where it lives

**The warning has to be on the line, not only in your report.** Whenever you leave a line
standing because only the owner can resolve it, append the reason in place, keeping the
original text intact ahead of it:

```markdown
- **Sam Iwu**: accepted a full-time offer, starting October 2026. UNVERIFIED (fix run
  2026-09-18): no date and no source anywhere; entities/sam-iwu.md says he is still a
  contractor. Confirm or delete.

- **Ferro retainer renewal** (2026-09-12): renewed at $6,500/mo through year-end. CONFLICT
  (fix run 2026-09-18): the 2026-09-10 call set it to $12,000/mo. Nothing sources this line.
  Ask before quoting either number.
```

This matters most for a **stale line that is newer than the line you just corrected**: an agent
reading that page takes the newer one, so the correction changed nothing unless the newer line
carries the warning. Check for that case explicitly after every batch: for each key you fixed,
look for another key on the same page about the same subject with a later date. Never delete
the line to resolve the conflict, and never pick a value yourself.

## Step 5: write the results back

After each batch, edit `$audit-results`:

- **Replace** each location's `## Current State` line with its new status. One line per
  location, always. Never a second line.
- Record every line you annotated and left standing, so the next run can see what is still
  waiting on the owner.
- **Append** one entry to `## Log`: the date, which batch, how many lines replaced, how many
  locations converted, and how many unsupported claims are still unanswered.

Then commit the batch.

## Step 6: re-audit and compare

When the batches are done, run `/second-brain-audit` again and compare the contradicted count
to the last `## Log` line.

If the count did not move much, say so and say why rather than presenting the conversion as a
result. Restructuring cannot reach a fact nobody ever wrote down, and when the count stays flat
that is usually what happened. The fix then is the write path, not another batch.

If the findings file has been renamed, flag it: `audit.py` skips files whose name starts with
`second-brain-audit`, so a renamed one gets read as evidence on the next scan, and it quotes
stale claims verbatim. Keep that name, or keep the file outside the notes folder.

## Rules that never bend

1. **Lose nothing.** Every line lands somewhere, verbatim. If a line cannot be placed, leave it
   where it is and report it.
2. **Never merge two subjects that look alike.** "Acme (May)" and "Acme Corp renewal" may be two
   real things. Report near-misses at the end of the batch and let the user decide.
3. **Never invent a value**, and never delete a claim to make a pile smaller. Anything left for
   the owner carries its reason on the line itself.
4. **Never edit or delete a `## Log` entry.**
5. **A date is a claim that the value was checked.** A line you only moved keeps its own date.
6. **Never copy the notes folder as a backup.** Git, or an informed no. Nothing else.
7. **Stop when the always-loaded surface has nothing contradicted.** An archive full of old
   pages is history, not rot.
