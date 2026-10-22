---
name: build-dark-factory
description: Builds a dark factory around a PRD: a repo that takes issues in and ships validated code out with nobody at the keyboard, built component by component into the user's actual repo, agnostic to the coding agent underneath. Requires a PRD and does not write one. Use when the user wants a dark factory, an autonomous or self-driving repository, a software factory, an agent that ships its own code, an unattended or overnight coding loop, lights-out coding, autonomous PRs, a repo that maintains itself, or asks how to reach level 4 or 5 of AI coding autonomy.
argument-hint: "[path/to/product.prd.md] [optional: path/to/repo]"
---

# Build a dark factory

**What the user typed:** $ARGUMENTS

> **Work out the PRD path and the repo path from that line yourself, and do not print a
> parse you have not checked.** Do not split on whitespace. Read the line, find the thing
> that looks like a `.md` PRD and the thing that looks like a directory, and confirm both
> back to the user as one sentence before Phase 0. If only one is given, work out from its
> extension which it is and ask for the other. If the PRD path does not exist, say so and
> stop - that is Phase 0a, reached early.

**Build the factory into the user's repo. Do not hand them a design document.** Every
phase below ends with files committed and something demonstrably working.

![The five components of a dark factory](dark-factory-diagram.png)

<!-- The diagram is for the HUMAN reading this repo. Do not describe it back to the user or
     narrate it during a build. -->

**Before anything else, read `references/rationale.md`** - the argument behind every
decision below, plus the *Operating facts* to deliver one line at a time, each at the moment
it becomes actionable.

## Output discipline - read this before you write a single word to the user

**Hard budgets; not style preferences:**

| Moment | Budget |
|---|---|
| Between one question and the next | **Nothing.** Ask. Do not preface, do not recap the last answer. |
| Finishing a phase | **Two lines.** What now exists, and the next question. |
| Explaining a concept | **Only when asked**, and then the short version first. |
| Reporting a file you wrote | **One line.** Its path and what decides its content. |
| A command's output | Never paste it. Say the verdict and the number. |

**Never do these:**

- Announce a plan for a phase before doing it. Do it, then say what exists.
- Restate the user's answer back to them as a paragraph. A picker already showed it.
- Explain WHY the skill works this way. That reasoning is in `references/`, for you, not
  for them.
- Print a table of everything you are about to build.
- Summarise at the end of a phase what you said at the start of it.
- Paste a file you just wrote. They can open it.

Decisions go through the question tool, with the words in the options rather than in a
paragraph above them. A useful test before any message: *would this still be true if I
deleted it?* If the files on disk carry the fact, delete it.

<!-- NO COST OR DURATION ESTIMATES IN THIS FILE, and none in the opening message (see
     rationale.md). Never write a `$` followed by a digit here: it renders as a positional
     argument substitution. _audit_runner.py fails both. -->

## What this is

**A dark factory is the way the user already codes with AI, with the human checkpoints
removed.** Write that process down and build the parts that make it safe to walk away
from; do not impose the example factory's shape. If Phase 0 is borderline, refuse, and
offer to stop after the guidance layer if the user wants a smaller first commitment.

**Name the three harnesses once, out loud, early**: the *agent* harness (Claude Code,
Codex, Pi - the vendor's problem), the *factory* harness (plan, implement, review, gate,
merge - `templates/runner/`, mostly copied), and the *validation* harness (checking the
work as a user would - component 5, yours, most of the work).

## Construction order

Components are numbered in anatomy order. Build in this order, and **state it to the user
before starting**:

