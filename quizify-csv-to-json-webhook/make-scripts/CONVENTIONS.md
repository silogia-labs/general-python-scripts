# make-scripts Conventions

Verification and naming conventions for the two Make.com IIFE modules in this
directory (`quizify-mapping.js`, `score-calculations.js`).

## Tag naming convention

All tag identifiers in `make-scripts/` use `snake_case_underscores`. The
canonical set emitted by `quizify-mapping.js`:

| Tag | Type |
|-----|------|
| `has_red_flags` | boolean flag |
| `has_triggers` | boolean flag |
| `has_limitations` | boolean flag |
| `has_pelvic_symptoms` | boolean flag |
| `is_athlete` | boolean flag |
| `hogar` | categorical |
| `menstrual` | categorical |
| `postpartum` | categorical |
| `peri_menu` | categorical |
| `consent_given` | boolean flag |

The `hasTag(tags, "...")` calls in `score-calculations.js` must match the
emitter spelling exactly — `tags.includes` performs a case-sensitive exact-match.

The `peri_menu`/`peri-menu` incident (MAKE-FIX-01) is the canonical example of
a hyphen outlier causing a silent mismatch: `quizify-mapping.js` emitted
`peri_menu` (underscore) while `score-calculations.js` consumed `peri-menu`
(hyphen), causing peri-menopause respondents to receive `life_stage_unspecified`
instead of `peri_menopause_menopause`. Do not introduce hyphenated tag
identifiers on either side of the module boundary.

Note: `score_total` (JS-recomputed in `score-calculations.js`) and `score-value`
(Python CSV pass-through) are independent values; a post-v1.1 audit should
confirm agreement.

## CONTRACT-01 verification

The canonical input key is `product-recommendation` (hyphenated, per D-05).
Module 1 reads it as `record["product-recommendation"]` and exposes it
downstream as `product_recommendation` (snake_case output key).

`docs/quizify-submissions.csv` does NOT contain a `product-recommendation`
column — the column is absent from the export. Verification requires a synthetic
inline-JSON fixture pasted into Make.com's module test interface:

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

Confirm Module 1 output exposes `product_recommendation: "programa-piso-pelvico"`
and does NOT contain a `product_result` key.

Do not add fake PII rows to the real CSV file.

## MAKE-FIX-01 verification

Deploy the updated `score-calculations.js`. Run the Make.com scenario against
these two rows:

| Row | Column | Value |
|-----|--------|-------|
| row 10 | `menopause_status` | `Perimenopausia` |
| row 35 | `menopause_status` | `Perimenopausia` |

Rows 10 and 35 correspond to respondents Karen Retamal and Javielys Mancilla
per CONTEXT.md.

Confirm Module 2 output has `is_peri_meno: true` and `life_stage` includes
`peri_menopause_menopause`.

## MAKE-FIX-02 verification

The 42-row sample contains zero athlete rows — no `sport_level` value contains
"alto". The only categorical values present are `Sedentaria` and
`Recreacional 2-3x/sem`.

**Non-athlete path (verifiable with current sample):** Use row 5
(`sport_level: Recreacional 2-3x/sem`). Confirm Module 2 output has
`activity_profile: "non_athlete"`.

When `data.is_athlete` is `undefined` (all current sample rows), the condition
`if (data.is_athlete)` is not entered and the default `"non_athlete"` applies —
this is the intended post-fix behavior (Pitfall D).

**Athlete path (synthetic fixture required):** Construct an inline JSON object
with `is_athlete: true` and pass it directly to Module 2 in Make.com's test
interface (bypassing Module 1). Confirm output has `activity_profile: "athlete"`.
