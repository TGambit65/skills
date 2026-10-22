# Adversarial review of this skills repo — October 2026

Baseline: upstream `coleam00/skills` at commit `847be08` (2026-10-07). Every finding below was made against
that commit; every fix is on top of it. Review cycle 2 of 7 completed; the second cycle was clean of
Critical/High defects in the revised files, so the loop stopped there.

## A. Objective, scope, and verification limits

**Objective.** Fix every defect found in a first-pass review of the 36 skills, 6 hooks and bundled scripts,
then hunt for more, with four goals: correctness, safety, no drift between skills, and lower token cost
without losing any behavioural instruction.

**Scope.** All 36 `SKILL.md` files and their `references/`, `templates/` and `scripts/`; `hooks/`; the
plugin manifests; `README.md`. Policy set by the repo owner: keep all 36 skill names, no merges or
deletions.

**Method.** Ten independent reviewers, one slice each, ran five passes per skill (coverage; correctness and
consistency with neighbours; security/safety; unsupported claims and pre-filled results; edge cases and
portability) and produced an A–G report plus a numbered inventory of every behavioural instruction in the
original. Their proposed files were applied centrally and verified. Cycle 2 used fresh reviewers who had
not seen cycle 1's reasoning: two instruction-loss auditors (original vs revised, ~946 instructions
traced), one cross-skill consistency reviewer, and one duplication cutter whose edits were accepted only
with a mechanical 485/485 instruction-to-line mapping.

**What was executed (commands and exit codes are in the commit messages and this file):**
`tools/check_contracts.py` (35 failures → 0); all five bundled test suites; the new 400-case hooks corpus;
Python 3.8 syntax check on all 32 scripts; a 39-command manual check of the secrets hook; the scripts
`audit.py`, `map_layer.py`, `run_ablation.py --dry-run`, `factory_doctor.py` against synthetic fixtures.

**What was NOT verified, and what would close the gap:**
- No skill was run inside Claude Code. Trigger behaviour, `$ARGUMENTS` substitution, `allowed-tools`
  enforcement, load-time `!`cmd`` semantics and subagent dispatch are verified as text, not observed.
  Closing it: run `piv-run-full-loop` on a small real feature in a real repo and compare against Step
  outputs described in the skill.
- `gh` and `claude` CLIs were not installed in the review environment. Flags are checked against the
  published references; scripts say "verify against your installed version" where it matters.
- Windows and macOS execution of scripts and hooks is by reading only (Linux, Python 3.9 executed).
- Python 3.8 compatibility is by AST check (`feature_version=(3,8)`), not by running 3.8.
- A second-round adversarial bypass hunt of the secrets hook could not be delegated (the brief was
  blocked by a content filter); a reduced 39-command check was run instead (section D).

## B. Requirement checklist

| Requirement | Status |
|---|---|
| Fix all 17 issues catalogued in the first-pass review | Met |
| Hunt additional gaps in every skill | Met — 416 issues reported in cycle 1 (26 Critical, 96 High, 149 Medium, 145 Low across 36 skills + hooks) |
| Correctness issues fixed | Met for everything reproducible here; see E for what is "Plausible" |
| Eliminate drift | Met mechanically: `tools/check_contracts.py` encodes 10 contract classes incl. 15 producer→consumer handoffs; `tools/test_all.py` runs everything |
| Reduce token count of descriptions | Met: 15,272 → 10,792 chars (−29%), ~3,800 → ~2,700 tokens at chars/4 |
| Reduce token count of bodies | Partially met: 44,494 → 40,929 words (−8%). Required safety/contract additions offset cuts in the short skills; the ten longest bodies fell 14–58% |
| No behavioural instruction lost | Met after cycle 2: two independent audits found 2 missing + 16 weakened items in cycle-1 output; all restored or re-decided explicitly (section D) |
| Keep all 36 names, no deletions | Met |
| Scripts zero-dependency, Python 3.8+ | Met (AST-verified) |
| Tests pass or skip on every OS | Met on Linux; Windows-only cases now skip; macOS/Windows not executed |

## C. Issues by severity (the catalogue; fixes in D)

The per-skill reports (one per skill, sections A–G) are not shipped in the repo; this section lists the
cross-cutting and highest-impact items. "Status" is the correction status.

