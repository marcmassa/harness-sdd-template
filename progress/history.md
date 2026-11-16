# Session History

## 2026-10-22 — Previous session retained
FEAT-009 plugin-packaging: specifications written and status spec_ready.
Human approval remains outstanding; no implementation was started.

## 2026-11-09 — Staged-file token limit hook completed
Installed .githooks/pre-commit with local core.hooksPath=.githooks.
Checks staged authored blobs against 20,000 bytes (5,000 estimated tokens),
with generated/lockfile exclusions and actionable splitting instructions.
Seven isolated Git integration tests pass; ./check.sh passes all nine suites.
Existing check.sh Python syntax warning and missing optional pytest remain;
the new unittest suite runs independently through test_token_limit.sh.
No files were staged or committed on the user's behalf.

## 2026-11-09 — FEAT-010 specification ready
Created specs/hybrid-team-stable-release/{requirements,design,tasks}.md:
32 EARS requirements, 32 sequential tasks, six milestones from base reliability
to evidence-backed stable 1.0. Every requirement maps to planned verification.
Registered FEAT-010 as spec_ready. Implementation has not started.
FEAT-009 plugin-packaging remains spec_ready with independent approval.
The new spec is explicitly included by .gitignore for review/versioning.
The on_spec_created hook runner found no registered event hooks.
Next: human reviews FEAT-010 requirements/design/tasks and explicitly approves
or requests changes; then start T1/M1. Real pilots, trusted CI configuration,
and publication authorization remain external evidence gates.

## 2026-11-09 — FEAT-010 approval and M1 implementation
User approved the spec. Recorded approval_FEAT-010.json with original file
hashes and base Git revision; changed only FEAT-010 to in_progress.
T1–T9 complete locally: repaired profile/detector tests, modularized bootstrap,
added mandatory/optional quality outcomes and negative regressions, isolated
consumer lifecycle, shared staged/revision token policy, four-job CI matrix,
and corrected/split README guarantees. check.sh passes all 11 suites, including
21 M1 tests; a disposable clean tree and local Python 3.13 also pass.
Remote CI has not been run, and no stable release is claimed.
M2 policy and six scenario decisions are ready at docs/team-policy.md and
scenarios.json. Seven policy tests pass. T10 is pending actual human review;
no scenario acceptance or authenticated reviewer identity was fabricated.
Next: human accepts or amends the six scenario decisions. Then finish T10,
implement T11 policy integration, and continue sequentially with M3.
FEAT-009 approval stays independent.

## 2026-11-10 — Independent validation of Claude M2/M3
Codex ran check.sh (12 suites) and the 179 M3 tests under Python 3.13.
A separate Claude review returned REQUEST_CHANGES. Codex reproduced unsafe
rollback through a directory symlink, stale journal overwrite, historical
exemption for active work, and retrospective lightweight registration.
FEAT-010 remains in_progress; M3 has not passed review and T13 remains partial.
Review: progress/claude-M3-review.md. Verification: progress/impl_hybrid-team-stable-release.md.
