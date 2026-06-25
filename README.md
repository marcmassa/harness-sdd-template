# Harness SDD — Agentic Development Framework

An opinionated framework for collaborating with AI agents on software projects of any kind. One canonical manifest drives the native config for any agentic CLI — opencode, gemini-cli, claude-code, or any other. Spec-driven. Traceable. Verifiable.

---

## Index

- [The Problem](#the-problem)
- [Impact](#impact)
- [Quickstart — 3 steps](#quickstart--3-steps)
- [What is Harness Engineering?](#what-is-harness-engineering)
- [Complete SDD Workflow](#complete-sdd-workflow)
- [Template Installation Lifecycle](#template-installation-lifecycle)
- [Template Structure](#template-structure)
- [Slash Commands](#slash-commands-available)
- [How to Customize for Your Stack](#how-to-customize-for-your-stack)
- [FAQ and Troubleshooting](#faq-and-troubleshooting)
- [License & Authority](#license--authority)

---

## The Problem

Without an explicit harness, AI agent interactions follow a recognizable pattern:

```
Human: "Add support for X"
Agent: (writes code without full context)
       (skips steps, assumes non-existent conventions)
       (leaves repo in an indeterminate state)
Human: (reviews, finds errors, asks for changes)
Agent: (iterates without memory of the previous iteration)
       → Frustration, wasted time, inconsistent code
```

The root cause is not the agent's capability — it is the absence of structure. The agent has no declared source of truth, no explicit workflow to follow, and no persistent memory between sessions.

### The Solution

```
Human: "Add support for X"
Agent (spec-author):
  1. Reads feature_list.json → detects feature with sdd:true, status:pending
  2. Creates specs/feature-x/requirements.md (EARS: R1, R2, ...)
  3. Creates specs/feature-x/design.md (files, signatures, alternatives)
  4. Creates specs/feature-x/tasks.md (checklist T1, T2, ... with R<n>)
  5. Sets status: spec_ready and STOPS

⏸ Human: Reads the 3 files in specs/feature-x/ and says "approved"

Agent (implementer):
  6. Executes tasks.md sequentially, marking [x]
  7. Adds tests with R<n> ↔ test traceability
  8. Runs ./check.sh → all green
  9. Sets status: done in feature_list.json
 10. Logs in progress/progress.md

→ Full traceability. Human only reviews once — at spec time, not after 3 code iterations.
```

---

## Impact

| What you get | How the framework enforces it |
|---|---|
| **Human reviews specs, not code** | Spec approval gate blocks implementation until human says yes |
| **0 requirements without a test** | `check.sh` enforces R↔test traceability — fails if any R<n> is untested |
| **Agent cold-start in < 1 min** | `AGENTS.md` + `feature_list.json` + `progress/current.md` give a new agent full project state |
| **No vendor lock-in** | One `agentic.json` manifest renders native config for any agentic CLI |
| **Any stack, any language** | Stack-aware only via `project_detect[]` — the framework itself is technology-agnostic |
| **Customizable agent behavior** | Steering files tune per-role directives; lifecycle hooks automate SDD transitions |
| **Repeatable process** | Every feature, every sprint, every team member follows the same spec→approve→implement→done flow |

---

## Quickstart — 3 steps

### Step 1 — Copy the framework into your repo

```bash
cp -r harness-sdd-template/. /path/to/your/repo/
cd /path/to/your/repo
```

### Step 2 — Bootstrap the CLI adapter

```bash
./.agents/bootstrap.sh detect          # See which CLIs are supported and detect your stack
./.agents/bootstrap.sh claude-code     # Render for claude-code. Others: opencode, gemini-cli
./.agents/bootstrap.sh --all --yes     # Render for all supported CLIs at once
```

### Step 3 — Tell your agent to set up the project

```
"Run /init"
```

The agent reads `.agents/commands/init.md`, walks the SCAFFOLD → IMPLEMENT → REMOVE lifecycle, shapes the manifest to your project's sub-agents, and runs `./check.sh`. You supervise; the agent does the work.

That's it. The agent is now operating under the harness.

> **Manual path:** If you prefer to do Step 3 by hand, see [Template Installation Lifecycle](#template-installation-lifecycle) below.

---

## What is Harness Engineering?

**Harness Engineering** structures a repository so that AI agents can work on it autonomously, traceably, and verifiably — without requiring a human to re-explain context at the start of every session.

| Pillar | Meaning | Implementation |
|---|---|---|
| **1. The Repo IS the System** | All info an agent needs is in the repo, not in the dev's mind | `AGENTS.md`, `feature_list.json`, `specs/`, `progress/`, `docs/` |
| **2. Spec Driven Development** | No code is written until requirements are specified, designed, and approved by a human | `specs/<feature>/{requirements,design,tasks}.md` with R<n> ↔ test traceability |
| **3. Operational Memory on Disk** | Session state, decisions, and backlog live in files, not in the chat | `progress/{current,progress,backlog,decisions,handoff}.md` |
| **4. Executable Verification** | A script (`check.sh`) validates builds, tests, spec integrity, and harness rules | `check.sh` — the gateway for declaring a task as `done` |
| **5. Customizable Agent Behavior** | Steering files customize per-role directives; lifecycle hooks automate SDD transition points | `agentic.json#steering[]` and `#hooks[]`, managed via `bootstrap.sh add-steering` / `add-hook` |

---

## Complete SDD Workflow

Once the framework is installed, the day-to-day workflow follows the SDD state machine:

```
                      ┌──────────────────────────────────────────┐
                      │           feature_list.json              │
                      │  (one feature at a time, sdd:true/false) │
                      └──────────────────────────────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │    pending       │
                               │  (no spec yet)   │
                               └────────┬─────────┘
                                        │ spec-author
                                        │ creates specs/<feature>/{requirements,design,tasks}.md
                                        ▼
                               ┌─────────────────┐
                               │   spec_ready     │
                               │  (⏸ waiting)     │◄──────────────────┐
                               └────────┬─────────┘                   │
                                        │                             │
                               ┌────────▼────────┐                   │
                               │  HUMAN          │── No → fix ───────┘
                               │  APPROVAL       │
                               └────────┬─────────┘
                                        │ Yes
                                        ▼
                               ┌─────────────────┐
                               │  in_progress     │
                               │  (implementing)  │
                               └────────┬─────────┘
                                        │ implementer follows tasks.md
                                        │ reviewer validates R<n>↔test traceability
                                        │ check.sh passes
                                        ▼
                               ┌─────────────────┐
                               │     done         │
                               │  (closed)        │
                               └─────────────────┘
```

---

## Template Installation Lifecycle

When you copy this framework into a project, the sub-agents ship as **scaffolds** — patterns to use as a starting point, never installed by default. The lifecycle has 3 stages:

```
                      ┌──────────────────────────────────────────────────┐
                      │   Copy the framework into your project           │
                      │   (preserves _template_subagents_examples[])     │
                      └────────────────────────┬─────────────────────────┘
                                               │
                                               ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │  STAGE 1 — SCAFFOLD                                                  │
   │  $ ./.agents/bootstrap.sh profile                                   │
   │                                                                     │
    │  Read the entries in _template_*_examples[] to see the                │
    │  patterns the framework provides.                                     │
    │  7 sub-agent scaffolds (4 canonicals + 3 illustrative) +              │
    │  2 steering + 3 hooks. Each carries _lifecycle: "scaffold".          │
   └────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼
   ┌─────────────────────────────────────────────────────────────────────┐
    │  STAGE 2 — IMPLEMENT                                                 │
    │  For each sub-agent / steering file / hook your project needs,       │
    │  copy a scaffold into the corresponding active array:                │
    │  subagents[], steering[], hooks[].                                   │
    │                                                                     │
    │  Quick try:    ./.agents/bootstrap.sh add-agent <name> --yes        │
    │                ./.agents/bootstrap.sh add-steering <name> --yes     │
    │                ./.agents/bootstrap.sh add-hook --event ... --script  │
    │  Customize:    copy + edit .agents/agentic.json by hand             │
   │                 (e.g. implementer -> python-implementer)            │
   │                                                                     │
   │  The renderer auto-scaffolds the SUBAGENT.md from                   │
   │  .agents/subagents/agent-template/ if it is missing.                │
   └────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │  STAGE 3 — REMOVE                                                    │
   │  $ ./.agents/bootstrap.sh remove-examples --yes                     │
   │                                                                     │
    │  Drops all _template_*_examples[] and _template_lifecycle from       │
    │  .agents/agentic.json. Entries already promoted to subagents[],     │
    │  steering[], hooks[] are NOT affected. Re-renders all adapters.     │
    └────────────────────────────────────┬────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  FINAL — project-only manifest                                      │
    │                                                                     │
    │  subagents[] / steering[] / hooks[] = the project's definitions.    │
    │  No _template_* residue, no placeholder entries, no leftover        │
   │  scaffold metadata. Just the project, shaped by the project.        │
   └─────────────────────────────────────────────────────────────────────┘
```

The intent is documented **inside the manifest itself** at `agentic.json#_template_lifecycle` — the lifecycle is part of the project's source of truth, not external documentation that can drift.

The completion gate (`bootstrap.sh init --validate`) catches the common agent mistakes observed during real-world testing:
- Scaffold metadata leaked into `subagents[]` (`_lifecycle`, `_intent`, `category`)
- Description copied verbatim from the scaffold (not customized)
- Scaffolds not dropped (`_template_subagents_examples[]` still present)
- `role_file` pointing to a non-existent file
- Required fields missing (`name`, `mode`, `description`, `role_file`, `permission`)

The agent MUST loop until `--validate` exits 0. Do not declare `/init` done otherwise.

---

## Template Structure

```
harness-sdd-template/
├── AGENTS.md                  # Navigation map for agents (read this first)
├── README.md                  # This file
├── DESIGN.md                  # High-level architecture (fill in for your project)
├── SECURITY.md                # Security policy
├── check.sh                   # Verification gateway (lint, test, spec integrity, ...)
├── feature_list.json          # Source of truth for features (one at a time)
│
├── .agents/                   # Framework internals
│   ├── agentic.json           #   Canonical manifest (source of truth)
│   ├── BOOTSTRAP.md           #   LLM fallback for unknown CLIs
│   ├── bootstrap.sh           #   Renderer dispatcher
│   ├── adapters/              #   CLI adapter templates (opencode, gemini-cli, claude-code, ...)
│   ├── subagents/             #   Sub-agent role files
│   │   ├── agent-template/    #     Scaffold source for new sub-agents
│   │   ├── harness/           #     Orchestrator
│   │   ├── spec-author/
│   │   ├── implementer/
│   │   └── reviewer/
│   ├── skills/                #   Specialized skills (sync'd from the registry)
│   ├── commands/              #   Slash-command bodies (/spec, /implement, ...)
│   └── harness/               #   Operational docs (CONVENTION, ROUTING, ...)
│
├── steering/                  #   Steering files (per-role agent behavior directives)
├── hooks/                     #   Lifecycle hook scripts + run-hooks.sh runner
│
├── specs/                     # Spec Driven Development artifacts
│   ├── README.md              #   How to write a spec
│   └── templates/             #   EARS templates (requirements, design, tasks)
│
├── progress/                  # Operational memory on disk
│   ├── current.md             #   Live session state
│   ├── progress.md            #   Append-only history
│   ├── backlog.md             #   Deferred items
│   ├── decisions.md           #   Architecture Decision Records
│   └── handoff.md             #   Hand-off notes between sessions
│
└── examples/                  # Reference implementations
    └── add-user-api/          #   End-to-end SDD example (stack-agnostic REST API feature)
```

The canonical source of truth is `.agents/agentic.json`. Every CLI-specific config
(`opencode.json`, `GEMINI.md`, `CLAUDE.md`, etc.) is generated from it by
`./.agents/bootstrap.sh <cli>` and is **gitignored** — each developer regenerates
their own after cloning.

---

## Slash Commands Available

| Slash command | Purpose |
|---|---|
| `/init` | Set up the project (one-time scaffold lifecycle). The agent does it. |
| `/status` | Show project state (active feature, specs pending, last progress). |
| `/spec` | Create the spec for the first `pending` feature with `"sdd": true`. |
| `/approve` | Approve a `spec_ready` feature and flip it to `in_progress`. |
| `/implement` | Execute `tasks.md` for the feature in `in_progress`. |
| `/done` | Run the reviewer, verify R↔test traceability, mark `done` if green. |
| `/check` | Shortcut to `./check.sh`. |

---

## How to Customize for Your Stack

### Adapt `check.sh`

The `check.sh` script detects what tools are available on the machine and runs only the relevant checks. Add blocks for your specific tools by following the pattern already in the file — each block is guarded by `command -v <tool>` so it only runs when the tool is installed.

### Adapt the canonical manifest

Edit `.agents/agentic.json` directly:

- Add or remove entries in `subagents[]` (the active set).
- Add `_lifecycle: "scaffold"` entries to `_template_subagents_examples[]` to publish project-specific sub-agent patterns for your team.
- Add or extend `project_detect[]` rules to set stack-aware permission overrides and skills for your languages and tools.

After every change, re-render the CLI adapters:

```bash
./.agents/bootstrap.sh <cli>          # Render for one CLI
./.agents/bootstrap.sh --all --yes    # Render for every adapter (no prompts)
./.agents/bootstrap.sh --check        # Drift check (CI-friendly)
```

### Adapt EARS templates

The templates in `specs/templates/` use generic examples. Replace them with examples relevant to your specific domain and language so that the spec-author agent produces specs that match your codebase style.

### Add a new CLI

Copy `.agents/adapters/_generic/` to `.agents/adapters/<your-cli>/` and write the adapter. The bootstrap mechanism is data-driven; see [`.agents/BOOTSTRAP.md`](.agents/BOOTSTRAP.md) for the LLM fallback when no prebuilt renderer exists.

---

## FAQ and Troubleshooting

**Q: My CLI is not in the list of supported adapters.**
A: Read [`.agents/BOOTSTRAP.md`](.agents/BOOTSTRAP.md) — it explains how to translate the canonical manifest to your CLI's native format by hand, or how to add a prebuilt adapter.

**Q: `bootstrap.sh --check` reports DRIFT.**
A: The canonical manifest and the on-disk adapter have diverged. Re-run `./.agents/bootstrap.sh <cli>` to regenerate.

**Q: `check.sh` says a canonical sub-agent is "orphaned".**
A: The canonical directory exists on disk but is not in `.agents/agentic.json` (neither in `subagents[]` nor in `_template_subagents_examples[]`). Either restore the entry, run `./.agents/bootstrap.sh prune` to clean up, or move the canonical into `_template_subagents_examples[]` if you want to keep it as a scaffold.

**Q: I want to add a sub-agent that's not a scaffold — a permanent part of my project.**
A: Add it directly to `subagents[]` in `.agents/agentic.json`. You don't need to use `add-agent`; that's only for borrowing scaffolds.

**Q: I want to share my project's sub-agents with other teams.**
A: Move them from `subagents[]` to `_template_subagents_examples[]` (with a `_lifecycle: "scaffold"` and an `_intent` hint) and ship the manifest. Other projects can then use `add-agent` to borrow them.

**Q: `add-agent` prompts even when I pass `--yes`. What's happening?**
A: If the scaffold entry is not in `_template_subagents_examples[]` (e.g. you typed a name that doesn't exist), the renderer reports the error and exits 1 — `--yes` only skips the human confirmation, not validation errors.

**Q: I want the agent to do the project setup, not me. How?**
A: Tell the agent *"run /init"* (or invoke the `/init` slash command directly). The agent reads `.agents/commands/init.md` and walks the 3-stage lifecycle (SCAFFOLD → IMPLEMENT → REMOVE) on its own, then runs `./check.sh` and reports. The human supervises; the agent does the work. This is the recommended path — it works the same way across opencode, gemini-cli, claude-code, and any other agentic CLI that supports slash commands.

**Q: The agent ran `/init` but the result is wrong — scaffolds still there, scaffold metadata leaked into `subagents[]`, description copied verbatim. What now?**
A: This is exactly what `bootstrap.sh init --validate` is designed to catch. Run it: it returns 0 (ok) or 1 (with specific errors). The errors tell you exactly what is wrong. If the agent skipped the validation, run it yourself and feed the errors back to the agent.

**Q: What are steering files and how do I use them?**
A: Steering files (in `steering/`) are Markdown files with YAML frontmatter that customize agent behavior globally or per role. Declare them in `agentic.json#steering[]` and manage them with `bootstrap.sh add-steering` / `remove-steering`. The framework ships with 2 scaffold examples.

**Q: What are lifecycle hooks and when do they fire?**
A: Hooks (`hooks/`) are shell scripts that execute automatically at SDD transition points — spec created, approved, implementation start/complete, review, feature done, check pass. The runner is `hooks/run-hooks.sh`. See `docs/sdd.md §7` for the full reference. Managed via `bootstrap.sh add-hook` / `remove-hook`.

**Q: Is this a framework or a template?**
A: Both. You start by copying it (template), but once in place it defines the rules, enforces the lifecycle, and provides the tooling — that's a framework. The distinction that matters: projects work *within* the harness, not just starting from it.

**Q: Does this work only for infrastructure projects?**
A: No. The framework is stack-agnostic. It works for any software project — backend APIs, frontend applications, data pipelines, CLI tools, platform services. Stack-specific tooling (linters, validators) is detected at runtime via `project_detect[]` in the manifest and is always optional.

---

> **Based on:** Real-world implementations in multiple production projects.
