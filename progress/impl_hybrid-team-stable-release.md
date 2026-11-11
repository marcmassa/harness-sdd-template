# Implementation — FEAT-010

## Approval
Human approved on 2026-11-09 in this chat. Exact original file digests and
base revision are recorded in approval_FEAT-010.json. FEAT-009 is unchanged.

## Baseline
./check.sh exits 0 with nine suites. Known false-positive behavior: invalid
Python syntax command, optional pytest inferred from tests/, undefined profile
manifest variable, and swallowed stack-detection error. These are M1 targets.
Fixtures: repository shipping FRESH manifest; temporary Git repositories.

## Traceability
| Requirements | Tasks | Evidence | State |
|---|---|---|---|
| R7, R9 | T1 | Human chat approval and approval_FEAT-010.json | Recorded |
| R4, R16 | T2 | Baseline ./check.sh and this report | Recorded |
| R1 | T3 | test_m1_bootstrap: fresh/partial/initialized, quoted path | Local PASS |
| R2 | T4 | test_m1_bootstrap: injected detector failure; parity test repaired | Local PASS |
| R3–R4 | T5 | test_m1_quality: missing tools, exit 42, invalid syntax, unittest vs pytest | Local PASS |
| R5 | T6 | test_m1_bootstrap: exported consumer lifecycle, deterministic render, foreign-file preservation | Local PASS |
| R6 | T7 | ci.yml four-combination matrix; test_m1_ci_contract | Configuration PASS; actual remote runs pending |
| R29 | T7 | shared .githooks/token_limit.py and test_m1_token_revisions | Local PASS |
| R28 | T8 | README split into linked guides; unsupported enforcement claims corrected | Local review complete |
| R7–R10, R22 | T9–T10 | docs/team-policy.md and seven test_team_policy tests | Policy prepared; human scenario review pending |

## External evidence
No remote CI, real pilots, or public release has been claimed or initiated.

## M1 validation — 2026-11-09
- ./check.sh: exit 0; all 11 registered suites pass.
- Disposable clean-tree copy with generated adapters removed: ./check.sh exit 0.
- Python 3.13: 21 M1 tests pass. Current default Python also passes.
- Seven staged-hook tests and seven team-policy tests pass.
- Changed/new authored files all <=20,000 bytes; git diff --check passes.
- Bootstrap split into six small sourced modules, resolved relative to the
  executable so ROOT_DIR fixtures still work; profile formatter is separate.
- Gateway no longer emits the invalid py_compile or inferred pytest warnings.
- Existing idle steering scaffold warnings remain visible and nonblocking.
- No GitHub workflow run or Ubuntu/Python 3.10 compatibility result is claimed.

## M2 review gate
T9 policy prepared. T10 human acceptance of all six decisions is recorded in
approval_M2-scenarios.json (declared chat approval, not authenticated).
FEAT-010 remains in_progress. FEAT-009 remains spec_ready and unapproved.

## T11 and M3 — implemented 2026-11-09, awaiting independent review
Task checkboxes are left to the supervisor. State below is local test evidence.
Suites: tests/test_workflow_{state,recovery,commands}.py, test_review_attestation.py,
test_evidence_gate.py (launcher tests/test_m3.sh, registered in check.sh).

| Requirement | Task | Evidence (test class in those suites) | State |
|---|---|---|---|
| R7, R10 | T11 | ApprovalTests scope-change/authority; RecordBindingTests; ScenarioReviewTests | Local PASS |
| R8 | T11 | LightweightTests: intake, risk flags, acceptance evidence, independent review | Local PASS |
| R9 | T11, T15 | TransitionTests approval-before-implementation; UnmanagedProjectTests labels weaker path | Local PASS |
| R22 | T11 | ScenarioReviewTests; policy trust order; commands treat external text as data | Local PASS; scenario decision is declared human |
| R28 (part) | T11 | CanonicalCommandTests; docs/workflow-contract.md; team-policy.md | Local PASS; AGENTS.md is T23 |
| R11 | T12, T15 | TransitionTests, ConcurrencyTests, RecordBindingTests, BootstrapDispatchTests | Local PASS |
| R12 | T12 | ApprovalTests digest determinism/no normalization; approval stored by record_approval | Local PASS |
| R13 | T12, T15 | ApprovalTests stale requirements/design; blocks check and completion | Local PASS |
| R14 | T12 | ApprovalTests checkbox-only preserved; task text needs scope change | Local PASS |
| R15 | T13 | RepositoryModeTests fail-closed/forgery; CapturedGitHubMetadataTests | **PARTIAL**: fail-closed only |
| R16 | T14 | EvidenceTests, RequirementParsingTests | Local PASS; suitability stays human |
| R17 | T14, T15 | ClosingGateTests, TaskParsingTests, HookTests | Local PASS |
| R23 (part) | T12 | test_unknown_format_version_refused_with_migration_hint; schemas/work-record.json | Local PASS; rest is M5 |

Unfinished: T13 trusted repository verification (R15). No provider job exists,
and repository mode fails closed. T13 should stay unchecked. All M4-M6 work,
remote CI runs, and pilots are outstanding. See claude-M3-implementation.md.

## Codex validation — 2026-11-10

`./check.sh --no-color` passed all 12 suites. Approved requirements and design
hashes, FEAT-009 metadata, the FRESH manifest and changed-file size were verified.
The independent Claude reviewer returned REQUEST_CHANGES. See
[its report](claude-M3-review.md). The reviewer ran static analysis and
in-memory probes. Codex ran the full suite and Python 3.13 M3 suite separately.

Two adversarial probes against temporary repositories failed the expected safety
contract despite the green suite:

- `rollback_incomplete` followed a `progress/work` directory symlink and replaced
  an external JSON file. The lexical path allowlist does not constrain the real
  destination. Normal work-record writes also need the same containment check.
- `commit_transition` accepted a stale `before` snapshot and overwrote a newer
  file. The journal prevents simultaneous journal creation, but does not compare
  current contents with the state used to validate the transition under that lock.

M3 acceptance is withheld. Repository review mode remains fail-closed with T13
partial, as noted in Claude's handoff.

The 179 M3 tests also passed with Python 3.13 on PATH. A third negative probe
showed `workflow-check` returning PASS for a historical feature in `in_progress`
without a work record. The historical exception should cover completed legacy
features only.

Codex also reproduced retrospective lightweight registration through
`workflow-init` after changing an active feature to `sdd:false`. The subsequent
strict `workflow-check` passed without an approval or classification decision.
The review records further issues and preserves T13 as incomplete.

## M5 started before M4 (ADR-2) — T20 implemented 2026-11-11, awaiting review

| Requirement | Task | Evidence (tests/test_inventory.py) | State |
|---|---|---|---|
| R23 | T20 | VersionDeclarationTests; UnknownVersionTests (inventory, manifest, newer framework, malformed paths) | Local PASS |
| R26 (part) | T20 | ExportInventoryTests: per-path ownership and baselines, foreign files excluded; LegacyAdoptionTests | Local PASS; update/cleanup by inventory is T21 |

Files: `.agents/schemas/versions.json`, `.agents/lib/inventory.py`,
`docs/maintenance.md`, `bootstrap.sh` (`version`, `inventory-adopt`, format gate,
inventory on export), `check.sh` format check. T20 box left for the reviewer.
