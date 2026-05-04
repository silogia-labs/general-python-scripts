# Phase 2: Core webhook mapping — Discussion Log

**Discussion date:** 2026-05-03
**Mode:** discuss (default), `--chain`

This log is for human reference only (audits, retrospectives). Downstream agents read CONTEXT.md, not this file.

## Areas Selected for Discussion

All four gray areas presented were discussed in a single batched round (default mode, batched questions per area).

---

## Area 1 — Per-question `answers-tags-N` distribution

**Question:** How should the single CSV `Answer tags` column populate the per-question `answers-tags-N` keys?

**Options presented:**

1. Heuristic match by tag prefix/keyword
2. Configured per-question tag map (static index map)
3. All tags on every question (replicate)
4. Empty per-question, expose row-level field

**User selection:** **Option 1 — Heuristic match by tag prefix/keyword**

**Follow-up — heuristic mechanism:**

- a. Configured tag→keyword map (substring match against header text)
- b. Pure token similarity (no config)
- c. External JSON map file

**User selection:** **a. Configured tag→keyword map**

**Captured in CONTEXT.md as:** D-01, D-02, D-03, D-04

---

## Area 2 — Answer shape (string vs array of objects)

**Question:** When does `answers-N` become an array of objects vs a plain string?

**Options presented:**

1. Comma-in-cell heuristic
2. Configured free-text question list
3. Always object array
4. Always plain string

**User selection:** **Option 1 — Comma-in-cell heuristic**

**Follow-up — `id` fallback (per WEB-03 / PROJECT.md "omit unknown id"):**

- a. Omit `id` key entirely
- b. Emit `id: null`
- c. Always include `answer_img`/`answer_tag` null

**User selection:** **a. Omit `id` key entirely** (combined with always-include `answer_img: null, answer_tag: null` per CONTEXT D-06)

**Captured in CONTEXT.md as:** D-05, D-06, D-07, D-08

---

## Area 3 — Empty / blank cells

**Question:** How should empty/blank dynamic cells be emitted?

**Options presented:**

1. Emit all keys; empty answers-N=""
2. Skip empty cells entirely
3. Emit question-N only when answered, but keep N stable

**User selection:** **Option 1 — Emit all keys; empty answers-N=""**

**Captured in CONTEXT.md as:** D-09

---

## Area 4 — `status`, `statusDate`, top-level `tags`

**Question:** How are top-level subscription/marker fields populated?

**Options presented:**

1. status from `Subscribed`; tags = source marker only
2. Same + merge `Answer tags` into top-level `tags`
3. status configurable via flag

**User selection:** **Option 1 — status from `Subscribed`; tags = source marker only**

**Note:** Unmatched tags from the per-question heuristic (Area 1, D-01) still flow into top-level `tags` as a fallback to avoid silent loss — this is consistent with Option 1's intent (no config, no flag) and was added to CONTEXT.md as D-13.

**Captured in CONTEXT.md as:** D-10, D-11, D-12, D-13

---

## Area 5 — Output destination

**Question:** Where does the JSON go, given Phase 1's stdout-for-data convention?

**Options presented:**

1. Default stdout, `-o/--output PATH` to write file
2. Required `--output PATH`
3. Stream NDJSON to stdout, `--array` for file

**User selection:** **Option 1 — Default stdout, `-o/--output PATH`**

**Captured in CONTEXT.md as:** D-16, D-17

---

## Area 6 — CLI integration with Phase 1

**Question:** Phase 1 chose 'single argparse entrypoint, no subcommands'. How to integrate Phase 2's JSON conversion?

**Options presented:**

1. Same script, add `--emit-json` (default) and keep `--dry-run`
2. Promote to subcommands now
3. New companion script

**User selection:** **Option 1 — Same script, default JSON, keep `--dry-run`**

**Captured in CONTEXT.md as:** D-15, D-16, D-18

---

## Claude's Discretion (recorded for reference)

- Internal helper module organization
- Exact log message wording
- Whether `html.unescape` is wrapped in a memoized helper
- Whether the tag-map dict lives at module top level or inside a small dataclass

## Deferred Ideas Surfaced

- Per-quiz tag-map JSON config file (`--tag-map path.json`) — defer until second quiz appears
- `--status-column` / `--status-map` overrides — defer until real CSV variants force the flexibility
- Subcommands — revisit in Phase 3 if parser pressure grows
- ID recovery from a Quizify question-bank export — out of v1 scope

---

*Phase: 2 — Core webhook mapping*
*Discussion log written: 2026-05-03*