**Critical**
1. `piv-commit` staged everything with no secret or junk screen — Verified correction (screened staging, refuse-list, never `git add -A`).
2. `piv-review-pr` approved via `gh pr review --approve`, which GitHub rejects for the PR's own author (the normal case after `piv-create-pr`) — Plausible correction (fallback to `gh pr comment`; `gh` not executed here).
3. `hooks/pre_tool_use_secrets.py`: any command containing `.env.example` was allowed in full (`cat .env.example; cat .env` passed); the guard failed *open* on its own exceptions — Verified correction (corpus cases, fail closed).
4. `hooks/stop_tests_must_pass.py`: deleting the test file defeated the tamper guard (red → `rm test` → exit 0) — Verified correction.
5. `ablate-ai-layer/run_ablation.py` appended to the user's `.gitignore` on every run while claiming never to touch the working tree — Verified correction.
6. `build-dark-factory` tests crashed everywhere but the author's machine (hardcoded `C:\Users\colem\...`; `write_text(newline=)` needs 3.10) — Verified correction (14/14, 59/59 pass).
7. `piv-run-full-loop` claimed hands-off while `piv-plan-implementation` has a hard stop-and-wait GATE; it also committed without validate or review — Verified correction (text on both sides; not executed in Claude Code).
8. `plan-create-stories` read PRD sections (`Implementation Phases`, `User Stories`) that `plan-create-prd` never writes — Verified correction (checker rule `handoffs`).
9. `skills-create/templates/SKILL.template.md` was invalid YAML (unquoted `: ` in `argument-hint`) — Verified correction.
10. `prime-*` ran `!`git ls-files`` at load, dumping every tracked file into context — Verified correction (bounded listing).

**High (selection)**
- `piv-investigate-issue:49` load-time command with a literal `[relevant-paths]` placeholder (ran, returned nothing, every time).
- Hardcoded `.claude/skills/<name>/` paths in `piv-run-full-loop`, `system-evolution-review`, `worktree-create`, `skills-create` — nonexistent under plugin/global install.
- Pre-filled result lines (`✅ Followed reproduction steps - issue resolved`, `[Show test results - all passing]`) in `piv-implement-issue`, `piv-implement`, `piv-run-full-loop`, `plan-create-stories`.
- `piv-implement` / `piv-implement-issue`: "fix until tests pass" with no rule against weakening tests and no retry cap.
- `worktree-create` branched from HEAD, not the stated base; `worktree-merge` had no dirty-tree check.
- `ablate-ai-layer`: every stripped-arm diff began with `deleted file CLAUDE.md`, naming its arm and defeating blind grading; `map_layer.py` reported skills as costing 0 always-loaded tokens (descriptions are always loaded).
- `drive-screen/autodrive.py` blind-approved `git push`; no persisted approve/refuse log.
- `build-dark-factory`: nodes could `Read` `.env` and post it in a PR body; no aggregate spend cap beside the per-run cap; bare `python` calls die on Debian/macOS.
- Secrets hook bypasses: glob/brace/variable spellings of `.env`, `$(…)` and `xargs`/`eval`/`base64` indirection, env dumps after `&&`, `rm -r -f`, `find -delete`, credential CLIs.
- `ast-grep` documented a non-existent CLI command (`dump_syntax_tree` is an MCP tool name) and wrong rule keys.
- `second-brain-audit/audit.py` detected only money conflicts, not text-valued state conflicts.
- `plan-create-prd` presented an unverifiable statistic ("1,645 audited vibe-coded apps; 170 leaked user data") as fact.

**Medium / Low** — ~290 items: severity-table divergence, four different base-branch idioms, "headless" vs
"unattended" vs "non-interactive" terminology, missing handoff literals, hardcoded `mcp__atlassian__*` tool
names, `docker-compose` v1 syntax, README count 35 vs 36 and a missing `second-brain-fix` row, a
find-and-replace artifact ("apply/piv-commit"), Windows-only test not skipped on POSIX, missing
`TEST_COMMAND` env override, description trigger phrases, stale doc links.

## D. Fixes applied

Nine commits on `adversarial-fix`, themed: tools; hooks; piv loop; planning/priming/issues; worktrees/rules/
meta; autonomy/tool skills; README/manifests; cycle 2. The diff against `847be08` is 84 files, +5,712/−3,180.

**New in the repo**
- `tools/check_contracts.py` — ten contract classes; 15 declared producer→consumer handoffs; 4 required-section
  contracts. Baseline 35 failures → 0.
- `tools/test_all.py` — one entrypoint: contracts + 5 suites + hooks corpus. 7/7 green.
- `hooks/_test_hooks.py` — 400-case regression corpus (374 secrets, 11 stop, 7 dependencies, 8 observers).
  Upstream hooks score 210/400 on it.
- `build-dark-factory/references/{rationale,prd-and-greenfield}.md`, `drive-screen/references/troubleshooting.md`
  — detail moved out of bodies, with pointers (and, for drive-screen, a hard rule to read the traps first).

**Cross-skill conventions now shared verbatim**
- Result vocabulary `PASS / FAIL / NOT RUN`; no ✅/✓ asserting a result anywhere (checker rule `no-prefilled`).
- Retry cap: 3 fix-and-rerun attempts per failing check, fix the code never the check, then `Status: PARTIAL`.
- Severity table identical in `piv-review-changes`, `piv-review-pr`, `piv-fix-review-findings`,
  `piv-investigate-issue`; security findings default to Critical unless *verified* unexploitable.
