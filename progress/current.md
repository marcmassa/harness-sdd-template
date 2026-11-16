# Current Session State

## Active Task
FEAT-010 — M5 in progress (ADR-2 order): T20 and T21 implemented, awaiting review.

## Progress
- [x] M1–M3 committed and pushed; CI green on Ubuntu/macOS with Python 3.10/3.13.
- [x] T11, T12, T14, T15 checked.
- [ ] T13: reviewed and exercised against the real API (fails closed); no run in Actions yet.
- [x] T20 versions and inventory; T21 update plan/apply/restore/keep/accept/adopt.
- [x] Role cards compacted; brief warns on role and description budgets.
- [x] harness-manager migrated to 0.9.0 (local branch, not pushed).
- [x] SecurIT: check.sh cache, --quiet, timings (local branch, not pushed).

## Pending
- Human review of T20 and T21 before their boxes are checked.
- T22 capability matrix, T23 split render.py (49 KB) and docs, T24 end-to-end exercise.
- FEAT-009 stays separately spec_ready.

## Blockers
T13 needs PR #4 merged (pull_request_target uses main's workflow file), then a pull
request approved by a second account to observe provider-verified.
Real pilot reports for M6 need human review.

## Next Step
Merge PR #4, observe trusted-review.yml on the next pull request, then T22.
