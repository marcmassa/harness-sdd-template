# Requirements — Hybrid team stable release

> FEAT-010 · 2026-11-09 · Status: spec_ready, pending human approval.
> Audience: maintainers, human reviewers, and implementing agents.
> Decision: approve one sequential initiative taking the framework from its
> current template baseline to an evidenced stable 1.0 release.
> Syntax: strict EARS; each R has one SHALL obligation.

## Context and goals

The canonical manifest, deterministic adapters, SDD documents, and lifecycle
hooks already exist. The review found a broken profile command, an error hidden
by a test, permissive quality checks, and documentation promising enforcement
that is not implemented. Team approval, ownership, and release evidence need
explicit contracts. The staged-file token hook is completed maintenance and
is a regression dependency, not unfinished work in this initiative.

Deliver reliable bootstrap and validation, proportionate human/AI governance,
verifiable approval and evidence, safe handoffs, maintainable distribution,
and real pilot evidence before calling the product stable.

## Scope boundaries

- Keep the framework local-first, Git-based, CLI-agnostic, and standard-library
  Python plus Bash. No hosted orchestration service or agent identity provider.
- Automate evidence completeness; humans assess its adequacy.
- Preserve five adapter entry points without claiming identical capabilities.
- Do not modify an adopted project's workflow or discard template scaffolds
  merely to initialize this framework's own development repository.
- FEAT-009 remains independently spec_ready. Native plugin packaging requires
  its own approval and compatibility review; it is not implicitly authorized.
- Native marketplace publication is optional for 1.0; portable distribution is
  mandatory. Actual publication needs the maintainer's explicit release action.

## M1 — Reliable base

### R1 — Profile reliability (Event)
WHEN profile runs against supported fresh, partial, and initialized fixtures,
the bootstrap SHALL return a complete report with exit status zero.

### R2 — Detection errors remain visible (Unwanted)
IF stack detection in a test raises an unexpected error, THEN the test SHALL
fail with an actionable diagnostic instead of treating the stack as absent.

### R3 — Mandatory failures block (Unwanted)
IF a mandatory configured check fails or its required executable is missing,
THEN check.sh SHALL return nonzero.

### R4 — Explicit check outcomes (Ubiquitous)
The verification gateway SHALL report each selected check as PASS, FAIL, or
SKIP with a reason, distinguishing required checks from optional checks.

### R5 — Reproducible lifecycle (Event)
WHEN the exported template is bootstrapped, initialized, rendered twice,
validated, and cleaned in an isolated fixture, the integration suite SHALL
verify preserved user files and deterministic framework output.

### R6 — CI baseline (Ubiquitous)
The CI configuration SHALL execute the mandatory suite on Ubuntu and macOS
with Python 3.10 and 3.13, including the staged-file token hook tests.

## M2 — Human/AI operating contract

### R7 — Explicit authority (Ubiquitous)
The team policy SHALL define human ownership and authorization for scope,
spec approval, implementation, technical review, merge, and publication.

### R8 — Proportionate workflow (State)
WHILE a work item is classified as lightweight, the workflow SHALL require a
recorded scope, risk rationale, acceptance evidence, and a closing review.

### R9 — Full SDD protection (State)
WHILE a work item is classified as full SDD, the workflow SHALL require
approval of requirements and design before implementation.

### R10 — Exceptions are accountable (Event)
WHEN an exception or scope change is accepted, the workflow SHALL record
its reason, human authorizer, affected controls, and reapproval decision.

## M3 — Verifiable SDD

### R11 — State machine (Event)
WHEN a supported command requests a state transition, the shared workflow
validator SHALL reject transitions whose prerequisites are not met.

### R12 — Versioned approval (Event)
WHEN full SDD approval is recorded, the approval record SHALL bind the
review decision to a deterministic digest of requirements.md and design.md.

### R13 — Stale approval (Unwanted)
IF approved requirements or design change, THEN implementation and completion
validation SHALL fail until a new approval is recorded.

### R14 — Task progress remains mutable (Event)
WHEN only task completion markers change, approval validation SHALL preserve
the existing requirements/design approval.

### R15 — Approval trust boundary (State)
WHERE repository-backed approval is required, the closing gate SHALL require
a trusted CI verification result tied to the reviewed revision rather than
accepting a self-declared local identity as authenticated human approval.

### R16 — Evidence completeness (State)
WHILE a full SDD feature is being completed, its evidence validator SHALL
require an existing automated test reference or reviewed manual evidence for
every declared requirement identifier.

### R17 — Closing gate (Event)
WHEN completion is requested, the workflow SHALL reject unfinished required
tasks, failed mandatory checks, stale evidence, or missing required review.

## M4 — Shared work and recovery

