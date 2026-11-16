# Decisions

Technical decisions log (lightweight ADR style).

## Format

### ADR-{N}: {Decision Title}
- **Status:** {Accepted / Proposed / Rejected / Superseded by ADR-N}
- **Context:** {Why was this decision needed?}
- **Decision:** {What was decided?}
- **Impact:**
  - Positive: {expected benefits}
  - Cost: {trade-offs or costs}
- **Discarded Alternatives:**
  - {Alternative A}: {reason for discard}
  - {Alternative B}: {reason for discard}

---

*[Decisions are added at the top, in reverse chronological order]*

### ADR-2: FEAT-010 runs M5 (distribution and updates) before M4 (shared work)
- **Status:** Accepted — human decision in chat, 2026-11-11
- **Context:** The approved spec orders the milestones M1 to M6. The framework is
  in use in several projects, each on a different framework version, and every
  improvement is ported by hand. M4 addresses multi-owner worktrees and handoffs,
  which those projects do not need yet.
- **Decision:** Execute T20–T24 (M5) before T16–T19 (M4). Task text, requirements,
  and design are unchanged; only the execution order differs. `tasks.md` is not
  edited, so its approved digest still holds.
- **Impact:**
  - Positive: consumers get versioned, non-destructive updates sooner.
  - Cost: R23's ownership and revision records (T16) arrive after the version
    formats (T20), so T20 must leave room for them.
- **Discarded Alternatives:**
  - Keep the approved order: delays the update path, the largest practical gap.
  - Edit `tasks.md` to reorder: changes approved task text for no added control.

### ADR-1: Bind the approved spec by digest without a team policy
- **Status:** Accepted — human decision in chat, 2026-11-11
- **Context:** "Never edit the approved spec" was verified only under an active
  `team_policy`. The default mode, used by this repository and every export,
  accepted silent edits to an approved spec.
- **Decision:** On the move to `in_progress`, store `spec_approval` (spec and
  task-structure digests) on the feature in `feature_list.json`. `check.sh` and
  the `done` transition fail if the spec changes while the feature is in
  progress. `workflow-approve --reviewer --evidence-ref` rebinds a changed spec
  after a human approves it.
- **Impact:**
  - Positive: the rule holds in every project with no extra ceremony.
  - Cost: it is a declared record in an editable file, not authentication.
    Features started earlier carry no digest and are not verified. Closed
    features are not re-verified, so specs may be archived after `done`.
- **Discarded Alternatives:**
  - Require `team_policy` for any integrity check: too heavy for small projects.
  - Verify `done` features forever: blocks archiving old specs.
