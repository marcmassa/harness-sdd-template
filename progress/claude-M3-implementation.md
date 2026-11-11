# Claude M3 implementation handoff — for independent review

Scope: FEAT-010 T11 and T12–T15, 2026-11-09. Stopped here as instructed.
Nothing was staged, committed, or pushed. FEAT-010 stays `in_progress`; task
boxes were not changed; `requirements.md` and `design.md` still match the
digests in `approval_FEAT-010.json`.

## Status by task

| Task | Status | Note |
|---|---|---|
| T11 | Implemented | Commands use shared gates; adapters rerendered |
| T12 | Implemented | Records, digest, transitions, journal, hook recovery |
| T13 | **Partial** | Local mode done. Trusted repository mode fails closed; keep unchecked |
| T14 | Implemented | Requirements, evidence, revision, review, tasks |
| T15 | Implemented | Wired into commands and `check.sh`; repository path blocked by T13 |

## Results

- `tests/test_m3.sh`: 179 tests pass (default interpreter, Python 3.15.2).
- `./check.sh`: exit 0, 12 suites, adapter drift check passes.
- `team_policy.py --scenarios ... --root .`: real accepted scenarios match their record.
- `workflow-validate FEAT-010 --target done`: correctly rejected, tasks T11–T32 unfinished.
- Changed files are at most 20,000 bytes; Python parses under the 3.8 grammar.
  Python 3.8 and the 3.10/3.13 CI matrix were not executed here.

## Files

New: `.agents/lib/{git_state,provider_review,workflow_ops,workflow_store}.py`,
`.agents/schemas/work-record.json`, `docs/workflow-contract.md`, `tests/test_m3.sh`,
`tests/{workflow_support,test_workflow_state,test_workflow_recovery,test_workflow_commands,test_review_attestation,test_evidence_gate}.py`.

Rewritten from the OpenCode draft: `.agents/lib/{approval,evidence,workflow,workflow_cli}.py`.

Changed: `.agents/lib/team_policy.py`, `.agents/bootstrap.sh`, `check.sh`,
`.agents/commands/{spec,approve,implement,done,status,check}.md`,
`docs/team-policy.md`, `docs/framework-workflow.md`, and this progress report.
`opencode.json`, `GEMINI.md`, `CLAUDE.md`, `.claude/`, `.gemini/` were regenerated
through bootstrap. They are stubs that point at canonical bodies.

## Interfaces

All through `./.agents/bootstrap.sh`: `spec-digest` and `workflow-{validate,
transition,init,approve,scope-change,evidence,run-checks,review,recover,rollback,check}`.
Details and opt-in steps are in `docs/workflow-contract.md`. `bootstrap.sh` documented
these before, but the draft never dispatched them.

Manifest (optional): `team_policy`, `team_policy_scenarios`. Policy (optional):
`max_concurrent`, `historical_features`, `repository_review`.

## Codex findings

| Finding | Fix | Regression |
|---|---|---|
| Evidence symlink escape | Real-path containment, read from the commit | `test_codex_reproduction_symlink_file_escape_rejected`, external dir, internal link |
| Unparsed pending task | Every checkbox parsed; malformed lines rejected | `test_codex_reproduction_unbolded_pending_task_blocks`, `TaskParsingTests` |
| `record=None` completion | Active policy always loaded from repository | `test_none_record_cannot_complete_under_active_policy` |
| Deleted record | Detected, with explicit `historical_features` | `test_deleting_opted_in_record_blocks_mutation_and_check` |
| Another feature's `spec_dir` | Must equal `specs/<name>`; symlinks refused | `test_spec_dir_of_another_feature_rejected` |
| `maxConcurrent` | Enforced in mutations and check; policy override | `ConcurrencyTests` |
| Pending hook gates | Blocks implementation and closure | `test_pending_hook_blocks_implementation_gate_and_closure` |
| Test symbol must exist | AST or function lookup in commit blob | `test_symbol_must_exist` |
| Revision shape only | Must be real commit, ancestor, or HEAD | `test_arbitrary_revision_shape_rejected` |
| Two-file atomicity | Write-ahead journal, detection, rollback | `JournalTests` |
| Repository attestation | HMAC removed; workspace data has no entry point | `RepositoryModeTests` |

## Found beyond the notes

- `check.sh` masked feature-list errors with `|| true`, so a status failure could pass. Fixed.
- `export` shipped the maintainer's accepted `human_review` entries. Export now writes
  null reviews; `docs/team-policy/example.json` is refused as an active policy.
- `--policy` and `--record` let callers select an easier gate. Both removed.
- Deleting a pending task from `tasks.md` would have passed; a checkbox-blind task digest now catches it.

## Limitations to weigh

1. **R15 / T13 not fulfilled.** `provider_review.py` is evaluated only against
   captured-format fixtures and no command calls it. No live API was used. Enabling
   it needs a privileged trusted job, its result channel, allowed reviewers, and a
   maintainer-reviewed privilege boundary. GitHub reviews carry no spec digest.
2. **Local identities are declared.** Reviewer names, roles, evidence `result`,
   and references are whatever the caller states. Only `check.sh` is observed.
3. **Workspace is not a trust boundary.** Removing `team_policy` and records together
   is visible in Git, not prevented.
4. Recovery is rollback-only. Roll-forward was omitted so a forged journal cannot apply a state.
5. Evidence binds to one HEAD, so any later commit requires re-recording it.
6. The transition requires a commit-matching tree, with `progress/` and
   `feature_list.json` exempt because they hold workflow state.
7. `AGENTS.md` (22,079 bytes) was not edited because that would violate R29; its §4
   still describes manual status edits until T23.
8. `.agents/schemas/{team-policy,release-evidence}.json` were not created (M5/M6).
   R23 is only partly addressed. No work record exists for FEAT-010 itself, since
   this repository keeps its FRESH manifest without opting in.
9. `progress/delegation_FEAT-010.json` appeared during the run; it is not from this session.

## Next steps

1. Independent Claude review of this handoff.
2. Supervisor checks T11, T12, T14, T15 if accepted, and leaves T13 unchecked.
3. Maintainer decides how to obtain trusted provider verification.
4. M4 begins only after that review.
