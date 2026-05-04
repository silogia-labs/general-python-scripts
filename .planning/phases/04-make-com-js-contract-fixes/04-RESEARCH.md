# Phase 4: Make.com JS Contract Fixes - Research

**Researched:** 2026-05-03
**Domain:** JavaScript (Make.com IIFE modules) — pure line-level edits, no new dependencies
**Confidence:** HIGH — all findings grounded in direct code inspection of the live files

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-04-01 (MAKE-FIX-02 ship gate):** No active Airtable formula, view, or email-segmentation rule currently consumes `activity_profile`. The semantic flip is a pure correctness fix with no downstream migration. Ship in Phase 4. Document the historical bug in MILESTONES.md under v1.1 as a behavioral correction.
- **D-04-02 (MAKE-FIX-01 ship gate):** No downstream consumer (Airtable, email template, Make.com filter) currently keys off the broken `"peri-menu"` (hyphen) string or off `life_stage_unspecified` for peri-respondents. Ship the one-character fix cleanly; no downstream coordination required.
- **D-04-03 (CONTRACT-01 — ghost line):** Remove `quizify-mapping.js:103` (`product_result: record.product_result || null,`) **entirely**. Pure dead code. Do NOT keep the line under any other name; do NOT replace with a comment. The diff is a single deletion.
- **D-04-04 (CONVENTIONS.md scope):** Verification-only / minimal scope. Cover exactly the four items mandated by MAKE-FIX-03 acceptance criterion. Target ~50–80 lines. No Module 1 vs Module 2 architecture explainer, no deployment playbook, no rollback procedure.

### Claude's Discretion

- Commit grouping inside the phase plan (one commit per fix vs. one bundled JS commit + one docs commit).
- Exact Markdown structure of CONVENTIONS.md — sections, checklist, or table; whichever reads cleanest at ~50–80 lines.
- Whether to verify rows 10 and 35 against the current CSV before locking verification doc (this research has done so — see CSV Verification section below).

### Deferred Ideas (OUT OF SCOPE)

- Make.com Module 1 vs Module 2 architecture documentation.
- Make.com deployment playbook / rollback procedure.
- Auditing Airtable formulas / email templates for `activity_profile` and `life_stage` consumers (confirmed no consumers; D-04-01 and D-04-02 gates satisfied).
- `Reomoto` typo at `score-calculations.js:157` — MAKE-COSMETIC-01, v1.2+.
- Dead-code init `profile = "profile_base"` at `score-calculations.js:217` — MAKE-COSMETIC-02, v1.2+.
- Local Node.js test harness — MAKE-TEST-01, v1.2+.
- `score_total` (JS-recomputed) vs `score-value` (Python pass-through) divergence audit — document-only note in CONVENTIONS.md; no code change.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONTRACT-01 | Remove dead `record.product_result` line from `quizify-mapping.js` so the JS output object cleanly reflects the D-05 hyphenated key | Line 103 confirmed as dead code; line 102 already reads `record["product-recommendation"]` correctly — single-line deletion |
| MAKE-FIX-01 | Replace `"peri-menu"` (hyphen) with `"peri_menu"` (underscore) at `score-calculations.js:213` | Line 213 confirmed: `const is_peri_meno = hasTag(tags, "peri-menu");` — one-character fix |
| MAKE-FIX-02 | Correct inverted `activity_profile` condition at `score-calculations.js:247-250` | Lines 247-250 confirmed: `!data.is_athlete` sets `"athlete"` — fix to `data.is_athlete` |
| MAKE-FIX-03 | Write `make-scripts/CONVENTIONS.md` covering four mandated topics with sample-row references | Row 10 = Karen Retamal (`Perimenopausia` confirmed), row 35 = Javielys Mancilla (`Perimenopausia` confirmed); non-athlete sample identified |
</phase_requirements>

---

## Summary

Phase 4 is a surgical, zero-dependency edit across two JavaScript files (187 and 295 lines respectively) plus one new Markdown file. There are no external libraries to install, no build steps to run, and no Python code to touch. The entire code surface is three line-level changes and one new ~50–80 line document.

