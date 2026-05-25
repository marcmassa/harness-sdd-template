# Diseño — deploy-cluster

> Decisiones técnicas para implementar el módulo `aws-eks-cluster`. Apoyado en las convenciones del proyecto.

## Resumen

Crear un módulo Terraform reutilizable para desplegar un cluster EKS completo con VPC, node groups, IRSA y security groups. El módulo sigue la estructura estándar del proyecto: `main.tf`, `variables.tf`, `outputs.tf` en `modules/aws-eks-cluster/`.

## Archivos afectados

| Archivo | Acción | Razón |
|---------|--------|-------|
| `modules/aws-eks-cluster/main.tf` | crear | Recurso principal del cluster EKS |
| `modules/aws-eks-cluster/variables.tf` | crear | Inputs del módulo |
| `modules/aws-eks-cluster/outputs.tf` | crear | Outputs (cluster endpoint, OIDC, kubeconfig) |
| `modules/aws-eks-cluster/vpc.tf` | crear | VPC, subnets, NAT Gateways, routing |
| `modules/aws-eks-cluster/node-groups.tf` | crear | Node groups gestionados o self-managed |
| `modules/aws-eks-cluster/security-groups.tf` | crear | Security groups y reglas |
| `modules/aws-eks-cluster/irsa.tf` | crear | OIDC provider |
| `environments/dev/terraform.tfvars` | modificar | Variables de ejemplo para dev |
| `environments/prod/terraform.tfvars` | modificar | Variables de ejemplo para prod |
| `tests/test_eks_cluster.py` | crear | Tests con Terratest |

## Estructura del módulo

```hcl
module "aws-eks-cluster" {
  source = "../../modules/aws-eks-cluster"

  cluster_name        = var.cluster_name
  environment         = var.environment
  region              = var.region
  kubernetes_version  = var.kubernetes_version
  node_instance_types = var.node_instance_types

  # Networking
  vpc_cidr               = var.vpc_cidr
  availability_zones     = var.availability_zones
  single_nat_gateway     = var.single_nat_gateway

  # Node groups
  node_group_type    = var.node_group_type
  node_min_size      = var.node_min_size
  node_max_size      = var.node_max_size
  node_desired_size  = var.node_desired_size

  # Security
  enable_irsa          = var.enable_irsa
  admin_cidr_blocks    = var.admin_cidr_blocks

  tags = var.tags
}
```

## Algoritmo de despliegue (terraform apply)

```
1. Crear VPC con subnets públicas/privadas
2. Crear Internet Gateway + NAT Gateways
3. Crear tablas de enrutamiento y asociaciones
4. Crear security groups (intra-cluster, LB → nodes, admin SSH)
5. Crear IAM role para EKS cluster
6. Crear cluster EKS (depende de VPC + SGs)
7. Crear OIDC provider si enable_irsa
8. Crear node groups (gestionados o self-managed)
9. Configurar aws-auth ConfigMap para acceso
```

## Manejo de errores

| Condición | Respuesta |
|-----------|-----------|
| VPC CIDR superpuesto con existente | Fallar con mensaje claro indicando el conflicto |
| Versión K8s no soportada | Validar en pre-fly contra lista de versiones AWS |
| Límite de AZs excedido | Validar que la región tiene ≥ 3 AZs en producción |
| Error en creación de cluster | Hacer `terraform destroy` de recursos creados parcialmente |

## Alternativa descartada

**Usar el módulo community de EKS (`terraform-aws-modules/eks`).**
Se descarta porque:
- El módulo community abstrae demasiado, dificultando la personalización fina de security groups y node groups
- El proyecto necesita control explícito sobre la VPC (naming, tagging, routing personalizado)
- El módulo community cambia de interfaz entre versiones mayores, generando riesgo de upgrade
- Preferimos un módulo propio más simple y predecible

## Riesgos

- **Límites de cuenta AWS:** La creación de cluster EKS puede fallar por límites de instancias o IPs. Documentar cómo solicitar aumentos de límite.
- **Dependencia circular:** El security group del cluster referencia los nodes, y viceversa. Usar `aws_ec2_tag` para evitar dependencias circulares.
- **Tiempo de creación:** Un cluster EKS tarda 15-25 minutos en crearse. Los tests de integración deben tener timeouts adecuados.
- **Coste:** NAT Gateway (~$32/mes), cluster EKS (~$73/mes), instancias EC2. Documentar coste estimado en el README del módulo.
