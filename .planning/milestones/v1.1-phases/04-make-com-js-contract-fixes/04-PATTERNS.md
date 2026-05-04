# Phase 4: Make.com JS Contract Fixes - Pattern Map

**Mapped:** 2026-05-03
**Files analyzed:** 3 (2 modified JS, 1 created Markdown)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` | transform / IIFE module | request-response | Self (surrounding code at lines 94–107) | exact — same file, structural deletion |
| `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` | classifier / IIFE module | request-response | Self (surrounding code at lines 211–250) | exact — same file, in-place text patch |
| `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` | verification doc | — | `quizify-csv-to-json-webhook/README.md` | role-match — operator-facing Markdown |

---

## Pattern Assignments

### `quizify-mapping.js` — CONTRACT-01 deletion (line 103)

**Analog:** Surrounding lines 94–107 of the same file.

**Object literal line format** (lines 94–107):
```javascript
const output = {
    email: record.email || null,
    firstName: record.firstName || null,
    lastName: record.lastName || null,
    phone: record.phone || null,
    status: record.status || null,
    statusDate: record.statusDate || null,
    quiz_title: record.quiz_title || null,
    product_recommendation: record["product-recommendation"] || null,
    product_result: record.product_result || null,   // <-- DELETE this line (line 103)
    title: record.title || null,
    type_page_url: record["type-page-url"] || null,
    tags: [] // final merged tags go here
};
```

**Trailing-comma convention:** Every property line ends with a comma, including the last property before a comment (`tags: []` does not end in a comma, but all scalar assignment lines do). After deleting line 103, line 102 (`product_recommendation: ...|| null,`) retains its trailing comma — that is correct and consistent with the file style. No extra edit required.

**Section header style** (lines 89, 110, 134):
```javascript
// === MAIN ===
// === PROCESS QUESTIONS ===
// === DERIVED TAGS LOGIC ===
```
Triple-equals flanked by a single space, all-caps label. No sub-headers inside sections.

**Dead code rule:** D-04-03 states no replacement comment is left behind. After deletion, no line in the file may contain `product_result`. Post-edit grep gate:
```bash
grep -c "product_result" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
# expected: 0
```

---

### `score-calculations.js` — MAKE-FIX-01 (line 213) and MAKE-FIX-02 (lines 247–250)

**Analog:** Surrounding code in the same file.

#### MAKE-FIX-01 — `hasTag` call argument fix (line 213)

**Section header pattern** (line 210):
```javascript
// ====== PROFILE DETERMINATION ======
```
Six-equals flanked by a single space, all-caps label. This is the heavier-weight header style used in `score-calculations.js` (contrast with the triple-equals style in `quizify-mapping.js`).

**`hasTag` call pattern** (lines 212–214):
```javascript
const is_postpartum = hasTag(tags, "postpartum");
const is_peri_meno = hasTag(tags, "peri-menu");   // <-- change "peri-menu" to "peri_menu"
const is_menstrual = hasTag(tags, "menstrual");
```

**Tag argument spelling convention** (all other `hasTag` calls in the file): string arguments use `snake_case_underscores` throughout. `"peri-menu"` (hyphen) is the sole outlier. After the fix, all three `hasTag` calls in this block use underscore tag names matching the emitter at `quizify-mapping.js:167`.

Post-edit grep gate:
```bash
grep -c '"peri-menu"' quizify-csv-to-json-webhook/make-scripts/score-calculations.js
# expected: 0
```

#### MAKE-FIX-02 — `activity_profile` condition fix (lines 247–250)

**Pattern context** (lines 246–250):
```javascript
// Activity profile (simple)
let activity_profile = "non_athlete";
if (!data.is_athlete) {       // <-- remove the ! negation
    activity_profile = "athlete";
}
```

**Pattern after fix:**
```javascript
// Activity profile (simple)
let activity_profile = "non_athlete";
if (data.is_athlete) {
    activity_profile = "athlete";
}
```

**Surrounding `let`/`if` block style:** single-line condition body wrapped in braces; no `else` branch (default is the `let` initializer above). This matches the same pattern at lines 237–244 (the `life_stage` block immediately above):
```javascript
let life_stage = "life_stage_unspecified";
if (is_postpartum) {
    life_stage = "postpartum";
} else if (is_peri_meno) {
    life_stage = "peri_menopause_menopause";
} else if (is_menstrual) {
    life_stage = "menstrual_cycle_active";
}
```
The `activity_profile` block is simpler (no `else if` chain) — that is intentional per the existing file.

**Inline comment style for sections** (line 245, line 252):
```javascript
// Activity profile (simple)
// NEW: context profile (Hogar / Doble jornada / Minería / Senior / Atleta)
```
Single-line `//` comment, no section-header delimiters. Use this style; do NOT add `// ======` delimiters to lines 245–250.

Post-edit grep gate:
```bash
grep -c '!data.is_athlete' quizify-csv-to-json-webhook/make-scripts/score-calculations.js
# expected: 0

grep -c 'if (data.is_athlete)' quizify-csv-to-json-webhook/make-scripts/score-calculations.js
# expected: 1
```

