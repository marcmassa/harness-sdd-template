# Claude M3 corrections and T13 — handoff for independent review

Scope: fixes for findings in `claude-M3-review.md`, Codex's probes in
`impl_hybrid-team-stable-release.md`, and the T13/R15 trusted verifier.
2026-11-10. Stopped for independent review; no M4 work.

Not done, deliberately: no staging, commit, push, or publish. No task boxes
changed. FEAT-010 is still `in_progress` and FEAT-009 still `spec_ready`.
`.agents/agentic.json` (FRESH) and the approved spec are unchanged:
`requirements.md` and `design.md` match `approval_FEAT-010.json`, and
`tasks.md` matches `30f1f94e…` once its checkboxes are reset. No global
config, credentials, private skills, or remote workflow were touched. No
GitHub API call or Actions run happened.

## Results (run here, sequentially)

| Command | Result |
|---|---|
| `bash tests/test_m3.sh` (Python 3.15.2) | 272 tests OK (was 179) |
| `python3.13 -m unittest discover -s tests -p "test_[wrtge]*.py"` | 286 tests OK (M3 suites plus team-policy and token-limit) |
| `./check.sh --no-color` | Exit 0; all 12 suites PASS; workflow contract `[SKIP]` (no team_policy) |
| `./.agents/bootstrap.sh --check` | Adapters in sync. Only canonical command bodies changed, so no render was needed |
| `ast.parse(feature_version=(3, 8))` on `.agents/lib` and `tests` | OK. Python 3.8/3.10 and Linux were not executed |
| Size scan of changed or untracked files | Largest is `tests/test_evidence_gate.py`, 18,897 bytes; all ≤ 20,000 |
| Lock-removal sanity check | With the lock patched out, the `maxConcurrent` race test fails, so it is not vacuous |

## Files

New: `.agents/lib/{safe_fs,classification,workflow_io,workflow_updates,workflow_check,github_api,trusted_candidate,trusted_verify}.py`,
`.github/workflows/trusted-review.yml`, `docs/trusted-review.md`,
`tests/test_{workflow_safety,workflow_classification,trusted_verify,github_api}.py`.

Rewritten:
- `workflow_store.py`: CAS, journal, rollback.
- `workflow_ops.py`: now transitions, records, and hooks only; it re-exports
  the split-out operations, so callers are unchanged.
- `provider_review.py`.

Modified:
- `.agents/lib/{workflow,approval,evidence,git_state,team_policy,workflow_cli}.py` and `check.sh`;
- `.agents/bootstrap.sh`: export list only;
- `.gitignore`: lock file;
- `.agents/commands/{approve,done,implement}.md`;
- `docs/{workflow-contract,team-policy}.md`;
- tests: `tests/test_m3.sh` and `tests/{test_workflow_recovery,test_workflow_state,test_evidence_gate,test_review_attestation}.py`.

## Findings → change → regression

