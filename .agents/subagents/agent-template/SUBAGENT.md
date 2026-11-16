---
name: agent-template
description: "Template role card. Copy this directory, then say in one sentence what the role does and when to use it (under 160 characters)."
mode: subagent
---

## Mission
[One or two sentences: the problem this role owns in this project, and why it exists.]

## Does
- [A concrete responsibility, written as an action with a visible result.]
- [Another responsibility. Three to six bullets are enough.]

## Does not
- [Work this role hands over, naming the role that takes it.]

## Rules
- Start from `./.agents/bootstrap.sh brief`. Open other files only when the task needs them.
- Never edit an approved spec. Change feature status only through `workflow-transition`.
- [A project rule this role must always follow.]

## Workflow
1. [First step of a typical task.]
2. [Next step. Keep to the steps that differ from other roles.]

## Skills
- [`skill-name` — the situation in which to load it.]

## Done when
- [ ] [An observable result that closes the role's work.]
- [ ] `./check.sh --quiet` passes.

<!--
Keep a role card under 3 KB: it is loaded every time the role acts.
Write it so that any agent CLI can use it: plain Markdown, repository-relative
paths, no tool names or model names of one vendor. Identity and judgement go
in SOUL.md; project-wide conventions go in steering/. Do not repeat them here.
-->
