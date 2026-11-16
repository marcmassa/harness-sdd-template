# Design — plugin-packaging

> Technical decisions for FEAT-009. The repository becomes a distributable plugin: Claude marketplace + OpenCode TS plugin. Verified schemas: Claude plugin/marketplace reference and OpenCode plugins docs (2026-10-22).

## Summary

The framework integrates in-repo with five CLIs but is distributed by copy. This feature makes the repo itself installable: a Claude marketplace whose single entry (plugin `harness-sdd`) ships the seven SDD commands and the four canonical agents self-contained, and an OpenCode TS plugin that enforces the SDD boundaries (approved specs read-only, generated adapters untouched) via `tool.execute.before`.

Distribution decisions verified against official docs:

- **Entry-as-manifest**: the marketplace entry carries the components; no `.claude-plugin/plugin.json` is generated. Docs: "No `plugin.json`: the entry is the manifest, regardless of `strict`."
- **Relative source `"."`**: the plugin root is the marketplace root. Relative paths resolve because the marketplace is added from GitHub (`github` source type → Claude Code has the files).
- **`harness-` namespacing not needed for commands**: the entry's command map keys become `harness-sdd:<name>` automatically (plugin namespacing).
- **No hooks**: SDD transitions are command-driven; Claude hook events are tool/session-scoped. Same finding as the Cursor adapter (FEAT-008 R4). The gap is documented.
- **Agents from scaffolds**: the shipping manifest is `FRESH`; the plugin must still ship `harness`, `spec-author`, `implementer`, `reviewer`. Stubs are generated from `_template_subagents_examples[]` entries with `category == "canonical"`, inlining `SUBAGENT.md` and `SOUL.md` content so they work in repos without the template.

## Affected Files

| File | Action | Reason |
|---------|--------|-------|
| `.agents/adapters/claude-code/claude-plugin-agents/_template.md.tmpl` | create | Self-contained agent stub template (R3) |
| `.agents/adapters/_common/render.py` | modify | `render_claude` emits `marketplace.json` + agent stubs; `render_opencode` emits the TS plugin (R1–R6) |
| `.claude-plugin/marketplace.json` | create (generated, committed) | The marketplace payload (R1, R2) |
| `.agents/plugin/claude/agents/*.md` | create (generated, committed) | Canonical agent stubs (R3) |
| `.opencode/plugins/harness-sdd.ts` | create (generated, gitignored) | OpenCode enforcement plugin (R5, R6) |
| `.gitignore` | modify | Add `/.opencode/`; keep `.claude-plugin/` and `.agents/plugin/` committed (R7, R1) |
| `.agents/bootstrap.sh` | modify | `clean`/owned set gains `.opencode` (R7) |
| `check.sh` | modify | `detect --clis` mapping (via bootstrap), hygiene owned set, register test (R7, R12) |
| `README.md` | modify | Install section: Claude marketplace + OpenCode plugin (R11); hook-gap note (R10) |
| `.agents/BOOTSTRAP.md` | modify | Output examples gain the new artifacts (R11) |
| `tests/test_plugin_packaging.sh` | create | R1–R12 coverage |
| `check.sh` (test loop) | modify | Register `test_plugin_packaging` |

## Signatures and Structures

### `.claude-plugin/marketplace.json` (generated, committed)

```jsonc
{
  "$schema": "https://json.schemastore.org/claude-code-marketplace.json",  // omit if schema URL unverifiable
  "name": "harness-sdd-template",
  "owner": { "name": "Marc Massa Capó", "email": "marcm117@gmail.com" },
  "description": "Harness SDD — spec-driven, traceable agentic development framework",
  "plugins": [
    {
      "name": "harness-sdd",
      "source": ".",
      "description": "Spec Driven Development workflow: /init, /status, /spec, /approve, /implement, /done, /check plus four canonical agents",
      "commands": {
        "init":      { "source": "./.agents/commands/init.md",      "description": "<from manifest>" },
        "status":    { "source": "./.agents/commands/status.md",    "description": "<from manifest>" },
        "spec":      { "source": "./.agents/commands/spec.md",      "description": "<from manifest>" },
        "approve":   { "source": "./.agents/commands/approve.md",   "description": "<from manifest>" },
        "implement": { "source": "./.agents/commands/implement.md", "description": "<from manifest>" },
        "done":      { "source": "./.agents/commands/done.md",      "description": "<from manifest>" },
        "check":     { "source": "./.agents/commands/check.md",     "description": "<from manifest>" }
      },
      "agents": [
        "./.agents/plugin/claude/agents/harness.md",
        "./.agents/plugin/claude/agents/spec-author.md",
        "./.agents/plugin/claude/agents/implementer.md",
        "./.agents/plugin/claude/agents/reviewer.md"
      ]
    }
  ]
}
```

