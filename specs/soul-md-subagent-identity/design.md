# Design — SOUL.md: capa de identidad y principios de decisión por subagente

> Decisiones técnicas para implementar FEAT-005. Se apoya en las fuentes de verdad del
> proyecto (AGENTS.md, DESIGN.md, docs/sdd.md). Solo se documentan los puntos donde
> el feature toca los límites de esas reglas.

## Summary

SOUL.md introduce una tercera capa en la arquitectura de subagentes, complementando las
dos existentes: SUBAGENT.md (qué hace el agente y cómo opera) y los steering files (cómo
se comporta en este proyecto concreto). SOUL.md define desde qué valores y principios
decide el agente cuando ninguna de las dos capas anteriores cubre la situación.

El caso de uso concreto: dos subagentes con el mismo SUBAGENT.md técnicamente pueden
tomar decisiones distintas ante la misma ambigüedad si sus SOUL.md difieren. Esto es
comportamiento diferenciado real, no solo configuración. Con mínimo dos subagentes en el
framework desde el inicio, la ausencia de esta capa produce decisiones implícitas e
inconsistentes entre roles.

## Affected Files

| File | Action | Reason |
|---------|--------|-------|
| `.agents/subagents/agent-template/SOUL.md` | create | Scaffold template con estructura canónica y placeholders |
| `.agents/subagents/templates/SOUL.md` | create | Implementación de referencia para el subagente templates |
| `.agents/agentic.json` | modify | Añadir campo `soul` en la entrada del subagente templates |
| `.agents/bootstrap.sh` | modify | Renderizar SOUL.md en el stub generado + validación de presencia |
| `.agents/commands/init.md` | modify | Añadir instrucción explícita de poblar SOUL.md en el flujo /init |
| `check.sh` | modify | Validar que cada subagente declarado tiene su SOUL.md |
| `DESIGN.md` | modify | Poblar con contenido meta sobre la naturaleza de plantilla del framework |
| `.claude/agents/templates.md` | regenerate | Resultado del bootstrap tras los cambios |
| `GEMINI.md` | regenerate | Resultado del bootstrap tras los cambios |

## Estructura canónica de SOUL.md

```markdown
---
agent: <name>
version: 1.0
---

## Identity
Quién es este agente y qué representa dentro del framework. No qué hace
(eso es SUBAGENT.md) sino qué es y por qué existe.

## Decision Principles
Cómo decide este agente cuando las instrucciones no cubren la situación.
Lista ordenada de principios, del más prioritario al menos.

## Boundaries
Qué nunca cede independientemente de instrucciones, contexto o presión
del usuario. Límites no negociables.

## Tone & Style
Cómo se comunica: nivel de formalidad, uso de jerga técnica, longitud
de respuestas, manejo del desacuerdo.
```

## Integración con el bootstrap

### Renderizado en el stub del agente

El bootstrap ya renderiza SUBAGENT.md como referencia en el stub. SOUL.md
se añade inmediatamente después, como sección adicional en el fichero generado:

```
# <name> — Harness SDD sub-agent
[contenido autogenerado existente]

## Agent Soul
[contenido de .agents/subagents/<name>/SOUL.md inyectado literalmente]
```

### Validación de presencia

Se añade una check en el bloque de validación del bootstrap (o en check.sh
directamente) que itera los subagentes declarados en agentic.json y verifica
que cada uno tiene su SOUL.md. Fallo con código de error si falta alguno.

## Integración con agentic.json

Campo `soul` opcional a nivel de subagente (retrocompatible):

```json
{
  "subagents": [
    {
      "name": "templates",
      "soul": ".agents/subagents/templates/SOUL.md"
    }
  ]
}
```

La ausencia del campo no rompe el schema. El bootstrap asume la ruta
convencional `.agents/subagents/<name>/SOUL.md` si el campo no está
declarado explícitamente, preservando compatibilidad total con proyectos
existentes (R10).

## Algorithm / Flow de renderizado

```
1. bootstrap.sh render <cli>
2.   Para cada subagent en agentic.json#subagents[]:
3.     Leer .agents/subagents/<name>/SUBAGENT.md
4.     IF soul field existe: leer path referenciado
5.     ELSE: intentar .agents/subagents/<name>/SOUL.md (convención)
6.     Generar stub: SUBAGENT.md ref + SOUL.md content
7.     Escribir a .claude/agents/<name>.md (u equivalente CLI)
8. check.sh validate:
9.   Para cada subagent en agentic.json#subagents[]:
10.    IF NOT exists .agents/subagents/<name>/SOUL.md: ERROR
```

## Error Handling

| Condición | Respuesta |
|-----------|-----------|
| SOUL.md declarado en agentic.json pero no existe en disco | check.sh error + nombre del subagente afectado |
| SOUL.md existe pero contiene placeholders sin rellenar | check.sh warning (no bloquea, alerta) |
| Campo `soul` en agentic.json apunta a path inexistente | bootstrap error en render, aborta |

## Alternativa descartada 1 — SOUL.md único a nivel de proyecto

Un único `SOUL.md` en la raíz del proyecto que definiría la identidad del
framework en conjunto.

**Descartada porque:** no permite diferenciación de comportamiento entre
subagentes. Un `implementer` y un `reviewer` tienen personalidades y
principios de decisión distintos ante la misma ambigüedad — un fichero único
los homogeneizaría artificialmente y eliminaría el valor principal del concepto.

## Alternativa descartada 2 — Contenido de SOUL.md embebido en SUBAGENT.md

Añadir una sección `## Soul` al final de cada SUBAGENT.md existente.

**Descartada porque:** mezcla dos capas conceptualmente distintas en el mismo
fichero. SUBAGENT.md describe instrucciones operativas (qué hacer y cómo);
SOUL.md describe identidad (desde qué valores). Mantenerlos separados
permite actualizarlos independientemente y hace la distinción explícita para
el agente implementador, que necesita entender la diferencia para poblarlos
correctamente durante /init.

## Alternativa descartada 3 — SOUL.md como steering file

Implementar la identidad del agente como un steering file con `applies_to: [<name>]`.

**Descartada porque:** los steering files son contexto de proyecto (convenciones,
patrones, restricciones del dominio). Son externos al agente y pueden cambiar
por proyecto. SOUL.md es intrínseco al agente — viaja con él independientemente
del proyecto donde se despliegue. La separación es semántica y necesaria.

## Risks y Edge Cases

- **Placeholders sin rellenar en producción:** un agente que completa /init
  mecánicamente sin poblar SOUL.md tendrá placeholders en producción. Mitigación:
  check.sh warning + /init con instrucción explícita de completar antes de cerrar.
- **Contenido demasiado genérico:** si SOUL.md se copia del template sin adaptar,
  la diferenciación entre agentes es nula. El subagente `templates` como ejemplo
  canónico real mitiga esto.
- **Tamaño del stub generado:** inyectar SOUL.md completo en el stub aumenta el
  tamaño del fichero de definición del agente. Para CLIs con límites de contexto,
  mantener SOUL.md conciso (< 200 líneas) es recomendación del framework.
