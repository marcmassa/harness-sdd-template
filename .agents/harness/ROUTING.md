# Agent Routing Decision Tree — Harness SDD

## Decision Tree

```
START: New Task Received
        │
        ▼
┌────────────────────────────────────────────┐
│ Is this an SDD spec/feature task?          │
│ (spec, sdd, feature_list, requirements,   │
│  design, tasks, ears, trazabilidad)        │
└──────────────────┬─────────────────────────┘
                   │
            ┌──────┴──────┐
            │ Yes         │ No
            ▼             ▼
     ┌─────────────────────────────────────────┐
     │ Check feature_list.json status:        │
     │                                        │
     │ pending → spec_author (quality-agent)  │
     │          → create specs/<feature>/     │
     │          → mark spec_ready → STOP      │
     │                                        │
     │ spec_ready → WAIT for human approval   │
     │                                        │
     │ in_progress → implementer + tester     │
     │               → run tasks.md           │
     │               → check.sh → done        │
     └─────────────────────────────────────────┘
                          │
                          ▼
             [Return to normal task routing]
                          │
                          ▼
┌────────────────────────────────────┐
│ Is this infrastructure / IaC?     │
│ (Terraform, Helm, K8s, Cloud)     │
└──────────────┬─────────────────────┘
               │
         ┌─────┴─────┐
         │ Yes       │ No
         ▼           ▼
  ┌────────────┐  ┌────────────────────┐
  │ cloud-     │  │ Is this testing?  │
  │ architect  │  │ (pytest, terratest)│
  │ + platform │  └────────┬───────────┘
  │ engineer   │           │
  └──────┬─────┘      ┌────┴────┐
         │            │ Yes    │ No
         │            ▼        ▼
         │      ┌────────┐ ┌──────────────────┐
         │      │ tester │ │ Is this docs/    │
         │      │ -agent │ │ handoff?         │
         │      └────────┘ └────────┬─────────┘
         │                          │
         │                     ┌────┴────┐
         │                     │ Yes    │ No
         │                     ▼        ▼
         │               ┌────────┐ ┌────────────┐
         │               │ escriba│ │ quality-   │
         │               └────────┘ │ agent      │
         │                          │ (review)   │
         │                          └────────────┘
         ▼
  ┌────────────────┐
  │ + quality-agent│
  │ + tester       │
  └────────────────┘
```

## Subagent Definitions

Cada subagente se define en `.agents/subagents/<nombre>/SUBAGENT.md` con frontmatter YAML estándar:
```yaml
---
name: <nombre>
type: subagent
user-invocable: true
description: "<descripción breve>"
model-agnostic: true
---
```
Para crear un nuevo subagente, copia `.agents/subagents/agent-template/`, renombra la carpeta y edita el SUBAGENT.md.

## Skills

Las **skills** (en `.agents/skills/`) son complementos que los agentes pueden cargar para adquirir conocimientos específicos o flujos de trabajo especializados sin necesidad de crear un nuevo subagente completo.

## Routing Matrix

| Task Type | Keywords | Primary Agent | Secondary Agents |
|-----------|----------|---------------|------------------|
| **SDD Spec** | spec, sdd, requirements, design, tasks, ears, feature_list | `spec_author` (quality-agent) | — |
| **SDD Implementation** | implement, code, after approval | `implementer` (orquestador) | `tester-agent`, `reviewer` |
| **Infra / IaC** | terraform, helm, k8s, cloud, aws, gcp, azure, vpc, eks, aks, gke | `cloud-architect` + `platform-engineer` | `quality-agent`, `tester-agent` |
| **Testing** | test, coverage, terratest, pytest, verification | `tester-agent` | `quality-agent` |
| **Security / Compliance** | security, policy, compliance, soc2, hipaa, network policy | `security-reviewer` | `quality-agent` |
| **Documentation** | docs, readme, progress, handoff, runbook | `escriba` | `quality-agent` |
| **General** | Any other task | `quality-agent` | (depends on specifics) |

*[Personaliza esta matriz con los nombres reales de tus subagentes una vez los crees en `.agents/subagents/`.]*
