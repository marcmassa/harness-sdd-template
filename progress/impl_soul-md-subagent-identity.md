# Implementation — soul-md-subagent-identity (FEAT-005)

## Traceability R↔Test

| Requirement | Test | Type | File |
|-------------|------|------|------|
| R1 — Estructura canónica de SOUL.md | T11: agent-template/SOUL.md tiene cuatro secciones | shell | tests/test_soul_md.sh |
| R2 — Ubicación por subagente | T10: check.sh detecta SOUL.md ausente | shell | tests/test_soul_md.sh |
| R3 — Declaración en agentic.json | T12: retrocompatibilidad sin campo soul | shell | tests/test_soul_md.sh |
| R4 — Renderizado por bootstrap | T9: stub claude contiene ## Agent Soul | shell | tests/test_soul_md.sh |
| R5 — Template de scaffold | T11: agent-template/SOUL.md tiene estructura canónica | shell | tests/test_soul_md.sh |
| R6 — Validación en check.sh | T10: exit code != 0 cuando falta SOUL.md | shell | tests/test_soul_md.sh |
| R7 — Guía en /init | Verificación manual: sección 3e añadida en init.md | manual | .agents/commands/init.md |
| R8 — Subagente templates como referencia | T9: contenido real en templates/SOUL.md renderizado | shell | tests/test_soul_md.sh |
| R9 — DESIGN.md como meta-plantilla | Verificación manual: DESIGN.md poblado con meta-contenido | manual | DESIGN.md |
| R10 — Sin breaking changes | T12: load_soul_content sin campo soul retorna "" sin error | shell | tests/test_soul_md.sh |

## Files Changed

| File | Action |
|------|--------|
| `.agents/subagents/agent-template/SOUL.md` | created |
| `.agents/subagents/templates/SOUL.md` | created |
| `.agents/agentic.json` | modified — campo `soul` en templates |
| `.agents/adapters/_common/render.py` | modified — load_soul_content, build_context, render_opencode |
| `.agents/adapters/claude-code/claude-agents/_template.md.tmpl` | modified — {{ item.soul_section }} |
| `.agents/commands/init.md` | modified — sección 3e + gate + mistake 8 |
| `check.sh` | modified — SOUL.md validation + test_soul_md |
| `DESIGN.md` | modified — contenido meta completo |
| `tests/test_soul_md.sh` | created |
| `.claude/agents/templates.md` | regenerated |
| `CLAUDE.md` | regenerated |
| `GEMINI.md` | regenerated |
| `.claude/commands/init.md` | regenerated |

## Notes

- El fallo de Init Validation en check.sh (state=PARTIAL) es preexistente:
  el template no ha pasado por /init, que es el estado normal de este repo.
  No es un fallo introducido por FEAT-005.
- test_soul_md.sh: 4/4 passing (T9, T10, T11, T12).
