# Independent review: FEAT-010 M2/M3

**Verdict: REQUEST_CHANGES.** T11, T12, T14 and T15 should not be checked yet. T13 is not implemented.

**I did not run `./check.sh` or any test suite.** This session was in plan mode, which allows read-only actions only. `check.sh` and the test suites write generated adapters and fixtures, so I couldn't run them, and none of the 179 passing tests from the implementer's report was verified by me. All repro steps below come from reading the code, plus in-memory probes of pure functions. I wrote no plan file and no `/tmp` fixtures, since only read-only tools were available.

## Findings, by severity

**1. High: `historical_features` lets a feature skip strict policy at any status.**
- **Where:** `.agents/lib/workflow_ops.py:372-378` exempts any listed feature id without checking its status. `team_policy.py:43-45` only checks the field's type. `docs/workflow-contract.md:20-21` says the list is for "features already closed before adoption", but nothing checks that.
- **Repro:** with a policy active, edit `feature_list.json` so FEAT-X is `done` (or `in_progress`) with no work record, and add FEAT-X to `historical_features`. `workflow-check` and `check.sh` then pass.
- **Test:** `tests/test_workflow_state.py:222-229` asserts that this passes for a feature that was just flipped to `done`.
- **Impact:** a policy edit, not a recorded decision, gives a new way to bypass strict mode. The list should be limited to `done` features and tied to the revision where the policy was adopted.

**2. High: a full-SDD feature can be downgraded to lightweight, or get its record created late.**
- **Where:** `create_record` (`workflow_ops.py:175-199`) accepts whatever status the feature already has. It fills in all risk flags as `False` itself (`:191`), so the "explicit false risk flags" check (`workflow.py:195-197`) checks nothing anyone declared.
- **Where:** `_validate_lightweight` only checks the intake fields up to `in_progress` (`workflow.py:201-205`). At `done` it accepts a non-human closing review (`require_human=False`, `:209`).
- **Repro:** take an `sdd:true` feature that is `in_progress` with no approval. Set `sdd:false`, delete its record (or never create one), then run `workflow-init --scope … --risk-rationale … --author-role … --no-high-risk`. `check.sh` passes, and `done` needs only an agent-role reviewer.
- **Impact:** no human authorizes the classification, so R8/R9 can be bypassed. The design's "disputed classification stays blocked" rule is not enforced.

**3. Medium: deleting `feature_list.json` skips the strict workflow check entirely.**
- **Where:** `check.sh:205` only warns `feature_list.json not found — skipping` and leaves the exit code alone. That skips `workflow-check` even when `team_policy` is active.
- **Fix:** if `.agents/agentic.json` declares `team_policy`, a missing feature list should fail.

**4. Medium: in the default unmanaged mode (this repo and every export), R13/R16/R17 are not enforced.**
- **Where:** `check_repository` returns `[SKIP]` (`workflow_ops.py:351-354`). `_validate_unmanaged` only checks tasks at `done` (`workflow.py:130-133`): no approval digest, evidence, `check.sh` result or review.
- **Impact:** `progress/approval_FEAT-010.json` is never read by any validator. Editing FEAT-010's `requirements.md` would pass `check.sh`, and FEAT-010 itself could be moved to `done` once its tasks are checked.
- The output is honestly labeled, but the M3 exit criterion ("stale approval and incomplete evidence prevent completion") does not hold for the framework's own feature or for default consumers. That needs to be stated before T15 is checked.

**5. Medium: "named test reference must exist" is weak outside `.py` and `.sh` files.**
- **Where:** `evidence.py:80-84` treats any filename containing "test" as a test file (probe: `docs/latest.md` → True). Any file under `tests/` also counts.
- **Where:** for other extensions, `evidence.py:117` only looks for the symbol as a word (probe: `tests/README.md::passed` → True, and `tests/fixtures/x.json::ok` → True).
- **Impact:** automated evidence can point at prose or data files.

**6. Medium–Low: concurrency gaps and lost updates.**
- `mutate_transition` reads the record (`workflow_ops.py:141`) and builds `new_record`. `commit_transition` then reads the "before" text from disk at `:163`. Anything written in between is silently overwritten and journaled as if it were the prior state.
- `_save` (evidence, review, approve, scope-change) has no lock and no journal.
- The `maxConcurrent` check (`workflow.py:89-97`) has a race: two different features can both pass validation before either writes. The `O_EXCL` journal only serializes the write phase.
- `_settle_hooks` (`:109-130`) overwrites anything a hook wrote to the record.

