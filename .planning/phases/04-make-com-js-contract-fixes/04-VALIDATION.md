---
phase: 4
slug: make-com-js-contract-fixes
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-03
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. JS-only edits with shell-grep gates as the deterministic verification layer; Make.com runtime confirmation is manual.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | shell (grep + test) — no Node test runner in v1.1 (MAKE-TEST-01 deferred) |
| **Config file** | none — gate commands are inline one-liners |
| **Quick run command** | `bash .planning/phases/04-make-com-js-contract-fixes/gates.sh` (planner emits this) |
| **Full suite command** | same as quick — phase has no per-task vs full distinction |
| **Estimated runtime** | <1 second |

---

## Sampling Rate

- **After every task commit:** Run the relevant grep gate(s) for that task (per-task command in the Verification Map below).
- **After every plan wave:** Run all 7 grep gates from RESEARCH.md §"Validation Architecture".
- **Before `/gsd-verify-work`:** All 7 grep gates green AND CONVENTIONS.md exists AND user has performed Make.com manual verification per CONVENTIONS.md.
- **Max feedback latency:** <1 second (grep against ~480 LOC of JS)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-XX | 01 (CONTRACT-01) | 1 | CONTRACT-01 | — | `product_result` dead key removed; `product_recommendation` retained | shell-grep | `grep -c "product_result" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` → `0` AND `grep -c "product_recommendation" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` → `1` | ✅ | ⬜ pending |
| 04-02-XX | 02 (MAKE-FIX-01) | 1 | MAKE-FIX-01 | — | Hyphenated `"peri-menu"` removed from consumer; underscore emitter unchanged | shell-grep | `grep -c '"peri-menu"' quizify-csv-to-json-webhook/make-scripts/score-calculations.js` → `0` AND `grep -c "peri_menu" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` → `1` | ✅ | ⬜ pending |
| 04-03-XX | 03 (MAKE-FIX-02) | 1 | MAKE-FIX-02 | — | Inverted `!data.is_athlete` removed; correct `data.is_athlete` present | shell-grep | `grep -c '!data.is_athlete' quizify-csv-to-json-webhook/make-scripts/score-calculations.js` → `0` AND `grep -c 'if (data.is_athlete)' quizify-csv-to-json-webhook/make-scripts/score-calculations.js` → `1` | ✅ | ⬜ pending |
| 04-04-XX | 04 (MAKE-FIX-03) | 2 | MAKE-FIX-03 | T-PII-01 | CONVENTIONS.md exists with the 4 mandated topics; PII-safe (row indices + categorical values only) | shell + grep | `test -f quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` AND `grep -q "snake_case" CONVENTIONS.md` AND `grep -q "row 10" CONVENTIONS.md` AND `grep -q "Perimenopausia" CONVENTIONS.md` AND `grep -q "non_athlete" CONVENTIONS.md` AND `grep -q "product-recommendation" CONVENTIONS.md` | ✅ (after task) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

No test framework install, no fixture files, no shared conftest needed. The grep one-liners are self-contained. CONVENTIONS.md is created by MAKE-FIX-03 itself, not a Wave 0 prereq.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Make.com Module 1 outputs `product_recommendation: "<value>"` (non-null) when given a synthetic record with `record["product-recommendation"]` set | CONTRACT-01 (success criterion #1) | Make.com runtime cannot be invoked from shell; CSV sample contains no `product-recommendation` column at all (per RESEARCH.md), so a synthetic inline-JSON fixture is required | Per CONVENTIONS.md §CONTRACT-01 verification: paste the synthetic JSON object (RESEARCH.md §"Pitfall #12 Caveat") into Make.com module test interface; confirm output exposes `product_recommendation` and has no `product_result` key |
| Make.com Module 2 emits `is_peri_meno: true` AND `life_stage` includes `peri_menopause_menopause` for rows 10 and 35 | MAKE-FIX-01 (success criterion #2) | Requires running the full Module 1 → Module 2 chain in Make.com against fixture rows | Per CONVENTIONS.md §MAKE-FIX-01 verification: deploy updated `score-calculations.js`; run scenario against rows 10 (Karen Retamal) and 35 (Javielys Mancilla); confirm `is_peri_meno` and `life_stage` outputs |
| Make.com Module 2 emits `activity_profile: "non_athlete"` for non-athlete rows (current sample) and `"athlete"` for synthetic athlete fixture | MAKE-FIX-02 (success criterion #3) | Sample CSV has zero athlete rows (RESEARCH.md confirmed); athlete branch requires synthetic `is_athlete: true` input | Per CONVENTIONS.md §MAKE-FIX-02 verification: deploy updated `score-calculations.js`; non-athlete path uses row 5 or row 34 (Recreacional 2-3x/sem); athlete path uses synthetic JSON object with `is_athlete: true` passed directly to Module 2 |

---

## Validation Sign-Off

- [ ] All tasks have shell-grep `<automated>` verify or are explicitly Manual (per the Manual-Only table above)
- [ ] Sampling continuity: every task has at least one automated grep gate (CONVENTIONS.md task uses 6 grep gates against the new file, deterministic)
- [ ] Wave 0 covers all MISSING references (no Wave 0 needed)
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-03 (auto-approved at create time — no Wave 0 prerequisites and grep gates are deterministic)
