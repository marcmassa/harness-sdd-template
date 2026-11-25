# Current Session State

## Active Task
FEAT-010 — T1–T25 checked and reviewed. M6 needs two real pilots (T26, T27).

## Progress
- [x] M1–M5 and T25 merged; CI green on Ubuntu/macOS with Python 3.10/3.13.
- [x] T20 and T21 reviewed and approved by the maintainer (2026-11-25).
- [x] MAINT-003–007 merged (PRs #13–#16): embedded bodies, `init --apply`, parallel
  `check.sh`, no generated `CLAUDE.md`, two roles by default.
- [x] Fixes from the SecurIT migration merged (#17–#19): no default skills registry,
  stale generated files pruned, archived logs pass the size hook.
- [x] SecurIT migrated to 0.9.0 with three roles (delfos #140, #141).
- [x] FEAT-009 spec approved by the maintainer (2026-11-25); starts when FEAT-010 closes.

## Pending
- T26 and T27: two real pilots, by consenting people. No owner identified yet.
- D-001: trusted-review.yml failed at startup three times, then worked again. Open.

## Blockers
- provider-verified with real data needs a repository in repository mode and a second
  reviewer account.
- Real pilot reports for M6 need human review.

## Next Step
Maintainer: name the pilot owners for T26/T27 and decide D-001. Then close FEAT-010 and
start FEAT-009 with `workflow-transition --target in_progress`.
