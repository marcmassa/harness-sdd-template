# Design — Hybrid team stable release

> FEAT-010 · 2026-11-09 · Proposed, pending human approval.
> Canonical context: ../../DESIGN.md and ../../docs/sdd.md.

## Summary

Evolve the existing local-first framework in six sequential milestones. Keep
agentic.json canonical for framework configuration, feature_list.json for
feature discovery, and Markdown for requirements/design/tasks. Add a small
standard-library workflow layer shared by commands and CI so correctness no
longer depends only on an agent remembering instructions.

This is one initiative, not simultaneous feature implementation. Its feature
remains in_progress until M6 is evidenced, or remains explicitly incomplete
when external pilot evidence is unavailable. Milestone status is reported
separately; no stable-release claim is inferred from passing local tests.

## Goals and non-goals

Goals: reliable quality gates; explicit human decisions; reproducible evidence;
recoverable ownership and handoffs; non-destructive updates; justified 1.0.
Non-goals: hosted scheduler, distributed lock service, proprietary database,
agent provenance detector, equal enforcement in every CLI, or proof that a
referenced test semantically satisfies a requirement.

## Baseline and dependency decisions

- Preserve the repository's FRESH shipping manifest; do not run /init merely to
  consume scaffolds here. Fixtures exercise consumer initialization instead.
- Existing Python minimum is documented as 3.8. New code stays syntax-compatible
  until a separate, explicit compatibility decision; 3.10/3.13 are the tested
  target matrix, not an implicit promise that all historical versions work.
- Existing profile failure and swallowed detection error are M1 regressions.
- Existing test_token_limit.py and .githooks/pre-commit are the shared policy
  baseline. Avoid duplicated ignore rules in CI.
- FEAT-009 is not approved by approving FEAT-010. Before optionally activating
  plugin packaging, amend its ownership assumptions in its own spec and obtain
  its independent approval. Portable export/update is sufficient for 1.0.
- Provider APIs and plugin event contracts must be checked against primary
  documentation when implemented; this spec asserts no unverified current API.
- skill-governance referenced by the spec-author role is not installed locally.
  Do not invent its contents or fetch a private registry automatically; use the
  repository's explicit SDD rules and the loaded technical-writing guidance.

## Components and affected files

Paths are proposed contracts. Prefer small modules below the authored-file
limit instead of extending the existing large shell/Python files indefinitely.

