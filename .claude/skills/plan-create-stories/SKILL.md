---
name: plan-create-stories
description: Decomposes a finished PRD into a flat backlog of small, engineer-ready tickets with acceptance criteria in Jira, GitHub Issues, or a local file. Use for a simple PRD with no architecture doc yet; for an epic plus architecture, use piv-slice-epic instead.
argument-hint: "<prd-path> --platform <jira|github|local> [--arch <architecture-path>] [--project KEY] [--epic KEY] [--milestone NAME]"
---

# Create Stories: PRD → Ticket Backlog

Turn a finished PRD into a backlog of small, well-formed tickets with explicit acceptance criteria. Reading,
decomposing, and writing criteria are the same for every platform — `--platform` only decides where the tickets
land.

**This skill vs `piv-slice-epic`:** use this for a simple PRD with no architecture session yet, when you want a
**flat, human-navigable backlog** (≤ ~1 day per ticket). Use `piv-slice-epic` for an epic *plus* its architecture
decisions, cut into **AI-sized PIV tickets with a dependency graph** — if you ran `plan-architecture`, that is
usually the right tool.

## Arguments

Parse them from `$ARGUMENTS`:

| Argument | Required | Meaning |
|----------|----------|---------|
| `<prd-path>` | yes | The PRD from `plan-create-prd` — a file path, or a tracker URL/key to fetch |
| `--platform` | yes | `jira`, `github`, or `local` (a markdown file under `docs/tickets/` — solo work, no tracker) |
| `--arch` | no | Architecture doc from `plan-architecture`; supplies phase grouping. An `## Architecture` section inside the PRD counts too |
| `--project` | jira: yes | Jira project key (e.g. `HELP`) |
| `--epic` | jira: optional | Epic key to parent the tickets under (e.g. `HELP-1`) |
| `--milestone` | github: optional | Milestone to attach the issues to |

If `--platform` is missing, or `--project` is missing for Jira, **stop and ask** — do not guess. Another tracker
(Linear, GitLab, Notion…): same decomposition, same confirmation, then create through that tracker's CLI/MCP
with the Jira field mapping.

## Workflow

### 1. Read and decompose the PRD

Read `<prd-path>` in full. A PRD from `plan-create-prd` is **intent, not a work breakdown** — it has no phases,
story list, or engineering tasks. Build the backlog from the sections it does have:

- **MVP** → the backbone. Each capability in the thinnest end-to-end line becomes one or more tickets; split any
  that hides more than ~a day of work.
- **Target User & JTBD** → the user-story framing of each ticket (who, when, so that).
- **Success Metrics** → acceptance criteria, plus any instrumentation/measurement tickets they imply.
- **Non-goals** → the boundary. Nothing here gets a ticket; list them in the report so nobody adds them later.
- **Problem Statement / Thesis / Open Questions** → context for descriptions. An open question that blocks a
  ticket goes into that ticket as an explicit item, never as a guess.

**Grouping:** with an architecture doc (`--arch`, or an `## Architecture` section), group tickets into phases by
its missing pieces and components, and add a ticket per spike it flagged. Without one the backlog is **flat** —
don't invent phases.

For every ticket, draft:
- **Title** — imperative, specific (`Add token refresh endpoint`, not `Auth`).
- **Description** — what and why, linked back to the PRD section it serves.
- **Acceptance criteria** — a checklist a reviewer can verify.
- **Group label** — the phase/component, when grouping applies.

Keep tickets small. A ticket that can't be described in one screen is two tickets. If an MVP item is too vague to
decompose, stop and flag it — that's a PRD gap, not a ticket-writing problem.

### 2. Confirm before creating anything

Print the proposed ticket list (titles, grouping, acceptance criteria), the non-goals you are excluding, and the
target platform/project/epic. Wait for a yes. **Never create tickets without this confirmation** — creating real
tickets is not reversible in one click.

### 3. Create the tickets — branch on `--platform`

**`jira`:** with your Jira tool (e.g. the Atlassian MCP), create each ticket in `--project`, under `--epic` when
given. Map group → label (or the epic); acceptance criteria → description. Capture each created issue key.

**`github`:** `gh issue create --title "..." --body "..." [--label <group>] [--milestone "..."]`; acceptance
criteria as a markdown checklist in the body; create a missing label with `gh label create`. Capture each issue
number/URL. (GitLab: the same motion with `glab issue create`.)

**`local`:** write `docs/tickets/<prd-slug>.md` (slug from the PRD filename), one `###` per ticket with
description, acceptance criteria, and group. Ask before overwriting an existing file.

If a create fails midway, stop, report what was created so far, and don't retry blindly — duplicates are worse
than a gap.

### 4. Report

- A table: ticket title → group → created key/number/URL (or the local file path).
- The PRD (and architecture doc) the backlog came from, and the non-goals excluded.
- Next step: each ticket enters its own PIV loop — `piv-plan-implementation` takes a ticket key/URL (or one
  ticket's section of the local file).

## Quality Checks

Confirm each before reporting; don't tick what you didn't check:

- [ ] Every ticket traces back to a PRD section (MVP item, metric, or JTBD) — none to a non-goal
- [ ] Every ticket has verifiable acceptance criteria
- [ ] Tickets are small (≤ ~1 day of work)
- [ ] The step-2 confirmation happened, and every create succeeded (or the failures are in the report)
- [ ] Grouping, where it exists, is kept as labels/epic so the backlog stays navigable; a flat backlog is flat on purpose

## Notes

- Greenfield vs brownfield changes the PRD's *scope* (MVP vs next epic), not this skill — it runs the same
  either way.