All three JS bugs are confirmed present in the current live files. Line numbers match PITFALLS.md exactly — no drift detected. The CSV verification fixture has also been validated: rows 10 and 35 contain `Perimenopausia` as expected. However, there are zero athlete rows (`sport_level` containing "alto") in the 42-row sample, and all rows have an empty `product-recommendation` column — both of which are known fixture gaps that CONVENTIONS.md must address explicitly.

**Primary recommendation:** Plan three focused edit tasks (one per REQ) plus one documentation task (MAKE-FIX-03). Group the two JS files in a single implementation commit to simplify review, then a separate docs commit for CONVENTIONS.md.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `product-recommendation` passthrough (CONTRACT-01) | Make.com Module 1 (`quizify-mapping.js`) | Python CLI (emitter, unmodified) | JS reads Python output; bug is in the JS reader, not the Python emitter |
| Peri-menopause life-stage classification (MAKE-FIX-01) | Make.com Module 2 (`score-calculations.js`) | Make.com Module 1 (tag emitter, unmodified) | Module 1 emits `peri_menu` correctly; Module 2 consumer reads it with wrong spelling |
| Activity profile classification (MAKE-FIX-02) | Make.com Module 2 (`score-calculations.js`) | Airtable (downstream consumer, no migration needed per D-04-01) | Inverted condition is self-contained in Module 2's `activity_profile` assignment |
| Verification documentation (MAKE-FIX-03) | `make-scripts/CONVENTIONS.md` (new file) | — | Pure documentation; references fixture rows and shell commands |

---

## Exact Code Targets (VERIFIED)

### CONTRACT-01: `quizify-mapping.js` lines 102–103

**File:** `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js`
**Current line count:** 187 lines [VERIFIED: direct file read]

```javascript
// line 101 — trailing comma from statusDate block
    quiz_title: record.quiz_title || null,
// line 102 — KEEP: correct D-05 hyphenated key read
    product_recommendation: record["product-recommendation"] || null,
// line 103 — DELETE: dead code; record.product_result is never emitted by Python
    product_result: record.product_result || null,
// line 104 — keep
    title: record.title || null,
```

**Action (D-04-03):** Delete line 103 entirely. No rename, no comment stub. The resulting diff is one line removed. After deletion, line 104 (`title: record.title || null,`) becomes line 103.

**Why line 103 is dead code:** Python's D-05-locked output uses `product-recommendation` (hyphen). `record.product_result` (underscore, no hyphen) is `undefined` in JavaScript when the key does not exist, which `|| null` coerces to `null`. It has always been `null` for every record. [VERIFIED: grep confirms `product_result` appears exactly once in the file, on line 103]

---

### MAKE-FIX-01: `score-calculations.js` line 213

**File:** `quizify-csv-to-json-webhook/make-scripts/score-calculations.js`
**Current line count:** 295 lines [VERIFIED: direct file read]

```javascript
// line 211 — context (profile section header comment)
// ====== PROFILE DETERMINATION ======
// line 212 (blank line)
// line 213 — FIX HERE: "peri-menu" (hyphen) → "peri_menu" (underscore)
const is_peri_meno = hasTag(tags, "peri-menu");
// line 214 — keep
const is_menstrual = hasTag(tags, "menstrual");
```

**Action:** Change `"peri-menu"` to `"peri_menu"` on line 213. One character change (hyphen → underscore). Do NOT touch `quizify-mapping.js:167` — that line emits `peri_menu` (underscore) correctly and is not touched by this phase.

**Emitter confirmation (quizify-mapping.js:167, VERIFIED):**
```javascript
process_filter_tag(output.menopause_status, "peri", "peri_menu")
```
The emitter already uses the underscore spelling. Only the consumer is wrong.

---

### MAKE-FIX-02: `score-calculations.js` lines 247–250

**File:** `quizify-csv-to-json-webhook/make-scripts/score-calculations.js`

```javascript
// line 245 — comment
// Activity profile (simple)
// line 246 (blank line)
// line 247 — keep (correct default)
let activity_profile = "non_athlete";
// line 248 — FIX HERE: !data.is_athlete → data.is_athlete
if (!data.is_athlete) {
// line 249 — keep (correct assignment)
    activity_profile = "athlete";
// line 250 — keep
}
```

