# Requisitos — deploy-cluster

> Feature P1-001 del `feature_list.json`. Despliegue de un cluster EKS en AWS usando Terraform, con node groups gestionados, VPC dedicada, IRSA y security groups.
>
> Cada requirement está redactado en EARS estricto y es verificable por al menos un test concreto.

## Formato EARS

| Patrón | Sintaxis | Cuándo usarlo |
|--------|----------|---------------|
| **Ubicuo** | `DEBE ...` | Siempre es verdad |
| **Evento** | `CUANDO <evento> DEBE ...` | Solo cuando ocurre algo |
| **Estado** | `MIENTRAS <estado> DEBE ...` | Mientras se cumple una condición |
| **Opcional** | `DONDE <opción> DEBE ...` | Comportamiento que puede variar |
| **No deseado** | `SI <condición> ENTONCES DEBE ...` | Respuesta a fallos o casos edge |

## Requisitos

### R1 — Módulo Terraform EKS
- **Patrón:** Ubicuo
- DEBE existir un módulo Terraform `aws-eks-cluster` ubicado en `modules/aws-eks-cluster/` con los siguientes inputs: `cluster_name`, `environment`, `region`, `kubernetes_version`, `node_instance_types`, `node_min_size`, `node_max_size`, `node_desired_size`.

### R2 — Cluster HA multi-AZ
- **Patrón:** Evento
- CUANDO se ejecuta `terraform apply` con `environment=production`, DEBE crearse el cluster EKS con nodos distribuidos en al menos 3 zonas de disponibilidad.

### R3 — IRSA (IAM Roles for Service Accounts)
- **Patrón:** Estado
- MIENTRAS `enable_irsa = true`, DEBE crearse un OIDC provider asociado al cluster y DEBE existir un output `oidc_provider_arn` con el ARN del provider.

### R4 — VPC dedicada
- **Patrón:** Ubicuo
- DEBE crearse una VPC dedicada para el cluster con subnets públicas y privadas, un NAT Gateway por AZ en producción (o uno único si `single_nat_gateway = true`), y tablas de enrutamiento separadas.

### R5 — Security groups mínimos
- **Patrón:** Ubicuo
- DEBEN crearse security groups que permitan: tráfico intra-cluster en todos los puertos entre nodos del mismo grupo, tráfico TCP/443 desde los load balancers hacia los nodos, y tráfico SSH solo desde IPs de administración.

### R6 — Node groups gestionados
- **Patrón:** Opcional
- DONDE `node_group_type = "managed"`, DEBE usarse un AWS-managed node group. DONDE `node_group_type = "self_managed"`, DEBE usarse un auto-scaling group tradicional.

### R7 — Rollback seguro
- **Patrón:** No deseado
- SI `terraform apply` falla después de crear recursos intermedios, ENTONCES DEBE ejecutarse `terraform destroy` para limpiar los recursos creados parcialmente y DEBE mostrarse un mensaje de error claro.

### R8 — Validación pre-fly
- **Patrón:** Evento
- CUANDO se ejecuta `terraform plan`, DEBE validarse que: (a) el nombre del cluster no excede 100 caracteres, (b) la versión de Kubernetes es soportada por AWS, (c) la región indicada tiene 3 AZs como mínimo.

## Trazabilidad con acceptance criteria

| Acceptance criterion | Cubierto por |
|----------------------|--------------|
| Módulo Terraform con inputs definidos | R1 |
| Cluster multi-AZ en producción | R2 |
| IRSA + OIDC provider cuando enable_irsa=true | R3 |
| VPC con subnets públicas/privadas + NAT Gateway | R4 |
| Security groups mínimos (intra-cluster, LB, SSH) | R5 |
| Node groups gestionados vs auto-scaling | R6 |
| Rollback en caso de fallo parcial | R7 |
| Validación pre-fly de parámetros | R8 |
