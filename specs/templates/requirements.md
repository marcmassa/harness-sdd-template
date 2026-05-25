# Requisitos — {Nombre de la funcionalidad}

> Feature {id} del `feature_list.json`. {Descripción breve de la funcionalidad y su contexto}
>
> Cada requirement está redactado en EARS estricto y es verificable por al menos un test concreto.

## Formato EARS

| Patrón | Sintaxis | Cuándo usarlo |
|--------|----------|---------------|
| **Ubicuo** | `DEBE ...` | Siempre es verdad, condición permanente |
| **Evento** | `CUANDO <evento> DEBE ...` | Solo cuando ocurre un evento específico |
| **Estado** | `MIENTRAS <estado> DEBE ...` | Mientras se cumple una condición |
| **Opcional** | `DONDE <opción> DEBE ...` | Comportamiento que puede variar según configuración |
| **No deseado** | `SI <condición> ENTONCES DEBE ...` | Respuesta a fallos o casos edge |

## Requisitos

### R1 — {título corto}
- **Patrón:** {Ubicuo / Evento / Estado / Opcional / No deseado}
- {Redacción EARS del requisito}

### R2 — {título corto}
- **Patrón:** {patrón}
- {Redacción EARS}

### R3 — {título corto}
- **Patrón:** {patrón}
- {Redacción EARS}

### R4 — {título corto}
- **Patrón:** {patrón}
- {Redacción EARS}

### R5 — {título corto}
- **Patrón:** {patrón}
- {Redacción EARS}

## Trazabilidad con acceptance criteria

| Acceptance criterion | Cubierto por |
|----------------------|--------------|
| {Criterio 1} | R1, R3 |
| {Criterio 2} | R2 |
| {Criterio 3} | R4, R5 |
