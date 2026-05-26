# AGENTS.md — Mapa de navegación para agentes

> Este archivo es el **punto de entrada** para cualquier agente que trabaje en este repositorio.
> No es una biblia de reglas: es un **mapa**. Lee solo lo que necesites cuando lo necesites (divulgación progresiva).

---

## 1. Before starting (mandatory)

1. Run `./check.sh` and verify it finishes without errors. If it fails, **stop** and resolve the environment before touching code.
2. Read `DESIGN.md` to understand the high-level architecture and global principles.
3. Read `feature_list.json`. Every new feature with `"sdd": true` goes through **Spec Driven Development**.
4. Read `progress/current.md` to understand the state of the last session.
5. If the task involves an SDD feature, read `specs/README.md` and `docs/sdd.md`.

## 2. Repository Map

| File / Folder | Content | When to read it |
|---|---|---|
| `DESIGN.md` | High-level architecture and global principles | Always, for architectural context |
| `feature_list.json` | Feature list with status (pending/spec_ready/in_progress/done/blocked) | Always, at the start |
| `progress/current.md` | Current session state | Always, at the start |
| `progress/history.md` | Append-only log of previous sessions | If historical context is needed |
| `specs/<feature>/` | requirements.md + design.md + tasks.md (SDD format) | Before implementing any feature with `"sdd": true` |
| `docs/sdd.md` | Complete SDD process (EARS, traceability, templates) | Before drafting or reading a spec |
| `check.sh` | Verification script (build, tests, validations) | Before declaring a task as done |

## 3. Hard Rules (non-negotiable)

- **One feature at a time.** Do not mix changes from multiple tasks in the same session.
- **Do not declare a task `done` without green tests.** Run `./check.sh` and ensure it passes.
- **Do not skip the spec phase.** Every feature with `"sdd": true` must pass through spec_author and get human approval before touching code.
- **Do not skip the human approval gate.** The flow stops at `spec_ready` and waits.
- **Document what you do** in `progress/current.md` while you work, not at the end.
- **Leave the repository clean** before closing the session (see §5).

## 4. Workflow (SDD)

```
pending → [spec_author] → spec_ready → ⏸ HUMAN → in_progress → [implementer → reviewer] → done
```

1. The agent detects the first `pending` feature with `"sdd": true` in `feature_list.json`.
2. The agent (as spec_author) reads `DESIGN.md` for architectural context.
3. The agent creates `specs/<name>/{requirements,design,tasks}.md` and marks status as `spec_ready`.
4. **Pause.** The human reads the spec in `specs/<name>/` and approves (or requests changes).
5. Once approved, change status to `in_progress` and proceed with implementation.
6. Execute `tasks.md` one by one, marking `[x]`.
7. Verify traceability `R<n>` ↔ test and completed tasks.
8. Run `./check.sh` — it must pass.
9. Mark as `done` and record the summary in `progress/progress.md`.

## 5. Session Closing

Before finishing:

1. Run `./check.sh` — all green.
2. If the task is finished: set `status: "done"` in `feature_list.json`.
3. Move the summary from `progress/current.md` to the end of `progress/history.md`.
4. Empty `progress/current.md`, leaving only the template.
5. Do not leave temporary files, debug print() statements, or TODOs without context.

## 6. Repository Stack

> **NOTE:** Customize this section according to your real project's technology stack.

| Layer | Technology |
|------|-----------|
| Infrastructure | *[e.g., Terraform, Terragrunt, Pulumi, CloudFormation]* |
| Orchestration / K8s | *[e.g., Helm, Kustomize, Crossplane, Docker Compose]* |
| CI/CD | *[e.g., GitHub Actions, GitLab CI, ArgoCD, Jenkins]* |
| Languages | *[e.g., Python, Go, TypeScript, Java, Rust]* |
| Validation | *[e.g., pytest, vitest, golangci-lint, tflint, checkov, trivy]* |

## 7. Project Subagents

Each subagent is defined in `.agents/subagents/<name>/SUBAGENT.md` with YAML frontmatter, mission, tasks, tools, and workflow.

| Agent | File | Responsibility |
|--------|---------|-----------------|
| `agent-template` | `.agents/subagents/agent-template/SUBAGENT.md` | **Example Template** — copy this directory to create new subagents |

*[Customize: duplicate `.agents/subagents/agent-template/`, rename the folder, and edit SUBAGENT.md for each role in your team. Common examples: cloud-architect, platform-engineer, security-reviewer, tester-agent, quality-agent, scribe.]*
