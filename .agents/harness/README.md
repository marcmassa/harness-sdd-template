# Harness SDD — Sistema de sub-agentes

Sistema de sub-agentes especializados para trabajar sobre las features del proyecto siguiendo el proceso SDD.

## Arquitectura de Agentes

```
                      ┌──────────────────────┐
                      │      HARNESS         │
                      │   (orquestador)      │
                      └────────┬─────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
     │  SPEC_AUTHOR   │ │  IMPLEMENTER   │ │  TESTER-AGENT  │
     │  (quality)     │ │  (orquestador) │ │  (tester)      │
     └────────────────┘ └────────────────┘ └────────────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                      ┌────────▼────────┐
                      │  REVIEWER       │
                      │  (quality)      │
                      └─────────────────┘
```

## Sub-agentes

Cada subagente se define en `.agents/subagents/<nombre>/SUBAGENT.md` con frontmatter YAML estándar.

| Agente | SUBAGENT.md | Responsabilidad |
|--------|-------------|-----------------|
| `agent-template` | `.agents/subagents/agent-template/SUBAGENT.md` | **Plantilla de ejemplo** — copia para crear nuevos subagentes |

*Para añadir un subagente real, duplica `.agents/subagents/agent-template/`, renombra la carpeta y personaliza el SUBAGENT.md.*

## Routing

Ver `ROUTING.md` para el árbol de decisión completo.
Ver `workflows.md` para flujos de trabajo predefinidos.
Ver `CONVENTION.md` para la convención de uso obligatoria.
