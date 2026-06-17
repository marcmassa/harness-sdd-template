# Requisitos — steering

> Feature **FEAT-003** de `feature_list.json`. Formaliza el concepto de «steering files» (archivos que dirigen el comportamiento del agente) como concepto de primera clase en el manifest `agentic.json`. Actualmente el steering es implícito (`instructions[]` + `AGENTS.md`). Este feature le da estructura, scope por agente, scaffolding, y validación.

## Patrones EARS

| Patrón | Sintaxis |
|--------|----------|
| Ubicuo | `DEBE ...` |
| Evento | `CUANDO <evento> DEBE ...` |
| Estado | `MIENTRAS <estado> DEBE ...` |
| Opcional | `DONDE <opción> DEBE ...` |
| No deseado | `SI <condición> ENTONCES DEBE ...` |

## Contexto y motivación

El Harness SDD template dirige el comportamiento del agente mediante dos mecanismos que ya existen:

1. `agentic.json#instructions[]` — lista plana de archivos que se cargan como contexto global. El renderer los vuelca directamente a `opencode.json#instructions[]`, `GEMINI.md`, y `CLAUDE.md`.
2. `agentic.json#subagents[].role_file` — cada sub-agente lee su `SUBAGENT.md` como su definición de rol.

Lo que **falta**:

- **Scope por agente**: no hay forma de declarar «este steering file aplica al implementer pero no al reviewer». Todo va al contexto global.
- **Estructura**: los archivos de steering son una lista plana sin metadatos (nombre, descripción, scope, applies_when).
- **Convención de directorio**: no existe un `steering/` o `.steer/` donde el proyecto organice sus directivas de comportamiento por rol.
- **Scaffolding**: crear un nuevo steering file para un agente es manual (copiar/pegar). No hay template.
- **Validación**: `check.sh` no verifica que los archivos referenciados en `steering` existan ni que su frontmatter YAML sea válido.

El ecosistema de CLIs ya tiene el concepto bajo distintos nombres:

| CLI | Mecanismo de steering | Formato |
|-----|----------------------|---------|
| OpenCode | `opencode.json#instructions[]` + `AGENTS.md` | JSON + Markdown |
| Claude Code | `CLAUDE.md` | Markdown |
| Gemini CLI | `GEMINI.md` | Markdown |

Los tres coinciden en que son **archivos Markdown cargados al inicio como contexto del LLM**. La diferencia es que en el Harness SDD queremos que cada sub-agente pueda tener **su propio steering file**, no solo uno global. Esto es consistente con la arquitectura del template (cada sub-agente tiene su `SUBAGENT.md`).

## Decisiones de arquitectura validadas

| Decisión | Opción elegida | Razón |
|----------|----------------|-------|
| Dónde vive el steering | **A — `steering/` en raíz del proyecto** | Visible, simple, consistente con `specs/`, `progress/`. No oculto en `.agents/`. |
| Cómo se declara en `agentic.json` | **A — array `steering[]` con objetos por archivo** | Consistente con `subagents[]` y `commands[]`. Cada entrada tiene `name`, `file`, `applies_to`, `description`. |
| Cómo se mapea a cada CLI | **B — merge al `instructions[]` global del CLI** | Simple, sin nueva superficie de API en cada adapter. Cada CLI ya soporta `instructions` como lista de archivos. El renderer concatena `instructions[]` global + `steering[].file`. |
| Scope por agente | **A — `applies_to: ["*"]` (global) o `applies_to: ["implementer", "reviewer"]`** | Flexible. El steering file se carga en el contexto del agente correspondiente. Los CLIs que no soportan per-agent instructions (Gemini, Claude) lo cargan globalmente con un aviso en el archivo. |
| Scaffolding de steering | **B — `agentic.json#_template_steering_examples[]` con un par de ejemplos** | Consistente con el lifecycle de sub-agents. No infla el manifest si el proyecto no usa steering. |
| Template de steering file | **A — YAML frontmatter + Markdown** | Igual que `SUBAGENT.md` y `SKILL.md`. El frontmatter lleva `name`, `description`, `applies_to`. |
| Validación en check.sh | **A — existen todos los archivos de `steering[].file`, YAML frontmatter válido** | Ligero, no bloqueante, informativo. |

## Requisitos

### R1 — Campo `steering` en `agentic.json`
- **Patrón:** Ubicuo
- El manifest `.agents/agentic.json` DEBE aceptar un campo `steering` de tipo array. Cada elemento DEBE tener los campos `name` (string, único), `file` (string, ruta relativa al steering file), `description` (string), y opcionalmente `applies_to` (array de strings con nombres de sub-agentes, default `["*"]` para global).

### R2 — Directorio `steering/` y convención de archivos
- **Patrón:** Ubicuo
- El proyecto DEBE incluir un directorio `steering/` en la raíz. Cada archivo dentro DEBE tener extensión `.md` y DEBE comenzar con un bloque YAML frontmatter (`---\nname: ...\ndescription: ...\napplies_to: [...]\n---`) seguido del cuerpo en Markdown.

### R3 — Renderer extiende `instructions` con steering files
- **Patrón:** Ubicuo
- `build_context` en `.agents/adapters/_common/render.py` DEBE incluir los steering files en el contexto del render. Para cada CLI: (a) si el CLI soporta `instructions` como array global (opencode, gemini, claude), los steering files DEBEN añadirse al array; (b) si el CLI soporta per-agent instructions, los steering files con `applies_to` específico DEBEN asignarse al agente correspondiente.

