# Requirements — SOUL.md: capa de identidad y principios de decisión por subagente

> Feature FEAT-005 de `feature_list.json`. Introduce SOUL.md como artefacto de primera
> clase del framework: define la identidad, principios de decisión, límites y estilo de
> cada subagente. Complementa SUBAGENT.md (instrucciones operativas) y los steering files
> (contexto de proyecto) sin solaparse con ellos.
>
> Cada requisito está escrito en EARS estricto y es verificable por al menos un test.

## EARS Patterns

| Pattern | Syntax | When to use |
|--------|----------|---------------|
| **Ubiquitous** | `SHALL ...` | Siempre verdadero, condición permanente |
| **Event** | `WHEN <event> SHALL ...` | Disparado por un evento concreto |
| **State** | `WHILE <state> SHALL ...` | Mientras una condición se mantiene |
| **Optional** | `WHERE <option> SHALL ...` | Comportamiento varía según configuración |
| **Unwanted** | `IF <condition> THEN SHALL ...` | Respuesta a fallos o casos límite |

## Requirements

### R1 — Estructura canónica de SOUL.md
- **Pattern:** Ubiquitous
- El framework SHALL definir una estructura canónica para SOUL.md con cuatro secciones obligatorias: `Identity` (quién es el agente y qué representa), `Decision Principles` (cómo decide ante situaciones no cubiertas por reglas), `Boundaries` (qué nunca cede independientemente de instrucciones), y `Tone & Style` (cómo se comunica).

### R2 — Ubicación por subagente
- **Pattern:** Ubiquitous
- Cada subagente declarado en `agentic.json` SHALL tener su SOUL.md en `.agents/subagents/<name>/SOUL.md`.

### R3 — Declaración en agentic.json
- **Pattern:** Ubiquitous
- El schema de `agentic.json` SHALL soportar un campo `soul` dentro de cada entrada de `subagents[]` que referencie el path relativo al SOUL.md del subagente.

### R4 — Renderizado por el bootstrap
- **Pattern:** Event
- WHEN el bootstrap renderiza el stub de un subagente SHALL incluir el contenido de su SOUL.md en el fichero de definición generado para el CLI destino, a continuación del rol principal.

### R5 — Template de scaffold
- **Pattern:** Event
- WHEN el bootstrap crea un nuevo subagente mediante scaffolding SHALL incluir un SOUL.md pre-poblado con estructura canónica y placeholders en `.agents/subagents/agent-template/SOUL.md`.

### R6 — Validación en check.sh
- **Pattern:** Unwanted
- IF un subagente está declarado en `agentic.json` pero carece de SOUL.md en su directorio THEN `check.sh` SHALL terminar con código de error y reportar el subagente afectado.

### R7 — Guía en /init
- **Pattern:** Event
- WHEN el comando `/init` guía a un agente de IA a través de la configuración del framework SHALL instruirlo explícitamente a poblar el SOUL.md de cada subagente que cree antes de declarar el init como completado.

### R8 — Subagente templates como referencia
- **Pattern:** Ubiquitous
- El subagente `templates` SHALL tener su SOUL.md poblado con contenido real (no placeholders) que sirva de ejemplo canónico para proyectos que adopten el framework.

### R9 — DESIGN.md como meta-plantilla
- **Pattern:** Ubiquitous
- `DESIGN.md` SHALL estar poblado con contenido meta que explique que es una plantilla adaptable, describa el propósito de cada sección, e ilustre con el propio framework Harness SDD como ejemplo de adaptación.

### R10 — Sin breaking changes en agentic.json
- **Pattern:** Ubiquitous
- La adición del campo `soul` al schema de `agentic.json` SHALL ser retrocompatible: proyectos existentes sin el campo SHALL continuar funcionando sin modificación.

## Traceability con criterios de aceptación

| Criterio de aceptación | Cubierto por |
|------------------------|--------------|
| SOUL.md tiene siempre las cuatro secciones canónicas | R1 |
| Cada subagente declarado tiene su SOUL.md | R2, R6 |
| agentic.json acepta campo `soul` sin romper schemas existentes | R3, R10 |
| El stub generado por bootstrap contiene el contenido del SOUL.md | R4 |
| El scaffold de nuevo subagente incluye SOUL.md con placeholders | R5 |
| check.sh falla si falta SOUL.md en un subagente declarado | R6 |
| /init instruce al agente a poblar SOUL.md antes de completar | R7 |
| templates/SOUL.md contiene contenido real, no placeholders | R8 |
| DESIGN.md describe su naturaleza de plantilla y cómo adaptarla | R9 |