| # | Finding | Change | Regression tests |
|---|---|---|---|
| Codex probe 1 | Rollback followed a `progress/work` symlink and replaced an external file | `safe_fs` opens every component with `dir_fd` and `O_NOFOLLOW`. This covers reads, atomic writes (temp file plus `rename` in the same directory fd), exclusive create, unlink, listing, and the lock. Journal and rollback use only it | `SymlinkEscapeTests` (5): rollback through a symlinked `progress/work`, record writes, a symlinked `progress` parent, a symlinked record file, a symlinked `feature_list.json`. External files are asserted unchanged |
| Codex probe 2 | `commit_transition` accepted a stale `before` and overwrote a newer file | All mutations run under `progress/work/.workflow.lock` (`flock`, re-entrant per thread, timeout with diagnostic). Each reads the text it validates under the lock. `commit_transition` and `write_if_unchanged` compare current text with it and raise `StateConflict` without writing | `StaleSnapshotTests` (3): a direct stale `before`, a concurrent edit during validation, a hand edit between read and write |
| 6 | Lost updates in evidence/check/review/approve; `maxConcurrent` race; `_settle_hooks` overwrite | `workflow_io.update_record` applies each change to the on-disk record under the lock. `run_checks` runs `check.sh` unlocked, then merges its entry under the lock, refusing if HEAD or the tree changed. Hooks run unlocked; the outcome is applied to the current record and only the `pending_hook` field changes | `ConcurrentCommandTests` (4): two-thread `maxConcurrent` race (exactly one admitted), concurrent evidence plus review, a review recorded by `check.sh` while it runs, the lock timeout. `test_hook_edit_to_record_is_preserved` |
| Malformed journal/records | `AttributeError` crashes; journal shape trusted | The journal must be an object with `format_version` 1, a `feature_id`, unique allowed paths, and before/after texts that parse as JSON objects. Nested record fields are type-checked. `feature_list.json` structure is validated | `MalformedStateTests` (5): six malformed journals and nine malformed records give diagnostics with exit 1 and no writes |
| 1, Codex probe 3 | `historical_features` exempted any status | Requires policy `adoption_revision`: a real ancestor commit whose manifest has no `team_policy`. Each listed feature must be `done` there and now, with no record | `HistoricalExemptionTests` (6), including the `in_progress` probe |
| 2, Codex probe 4 | Retrospective lightweight intake / unauthorized SDD downgrade | `classification.py`: lightweight needs a human `scope` decision (`--classified-by/--classification-ref`, stored as `lightweight.classification`), re-validated at every gate. Refused unless the feature is `pending` and has no spec dir. Also refused if it was ever committed with `sdd` true, or its record was ever committed. Full records only at `pending`/`spec_ready`. `workflow-check` fails if a committed record is missing | `LightweightClassificationTests` (8), including the downgrade probe |
| 3 | Missing `feature_list.json` skipped strict checks | The `check.sh` workflow section runs unconditionally. `check_repository` fails when `team_policy` is active and state is missing | `test_missing_feature_list_fails_under_active_policy`, `..._without_policy_skips`, `test_check_script_runs_workflow_check_even_without_feature_list` |
| 5 | Prose or data files could be "automated" evidence | Only `test_*.py`/`*_test.py`/`test_*.sh`/`*_test.sh` count. Python symbols must be `test*` functions or methods via AST; shell symbols must be `test*` functions (the shunit2 convention). Paths with `.git`, `..`, or absolute paths are refused | `EvidenceSourceTests` (2) with the review's probe files |
| 10 | Stale evidence could never be removed | `add_evidence` moves entries for older revisions, and same-key replacements, to `superseded_evidence`. `workflow-evidence-remove` requires a reason | `test_stale_and_renamed_evidence_is_superseded_not_stuck`, `test_wrong_entry_can_be_removed_with_a_reason` |
| 7 | Hidden tasks (blockquote, HTML comment, `1. T2`) | Blockquotes are parsed. Task ids or checkboxes inside comments are refused. A bare task with no separator is refused | `HiddenTaskTests` (2) |
| 8 | Hook failures not surfaced | `workflow-check` fails on any `pending_hook`. Unmanaged required failures are persisted on the feature in `feature_list.json` and recovered with a declared name. New `workflow-run-hook` for `on_review_*` and `on_implementation_*`; `done.md`/`implement.md` use it | `HookOutcomeTests` (4) |
| 9 | Record glob ignored symlinks | `work_record_names` refuses non-regular entries | `test_symlinked_record_file_refused_by_check_listing` |

Existing tests changed because their contract changed:
- The journal tests now patch `safe_fs.write_text`.
- The historical test now expects the `adoption_revision` requirement.
- The `.git` test now expects the "inside the repository" message.
- Lightweight fixtures add a classifier.
- `RepositoryModeTests` was rewritten for the pending label.

## T13 / R15: trusted verifier

**Entry point.** `python3 .agents/lib/trusted_verify.py --trusted-ci`, run from
`.github/workflows/trusted-review.yml`. Its only option is the required
explicit flag. There is no endpoint, key, policy, or result-file option.

**Trigger and code origin.** The workflow triggers only on `pull_request_target`
(opened, synchronize, reopened, edited, ready_for_review), which per GitHub's
events docs runs the default-branch workflow file. Permissions are `{}` at the
top and `contents: read` / `pull-requests: read` on the job. The job checks
out `${{ github.sha }}` (the default branch) with `persist-credentials: false`.
Its single `run` line has no `${{ }}` interpolation, and the job has no `if:`
(a conditionally skipped job reports success).

**Provider data.** `github_api.py`:
- fixed `https://api.github.com` origin, sending `X-GitHub-Api-Version: 2026-03-10` (from the current REST docs);
- token sent as an unredirected header, and redirects refused;
- `link` header `rel="next"` pagination, restricted to the same origin and bounded to 50 pages;
- an 8 MB response cap;
- 401/403/429/404/5xx, transport, and JSON errors map to `ProviderAuthError`/`ProviderUnavailable`/`ProviderError`, all failing closed;
- the token is redacted from error messages.

**Candidate data.** `refs/pull/N/head` is fetched from
`https://github.com/<policy repository>.git`, with hooks disabled, only the
https protocol allowed, and no tags or submodules. The token goes through
`GIT_CONFIG_*` env only. The candidate is read with `ls-tree`/`cat-file`, and
spec artifacts must be regular blobs.

**Context checks (exit 2).** It refuses to run unless:
- `GITHUB_ACTIONS` is true and the event is `pull_request_target`;
- a token is present;
- the event file is outside the workspace;
- the event repository equals `GITHUB_REPOSITORY`, which equals the policy repository;
- the checkout HEAD equals `GITHUB_SHA` and the tree is clean;
- `GITHUB_REF` is `refs/heads/<base_branch>`, and that branch is the default branch.