### R4 — Steering file global vs. por agente
- **Patrón:** Opcional
- DONDE un steering file tenga `applies_to: ["*"]` (o ausente), DEBE añadirse a `instructions[]` global. DONDE `applies_to` nombre sub-agentes específicos (e.g., `["implementer"]`), el steering file DEBE añadirse como `instructions` específicas de ese agente en `opencode.json#agent.<name>.instructions` (opencode) o como archivo adicional en el bloque de instrucciones del agente (claude, gemini).

### R5 — Scaffold de ejemplo: `steering/global-conventions.md`
- **Patrón:** Ubicuo
- El template DEBE incluir un archivo `steering/global-conventions.md` de ejemplo con frontmatter YAML (`name: global-conventions`, `description: "Convenciones globales del proyecto que aplican a todos los agentes"`, `applies_to: ["*"]`) y cuerpo con placeholders del estilo `<!-- TODO: definir convenciones -->`.

### R6 — Scaffold de ejemplo: `steering/implementer-patterns.md`
- **Patrón:** Ubicuo
- El template DEBE incluir un archivo `steering/implementer-patterns.md` de ejemplo con frontmatter YAML (`name: implementer-patterns`, `description: "Patrones de código y convenciones para el implementer"`, `applies_to: ["implementer"]`) y cuerpo con placeholders.

### R7 — Campo `_template_steering_examples` en `agentic.json`
- **Patrón:** Ubicuo
- El manifest DEBE incluir un campo `_template_steering_examples` con las referencias a los steering files de ejemplo (R5, R6). Este campo sigue el mismo convenio de underscore que `_template_subagents_examples`: es informativo, no se renderiza automáticamente, y se elimina con `remove-examples`.

### R8 — Bootstrap comando `add-steering`
- **Patrón:** Evento
- CUANDO se ejecute `./.agents/bootstrap.sh add-steering <name>`, el script DEBE crear un steering file desde el template en `steering/` con el frontmatter personalizado (name, description preguntados interactivamente o pasados por flags `--description` y `--applies-to`), y añadir la entrada al array `steering[]` de `agentic.json`. Si el directorio `steering/` no existe, DEBE crearlo.

### R9 — Bootstrap comando `remove-steering`
- **Patrón:** Evento
- CUANDO se ejecute `./.agents/bootstrap.sh remove-steering <name>`, el script DEBE eliminar la entrada del array `steering[]` de `agentic.json`. El archivo en disco en `steering/` NO DEBE eliminarse automáticamente (el usuario decide si conserva el archivo).

### R10 — Validación en `check.sh`
- **Patrón:** Ubicuo
- `./check.sh` DEBE incluir una sección «Steering Validation» que: (a) verifique que todos los archivos referenciados en `agentic.json#steering[].file` existen en disco; (b) verifique que cada archivo tiene un bloque YAML frontmatter válido con `name` y `description`; (c) advierta si hay archivos en `steering/` no referenciados en el manifest. Los errores DEBEN reportarse como ⚠️ (warning), no como ❌ (fail), porque el steering es opcional.

### R11 — Integración con el renderer de opencode
- **Patrón:** Ubicuo
- `render_opencode` en `.agents/adapters/_common/render.py` DEBE: (a) añadir los steering files globales (`applies_to: ["*"]`) al array `instructions` de `opencode.json`; (b) para steering files con `applies_to` específico, añadirlos al campo `instructions` dentro del objeto `agent.<name>` correspondiente, SI opencode soporta `instructions` a nivel de agente. Si no lo soporta, añadirlos al `instructions` global con un comentario en el prompt del agente indicando la asociación.

### R12 — Documentación en `AGENTS.md`
- **Patrón:** Ubicuo
- `AGENTS.md` DEBE incluir una referencia al concepto de steering en §2 (Repository Map), indicando que `steering/` contiene archivos que dirigen el comportamiento de los agentes y que `agentic.json#steering[]` los declara.

### R13 — Sin breaking changes
- **Patrón:** Ubicuo
- El campo `steering` en `agentic.json` DEBE ser opcional. Manifests existentes sin `steering` DEBEN seguir siendo válidos y renderizables. Si `steering` está ausente o es `[]`, el renderer DEBE comportarse exactamente como antes de este feature.

### R14 — Steering file template en `specs/templates/`
- **Patrón:** Ubicuo
- El directorio `specs/templates/` DEBE contener un archivo `steering.md` con la plantilla base para crear nuevos steering files: estructura YAML frontmatter + secciones sugeridas (Contexto, Convenciones, Anti-patrones, Ejemplos).

### R15 — Test de steering en `tests/`
- **Patrón:** Ubicuo
- DEBE existir un test `tests/test_steering.sh` ejecutable que: (a) verifique que `opencode.json#instructions[]` incluye los paths de los steering files globales declarados en `agentic.json#steering[]`; (b) verifique que los steering files existen en disco; (c) verifique que el YAML frontmatter de cada steering file es parseable.

### R16 — check.sh verde tras implementación
- **Patrón:** Evento
- CUANDO se complete la implementación, `./check.sh` DEBE pasar con exit 0, incluyendo la validación de steering (R10, R15).

## Trazabilidad con Criterios de Aceptación

| Criterio | Cubierto por |
|----------|--------------|
| Campo `steering` en el schema del manifest | R1 |
| Directorio y convención de archivos | R2, R14 |
| Renderer extiende instructions con steering | R3, R11 |
| Scope global vs. por agente | R4 |
| Ejemplos scaffold (global + implementer) | R5, R6 |
| Campo `_template_steering_examples` | R7 |
| Comandos bootstrap (add/remove steering) | R8, R9 |
| Validación en check.sh | R10, R15 |
| Documentación en AGENTS.md | R12 |
| Compatibilidad hacia atrás | R13 |
| Template en specs/templates/ | R14 |
| Test automatizado | R15 |
| Cierre limpio (check.sh verde) | R16 |
