# Implementation report — portable-template (FEAT-006)

## Traceability R<n> ↔ Test

| Requirement | Test | Type | File |
|-------------|------|------|------|
| R1 | shipping manifest is FRESH | shell | tests/test_portable_template.sh |
| R2 | shipping manifest is FRESH | shell | tests/test_portable_template.sh |
| R3 | templates SOUL.md kept | shell | tests/test_portable_template.sh |
| R3 | T9 fixture Agent Soul | shell | tests/test_soul_md.sh |
| R4 | default_agent omitted unless active | shell | tests/test_portable_template.sh |
| R5 | default_agent omitted unless active | shell | tests/test_portable_template.sh |
| R6 | consecutive --all runs left agentic.json unchanged | shell | tests/test_portable_template.sh |
| R7 | consecutive --all runs left agentic.json unchanged | shell | tests/test_portable_template.sh |
| R8 | consecutive --all runs left agentic.json unchanged | shell | tests/test_portable_template.sh |
| R9 | hook examples are real and inactive | shell | tests/test_portable_template.sh |
| R10 | empty active hook fails check.sh | shell | tests/test_portable_template.sh |
| R11 | exported tree check.sh exits 0 | shell | tests/test_portable_template.sh |
| R12 | active TODO steering fails check.sh | shell | tests/test_portable_template.sh |
| R13 | scaffold TODO files do not fail a FRESH tree | shell | tests/test_portable_template.sh |
| R14 | exported tree check.sh exits 0 (terraform installed, no *.tf) | shell | tests/test_portable_template.sh |
| R15 | shipping ./check.sh subagent section | shell | ./check.sh |
| R16 | detect lists three CLIs | shell | tests/test_portable_template.sh |
| R17 | project stack is labeled | shell | tests/test_portable_template.sh |
| R18 | export refused a non-empty destination | shell | tests/test_portable_template.sh |
| R19 | export payload present | shell | tests/test_portable_template.sh |
| R20 | export omitted framework history | shell | tests/test_portable_template.sh |
| R21 | exported feature list is a single pending example | shell | tests/test_portable_template.sh |
| R22 | exported progress is a template | shell | tests/test_portable_template.sh |
| R23 | SECURITY.md names the project | shell | tests/test_portable_template.sh |
| R24 | SECURITY.md + export feature list | shell | tests/test_portable_template.sh |
| R25 | ./check.sh exit 0 on this repository | shell | ./check.sh |
| R26 | exported tree check.sh exits 0 | shell | tests/test_portable_template.sh |
| R27 | adopted tree is INITIALIZED and check.sh exits 0 | shell | tests/test_portable_template.sh |
| R28 | add-agent scaffolded SOUL.md | shell | tests/test_portable_template.sh |
| R29 | GEMINI.md does not hardcode the harness default | shell | tests/test_portable_template.sh |
| R30 | fixture global steering injected into instructions | shell | tests/test_steering.sh |

## Notes

- `add-agent` now drops `category` as well as `_lifecycle` and `_intent`. Without that, a promoted scaffold fails the init gate and R27 cannot go green.
- `check.sh` hook and steering validators no longer swallow the Python exit code with `|| true`. Active empty hooks and `<!-- TODO` steering now fail the gate.
- Shipping manifest is `FRESH`. `./check.sh` reports that as information, not a failure.
- T17 and T18 are left for the reviewer. Status remains `in_progress`.
