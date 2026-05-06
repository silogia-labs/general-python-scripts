# Phase 10: Make.com Hygiene & Node Test Harness — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 14 (5 modified + 9 new; fixtures counted as one group per module)
**Analogs found:** 11 / 14 (3 surfaces are first-of-kind in the repo: JS test harness, JS package manifest, JS .gitignore)

## File Classification

| File | Action | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `make-scripts/quizify-mapping.js` | EDIT (wrap in `mapRecord` + footer + `"use strict"`) | source module (Make.com IIFE ↔ Node CJS) | transform (record → mapped record) | self (current top-level body) + `score-calculations.js` (parallel module) | exact (locked verbatim D-10-01..05) |
| `make-scripts/score-calculations.js` | EDIT (same wrap + Reomoto→Remoto :157 + remove `let profile = "profile_base"` :217) | source module (same) | transform (mapped record → scores+profile) | self + sibling | exact (locked) |
| `pyproject.toml` | EDIT (add fresh `[tool.pytest.ini_options]` table) | config (pytest collection scope) | n/a | none in this `pyproject.toml` (section absent) — TOML idiom standard | role-match |
| `quizify-csv-to-json-webhook/README.md` | EDIT (add `### Make.com module tests` subsection under existing `## Development`) | docs | n/a | Phase 9 README usage example added under existing H2 (commit `6edc5d1`) | exact (D-11 ten-section lock + drift-test pattern) |
| `.github/workflows/<existing>` | EDIT or CREATE (locate at plan time per RESEARCH OQ#1) | CI config | request-response (job invocation) | none in working tree (`.github/` empty) — RESEARCH §Code Examples §Example 3 locks shape | locked-skeleton |
| `make-scripts/package.json` | NEW | config (Node package manifest) | n/a | none in repo — first JS package.json | locked-skeleton (D-10-15 + RESEARCH §Example 5) |
| `make-scripts/.gitignore` | NEW | config (gitignore) | n/a | repo `.gitignore` files (idiom only) | locked-skeleton (D-10-19 + RESEARCH §Example 6) |
| `make-scripts/tests/contract-01.test.js` | NEW | unit test (JS) | request-response (call `mapRecord(fixture)`, assert) | RESEARCH Pattern 3 (verbatim shape); Python analog: `tests/test_argparse_ndjson.py` (per-requirement test idiom) | locked-skeleton + role-match |
| `make-scripts/tests/make-fix-01.test.js` | NEW | unit test (JS) | request-response | same | same |
| `make-scripts/tests/make-fix-02.test.js` | NEW | unit test (JS) | request-response | same | same |
| `make-scripts/tests/cosmetic-01.test.js` | NEW (RED-then-GREEN per D-10-10) | unit test (JS) | request-response | RESEARCH Pattern 3 + Pitfall 6 sequencing note | locked-skeleton |
| `make-scripts/tests/cosmetic-02.test.js` | NEW | unit test (JS, sweep) | batch (loop fixtures, assert each) | RESEARCH §Open Q3 — sweep all `score-calculations` fixtures | locked-skeleton |
| `make-scripts/tests/globals.test.js` | NEW | unit test (JS, snapshot diff) | event-driven (before/after `require`) | RESEARCH Pattern 2 (verbatim) | locked-skeleton |
| `make-scripts/tests/fixtures/{quizify-mapping,score-calculations}/*.json` | NEW (synthetic) | test fixture (JSON) | n/a | `make-scripts/CONVENTIONS.md` §"CONTRACT-01 verification" inline-JSON shape (lines 48–59) | exact (D-10-07 mandates mirroring) |
| `quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py` | NEW | unit test (Python grep gate) | transform (read JSON, assert keys) | `tests/test_security_grep_gates.py` (Phase 9, full file) | exact (extends idiom) |
| `quizify-csv-to-json-webhook/tests/test_make_scripts_no_pii.py` | NEW | unit test (Python grep gate) | transform (read fixtures, scan for PII tokens) | `tests/test_security_grep_gates.py` + `tests/conftest.py:127` `SYNTHETIC_PII_TOKENS` | role-match (T-PII-01 carry-forward) |

## Pattern Assignments

### `make-scripts/score-calculations.js` (EDIT — wrap + 2 cosmetic fixes)

**Analog:** self (current shape lines 1–end). Locked target shape per RESEARCH §Example 1.

**Source-fix call-sites:**

`score-calculations.js:157` (current):
```js
if (work.includes("remoto")) return "Reomoto";
```
→ MAKE-COSMETIC-01 fix:
```js
if (work.includes("remoto")) return "Remoto";  // FIX MAKE-COSMETIC-01 (was "Reomoto")
```

`score-calculations.js:217` (current):
```js
let profile = "profile_base";
```
→ MAKE-COSMETIC-02 fix (every code path reassigns; verified A6 in RESEARCH):
```js
let profile;  // FIX MAKE-COSMETIC-02 — every branch in lines 220-233 reassigns
```

**Wrap pattern (D-10-01..04):** Lift current `// ====== MAIN INPUT ======` block (lines 167–end of top-level logic, which culminates in a `return out;` or final `out` reference) into `function mapRecord(record) { ... return out; }`. Replace `input.data || {}` (line 170) with `record || {}`. Helpers above line 167 (`scorePainIntensity`, `scoreCountArray`, `classifyTotalScore`, `calculateContextProfile`, `hasTag`, etc.) and constants (`SCORE_RULES`, `SLEEP_MAP`, `TOTAL_SCORE_LEVELS`) stay module-private — only `mapRecord` is exported.

**Footer pattern (D-10-02 verbatim, identical to `quizify-mapping.js`):**
```js
// === DUAL-EXPORT FOOTER (D-10-02) ===
if (typeof input !== "undefined") { output = mapRecord(input.data || {}); }
if (typeof module !== "undefined") { module.exports = { mapRecord }; }
```

**Strict-mode pattern (D-10-03):** First non-comment line of the file:
```js
"use strict";
```

---

### `make-scripts/quizify-mapping.js` (EDIT — wrap + footer)

**Analog:** self. Same wrap shape as `score-calculations.js` but the footer's IIFE-side body adapts to Module 1's input shape (RESEARCH §Example 2 + A8 — `input.quiz_response` may be array-wrapped).

**Footer body delta (RESEARCH §Example 2):**
```js
if (typeof input !== "undefined") {
    const raw = input.quiz_response;
    const record = Array.isArray(raw) ? raw[0] : raw;
    output = mapRecord(record);
}
if (typeof module !== "undefined") { module.exports = { mapRecord }; }
```

The `typeof input` and `typeof module` guards are byte-identical with `score-calculations.js`; only the body inside the `input` guard differs (Module 1 takes `quiz_response`; Module 2 takes `data`). Plan-phase confirms with user; default per A8 is "caller unwraps before passing to `mapRecord`."

**No source-logic changes** in this file (no Reomoto / no profile_base — those are in Module 2 only).

---

### `make-scripts/package.json` (NEW)

**Analog:** None in repo (first JS package manifest). Skeleton locked verbatim by D-10-15 + RESEARCH §Example 5:

```json
{
  "name": "quizify-make-scripts",
  "version": "0.0.0",
  "private": true,
  "scripts": {
    "test": "node --test"
  },
  "dependencies": {},
  "devDependencies": {}
}
```

**Invariant:** No top-level keys beyond these six. The Python grep-gate test (below) enforces empty `dependencies` AND `devDependencies` in CI.

---

### `make-scripts/.gitignore` (NEW)

**Analog:** None directly; locked verbatim by D-10-19 + RESEARCH §Example 6:

```
node_modules/
coverage/
```

**No other entries.** RESEARCH Anti-pattern note: do NOT add `package-lock.json` — empty deps means `npm install` is never run, so no lockfile is ever generated. (Plan-phase optionally documents this; not part of locked content.)

---

### `make-scripts/tests/contract-01.test.js` (NEW) and siblings `make-fix-01.test.js`, `make-fix-02.test.js`

**Analog:** RESEARCH §Pattern 3 (verbatim shape). Python sibling for the per-requirement-file idiom: `tests/test_argparse_ndjson.py` (each test function targets one requirement; comment names the spec line).

**Pattern (D-10-09 inline-citation comment + `node:assert/strict`):**
```js
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { mapRecord } = require("../score-calculations");
const fixture = require("./fixtures/score-calculations/peri-meno-row.json");

test("MAKE-FIX-01: peri_menu (underscore) → life_stage_profile=peri_menopause_menopause", () => {
    const out = mapRecord(fixture);
    // CONVENTIONS.md:18 — peri_menu (underscore, not hyphen)
    // ROADMAP success criterion #2
    assert.strictEqual(out.life_stage_profile, "peri_menopause_menopause");
});
```

**Per-file requirement mapping (D-10-06):**
- `contract-01.test.js` — assert `out.product_recommendation` populated; assert `"product_result"` key NOT present (CONVENTIONS.md §"CONTRACT-01 verification").
- `make-fix-01.test.js` — assert `out.is_peri_meno === true` and `out.life_stage` (or `life_stage_profile`) === `"peri_menopause_menopause"` for `peri_menu` fixture.
- `make-fix-02.test.js` — assert `out.activity_profile === "non_athlete"` when `is_athlete` undefined; `=== "athlete"` when true (CONVENTIONS.md §"MAKE-FIX-02 verification" — Pitfall D).

---

### `make-scripts/tests/cosmetic-01.test.js` (NEW; RED-before-GREEN per D-10-10)

**Analog:** RESEARCH Pitfall 6 sequencing note + Pattern 3 shape.

**Pattern — positive + negative-regression assertions (per CONTEXT Claude's-Discretion default):**
```js
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { mapRecord } = require("../score-calculations");

const fixture = require("./fixtures/score-calculations/work-remoto.json");

test("MAKE-COSMETIC-01: work=remoto → context_profile === 'Remoto'", () => {
    const out = mapRecord(fixture);
    // ROADMAP success criterion #1 — score-calculations.js:157
    // Was "Reomoto" (typo); fixed in MAKE-COSMETIC-01.
    assert.strictEqual(out.context_profile, "Remoto");
});

test("MAKE-COSMETIC-01 negative regression: literal 'Reomoto' never appears in any fixture output", () => {
    const dir = path.join(__dirname, "fixtures", "score-calculations");
    for (const f of fs.readdirSync(dir).filter(x => x.endsWith(".json"))) {
        const fix = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
        const out = mapRecord(fix);
        // D-10-09 negative-regression citation: ROADMAP SC #1
        assert.notStrictEqual(out.context_profile, "Reomoto",
            `fixture ${f} regressed to typo`);
    }
});
```

**Sequencing (D-10-10 + RESEARCH Pitfall 6):**
1. **Wrap commit** — extract `mapRecord` + add footer in BOTH modules; PRESERVE typo and dead init. (Tests not yet committed; modules now `require()`-able.)
2. **RED commit** — add all six test files. `cosmetic-01` and `cosmetic-02` fail with clean diagnostics (`Expected "Remoto" got "Reomoto"`); the other 4 pass.
3. **GREEN commit** — apply both source fixes (`Reomoto`→`Remoto` :157; remove `profile_base` init :217). Suite goes 6/6 green.

The failing-then-passing trail must be visible in `git log`.

---

### `make-scripts/tests/cosmetic-02.test.js` (NEW; sweep)

**Analog:** RESEARCH Open Q3 (sweep recommendation) + Pattern 2 (`fs.readdirSync` loop shape).

**Pattern — exhaustive fixture sweep:**
```js
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { mapRecord } = require("../score-calculations");

test("MAKE-COSMETIC-02: 'profile_base' never appears in mapRecord output across all fixtures", () => {
    const dir = path.join(__dirname, "fixtures", "score-calculations");
    const files = fs.readdirSync(dir).filter(f => f.endsWith(".json"));
    assert.ok(files.length >= 5, "need fixtures covering all profile branches");
    for (const f of files) {
        const fix = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
        const out = mapRecord(fix);
        // ROADMAP success criterion #1 — score-calculations.js:217 dead init removed
        assert.notStrictEqual(out.profile, "profile_base",
            `fixture ${f}: profile fell through to dead init`);
        // Belt-and-suspenders: stringify and grep
        assert.ok(!JSON.stringify(out).includes("profile_base"),
            `fixture ${f}: 'profile_base' string found anywhere in output`);
    }
});
```

**Branch coverage required (RESEARCH §Wave 0 Gaps):** fixtures must exercise `has_red_flags=true`, `score_level=severo`, `=moderado`, `=leve` (low_complexity) — minimum 4 fixtures for cosmetic-02; combined with `work-remoto.json` for cosmetic-01 the score-calculations fixture set is ≥ 5.

---

### `make-scripts/tests/globals.test.js` (NEW)

**Analog:** RESEARCH Pattern 2 (verbatim — copy directly).

**Pattern (D-10-11..D-10-13):**
```js
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function loadFixtures(moduleName) {
    const dir = path.join(__dirname, "fixtures", moduleName);
    return fs.readdirSync(dir)
        .filter(f => f.endsWith(".json"))
        .map(f => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
}

test("score-calculations leaks no globals", () => {
    const before = new Set(Reflect.ownKeys(globalThis));   // D-10-11: Reflect.ownKeys (sym + str)
    const { mapRecord } = require("../score-calculations");
    for (const fixture of loadFixtures("score-calculations")) mapRecord(fixture);
    const leaked = Reflect.ownKeys(globalThis).filter(k => !before.has(k));
    // D-10-12: no allowlist — any new key fails
    assert.deepStrictEqual(leaked, [],
        `score-calculations.js leaked: ${String(leaked)}`);
});

test("quizify-mapping leaks no globals", () => {
    const before = new Set(Reflect.ownKeys(globalThis));
    const { mapRecord } = require("../quizify-mapping");
    for (const fixture of loadFixtures("quizify-mapping")) mapRecord(fixture);
    const leaked = Reflect.ownKeys(globalThis).filter(k => !before.has(k));
    assert.deepStrictEqual(leaked, [],
        `quizify-mapping.js leaked: ${String(leaked)}`);
});
```

**Notes:**
- `Set` for `before` — array `.includes` is O(n).
- `Reflect.ownKeys` not `Object.keys` (D-10-11) — captures symbol-keyed leaks.
- Each `test()` block re-snapshots independently (D-10-13) so module-load order doesn't matter.

---

### `make-scripts/tests/fixtures/{quizify-mapping,score-calculations}/*.json` (NEW)

**Analog:** `make-scripts/CONVENTIONS.md` §"CONTRACT-01 verification" inline-JSON shape (lines 48–59 — `{ "product-recommendation": ..., "email": "test@example.com", "firstName": "Test", "lastName": "User", ... }`).

**Pattern — synthetic + Make.com paste-compatible (D-10-07 + D-10-08 + T-PII-01):**
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

**Forbidden values (T-PII-01 carry-forward):** No row data from `docs/quizify-submissions.csv`. Specifically forbidden by name in CONVENTIONS.md §"MAKE-FIX-01 verification": `Karen Retamal`, `Javielys Mancilla`, real emails, real phones. Use `Test User` / `test@example.com` only.

**Required fixtures:**

`fixtures/quizify-mapping/`:
- `happy-path.json` — minimum one structurally-complete record.
- `peri-meno-row.json` — `menopause_status: "Perimenopausia"` to exercise `peri_menu` tag emission.

`fixtures/score-calculations/`:
- `happy-path-low-score.json` — `score_level=leve` branch.
- `red-flags-row.json` — `has_red_flags: true` branch.
- `peri-meno-row.json` — for life-stage refinement coverage (also feeds `make-fix-01`).
- `activity-non-athlete.json` — `is_athlete` undefined (feeds `make-fix-02`).
- `activity-athlete.json` — `is_athlete: true` (feeds `make-fix-02`).
- `work-remoto.json` — exercises `Reomoto`/`Remoto` branch (feeds `cosmetic-01`).
- (Add `severo` and `moderado` score-level fixtures for `cosmetic-02` branch sweep.)

Minimum count: ≥ 5 score-calculations fixtures + ≥ 2 quizify-mapping fixtures (CONTEXT discretion).

---

### `quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py` (NEW)

**Analog:** `tests/test_security_grep_gates.py` (Phase 9, full file — 65 lines).

**Pattern to copy — module-level constants + per-invariant test functions:**
```python
# from test_security_grep_gates.py:21-25
ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "quizify_csv_ingest.py"
SRC = SRC_PATH.read_text(encoding="utf-8")
```

**Adapted for D-10-16 (RESEARCH §Pattern 4 verbatim):**
```python
"""Phase 10 D-10-16 — empty-deps gate for make-scripts/.

Asserts make-scripts/package.json ships with empty dependencies and devDependencies
so the stdlib-only-at-runtime invariant (D-13 extended to JS) is enforced in CI
without requiring Node to be installed in the pytest job.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "make-scripts" / "package.json"


def test_make_scripts_zero_runtime_deps():
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    assert pkg.get("dependencies", {}) == {}, \
        "D-13: no JS runtime deps allowed in make-scripts/"


def test_make_scripts_zero_dev_deps():
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    assert pkg.get("devDependencies", {}) == {}, \
        "D-13: no JS dev deps — node:test stdlib only"


def test_make_scripts_private_package():
    pkg = json.loads(PKG.read_text(encoding="utf-8"))
    assert pkg.get("private") is True, \
        "make-scripts/package.json must be marked private"
```

**Optional fourth test (RESEARCH §Wave 0 Gaps "use strict" gate):**
```python
def test_make_scripts_use_strict_directive():
    """D-10-03 — first non-comment, non-blank line is `"use strict";`."""
    for src in ("quizify-mapping.js", "score-calculations.js"):
        path = ROOT / "make-scripts" / src
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            assert stripped == '"use strict";', \
                f"{src}: first non-comment line is {stripped!r}, not \"use strict\";"
            break
```

---

### `quizify-csv-to-json-webhook/tests/test_make_scripts_no_pii.py` (NEW)

**Analog:** `tests/test_security_grep_gates.py` (grep-gate idiom) + `tests/conftest.py:127` `SYNTHETIC_PII_TOKENS` constant (T-PII-01 negative-substring source).

**Pattern — read every fixture, scan for forbidden tokens:**
```python
"""Phase 10 T-PII-01 carry-forward — make-scripts/tests/fixtures/ has no real PII.

Asserts no fixture file in make-scripts/tests/fixtures/ contains tokens drawn from
docs/quizify-submissions.csv. Names from CONVENTIONS.md §MAKE-FIX-01 verification
(Karen Retamal, Javielys Mancilla) are explicitly forbidden — they appear in
manual-verification docs but must NOT be ported into automated fixtures.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "make-scripts" / "tests" / "fixtures"

# Names explicitly named in CONVENTIONS.md as live-verification respondents (do NOT replicate).
FORBIDDEN_TOKENS = (
    "Karen Retamal", "Karen", "Retamal",
    "Javielys Mancilla", "Javielys", "Mancilla",
    # Add other tokens from SYNTHETIC_PII_TOKENS in conftest.py if applicable.
)


def _walk_fixtures():
    if not FIXTURE_ROOT.exists():
        return
    yield from FIXTURE_ROOT.rglob("*.json")


def test_no_real_pii_in_fixtures():
    leaks = []
    for path in _walk_fixtures():
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                leaks.append((path.name, token))
    assert not leaks, f"PII tokens found in fixtures: {leaks}"
```

**Note:** Plan-phase decides whether to import `SYNTHETIC_PII_TOKENS` from `conftest.py` directly (cleaner) or hard-code the forbidden names (more portable). Default: hard-code the CONVENTIONS.md-named tokens; conftest's tokens are emails/phones unlikely to appear in synthetic JSON anyway.

---

### `pyproject.toml` (EDIT — add fresh `[tool.pytest.ini_options]`)

**Analog:** None in this file (verified — no existing `[tool.pytest.ini_options]` table). Standard TOML idiom.

**Pattern (RESEARCH §Example 4 + Pitfall 3 — TOML array, not space-separated string):**

Append at end of `quizify-csv-to-json-webhook/pyproject.toml`:
```toml
[tool.pytest.ini_options]
norecursedirs = ["make-scripts", "node_modules"]
```

**Verification command (RESEARCH Pitfall 3):**
```bash
cd quizify-csv-to-json-webhook && pytest --collect-only | grep -c "\.test\.js"
# expected: 0
```

Existing 158 Python tests must still collect.

---

### `quizify-csv-to-json-webhook/README.md` (EDIT — `### Make.com module tests` subsection)

**Analog:** Phase 9 README pattern (commit `6edc5d1` — usage example added under existing H2; RESEARCH Pitfall 5).

**Pattern (D-11 ten-section lock + drift test — `tests/test_readme_help_alignment.py:18-29`):**
- Locked top-level sections (count = 10): Purpose, Quickstart, CLI reference, Configuration, Column assumptions, Output shape, Limitations, Privacy notes, Exit codes, Development.
- New content goes under `## Development` as a `###` subsection or paragraph. NEVER add a new top-level `## ...` heading.

**Subsection skeleton (D-10-20 invocation):**
```markdown
### Make.com module tests

The `make-scripts/` directory ships two co-owned Make.com IIFE modules
(`quizify-mapping.js`, `score-calculations.js`) plus a zero-dependency
`node:test` regression suite under `make-scripts/tests/`.

Run from repo root:

```sh
node --test quizify-csv-to-json-webhook/make-scripts/
```

Or, equivalent shorthand for operators inside `make-scripts/`:

```sh
cd quizify-csv-to-json-webhook/make-scripts && npm test
```

Requires Node 20+. No `npm install` is ever run — the package ships with
empty `dependencies` and `devDependencies` (enforced by
`tests/test_make_scripts_no_deps.py` in CI).

After merging changes to `quizify-mapping.js` or `score-calculations.js`,
operators must paste the updated module body into the live Make.com Code
modules and re-run the inline-JSON verification fixtures in
`make-scripts/CONVENTIONS.md` (CONTRACT-01 / MAKE-FIX-01 / MAKE-FIX-02).
The `node --test` suite catches regressions before paste; CONVENTIONS.md
fixtures catch operator-drift after paste.
```

**Drift-test invariant:** After edit, `pytest tests/test_readme_help_alignment.py` must stay 2/2 green. Verify section count remains exactly 10 (`grep -c "^## " README.md` = 10).

---

### `.github/workflows/<existing>` (EDIT or CREATE)

**Analog:** RESEARCH §Example 3 (verbatim skeleton).

**Pattern (D-10-17 + Pitfall 4 — no `cache: 'npm'`):**
```yaml
  make-scripts-test:
    name: make-scripts node:test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          # NO `cache: 'npm'` — empty deps, no lockfile (RESEARCH Pitfall 4).
      - name: Run node:test
        working-directory: quizify-csv-to-json-webhook/make-scripts
        run: node --test
```

**Plan-time discovery required (RESEARCH OQ#1):** `find .github -type f` returned empty in the working tree at research time. Plan-phase MUST run `find . -type d -name .github` and `git ls-files | grep .github` to locate the workflow file. If genuinely absent, this phase creates one (different task shape).

## Shared Patterns

### Inline citation comment on every assertion (D-10-09)
**Source:** RESEARCH §Pattern 3 + CONTEXT D-10-09.
**Apply to:** Every assertion in every `*.test.js` file (positive and negative — A9).
**Rule:** Comment names `CONVENTIONS.md:<line>` AND/OR `ROADMAP success criterion #N`. No opaque snapshot files.
```js
// CONVENTIONS.md:18 — peri_menu (underscore, not hyphen)
// ROADMAP success criterion #2
assert.strictEqual(out.is_peri_meno, true);
```

### Stdlib-only at runtime (D-13 extended to JS)
**Source:** D-10-15 + D-13.
**Apply to:** All `.test.js` files and both source modules.
**Rule:** Only `node:test`, `node:assert` (use `/strict` form), `node:fs`, `node:path` may appear in `require()` statements. No third-party imports anywhere. Enforced in CI by `test_make_scripts_no_deps.py`.

### Synthetic-only fixtures (T-PII-01)
**Source:** `tests/conftest.py:127` `SYNTHETIC_PII_TOKENS` constant + CONVENTIONS.md "DO NOT replicate" annotations.
**Apply to:** Every JSON file under `make-scripts/tests/fixtures/`.
**Rule:** Use `Test User`, `test@example.com`. Forbidden: any value from `docs/quizify-submissions.csv`; the names `Karen Retamal` and `Javielys Mancilla` (named in CONVENTIONS.md §MAKE-FIX-01). Enforced by `test_make_scripts_no_pii.py`.

### Dual-export footer (D-10-02)
**Source:** RESEARCH §Pattern 1 (verbatim).
**Apply to:** BOTH `quizify-mapping.js` AND `score-calculations.js`.
**Rule:** Both `typeof input` and `typeof module` guards required. Use `typeof X !== "undefined"` form (RESEARCH Pitfall 1 — never bare `if (input)` in strict mode).

### `"use strict";` at file top (D-10-03)
**Source:** RESEARCH §Example 1 / 2 (line 1).
**Apply to:** Every JS file in `make-scripts/` and `make-scripts/tests/` (modules and tests).
**Rule:** First non-comment, non-blank line. Optional Python grep-gate enforces it (`test_make_scripts_no_deps.py::test_make_scripts_use_strict_directive` if planner adds it).

### Append-only test file additions
**Source:** `tests/conftest.py:120` comment idiom ("Append-only; no existing fixture is mutated") — Phase 8/9 carry-forward.
**Apply to:** `pyproject.toml` (append new section), `README.md` (append within `## Development`), CI workflow (append job).
**Rule:** Existing config and existing tests must remain unmodified.

### Module-level `Path(__file__).resolve().parents[1]` for repo-root anchoring
**Source:** `tests/test_security_grep_gates.py:21` and `tests/test_readme_help_alignment.py:14`.
**Apply to:** Both new Python test files (`test_make_scripts_no_deps.py`, `test_make_scripts_no_pii.py`).
**Rule:** Anchor to `quizify-csv-to-json-webhook/` directory (one level up from `tests/`), then path-join into `make-scripts/`.

### RED-before-GREEN commit ordering (D-10-10)
**Source:** RESEARCH Pitfall 6 sequencing note.
**Apply to:** `cosmetic-01.test.js` ↔ `score-calculations.js:157` fix.
**Rule:** Three-commit sequence: (1) wrap commit (typo PRESERVED, modules require()-able), (2) RED commit (tests added; cosmetic-01/02 fail with clean diagnostic), (3) GREEN commit (source fixes applied; suite goes 6/6 green). Trail visible in `git log`.

## No Analog Found

| Surface | Reason |
|---|---|
| `make-scripts/package.json` | First JS package manifest in repo. Locked verbatim by D-10-15 + RESEARCH §Example 5. |
| `make-scripts/.gitignore` | First JS-scoped `.gitignore`. Locked verbatim by D-10-19 + RESEARCH §Example 6. |
| `node:test` runner usage | First JS test harness in repo. Skeletons locked in RESEARCH §Patterns 2 / 3. |
| `Reflect.ownKeys(globalThis)` snapshot | First globals-leak test in repo. Locked in RESEARCH §Pattern 2. |
| GitHub Actions `make-scripts-test` job | `.github/workflows/` empty in working tree at research time (RESEARCH OQ#1). Skeleton locked in RESEARCH §Example 3; plan-phase must locate or create the workflow file. |

## Metadata

**Analog search scope:**
- `quizify-csv-to-json-webhook/tests/test_security_grep_gates.py` (full file — Python grep-gate idiom).
- `quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` (full file — D-11 drift-test invariants + REQUIRED_SECTIONS list).
- `quizify-csv-to-json-webhook/tests/conftest.py:120-130` (append-only-fixture comment + `SYNTHETIC_PII_TOKENS`).
- `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` (full file — inline-JSON fixture shape, T-PII-01 forbidden names, tag-spelling table).
- `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` lines 150–250 (Reomoto site, profile_base init, branch coverage).
- `quizify-csv-to-json-webhook/pyproject.toml` (full file — confirmed `[tool.pytest.ini_options]` absent; fresh section).
- `.planning/phases/09-auto-01-http-post-delivery/09-PATTERNS.md` (format mirror).

**Files scanned:** 7 source/config + RESEARCH.md + CONTEXT.md (locked skeletons treated as authoritative for surfaces with no in-repo analog).

**Pattern extraction date:** 2026-05-05.
