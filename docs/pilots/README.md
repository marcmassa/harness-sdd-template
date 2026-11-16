# Pilot reports

Version 1.0 needs reviewed reports from two real pilots. A pilot is the
framework used on real work by real people, not a test.

| Context | Who | Report |
|---|---|---|
| `small-team` | At least one human and one agent | Not started |
| `team` | At least two humans using at least two supported CLIs | Not started |

One person may take part in both, but the two reports must describe different
work. No pilot owner has been identified yet; a pilot starts when its human
participants agree to take part.

## What a pilot covers

Each pilot carries out, and reports on, six exercises: installation, one
approved change, a code review, a handoff, an upgrade, and a recovery. It
records a baseline from before the framework, and five measurements:
onboarding time, time waiting for approval, rework, defects found after
closing, and false blocks. It lists every issue left unresolved.

Record only those aggregates. Do not put source code, secrets, or personal
names in a report: participants are named by role. The measurements describe
the framework, and are not used to compare people or agents.

## Writing a report

1. Copy `example-synthetic.json` to `docs/pilots/<pilot-id>.json`.
2. Set `"kind": "real"` and replace every value with what happened.
3. A human who took part reviews it and fills in `human_review`.
4. Validate it:

```bash
./.agents/bootstrap.sh pilot-validate docs/pilots/<pilot-id>.json
```

A report with `"kind": "synthetic"` is accepted by the validator and never
counts as a pilot. `example-synthetic.json` is one; its content is invented.

## Release readiness

```bash
./.agents/bootstrap.sh release-readiness 1.0.0
```

The command reads the repository and lists what is missing. It needs the
milestone tasks checked, CI evidence for the candidate revision in
`releases/<version>/ci.json`, a current compatibility matrix, both real pilot
reports, and no open release-blocking defect in `releases/<version>/defects.json`.
The contracts are in `.agents/schemas/release-evidence.json`.

It never publishes. `ready` means the evidence is complete; tagging,
packaging, and announcing remain separate steps that need the maintainer's
explicit authorization.
