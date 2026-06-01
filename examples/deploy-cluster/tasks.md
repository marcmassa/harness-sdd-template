# Tasks — deploy-cluster

> Discrete steps in order. The implementer marks `[x]` upon completing each one.

## Implementation

- [ ] **T1** — Create `modules/aws-eks-cluster/variables.tf` with all inputs defined in R1. Covers: R1.
- [ ] **T2** — Create `modules/aws-eks-cluster/vpc.tf` with VPC, public/private subnets, IGW, NAT Gateways, and routing tables. Covers: R2, R4.
- [ ] **T3** — Create `modules/aws-eks-cluster/security-groups.tf` with intra-cluster rules, LB→nodes, and admin SSH. Covers: R5.
- [ ] **T4** — Create `modules/aws-eks-cluster/main.tf` with the `aws_eks_cluster` resource, IAM role, and VPC+SGs dependencies. Covers: R1, R2.
- [ ] **T5** — Create `modules/aws-eks-cluster/irsa.tf` with OIDC provider conditional on `enable_irsa`. Covers: R3.
- [ ] **T6** — Create `modules/aws-eks-cluster/node-groups.tf` with support for managed and self-managed node groups. Covers: R6.
- [ ] **T7** — Create `modules/aws-eks-cluster/outputs.tf` with cluster endpoint, OIDC ARN, kubeconfig. Covers: R3.
- [ ] **T8** — Create `environments/dev/terraform.tfvars` and `environments/prod/terraform.tfvars` with examples. Covers: R2 (prod multi-AZ).
- [ ] **T9** — Add pre-flight validation in `variables.tf` (name ≤ 100 chars, supported K8s version, region with ≥ 3 AZs). Covers: R8.

## Tests

- [ ] **T10** — Create unit test that verifies module creation with `terraform init` and `terraform validate`. Covers: R1.
- [ ] **T11** — Create integration test that deploys the module in an AWS sandbox and verifies that the cluster is created with 3 AZs in prod. Covers: R2, R4.
- [ ] **T12** — Create test that verifies IRSA is created only when `enable_irsa=true`. Covers: R3.
- [ ] **T13** — Create test that verifies `terraform plan` fails with cluster name > 100 characters. Covers: R8.

## Closure

- [ ] **T14** — Document traceability `R<n> ↔ test` in `progress/impl_deploy-cluster.md`. Covers: traceability.
- [ ] **T15** — Run `./check.sh` and verify everything passes. Covers: final verification.
- [ ] **T16** — Update `feature_list.json`: move P1-001 to status "done". Covers: closure.
- [ ] **T17** — Log summary in `progress/progress.md`. Covers: log.
