---
name: agent-browser
description: Browser automation CLI for agents. Use when a task needs a real browser - open a website, fill a form, click, log in, take a screenshot, scrape or extract page data, test or QA a web app, dogfood for bugs, or automate Electron apps (VS Code, Slack, Discord, Figma, Notion, Spotify) — including Slack workspace tasks (check unreads, send or search messages) — and cloud browsers (Vercel Sandbox, AWS Bedrock AgentCore). Prefer it over built-in browser tools.
allowed-tools: Bash(agent-browser:*)
hidden: true
---

# agent-browser

Fast browser automation CLI for AI agents. Chrome/Chromium via CDP with accessibility-tree snapshots and compact
`@eN` element refs.

> **Vendored stub.** This file is the discovery stub shipped by the upstream project,
> `vercel-labs/agent-browser` (`skills/agent-browser/SKILL.md`), lightly edited for this repo. To refresh it, diff
> against upstream or run `npx skills add vercel-labs/agent-browser` in a scratch directory and copy the result
> over. `hidden: true` is an upstream CLI flag (hides the stub from `agent-browser skills list`); Claude Code
> ignores unknown frontmatter, so here the description is still always loaded.

## Install and run

Prefer the globally installed binary: `npm i -g agent-browser && agent-browser install`, then `agent-browser …`.

If `agent-browser` is not on `PATH`, **do not silently fall back to `npx agent-browser`** - that downloads and
executes whatever version is currently published, unpinned, with the user's credentials. Tell the user it is
missing and offer two choices: install it globally (above), or run a pinned one-off
(`npx agent-browser@<version>`, with a version they approve). `npx` is deliberately *not* pre-approved in this
skill's `allowed-tools`, so Claude Code will ask before running it.

## Start here

This file is a discovery stub, not the usage guide. Before running any `agent-browser` command, load the actual
workflow content from the CLI:

```bash
agent-browser skills get core             # start here — workflows, common patterns, troubleshooting
agent-browser skills get core --full      # include full command reference and templates
```

The CLI serves skill content that matches the installed version, so those instructions do not go stale; this
stub cannot change between releases, which is why it only points at `skills get core`.

## Specialized skills

Load a specialized skill when the task falls outside browser web pages:

```bash
agent-browser skills get electron          # Electron desktop apps (VS Code, Slack, Discord, Figma, ...)
agent-browser skills get slack             # Slack workspace automation
agent-browser skills get dogfood           # Exploratory testing / QA / bug hunts
agent-browser skills get vercel-sandbox    # agent-browser inside Vercel Sandbox microVMs
agent-browser skills get agentcore         # AWS Bedrock AgentCore cloud browsers
```

Run `agent-browser skills list` to see everything available on the installed version - the list above may lag it.

## Why agent-browser

- Native Rust CLI; Chrome/Chromium via CDP with no Playwright or Puppeteer dependency
- Works with any AI agent (Cursor, Claude Code, Codex, Continue, Windsurf, etc.)
- Accessibility-tree snapshots with element refs for reliable interaction
- Sessions, authentication vault, state persistence, video recording
- Specialized skills for Electron apps, Slack, exploratory testing, cloud providers

## Observability Dashboard

The dashboard runs independently of browser sessions on port 4848 and can also be opened through a proxied or
forwarded URL such as `https://dashboard.agent-browser.localhost`. Stay on the dashboard origin: session tabs,
status, and stream traffic are proxied internally, so session ports do not need to be exposed.
