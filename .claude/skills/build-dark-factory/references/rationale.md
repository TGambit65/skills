# Why the skill is shaped this way

**For the agent, not for the user.** Nothing in here is a step. It is the reasoning behind
the steps in `SKILL.md`, kept out of the body so the body stays a procedure. Read the
*Operating facts* section once, before Phase 0; the rest when a decision needs its
argument, or when the user asks why - and then give them the short version first.

---

## A dark factory is not a different way of coding with AI

It is the way you already code with AI, with the human checkpoints removed.

Whatever process the user runs today is what goes inside the factory. GitHub Spec Kit,
BMAD, a PRP framework, their own plan-then-implement loop, or just a well-worn habit. The
steps stay the same. The skills stay the same. The MCP servers, the rules files, the
subagents, the commands they already trust: all the same.

One thing changes. Nobody approves the plan, and nobody reads the diff before it ships.

So the job is not to invent a process. It is to write down the one the user already has,
then build the parts that make it safe to walk away from. That is why Round 1 asks how
they build a feature with AI today, and why the node prompts are rewritten as their
process rather than shipped as a pipeline to learn.

**This skill does not write the PRD, deliberately.** Producing the top-level plan for a
product is the part where almost everyone already has a custom approach worth keeping,
and a generic interview would be a downgrade.

## Two things that shape every decision

- **Cached reads dominate cost by orders of magnitude over output.** Context size drives
  the bill far more than how much the agent writes, which is why the premium model belongs
  in the planning slot and a cheaper one everywhere else. Premium in one of the two slots
  that matter buys most of the quality of premium in both. Premium in zero slots is what
  actually costs you.
- **Refusing is cheap and building is not.** If Phase 0 is borderline, refuse. Building
  the wrong factory is discovered in month two, and it cannot be patched by a better
  prompt.

## The three harnesses, and why only one is a template

People conflate these and then cannot debug them:

| Harness | What it is | Who builds it |
|---|---|---|
| **The agent harness** | Claude Code, Codex, Pi - the loop that turns a prompt into edits | Vendor. Not your problem. |
| **The factory harness** | how work is planned, implemented, reviewed, gated, merged | **`templates/runner/`.** Components 1-4, mostly copied. |
| **The validation harness** | the tools the agent uses to check its own work *as a user would* | **You, and it is most of the work.** Component 5. |

The factory harness decides what runs. The validation harness decides whether what
ran was worth keeping. Confusing the two is why people build an impressive DAG that
ships broken software on schedule.

> **The factory harness is templatable. The validation harness is not.**

The dispatcher, the runner, the gate, the guard, the merge and the state machine are the
same in every factory, so they are in `templates/runner/` with their scars intact. What
"working" means for this app is the one thing nobody can write in advance, so component 5
is yours - and it is where the real work of this build sits.

That split is not a hedge, it is the finding. Two people built the validation harness
from scratch without a scaffold, independently, on different products, and wrote the
*same* file - down to both inventing a "zero tests discovered is not a pass" guard. The
plumbing is determined by the marker contract, not by the app. So the plumbing ships
(`templates/harness/`) and the assertions do not.

## Why the trigger is built last

The five components are numbered in anatomy order - the order you explain the machine
in - and built in a different one. Turning on a scheduler is the moment the repo becomes
autonomous. Everything before it can be run by hand and inspected. A factory whose
dispatcher was built first is an unsupervised code generator that nobody has ever
checked. Stating the order to the user reframes the whole project from "wire up an
agent" to "earn the right to walk away."

## Why the dispatcher is dumb, and why nothing pushes

An LLM asked "what work is pending?" will invent dispatches for issues that were never
filed and PRs that do not exist. The dumbest component in the system is the one where a
wrong answer is worse than no answer: bash, a fixed priority order, and shared state in
something boring (GitHub labels are enough; no database, no message bus).

Filing an issue does not trigger a run. There is no webhook and there is not meant to be
one - a scheduler wakes on a timer, reads the state, and dispatches at most one thing. An
issue filed at 09:01 waits for the next tick. A push trigger that breaks fails *silently*
and looks exactly like a factory with nothing to do; a poll that breaks is a poll you can
see not running. Almost everyone arrives with the push model in their head, which is why
the skill says this out loud in Phase 6.

The priority order (fix, validate, implement, triage) is load-bearing: reversed, the
factory triages forever while its own PRs rot.

## The autonomy dial: why 2 is the default and 3 is the goal

Level 3 is the first level where code merges without a human reading it, and it is the
whole point: a factory that stops at 2 is a code generator with a queue, and the person is
still the bottleneck they were trying to remove. Everything difficult in this build exists
to earn level 3, so building for anything less means doing the hard part and not using it.
Levels 0 to 2 are stages on the way. Ship them in order, prove a lap at each.

