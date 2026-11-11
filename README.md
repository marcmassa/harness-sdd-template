# Harness SDD — Agentic Development Framework

A local-first, CLI-agnostic framework for human/AI collaboration. A canonical
manifest generates native adapters; specifications and session records provide
persistent project context. Human review remains necessary. Supported adapter
entry points: opencode, gemini-cli, claude-code, cursor, and codex.

## Quickstart — 3 steps

### Step 1 — Export the framework into your repo

```bash
./.agents/bootstrap.sh export /path/to/your/repo
cd /path/to/your/repo
```

`export` copies the portable payload and resets feature history. Do not use `cp -r`: that copies this repository's own specs, progress log, and maintainer files.

### Step 2 — Bootstrap the CLI adapter

```bash
./.agents/bootstrap.sh detect --clis   # Observe which CLIs have evidence in this project
./.agents/bootstrap.sh --all           # Proposes target_clis from the evidence and asks you to confirm
./.agents/bootstrap.sh opencode        # Or render just one CLI explicitly
```

The confirmed choice is persisted in `target_clis` inside `.agents/agentic.json`, so `--all` never generates adapters for CLIs the project does not use (a Cursor-only project never gets `CLAUDE.md`/`.claude/` or `GEMINI.md`/`.gemini/`). `./.agents/bootstrap.sh clean` removes stray adapters later.

### Step 3 — Tell your agent to set up the project

```
"Run /init"
```

The agent reads `.agents/commands/init.md`, walks the SCAFFOLD → IMPLEMENT → REMOVE lifecycle, shapes the manifest to your project's sub-agents, and runs `./check.sh`. You supervise; the agent does the work.

That's it. The agent is now operating under the harness.

> **Manual path:** If you prefer to do Step 3 by hand, see [Template Installation Lifecycle](docs/framework-workflow.md#template-installation-lifecycle).

---

## Contributor checks

Requires Python 3 and Bash. The CI target matrix is Ubuntu/macOS with Python
3.10 and 3.13. Local tests alone do not establish remote matrix compatibility.

```sh
git config --local core.hooksPath .githooks
./check.sh
```

The [pre-commit hook](.githooks/README.md) checks staged authored text against
20,000 bytes (5,000 tokens using bytes/4), with explicit generated-file exclusions.
The [quality gateway](docs/quality-checks.md) distinguishes required failures
from optional checks and does not require pytest merely because tests/ exists.

## Documentation

- [Problem, benefits, and current guarantees](docs/framework-overview.md)
- [Workflow, scaffold lifecycle, structure, and commands](docs/framework-workflow.md)
- [Customization and troubleshooting](docs/framework-customization.md)
- [Proposed human/AI team policy](docs/team-policy.md) — awaiting scenario review
- [SDD process](docs/sdd.md)
- [Global architecture](DESIGN.md)
- [Agent navigation and mandatory gates](AGENTS.md)
- [Unknown CLI bootstrap](.agents/BOOTSTRAP.md)
- [Security policy](SECURITY.md)

FEAT-010 is in progress: trusted approvals, automatic evidence completeness,
team handoffs, safe upgrades, and stable-release pilot evidence are not yet
complete. Native plugin packaging (FEAT-009) remains separately unapproved.

## License and authority

See [LICENSE](LICENSE). Maintainer provenance is recorded separately in the
framework source repository.
