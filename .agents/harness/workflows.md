# Workflows del Harness SDD

Flujos de trabajo predefinidos para las tareas más comunes en un proyecto Cloud/DevOps con SDD.

---

## 0. Spec Driven Development (SDD) — Feature Completa

**Trigger:** "Implementar feature [X]" (con `"sdd": true` en `feature_list.json`)

### Fase 0: Spec (spec_author / quality-agent)
1. Leer `feature_list.json` → detectar primera feature `pending` con `"sdd": true`
2. Leer `specs/README.md` y `specs/templates/`
3. Leer `docs/sdd.md` si se necesita contexto EARS
4. Crear `specs/<feature>/requirements.md` (EARS estricto, R1, R2, ...)
5. Crear `specs/<feature>/design.md` (arquitectura, alternativas, firmas)
6. Crear `specs/<feature>/tasks.md` (checklist T1, T2, ... con referencias R<n>)
7. Actualizar `feature_list.json`: `status: "spec_ready"`
8. **Parar** — notificar al humano que revise los specs en `specs/<feature>/`

### Fase 1: Gate Humano
1. Humano lee `specs/<feature>/{requirements,design,tasks}.md`
2. Si aprueba → continuar. Si pide cambios → corregir y volver a presentar.
3. Actualizar `feature_list.json`: `status: "in_progress"`

### Fase 2: Implementación (implementer / platform-engineer)
1. **Importante:** Cargar y aplicar la skill `terraform-structure` (`.agents/skills/terraform-structure/SKILL.md`) para determinar la estructura de carpetas y el uso de templates.
2. Ejecutar tasks.md secuencialmente, marcando `[x]` cada T<n>
3. Seguir el diseño definido en `design.md` e integrar los metadatos de los ficheros XML de arquitectura en los ficheros `terraform.tfvars`.
4. Commits tras cada task completada (opcional pero recomendado)

### Fase 3: Tests (tester-agent)
1. Implementar tests según tasks.md
2. Documentar trazabilidad `R<n> ↔ test` en `progress/impl_<feature>.md`
3. Verificar cobertura

### Fase 4: Review y Cierre (reviewer / quality-agent)
1. Verificar trazabilidad: cada R<n> tiene test, cada test cubre ≥1 R<n>
2. Ejecutar `./check.sh` — debe pasar limpio
3. Actualizar `feature_list.json`: `status: "done"`
4. Registrar en `progress/progress.md`

---

## 1. Nuevo Módulo Terraform

**Trigger:** "Crear módulo Terraform para [recurso AWS/GCP/Azure]"

1. **Spec phase:**
   - Si `sdd: true`: spec_author crea requirements/design/tasks
   - Si `sdd: false`: ir directamente a implementación
2. **Implementación:**
   - Crear `modules/<nombre>/main.tf`, `variables.tf`, `outputs.tf`
   - Seguir convenciones de naming del proyecto
   - Añadir `README.md` en el módulo con inputs, outputs y ejemplo
3. **Validación:**
   - `terraform fmt -check`
   - `terraform validate`
   - `terraform-docs` para generar documentación
4. **Tests:**
   - Terratest o Kitchen-Terraform para el módulo
5. **Cierre:**
   - `check.sh` verde
   - Actualizar feature_list.json

---

## 2. Pipeline CI/CD

**Trigger:** "Crear pipeline CI/CD para [componente]"

1. **Especificación:**
   - Definir triggers (push, PR, schedule)
   - Definir stages (lint, build, test, deploy, smoke)
   - Definir entornos (dev, staging, prod)
2. **Implementación:**
   - Crear `.github/workflows/` o `.gitlab-ci.yml` o `Jenkinsfile`
   - Integrar `check.sh` como quality gate
3. **Validación:**
   - Ejecutar pipeline en seco (dry-run)
   - Verificar que los secrets están correctamente referenciados
4. **Cierre:**
   - `check.sh` verde
   - PR con revisión humana

---

## 3. Bug Fix

**Trigger:** "Fix bug en [componente]"

1. **Reproducir (tester-agent):**
   - Escribir test que reproduce el bug
   - Confirmar que el test falla
2. **Fix (agente correspondiente):**
   - Bug infra → `platform-engineer`
   - Bug IaC → `cloud-architect`
   - Bug test → `tester-agent`
3. **Verificar (tester-agent):**
   - Confirmar que el test pasa
   - Añadir tests edge cases relacionados
4. **Review (quality-agent):**
   - Verificar que el fix no introduce regresiones
   - `check.sh` verde

---

## 4. Seguridad / Compliance

**Trigger:** "Auditar [componente] por [estándar]"

1. **Análisis (security-reviewer):**
   - Escanear con tools (checkov, tfsec, trivy, sonarqube)
   - Identificar hallazgos críticos
   - Clasificar por severidad
2. **Mitigación (platform-engineer):**
   - Corregir hallazgos en el código IaC
   - Añadir políticas de seguridad
   - Verificar que las correcciones no rompen funcionalidad
3. **Validación (security-reviewer):**
   - Re-escanear
   - Confirmar que todos los críticos están mitigados
4. **Documentación (escriba):**
   - Actualizar runbooks
   - Registrar decisiones en `progress/decisions.md`

---

## Checklist Universal Pre-Commit

Antes de cualquier commit:

```bash
# SDD + builds + tests + validations (vía check.sh)
./check.sh

# No secrets
git diff --cached | grep -i "password\|secret\|token\|api_key\|aws_access_key"

# Terraform sintaxis (si aplica)
terraform fmt -check -recursive
terraform validate

# No hardcoded credentials
grep -r "access_key" modules/ --include="*.tf" | grep -v "variable" || true
```
