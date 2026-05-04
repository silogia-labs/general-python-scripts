# Phase 4: Make.com JS Contract Fixes - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 4-make-com-js-contract-fixes
**Areas discussed:** Athlete-flip ship gate (MAKE-FIX-02), Peri-tag downstream gate (MAKE-FIX-01), Ghost-key treatment (CONTRACT-01), CONVENTIONS.md scope (MAKE-FIX-03)

---

## Athlete-flip ship gate (MAKE-FIX-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Ship the fix; no downstream consumers (Recommended) | User confirms `activity_profile` is NOT used by any active Airtable formula, view, or email-segmentation rule today. Ship corrected logic, document historical bug in MILESTONES.md, no migration needed. | ✓ |
| Ship the fix + audit/notify downstream | Airtable views/campaigns segmented on `activity_profile` exist. Ship the fix AND add a follow-up audit task. Note semantic change in PROJECT.md Key Decisions. | |
| Defer MAKE-FIX-02 to v1.2 | Customer impact unclear; punt the inversion fix. Phase 4 ships only CONTRACT-01, MAKE-FIX-01, MAKE-FIX-03. | |

**User's choice:** Ship the fix; no downstream consumers.
**Notes:** Satisfies the user-confirmation gate mandated by Pitfall #14. Captured as D-04-01 in CONTEXT.md.

---

## Peri-tag downstream gate (MAKE-FIX-01)

| Option | Description | Selected |
|--------|-------------|----------|
| No downstream uses the hyphen — ship clean (Recommended) | Nothing keys off `"peri-menu"` (it never matched anyway) or `life_stage_unspecified` for peri-respondents. Single-character JS fix only. | ✓ |
| Update downstream alongside JS fix | Some Airtable/template logic exists. Add CONVENTIONS.md verification step listing affected downstream surfaces; user updates outside repo. Ship JS in same phase. | |
| Need to investigate before shipping MAKE-FIX-01 | Defer MAKE-FIX-01 until downstream audit completes. Phase 4 ships CONTRACT-01, MAKE-FIX-02, MAKE-FIX-03 only. | |

**User's choice:** No downstream uses the hyphen — ship clean.
**Notes:** Captured as D-04-02 in CONTEXT.md. After fix, peri-respondents start receiving `peri_menopause_menopause` instead of `life_stage_unspecified` — pure correctness recovery.

---

## Ghost-key treatment (CONTRACT-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Remove line 103 entirely (Recommended) | Pure dead code per Pitfall #12. Delete the line. Output object loses a `product_result: null` key that nothing downstream references. Cleanest fix. | ✓ |
| Keep line 103 but fix the key name | Rename to `record["product-recommendation"]` so both lines emit the same value under different output names — only if some downstream Make.com module reads `product_result` from the JS output. | |
| Remove line 103 AND add a guard comment | Delete plus add a `// D-05: Python emits hyphenated keys only` comment near line 102 to deter future re-introduction. | |

**User's choice:** Remove line 103 entirely.
**Notes:** Captured as D-04-03 in CONTEXT.md. Single-line deletion. No comment added per project's "default to no comments" stance.

---

## CONVENTIONS.md scope (MAKE-FIX-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Verification-only — minimal scope (Recommended) | Tight focused doc. Just the four items in MAKE-FIX-03 acceptance criterion. ~50–80 lines. Matches v1.0's no-frills doc ethos. | ✓ |
| Verification + co-ownership reference | Adds a short Module 1 vs Module 2 boundary section, file roles, D-05 contract pointer, Pitfall reference. ~120–180 lines. | |
| Full Make.com integration playbook | Includes Make.com deployment, sandbox testing, rollback. Risks scope creep beyond v1.1. | |

**User's choice:** Verification-only — minimal scope.
**Notes:** Captured as D-04-04 in CONTEXT.md. Co-ownership reference deferred for a v1.2+ docs phase if needed.

---

## Claude's Discretion

- **Commit grouping inside the phase plan** — one commit per fix vs. one bundled JS commit + one docs commit. Planner's call.
- **Exact Markdown structure of CONVENTIONS.md** — sections, checklist, or short table; whichever reads cleanest at the ~50–80 line target.
- **Pre-locking verification of rows 10/35** — recommended to grep the current `quizify-submissions.csv` to confirm `Perimenopausia` placement before writing CONVENTIONS.md, but not gating.

## Deferred Ideas

- Make.com Module 1 vs Module 2 architecture documentation (v1.2+ docs phase if needed).
- Make.com deployment playbook / rollback procedure (out of scope per D-04-04).
- Future audit of Airtable / email templates if new consumers of `activity_profile` or `life_stage` are introduced post-v1.1.
- `Reomoto` typo at `score-calculations.js:157` (MAKE-COSMETIC-01, v1.2).
- Dead-code init `profile = "profile_base"` at `score-calculations.js:217` (MAKE-COSMETIC-02, v1.2).
- Local Node.js test harness for `make-scripts/` (MAKE-TEST-01, v1.2).
- `score_total` vs `score-value` divergence audit (Pitfall #17 — doc-note only in v1.1).
