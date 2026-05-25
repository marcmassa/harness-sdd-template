# SDD — Spec Driven Development

Este directorio contiene las **especificaciones formales** de cada funcionalidad del proyecto. Cada funcionalidad sigue el proceso SDD: **Requisitos → Diseño → Tareas → Código**, con un gate de aprobación humano antes de implementar.

## Flujo SDD

```
pending → [spec_author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

### Fases

| Fase | Quién | Qué produce |
|------|-------|-------------|
| **Requisitos** | `spec_author` (quality-agent) | `specs/<nombre>/requirements.md` — en notación EARS |
| **Diseño** | `spec_author` | `specs/<nombre>/design.md` — decisiones técnicas, alternativas descartadas |
| **Tareas** | `spec_author` | `specs/<nombre>/tasks.md` — checklist ejecutable con trazabilidad R<n> |
| **Gate** | **Humano** | Lee los 3 archivos → aprueba o solicita cambios |
| **Implementación** | `implementer` | Código, módulos Terraform, configuraciones |
| **Tests** | `tester-agent` | Tests de infraestructura, unitarios, integración |
| **Revisión** | `reviewer` (quality-agent) | Verifica trazabilidad: cada R<n> tiene un test |

## Estructura

```
specs/
├── README.md                    # Este archivo
├── templates/                   # Plantillas reutilizables
│   ├── requirements.md          # EARS notation template
│   ├── design.md                # Technical decisions template
│   └── tasks.md                 # Task checklist template
└── <feature-name>/              # Un directorio por funcionalidad
    ├── requirements.md          # R1, R2, ... (EARS estricto)
    ├── design.md                # Decisiones técnicas
    └── tasks.md                 # T1, T2, ... con referencias R<n>
```

El `<feature-name>` debe coincidir con el campo `name` en `feature_list.json`.

## Reglas de trazabilidad

1. Cada **R**equisito (`R1`, `R2`, ...) debe ser verificable por al menos un test concreto.
2. Cada **T**area (`T1`, `T2`, ...) debe referenciar los R<n> que cubre.
3. El implementador documenta el mapa `R<n> → test` en el reporte de implementación (`progress/impl_<feature>.md`).
4. El revisor verifica explícitamente esta correspondencia y rechaza si falta.

## Estados de una feature

| Estado | Significado |
|--------|-------------|
| `pending` | Sin spec — el spec_author es el primero en actuar. |
| `spec_ready` | Spec escrito — esperando aprobación humana. NO se toca código. |
| `in_progress` | Spec aprobado — implementador trabajando. |
| `done` | Código + tests, revisor aprobó, `check.sh` verde. |
| `blocked` | Atascado — razón en `progress/current.md`. |

Ver `docs/sdd.md` para la documentación completa del proceso SDD.
Ver `AGENTS.md` para la matriz de delegación de agentes.
