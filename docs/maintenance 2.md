# Maintenance: versions and the installed inventory

## Versions

`.agents/schemas/versions.json` declares the framework release, the format
version of the manifest, work records, and the inventory, and the range each
one supports. `./.agents/bootstrap.sh version` prints them, plus the state of
the installed files.

An unknown format version is refused, not guessed at: every `bootstrap.sh`
command except `help`, `version`, and `brief` stops, and `./check.sh` fails,
naming the supported versions. A manifest with no `version` field predates
versioning and is read as format 1.

## Installed inventory

`./.agents/bootstrap.sh export <dest>` writes `<dest>/.harness/installed.json`:
the framework version installed, the format versions, and for every installed
file a baseline SHA-256 and an owner class.

| Owner class | Meaning | Examples |
|---|---|---|
| `framework` | Maintained by the framework; an update may replace it if you have not changed it | `.agents/lib/`, `.agents/commands/`, `check.sh`, `hooks/run-hooks.sh`, `AGENTS.md` |
| `seed` | Created at install, yours afterwards; an update never replaces it | `feature_list.json`, `.agents/agentic.json`, `DESIGN.md`, `README.md`, `progress/`, `steering/` |

Files the inventory does not list are yours and are never touched. Commit
`.harness/installed.json`; `.harness/backups/` is local and git-ignored.

`bootstrap.sh version` compares each owned file with its baseline and reports
how many are unchanged, modified, missing, or uncertain. It changes nothing.

## Adopting an install that has no inventory

A project installed before inventories existed needs one before it can be updated:

```bash
# in the framework source
./.agents/bootstrap.sh export /tmp/harness-release
# in the project
./.agents/bootstrap.sh inventory-adopt /tmp/harness-release
```

Adoption writes only `.harness/installed.json`, with version `legacy`:

- A file identical to the release is owned, with that baseline.
- A file that differs is recorded as **uncertain**. It may be an older
  framework version or your own edit, and the two cannot be told apart, so
  every update treats it as a conflict and leaves it for you to resolve.
- A file the release does not ship is not recorded.

The project needs the current `.agents/lib/inventory.py`,
`.agents/schemas/versions.json`, and `.agents/bootstrap.sh` to run the command.

## Updating an installed project

Updates are driven from the framework source against a project directory. The
release is a fresh export of the source.

```bash
./.agents/bootstrap.sh update-plan ../my-project                  # changes nothing
./.agents/bootstrap.sh update-apply ../my-project --plan <digest> # the digest the plan printed
./.agents/bootstrap.sh update-restore ../my-project               # undo the last update
```

The plan compares three things per path: the installed baseline, the file as
it is now, and the new release.

| Plan action | When | What apply does |
|---|---|---|
| `replace` | The file still equals its installed baseline | Replaces it |
| `add` | The release ships a new file and nothing occupies the path | Creates it |
| `remove` | The release no longer ships it and you did not change it | Deletes it |
| `current` | It already equals the release | Records the new baseline |
| `keep` | The path is project-owned (`seed`) | Nothing |
| `conflict` | Changed or deleted locally, uncertain baseline, a file of yours at a new path, or a symlink on the way | Nothing. The incoming version is saved under `.harness/backups/<id>/incoming/` for a manual merge |

`update-apply` takes the digest of the plan you reviewed. If the project or
the release changed since then, it stops and writes nothing. Before changing
any file it copies the current versions and the inventory to
`.harness/backups/<id>/` and records a journal there.

If an update is interrupted, the next `update-plan` refuses to run until
`update-restore` has put the project back. Restore refuses to overwrite a file
you edited after the update unless you pass `--overwrite-edits`.

A conflict stays a conflict on every later update until you resolve it. Merge
it by hand so that it equals the release, or declare the file yours:

```bash
./.agents/bootstrap.sh update-keep ../my-project check.sh AGENTS.md
```

`update-keep` marks the paths project-owned; updates never propose them again.
`update-accept ../my-project <path>...` does the opposite: it installs the
release version of the named conflicts, after backing up yours, and
`update-restore` can undo it. Use it for framework internals of a legacy
install that you never customized.

For a project installed before inventories existed, run
`./.agents/bootstrap.sh update-adopt ../my-project` first. It only writes the
inventory, as described above.

Limits: the update does not merge file contents, does not touch Git, hooks
configuration, or generated adapters, and the backup is local to the machine
that applied it. Review `git diff` in the project before committing.
