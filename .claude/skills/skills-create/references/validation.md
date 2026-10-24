# Validation Gates

Run these after creating or refactoring a skill. Fix failures before declaring done. Each gate says who can run
it: **agent** (do it yourself, from the session) or **user** (needs a human at the prompt — ask, don't assert).

## Gate 1 — Structure (agent)
- `SKILL.md` exists with valid YAML frontmatter delimited by `---`.
- Frontmatter has `name` (matches the directory, lowercase-hyphen, ≤64) and `description` (≤1024, non-empty).
- Every `arguments:` entry is used as `$name` in the body.
- Every file referenced in the body actually exists (no dead pointers), and no path hardcodes
  `.claude/skills/<some-skill>/...` (use relative paths or `${CLAUDE_SKILL_DIR}`).
```bash
ls -R .claude/skills/<name>
grep -nE '`(references|templates|scripts|assets)/' .claude/skills/<name>/SKILL.md
claude plugin validate .                # only if the skill ships in a plugin: run it on the plugin root
                                        # (where .claude-plugin/plugin.json lives), not on .claude/skills
python3 tools/check_contracts.py        # in the skills repo that ships this skill: frontmatter, arguments,
                                        # bundled-file refs across every skill
```

## Gate 2 — Description quality (agent)
- Third person; not "Use this when you…".
- States WHAT it does AND WHEN to use it, key use case first.
- Contains literal trigger phrases a user would actually say, plus the `/name` invocation.

## Gate 3 — Body style & size (agent)
- Imperative / infinitive voice throughout; no second person ("you should").
- The body is the decision spine + pointers, not a data dump.
- Under 500 lines; investigate anything over ~2,000 words for content that belongs in `references/`.

## Gate 4 — Progressive disclosure (agent)
- Bulky / occasionally-needed / output-shaped detail lives in `references/` or `templates/` (or is cited by
  path/URL, or gathered at runtime) — not inlined.
- No content duplicated between body and resources.
- Always-needed output formats have a **mandatory-read** pointer; sometimes-needed detail has a lazy pointer.
- References are one level deep and all linked from a Resources section.

## Gate 5 — Behavior preservation (refactors only — non-negotiable) (agent)
- The trimmed skill + resources drives the SAME process and SAME output as the original.
- At every point the original inlined content, the body now reaches the right pointer at the right time.
- Nothing dropped, nothing duplicated. When uncertain, keep content in the body.

## Gate 6 — Independent review (agent)
If the project has a reviewer subagent (`.claude/agents/code-reviewer.md`), hand it the new skill for a fresh-eyes
check of description quality, organization, and progressive disclosure; otherwise do that pass yourself,
re-reading the skill cold against Gates 2–4. Apply high-confidence findings; ignore noise.

## Gate 7 — Trigger test, then exercise for real
What the agent can do from inside the session:
- **Loaded at all (agent):** Claude Code watches `.claude/skills/` and `~/.claude/skills/` for changes, so a new or
  edited skill is live without a restart (a brand-new top-level skills directory needs `/reload-skills`). Ask
  "What skills are available?" and confirm the new skill is listed with its description. If the frontmatter failed
  to parse the skill loads with an empty description and will never auto-trigger — Gate 1's `claude plugin
  validate` catches this.
- **Trigger-phrase match (agent):** for each trigger phrase from Step 1, check it appears (or is clearly
  paraphrased) in the `description`. The listing is the only thing Claude matches against.

What needs the user at the prompt — ask them to do it and report back; do not claim it passed:
- **User invocation (user):** type `/<name>` and confirm it appears in the menu and runs.
- **Agent invocation (user):** in a fresh session, describe a task in the skill's domain using one of the trigger
  phrases and confirm the skill auto-loads. If it doesn't, strengthen the `description` triggers and retry.
  (`claude --debug` shows what was matched; for a plugin skill, a `tool_used: Skill` eval case with
  `claude plugin eval` measures this across many prompts.)
- **Exercise it end-to-end on real work** — don't stop at "it loaded." A real run surfaces bugs a load-check never
  will. Fold what you learn back in.

## Done
All agent gates pass and the user-run checks have been requested (or done, if the user is driving). For a
refactor, **Gate 5 is non-negotiable** — a refactor that changes output is a regression.
