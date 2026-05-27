---
name: agent-template
type: subagent
user-invocable: true
description: "Subagente de ejemplo que sirve como plantilla para implementar más subagentes. Incluye la estructura y formato idóneos: frontmatter YAML, misión, tareas, herramientas, normas, directrices, integración y workflow."
model-agnostic: true
---

## Misión
[Describe aquí el propósito fundamental de este subagente: qué problema resuelve, qué área del proyecto cubre, y por qué es necesario.]

## Tareas principales

1. **[Área 1 — Nombre descriptivo]**:
   - [Acción concreta y medible 1].
   - [Acción concreta y medible 2].
   - [Acción concreta y medible 3].

2. **[Área 2 — Nombre descriptivo]**:
   - [Acción concreta y medible 1].
   - [Acción concreta y medible 2].

3. **[Área 3 — Nombre descriptivo]**:
   - [Acción concreta y medible 1].
   - [Acción concreta y medible 2].
   - [Acción concreta y medible 3].

4. **[Área 4 — Nombre descriptivo]**:
   - [Acción concreta y medible 1].

## Herramientas disponibles
- `[ruta/archivo]` — [Descripción de cuándo y cómo usarlo]
- `[ruta/archivo]` — [Descripción de cuándo y cómo usarlo]
- `[ruta/archivo]` — [Descripción de cuándo y cómo usarlo]

## Normas de estilo
- **Harness Compliance**: Este agente opera bajo el marco del **Harness SDD**. Debe consultar siempre `AGENTS.md`, `feature_list.json` y `progress/current.md` antes de actuar.
- **Modular Skills**: No debe reinventar flujos estándar. Debe verificar la existencia de habilidades en `.agents/skills/` y, si no existen, sincronizarlas usando `./.agents/skills/sync-skills.sh`.
- **[Norma 3]**: [Descripción de la norma y cómo aplicarla].

## Directrices
- **Harness First**: Toda acción debe ser trazable en el SDD y validada mediante `./check.sh`.
- **Skills Oriented**: Si la tarea implica tecnologías estándar (Terraform, K8s, Cloud), debe priorizar el uso de las instrucciones definidas en las *skills* descargadas.
- [Directriz 3: comportamiento o restricción importante].

## Integración con otros subagentes
- **[Otro subagente]**: [Cómo colaboran, qué información intercambian, en qué orden trabajan].
- **[Otro subagente]**: [Cómo colaboran, qué información intercambian, en qué orden trabajan].

## Workflow
1. [Paso 1 del flujo de trabajo típico].
2. [Paso 2 del flujo de trabajo típico].
3. [Paso 3 del flujo de trabajo típico].
4. [Paso 4 del flujo de trabajo típico].
5. [Paso 5 del flujo de trabajo típico].

---

*Copia este directorio completo (`.agents/subagents/agent-template/`) como base para crear nuevos subagentes. Renombra la carpeta y ajusta los campos del frontmatter YAML, la misión, tareas y el resto de secciones según el rol del nuevo agente.*
