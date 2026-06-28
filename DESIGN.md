# System Design & Architecture

> **This file is a template.** Every section below is a guideline for
> what to document when you adopt the Harness SDD framework in your project.
> The content you see here describes the framework itself as an example.
> When you start a new project, replace this content with your project's
> actual architecture. Do not leave this file as a copy of the template.
>
> This document serves as the primary "macro" source of truth for all
> developers and AI agents. Agents read it before proposing feature designs.

---

## 1. System Overview

**What to write here:** 2-4 sentences describing what the system does, the
problem it solves, and who uses it. Enough for an agent or new developer to
understand the domain without reading the code.

**Harness SDD (this template) example:**

Harness SDD is a CLI-agnostic framework for running AI agent workflows on
software projects. It solves the context and consistency problem: agents
working without a structured environment hallucinate, lose context between
sessions, and produce inconsistent results. The framework wraps any project
with a canonical manifest (`agentic.json`), a Specification-Driven Development
workflow, and a set of steering, hooks, and sub-agent definitions that give
any AI agent a stable operating context from the first session.

Target users: engineering teams adopting agentic AI workflows who want
repeatability and traceability without modifying the underlying model.

---

## 2. Architectural Principles

**What to write here:** 3-6 principles that constrain every architectural
decision in this project. These are the non-negotiable properties of the system.

**Harness SDD example:**

- **CLI-agnostic**: the canonical manifest (`agentic.json`) is the single
  source of truth. CLI-specific files (`opencode.json`, `GEMINI.md`, `CLAUDE.md`)
  are generated artifacts — never edited by hand.
- **Determinism**: the same manifest + same project root always produces
  identical adapter output. The parity tests in `tests/` enforce this.
- **Traceability**: every feature change goes through `spec → approve → implement → done`.
  No code without a spec; no spec without human approval.
- **Steering System**: agent behavior is directed via steering files in `steering/`
  (global and per-role), declared in `agentic.json#steering[]`. See `AGENTS.md §0.5`.
- **Hooks System**: SDD lifecycle transitions trigger hook scripts in `hooks/`
  via `hooks/run-hooks.sh`. See `docs/sdd.md §7`.
- **Backward compatibility**: schema changes to `agentic.json` must be optional
  with safe defaults. Existing projects must not break on framework updates.

---

## 3. High-Level Architecture

**What to write here:** the primary architectural pattern and a component
diagram showing how the main pieces relate. Keep it at the conceptual level —
boxes and arrows, not code.

**Harness SDD example:**

### Pattern

Multi-adapter renderer with a CLI-agnostic canonical manifest. The manifest
drives all adapters; adapters are generated, never primary.

### Component Diagram

```
[agentic.json]  ←── canonical source of truth
      │
      ▼
[render.py]  ─── stack detection ──► [project_detect rules]
      │
      ├──► [opencode.json]       ← OpenCode adapter
      ├──► [GEMINI.md]           ← Gemini CLI adapter
      └──► [CLAUDE.md + .claude/] ← Claude Code adapter

[subagents/]     ─── SUBAGENT.md (instructions) + SOUL.md (identity)
[steering/]      ─── per-role behavior directives
[hooks/]         ─── lifecycle automation (on_spec_created, on_feature_done, …)
[specs/<feat>/]  ─── requirements.md + design.md + tasks.md (SDD artifacts)
[progress/]      ─── session state, decisions, handoffs
```

---

## 4. Key Components & Responsibilities

**What to write here:** a table of the main components, what each one does,
and which technology or tool implements it.

| Component | Responsibility | Technology |
|-----------|----------------|------------|
| `agentic.json` | Canonical manifest: declares agents, skills, commands, steering, hooks | JSON |
| `render.py` | Reads manifest, generates CLI adapters deterministically | Python 3 |
| `bootstrap.sh` | CLI for render.py: render, validate, scaffold lifecycle management | Bash |
| `check.sh` | Verification gateway: JSON validity, adapter parity, SDD integrity | Bash + Python |
| `subagents/<name>/SUBAGENT.md` | Operational instructions for each agent role | Markdown |
| `subagents/<name>/SOUL.md` | Identity, decision principles, and boundaries per agent | Markdown |
| `steering/<name>.md` | Per-role behavior directives (project-level context) | Markdown |
| `hooks/run-hooks.sh` | Executes lifecycle scripts at SDD transition points | Bash |
| `specs/<feat>/` | SDD artifacts: requirements (EARS), design, tasks | Markdown |
| `progress/` | Session state, decisions, progress log, handoffs | Markdown |

---

## 5. Data Flow & Integration

**What to write here:** how data flows through the system, how components
communicate, and how external integrations are handled.

**Harness SDD example:**

The framework has no runtime data flow — it is a static configuration system.
The flow is build-time and session-time:

**Build-time (developer runs bootstrap):**
```
Edit agentic.json → bootstrap.sh <cli> → render.py reads manifest
→ writes CLI-specific adapter files → check.sh validates consistency
```

**Session-time (agent reads context):**
```
Agent starts → reads AGENTS.md (navigation) → reads CLAUDE.md/GEMINI.md (instructions)
→ reads feature_list.json (active feature) → reads progress/current.md (session state)
→ reads specs/<feat>/tasks.md (what to do) → executes → check.sh validates
```

**Lifecycle hooks (SDD transitions):**
```
/spec → hooks/run-hooks.sh on_spec_created → custom scripts in hooks/
/approve → on_spec_approved → ...
/implement → on_implementation_start / on_implementation_complete → ...
/done → on_review_complete / on_feature_done → ...
```

---

## 6. Global Constraints

**What to write here:** hard technical constraints that every agent and
developer must respect. Things that cannot be negotiated at the feature level.

**Harness SDD example:**

- **No hand-editing generated files**: `opencode.json`, `GEMINI.md`, `CLAUDE.md`,
  `.claude/`, `.gemini/` are generated. Edit `agentic.json` and re-render.
- **check.sh is the gateway**: no feature is `done` unless `check.sh` exits 0.
- **One feature `in_progress` at a time**: enforced by `check.sh` and `feature_list.json`.
- **Spec before code**: features with `sdd: true` require human-approved spec
  before implementation begins. No exceptions.
- **Python 3.8+**: `render.py` requires Python 3.8 or later. No external
  dependencies beyond the standard library.

---

> **Note to AI agents:** Before proposing a feature-specific design in
> `specs/<feature>/design.md`, read this document to ensure the proposal
> aligns with the principles and constraints defined here. If a feature
> requires violating a constraint, document the justified exception in
> the feature's `design.md` as a discarded alternative section.
