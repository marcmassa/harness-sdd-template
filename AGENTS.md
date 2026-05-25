# AGENTS.md — Mapa de navegación para agentes

> Este archivo es el **punto de entrada** para cualquier agente que trabaje en este repositorio.
> No es una biblia de reglas: es un **mapa**. Lee solo lo que necesites cuando lo necesites (divulgación progresiva).

---

## 1. Antes de empezar (obligatorio)

1. Ejecuta `./check.sh` y verifica que termina sin errores. Si falla, **para** y resuelve el entorno antes de tocar código.
2. Lee `feature_list.json`. Toda feature nueva con `"sdd": true` pasa por **Spec Driven Development**.
3. Lee `progress/current.md` para entender en qué estado quedó la última sesión.
4. Si la tarea involucra una feature SDD, lee `specs/README.md` y `docs/sdd.md`.

## 2. Mapa del repositorio

| Archivo / carpeta | Qué contiene | Cuándo leerlo |
|---|---|---|
| `feature_list.json` | Lista de features con estado (pending/spec_ready/in_progress/done/blocked) | Siempre, al empezar |
| `progress/current.md` | Estado de la sesión actual | Siempre, al empezar |
| `progress/history.md` | Bitácora append-only de sesiones anteriores | Si necesitas contexto histórico |
| `specs/<feature>/` | requirements.md + design.md + tasks.md (formato SDD) | Antes de implementar cualquier feature con `"sdd": true` |
| `docs/sdd.md` | Proceso SDD completo (EARS, trazabilidad, plantillas) | Antes de redactar o leer un spec |
| `check.sh` | Script de verificación (build, tests, validaciones) | Antes de declarar una tarea como done |

## 3. Reglas duras (no negociables)

- **Una sola feature a la vez.** No mezcles cambios de varias tareas en la misma sesión.
- **No declares una tarea `done` sin pruebas verdes.** Ejecuta `./check.sh` y asegúrate de que pasa.
- **No saltes la fase de spec.** Toda feature con `"sdd": true` debe pasar por spec_author y obtener aprobación humana antes de tocar código.
- **No saltes la puerta de aprobación humana.** El flujo se detiene en `spec_ready` y espera.
- **Documenta lo que haces** en `progress/current.md` mientras trabajas, no al final.
- **Deja el repositorio limpio** antes de cerrar la sesión (ver §5).

## 4. Flujo de trabajo (SDD)

```
pending → [spec_author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

1. El agente detecta la primera feature `pending` con `"sdd": true` en `feature_list.json`.
2. El agente (como spec_author) crea `specs/<name>/{requirements,design,tasks}.md` y marca status como `spec_ready`.
3. **Pausa.** El humano lee el spec en `specs/<name>/` y aprueba (o pide cambios).
4. Una vez aprobado, cambiar status a `in_progress` y proceder con la implementación.
5. Ejecutar `tasks.md` una a una, marcando `[x]`.
6. Verificar trazabilidad `R<n>` ↔ test y tasks completas.
7. Ejecutar `./check.sh` — debe pasar.
8. Marcar `done` y registrar resumen en `progress/progress.md`.

## 5. Cierre de sesión

Antes de terminar:

1. Ejecuta `./check.sh` — todo verde.
2. Si la tarea está acabada: marca `status: "done"` en `feature_list.json`.
3. Mueve el resumen de `progress/current.md` al final de `progress/history.md`.
4. Vacía `progress/current.md` dejando solo la plantilla.
5. No dejes archivos temporales, ni print() de debug, ni TODOs sin contexto.

## 6. Stack del repositorio

*[Personalizar: indica aquí tu stack tecnológico principal]*

| Capa | Tecnología |
|------|-----------|
| Infraestructura | *[ej: Terraform, Terragrunt, Pulumi]* |
| Kubernetes | *[ej: Helm, Kustomize, Crossplane]* |
| CI/CD | *[ej: GitHub Actions, GitLab CI, ArgoCD]* |
| Lenguajes | *[ej: Python, Go, TypeScript, HCL]* |
| Validación | *[ej: pytest, golangci-lint, tflint, checkov]* |

## 7. Subagentes recomendados

| Agente | Responsabilidad principal |
|--------|--------------------------|
| `cloud-architect` | Diseño de infraestructura multi-cloud, decisión de servicios, costes |
| `platform-engineer` | Implementación Terraform/Pulumi, pipelines, Helm |
| `security-reviewer` | Políticas de seguridad, compliance, network policies |
| `tester-agent` | Tests de infraestructura (Terratest, Kitchen-Terraform) |
| `quality-agent` | Code review, buenas prácticas, validación de convenciones |
| `escriba` | Documentación técnica, runbooks, handoffs |

*[Personalizar: ajusta los subagentes según tu equipo y stack]*
