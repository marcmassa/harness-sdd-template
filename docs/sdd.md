# Spec Driven Development (SDD) — Documentación completa

> Este documento describe en detalle el proceso SDD implementado en el proyecto.
> Es la referencia completa para spec_authors, implementers y reviewers.

---

## 1. Filosofía

SDD (Spec Driven Development) es un proceso en el que **los requisitos, el diseño y las tareas se escriben y aprueban antes de escribir una sola línea de código**. Esto contrasta con enfoques como:

- **Code-first:** el agente escribe código directamente y luego se revisa
- **Chat-driven:** los requisitos existen solo en la conversación, no en disco

SDD prioriza la **trazabilidad** y la **aprobación humana temprana** sobre la velocidad de escritura de código. El resultado es código de mayor calidad, con menos iteraciones y con un registro permanente de por qué se hizo cada cosa.

## 2. El ciclo SDD en detalle

### 2.1 pending → spec_ready

**Entrada:** Una feature en `feature_list.json` con `status: "pending"` y `"sdd": true`.

**Quién:** El agente `spec_author` (típicamente un agente de calidad/code-quality).

**Qué produce:**
- `specs/<feature-name>/requirements.md` — requisitos en EARS
- `specs/<feature-name>/design.md` — decisiones técnicas
- `specs/<feature-name>/tasks.md` — checklist ejecutable

**Reglas:**
- El spec_author NO escribe código. Solo escribe specs.
- El spec_author lee `specs/templates/` y `docs/sdd.md` antes de empezar.
- El nombre de la carpeta en `specs/` debe coincidir con `name` en `feature_list.json`.
- Cada archivo sigue las plantillas en `specs/templates/`.
- Al terminar, actualiza `feature_list.json`: `status: "spec_ready"`.

### 2.2 spec_ready → ⏸ Humano

**Entrada:** Feature con `status: "spec_ready"` y archivos en `specs/<feature-name>/`.

**Quién:** Un humano (tech lead, SRE, cloud architect).

**Qué revisa:**
- `requirements.md`: ¿Los requisitos cubren todos los casos? ¿Son verificables? ¿Usan EARS correctamente?
- `design.md`: ¿La arquitectura es correcta? ¿Las alternativas descartadas tienen sentido? ¿Los riesgos están cubiertos?
- `tasks.md`: ¿Las tareas están en orden lógico? ¿Cada R<n> tiene test?

**Resultado:**
- **Aprobar** → cambiar `status: "in_progress"` y lanzar implementación.
- **Solicitar cambios** → el spec_author corrige y vuelve a presentar.

### 2.3 in_progress → done

**Entrada:** Feature con `status: "in_progress"`.

**Quién:** El `implementer` y el `tester-agent`.

**Flujo:**
1. El implementer ejecuta `tasks.md` de arriba a abajo, marcando `[x]`.
2. Por cada tarea de implementación: escribe código, configuración o infraestructura.
3. Por cada tarea de test: escribe tests que verifican los R<n> referenciados.
4. Documenta la trazabilidad `R<n> ↔ test` en `progress/impl_<feature>.md`.
5. Ejecuta `./check.sh` — debe pasar limpio.
6. El **reviewer** (humano o quality-agent) verifica:
   - Todas las tasks están marcadas `[x]`.
   - Cada R<n> tiene al menos un test.
   - `check.sh` pasa.
   - No hay efectos secundarios no documentados.
7. Si aprueba → `status: "done"`, registrar en `progress/progress.md`.

## 3. EARS — Easy Approach to Requirements Syntax

### 3.1 Los 5 patrones

| Patrón | Cuándo | Sintaxis | Ejemplo (Cloud) |
|--------|--------|----------|-----------------|
| **Ubicuo** | La condición es siempre verdad | `DEBE <acción>` | `DEBE existir un módulo Terraform aws-eks-cluster` |
| **Evento** | La acción se dispara por un evento | `CUANDO <evento> DEBE <acción>` | `CUANDO se ejecuta terraform apply DEBE crearse el cluster` |
| **Estado** | La acción depende de un estado continuo | `MIENTRAS <estado> DEBE <acción>` | `MIENTRAS enable_irsa = true DEBE asociarse un OIDC provider` |
| **Opcional** | El comportamiento varía por configuración | `DONDE <opción> DEBE <acción>` | `DONDE environment = production DEBE usarse 3 AZs` |
| **No deseado** | Respuesta a fallos o condiciones inesperadas | `SI <condición> ENTONCES DEBE <acción>` | `SI terraform plan detecta destrucción DEBE abortar` |

