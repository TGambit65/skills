# Phase 0 in full: the PRD as input, and the greenfield path

**Read before Phase 0.** `SKILL.md` carries the decisions; this carries what they are
made from. The PRD mapping table and the greenfield fork are used on every run that has
a PRD, which is every run that gets past 0a.

---

## What a PRD is here, and what to do with the parts it should not contain

**The input to this skill is a PRD**: what is being built and why, at the level a
product manager writes it. Problem, users, scope, and above all **non-goals**. Call it
a spec, a brief, a product doc, an epic; the name does not matter and the content
does.

It deliberately does **not** contain the tech stack, the architecture, the data model,
or the file layout. Those are engineering decisions, they come later, and in a factory
they are usually decided on the first real run or already settled by the existing
codebase. Asking for them here is how a PRD turns into a spec nobody can change.

**When the PRD contains one anyway - and it usually will - treat it as SETTLED, not as
scope, and say that you are doing so.** Someone who is not an engineer writes down the
stack because it is the part they feel confident about; a career-changer's brief will name
the framework, the host and a table sketch before it names a single non-goal. Arguing them
out of it buys nothing and costs the room.

So: take it as a decision already made, do not put it in `MISSION.md` (it is not scope and
the factory must not defend it), and flag it in one line so it is a choice rather than
something you quietly assumed. The one thing to check out loud is **reachability** - a
stack that can only be exercised through a rendered page needs the logic split out behind
something an E2E can call. See the reachability constraint below.

## Mapping the PRD onto the factory

Read the PRD in full before asking a single question. Then map it:

| The PRD gives you | The factory builds from it |
|---|---|
| the problem, and why it is worth solving | the framing at the top of `MISSION.md` |
| who the users are | the person the E2E path is acted out as |
| MVP scope, the capability areas | what triage is allowed to accept |
| **non-goals**, sorted first (R2.1) | **permanent ("not ever") → `MISSION.md` out-of-scope-forever, the most load-bearing list in the whole build. Deferred ("not now") → the backlog, never the out-of-scope list, or the factory refuses that work when its issue comes up** |
| success metrics | what the validation harness is ultimately arguing about |
| open questions, anything marked TBD | a decision to be **proposed**, not a wall. The factory picks a defensible value, records it, and the merge is held for a human. It escalates only for the short list in `FACTORY_RULES.md` §7.2 - read "open" as "I have not decided", never as "you may not propose" |

And be explicit with the user about **what the PRD does not give you**, because these
are exactly what the interview exists to produce:

- the E2E happy path, narrated as observable steps
- the protected list
- the two gates that have to be code rather than prompt
- the target autonomy level
- the stop button
- how work arrives, and where the factory runs

## Why the refusal without a PRD is absolute

Without a written scope, `MISSION.md` has no out-of-scope list, and without that list
every plausible feature request is arguably in scope. The factory will build all of them.
That is the single most common way an autonomous repo goes wrong, and it cannot be
patched later by a better prompt. Point at the `plan-create-prd` skill in this repo and
stop. Coming back in twenty minutes with a real PRD is the fastest path, not a detour.

---

## "Unobservable" means cannot be observed, not does not exist yet

The first refusal in 0b is about software that cannot be observed - nothing to start,
nothing to invoke, and nothing importable either. Component 5 has nothing to stand on.

A greenfield repo trips this and the no-tests refusal by definition, and refusing it
would be refusing the premise rather than a defect. Greenfield goes to the path below.

**A library is not this case.** The harness ships three drivers - `http` (a server),
`cli` (a command), and `library` (no process at all; the E2E imports it and calls it) -
and `APP_STARTED driver=library` means the import succeeded, which is the same claim a
server answering makes. This bullet used to open with the words "a library", and a test
run against a pure Python library nearly hard-refused a repo the scaffold supports out
of the box. Read `templates/harness/appproc.py` before deciding something is
unobservable.

---

## Greenfield: the walking skeleton, and it is SMALL

**This is the common case, not the exception.** Most people want a dark factory at the
start of a project, which is also the best time to build one - the guidance layer is
cheapest to write when nothing contradicts it yet, and the sim/presentation split below is
free before there is code and expensive afterwards.