| Build | Component |
|---|---|
| 0th | *(the PRD)* |
| 1st | **Guidance layer** (#4) |
| 1.5th | *(the walking skeleton)* - **greenfield only**, AFTER the guidance layer, deliberately tiny |
| 2nd | **Validation harness** (#5) |
| 3rd | **Workflow-driven repo** (#1) |
| 4th | **Deployment** (#3) |
| **Last** | **The trigger** (#2) - goes on only when 1-4 are proven |

## Phase 0. The input, the two ways to refuse, and the greenfield path

**Read `references/prd-and-greenfield.md` before this phase**: the PRD-to-factory mapping
table, the settled-stack rule, and the whole greenfield path.

### 0a. There has to be a PRD

The input is a PRD: problem, users, scope, and above all **non-goals**. Call it a spec, a
brief, an epic; the content is what matters. Read it in full before asking a single
question, then map it with the table in the reference.

- A tech stack in the PRD is **SETTLED, not scope**: do not put it in `MISSION.md`, flag
  in one line that you are treating it as decided, and check **reachability** out loud.
- Anything marked TBD is a decision to be **proposed** by the factory and held at the
  merge, never a wall.
- Say what the PRD does not give you, because the interview exists to produce it: the
  E2E happy path, the protected list, the two gates that must be code, the autonomy
  level, the stop button, how work arrives and where the factory runs.

**Refuse if there is no PRD.** Say why - without a written scope there is no out-of-scope
list, and the factory will build every plausible request - point at `plan-create-prd`,
and stop.

### 0b. The repo has to be observable

Inspect before asking anything: a test command that runs, a way to start the app, existing
CI, whether `gh` is authenticated, whether the repo is public, whether `bash` and `python`
resolve on the machine that will run it, and **whatever AI coding setup already exists**
(`CLAUDE.md`, `AGENTS.md`, `.claude/`, `.cursor/`, skills, commands, MCP config). That
last one is the process to encode. Skim `references/setup.md` now to refuse early.

**Decide brownfield vs greenfield by LOOKING. Do not ask.** Brownfield has source files
that are not scaffolding; greenfield has a PRD, maybe a `.gitignore`, a README, and nothing
that runs. Say which you concluded and why, in one line, so the user can correct it. On
greenfield the refusals below are trivially true and carry no signal: go to 0c.

**Refuse, and say why, when:**

- **There is no way to observe the software working** - nothing to start, invoke, or
  import. This is about software that *cannot be observed*, not software that does not
  exist yet. A library is observable (the `library` driver); read
  `templates/harness/appproc.py` before deciding something is not.
- **The repo has no CI and no test command at all.** Start with a test suite.
- **The user wants the agent to touch auth, payments, or anything with a blast radius
  they cannot absorb.** Those go on the protected list, not into the factory.

If any of these hold, offer the smaller version: guidance layer and harness now, stop before
autonomy.

Never print, cat, echo, grep or quote the contents of an env or secret file — not even masked. Name the file or
the key; never the value. If a value is missing, ask the user to add it themselves.

### 0c. Greenfield: the walking skeleton, and it is SMALL

Greenfield is the common case, not a refusal. Say two things **now**:

1. **The skeleton is the thinnest vertical slice, NOT the MVP.** The test is *"can an E2E
   assert something a user would notice?"* - one behaviour, end to end. Name the slice and
   name what you are leaving out; everything else in the MVP is issues.
2. **The logic must live behind a headless surface the harness can drive** - `http`,
   `cli` or `library`. Simulation separate from rendering, now.

Name the MVP items that are feel, presentation or readability as **permanently human** in
`MISSION.md` and `FACTORY_RULES.md`; the factory owns the simulation layer, not the product.

Order on greenfield: Phase 1, Phase 2, the skeleton sized against R1.1, then Phase 3 onwards.
**The fork (skeleton now / scaffolds only / stop, architecture first) is a question-tool call
presented AFTER Phase 1, recommending the first** - flag in Phase 0 that it is coming. Option
text is in the reference.

## Phase 1. Interview

Read `references/interview.md` and work through it. **Three rounds, not a questionnaire:**
Round 1 is the three questions below, one at a time, before anything else. Round 2 is six
only the user can answer, each about something that has already happened to them - never
ask them to design an artifact; turn the answer into scenarios, defects and rules yourself.
Round 3 is a **single message** of every remaining setting with its default filled in,
asking what to change.

**Propose defaults; do not interrogate.** The PRD has already answered part of this: read
its scope and non-goals back as a proposal and never re-ask what it answers. Reflect each
answer back as a concrete artifact (*"so the merge gate is: X"*) before moving on.

**EVERY QUESTION GOES THROUGH THE QUESTION TOOL** (`AskUserQuestion` in Claude Code, or
the equivalent). Every one, including the open-ended ones; no prose fallback. For an open
question, derive the options from **their PRD and their repo** and cite the source. And:

1. **Exactly one option marked `(Recommended)`, first, with the reason in its one-line
   description.** Where a recommendation would be dishonest, say that instead.
2. **Add an *"Explain this first"* option** wherever the question touches a holdout,
   mutation set, ratchet, independence line or structural gate. Use `interview.md`'s
   one-breath explanation. Do not lecture.

Round 1 - do not let any of these slide:

1. **"Walk me through the single most useful thing someone does with this, from the
   first click to the thing they end up looking at."** That becomes the main path checked
   on every change.
2. **"How do you build a feature with AI today?"** One open question; read `CLAUDE.md`,
   `AGENTS.md`, `.claude/` and `.cursor/` for the rest. The workflows should be recognisably
   their process with the approvals taken out.
3. **"Are you willing to let code reach your users without anyone reading it first?"**
   Then the dial. **Recommend level 2, and say that 3 is the goal.**

### The autonomy dial

| Level | What is automatic | What you still do |
|---|---|---|
| 0 | workflows exist | run them by hand |
| 1 | labelled issue → PR opens | review and merge everything |
| 2 | + validator runs and posts a verdict | merge everything |
| 3 | + validator **auto-merges** when every structural gate is green | write the issues, cut releases |
| 4 | + it triages its own issues, and a scheduled test files its own bugs | write the important issues |
| 5 | + it writes its own issues from the mission | nothing |

**Level 2 is the default. Level 3 is the goal, and it is built for from day one.** 3 is
the first level where code reaches users with nobody having read it, so **the user opts
into it in their own words**, after watching the gate refuse something real at 2 - never
because it was the option they accepted by default. Above 3 is a different question, not
a further step.

## Phase 2. The guidance layer (component 4)

Read `references/guidance-layer.md`. Write three files from the templates:

- `MISSION.md` - what is being built, and what is **deliberately out of scope forever**
- `FACTORY_RULES.md` - how the agent behaves unsupervised, and the protected list
- `CLAUDE.md` / `AGENTS.md` - the conventions any project has (template in
  `templates/CLAUDE.md`; if one already exists, **keep it and pull the factory-only
  rules out of it** rather than writing a new one over the top)

**`MISSION.md` is a compression of the PRD, not a new document.** Draft it from the PRD
directly and show the user the diff in meaning, not just the file. The non-goals become
the out-of-scope list almost verbatim; anything the interview added is marked as such.

**All three files go on the protected list, and a PR that touches them is auto-rejected
before anything else is evaluated.** Enforce this in code, not in a prompt.

Run `scripts/factory_doctor.py --repo <path>` now. It will fail loudly, which is correct:
it is the checklist you are about to work through.

## Phase 3. The validation harness (component 5)

Read `references/validation-harness.md` in full before writing anything. **Its opening
section is the contract the runner expects** - the entrypoint, the markers, the append
rule, the `--quick` subset.

**Start from the scaffold, then delete its assertions.**

```bash
cp -r templates/harness <repo>/harness
```

The scaffold is plumbing only - step ladder, counted markers, `--quick` subset, an
app-process manager - and it is not Python-only or web-only: every command lives in
`harness.config.json`, and the driver is `http`, `cli` or `library`.

**Every assertion in `e2e.py` is a worked example and all of it should be deleted.** The
same goes for `.factory/holdout/run.py` and `harness/mutations/defects.json`. Each carries
a marker line you delete when the content becomes yours, and `factory_doctor` **blocks at
level 2+** until you do. The interview produced the content: **R1.1** the journey,
**R2.5a** the composed scenarios the builder cannot read, **R2.5b** the defects that must
be caught.

The short version:

- **Climb the ladder:** static → unit → integration → **E2E as the real user** → visual
  judging → holdout scenarios → deterministic gate.
- **Draw the independence line after integration.** Everything below it is inside the
  agent's optimization loop. More tests below the line is not the fix.
- **At least two gates must be code the model cannot talk past:** the merge itself, and a
  positive assertion that the app actually started.
- **Empty is not pass.** Assert how many checks *ran*, not just how many failed.
- **The validator never learns how the code was written.** Only what was asked and what
  the code does now.

Deliverable: a `validate` entrypoint a workflow can call, emitting explicit markers, and a
bash merge gate that greps for them.

## Phase 4. The workflow-driven repo (component 1)

Read `references/automation.md`. **Copy the runner; do not write one.**
`templates/runner/factory/` is a working execution layer; its `README.md` is the install
order and states what it runs on (bash - Git Bash on Windows - and `python`).

```bash
cp -r templates/runner/factory <repo>/factory
mkdir -p <repo>/.factory/{locks,holdout,runs}
```

Then three edits:

1. **`factory/config.sh`** - the agent, the models (premium in the planning slot, cheaper
   everywhere else), `FACTORY_VALIDATE_CMD` pointing at the harness from Phase 3, and
   **both spend caps**: `FACTORY_MAX_BUDGET_USD` per agent call and
   `FACTORY_MAX_DAILY_USD` for the day. Every project-specific value lives here; editing
   another script to change a path is a bug in `config.sh`.
2. **`factory/guard.py`** - the protected list. Seed it; do not just accept what the
   interview returned.
3. **`factory/prompts/*.md`** - **rewrite these as the user's own process.** This is where
   R1.2 lands. If they plan with one skill and implement with another, those are two
   nodes. If a rules file or an MCP server is loaded at a step today, load it at that step
   here.

**Verify the agent's flags against the installed CLI** with the loop in `automation.md`
before the first unattended run: a flag the CLI does not know falls through into the prompt.

If the user already runs a workflow engine (Archon, a YAML DAG, GitHub Actions, an Agent
SDK program), the runner is still the reference for *what the nodes must do* - the
fresh-context boundary, the tool allowlists, the holdout deny, the commit step, the gate.
Port those properties; do not port the bash.

## Phase 5. Deployment (component 3)

Read `references/deployment.md`. The trap: **GitHub does not trigger workflows on commits
made with the default `GITHUB_TOKEN`.** The agent commits, the deploy never fires, nothing
errors. The loop has to end at real users.

## Phase 6. The trigger (component 2)

Only now. Read `references/setup.md` in full and the automation reference's dispatcher
section.

**Say out loud: nothing pushes.** Filing an issue does not trigger a run. A scheduler
wakes on a timer, reads the state, and dispatches at most one thing; an issue filed at
09:01 waits for the next tick.

**Build the trigger's configuration now; install it at Phase 7 step 4.** The dial is
enforced in `orchestrator.sh` via `FACTORY_AUTONOMY`, `install-trigger.sh` refuses below
dial 1, and the dial does not leave 0 until Phase 7 has proven a lap by hand. Arm it with
the installer rather than by hand:

```bash
bash factory/install-trigger.sh --status     # what is armed right now
bash factory/install-trigger.sh --install    # cron, systemd timer, or Task Scheduler
bash factory/install-trigger.sh --remove
```

Then run `factory_doctor` once more; it now checks whether a scheduler is actually armed.
**The dispatcher is the dumbest, most deterministic thing in the system** - bash, a fixed
priority order, state in GitHub labels; never a model deciding what to run. The order is
load-bearing: **1.** fix a PR that needs fixing, **2.** validate a PR waiting for review,
**3.** implement the highest-priority accepted issue, **4.** triage untriaged issues.
Finish in-flight work before starting new work.

## Phase 7. Prove it, then earn level 3

The build is finished at **level 2 with the path to 3 written down**; 3 is raised only when
the user says so. These steps are the evidence that earns it:

1. Run the walking skeleton by hand: one real issue, all the way to a PR you merge
   yourself. Do not proceed on a factory that has never completed a lap.
2. `python scripts/factory_doctor.py --repo <path> --audit` until it is clean. It refuses
   level 3 while there is no holdout.
3. **`python scripts/_test_runner.py --repo <path>`** and
   **`python scripts/_audit_runner.py --repo <path>`.** The doctor audits the user's repo;
   these audit the machinery underneath, and a factory that fails them fails *silently*.
   Re-run both after any hand-edit under `factory/` and before re-arming a factory that
   has been idle.
4. Raise the dial to 1, then 2, watching one full cycle at each, and install the trigger
   at 1. **Stop at 2.** Raise to 3 only when the user states it in their own words, after
   the gate has refused something real; record the decision and what convinced them in
   `.factory/decisions.md`.
5. Write `FACTORY.md` from the template - what was built, which level it runs at, and
   what has to be true before the next notch. **Link the PRD it was built from.**

## Resources

- **`dark-factory-diagram.png`**: the system on one page. For the human, not the agent.
- `references/rationale.md`: the argument behind every decision, and the *Operating facts*.
- `references/prd-and-greenfield.md`: PRD mapping table, settled-stack rule, observability refusal, the walking-skeleton path and the fork's option text.
- `references/interview.md`: the three rounds, what each question is for, the one-breath explanations.
- `references/guidance-layer.md`: the three-file split, the placement test, protected files, the out-of-scope list.
- `references/validation-harness.md`: the runner's contract, the ladder, the independence line, holdout design, structural vs prompted gates.
- `references/automation.md`: headless contracts for eight agents and the flag-verification loop, orchestrator options, dispatcher rules.
- `references/deployment.md`: deploy strategies, the `GITHUB_TOKEN` trap, GitHub scheduling gotchas.
- `references/setup.md`: prerequisites (bash, `python`, `gh`), the platform tax, scheduling, the stop button.
- `templates/`: `MISSION.md`, `FACTORY_RULES.md`, `FACTORY.md`, `CLAUDE.md`. Copy and fill; never ship a template's placeholder text.
- **`templates/runner/`**: the working execution layer, copied in Phase 4. Its comments record real incidents; do not tidy them away.
- **`templates/harness/`**: the validation harness's *plumbing*, copied in Phase 3.
- `scripts/factory_doctor.py`: deterministic audit of a factory repo - protected files, holdout leaks, gate-is-code, empty-is-not-pass, ignored secrets, autonomy level. Never read its source into context; only its output.
- `scripts/_test_factory_doctor.py`: the doctor's own tests. Run after changing the doctor.
- **`scripts/_test_runner.py`**: the runner's behaviour suite against the real shell scripts with a stubbed agent. `--repo <path>` tests a factory somebody BUILT; `--mutate` restores each historical defect and requires the suite to go red. Skips, with a message, where `bash` or `git` is missing.
- **`scripts/_audit_runner.py`**: the structural invariants no behaviour test can express - an unexported knob, an unsubstituted placeholder, a state nothing dispatches on, an unguarded command before an escalate. `--repo` works here too.