**Verification checks (exit 1).** All are listed in `docs/trusted-review.md`:
- the pull request is open, not merged, in the expected repository and base, with the same number;
- its head is a full SHA equal to the event head and to the fetched commit;
- reviews are paginated, the latest decisive state per login wins, and dismissed or ghost reviews never count;
- an allowed, `User`, non-author reviewer approves exactly the head;
- no allowed reviewer has changes requested;
- for each in-scope feature at `in_progress` or `done`: a repository-mode approval naming a PR and a login, spec and task digests computed from the candidate's blobs, and the named login currently approving a commit whose own blobs hash to that digest (on this PR or the named earlier PR);
- for `done`: the closure revision is an ancestor of the head and differs only in state paths, tasks are complete, evidence resolves in that revision's blobs, and `check.sh` passed for it.

The policy always comes from the trusted checkout. `TrustedRepositoryReview`
is built only in memory from provider data and bound to the head.

**Local side.** Repository mode needs a complete `repository_review`
(`provider`, `repository`, `base_branch`, `allowed_reviewers`).
`workflow-approve` needs `--pull-request` and an allowed login. Local gates
return `pending-trusted-verification` and can never return
`provider-verified`; `workflow-check` repeats the label. Closure is consumed
through the required check: the PR carrying the `done` transition merges only
if the trusted run passed for its exact head (`docs/trusted-review.md`,
"How closure consumes the result").

**Tests:**
- `test_trusted_verify.py` (32): a real Git fixture with mocked provider and CI env;
- `test_github_api.py` (17): mocked transport, a loopback HTTP server proving redirect refusal and that the redirect target is never contacted, the size cap, connection failure, and static trust-boundary checks of the workflow YAML;
- `test_review_attestation.py`: forged workspace or HMAC metadata are still rejected.

## Residual gaps and spec impact (state these before checking T13/T15)

1. **External evidence for R15 is still missing.** The workflow has never run;
   no real provider response was seen; the real `git fetch` path is replaced by
   a fake in tests. Two points need confirming in a real repository: that
   `pull_request_target` checks attach to the PR head, and how branch
   protection matches the check name. `actions/checkout@v6` is not SHA-pinned;
   I could not verify a SHA offline, so the maintainer must pin it. The docs
   tell maintainers to re-run the check after approval, because
   `pull_request_target` does not fire on reviews.
   Spec impact: T13 code and configuration exist, and the T13 text's "before
   enabling CI" verification of the real privilege boundary remains a
   maintainer action.
2. **The required-check name is not bound to a workflow.** All Actions jobs
   share one app source. GitHub requires every same-named check to pass, so a
   forged check cannot mask a failure. If the trusted run is absent, though, a
   same-named check from a PR workflow is indistinguishable by name.
   Mitigation is CODEOWNERS on `.github/workflows/` plus required review. This
   is documented, not solved.
3. **Repository-mode closure is merge-gated, not locally gated.** Without the
   required check configured, repository mode authenticates nothing. Locally
   this stays visible only as `pending-trusted-verification`. In repository
   mode the local closing review is still a declared record; the
   authenticated review is the provider approval of the head.
4. **Unmanaged default (finding 4) is intentionally unchanged.** This repo and
   every FRESH export enforce structural gates only (transitions, spec
   artifacts, concurrency, finished tasks, recorded hook failures). FEAT-010's
   own approval file is not machine-validated, because opting in would change
   the shipped FRESH manifest, which the design forbids for this repo.
   Spec impact: the M3 exit criterion holds for opted-in projects only.
5. **Narrow trusted scope.**
   - In the trusted job, lightweight records, feature removals, and policy
     edits are covered only by the required code review.
   - Policy edits take effect after merge.
   - Local role names, reviewer names, and evidence `result` values stay
     declared; only `check.sh` is observed.
6. **Workspace trust.** The workspace is not a trust boundary. Removing
   `team_policy` together with the records is visible in Git; in repository
   mode it needs an approved PR.
7. **Locking and lock file.** The lock is per working tree. Cross-clone
   ownership is M4. `progress/work/.workflow.lock` is ignored here; consumers
   must ignore it themselves, since `.gitignore` is not exported.
8. **Stricter by design.**
   - A deleted committed record blocks until restored (no archive path before M4).
   - Opt-in requires no in-progress features without records.
   - Any `T<n>` or checkbox inside an HTML comment in `tasks.md` is refused.
9. **Still open.**
   - `review_mode` downgrade by editing the policy is mitigated only in
     repository mode, where the trusted job reads the base policy.
   - `AGENTS.md` still describes manual status edits (T23).
   - `check.md`'s `on_check_pass` still calls `run-hooks.sh` directly, since it
     is not feature-scoped.
10. **Untested platforms.** Python 3.8/3.10 and Linux were not executed. The
    `O_NOFOLLOW`/`dir_fd` semantics are POSIX; the CI matrix should confirm.

## Next step

Independent Claude review of this handoff and the code, then Codex
verification. The supervisor decides T11–T15 boxes; T13 depends on gaps 1–3.