### 3.2 Reglas duras EARS

1. **Cada requirement tiene un id único y estable:** `R1`, `R2`, ...
2. **Cada requirement es verificable por al menos un test.**
3. **Un requirement = un DEBE.** No mezcles varios DEBE en la misma frase.
4. **Solo DEBE / NO DEBE.** No uses "podría", "puede", "soporta", "debería".
5. **El orden importa:** R1 antes de R2 si hay dependencia lógica.

### 3.3 Ejemplos EARS para Cloud/DevOps

```markdown
## R1 — (Ubicuo)
DEBE existir un módulo Terraform `aws-vpc` con los parámetros:
`vpc_cidr`, `environment`, `azs`, `enable_nat_gateway`, `tags`.

## R2 — (Evento)
CUANDO se ejecuta `terraform apply` con `environment=production`,
DEBE crearse un VPC con subnets públicas en 3 AZs y un NAT Gateway por AZ.

## R3 — (Estado)
MIENTRAS `enable_nat_gateway = true`, DEBE crearse un NAT Gateway
en cada subnet pública con una Elastic IP asociada.

## R4 — (Opcional)
DONDE `single_nat_gateway = true`, DEBE crearse un único NAT Gateway
en lugar de uno por AZ, independientemente del valor de `enable_nat_gateway`.

## R5 — (No deseado)
SI el `terraform plan` detecta que se va a eliminar un recurso existente
con `prevent_destroy = true`, ENTONCES DEBE abortar la ejecución y mostrar
un mensaje de error claro.
```

## 4. Trazabilidad

### 4.1 Mapa R<n> → test

El implementador documenta la trazabilidad en `progress/impl_<feature>.md`:

```markdown
## Trazabilidad R<n> ↔ Test

| Requisito | Test | Tipo | Archivo |
|-----------|------|------|---------|
| R1 | test_vpc_created_with_correct_cidr | unit | tests/test_vpc.py |
| R2 | test_production_creates_3_azs | integration | tests/test_vpc.py |
| R3 | test_nat_gateway_created_when_enabled | unit | tests/test_vpc.py |
| R4 | test_single_nat_gateway_when_flag_set | unit | tests/test_vpc.py |
| R5 | test_abort_on_destructive_plan | integration | tests/test_vpc.py |
```

### 4.2 Verificación del revisor

El revisor comprueba:

1. **Completitud:** Cada R<n> tiene al menos un test en la tabla.
2. **Cobertura:** Cada test listado existe realmente y pasa.
3. **Idoneidad:** El test verifica exactamente lo que dice el requirement (no un proxy).
4. **check.sh:** El script pasa limpio.

## 5. Anti-patrones

### ❌ Spec sin alternativas descartadas
El `design.md` debe incluir **al menos una alternativa descartada**. Si no la tiene, el spec_author no ha pensado suficientes opciones.

### ❌ Requirements no verificables
`R1: El sistema DEBE ser rápido` no es verificable. ¿Qué significa "rápido"? ¿< 1s? ¿< 100ms? ¿Bajo qué carga?

### ❌ Tasks que no referencian R<n>
Toda task debe referenciar al menos un R<n>. Si una task no cubre ningún requisito, ¿por qué existe?

### ❌ Mezclar features en el mismo spec
Un spec cubre UNA feature. Si dos features están relacionadas pero pueden implementarse por separado, crea specs separados y gestiona dependencias en `progress/backlog.md`.

### ❌ Implementar sin aprobación
Si el spec está en `spec_ready` pero el humano no ha aprobado, NO se escribe código. El spec_author espera.

## 6. FAQ

### ¿Puedo tener specs para features que no son sdd:true?
Técnicamente sí, pero el proceso no las valida ni exige su presencia. Para features complejas aunque no sean sdd, se recomienda escribirlas igualmente.

### ¿Qué hago si una feature cambia durante la implementación?
Si el cambio es pequeño, actualiza el `tasks.md` y documenta en `progress/impl_<feature>.md`. Si el cambio es grande (nuevos requisitos R6+ o cambio de arquitectura), para, actualiza el spec y pasa por aprobación humana otra vez.

### ¿Y si el revisor es un agente IA?
El revisor IA verifica trazabilidad y completitud de tasks. La aprobación final (humana) sigue siendo necesaria para el spec. El revisor IA es complementario, no sustituto.

### ¿Cuándo uso sdd: false?
Para tareas triviales: typos, cambios de nombre, actualizaciones de dependencias, refactors puramente mecánicos. Si hay duda, usa `sdd: true`.
