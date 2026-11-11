# Tasks — Hybrid team stable release

> FEAT-010 · Sequential implementation after approval of this spec.
> All implementation boxes are intentionally unchecked. A milestone may be
> complete while the initiative remains incomplete. Existing hook maintenance
> is finished and is regression input, not an unchecked deliverable.

## Approval and execution

- [x] **T1** — Obtain explicit human approval of these three documents; record
  the approved revision and scope before setting FEAT-010 in_progress. Confirm
  FEAT-009 remains separate and that no other feature is in_progress. _(R7, R9)_
- [x] **T2** — Record the existing ./check.sh baseline, fixture versions, and
  implementation report at progress/impl_hybrid-team-stable-release.md. Maintain
  an R -> task -> test/evidence map throughout implementation. _(R4, R16)_

## M1 — Reliable base

- [x] **T3** — Add profile lifecycle regressions; fix undefined manifest/report
  interpolation without changing fresh template state. _(R1)_
- [x] **T4** — Repair the missing json import in detection tests; inject a
  detector failure and assert nonzero instead of silent absence. _(R2)_
- [x] **T5** — Implement required/optional check outcomes and exit propagation;
  replace invalid syntax checking and avoid imposing pytest on unittest-only
  projects. Test missing tools and failing child commands. _(R3, R4)_
- [x] **T6** — Exercise export/init/render/check/clean in disposable Git repos,
  including modified user files and deterministic repeated output. _(R5)_
- [x] **T7** — Add Ubuntu/macOS x Python 3.10/3.13 CI, token-hook regression,
  and a changed-file size gate reusing the hook policy; test invalid diff bases,
  staged/revision attributes, deletion, rename, and unusual filenames. _(R6, R29)_
- [x] **T8** — Run M1 tests and ./check.sh; record real CI results when available.
  Correct README claims that are not yet enforced. _(R1–R6, R28–R29)_

**M1 exit:** lifecycle fixtures pass; required failures block; CI matrix defined
and real execution evidence distinguished from local success.

## M2 — Human/AI operating contract

- [x] **T9** — Define roles, human authority, review modes, publication boundary,
  lightweight/full classification, exception handling, and source trust labels.
  _(R7–R10, R22)_
- [x] **T10** — Add policy validation and six scenario fixtures; obtain human
  review of their decisions and document the review reference. _(R7–R10, R22)_
- [x] **T11** — Update canonical commands/instructions to use the policy and
  retain human gates; rerender adapters, then run ./check.sh. _(R7–R10, R22, R28)_

**M2 exit:** human reviewer accepts the authority/scenario matrix; automatic
validation rejects absent policy fields and unreviewed exceptions.

## M3 — Verifiable SDD

- [x] **T12** — Implement versioned work/evidence records, deterministic spec
  digest, shared state transition validation, atomic writes, and explicit
  failed-hook recovery. _(R11–R14, R17, R23)_
- [ ] **T13** — Implement declared local review and trusted repository review
  modes; verify actual provider documentation and privilege boundaries before
  enabling CI. Add tests for forged metadata, stale revision, changed specs,
  task-only updates, missing reviewer, and unavailable required provider access.
  _(R12–R15)_
- [x] **T14** — Validate requirement identifiers, automated/manual evidence,
  test references, candidate revision, mandatory results, independent review,
  and unfinished tasks at closure. _(R16–R17)_
- [x] **T15** — Integrate validators into canonical approve/implement/done and
  check.sh; run positive and negative state-machine scenarios and ./check.sh.
  _(R9, R11–R17)_

**M3 exit:** stale approval and incomplete evidence prevent completion;
self-declared identity never satisfies required repository authentication.

## M4 — Shared work and recovery

- [ ] **T16** — Add per-feature ownership, branch/worktree, dependency and
  revision records; keep default concurrency 1 with explicit opt-in overrides.
  _(R18–R19, R23)_
- [ ] **T17** — Implement local claim conflicts, merge-time conflict detection,
  dependency-cycle checks, and authorized reassignment preserving history.
  Explicitly document cross-clone locking limits. _(R19, R21)_
- [ ] **T18** — Add immutable handoffs and old-session migration; exercise two
  independent worktrees and a third participant resuming from recorded state.
  _(R18, R20–R21)_
- [ ] **T19** — Validate an external-data instruction scenario, conflicting
  claims, stale handoff revision, abandoned work, and ./check.sh. _(R18–R22)_