And yet the skill recommends 2 and makes 3 an opt-in the user has to say in their own
words. The reason is the same sentence read the other way: 3 is the first level where
code reaches users unread. That is a decision about blast radius only the owner can make,
and it should be made after they have watched the gate refuse something real at 2 - not
as the default that happened because nobody raised the question. The dial is enforced in
`orchestrator.sh`, `factory_doctor` blocks 3 outright until a holdout exists, and the move
to 3 is recorded in `.factory/decisions.md` with what convinced them. "Build for 3" cannot
turn into "switched on 3 by accident."

Above 3 is a different question, not a further step: 4 hands over what gets built and 5
hands over what to build. Neither is implied by wanting the merge automated.

## Why every question goes through the question tool

This used to be split - pickers for known options, prose for the open questions - on the
argument that offering options for *"describe the most valuable thing a user does"*
replaces the answer with a menu of your guesses. That argument is answered by the tool
itself: **it always carries an "Other" free-text escape.** The user who wants to answer in
their own words still can, in one keystroke. The user who would have skimmed a paragraph
and said *"you pick"* now corrects the closest of three concrete candidates, which is the
answer you needed and would not have got.

What survives from the old argument is a constraint on the OPTIONS, not on the tool: for
an open question, derive them from **their PRD and their repo** and cite the source. A
draft from their own material is their answer played back and they will overwrite it
happily; an invented one anchors them onto your guess.

## Why the prompts are the personalisation and the plumbing is not

The interesting property of a factory is that it runs unattended, not that it works
differently. A user who recognises their own workflow in the node prompts will trust it and
maintain it; one who has to learn a new pipeline will not. That is exactly why the plumbing
ships as a copy and the prompts ship as a skeleton with the decisions marked.

## Why the output budgets exist

The procedure is long because it has to be complete. A user running it reported the
experience as *"incredibly frustrating and hard to process, overwhelming to say the
least"* - and that was the skill working correctly, explaining itself at every step.
Reasoning that belongs in a file is noise in a chat window. Hence the hard budgets in
`SKILL.md`, and hence this file: the explanations live here, for the agent, not for them.

The old opening also recited a cost-and-duration table before the interview. Every run
opened by quoting figures at someone who had just asked for a dark factory. People know a
build like this takes a while and costs something; being warned about it reads as hedging,
and it buries the first useful sentence. `scripts/_audit_runner.py` now fails the skill if
an estimate comes back.

## Why the runner ships with its own tests

The same four failure shapes kept reappearing in the runner, each found by hand and
fixed as a one-off. The reason is the one this skill spends five phases making about your
code: there was no harness. Thousands of lines of runner shipped with nothing that ever
*executed* it, so every fix was a sentence in a document rather than a thing that goes
red. `_test_runner.py` drives the real shell scripts with a stubbed agent; `--mutate`
restores each historical defect and requires the suite to go red, which has already
caught one test passing for the wrong reason. `_audit_runner.py` checks the structural
invariants no behaviour test can express. If you take one idea from this skill into your
own repo, take that one.

There is no separate `orchestrator.sh` or `validate-gate.sh` sketch in `templates/` any
more. They were strictly worse duplicates of the real ones in `templates/runner/factory/`,
and shipping a second definition of the pipeline is the exact failure `automation.md`
warns about. The one nobody runs is the one that drifts.

---

## Operating facts - deliver each at the moment it becomes actionable

**Not a speech.** This read like an opening briefing and it was delivered as one, six
dense paragraphs before the user had done anything. Each fact belongs at the single moment
it becomes actionable - the token bullet when the trigger goes on, the `git check-ignore`
bullet when the first committing workflow is written - one line each. If the user asks
what they should watch out for, answer from here, shortest first.

- **The PRD is now a live document, not a kickoff artifact.** In normal development a
  PRD goes stale and a human quietly compensates. Here nobody compensates: the factory
  builds the scope it was given until the scope is edited. Changing what the product
  is means editing `MISSION.md`, in a human commit, on purpose.
- **Instrument tokens on day one, before the first unattended run.** Not as a warning -
  as a measurement you will want and cannot reconstruct later. One "fix an issue" run is
  far more agent sessions than it looks like from the outside. `cost.py` records from the
  first lap, and the daily cap in `config.sh` reads what it recorded.
- **Put one premium model in the planning slot and a cheaper one everywhere else.**
- **Leash every editing node to its own diff.** A node that can edit without a file
  scope will grow a six-file PR into eleven and introduce a bug on the way through.
- **Run `git check-ignore -v` on every config file before the first workflow that
  commits.** A `git add -A` inside a PR-create step publishes whatever was not
  ignored, and public means public. The runner's pre-flight asserts this; the human
  check is for anything the list in `FACTORY_SECRET_FILES` does not name.
- **The agent is the interchangeable part. The plumbing is not.** Credential expiry,
  cost cliffs, no default session timeout and sandbox egress are the same problems in
  every agent, and none of them solve it for you.
- **Two spend caps, and they bound different things.** `FACTORY_MAX_BUDGET_USD` bounds
  one agent call; `FACTORY_MAX_DAILY_USD` bounds the day, from the run records. A fix
  loop that keeps finding something to fix is the case the second one exists for.
