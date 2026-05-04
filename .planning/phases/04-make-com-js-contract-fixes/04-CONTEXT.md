# Phase 4: Make.com JS Contract Fixes - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure JS edits to the two co-owned Make.com modules (`quizify-mapping.js`, `score-calculations.js`) plus one new Markdown file (`make-scripts/CONVENTIONS.md`). Deliverables:

- **CONTRACT-01** — Remove the dead `record.product_result` ghost line so the JS output object cleanly reflects D-05's hyphenated key.
- **MAKE-FIX-01** — Replace `"peri-menu"` (hyphen, broken) with `"peri_menu"` (underscore, canonical) at `score-calculations.js:213` so peri respondents receive `peri_menopause_menopause` instead of `life_stage_unspecified`.
- **MAKE-FIX-02** — Correct the inverted `activity_profile` condition at `score-calculations.js:247-250` so `data.is_athlete === true` yields `"athlete"` and otherwise yields `"non_athlete"`.
- **MAKE-FIX-03** — Write `make-scripts/CONVENTIONS.md` documenting the tag spelling rule and the three verification approaches.

**Zero Python changes.** No new test toolchain. Independent of Phases 5 and 6.

</domain>

<decisions>
## Implementation Decisions

### Customer-Facing Impact Gates (Pre-merge confirmations)

- **D-04-01 (MAKE-FIX-02 ship gate):** No active Airtable formula, view, or email-segmentation rule currently consumes `activity_profile`. The semantic flip (non-athletes who currently land in `"athlete"` will start landing in `"non_athlete"`) is a **pure correctness fix** with no downstream migration. Ship in Phase 4. Document the historical bug in MILESTONES.md under v1.1 as a behavioral correction.
- **D-04-02 (MAKE-FIX-01 ship gate):** No downstream consumer (Airtable, email template, Make.com filter) currently keys off the broken `"peri-menu"` (hyphen) string or off `life_stage_unspecified` for peri-respondents. Ship the one-character fix cleanly; no downstream coordination required.

### Code Treatment

- **D-04-03 (CONTRACT-01 — ghost line):** Remove `quizify-mapping.js:103` (`product_result: record.product_result || null,`) **entirely**. It is pure dead code; nothing downstream references the `product_result` output key. Do NOT keep the line under any other name; do NOT replace with a comment. The diff is a single deletion.

### Documentation Scope