- Commands iterate `ctx["commands"]` (manifest order, name → map key).
- Agents iterate the `category == "canonical"` scaffolds (stable order: harness, spec-author, implementer, reviewer).
- The `$schema` line is only kept if the schema URL is confirmed; otherwise omit (unknown top-level keys are stripped with a warning — better to omit).
- `owner` values come from `AUTHORITY` (current values above). A renderer should NOT parse AUTHORITY; hardcode the values in the renderer, sourced from the manifest: add optional manifest fields `author: {name, email}` — if absent, fall back to the current constants. Keep it simple: hardcode in `render.py` with a comment; an `author` manifest field is future work.

### Self-contained agent stub (`.agents/plugin/claude/agents/<name>.md`)

```
---
name: {{ item.name }}
description: "{{ item.description }}"
---

# {{ item.name }} — Harness SDD sub-agent (plugin, self-contained)

You are `{{ item.name }}` in the Harness SDD framework.

{{ item.role_content }}

{{ item.soul_section }}
```

Renderer enrichment (in the plugin render path):

```python
def _plugin_agent_item(root, scaffold):
    item = {k: v for k, v in scaffold.items() if not k.startswith("_")}
    role_file = root / item["role_file"]
    item["role_content"] = role_file.read_text() if role_file.exists() else "(role file missing)"
    item["soul_section"] = soul loading (existing load_soul_content + header) if scaffold declares a soul or default path exists
    item["agent_md_path"] = f"./.agents/plugin/claude/agents/{item['name']}.md"
    return item
```

Frontmatter requirement: Claude agent `.md` files need `name` and `description`. The scaffold `SUBAGENT.md` body already starts with its own YAML frontmatter (`name:`, `type:`) — inlining it under our frontmatter means a second `---` block in the body. Claude parses only the first block; the body's block renders as text. Acceptable: the body frontmatter appears as content lines. Sanitize: strip a leading frontmatter block from `role_content` before inlining (regex `^---\n.*?\n---\n`, DOTALL) to avoid confusing dumps.

### OpenCode TS plugin (`.opencode/plugins/harness-sdd.ts`, generated)