| Paths | Action and responsibility |
|---|---|
| .agents/bootstrap.sh | Fix profile; delegate new workflow/update operations |
| .agents/adapters/_common/render.py | Integrate inventory and capability declarations |
| .agents/lib/{quality,workflow,approval,evidence,claims,inventory,update,release}.py | Small standard-library modules with testable boundaries |
| .agents/schemas/{team-policy,work-record,release-evidence}.json | Versioned structural contracts; validate with stdlib code |
| .agents/agentic.json | Optional policy, concurrency, and version declarations |
| .agents/commands/*.md | Call shared validation; preserve explicit human gates |
| check.sh | Required/optional checks; workflow and changed-file validation |
| .github/workflows/ci.yml | Baseline matrix and trusted review verification |
| .githooks/pre-commit and shared token policy helper | Preserve staged behavior; reuse for CI diff ranges |
| tests/test_*.py and small .sh launchers | Isolated unit/integration fixtures |
| progress/work/<feature>.json | One tracked work record per active feature |
| progress/handoffs/<feature>/<id>.md | Immutable handoff entries |
| progress/current.md | Current session pointer, not shared global ownership |
| .harness/installed.json | Installed version, owned paths, and baseline digests |
| .harness/backups/<update-id>/ | Local recovery data, excluded from export/version control |
| docs/team-policy.md, docs/maintenance.md, docs/compatibility.md | Authority, operating boundaries, supported behavior |
| docs/pilots/<pilot-id>.md | Human-reviewed real pilot evidence |
| releases/1.0.0/{readiness.json,validation.md} | Candidate evidence, never fabricated publication |
| AGENTS.md, DESIGN.md, README.md, CONTRIBUTING.md | Navigation, actual architecture, supported claims |

Generated adapter edits always go through canonical configuration/templates
and bootstrap; never patch generated outputs by hand.

## M1 — Quality gate design

Define each check as an id, command, applicability predicate, and required flag.
Exit 0 only if all applicable required checks pass. An inapplicable optional
check is SKIP with a reason; a required unavailable executable is FAIL. Do not
infer that any tests/ directory implies pytest: distinguish framework unittest
suites from an adopted project's declared checks.

Use compileall or explicit compile() for Python syntax checks instead of the
current invalid py_compile invocation. Exercise failing commands, absent tools,
unsupported stacks, and child exit-code propagation. Tests operate on temporary
repositories, never on the consumer's tracked manifest or user Git config.

CI checks changed authored files against the same 20,000-byte policy as the hook.
For pull requests use the merge-base to candidate diff; for push use a validated
before/after range; handle an absent/all-zero base explicitly. Do not fail an
unchanged legacy oversized file. Read attributes/content from the candidate
revision, not untrusted working-tree overrides. Fail if revision inputs cannot
be resolved rather than silently skipping. Test spaces, newlines, UTF-8,
renames, deletions, generated attributes, and partial staging for hook mode.

## M2 — Authority and risk policy

Policy declares human owner, risk class, review mode, and decision boundaries.
The lightweight route is allowed for scoped documentation or low-risk fixes
with no public contract, permission, state migration, or approval-model change.
The full route applies to behavior changes and risk-bearing maintenance.
A reviewer can escalate classification; a disputed classification stays blocked.

Humans own scope acceptance and publication. Agents may prepare proposals,
implement approved scope, and generate evidence. A full-SDD author cannot
satisfy a required independent review with its own unchecked local record.
Merge rights and release credentials remain repository/provider controls.

Document six decision scenarios: small fix, incompatible API change, approved
spec change, failed check, external instruction injection, abandoned work.
Each scenario states permitted action, responsible human, and expected gate.

## M3 — State and approval contracts

Proposed shared operations, exposed through bootstrap subcommands:

```text
validate_transition(feature, target, record, evidence, policy) -> diagnostics
spec_digest(requirements_bytes, design_bytes) -> sha256
verify_approval(record, current_digest, trusted_review) -> diagnostics
validate_evidence(requirement_ids, evidence, revision) -> diagnostics
```

Transitions retain pending/spec_ready/in_progress/done/blocked. Reopening done
requires a reason and invalidates completion evidence. Returning from blocked
rechecks prerequisites. Invalid operations exit nonzero without changing state.
Writes use a same-directory temporary file, flush, and atomic replacement.
Lifecycle hooks run after validated transition; record a failed post-transition
hook as an explicit incomplete event rather than silently rerunning side effects.
Hook failure recovery must be idempotent or explicitly human-confirmed.

Approval digest: SHA-256 over a version prefix and length-prefixed raw bytes
of requirements.md then design.md. No newline/encoding normalization; even a
format edit requires reapproval. tasks.md checkboxes are excluded; substantive
task changes are reviewed against the approved scope and recorded as a change
request when scope differs. Task exclusion is not permission to expand scope.

Example work record (field names are the proposed v1 wire contract):

```json
{
  "format_version": 1,
  "feature_id": "FEAT-010",
  "owner": "maintainer-or-agent-session",
  "branch": "feat/hybrid-team-stable-release",
  "worktree": null,
  "dependencies": [],
  "revision": "full-git-object-id",
  "risk": "full",
  "approval": {
    "spec_digest": "sha256-value",
    "review_mode": "local",
    "reviewer": "declared-human-reviewer",
    "evidence_ref": "review-or-decision-reference"
  },
  "handoff": null,
  "evidence": []
}
```

Local mode is a declared human decision record, not authentication. Repository
mode uses provider-authenticated review metadata fetched in trusted CI, checks
an allowed human reviewer against team policy, and ties approval to the reviewed
revision/spec digest. No CI token is exposed to untrusted fork code; privilege
boundaries must be verified before enabling the provider job. Tests use captured
metadata fixtures, not live privileged APIs. Never accept a workspace-supplied
JSON file as trusted attestation merely because its shape is valid.

The trusted job may validate a newer implementation revision only if the current
spec digest matches the approved digest and the configured code review policy
is satisfied. Missing provider access produces a clear failure in required
repository mode. Offline local mode is explicitly reported as weaker assurance.

Evidence records contain requirement id, kind (automated/manual), source path
or review reference, result, revision, reviewer for manual evidence, and check
command where applicable. Verify referenced tests exist, required runs passed,
and results match the candidate revision. Humans assess test suitability.

## M4 — Claims, concurrency, and handoffs

The default maxConcurrent remains 1. An explicit team policy may raise it for
independent features; the old feature_list.rules.maxConcurrent is honored during
migration. Do not assume different files imply independent business changes.

Local claims use exclusive creation with a claim identifier. Tracked records
provide Git conflict visibility across clones; they are not distributed locks.
Shared teams coordinate ownership via their repository/PR process. A merge-time
validator detects duplicate claims, dependency cycles, and conflicting active
ownership. Never promise to prevent concurrent offline work in separate clones.

A handoff is immutable Markdown plus a record pointer and expected revision.
Recovery creates a reassignment event; no automatic timeout steals ownership.
Current session files become pointers to work records. Preserve existing
progress/history and expose a migration for old session-only state.

## M5 — Inventory, updates, and compatibility

The inventory stores installed framework version, format versions, each owned
path, and baseline SHA-256. Export creates consumer-shaped inventory without
maintainer feature history. Old exports require an explicit inventory adoption
step based on known release contents; uncertain files become conflicts.

```text
plan_update(installed, incoming, filesystem) -> UpdatePlan
apply_update(plan, expected_digests) -> receipt | conflict
restore_update(receipt) -> diagnostics
```

Use three-way comparison: original installed baseline, current contents, new
release. Unmodified owned files may update; locally changed files produce a
conflict; foreign files stay untouched. Reject traversal, absolute destination
paths, and symlink escapes. Apply rechecks digests to catch edits after planning.
Back up before mutation and journal steps so interrupted updates are recoverable.
Restore rejects overwriting edits made after apply unless separately confirmed.
A remove operation removes unchanged owned files only and reports retained files.

Manifest additions are optional with backward-compatible defaults; unknown
future formats fail with a migration diagnostic. Keep templates and adapters
synchronized through the renderer. The capability matrix links each claimed
control to tests or manual evidence, identifying instruction-only enforcement.

Split long authored files by topic/responsibility when modified. Do not relabel
them generated to bypass the hook. Navigation entry should target <=120 lines;
move operational detail into linked documents and preserve mandatory gates.

## M6 — Pilot and release evidence

Two real contexts are required, without assuming participant identities:
small team (at least one human plus an agent), and team (at least two humans
using at least two supported CLIs). One participant may join both contexts but
the reports must describe distinct work and observations.

Each pilot records date range, participant consent/roles, framework version,
initial baseline, installation, approved change, code review, handoff, upgrade,
recovery exercise, elapsed onboarding time, approval waiting time, rework,
post-close defects, false blocks, and unresolved issues. Aggregate only needed
metrics; do not collect source secrets or rank human/agent productivity.
Simulated fixtures verify the report validator but do not count as real pilots.

Release readiness is an offline command producing a report, not a publish action.
Missing pilots leaves the initiative at release-candidate with an explicit list
of missing evidence. A release blocker is data loss, incorrect mandatory gating,
authentication bypass claim, failed supported-matrix test, or broken documented
installation/update/recovery. Maintainer records severity and disposition of
other defects. No unresolved blocker is waived by renaming it.

Before 1.0 the maintainer reviews candidate artifacts, CI evidence, migration
notes, capability matrix, pilot reports, and remaining limitations. Tagging,
publishing plugins/packages, and announcing remain separate authorized actions.

## Milestone dependencies and estimates

| Milestone | Depends on | Exit | Effort estimate |
|---|---|---|---|
| M1 Reliable base | Existing baseline | Mandatory gates and isolated lifecycle tests green | 1 week |
| M2 Authority | M1 | Reviewed policy scenarios | 1 week |
| M3 Verifiable SDD | M2 | State, digest, trusted review, and evidence gates | 2–3 weeks |
| M4 Team handoffs | M3 | Claims, conflicts, and recovery exercised | 1–2 weeks |
| M5 Distribution | M4 | Inventory/update/rollback and capability evidence | 1–2 weeks |
| M6 Stable evidence | M5 | Real pilots, green CI, maintainer review | >=2 calendar weeks |

Estimate: 8–12 weeks with review availability; external pilot timing is not an
agent completion guarantee. No simultaneous implementation of unrelated features.

## Rollout, rollback, and errors

Introduce optional formats and validators first; migrate fixtures before real
projects. Opt a pilot into strict repository mode only after trusted CI setup is
reviewed. Cut release-candidate artifacts before recruiting stable-release pilots.

| Failure | Behavior |
|---|---|
| Missing required tool, approval, or evidence | Nonzero, precise remediation, no done transition |
| Unknown format version | Refuse mutation; identify supported version/migration |
| Claim conflict or stale revision | Preserve record; require refresh/reassignment |
| Post-transition hook failure | Persist incomplete event; explicit recovery |
| Update conflict or concurrent edit | Preserve file, report conflict; recover via receipt |
| Missing pilot or CI evidence | Candidate remains not-ready; no fabricated success |

Rollback restores backed-up owned files and previous format records, subject to
post-update edit checks. Never change user files, Git hooksPath, branch protection,
or remote configuration as an unannounced side effect of rollback/uninstall.

## Discarded alternatives

1. More instructions as the only enforcement: cannot reliably detect stale
   approvals, absent evidence, or false-green checks.
2. Hosted coordinator/database: operational complexity before pilot demand.
3. Directory-wide generated ownership: risks deleting or blocking user config.
4. Trust an agent-written reviewer name as authentication: does not establish
   a human decision; repository mode needs an external trust boundary.
5. Mandatory full ceremony for every edit: encourages bypass for small changes.
6. Native plugin packaging as a prerequisite for 1.0: confuses distribution with
   quality; preserve FEAT-009's separate approval and validate portable installs.

## Risks and remaining external inputs

- Migrations may break existing consumers: retain fixtures and explicit adoption.
- Provider review verification may differ across hosts: first support the repo's
  verified provider, document local mode elsewhere; never imply portable auth.
- Required skills may be unavailable: document dependencies and installation,
  never silently grant invented policy authority.
- Maintainer must identify actual pilot participants, allowed human reviewers,
  repository permissions, and final publication destination before their gates.
  These inputs do not block M1; they do block claims dependent on real evidence.
