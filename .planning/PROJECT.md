# Quizify CSV → Webhook JSON

## What This Is

This initiative lives inside the `general-python-scripts` utilities repository. It adds a small Python helper that turns Quizify.io CSV exports (from https://app.quizify.io) into JSON payloads shaped like `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`, so integrations that expect webhook-style records can consume exports without manual rework.

## Core Value

Each CSV submission row becomes one webhook-compatible JSON object with correct contact fields, ordered `question-N` / `answers-N` / `answers-tags-N` keys, scoring-related fields, and tags—including sensible behavior when Quizify omits answer IDs or encodes characters as HTML entities.

## Requirements

### Validated

- ✓ Utilities-repo pattern (folder per helper script, minimal coupling) — existing across this repository

### Active

- [ ] A CLI converts Quizify CSV exports into JSON matching the documented webhook example structure
- [ ] Conversion handles dynamic question columns, trailing score/tag columns, and HTML entities in cells

### Out of Scope

- Changing Quizify’s export format or product behavior — external dependency
- Perfect reconstruction of numeric answer `id` values missing from CSV — document fallback (omit or null) instead of inventing IDs

## Context

- Target payload shape: `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`
- Representative export: `quizify-csv-to-json-webhook/docs/quizify-submissions.csv`
- CSV layout: leading contact columns (`First name`, `Last name`, `Email`, etc.), a block of quiz question columns whose titles vary by quiz, then trailing fields such as `Result logic`, `Score category`, `Score value`, `Answer tags`, `Time to complete`, and `Date`.
- Peer scripts in this repo (Confluence export, GitHub inventory, etc.) stay unrelated; reuse only general Python style conventions.

## Constraints

- **Technology**: Python 3; prefer standard library; add dependencies only when justified
- **Data quality**: Cells may contain HTML entities (`&gt;`, `&lt;`) that must appear as plain characters in JSON strings
- **Privacy**: Treat exports as PII; avoid verbose logging of row contents by default

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Defer full-repo codebase map at init | Narrow deliverable with explicit CSV/JSON fixtures under `quizify-csv-to-json-webhook/docs/` | — Pending (run `/gsd-map-codebase` later if desired) |
| Skip parallel domain research agents during init | Contract files in-repo define mapping expectations | — Pending |
| Workflow prefs from `~/.gsd/defaults.json` | Existing saved defaults (YOLO, balanced models, git-track planning docs) | ✓ Applied |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):

1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. “What This Is” still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):

1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-03 after initialization*