**M4 exit:** independent work records do not overwrite one another; conflicts
and reassignment are visible and recoverable.

## M5 — Distribution and maintenance

- [ ] **T20** — Define framework/format versions, compatibility ranges, inventory
  adoption for legacy consumers, and unknown-version rejection. _(R23, R26)_
- [ ] **T21** — Implement non-mutating update plans and safe apply/restore with
  three-way comparisons, backups, journal, digest rechecks, and narrow ownership.
  Test traversal, symlinks, interruption, changed files, and foreign configuration.
  _(R24–R26)_
- [ ] **T22** — Publish the adapter capability matrix with evidence links;
  document native plugin packaging as optional pending FEAT-009 approval.
  _(R26–R27)_
- [ ] **T23** — Split touched oversized authored files; shorten AGENTS.md to
  navigation; document contribution, hook install, team policy, migration,
  update/rollback, and release ownership. Validate links and claims. _(R28–R29)_
- [ ] **T24** — Exercise legacy upgrade, clean install, rollback, removal, all
  five adapter entry points, and ./check.sh. Record supported versus skipped
  native-tool checks without claiming skips are validation. _(R23–R29)_

**M5 exit:** a release candidate installs and updates without overwriting user
files; documentation states actual capabilities and compatibility.

## M6 — Real pilot and stable evidence

- [ ] **T25** — Prepare pilot/report and readiness formats, test missing/invalid
  reports, and identify consenting human pilot owners. Synthetic test fixtures
  must be labeled and cannot count toward the two real pilots. _(R30–R31)_
- [ ] **T26** — Execute the small-team pilot: baseline metrics, installation,
  approved change, technical review, handoff, update, and recovery; obtain a
  human-reviewed report. _(R30)_
- [ ] **T27** — Execute the multi-person/multi-tool pilot with the same evidence;
  compare observations and record unresolved defects and dispositions. _(R30)_
- [ ] **T28** — Resolve release blockers, rerun affected checks and mandatory CI,
  review the compatibility matrix, and generate 1.0 readiness evidence. Missing
  real evidence leaves this task unchecked and the release not-ready. _(R31)_
- [ ] **T29** — Present exact candidate artifacts, evidence and remaining limits
  for maintainer release review; leave public tag/package/marketplace publication
  pending explicit authorization. _(R31–R32)_

**M6 exit:** real pilots reviewed, mandatory CI green, no unresolved blocker,
readiness accepted. Publication is a separate authorized operation.

## Closure

- [ ] **T30** — Review all 32 R identifiers against actual test/manual evidence;
  distinguish local checks from trusted CI and real pilot records. _(R1–R32)_
- [ ] **T31** — Run ./check.sh, the relevant changed-file token gate, and release
  readiness validation; record commands and results. _(R3–R6, R17, R29, R31)_
- [ ] **T32** — Only after all required evidence and human reviews exist, mark
  FEAT-010 done; append the completed session summary to progress/history.md
  and restore progress/current.md to its template. _(R17, R28, R30–R32)_

## Requirement -> primary tasks

| Requirement | Tasks | Requirement | Tasks |
|---|---|---|---|
| R1 | T3, T8 | R17 | T12, T14, T15 |
| R2 | T4, T8 | R18 | T16, T18, T19 |
| R3 | T5, T8 | R19 | T16, T17, T19 |
| R4 | T2, T5, T8 | R20 | T18, T19 |
| R5 | T6, T8 | R21 | T17, T18, T19 |
| R6 | T7, T8 | R22 | T9, T10, T11, T19 |
| R7 | T1, T9, T10, T11 | R23 | T12, T16, T20, T24 |
| R8 | T9, T10, T11 | R24 | T21, T24 |
| R9 | T1, T9, T10, T11, T15 | R25 | T21, T24 |
| R10 | T9, T10, T11 | R26 | T20, T21, T22, T24 |
| R11 | T12, T15 | R27 | T22, T24 |
| R12 | T12, T13, T15 | R28 | T8, T11, T23, T24 |
| R13 | T12, T13, T15 | R29 | T7, T8, T23, T24 |
| R14 | T12, T13, T15 | R30 | T25, T26, T27 |
| R15 | T13, T15 | R31 | T25, T28, T29 |
| R16 | T2, T14, T15 | R32 | T29 |
