# Design — deploy-cluster

> Technical decisions to implement the `aws-eks-cluster` module. Supported on project conventions.

## Summary

Create a reusable Terraform module to deploy a complete EKS cluster with VPC, node groups, IRSA, and security groups. The module follows the standard project structure: `main.tf`, `variables.tf`, `outputs.tf` in `modules/aws-eks-cluster/`.

## Affected Files

| File | Action | Reason |
|---------|--------|-------|
| `modules/aws-eks-cluster/main.tf` | create | Main EKS cluster resource |
| `modules/aws-eks-cluster/variables.tf` | create | Module inputs |
| `modules/aws-eks-cluster/outputs.tf` | create | Outputs (cluster endpoint, OIDC, kubeconfig) |
| `modules/aws-eks-cluster/vpc.tf` | create | VPC, subnets, NAT Gateways, routing |
| `modules/aws-eks-cluster/node-groups.tf` | create | Managed or self-managed node groups |
| `modules/aws-eks-cluster/security-groups.tf` | create | Security groups and rules |
| `modules/aws-eks-cluster/irsa.tf` | create | OIDC provider |
| `environments/dev/terraform.tfvars` | modify | Example variables for dev |
| `environments/prod/terraform.tfvars` | modify | Example variables for prod |
| `tests/test_eks_cluster.py` | create | Tests with Terratest |

## Module Structure

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

## Deployment Algorithm (terraform apply)

```
1. Create VPC with public/private subnets
2. Create Internet Gateway + NAT Gateways
3. Create routing tables and associations
4. Create security groups (intra-cluster, LB → nodes, admin SSH)
5. Create IAM role for EKS cluster
6. Create EKS cluster (depends on VPC + SGs)
7. Create OIDC provider if enable_irsa
8. Create node groups (managed or self-managed)
9. Configure aws-auth ConfigMap for access
```

## Error Handling

| Condition | Response |
|-----------|-----------|
| Overlapping VPC CIDR with existing | Fail with a clear message indicating the conflict |
| Unsupported K8s version | Validate in pre-flight against AWS version list |
| AZ limit exceeded | Validate that the region has ≥ 3 AZs in production |
| Error in cluster creation | Run `terraform destroy` of partially created resources |

## Discarded Alternative

**Use the EKS community module (`terraform-aws-modules/eks`).**
Discarded because:
- The community module abstracts too much, making fine-grained customization of security groups and node groups difficult.
- The project needs explicit control over the VPC (naming, tagging, custom routing).
- The community module changes interface between major versions, creating upgrade risk.
- We prefer our own simpler and more predictable module.

## Risks

- **AWS account limits:** EKS cluster creation can fail due to instance or IP limits. Document how to request limit increases.
- **Circular dependency:** The cluster security group references the nodes, and vice versa. Use `aws_ec2_tag` to avoid circular dependencies.
- **Creation time:** An EKS cluster takes 15-25 minutes to create. Integration tests must have adequate timeouts.
- **Cost:** NAT Gateway (~$32/month), EKS cluster (~$73/month), EC2 instances. Document estimated cost in the module's README.