**Action:** Remove the `!` negation on line 248. Change `if (!data.is_athlete)` to `if (data.is_athlete)`. The semantic intent of the variable initialization (`non_athlete` as default) plus the condition flip (`if (is_athlete) set athlete`) matches the correct logic.

**Behavioral impact:** Every respondent with `data.is_athlete === false` currently gets `activity_profile = "athlete"`. After the fix, they get `"non_athlete"`. D-04-01 confirms no active Airtable/email consumer depends on this field. [VERIFIED: CONTEXT.md D-04-01]

---

## CSV Verification Results (VERIFIED)

### Row 10 and 35 — Perimenopausia confirmation

**File:** `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` (42 data rows + 1 header = 43 lines)

Direct parse of the CSV confirms:

| Data row | Name | `Perimenopausia/Menopausia` column value |
|----------|------|------------------------------------------|
| Row 10 (file line 10) | Karen Retamal carreño | `"Perimenopausia"` |
| Row 35 (file line 35) | Javielys Mancilla ruiz | `"Perimenopausia"` |

**Confirmed:** Both rows contain `Perimenopausia`. PITFALLS.md's claim is accurate. No drift detected. [VERIFIED: direct CSV parse]

Note: Row 22 (Verónica García) has `"Menopausia"` (not peri). It should NOT be cited as a MAKE-FIX-01 verification row — the fix is for the `peri_menu` tag path only.

### Non-athlete sample rows for MAKE-FIX-02

The CSV has **zero athlete rows** — no row has `sport_level` containing "alto". [VERIFIED: direct CSV parse of all 42 rows]

All sport_level values found: `"Sedentaria"`, `"Recreacional 2-3x/sem"`. Neither contains "alto" so none would emit the `is_athlete` tag from `quizify-mapping.js:163`.

**Best non-athlete sample for CONVENTIONS.md verification:** Row 34 (Javielys Mancilla ruiz) — `sport_level = "Recreacional 2-3x/sem"`, `Perimenopausia` in menopause column. This row conveniently also verifies MAKE-FIX-01 in the same run. Alternatively, row 5 (Susana Recabarren) — `sport_level = "Recreacional 2-3x/sem"` — is a clean, single-concern non-athlete row with complete data.

**CONVENTIONS.md implication:** The MAKE-FIX-02 verification step must note that the 42-row sample contains no athlete respondents. The verification description should specify: "use a row with `Nivel de deporte: Recreacional 2-3x/sem` (e.g. row 34 or row 5) and confirm the JS output has `activity_profile: "non_athlete"`" — and acknowledge that an athlete row would require a synthetic fixture.

### product-recommendation column — all-null confirmation

The CSV does not contain a `product-recommendation` column at all — the column is absent from the exported headers. [VERIFIED: direct CSV parse; no `product`-related column keys found]

This is consistent with Pitfall #12: the Python CLI emits `product-recommendation: null` as a reserved placeholder for all current rows, and the export does not include it. CONTRACT-01's manual verification requires a **synthetic fixture** to observe a non-null passthrough.

---

## Out-of-Scope Code Observations (Planner Must NOT Fix in Phase 4)

These were observed during the code read. They are deferred to v1.2 per REQUIREMENTS.md. The planner must not include tasks for these.

### MAKE-COSMETIC-01: `Reomoto` typo at score-calculations.js:157

```javascript
// line 157 — typo: "Reomoto" should be "Remoto"
    if (work.includes("remoto")) return "Reomoto";
```

**Status:** Deferred to v1.2 as MAKE-COSMETIC-01. Do not fix in Phase 4.

### MAKE-COSMETIC-02: Dead-code `profile = "profile_base"` initializer at score-calculations.js:217

```javascript
// line 217 — dead init: always overwritten by lines 221-231
let profile = "profile_base";
```

The variable is always overwritten inside the `if/else` block at lines 220-233 (or stays `"profile_base"` only in the unreachable case where `data.has_red_flags` is falsy AND no score band matches, but `classifyTotalScore` has a default of `"unknown"` that lands in the `else` branch setting `"low_complexity"`). The value `"profile_base"` never makes it to `out.profile` in practice.

