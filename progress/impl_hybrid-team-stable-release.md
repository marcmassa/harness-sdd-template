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

## First remote CI evidence — 2026-11-11

Run 43109307463 (commit 6cd752c) failed in all four jobs on one cause: the
FEAT-009 spec was git-ignored and missing remotely. Run 43110408983 (commit
0a66652) passed on ubuntu-latest and macos-latest with Python 3.10 and 3.13,
including the changed-file size gate. `trusted-review.yml` has still never run
(it triggers on pull requests only), so R15/T13 remain without remote evidence.

## T21 implemented 2026-11-15, awaiting review

| Requirement | Task | Evidence (tests/test_update.py) | State |
|---|---|---|---|
| R24 | T21 | PlanTests: per-file add/replace/conflict/remove, non-mutating, stable digest | Local PASS |
| R25 | T21 | ApplyTests and RestoreTests: conflicts preserved, backup, stale plan refused, interruption detected and restored, post-update edits protected | Local PASS |
| R26 | T21 | Foreign files and tool configuration untouched; symlinks and traversal refused; only inventory paths change | Local PASS |

Files: `.agents/lib/update.py`, `bootstrap.sh` (`update-plan/apply/restore/keep/adopt`),
`docs/maintenance.md`. Export no longer ships machine-local synced skills.

## First real migrations — 2026-11-15 (input for M6, not yet a reviewed pilot report)

| Project | Starting point | Result |
|---|---|---|
| harness-manager | Legacy install with bootstrap, 38 features done | `update-adopt` matched 11 files, recognized 22 as untouched earlier releases, 2 uncertain (`AGENTS.md`, `check.sh`). `update-apply` changed 76 paths; its own `check.sh` passes (36 checks). Local commit 3caa189 on `chore/harness-sdd-0.9.0`, not pushed |
| SecurIT | Hand-adapted install that removed the renderer on purpose; 0 of 24 files match any release | Full update not applied: it would re-add 64 files the project chose to drop. Targeted change to its `check.sh` only (green-run cache, `--quiet`, timings), local commit 329b213f on `chore/harness-context-budget`, not pushed, full check not run with the change |