Greenfield is **not** a refusal. But it does mean component 5 has nothing to stand on
today, and no ordering of the phases fixes that. Something has to exist first.

### The skeleton is the thinnest vertical slice, NOT the MVP

This is where a greenfield build goes wrong, and it goes wrong in the same direction every
time: the agent proposes building the core of the product so the harness has something to
test, the user agrees because it sounds necessary, and now the interesting, risky work has
been done by hand and the factory is left with the leftovers. That inverts the entire
point.

**Build the smallest slice that produces one observable, assertable behaviour end to end.**
For a game: one enemy, one hit, one damage number, persisted across a restart. For a
service: one endpoint that writes one row and reads it back. For a CLI: one command with
one flag that changes one line of output.

The test is not "is this useful" - it is **"can an E2E assert something a user would
notice?"** If yes, stop building and start building the factory. Everything else in the
MVP is issues, and the factory building them is the thing you are here for.

State the size explicitly before starting, and say what you are deliberately leaving out:
*"I am building one horn level, one wave, one damage number and a save file. Not the
reward curve, not the elemental interactions, not wave composition - those are issue
one, two and three."*

### The reachability constraint, decided NOW

**The harness reaches software exactly three ways** - `http` (a server), `cli` (a command),
`library` (imported and called). Read `templates/harness/appproc.py`. A rendered window, a
game loop, a canvas, a native UI is **none of them**.

So on greenfield this stops being an architecture preference and becomes a hard
requirement: **the logic must live behind a headless, scriptable surface that an E2E can
drive.** Simulation separate from rendering. Domain separate from view. If the rules only
exist inside engine nodes and a render loop, there is nothing to assert and the factory
cannot be built at level 3 - not because the skill is limited, but because nothing can
check the work.

Say this before any code is written. It is nearly free now and it is a rewrite later.

### The factory's scope is strictly smaller than the MVP

Some MVP items are not machine-validatable and never will be: *"combat feels good"*,
*"the escalation is visibly and audibly different"*, *"a first-time player understands
it"*. Those are feel, presentation and readability.

Name them out loud, write them into `MISSION.md` and `FACTORY_RULES.md` as **permanently
human**, and be clear that the factory owns the simulation layer rather than the product.
That is still a large and valuable surface - usually most of the actual risk - but
pretending it is the whole MVP is how you end up with a green factory shipping a game
nobody wants to play.

### Then, in this order - and the fork comes AFTER the interview

Say the two things above (the skeleton is a slice; the logic has to be reachable) **now**,
in Phase 0, because both change what the user tells you in the interview. Then:

1. **Phase 1, the interview.** It is unchanged on greenfield.
2. **Phase 2, the guidance layer.** Markdown, needs no code, and every later component
   reads it - including the skeleton, which should be built inside the mission's scope
   rather than alongside it. This is also the natural stopping point a greenfield user
   might want, and putting the skeleton first removes it.
3. **The skeleton**, named and sized against the journey from R1.1.
4. Phase 3 onwards as written.

**The fork below is presented after Phase 1, not here.** Its recommended option requires
you to name the slice and name what you are leaving out, and you cannot do either honestly
before R1.1 has told you what the journey is. Asking in Phase 0 gets a decision made on
information nobody has yet. Flag in Phase 0 that the choice is coming; put it after the
interview.

### The fork, once the interview has given you a journey

Three known answers, so this is a question-tool call like every other,
and **recommend the first**:

1. **Build the thin skeleton now, then the factory on it** *(recommended)* - name the
   slice and name what you are leaving out, so "recommended" cannot be read as "I will
   build your MVP".
2. **Guidance layer and scaffolds only** - `MISSION.md`, `FACTORY_RULES.md`, `CLAUDE.md`,
   plus `runner/` and `harness/` copied in with the contract documented and the assertions
   left empty. The user builds the skeleton; you resume at component 5. A real option, not
   a consolation: the `MISSION.md`/`FACTORY_RULES.md` pair earns its keep in interactive
   work whether or not a cron is ever turned on.
3. **Stop - architecture first** - when the PRD defers the thing the reachability
   constraint depends on, and the user would rather settle it before code exists.
