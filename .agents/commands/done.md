# /done

Run the reviewer on the feature currently in `in_progress` and mark it `done` if all checks pass.

## Steps

1. Read `feature_list.json` and find the feature with `status: "in_progress"`.
2. Run `hooks/run-hooks.sh on_review_start --feature-id "<feature_id>" --feature-name "<feature_name>" --agent-name "reviewer"`.
3. Verify the `R<n> ↔ test` table in `progress/impl_<feature>.md` is complete.
4. Run `./check.sh`. It must pass with no errors.
5. Inspect `git status` and `git diff` — only files declared in `specs/<feature>/design.md` "Affected Files" should be touched.
6. Look for: debug `print()`s, TODO comments without context, hardcoded secrets, stray files.
7. Run `hooks/run-hooks.sh on_review_complete --feature-id "<feature_id>" --feature-name "<feature_name>" --agent-name "reviewer"`.
8. On success:
   - Update `feature_list.json`: `status: "done"`.
   - Run `hooks/run-hooks.sh on_feature_done --feature-id "<feature_id>" --feature-name "<feature_name>"`.
   - Append a summary entry to `progress/progress.md` (format: `{date} | {type} | {title} | {files} | {next}`).
9. On failure: report the defects and leave the feature in `in_progress`.

## Guardrails

- Do not mark `done` if `./check.sh` fails.
- Do not mark `done` if any R<n> is missing a test.
- Do not mark `done` if the diff touches files outside the declared scope.
