# Diseño — {Nombre de la funcionalidad}

> Decisiones técnicas para implementar la feature {id}. Apoyado en las fuentes de verdad del proyecto (AGENTS.md, docs/). Solo se documentan los puntos donde la feature roza la frontera de esas reglas.

## Resumen

{1-2 párrafos explicando qué hace esta funcionalidad y por qué es necesaria}

## Archivos afectados

| Archivo | Acción | Razón |
|---------|--------|-------|
| `ruta/al/archivo.tf` | crear | {razón} |
| `ruta/al/archivo_test.go` | crear | {razón} |
| `ruta/al/archivo.py` | modificar | {razón} |

## Firmas y estructuras

### Terraform
```hcl
module "example" {
  source = "./modules/example"
  # inputs
  name        = string
  environment = optional(string, "dev")
  tags        = optional(map(string), {})
}
```

### Python / Go / TypeScript
*[Especificar firmas de funciones, clases o interfaces según el lenguaje del proyecto]*

```python
# module.function — descripción
def funcion(param: str) -> dict: ...
```

## Algoritmo / Flujo

```
1. {paso 1 — validación de inputs}
2. {paso 2 — creación de recurso principal}
3. {paso 3 — configuración de dependencias}
4. {paso 4 — verificación y outputs}
```

## Manejo de errores

| Condición | Respuesta |
|-----------|-----------|
| {error case 1} | {comportamiento esperado} |
| {error case 2} | {comportamiento esperado} |

## Alternativa descartada

{Explicar qué otra aproximación se consideró y por qué se descartó. Mínimo una alternativa.}

## Riesgos y edge cases

- {riesgo 1 — impacto y mitigación}
- {riesgo 2 — impacto y mitigación}
- {edge case 1 — comportamiento esperado}
