# Contributing

This repository is the Harness SDD framework. A change here reaches every
project on its next update, so each one goes through the same gates the
framework asks of its users.

## Set up

Requires Bash, Git, and Python 3.10 or later. No package is installed.

```sh
git config --local core.hooksPath .githooks   # enables the staged-file size hook
./.agents/bootstrap.sh <your-cli>             # generates your CLI's adapter (git-ignored)
./check.sh --quiet                            # must pass before and after your change
```

The hook rejects a staged authored file above 20,000 bytes. Split the file by
responsibility; do not exempt it. Details: [.githooks/README.md](.githooks/README.md).

## Make a change

1. Branch from `main`. One feature in progress at a time.
2. For a feature with `"sdd": true`, write the spec and wait for a human to
   approve it before implementing: [docs/sdd.md](docs/sdd.md). A small
   maintenance change is registered in `feature_list.json` with `"sdd": false`.
3. Add a regression test under `tests/`. A new suite gets a small `.sh`
   launcher and is registered in `check.sh`.
4. Change capabilities in `.agents/agentic.json` or the templates, never in a
   generated adapter. Re-render and confirm `./.agents/bootstrap.sh --check`
   reports no drift.
5. If the change alters what an adapter delivers, edit
   `.agents/schemas/capabilities.json` and run
   `./.agents/bootstrap.sh capabilities --write`.
6. Open a pull request. CI runs `./check.sh` and the changed-file size gate on
   Ubuntu and macOS with Python 3.10 and 3.13.

Where things are: [docs/framework-workflow.md](docs/framework-workflow.md).
How to extend the manifest, `check.sh`, or add a CLI:
[docs/framework-customization.md](docs/framework-customization.md).

## What a consumer receives

A release is what `./.agents/bootstrap.sh export <dir>` writes. Test a change
against an exported copy, not only against this repository. Files are owned by
the framework or by the project, as recorded in the installed inventory:
[docs/maintenance.md](docs/maintenance.md).

| Topic | Document |
|---|---|
| Versions, inventory, updating a project, rollback, adopting a legacy install | [docs/maintenance.md](docs/maintenance.md) |
| Roles, human authority, review modes, exceptions | [docs/team-policy.md](docs/team-policy.md) |
| Gates behind `/spec`, `/approve`, `/implement`, `/done` | [docs/workflow-contract.md](docs/workflow-contract.md) |
| Trusted repository review and its deployment | [docs/trusted-review.md](docs/trusted-review.md) |
| What each CLI adapter enforces | [docs/compatibility.md](docs/compatibility.md) |
| Quality gateway and context budget | [docs/quality-checks.md](docs/quality-checks.md) |

## Releases

The maintainer of this repository owns releases. Nobody else, human or agent,
tags, packages, or publishes.

1. Set `framework_version` in `.agents/schemas/versions.json`. A change to the
   manifest, work-record, or inventory format adds a format version and keeps
   the previous one in `supported` until a migration exists.
2. Run `./check.sh` and confirm CI is green on `main`.
3. Exercise an update from the previous release with
   `./.agents/bootstrap.sh update-plan` on an exported copy of that release.
4. Tag and publish. Publication is a separate step that requires the
   maintainer's explicit authorization each time.

Security reports: [SECURITY.md](SECURITY.md).
