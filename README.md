# Harness SDD — Implementation Template

Template for adopting **Harness Engineering + Spec Driven Development (SDD)** in any software project (Infrastructure, Platform, or Application).

This template provides a structured, traceable, and verifiable workflow for AI agents and human developers to collaborate effectively.

---

## Index

- [What is Harness Engineering?](#what-is-harness-engineering)
- [Why SDD + Harness?](#why-sdd--harness)
- [Benefits](#benefits)
- [Complete Workflow](#complete-workflow)
- [Template Structure](#template-structure)
- [Quick Adoption Guide (5 steps)](#quick-adoption-guide-5-steps)
- [How to Customize for Your Stack](#how-to-customize-for-your-stack)
- [FAQ and Troubleshooting](#faq-and-troubleshooting)

---

## What is Harness Engineering?

**Harness Engineering** is a methodology to structure code repositories so that AI agents can work on them autonomously, traceably, and verifiably.

The harness has 4 pillars:

| Pillar | Meaning | Implementation |
|-------|-----------------|----------------------|
| **1. The Repo IS the System** | All info an agent needs is in the repo, not in the dev's mind | `AGENTS.md`, `feature_list.json`, `specs/`, `progress/`, `docs/` |
| **2. Spec Driven Development** | No code is written until requirements are specified, designed, and approved by a human | `specs/<feature>/{requirements,design,tasks}.md` with R<n> ↔ test traceability |
| **3. Operational Memory on Disk** | Session state, decisions, and backlog live in files, not in the chat | `progress/{current,progress,backlog,decisions,handoff}.md` |
| **4. Executable Verification** | A script (`check.sh`) validates builds, tests, spec integrity, and harness rules | `check.sh` — gateway for declaring a task as `done` |

---

## Why SDD + Harness?

### The Problem

Without an explicit harness, AI agent interactions often follow this pattern:

```
Human: "Add support for X"
Agent: (writes code without full context)
       (skips steps, assumes non-existent conventions)
       (leaves repo in an indeterminate state)
Human: (reviews, finds errors, asks for changes)
Agent: (iterates without memory of the previous iteration)
       → Frustration, wasted time, inconsistent code
```

### The Solution

With SDD + Harness, the flow is:

```
Human: "Add support for X"
Agent (spec_author):
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

→ Full traceability, 0 ambiguity, human only reviews once
```

---

## Benefits

1. **Full Traceability:** Every decision is recorded in `progress/decisions.md` (ADR). Requirements (R1, R2...) map to specific tests.
2. **One Feature at a Time:** The harness ensures only one feature is `in_progress`, avoiding context switching and dependencies.
3. **Multi-Team Consistency:** Developers, SREs, and AI agents follow the same flow (spec → approval → code → tests → close).
4. **Reduced Code Review Friction:** Reviewers trust the process (approved spec + `check.sh` + traceability).
5. **AI Agent Onboarding:** A new agent can read `AGENTS.md` and `feature_list.json` to understand the project state immediately.
6. **Modular & Agnostic Architecture:** The template methodology is technology-independent. Specific technical knowledge is pulled from a centralized [Agent Skills Registry](https://gitlab.devops.onesait.com/onesait/technology/devops/infrastructure/agent-skills-registry.git).

---

## Complete Workflow

### State Diagram

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
                                       │ quality-agent / spec_author
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
                                       │ tester-agent adds tests
                                       │ R<n> ↔ test documented
                                       │ check.sh passes
                                       ▼
                              ┌─────────────────┐
                              │     done         │
                              │  (closed)        │
                              └─────────────────┘
```

---

## Quick Adoption Guide (5 steps)

### Step 1: Copy the Template to Your Repo

```bash
cp -r harness-sdd-template/* /path/to/your/repo/
cd /path/to/your/repo
```

### Step 2: Customize `AGENTS.md`

Edit the main file to reflect your stack, teams, and agents.

### Step 3: Create Your First Feature in `feature_list.json`

Add a pending feature entry with `sdd: true` to start the SDD process.

### Step 4: Run `check.sh` to Verify

```bash
chmod +x check.sh
./check.sh
```

### Step 5: Launch Your First SDD Cycle

Ask your AI agent:

> "Apply Harness Engineering with SDD to implement the pending features in feature_list.json"

---

## How to Customize for Your Stack

### Adapt `check.sh`

The generic `check.sh` supports Python, TypeScript, and Go. Add blocks for your specific tools (e.g., `terraform fmt`, `hadolint`, `rustc`, etc.).

### Adapt EARS Templates

The templates in `specs/templates/` use generic examples. You can replace them with examples relevant to your specific domain (Infra, Web, Data, etc.).

---

> **Based on:** Real-world implementations in multiple production projects.