- "Interactive only — not for non-interactive runs" in `plan-create-prd`, `plan-architecture`, `piv-slice-epic`,
  `plan-create-stories`; a non-interactive contract in `piv-run-full-loop`, `piv-plan-implementation`,
  `piv-implement`, `piv-commit`, `prime-codebase`.
- Agent-written folders: `.claude/plans/`, `.claude/reports/`, `.claude/execution-reports/`, `docs/tickets/`,
  `docs/issues/` commit with the work; `.claude/code-reviews/`, `.claude/system-reviews/`, `.claude/scans/`
  ask-first, default no.
- One base-branch idiom: `git symbolic-ref refs/remotes/origin/HEAD` → `git remote show origin` → `main`, say so.
- One subagent-fallback rule: project agent → built-in general-purpose subagent → inline.
- Tracker tools named generically with Jira/Atlassian as the example.
- Secrets: "never print, cat, echo, grep or quote the contents of an env or secret file — not even masked".

**Deliberate design changes (not bug fixes; revert if you disagree)**
- `build-dark-factory` default autonomy level 2 (validator posts a verdict, human merges); level 3 (auto-merge)
  is an explicit opt-in. The author's argument for 3 as the goal is kept. Also `FACTORY_MAX_DAILY_USD=50`
  beside the per-run `$8` cap, and secret files denied to nodes.
- `hooks/pre_tool_use_secrets.py` fails **closed** on its own exceptions; the other hooks fail open (the stop
  hook fails open loudly, exit 1 with a message).
- `agent-browser`: `Bash(npx agent-browser:*)` removed from `allowed-tools` so Claude Code prompts before
  fetching an unpinned remote package; the global binary is preferred.
- `piv-implement-issue` `allowed-tools`: original runners kept, plus read-only git, branch creation, `gh issue view`.
- `prime-*`: the full `git ls-files` dump is replaced by a bounded listing (count + top level, then scoped).
- `plan-create-prd`: the unverifiable statistic is removed rather than attributed.

**Cycle-2 restorations** (items the audits found missing or weakened in cycle-1 output): fresh-scaffold →
greenfield lane in `rules-create-global`; PRDs that do carry phases/stories in `plan-create-stories`; plan/
execute skill reads mandatory-when-installed in `system-evolution-review`; Slack triggers in `agent-browser`;
preventive traps as `drive-screen` hard rule 10; fail-closed consequence and recovery in `hooks-create`;
RCA-only dirty tree allowed in `piv-implement-issue`; 80% coverage default in the plan template; "continue
with the next feature" in the full loop.

## E. Remaining risks and unknowns

1. **Nothing has run inside Claude Code.** The largest residual risk is a skill that reads correctly but
   triggers or chains differently in a live session. Evidence to close: one real `piv-run-full-loop` run and
   one `piv-investigate-issue` → `piv-implement-issue` → `piv-commit` → `piv-create-pr` → `piv-review-pr` chain.
2. **Deny-list hooks are a speed bump.** Classes a deny-list cannot close, listed in `hooks/README.md`:
   write-a-script-then-run-it, sweeps that never name the file, arbitrary interpreter one-liners, persistent
   shell aliases/functions/fds, network exfiltration, harness-level fail-open when `uv` is missing or the hook
   times out. The wall is `permissions.deny` plus sandboxing; `settings.json.example` ships both.
   Known judgment calls: `cat .git/config` is allowed; `find … -delete` and `env | grep` are blocked.
3. **`gh` / `claude` CLI flags** (`gh pr review` self-approval behaviour, `isDraft`, `--max-budget-usd`,
   `--permission-mode`) are from published references, not executed.
4. **Body token reduction fell short of the 20% target** (−8%). The ten longest bodies fell 14–58%; the
   short PIV-loop skills grew because the fixes added rules (commit hygiene, non-interactive mode, retry caps).
   Further cuts would remove instructions.
5. **Behavioural compliance** with prose rules ("never weaken a test", "refuse to stage secrets") is a
   model property; a hook is the guarantee and the skills now say so.
6. **`hidden: true`** on `agent-browser` is an upstream flag not in current Claude Code docs; harmless if
   ignored.
7. **Daily spend cap** in the dark factory is fail-open for agents that report no cost (logged as `unmeasured`).

## F. Verdict

**READY** for merge as a reviewed candidate, with the explicit caveat that no end-to-end run inside Claude
Code was performed. Cycle 2 found 0 Critical / 0 High defects in the revised files once its restorations
were applied, the contract checker is clean, and 7/7 executable checks pass.

## G. How to re-verify

```bash
python3 tools/test_all.py                 # 7/7 expected
python3 tools/check_contracts.py --tokens # per-skill budget; 0 failures expected
git diff 847be08 --stat                   # the full change set
```

For the always-loaded budget: 36 descriptions, 10,792 chars (~2,700 tokens at chars/4; measure with your
tokenizer for the exact figure).