### R18 — Work ownership (Ubiquitous)
Each active work record SHALL identify its feature, owner, branch or worktree,
dependencies, revision, and latest handoff.

### R19 — Conflicting work claims (Unwanted)
IF a work claim conflicts with an active claim under the configured policy,
THEN the workflow SHALL reject it without silently replacing the existing owner.

### R20 — Handoff completeness (Event)
WHEN work is handed off, the record SHALL include objective, changes, check
results, pending decisions, and an executable next action.

### R21 — Controlled recovery (Event)
WHEN an abandoned claim is reassigned, the workflow SHALL preserve the prior
claim and record the human-authorized reassignment.

### R22 — Trust labels (Ubiquitous)
The team instructions SHALL distinguish project policy, approved specs,
external source data, and unapproved agent proposals.

## M5 — Distribution and maintenance

### R23 — Versioned formats (Ubiquitous)
The framework SHALL declare its release version, manifest format version,
work-record format version, and supported compatibility ranges.

### R24 — Safe updates (Event)
WHEN a framework update is planned, the updater SHALL produce a non-mutating
per-file add/replace/conflict/remove plan based on the installed inventory.

### R25 — Transactional update (Event)
WHEN a reviewed update plan is applied, the updater SHALL preserve user-owned
and modified files through conflict handling and a recoverable backup.

### R26 — Narrow ownership (Ubiquitous)
Generation, protection, cleanup, and removal SHALL target inventory-owned paths
rather than treating complete tool configuration directories as framework-owned.

### R27 — Honest adapter capabilities (Ubiquitous)
The compatibility matrix SHALL identify instructions, commands, enforceable
controls, unsupported behavior, and validation evidence for each adapter.

### R28 — Maintainable documentation (Ubiquitous)
The documentation SHALL provide a short navigation entry, contributor setup,
human/AI policy, maintenance instructions, migration/rollback procedures, and
release ownership without claiming unverified guarantees.

### R29 — File size regression (Unwanted)
IF a newly changed authored text file exceeds 20,000 bytes, THEN repository
validation SHALL reject it using the same estimation and exclusions as the
pre-commit hook.

## M6 — Demonstrated stable release

### R30 — Real pilot evidence (State)
WHILE stable release readiness is evaluated, the release checklist SHALL
require reviewed reports from two real pilot contexts, one small team and one
multi-person, multi-tool team, covering installation, review, handoff, update,
and recovery with baseline measurements and unresolved issues.

### R31 — Stable readiness (Event)
WHEN version 1.0 is proposed, the release validator SHALL reject readiness
without all milestone evidence, green mandatory CI, a resolved compatibility
matrix, reviewed pilot reports, and zero unresolved release-blocking defects.

### R32 — Publication authority (Event)
WHEN release readiness succeeds, the workflow SHALL leave public tagging,
package/marketplace publication, and announcements pending explicit maintainer
authorization for the concrete release artifacts.

## Acceptance and verification map

Tests below are planned, not claimed as existing. Automated checks establish
structure and reproducibility; human review establishes policy adequacy and
pilot authenticity. Evidence for a non-software requirement is still explicit.

| Requirements | Planned verification | Acceptance |
|---|---|---|
| R1 | test_bootstrap_profile.py | Three lifecycle states, valid reports |
| R2 | test_stack_detection_errors.py | Injected failure cannot become SKIP |
| R3–R4 | test_quality_gate.py | Required missing/failing tools block; optional skip is explicit |
| R5 | test_framework_lifecycle.py | Clean-room lifecycle and preservation |
| R6 | test_ci_contract.py + real CI runs | Four OS/Python combinations green |
| R7–R10 | test_team_policy.py + human scenario review | Authority and exception scenarios accepted |
| R11–R14 | test_workflow_state.py | Illegal transitions and stale approvals rejected |
| R15 | test_review_attestation.py + repository configuration review | Untrusted self-approval rejected in repository mode |
| R16–R17 | test_evidence_gate.py | Missing, failing, or stale evidence blocks closure |
| R18–R21 | test_work_claims.py | Conflict, transfer, and recovery scenarios |
| R22 | test_team_policy.py + external-data scenario review | Unapproved source data cannot redefine policy |
| R23 | test_format_versions.py | Legacy fixture migration and unknown-version rejection |
| R24–R26 | test_framework_update.py | Dry run, conflict, interrupted apply, restore, foreign-file preservation |
| R27–R28 | test_documentation_contract.py + maintainer review | Claims link to capability evidence |
| R29 | test_token_limit.py + CI changed-file test | Same bytes/exemptions; no repository-wide grandfathered scan |
| R30–R32 | test_release_readiness.py + reviewed pilot/release records | Missing evidence blocks 1.0; no automatic publication |