```ts
import * as fs from "node:fs"
import * as path from "node:path"

const GENERATED_ADAPTERS = [
  "opencode.json", "opencode.jsonc", "GEMINI.md", "CLAUDE.md",
  ".claude", ".gemini", ".cursor", ".opencode",
]
const SPEC_FILES = new Set(["requirements.md", "design.md", "tasks.md"])

function activeSddFeature(root: string): string | null {
  const p = path.join(root, "feature_list.json")
  if (!fs.existsSync(p)) return null
  try {
    const list = JSON.parse(fs.readFileSync(p, "utf8"))
    for (const f of list.features ?? []) {
      if (f.sdd === true && f.status === "in_progress") return f.name
    }
  } catch {}
  return null
}

function targetPath(root: string, args: unknown): string | null {
  // collect the first string arg that looks like a repo-relative or absolute path
}

export const HarnessSDDPlugin = async ({ directory }: { directory: string }) => {
  return {
    "tool.execute.before": async (input: { tool: string }, output: { args: Record<string, unknown> }) => {
      const tool = String(input?.tool ?? "").toLowerCase()
      if (!["edit", "write", "multiedit", "patch", "apply_patch"].includes(tool)) return
      const rel = targetPath(directory, output.args)
      if (!rel) return
      if (GENERATED_ADAPTERS.some((g) => rel === g || rel.startsWith(g + "/"))) {
        throw new Error(`[Harness SDD] '${rel}' is generated — edit .agents/agentic.json and re-run ./.agents/bootstrap.sh <cli>`)
      }
      const m = rel.match(/^specs\/([^/]+)\/(requirements|design|tasks)\.md$/)
      if (m && SPEC_FILES.has(m[2])) {
        const active = activeSddFeature(directory)
        if (active && m[1] === active) {
          throw new Error(`[Harness SDD] specs/${m[1]}/ is approved and read-only — run /done or update the spec with the human's approval`)
        }
      }
    },
  }
}
```

Notes:
- Zero external deps → no `.opencode/package.json` needed. Node builtins are static imports (Bun-compatible).
- The tools list is defensive: unknown/renamed tools simply skip the guard.
- `.opencode/` is wholly generated → `clean` removes it whole (like `.claude`), `hygiene` warns on stray.
- The specs guard is precise: only the ACTIVE `sdd`-in_progress feature's spec is locked; other specs (e.g. `specs/templates/`) stay editable.

### Rendering integration

`render_claude` gains after the existing writes:

```python
plugin_ok = render_claude_plugin(root, manifest, ctx, check)
```

`render_claude_plugin`:
1. Build `agents` list from canonical scaffolds; write stubs to `.agents/plugin/claude/agents/<name>.md` (write_file → drift-checked).
2. Build the marketplace dict; `json.dumps(..., indent=2)` + newline; write to `.claude-plugin/marketplace.json` (write_file → drift-checked).

`render_opencode` gains: write `.opencode/plugins/harness-sdd.ts` with the plugin source (a module-level constant string in `render.py` — the TS never varies per manifest, so it is a constant template; still drift-checked).

## Algorithm / Flow

```
1. Add the plugin-agent template + _plugin_agent_item enrichment.
2. Extend render_claude with render_claude_plugin (marketplace + stubs).
3. Extend render_opencode with the TS plugin write.
4. Gitignore: add /.opencode/; verify .claude-plugin/ and .agents/plugin/ are committed.
5. clean/detect --clis/hygiene: opencode owned gains .opencode.
6. Docs: README install section, BOOTSTRAP.md step 9, hook-gap note.
7. tests/test_plugin_packaging.sh; register in check.sh loop; re-render; ./check.sh green.
```

## Error Handling

| Condition | Response |
|-----------|-----------|
| Canonical scaffold role_file missing at render | stub body gets `(role file missing)` marker; render does not fail |
| `claude` CLI absent in tests | skip validation assertion, exit 0 |
| Marketplace entry path check | all sources/agents paths are `./`-prefixed and inside the repo root by construction |
| TS plugin with unknown tool name | guard skips (defensive tool list) |
| Consumer repo renders the plugin with zero canonical scaffolds (post `/init` repo) | marketplace entry omits `agents` key when the list is empty |

## Discarded Alternative

**Generate `.claude-plugin/plugin.json` alongside the marketplace.** Discarded: with `plugin.json` present, entry component fields append under strict mode — two sources of the same truth. Entry-as-manifest keeps one generated file per concern and matches the documented marketplace-root pattern. If Anthropic later requires `plugin.json` for relative sources, the renderer gains it in one place.

**Publish an npm opencode plugin now** (`@marcmassa/harness-sdd`). Discarded: publishing is a maintainer action with registry credentials; the repo-local TS plugin delivers the enforcement today, and promoting it to npm later only needs a `package.json` wrapper — documented as the follow-up path.

**Ship skills in the marketplace entry.** Discarded: `.agents/skills/*` is gitignored (skills come from the registry at sync time), so marketplace-served content would be empty; the plugin relies on AGENTS.md/commands instead — documented limitation.

## Risks and Edge Cases

- **`.claude-plugin/marketplace.json` is generated-but-committed** — an exception to the "never commit generated files" rule, required because the marketplace is served from the repository. Drift checks make hand-edits visible: any manual edit fails `bootstrap.sh claude-code --check`.
- The agent stubs inline role content: updating a `SUBAGENT.md` requires re-rendering for the plugin to ship fresh content. The autogen header on each stub says so.
- `claude plugin validate` may warn about unknown fields if schema assumptions drift; the test treats errors as failures and warnings as acceptable.
- The TS plugin reads `feature_list.json` per edit — negligible IO cost, always-current state.
- Bundled plugins installed at user scope add context tokens (names/descriptions only); the plugin ships 7 commands + 4 agents — a modest footprint, noted in README.
- OpenCode `output.args` shapes vary by tool; `targetPath` collects the first plausible path string and returns `null` when none match — the guard is best-effort by design and fails open.
