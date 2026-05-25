# Convención de Uso del Harness SDD

## Propósito

Establecer la guía para que cualquier agente (IA o humano) que trabaje en este repositorio use el harness de forma consistente.

## Reglas Obligatorias

1. **Clasifica la tarea primero.** Usa `ROUTING.md` para determinar qué agente(s) usar.
2. **Lee el contexto.** Siempre lee `AGENTS.md`, `feature_list.json` y `progress/current.md` antes de empezar.
3. **Una feature a la vez.** `check.sh` rechazará más de un `in_progress`.
4. **No saltes el spec.** Si `sdd: true`, pasa por spec_author → humano → implementación.
5. **check.sh es el gateway.** No declares `done` sin que pase limpio.
6. **Documenta en disco.** Todo avance en `progress/current.md`. Al cerrar, resumen en `progress/progress.md`.

## Flujo Recomendado

```
1. ./check.sh                            # Verificar que el entorno está listo
2. Leer feature_list.json                 # Identificar siguiente feature
3. Leer progress/current.md               # Contexto de la sesión
4. Leer specs/<feature>/ (si aplica)      # Spec aprobado
5. Ejecutar tasks.md                       # Implementación secuencial
6. ./check.sh                              # Verificación final
7. Actualizar feature_list.json            # Marcar done
8. Registrar en progress/progress.md       # Cierre
```

## Checklist de Recomendaciones

Antes de ejecutar tareas complejas:

- [ ] ¿He clasificado la tarea usando ROUTING.md?
- [ ] ¿He leído feature_list.json para entender el estado?
- [ ] ¿He consultado progress/current.md para contexto?
- [ ] ¿He verificado que no hay otra feature en in_progress?
- [ ] ¿Ejecutaré `./check.sh` antes de declarar done?