**7. Low–Medium: task parsing can hide tasks when there is no task digest (unmanaged mode).** These probe inputs passed `validate_tasks` even though they contain unfinished tasks:
- `> - [ ] T2` (blockquote)
- `<!-- - [ ] T2 -->` (HTML comment)
- `1. T2 do it` (numbered, no separator)

In strict mode, `task_structure_digest` catches these edits relative to the approved text.

**8. Low: failed hooks are not always surfaced.**
- `check_repository` never inspects `pending_hook` on a `blocked` feature (`workflow_ops.py:366-369`).
- Without a work record, a failed required hook is not saved (`:118-119`), only an exit code of 1.
- The `on_review_*` hooks in `.agents/commands/done.md` run outside the workflow, so their failures are not recorded.

**9. Low: symlinks around work records.**
- `check_repository` loads records found by glob without checking for symlinks (`workflow_ops.py:357-358`), while `read_record` does refuse them.
- If `progress/work/` is itself a symlink, atomic writes and the journal land outside the repo.

**10. Low: an extra stale evidence entry can never be removed.** Every entry must match the candidate revision (`evidence.py:178-181`). Entries are only replaced per (requirement, source) (`workflow_ops.py:255-257`), and no command removes one. A renamed test therefore blocks closure until the JSON is edited by hand. This fails closed, so it is not a bypass, but it makes "multiple records per requirement" fragile.

**11. Already disclosed, still open:**
- `review_mode` comes from an editable policy file, so repository mode can be downgraded to local by editing it.
- The exported `AGENTS.md` still tells agents to edit status by hand.
- Reviewer names, evidence `result` values and closing reviews are all declared. Only the `check.sh` result is actually observed.

## T13 / trusted repository approval: not implemented

Repository mode does fail closed:
- `workflow_ops.py:205` refuses non-local approvals.
- `approval.py:69-70` requires an in-memory `TrustedRepositoryReview` object, which no command ever creates.
- `workflow_cli.py` has no option for an attestation file.

So workspace JSON or a self-supplied HMAC key cannot satisfy it. But nothing connects to a provider: `.github/workflows/ci.yml` has no trusted review job. `evaluate_github_review` is only checked against captured fixtures, and it does not check the PR's state, base branch or whether the head comes from a fork. R15 is unmet, and T13 and the M3 exit must stay unchecked.

## Checks that held up (code reading and hashes)

- **Approved spec unchanged:** `requirements.md` and `design.md` match the SHA-256 values in `progress/approval_FEAT-010.json`. With `[x]` reset to `[ ]`, `tasks.md` hashes to the approved `30f1f94e…`, so only checkbox markers changed.
- **FEAT-009** is still `spec_ready`.
- **Manifest:** `.agents/agentic.json` is unmodified and has no `team_policy`, so the FRESH manifest is not initialized.
- **File sizes:** the largest changed authored file is `workflow_ops.py` at 18,812 bytes; all are ≤ 20,000.
- **Spec and revision binding:**
  - `spec_dir` must equal `specs/<name>`, and symlinked spec directories or artifacts are refused.
  - The record's revision must be a real commit, and `approved_revision` must be an ancestor of the candidate.
  - Closing evidence, checks and review must all match the candidate revision.
  - A strict `done` requires a clean tree, with `progress/` and `feature_list.json` exempt.
- **Missing record:** with a policy active, a missing record or a `None` record blocks transitions.
- **Failed hooks:** a failed required hook leaves a pending event that blocks everything except a move to `blocked`.
- **Recovery:** it is rollback-only, and rollback refuses if a file changed since the crash.
- **Export:** scenario reviews are reset to null, and `progress/approval_M2-scenarios.json` is not exported.

## Commands actually run (all read-only)

- `git diff --stat`, `git status --short`, `wc -c`, `shasum -a 256` on the spec files and on the `tasks.md` with markers reset (matches approved hash)
- `sed`/`grep` over `bootstrap.sh`, `check.sh`, `render.py` and `ci.yml`; Python one-liners reading `feature_list.json` and `agentic.json`
- In-memory probes with `python3 -B` of `evidence._is_test_path`, `_symbol_exists`, `validate_tasks` and `approval.task_structure_digest`; results quoted above

**Not run:** `./check.sh`, `tests/test_m3.sh`, the other suites, and any disposable fixtures for findings 1–3, 6 and 9. Those repros are code-traced, not executed.

**Verdict: REQUEST_CHANGES for M2/M3.** Fix findings 1–3 with tests that exercise the attack, and either enforce finding 4 or state it explicitly as a limit of M3. T13 stays unchecked until a trusted provider verifier exists.