**Status:** Deferred to v1.2 as MAKE-COSMETIC-02. Do not fix in Phase 4.

### Pitfall #17 — score_total vs score-value divergence note

`score-calculations.js` line 270 assigns `out.score_total` (JS-recomputed from raw answers). Python emits `score-value` as a CSV pass-through string from the trailer. These are independent values. CONVENTIONS.md should include a one-line note: "score_total (JS-recomputed) and score-value (Python CSV pass-through) are independent. A post-v1.1 audit should confirm agreement." No code change in Phase 4.

---

## Architecture Patterns (for this phase)

### IIFE module contract
Both JS files are Make.com code modules with a fixed contract: they receive `input` from the previous module and `return` a single output object. There are no imports, no exports, no build step. Every edit is a pure in-place text change to a `.js` file that is pasted into Make.com's code editor.

### Tag spelling convention
All tag names emitted in `quizify-mapping.js` use `snake_case_underscores`: `has_red_flags`, `is_athlete`, `peri_menu`, `hogar`, `menstrual`, `postpartum`, `consent_given`. The `peri-menu` hyphen in `score-calculations.js:213` is the **only** outlier across both files.

### Module 1 → Module 2 data flow

```
Python CLI (emits JSON)
    ↓  record["product-recommendation"]  (hyphenated key, D-05)
quizify-mapping.js (Module 1)
    ↓  output.product_recommendation     (snake_case output key)
    ↓  output.tags = [..., "peri_menu", ...]  (when menopause_status contains "peri")
    ↓  output.is_athlete = true/false    (when sport_level contains "alto")
score-calculations.js (Module 2)
    ↓  hasTag(tags, "peri_menu")         → is_peri_meno (AFTER FIX)
    ↓  if (data.is_athlete)              → activity_profile (AFTER FIX)
    ↓  out.life_stage_profile = "peri_menopause_menopause"
    ↓  out.activity_profile = "non_athlete" | "athlete"
Airtable / email routing
```

---

## Validation Architecture

### Framework

No automated test runner exists for `make-scripts/` in v1.1. MAKE-TEST-01 is deferred to v1.2. The validation approach for this phase is:

1. **Shell-grep gates** — run before and after each edit to confirm the textual change landed correctly (fast, deterministic, no runtime required)
2. **Manual verification in Make.com** — run the scenario against fixture rows after deploying the updated JS (required to observe runtime behavior; cannot be automated in v1.1)

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Pre-phase State |
|--------|----------|-----------|-------------------|-----------------|
| CONTRACT-01 | `product_result` dead line is removed | shell-grep | `grep -c "product_result" quizify-mapping.js` → must be `0` | Currently `1` (bug present) |
| CONTRACT-01 | `product_recommendation` key is still present | shell-grep | `grep -c 'product_recommendation' quizify-mapping.js` → must be `1` | Currently `1` |
| MAKE-FIX-01 | `peri-menu` (hyphen) is absent from score-calculations.js | shell-grep | `grep -c '"peri-menu"' score-calculations.js` → must be `0` | Currently `1` (bug present) |
| MAKE-FIX-01 | `peri_menu` (underscore) emitter in quizify-mapping.js is untouched | shell-grep | `grep -c 'peri_menu' quizify-mapping.js` → must be `1` | Currently `1` |
| MAKE-FIX-02 | Inverted `!data.is_athlete` condition is gone | shell-grep | `grep -c '!data.is_athlete' score-calculations.js` → must be `0` | Currently `1` (bug present) |
| MAKE-FIX-02 | Correct `data.is_athlete` condition is present | shell-grep | `grep -c 'if (data.is_athlete)' score-calculations.js` → must be `1` | Currently `0` |
| MAKE-FIX-03 | CONVENTIONS.md file exists | shell | `test -f quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md && echo OK` | Currently absent |

All commands must be run from the repo root, with paths relative to the project root:

