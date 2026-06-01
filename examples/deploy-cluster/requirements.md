# Requirements — deploy-cluster

> Feature P1-001 from `feature_list.json`. Deploys an EKS cluster on AWS using Terraform, with managed node groups, dedicated VPC, IRSA, and security groups.
>
> Each requirement is written in strict EARS and is verifiable by at least one concrete test.

## EARS Format

| Pattern | Syntax | When to use |
|--------|----------|---------------|
| **Ubiquitous** | `SHALL ...` | Always true |
| **Event** | `WHEN <event> SHALL ...` | Only when something happens |
| **State** | `WHILE <state> SHALL ...` | While a condition holds |
| **Optional** | `WHERE <option> SHALL ...` | Behavior that can vary |
| **Unwanted** | `IF <condition> THEN SHALL ...` | Response to failures or edge cases |

## Requirements

### R1 — Terraform EKS Module
- **Pattern:** Ubiquitous
- A Terraform module `aws-eks-cluster` SHALL exist under `modules/aws-eks-cluster/` with the following inputs: `cluster_name`, `environment`, `region`, `kubernetes_version`, `node_instance_types`, `node_min_size`, `node_max_size`, `node_desired_size`.

### R2 — HA Multi-AZ Cluster
- **Pattern:** Event
- WHEN `terraform apply` runs with `environment=production`, an EKS cluster SHALL be created with nodes distributed across at least 3 availability zones.

### R3 — IRSA (IAM Roles for Service Accounts)
- **Pattern:** State
- WHILE `enable_irsa = true`, an OIDC provider SHALL be created associated with the cluster, and an output `oidc_provider_arn` SHALL exist with the provider's ARN.

### R4 — Dedicated VPC
- **Pattern:** Ubiquitous
- A dedicated VPC SHALL be created for the cluster with public and private subnets, one NAT Gateway per AZ in production (or a single one if `single_nat_gateway = true`), and separate routing tables.

### R5 — Minimum Security Groups
- **Pattern:** Ubiquitous
- Security groups SHALL be created that allow: intra-cluster traffic on all ports between nodes of the same group, TCP/443 traffic from load balancers to the nodes, and SSH traffic only from administration IPs.

### R6 — Managed Node Groups
- **Pattern:** Optional
- WHERE `node_group_type = "managed"`, an AWS-managed node group SHALL be used. WHERE `node_group_type = "self_managed"`, a traditional auto-scaling group SHALL be used.

### R7 — Safe Rollback
- **Pattern:** Unwanted
- IF `terraform apply` fails after creating intermediate resources, THEN `terraform destroy` SHALL run to clean up partially created resources, and a clear error message SHALL be displayed.

### R8 — Pre-flight Validation
- **Pattern:** Event
- WHEN `terraform plan` runs, validation SHALL occur that: (a) the cluster name does not exceed 100 characters, (b) the Kubernetes version is supported by AWS, (c) the indicated region has at least 3 AZs.

## Traceability with acceptance criteria

| Acceptance criterion | Covered by |
|----------------------|--------------|
| Terraform module with defined inputs | R1 |
| Multi-AZ cluster in production | R2 |
| IRSA + OIDC provider when enable_irsa=true | R3 |
| VPC with public/private subnets + NAT Gateway | R4 |
| Minimum security groups (intra-cluster, LB, SSH) | R5 |
| Managed vs auto-scaling node groups | R6 |
| Rollback on partial failure | R7 |
| Pre-flight validation of parameters | R8 |
