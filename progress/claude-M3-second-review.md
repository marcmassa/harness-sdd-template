# Second independent review: FEAT-010 M3 corrections

2026-11-11. Reviewed `claude-M3-corrections.md` against the code, ran the
suites, and probed disposable repositories. Nothing was staged or committed,
no task box was changed, and the approved spec is untouched.

**Verdict: the eleven earlier findings are fixed. Three new defects were found
and fixed here. T11, T12, T14, and T15 can be checked; T13 stays unchecked
until the trusted workflow has run in a real repository.**

## Run here

| Command | Result |
|---|---|
| `./check.sh --no-color` | Exit 0, 12 suites pass, workflow contract `[SKIP]` (no team_policy) |
| `bash tests/test_m3.sh` (Python 3.13.18) | 272 OK before the fixes; suite passes with the 3 added M3 tests |
| `./.agents/bootstrap.sh --check` | Adapters in sync |

Not run: Linux, Python 3.10, any GitHub Actions run, any live provider call.
`trusted_verify.py`, `github_api.py`, `trusted_candidate.py`, and
`provider_review.py` were not read line by line in this pass.

## New findings, all reproduced, fixed, and covered

| # | Finding | Fix | Regression test |
|---|---|---|---|
| 1 | Without a team policy (this repository and every export), `pending -> blocked -> in_progress` succeeded, skipping `spec_ready`. The origin of a block was not stored | `mutate_transition` stores `blocked_from` on the feature; `_validate_unmanaged` enforces it. A hand-blocked feature returns only to `pending` or `spec_ready` | `test_unmanaged_blocking_cannot_skip_the_spec_gate`, `test_unmanaged_hand_blocked_feature_reenters_before_the_gates` |
| 2 | Under an active policy, a `done` feature made `check.sh` fail once a later commit renamed or deleted a test named in its evidence (`evidence source does not exist`) | Stored closures validate evidence in the closure revision's blobs only | `test_closed_feature_stays_valid_after_its_tests_are_renamed` |
| 3 | The exported `.gitignore` carried this repository's `/specs/*` rule, so a consumer's specs, `specs/README.md`, and the templates were ignored by Git | `export` drops the `/specs/` rules from the copy | `test_exported_gitignore_keeps_consumer_specs_committable` |

Correction to `claude-M3-corrections.md` gap 7: `.gitignore` is exported, and
the lock file is ignored in consumers. The new test asserts it.

## Still open (unchanged, for the maintainer)

- R15 has no external evidence: `trusted-review.yml` has never run.
- The unmanaged default enforces structural gates only, so the M3 exit
  criterion holds for opted-in projects. FEAT-010's own approval file is not
  machine-validated.
- This repository's `.gitignore` still ignores `/specs/*` except FEAT-010's
  spec, so `specs/plugin-packaging/` (FEAT-009, `spec_ready`) is untracked.
- `AGENTS.md` (22,079 bytes) is over the 20,000-byte limit and still describes
  manual status edits (T23).
- `steering/global-conventions.md` and `steering/implementer-patterns.md`
  produce an undeclared-file warning on every `check.sh` run.
