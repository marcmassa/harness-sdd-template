# Harness SDD — Template de Implementación

Plantilla para adoptar **Harness Engineering + Spec Driven Development (SDD)** en equipos Cloud y DevOps.

Este template empaqueta la experiencia de implementación real en dos proyectos (Hypermove y SecurIT) en un formato reutilizable. Puedes copiarlo, adaptarlo e integrarlo en cualquier repositorio de infraestructura, plataforma o desarrollo.

---

## Índice

- [¿Qué es Harness Engineering?](#qué-es-harness-engineering)
- [¿Por qué SDD + Harness?](#por-qué-sdd--harness)
- [Beneficios para equipos Cloud y DevOps](#beneficios-para-equipos-cloud-y-devops)
- [Flujo de trabajo completo](#flujo-de-trabajo-completo)
- [Estructura del template](#estructura-del-template)
- [Guía de adopción rápida (5 pasos)](#guía-de-adopción-rápida-5-pasos)
- [Cómo personalizar para tu stack](#cómo-personalizar-para-tu-stack)
- [FAQ y troubleshooting](#faq-y-troubleshooting)

---

## ¿Qué es Harness Engineering?

**Harness Engineering** es una metodología para estructurar repositorios de código de forma que los agentes de IA (Claude Code, Copilot, opencode, etc.) puedan trabajar sobre ellos de forma autónoma, trazable y verificable.

El harness tiene 4 pilares:

| Pilar | ¿Qué significa? | ¿Cómo se manifiesta? |
|-------|-----------------|----------------------|
| **1. El repositorio ES el sistema** | Toda la información que un agente necesita debe estar en archivos del repo, no en la mente del desarrollador | `AGENTS.md`, `feature_list.json`, `specs/`, `progress/`, `docs/` |
| **2. Spec Driven Development** | No se escribe código hasta que los requisitos están especificados, diseñados y aprobados por un humano | `specs/<feature>/{requirements,design,tasks}.md` con trazabilidad R<n> ↔ test |
| **3. Memoria operativa en disco** | El estado de la sesión, decisiones y backlog viven en archivos, no en el chat | `progress/{current,progress,backlog,decisions,handoff}.md` |
| **4. Verificación ejecutable** | Un script (`check.sh`) valida builds, tests, integridad del spec y reglas del harness | `check.sh` — gateway para declarar una tarea como `done` |

### ¿Por qué es relevante para Cloud y DevOps?

Los equipos de plataforma e infraestructura gestionan repositorios con alta complejidad técnica: Terraform modules, Helm charts, pipelines CI/CD, Kubernetes manifests, políticas de seguridad, etc. Estos repositorios son **candidatos ideales** para Harness Engineering porque:

- **Alta densidad de conocimiento tácito** — la configuración de un cluster rara vez está documentada
- **Múltiples agentes involucrados** — developes, SREs, security, compliance
- **Repetitividad** — añadir un provider cloud, desplegar en una nueva región, auditar políticas
- **Riesgo alto** — un cambio mal hecho en IaC puede tumbar producción

Harness Engineering convierte el repositorio en una **máquina de estado** que cualquier agente (humano o IA) puede leer, entender y modificar con seguridad.

---

## ¿Por qué SDD + Harness?

### El problema

Sin un harness explícito, el trabajo con agentes de IA sigue este patrón:

```
Humano: "Añade soporte para AWS S3 como backend de Terraform"
Agente: (escribe código sin entender el contexto completo)
        (salta pasos, asume convenciones que no existen)
        (deja el repo en un estado indeterminado)
Humano: (revisa, encuentra errores, pide cambios)
Agente: (itera sin memoria de la iteración anterior)
        → Frustración, pérdida de tiempo, código inconsistente
```

### La solución

Con SDD + Harness, el flujo es:

```
Humano: "Añade soporte para AWS S3 como backend de Terraform"
Agente (spec_author):
  1. Lee feature_list.json → detecta feature con sdd:true, status:pending
  2. Crea specs/s3-backend/requirements.md (EARS: R1, R2, ...)
  3. Crea specs/s3-backend/design.md (archivos, firmas, alternativas)
  4. Crea specs/s3-backend/tasks.md (checklist T1, T2, ... con R<n>)
  5. Marca status: spec_ready y PARA

⏸ Humano: Lee los 3 archivos en specs/s3-backend/ y dice "aprobado"

Agente (implementer):
  6. Ejecuta tasks.md secuencialmente, marcando [x]
  7. tester-agent añade tests con trazabilidad R<n> ↔ test
  8. Ejecuta ./check.sh → todo verde
  9. Marca status: done en feature_list.json
  10. Registra en progress/progress.md

→ Trazabilidad completa, 0 ambigüedad, humano solo revisa una vez
```

### Principio clave

> **El agente no implementa lo que tú le pides. Implementa lo que tú apruebas.**

La puerta de aprobación humana en `spec_ready` es el mecanismo que evita que el agente malinterprete instrucciones y escriba código incorrecto. El humano revisa 3 archivos markdown (no código) y da el visto bueno — o pide cambios antes de que se escriba una sola línea.

---

## Beneficios para equipos Cloud y DevOps

### 1. Trazabilidad completa

Cada decisión técnica queda registrada en el formato ADR (`progress/decisions.md`). Cada requerimiento (`R1`, `R2`, ...) se mapea a un test concreto. ¿Por qué se eligió AWS EKS sobre GKE en la región `eu-west-1`? Está en el spec de diseño. ¿Qué requisito de compliance cubre el módulo de S3 encryption? El task T3 referencia R4.

### 2. Una feature a la vez

El harness valida que solo haya una feature en `in_progress`. Esto evita:

- Cambios a medias en múltiples providers cloud simultáneamente
- Dependencias entre features que deberían estar en el mismo PR
- Sesiones de trabajo sin foco que dejan el repositorio inconsistente

### 3. Consistencia multi-equipo

Cuando un developer, un SRE y un agente IA trabajan en el mismo repositorio, el harness garantiza que:

- Todos siguen el mismo flujo (spec → approval → code → tests → close)
- Todos documentan en el mismo formato (EARS, ADRs, progress)
- Todos verifican con el mismo script (`check.sh`)
- El handoff entre equipos es un archivo markdown, no una conversación

### 4. Reducción de fricción en code review

El revisor humano no necesita entender el código línea por línea si confía en el proceso:

- El spec (aprobado previamente) define qué se espera
- `check.sh` verifica builds, tests y reglas del harness
- La trazabilidad R<n> ↔ test demuestra cobertura
- El revisor solo mira el diff para detectar efectos secundarios

### 5. Onboarding para agentes IA

Un nuevo agente (o un agente que vuelve tras meses) puede leer `AGENTS.md`, `feature_list.json` y `progress/current.md` y entender:

- En qué estado está el proyecto
- Qué se está haciendo ahora
- Cuál es el flujo de trabajo
- Dónde están las fuentes de verdad

Sin tener que preguntar a un humano.

---

## Flujo de trabajo completo

### Diagrama de estado

```
                          ┌──────────────────────────────────────────┐
                          │           feature_list.json              │
                          │  (una feature a la vez, sdd:true/false)  │
                          └──────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │    pending       │
                              │  (sin spec)      │
                              └────────┬─────────┘
                                       │ quality-agent / spec_author
                                       │ crea specs/<feature>/{requirements,design,tasks}.md
                                       ▼
                              ┌─────────────────┐
                              │   spec_ready     │
                              │  (⏸ esperando)   │◄──────────────────┐
                              └────────┬─────────┘                   │
                                       │                             │
                              ┌────────▼────────┐                   │
                              │  APROBACIÓN     │── No → corrige ────┘
                              │   HUMANA        │
                              └────────┬─────────┘
                                       │ Sí
                                       ▼
                              ┌─────────────────┐
                              │  in_progress     │
                              │  (implementando) │
                              └────────┬─────────┘
                                       │ implementer sigue tasks.md
                                       │ tester-agent añade tests
                                       │ R<n> ↔ test documentado
                                       │ check.sh pasa
                                       ▼
                              ┌─────────────────┐
                              │     done         │
                              │  (cerrado)       │
                              └─────────────────┘
```

### Fases detalladas

#### Fase 0: Planificación (humano o lead)

1. Identificar la siguiente feature prioritaria del backlog
2. Añadir entrada en `feature_list.json` con `status: "pending"` y `sdd: true` si requiere spec
3. Opcional: dejar `sdd: false` para tareas triviales (typos, refactors menores, chores)

#### Fase 1: Spec (spec_author → quality-agent)

1. Leer `feature_list.json` y detectar primera feature `pending` con `sdd: true`
2. Leer `specs/README.md` y `specs/templates/`
3. Leer `docs/sdd.md` si se necesita contexto EARS detallado
4. Crear `specs/<feature>/requirements.md`:
   - Requisitos en notación EARS estricta (R1, R2, ...)
   - Cada R<n> debe ser verificable por al menos un test concreto
   - Patrones: Ubicuo, Evento, Estado, Opcional, No deseado
5. Crear `specs/<feature>/design.md`:
   - Archivos afectados (con acción y razón)
   - Firmas de funciones/clases/componentes
   - Algoritmo o flujo paso a paso
   - Manejo de errores
   - **Al menos una alternativa descartada** con justificación
   - Riesgos y edge cases
6. Crear `specs/<feature>/tasks.md`:
   - Checklist numerado (T1, T2, ...)
   - Cada tarea referencia los R<n> que cubre
   - Incluye tareas de implementación, tests y cierre
7. Actualizar `feature_list.json`: cambiar `status` a `"spec_ready"`
8. **PARAR** — notificar al humano que revise los archivos en `specs/<feature>/`

#### Fase 2: Gate humano (obligatorio para features SDD)

1. Humano lee `specs/<feature>/requirements.md`:
   - ¿Los requisitos cubren todos los casos de uso?
   - ¿Son verificables? ¿Falta alguno?
   - ¿El lenguaje EARS es correcto (DEBE, NO DEBE)?
2. Humano lee `specs/<feature>/design.md`:
   - ¿La arquitectura propuesta es correcta?
   - ¿La alternativa descartada tiene sentido?
   - ¿Hay riesgos no cubiertos?
3. Humano lee `specs/<feature>/tasks.md`:
   - ¿Las tareas están en orden lógico?
   - ¿Cada R<n> tiene al menos un test asociado?
4. Decisión:
   - **Aprobar** → continuar a Fase 3
   - **Solicitar cambios** → spec_author corrige y vuelve a presentar (loop Fase 1-2)
5. Actualizar `feature_list.json`: cambiar `status` a `"in_progress"`

#### Fase 3: Implementación (implementer)

1. Ejecutar tasks.md secuencialmente, marcando `[x]` al completar cada T<n>
2. Por cada task de implementación:
   - Escribir código siguiendo `design.md` y convenciones del proyecto
   - Commit tras cada task completada (opcional pero recomendado)
3. Por cada task de tests:
   - Escribir tests que verifiquen los R<n> referenciados
   - Documentar trazabilidad `R<n> → test` en `progress/impl_<feature>.md`
4. Documentar:
   - Mapa de trazabilidad completo
   - Cualquier desviación del spec original (y por qué)

#### Fase 4: Verificación y cierre (reviewer)

1. Ejecutar `./check.sh` — **debe pasar limpio**
2. `check.sh` valida:
   - ✅ Build del proyecto (Go/Python/TS según stack)
   - ✅ Tests unitarios y de integración
   - ✅ JSON válido en `feature_list.json`
   - ✅ Solo una feature en `in_progress`
   - ✅ Specs presentes para features SDD con estado avanzado
   - ✅ Archivos de progreso presentes
3. Revisor verifica trazabilidad:
   - Cada R<n> tiene al menos un test → `progress/impl_<feature>.md`
   - Cada test cubre al menos un R<n>
4. Actualizar `feature_list.json`: cambiar `status` a `"done"`
5. Registrar en `progress/progress.md`: resumen de lo implementado, archivos tocados, decisiones
6. Opcional: mover resumen de `progress/current.md` al final de `progress/history.md`

---

## Estructura del template

```
repositorio/                          # ← Tu repositorio (copia esta carpeta)
│
├── AGENTS.md                         # Punto de entrada para agentes IA
│                                     # Divulgación progresiva: solo lee lo necesario
│
├── feature_list.json                 # Registro machine-legal de features
│                                     # Formato: id, name, title, type, status, sdd, priority, agent
│                                     # Una feature a la vez en in_progress
│
├── check.sh                          # Script de verificación ejecutable
│                                     # Build + tests + validaciones SDD
│                                     # Gateway para declarar una tarea como done
│
├── specs/                            # Spec Driven Development
│   ├── README.md                     # Documentación del proceso SDD
│   ├── templates/                    # Plantillas reutilizables
│   │   ├── requirements.md           # EARS: Requisitos en 5 patrones
│   │   ├── design.md                 # Decisiones técnicas + alternativas
│   │   └── tasks.md                  # Checklist con trazabilidad R<n>
│   └── <feature-name>/               # Un directorio por feature (creado por spec_author)
│       ├── requirements.md           # R1, R2, ... (EARS estricto)
│       ├── design.md                 # Arquitectura, firmas, alternativas
│       └── tasks.md                  # T1, T2, ... (checklist ejecutable)
│
├── docs/
│   └── sdd.md                        # Documentación completa del proceso SDD
│                                     # EARS en detalle, trazabilidad, ejemplos, anti-patrones
│
├── progress/                         # Memoria operativa (vive en disco, no en el chat)
│   ├── current.md                    # Snapshot de la sesión activa
│   ├── progress.md                   # Bitácora cronológica append-only
│   ├── backlog.md                    # Lista priorizada de pendientes
│   ├── decisions.md                  # ADR ligeros (Arquitecture Decision Records)
│   └── handoff.md                    # Estado transferible entre agentes/sesiones
│
├── .agents/
│   └── harness/                      # Sistema de sub-agentes
│       ├── README.md                 # Documentación interna del harness
│       ├── ROUTING.md                # Árbol de decisión + matriz de enrutamiento
│       ├── workflows.md              # Flujos predefinidos para tareas comunes
│       ├── CONVENTION.md             # Convención de uso obligatoria
│       ├── harness.sh                # CLI para enrutamiento y checks
│       ├── context/
│       │   ├── shared-context.md     # Contexto compartido entre agentes
│       │   ├── task-queue.json       # Cola de tareas
│       │   └── agent-results/        # Resultados de ejecuciones de subagentes
│       └── agents/
│           └── prompts/              # Plantillas de prompts para subagentes
│
└── examples/
    └── deploy-cluster/               # Spec de ejemplo: despliegue de cluster EKS
        ├── requirements.md           # 8 requisitos EARS
        ├── design.md                 # Diseño con Terraform + VPC + EKS + node groups
        └── tasks.md                  # 14 tareas con trazabilidad
```

### ¿Qué incluir en tu stack real?

El template es agnóstico del stack. Adapta estos directorios según tu proyecto:

| Stack | Directorios clave |
|-------|-------------------|
| **Terraform / OpenTofu** | `terraform/`, `modules/`, `environments/`, `terragrunt/` |
| **Kubernetes / Helm** | `charts/`, `manifests/`, `kustomize/`, `clusters/` |
| **Python (Cloud tooling)** | `src/`, `backend/`, `lambda/`, `scripts/` |
| **TypeScript (CDK, Pulumi)** | `src/`, `lib/`, `bin/`, `stacks/` |
| **Go (CLIs, operators)** | `cmd/`, `internal/`, `pkg/` |
| **Crossplane / ACK** | `compositions/`, `claims/`, `providers/` |
| **CI/CD Pipelines** | `.github/`, `gitlab-ci/`, `jenkins/`, `.circleci/` |
| **Docs / Runbooks** | `docs/`, `runbooks/`, `playbooks/` |

---

## Guía de adopción rápida (5 pasos)

### Paso 1: Copia el template en tu repositorio

```bash
# Asumiendo que tienes este template en algún lado accesible
cp -r harness-sdd-template/* /tu/repositorio/
cd /tu/repositorio
```

### Paso 2: Personaliza `AGENTS.md`

Edita el archivo principal para reflejar tu stack, tus equipos y tus agentes:

```markdown
# Fuentes de verdad del proyecto
1. `feature_list.json` — features y estado
2. `specs/<feature>/` — specs para features complejas
3. `AGENTS.md` — este archivo

## Stack
- Infraestructura: Terraform v1.x, AWS, GCP, Azure
- CI/CD: GitHub Actions
- Kubernetes: EKS, Helm, Kustomize

## Subagentes recomendados
- `cloud-architect` — diseño de infraestructura multi-cloud
- `security-reviewer` — políticas de seguridad, compliance
- `platform-engineer` — implementación Terraform/K8s
```

### Paso 3: Crea tu primer feature en `feature_list.json`

```json
{
  "project": "Mi Plataforma Cloud",
  "features": [
    {
      "id": "P1-001",
      "name": "eks-cluster-bootstrap",
      "title": "Bootstrapping de cluster EKS con node groups",
      "type": "feat",
      "status": "pending",
      "sdd": true,
      "priority": "P0",
      "agent": "platform-engineer"
    }
  ]
}
```

### Paso 4: Ejecuta `check.sh` para verificar

```bash
./check.sh
# → Muestra Python syntax ok, Terraform fmt ok, feature_list.json válido
```

Si el script no se adapta a tu stack, edítalo. Está diseñado para ser modificable:
- `--py-only`, `--ts-only`, `--go-only` flags para filtrar checks
- Las secciones son modulares: añade `terraform fmt` o `tflint` fácilmente

### Paso 5: Lanza tu primer ciclo SDD

Pide a tu agente IA favorito:

> "Implementa la siguiente feature pendiente siguiendo el flujo SDD definido en AGENTS.md"

El agente leerá `feature_list.json`, detectará `P1-001` con `sdd: true` y `status: pending`, y comenzará la Fase 1 (creación del spec). Cuando termine, tú revisas los archivos en `specs/eks-cluster-bootstrap/` y apruebas.

---

## Cómo personalizar para tu stack

### Adaptar `check.sh`

El script `check.sh` genérico soporta Python, TypeScript y Go. Si tu stack usa otras herramientas, añade bloques en la misma sección:

```bash
# Terraform checks (ejemplo)
section "Terraform — Format"
if command -v terraform &>/dev/null; then
    (cd "$ROOT_DIR" && terraform fmt -check -recursive) && pass "terraform fmt" || fail "terraform fmt"
    (cd "$ROOT_DIR" && terraform validate) && pass "terraform validate" || fail "terraform validate"
fi

# Dockerfile lint (ejemplo)
section "Docker — Hadolint"
if command -v hadolint &>/dev/null; then
    find . -name Dockerfile -exec hadolint {} \; && pass "hadolint" || fail "hadolint"
fi
```

### Adaptar las fuentes de verdad

En `AGENTS.md`, la sección "Fuentes de verdad (prioridad)" debe reflejar tu stack:

```markdown
## Fuentes de verdad
1. `architecture.md` — decisiones de alto nivel (regiones, providers, networking)
2. `terraform/terragrunt.hcl` — config de estado remoto y backends
3. `feature_list.json` — features actuales y su estado
4. `specs/<feature>/` — specs detallados
5. `runbooks/` — procedimientos operativos
```

### Añadir subagentes específicos de Cloud/DevOps

Los subagentes definidos en el template (`orquestador`, `design-agent`, `tester-agent`, `quality-agent`, `escriba`) son genéricos. Para un equipo Cloud/DevOps, considera:

| Subagente | Responsabilidad |
|-----------|----------------|
| `cloud-architect` | Diseño de infraestructura multi-cloud, decisiones de proveedor, costes |
| `security-reviewer` | Políticas de seguridad, compliance (SOC2, HIPAA, PCI), network policies |
| `terraform-specialist` | Módulos Terraform, state management, providers, workspaces |
| `k8s-operator` | Helm charts, Kustomize, operators, RBAC, pod security policies |
| `pipeline-engineer` | CI/CD pipelines, GitHub Actions, GitLab CI, ArgoCD |

### Adaptar los templates EARS para Cloud

Los templates `specs/templates/` usan ejemplos genéricos. Sobrescríbelos con ejemplos de infraestructura:

```markdown
# requirements.md (adaptado para Cloud)

## R1 — (Ubicuo)
DEBE existir un módulo Terraform `aws-eks-cluster` con los parámetros
`cluster_name`, `region`, `kubernetes_version`, `node_instance_types`.

## R2 — (Evento)
CUANDO se ejecuta `terraform apply` con `environment=production`,
DEBE crearse un cluster EKS con HA multi-AZ en 3 zonas de disponibilidad.

## R3 — (Estado)
MIENTRAS `enable_irsa = true`, DEBE asociarse un OIDC provider al cluster.

## R4 — (No deseado)
SI el `terraform plan` detecta que se va a destruir un recurso existente,
ENTONCES DEBE abortar la ejecución y mostrar el diff destructivo.
```

---

## FAQ y troubleshooting

### ¿Es obligatorio usar agentes IA? 

No. El harness funciona igual si lo usa un humano. `feature_list.json`, `progress/` y `check.sh` son útiles para cualquier equipo, con o sin IA. Los agentes IA son un acelerador, no un requisito.

### ¿Y si mi feature no necesita spec? (sdd: false)

Para tareas triviales (typo en README, renombrar variable, actualizar dependencia), marca `"sdd": false`. El agente puede implementar directamente sin pasar por las fases 1-2. El `check.sh` no validará specs para esas features.

### ¿Cómo gestiono features que dependen de otras?

No pueden estar ambas `in_progress`. Termina la primera (→ `done`), luego empieza la segunda. Si necesitas coordinar, documenta la dependencia en `progress/backlog.md` o en el `design.md` de la feature dependiente.

### ¿Qué pasa si el spec cambia durante la implementación?

Si el cambio es pequeño, documéntalo en el `tasks.md` (añade una nota) y en `progress/impl_<feature>.md`. Si el cambio es grande, el implementador debe parar, actualizar el spec (requirements/design) y volver a pasar por aprobación humana.

### ¿Cómo manejo features SDD que ya existían antes de adoptar el harness?

Marca las features existentes como `"status": "done"` y `"sdd": false`. A partir de la adopción, las nuevas features complejas usan `sdd: true`.

### Mi equipo usa OpenTofu, no Terraform

El template es agnóstico del stack. Cambia `terraform` por `tofu` en `check.sh` y en los ejemplos. El proceso SDD es el mismo.

### ¿Cómo integro esto con nuestro CI/CD?

Ejecuta `check.sh` como parte del pipeline de CI:

```yaml
# GitHub Actions example
- name: Harness validation
  run: ./check.sh
```

Considera ejecutar solo `check.sh --py-only` (o el flag que corresponda) en CI para evitar duplicar checks que ya corre el pipeline nativo, y el `check.sh` completo como pre-commit hook local.

---

> **Licencia:** Apache 2.0 — puedes usar, modificar y redistribuir libremente.
>
> **Basado en:** Implementación real en Hypermove (Go + React 19) y SecurIT (Python/Flask + TypeScript/Vite).
>
> **Referencia original:** [github.com/betta-tech/harness-sdd](https://github.com/betta-tech/harness-sdd)