```bash
# Full post-fix gate suite (run from repo root)
grep -c "product_result" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
# expected: 0

grep -c "product_recommendation" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
# expected: 1

grep -c '"peri-menu"' quizify-csv-to-json-webhook/make-scripts/score-calculations.js
# expected: 0

grep -c "peri_menu" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
# expected: 1

grep -c '!data.is_athlete' quizify-csv-to-json-webhook/make-scripts/score-calculations.js
# expected: 0

grep -c 'if (data.is_athlete)' quizify-csv-to-json-webhook/make-scripts/score-calculations.js
# expected: 1

test -f quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md && echo "CONVENTIONS.md OK"
# expected: CONVENTIONS.md OK
```

### Manual Verification (Make.com runtime — post-deploy)

Per ROADMAP.md Phase 4 success criteria, manual verification must confirm runtime behavior in Make.com. Shell-grep only confirms the text change; only Make.com execution confirms the semantic fix. The planner must include a manual verification step after the JS files are updated in Make.com.

### Wave 0 Gaps

None — no new test framework or fixture files are required. The shell-grep commands above are self-contained one-liners with no setup. CONVENTIONS.md IS the verification scaffold; it is created by MAKE-FIX-03, not a Wave 0 prerequisite.

---

## Pitfall #12 Caveat — CONTRACT-01 Synthetic Fixture

The `docs/quizify-submissions.csv` sample does not contain a `product-recommendation` column. The Python CLI emits this key as a reserved placeholder (`null`) for all 42 current rows. The column is not even present in the CSV export. [VERIFIED: direct parse; no `product`-related column headers found]

**Consequence for CONVENTIONS.md:** The CONTRACT-01 verification step cannot reference a real CSV row with a non-null `product-recommendation`. The CONVENTIONS.md must describe constructing a synthetic test using an **inline JSON example** rather than a CSV row reference.

**Recommended approach for the CONVENTIONS.md verification step:**

Describe constructing a synthetic `input.quiz_response` JSON object manually in Make.com's code module test interface (or via the "Run once" tool), with:

```json
{
  "product-recommendation": "programa-piso-pelvico",
  "email": "test@example.com",
  "firstName": "Test",
  "lastName": "User",
  "phone": "",
  "status": "",
  "statusDate": "",
  "quiz_title": "quizify"
}
```

Then verify that the Module 1 output object contains `product_recommendation: "programa-piso-pelvico"` and does NOT contain a `product_result` key. This is the inline-JSON approach — no CSV row hand-editing required.

Do NOT instruct adding a new row to `quizify-submissions.csv` with fake PII values (T-PII-01 concern).

---

## Common Pitfalls (Confirmed for Phase 4)

### Pitfall A: Editing the emitter instead of the consumer (MAKE-FIX-01)

**What goes wrong:** Developer reads Pitfall #13 and edits `quizify-mapping.js:167` (`process_filter_tag(..., "peri_menu")`) instead of `score-calculations.js:213`. The emitter is already correct.

**Prevention:** The acceptance criterion must explicitly state: "Only `score-calculations.js:213` is modified. `quizify-mapping.js` is NOT modified for MAKE-FIX-01."

### Pitfall B: Adding a comment stub for the deleted ghost line (CONTRACT-01)

**What goes wrong:** Developer removes `record.product_result || null` but replaces it with `// product_result: removed — was dead code`. This leaves a comment reference to the dead key, which may confuse future readers.

**Prevention:** D-04-03 is explicit: "Do NOT replace with a comment. The diff is a single deletion." Acceptance criterion: after the edit, no line in `quizify-mapping.js` contains `product_result`.

### Pitfall C: Forgetting the trailing comma after line 103 deletion

**What goes wrong:** Line 103 ends with a comma: `product_result: record.product_result || null,`. Deleting it leaves line 102 (`product_recommendation: record["product-recommendation"] || null,`) with a trailing comma before `title` on line 104. This is **valid JavaScript** (ES5+ allows trailing commas in object literals) and is NOT a bug. The file already has other trailing commas in the `output` object initialization. No action needed.

### Pitfall D: Line 248 negation removal creates a logic gap

