# Current Session State

## Active Task
FEAT-010 — M4, M5, and T25 implemented, awaiting review. M6 now needs real pilots.

## Progress
- [x] M1–M3 committed and pushed; CI green on Ubuntu/macOS with Python 3.10/3.13.
- [x] T11, T12, T14, T15 checked.
- [x] T13: reviewed, exercised against the real API, first run in Actions on PR #6 (not-required).
- [x] T20 versions and inventory; T21 update plan/apply/restore/keep/accept/adopt.
- [x] Role cards compacted; brief warns on role and description budgets.
- [x] harness-manager migrated to 0.9.0 (local branch, not pushed).
- [x] SecurIT: check.sh cache, --quiet, timings (local branch, not pushed).

## Pending
- Human review of T20 and T21 before their boxes are checked.
- T26 and T27: two real pilots, by consenting people. No owner identified yet.
- D-001: trusted-review.yml fails at startup since 2026-11-16 17:24 UTC; cause unknown.
- FEAT-009 stays separately spec_ready.

## Blockers
provider-verified with real data needs a repository in repository mode and a second
reviewer account.
Real pilot reports for M6 need human review.

## Next Step
Maintainer: read the D-001 run annotation, decide the T16–T25 boxes, name pilot owners.
