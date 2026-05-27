# Skills

Este directorio contiene las **skills** (habilidades) de los agentes. Para mantener la plantilla agnóstica, las skills se gestionan de forma centralizada en el [Agent Skills Registry](https://gitlab.devops.onesait.com/onesait/technology/devops/infrastructure/agent-skills-registry.git).

## Cómo obtener/actualizar skills

Ejecuta el script de sincronización para descargar las últimas versiones de las skills estándar:

```bash
./.agents/skills/sync-skills.sh
```

## Propósito

Las skills permiten extender las capacidades de los agentes de Gemini CLI mediante:
- **Flujos de trabajo especializados:** Instrucciones detalladas para tareas comunes.
- **Integraciones de herramientas:** Configuraciones para interactuar con herramientas específicas.
- **Conocimiento del dominio:** Guías sobre arquitectura, convenciones o tecnologías particulares del proyecto.

## Estructura

Cada skill reside en su propio subdirectorio, conteniendo un archivo `SKILL.md` con sus instrucciones y recursos.