**What goes wrong:** Developer reads the fix as "change `!data.is_athlete` to `data.is_athlete`" and produces `if (data.is_athlete) { activity_profile = "athlete"; }`. They verify this looks correct. But then they check what happens when `data.is_athlete` is `undefined` (which is the case for all 42 rows in the sample CSV since the quiz has no athlete respondents). `undefined` is falsy, so the condition is never entered and the default `"non_athlete"` applies. This is actually the correct behavior — just confirm it is intentional.

**Prevention:** No action needed. `data.is_athlete` is `undefined` for all current sample rows, which correctly routes to `"non_athlete"`. The fix is correct. Document this behavior in CONVENTIONS.md verification.

---

## Security Domain

`security_enforcement: true` per config.json. ASVS Level 1 applies.

| ASVS Category | Applies | Notes |
|---------------|---------|-------|
| V2 Authentication | No | No auth in JS modules |
| V3 Session Management | No | Stateless IIFE modules |
| V4 Access Control | No | No ACL logic |
| V5 Input Validation | Minimal | JS reads from Make.com-controlled `input` object; no user-facing input in this phase's edit surface |
| V6 Cryptography | No | No crypto operations |

**PII constraint (T-PII-01 carry-forward):** CONVENTIONS.md must reference rows by index (row 10, row 35) and column names only. No cell content beyond categorical enum values (e.g. `"Perimenopausia"` is a categorical enum value, safe to cite). First names in CONTEXT.md (Karen Retamal, Javielys Mancilla) are present in the locked decisions — use them only as row identifiers, not as examples of PII content.

The inline JSON synthetic fixture for CONTRACT-01 (above) uses `test@example.com` — compliant with T-PII-01.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified by direct file inspection or direct CSV parse. No assumed claims.**

---

## Open Questions

1. **Athlete fixture for MAKE-FIX-02 full runtime verification**
   - What we know: The 42-row CSV has zero athlete rows. `sport_level` containing "alto" would be required to produce `is_athlete = true` in Module 1 output, which would then trigger `activity_profile = "athlete"` after the fix.
   - What's unclear: Whether the operator has a real athlete respondent row available for runtime testing in Make.com (outside the sample CSV).
   - Recommendation: CONVENTIONS.md should document that the non-athlete path is verifiable with the current sample, and that the athlete path requires a synthetic `input.quiz_response` object with `is_athlete: true` passed directly to Module 2 (bypassing Module 1) to confirm the correct branch in isolation.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is pure JS text edits and one new Markdown file. No external tools, runtimes, databases, or CLI utilities beyond a text editor are required. No shell commands beyond `grep` and `test` (both universally available) are needed for the gate checks.

---

## Sources

### Primary (HIGH confidence)
- Direct read of `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` (187 lines, 2026-05-03) — CONTRACT-01 target lines 102-103 confirmed
- Direct read of `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` (295 lines, 2026-05-03) — MAKE-FIX-01 target line 213 and MAKE-FIX-02 target lines 247-250 confirmed
- Direct parse of `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` (42 data rows) — rows 10 and 35 Perimenopausia confirmed; zero athlete rows confirmed; product-recommendation column absent confirmed
- `.planning/phases/04-make-com-js-contract-fixes/04-CONTEXT.md` — locked decisions D-04-01 through D-04-04
- `.planning/REQUIREMENTS.md` — CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02, MAKE-FIX-03 requirement text
- `.planning/research/PITFALLS.md` — Pitfalls 12, 13, 14, 17 (all grounded in prior direct code inspection)

### Secondary (MEDIUM confidence)
- None applicable — all claims are code-verified.

---

## Metadata

**Confidence breakdown:**
- Exact code targets (line numbers, surrounding context): HIGH — grep and direct read confirm all three edit sites
- CSV fixture state (rows 10/35 peri, athlete absence, product-recommendation null): HIGH — direct CSV parse
- Shell-grep gate commands: HIGH — executed against pre-fix files; expected outputs confirmed
- Deferred items (Reomoto, profile_base): HIGH — grep confirms exact line numbers match REQUIREMENTS.md references

**Research date:** 2026-05-03
**Valid until:** Indefinite for file structure; re-verify line numbers if any other edit lands in either JS file before Phase 4 executes
