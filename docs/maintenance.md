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

Update planning, apply, and restore are not implemented yet (FEAT-010 T21).