- **D-04-04 (CONVENTIONS.md scope):** Verification-only / minimal scope. Cover exactly the four items mandated by MAKE-FIX-03 acceptance criterion:
  1. Tag canonical-spelling rule (snake_case underscores throughout `make-scripts/`).
  2. CONTRACT-01 verification approach for the `product-recommendation` passthrough — note that `docs/quizify-submissions.csv` has `product-recommendation: null` for all 42 rows (per Pitfall #12), so a synthetic fixture or hand-edited row is required to observe a non-null passthrough.
  3. MAKE-FIX-01 verification using sample rows 10 (Karen Retamal) and 35 (Javielys Mancilla) — both carry `Perimenopausia` in `menopause_status`.
  4. MAKE-FIX-02 verification using a non-athlete row (`sport_level` not containing "alto").
  Target ~50–80 lines. No Module 1 vs Module 2 architecture explainer, no deployment playbook, no rollback procedure. Matches v1.0's no-frills doc ethos.

### Implementation Constraints (carried forward, not re-asked)

- D-05 hyphen-key convention (`product-recommendation`, `result-logic`, `score-category`, `score-value`) is the source of truth — JS conforms to Python, never the reverse.
- Snake_case underscore is the canonical tag spelling across both JS files. Do not introduce new hyphenated tag identifiers.
- v1.0 manual-verification ethos preserved — no Node test runner, no Jest, no CI on JS in v1.1. MAKE-TEST-01 remains deferred to v1.2 per REQUIREMENTS.md.
- T-PII-01 — CONVENTIONS.md must reference rows by index (row 10, row 35) and column names only; no cell content beyond categorical enum values.

### Claude's Discretion

- Commit grouping inside the phase plan (one commit per fix vs. one bundled JS commit + one docs commit) — planner's call. The four edits are tightly coupled in scope but independent in correctness.
- Exact Markdown structure of CONVENTIONS.md — the four mandated topics can be sections, a checklist, or a short table; whichever reads cleanest at ~50–80 lines.
- Whether to verify rows 10 and 35 actually contain `Perimenopausia` against the current `docs/quizify-submissions.csv` before locking the verification doc — recommended but not gating.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance criteria
- `.planning/ROADMAP.md` §"Phase 4: Make.com JS Contract Fixes" — phase goal, dependencies, four success criteria.
- `.planning/REQUIREMENTS.md` §"Contract Reconciliation (CONTRACT-XX)" and §"Make.com JS Fixes (MAKE-FIX-XX)" — REQ text for CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02, MAKE-FIX-03 with file:line references.

### Project decisions and constraints
- `.planning/PROJECT.md` §"Key Decisions" — D-05 (locked tail-key order), the v1.1 entry confirming `make-scripts/` as co-owned consumer surface, and the manual-verification-only decision.
- `.planning/PROJECT.md` §"Constraints" — T-PII-01 carry-forward (PII-safe stderr).

### Pitfalls and known landmines (high-priority read for planner)
- `.planning/research/PITFALLS.md` §"Pitfall 12" — `product_result` ghost-key context for CONTRACT-01; explains why line 103 is dead code and the synthetic-fixture caveat (sample CSV has all-null `product-recommendation`).
- `.planning/research/PITFALLS.md` §"Pitfall 13" — `peri_menu` vs `peri-menu` mismatch context for MAKE-FIX-01; canonical-spelling rationale.
- `.planning/research/PITFALLS.md` §"Pitfall 14" — `is_athlete` inversion context for MAKE-FIX-02; downstream-impact analysis (the user-confirmation gate is satisfied by D-04-01).
- `.planning/research/PITFALLS.md` §"Pitfall 17" — `score_total` (JS-recomputed) vs `score-value` (Python pass-through) divergence; document-only note for CONVENTIONS.md or MILESTONES.md.

### Files being edited
- `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` — CONTRACT-01 target (line 103 deletion). Currently 187 lines.
- `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` — MAKE-FIX-01 target (line 213) and MAKE-FIX-02 target (lines 247–250). Currently 295 lines.
- `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` — new file from MAKE-FIX-03.

### Verification fixture
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — 42-row sample. Rows 10 (Karen Retamal) and 35 (Javielys Mancilla) carry `Perimenopausia` per REQ MAKE-FIX-03. All rows have `product-recommendation: null` per Pitfall #12 — a synthetic row or hand-edit is required for CONTRACT-01 manual verification.
- `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json` — golden envelope shape; reference for understanding what Module 1 outputs after the fix.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `process_filter_tag(value, needle, tagName)` in `quizify-mapping.js` — already correctly emits `peri_menu` (line ~167). MAKE-FIX-01 fixes the *consumer* (`hasTag(tags, "peri-menu")` at `score-calculations.js:213`), never the emitter. Do not touch the emit side.
- `hasTag(tags, ...)` helper in `score-calculations.js` — exact-match utility used pervasively. The MAKE-FIX-01 fix is a one-character argument change; no helper edits.

### Established Patterns
- Both JS files were authored as Make.com IIFE modules — they expect a single `record` input and return a single `output` object. No imports, no test framework, no build step. The patch surface is intentionally small.
- All emitted tag names in `quizify-mapping.js` use snake_case underscores (`has_red_flags`, `is_athlete`, `peri_menu`, etc.). The hyphen at `score-calculations.js:213` is the only outlier — fixing it harmonizes the module pair.
- `quizify-mapping.js` lines 102 and 103 are stacked dead/live code: line 102 reads the correct hyphenated key; line 103 reads the dead underscore key. Removing line 103 is the only edit CONTRACT-01 requires.

### Integration Points
- Python emits → Make.com Module 1 (`quizify-mapping.js`) reads `record["product-recommendation"]` (D-05). After CONTRACT-01, the JS output object cleanly exposes `product_recommendation` only.
- Module 1 output → Module 2 (`score-calculations.js`) reads `tags` array via `hasTag()`. After MAKE-FIX-01, the `peri_menu` tag emitted by Module 1 is correctly observed by Module 2's life-stage classifier.
- Module 2 output → Airtable / email templates. D-04-01 and D-04-02 confirm no downstream consumer requires migration after MAKE-FIX-01 or MAKE-FIX-02 lands.

</code_context>

<specifics>
## Specific Ideas

- CONVENTIONS.md verification rows are explicitly named: row 10 = Karen Retamal, row 35 = Javielys Mancilla. Use these row numbers verbatim.
- The phase delivers four file changes total: 1 deletion in `quizify-mapping.js`, 1 string change at `score-calculations.js:213`, 1 condition flip at `score-calculations.js:247-250`, and 1 new ~50–80 line `CONVENTIONS.md`. Anything beyond this surface is scope creep.

</specifics>

<deferred>
## Deferred Ideas

- **Make.com Module 1 vs Module 2 architecture documentation** — not in MAKE-FIX-03 scope. If future-you wants a co-ownership reference doc with file roles and the D-05 contract pointer, capture as a v1.2+ docs phase, not in CONVENTIONS.md.
- **Make.com deployment playbook / rollback procedure** — explicitly out of scope per D-04-04.
- **Auditing Airtable formulas / email templates for `activity_profile` and `life_stage` consumers** — D-04-01 and D-04-02 confirmed no consumers exist today. If new consumers are introduced post-v1.1, re-validate before touching these tags.
- **`Reomoto` typo at `score-calculations.js:157`** — MAKE-COSMETIC-01, deferred to v1.2 per REQUIREMENTS.md.
- **Dead-code init `profile = "profile_base"` at `score-calculations.js:217`** — MAKE-COSMETIC-02, deferred to v1.2 per REQUIREMENTS.md.
- **Local Node.js test harness for `make-scripts/`** — MAKE-TEST-01, deferred to v1.2 per REQUIREMENTS.md.
- **`score_total` (JS-recomputed) vs `score-value` (Python pass-through) divergence audit** — Pitfall #17 latent risk. Add as a one-line documentation note in CONVENTIONS.md or MILESTONES.md only; no code change in v1.1.

</deferred>

---

*Phase: 4-make-com-js-contract-fixes*
*Context gathered: 2026-05-03*
