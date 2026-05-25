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

| Agente | Responsabilidad |
|--------|-----------------|
| `spec_author` | Escribe specs (requirements, design, tasks) para features con sdd:true |
| `implementer` | Ejecuta las tasks de implementación siguiendo el spec aprobado |
| `tester-agent` | Escribe tests y documenta trazabilidad R<n> ↔ test |
| `reviewer` | Verifica trazabilidad, completitud de tasks y check.sh |

## Routing

Ver `ROUTING.md` para el árbol de decisión completo.
Ver `workflows.md` para flujos de trabajo predefinidos.
Ver `CONVENTION.md` para la convención de uso obligatoria.