Defects the migrations exposed, fixed in the framework: legacy files could not
be told from local edits (now matched against the source's Git history);
starter and scaffold files were added to initialized projects (now never
added); no way to accept a conflict explicitly (`update-accept`); the brief
ignored `.kiro/specs`; releases shipped machine-local skills.

## T13 — 2026-11-16

Line-by-line review of `trusted_verify`, `github_api`, `trusted_candidate`, and
`provider_review`; three fixes with tests (any unforeseen error is a rejection,
inert summary text, hostile test source cannot crash the gate). First runs
against the real GitHub API and a real pull-request fetch, all failing closed
as expected; see `docs/trusted-review.md`, "Evidence so far". Pull request #4
is open against `main`. T13 stays unchecked: no run inside GitHub Actions and
no positive `provider-verified` result with real data yet.

PR #4 merged 2026-11-16 (`295d138`). First run of `trusted-review.yml` in
GitHub Actions on PR #6 (run 43827430983): read-only token, trusted base
checkout, check attached to the pull request, result `not-required`. T13
checked: both review modes are implemented, the provider behaviour and the
privilege boundary were verified with real runs, and the listed negative
tests exist. R15 state: Local PASS plus remote boundary evidence. Still not
observed: `provider-verified` with a real second reviewer, and the ruleset
binding; both need a repository that opts in to repository mode.

## T22 implemented 2026-11-16, awaiting review

| Requirement | Task | Evidence (tests/test_capability_matrix.py) | State |
|---|---|---|---|
| R27 | T22 | AdapterClaimTests: each adapter rendered from one fixture; generated files equal the declared outputs; permission level checked per adapter. MatrixDocumentTests: document generated from the data file, drift detected, every evidence reference exists | Local PASS |
| R26 (part) | T22 | Matrix lists the exact paths each adapter generates; no adapter owns a whole tool directory | Local PASS |

Files: `.agents/schemas/capabilities.json`, `.agents/lib/capabilities.py`,
`docs/compatibility.md` (generated), `bootstrap.sh capabilities`. Native plugin
packaging is stated as optional and pending FEAT-009 approval. Found while
verifying: `CLAUDE.md` claimed that `.claude/settings.json` enforces edit
permissions; its `deny` list is empty. The claim is corrected and a test
keeps it out.

## T23 implemented 2026-11-16, awaiting review

| Requirement | Task | Evidence | State |
|---|---|---|---|
| R29 | T23 | `render.py` (49,030 bytes) split into `render_core`, `render_adapters`, `render_scaffold`, `render_init`, `render_export` plus a 9 KB entry point; largest module 14,130 bytes. A snapshot of renderer behaviour (export tree, 26 commands, every generated file; 2,083 lines) is byte-identical before and after. `tests/test_docs_contract.py`: no tracked authored file above 20,000 bytes; modules do not import the entry point | Local PASS |
| R28 | T23 | `CONTRIBUTING.md` (contribution, hook install, releases and their owner) links team policy, maintenance, update and rollback; README index updated; `AGENTS.md` is 120 lines. Tests: relative links and anchors resolve, every documented `bootstrap.sh` and `workflow-*` command exists | Local PASS |

The snapshot comparison was run once by hand and is not part of the suite; the
existing parity, plugin-adapter, target-CLI, portable-template, and M1 suites
cover the renderer on every run.

## T24 implemented 2026-11-16, awaiting review

Suite `tests/test_m5_e2e.py`, run by `check.sh`. Each case uses real exported projects.

| Exercise | What ran | Result |
|---|---|---|
| Legacy upgrade | Release `e286f4b` (before inventories) exported with its own tooling; a customized `check.sh` and a project file added; `update-adopt`, `update-plan`, `update-apply` from the current source | More than 10 files recognized as an untouched earlier release; custom `check.sh` kept as a conflict; project file untouched; inventory at 0.9.0; the new `brief` and `version` run in the project |
| Clean install | `export`, a project role, scaffolds removed, `init --validate`, `./check.sh` and `--quiet` | PASS |
| Five entry points | Each adapter rendered in both projects; every declared output file present; `--check` reports no drift | PASS |
| Rollback | `update-restore` after the legacy upgrade | Project byte-identical to its state before the update |
| Removal | New `update-remove`: plan, then apply by digest, then restore | Unchanged framework files removed, changed and project-owned files kept and listed, restore byte-identical |

| Requirement | State |
|---|---|
| R23, R24, R25, R26 | Local PASS (this suite, `test_inventory.py`, `test_update.py`) |
| R27, R28, R29 | Local PASS (`test_capability_matrix.py`, `test_docs_contract.py`) |

Native-tool checks: **not performed for any adapter.** The suite prints one
`[SKIP] native check <cli>: not run` line per adapter and states whether the
binary is on the machine. On the maintainer's machine `claude`, `codex`, and
`opencode` were present and `gemini` and `cursor-agent` were not; none was
invoked. `docs/compatibility.md` says the same. In a clone without the
`e286f4b` commit the legacy cases skip with an explicit message; CI fetches
full history and runs them.

## M4 (T16–T19) implemented 2026-11-16, awaiting review

Suite `tests/test_ownership.py` (launcher `tests/test_m4.sh`).

| Requirement | Task | Evidence (test class) | State |
|---|---|---|---|
| R18 | T16, T18 | RecordIdentityTests: feature, owner, claim, branch, dependencies, revision, handoff; brief shows owner and latest handoff | Local PASS |
| R19 | T16, T17 | ClaimConflictTests: second claim rejected and owner unchanged; two features in progress need separate branches; dependency cycle refused at start and by workflow-check; copied claim id and hand-edited owner detected. Default limit 1, explicit `max_concurrent` | Local PASS |
| R20 | T18 | HandoffTests: all five fields required, written once, immutable, accumulating; unreferenced or pre-existing files refused; old session state migrated without touching the old file | Local PASS |
| R21 | T17, T18 | ReassignmentTests: human `scope` authority, reason and evidence required, previous claim kept. ResumeTests: next participant resumes; stale and tampered handoffs refused. WorktreeTests: two worktrees, merge, third participant resumes | Local PASS |
| R22 | T19 | `test_external_instructions_in_a_handoff_are_data`: instruction-like handoff text changes no state, approval, or gate; trust order unchanged | Local PASS |
| R23 (part) | T16 | New record fields are optional under format 1; records without a claim remain valid | Local PASS |

Files: `.agents/lib/ownership.py` (validation), `.agents/lib/handoffs.py`
(claim, reassign, handoff, resume, migrate-session), wired into
`validate_transition`, `workflow-check`, `workflow-init`, and the CLI.
Documented limit: tracked records are not a distributed lock; two clones can
work offline on the same feature and the conflict appears when branches meet.

## T25 implemented 2026-11-16, awaiting review; pilot owners not identified

| Requirement | Task | Evidence (tests/test_release.py) | State |
|---|---|---|---|
| R30 | T25 | PilotReportTests: every required field, context rules, consent, six exercises, five metrics, human review. Synthetic reports validate and never count; the shipped example is labeled synthetic; the repository holds no real report | Local PASS |
| R31 | T25 | ReadinessTests: ready only with checked milestone tasks, green CI on all four combinations for the candidate, current matrix, two distinct real pilots, and no open blocker; each gap is named. A blocking category blocks whatever severity label it carries | Local PASS |
| R32 | T25 | Readiness writes a report and creates no tag; every report states that publication needs explicit authorization | Local PASS |

Files: `.agents/schemas/release-evidence.json`, `.agents/lib/release.py`,
`docs/pilots/README.md`, `docs/pilots/example-synthetic.json`,
`releases/1.0.0/defects.json`, `bootstrap.sh pilot-validate` and
`release-readiness`.

Deviation from the design: pilot reports are JSON (`docs/pilots/<id>.json`),
not Markdown, so the validator can check them.

Not done, and not doable by an agent: identifying consenting human pilot
owners. `docs/pilots/README.md` says none has been identified.

Open defect D-001 (`releases/1.0.0/defects.json`): `trusted-review.yml` ended in
`startup_failure` on three runs on 2026-11-16 between 17:24 and 17:37 UTC with an
unchanged workflow file, then ran successfully again at 18:26 UTC. Cause not
determined. It stays recorded as an open release blocker (incorrect-gating) until
the maintainer decides its disposition.

`./.agents/bootstrap.sh release-readiness 1.0.0` on this repository reports
`release-candidate`: milestone tasks unchecked, no CI evidence file, no real
pilot reports, and D-001 open.