---

### `CONVENTIONS.md` — new verification doc (MAKE-FIX-03)

**Analog:** `quizify-csv-to-json-webhook/README.md`

#### Section structure pattern (README.md)

The README uses `##` H2 sections, no H3 sub-sections. Each section is 1–3 short paragraphs or a single table. No section exceeds ~15 lines of body content. Section titles are plain noun phrases (no gerunds, no "How to…" phrasing):

```markdown
## Purpose
## Quickstart
## CLI reference
## Configuration
## Column assumptions
## Output shape
## Limitations
## Privacy notes
## Exit codes
## Development
```

**CONVENTIONS.md should mirror this style:** `##` H2 only, noun-phrase titles, no H3, ~4–6 sections total to stay within the 50–80 line target.

#### Fenced code block convention (README.md lines 19–21, 261–281)

Shell commands use triple-backtick fences with explicit `bash` language tag:
```markdown
```bash
grep -c "product_result" quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js
# expected: 0
```
```

JSON examples use triple-backtick fences with explicit `json` language tag (per RESEARCH.md synthetic fixture block).

#### Table formatting (README.md lines 31–38, 44–46)

Pipe-table with header row and separator row; column widths are not padded to align:
```markdown
| Flag | Default | Description | Env var |
|------|---------|-------------|---------|
| `--dry-run` | off | Print layout summary... | — |
```
Inline code for flag names and key names uses single backticks. Em-dash `—` for empty cells.

#### Tone and scope rules (from D-04-04 and README.md)

- No architecture explainer, no deployment playbook, no rollback section.
- Verification steps cite row numbers and column names only (T-PII-01). Names (Karen Retamal, Javielys Mancilla) may be used only as row identifiers in a reference table, not as example data.
- Categorical enum values (`"Perimenopausia"`, `"Recreacional 2-3x/sem"`) are safe to cite inline.
- First-person plural ("we") is absent from README; use declarative imperative ("Run", "Confirm", "Verify") or passive ("is absent", "must be").

#### Mandated content map (from D-04-04)

The four required topics map to recommended section names:

| Topic | Recommended Section Title |
|-------|--------------------------|
| Tag canonical-spelling rule (snake_case throughout) | `## Tag naming convention` |
| CONTRACT-01 verification (synthetic JSON fixture; no real CSV row) | `## CONTRACT-01 verification` |
| MAKE-FIX-01 verification (rows 10 and 35, `Perimenopausia`) | `## MAKE-FIX-01 verification` |
| MAKE-FIX-02 verification (non-athlete row; athlete path needs synthetic fixture) | `## MAKE-FIX-02 verification` |

Optional one-line note (from Pitfall #17): `score_total` (JS-recomputed) vs `score-value` (Python CSV pass-through) are independent values. May be appended to `## Tag naming convention` or as a standalone `## Known divergences` note.

---

## Shared Patterns

### IIFE module contract (both JS files)

**Source:** Both `quizify-mapping.js` and `score-calculations.js`.
**Apply to:** All edits within either JS file.

```javascript
// No imports, no exports. Input comes from Make.com's built-in `input` variable.
// Output is a plain return statement at the end of the file.
const data = input.data || {};
// ... computation ...
return out;
```

No `module.exports`, no `import`, no `require`. The file is pasted directly into Make.com's code editor. Every change is an in-place text patch to the flat JS source.

### Tag name spelling (both JS files)

**Source:** `quizify-mapping.js` lines 158–167, `score-calculations.js` lines 212–214.
**Apply to:** Any `hasTag(tags, "...")` call and any `process_filter_tag(..., "tag_name")` call.

All tag identifiers use `snake_case_underscores`. The complete canonical set emitted by `quizify-mapping.js`:
- `has_red_flags`, `has_triggers`, `has_limitations`, `has_pelvic_symptoms`
- `is_athlete` (boolean flag companion to `athlete` tag)
- `hogar`, `menstrual`, `postpartum`, `peri_menu`
- `consent_given`

`"peri-menu"` (hyphen) at `score-calculations.js:213` is the only outlier across both files. After MAKE-FIX-01, there are zero hyphenated tag identifiers in either file.

### `hasTag` helper usage pattern

**Source:** `score-calculations.js` lines 101–104.

```javascript
function hasTag(tags, target) {
    if (!Array.isArray(tags)) return false;
    return tags.includes(target);
}
```

Exact-match string comparison; no lowercase normalization; case-sensitive. Tag strings must match exactly as emitted by Module 1. Do not alter this helper.

---

## No Analog Found

None. All three files have strong analogs.

---

## Metadata

**Analog search scope:** `quizify-csv-to-json-webhook/make-scripts/`, `quizify-csv-to-json-webhook/README.md`, `quizify-csv-to-json-webhook/docs/`
**Files scanned:** 4 (2 JS source files, 1 README, 1 docs directory listing)
**Pattern extraction date:** 2026-05-03
