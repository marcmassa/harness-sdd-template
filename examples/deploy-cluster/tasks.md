# Tareas — deploy-cluster

> Pasos discretos en orden. El implementador marca `[x]` al completar cada uno.

## Implementación

- [ ] **T1** — Crear `modules/aws-eks-cluster/variables.tf` con todos los inputs definidos en R1. Cubre: R1.
- [ ] **T2** — Crear `modules/aws-eks-cluster/vpc.tf` con VPC, subnets públicas/privadas, IGW, NAT Gateways y routing tables. Cubre: R2, R4.
- [ ] **T3** — Crear `modules/aws-eks-cluster/security-groups.tf` con reglas intra-cluster, LB→nodes y admin SSH. Cubre: R5.
- [ ] **T4** — Crear `modules/aws-eks-cluster/main.tf` con el recurso `aws_eks_cluster`, IAM role y dependencias de VPC+SGs. Cubre: R1, R2.
- [ ] **T5** — Crear `modules/aws-eks-cluster/irsa.tf` con OIDC provider condicional a `enable_irsa`. Cubre: R3.
- [ ] **T6** — Crear `modules/aws-eks-cluster/node-groups.tf` con soporte para managed y self-managed node groups. Cubre: R6.
- [ ] **T7** — Crear `modules/aws-eks-cluster/outputs.tf` con cluster endpoint, OIDC ARN, kubeconfig. Cubre: R3.
- [ ] **T8** — Crear `environments/dev/terraform.tfvars` y `environments/prod/terraform.tfvars` con ejemplos. Cubre: R2 (prod multi-AZ).
- [ ] **T9** — Añadir validación pre-fly en `variables.tf` (nombre ≤ 100 chars, versión K8s soportada, región con ≥ 3 AZs). Cubre: R8.

## Tests

- [ ] **T10** — Crear test unitario que verifica la creación del módulo con `terraform init` y `terraform validate`. Cubre: R1.
- [ ] **T11** — Crear test de integración que despliega el módulo en un sandbox AWS y verifica que el cluster se crea con 3 AZs en prod. Cubre: R2, R4.
- [ ] **T12** — Crear test que verifica que IRSA se crea solo cuando `enable_irsa=true`. Cubre: R3.
- [ ] **T13** — Crear test que verifica que `terraform plan` falla con nombre de cluster > 100 caracteres. Cubre: R8.

## Cierre

- [ ] **T14** — Documentar trazabilidad `R<n> ↔ test` en `progress/impl_deploy-cluster.md`. Cubre: trazabilidad.
- [ ] **T15** — Ejecutar `./check.sh` y verificar que todo pasa. Cubre: verificación final.
- [ ] **T16** — Actualizar `feature_list.json`: mover P1-001 a status "done". Cubre: cierre.
- [ ] **T17** — Registrar resumen en `progress/progress.md`. Cubre: registro.
