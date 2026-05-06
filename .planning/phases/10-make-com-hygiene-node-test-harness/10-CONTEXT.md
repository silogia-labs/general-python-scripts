# Phase 10: Make.com Hygiene & Node Test Harness - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

The two co-owned Make.com JS modules (`quizify-mapping.js`, `score-calculations.js`) ship cosmetic fixes (`Reomoto`→`Remoto` typo, dead `profile_base` initializer removal) locked behind a zero-dependency `node:test` regression net that retroactively covers v1.1 fixes (CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02) and the new v1.2 cosmetic fixes (MAKE-COSMETIC-01/02), plus a CI gate preventing accidental global writes or npm dependency creep. Parallel-safe with Phases 7–9 — no Python pipeline changes.

**In scope:** JS source edits in `make-scripts/`, new `make-scripts/tests/` tree, `make-scripts/package.json`, `make-scripts/.gitignore`, `pyproject.toml` `norecursedirs` addition, README additions for `make-scripts/` testing, GitHub Action job for `node --test`, Python grep-gate test for empty deps.

**Out of scope:** Python pipeline changes; behavioral changes to JS scoring logic beyond the two locked cosmetic fixes; new Make.com features; eslint/prettier or any JS toolchain beyond stdlib `node:test`.

</domain>

<decisions>
## Implementation Decisions

### mapRecord Extraction Shape
- **D-10-01:** Both modules wrap all top-level logic in a pure `function mapRecord(record) { ... return out; }`. Top-level body becomes function body; `data`/`tags` derive from the `record` parameter (not `input.data`).
- **D-10-02:** Dual-export footer pattern is mandatory and identical across both modules:
  ```js
  if (typeof input !== "undefined") { output = mapRecord(input.data || {}); }
  if (typeof module !== "undefined") { module.exports = { mapRecord }; }
  ```
  Both guards are required: the `input` guard prevents Node `require()` from throwing on the undefined Make.com `input` global; the `module` guard prevents Make.com's IIFE sandbox from breaking on the undefined `module` global.
- **D-10-03:** `"use strict";` is the first non-comment line of every module (criterion #3).
- **D-10-04:** Only `mapRecord` is exported. Helpers (`scorePainIntensity`, `hasTag`, `scoreCountArray`, `classifyTotalScore`, etc.) and constants (`SCORE_RULES`, `SLEEP_MAP`, `TOTAL_SCORE_LEVELS`) stay module-private. Tests assert through the public `mapRecord` surface only — refactors of helpers must not break tests.
- **D-10-05:** Make.com paste-in deployment must remain byte-paste-compatible — operators copy the whole file into Make.com's code module without manual edits. Verified by re-running CONVENTIONS.md MAKE-FIX-01/02 inline-JSON test fixtures against the deployed module.

### Test Layout & Fixtures
- **D-10-06:** Per-requirement test files under `make-scripts/tests/`:
  - `tests/contract-01.test.js` — CONTRACT-01 (`product-recommendation` → `product_recommendation`)
  - `tests/make-fix-01.test.js` — MAKE-FIX-01 (`peri_menu` underscore tag → `peri_menopause_menopause`)
  - `tests/make-fix-02.test.js` — MAKE-FIX-02 (`activity_profile` defaults to `non_athlete` when `is_athlete` undefined)
  - `tests/cosmetic-01.test.js` — MAKE-COSMETIC-01 (`Reomoto` → `Remoto` at `score-calculations.js:157`; fail-before-fix RED case)
  - `tests/cosmetic-02.test.js` — MAKE-COSMETIC-02 (`profile_base` does not appear in `mapRecord` output for any fixture)
  - `tests/globals.test.js` — globalThis snapshot diff (criterion #3)
- **D-10-07:** Fixtures live as standalone JSON files under `tests/fixtures/quizify-mapping/` and `tests/fixtures/score-calculations/`, loaded via `require()` or `fs.readFileSync`. Format mirrors the inline-JSON paste-in payloads documented in `CONVENTIONS.md` so a fixture file can be pasted directly into Make.com's module test interface for live verification.
- **D-10-08:** All fixtures are synthetic-only (T-PII-01 carry-forward). Names like `Test User`, `test@example.com`. No values from `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` may appear in any fixture file. Existing v1.1 grep gates that block real PII tokens extend to `make-scripts/tests/fixtures/`.
- **D-10-09:** Each `node:test` assertion includes an inline citation comment naming the CONVENTIONS.md line and/or ROADMAP success criterion the assertion locks. Pattern:
  ```js
  // CONVENTIONS.md:18 — peri_menu (underscore, not hyphen)
  // ROADMAP success criterion #2
  assert.strictEqual(out.is_peri_meno, true);
  ```
  No opaque snapshot files. Reviewers must be able to jump from any failing assertion to the spec line that justifies it.
- **D-10-10:** RED-before-GREEN ordering for cosmetic fixes — `tests/cosmetic-01.test.js` is committed in a state that **fails against current `score-calculations.js:157`** (`Reomoto`), then the source fix flips it green in the same plan or the immediate next plan. Test diff and source diff land in separate commits so the failing-then-passing trail is visible in `git log`.

### globalThis Snapshot Strategy
- **D-10-11:** Snapshot mechanism uses `Reflect.ownKeys(globalThis)` (string + symbol keys), not `Object.keys()`. Captures Node-internal symbol-keyed state too.
- **D-10-12:** Diff contract: snapshot keys *before* `require(module)`, then exercise the module with the full fixture set (every JSON file under `tests/fixtures/<module>/`), then re-snapshot. Assert leaked keys array is exactly `[]` — no allowlist. Any new key fails the test with the leaked names in the assertion message.
- **D-10-13:** The snapshot test runs both modules × representative fixture set in the same test file (`tests/globals.test.js`), one `test()` block per module. Each block re-reads the before-snapshot independently so module ordering does not affect the assertion.
- **D-10-14:** The test runs in a single `node --test` process where each `tests/*.test.js` file is its own subtest scope; module-level state from one file does not bleed into another (Node test runner spawns one worker per file by default).

### CI Gates & Runner Wiring
- **D-10-15:** `make-scripts/package.json` is a private package with `"private": true`, `"scripts": { "test": "node --test" }`, empty `"dependencies": {}`, and empty `"devDependencies": {}`. No other top-level keys beyond `name`, `version`.
- **D-10-16:** Empty-deps gate is enforced by a Python pytest test (extends Phase 9's grep-gate pattern, runs in existing pytest CI without requiring Node):
  ```python
  def test_make_scripts_zero_deps():
      pkg = json.loads(Path("quizify-csv-to-json-webhook/make-scripts/package.json").read_text())
      assert pkg.get("dependencies", {}) == {}, "D-13: no JS runtime deps allowed"
      assert pkg.get("devDependencies", {}) == {}, "D-13: no JS dev deps — node:test stdlib only"
  ```
  File location: `quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py` (alongside other Python tests).
- **D-10-17:** A new GitHub Actions job runs `cd quizify-csv-to-json-webhook/make-scripts && node --test` on `actions/setup-node@v4` with `node-version: "20"`. Job is added to the existing CI workflow (not a new workflow file) so PR status checks stay consolidated. Job runs in parallel with the existing pytest job.
- **D-10-18:** `pyproject.toml` `[tool.pytest.ini_options]` adds `norecursedirs = ["make-scripts", "node_modules"]` so pytest does not attempt to collect `*.test.js` files. Existing entries (if any) are preserved.
- **D-10-19:** `make-scripts/.gitignore` blocks `node_modules/` and `coverage/`. No other entries.
- **D-10-20:** Local-dev invocation documented in README: `node --test quizify-csv-to-json-webhook/make-scripts/` (raw command, no `cd` required) is the canonical form. `npm test` is mentioned as the equivalent shorthand for operators inside `make-scripts/`.

### Claude's Discretion
- Exact wording of the README addition for `make-scripts/` testing (must respect D-11 ten-section lock + drift test).
- Exact `node-version` minor (`"20"` is fine; bump to LTS `"22"` is acceptable if `node:test` parity verified).
- Whether `cosmetic-01.test.js` asserts `out.work_profile !== "Reomoto"` (negative) or `=== "Remoto"` (positive) — both satisfy criterion #1; pick whichever is clearer at write time. Default: positive assertion plus a negative regression assertion that the literal string `"Reomoto"` does not appear in any fixture's output.
- Number of fixtures per module (minimum: one happy-path + one edge per branch covered by an assertion).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Project-Level
- `.planning/ROADMAP.md` — Phase 10 entry: 5 success criteria with file:line citations (`score-calculations.js:157`, `score-calculations.js:217`).
- `.planning/REQUIREMENTS.md` — MAKE-COSMETIC-01/02, MAKE-TEST-01/02/03 requirement definitions.
- `.planning/PROJECT.md` — D-13 (stdlib-only-at-runtime), D-11 (README ten-section lock), T-PII-01 (synthetic-fixtures-only) carry-forward locks.
- `.planning/STATE.md` — v1.2 entry constraints; Phase 10 carried-flag: empirical Make.com IIFE sandbox semantics for `module`, `"use strict"`, `console` to validate dual-export-guard pattern.

### Make.com Module Conventions
- `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` §"Tag naming convention" — canonical tag spelling table (line 11+); `peri_menu` at line 18.
- `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` §"CONTRACT-01 verification" — inline-JSON fixture format that fixture JSON files must mirror.
- `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` §"MAKE-FIX-01 verification" — Karen Retamal / Javielys Mancilla rows 10/35 (DO NOT replicate; use synthetic equivalents).
- `quizify-csv-to-json-webhook/make-scripts/CONVENTIONS.md` §"MAKE-FIX-02 verification" — Pitfall D (`undefined is_athlete` → `non_athlete` default).

### Source Files Under Test
- `quizify-csv-to-json-webhook/make-scripts/quizify-mapping.js` — Module 1 (CSV record → mapped record + tags).
- `quizify-csv-to-json-webhook/make-scripts/score-calculations.js` — Module 2 (mapped record → scores + profile + email_template_id). Cosmetic fixes target lines 157 (`Reomoto`) and 217 (`profile = "profile_base"`).

### Prior Phase Context
- `.planning/phases/04-make-com-js-contract-fixes/` — original CONTRACT-01 / MAKE-FIX-01 / MAKE-FIX-02 work this phase retroactively tests.
- `.planning/phases/09-auto-01-http-post-delivery/09-CONTEXT.md` — most recent phase; references the grep-gate test pattern this phase extends to JS deps enforcement.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Phase 9 grep-gate pattern** (`tests/test_grep_gates.py` style) — extend to `tests/test_make_scripts_no_deps.py` (D-10-16). Same idiom: pytest reads a source file, asserts presence/absence of literal strings or JSON keys.
- **`CONVENTIONS.md` inline-JSON fixtures** — already documented for live Make.com test interface; lift the JSON shape directly into `tests/fixtures/*.json` files so a single fixture serves both automated tests and manual Make.com verification.
- **TRAIL-03 / D-11 drift-test pattern** — README additions for `make-scripts/` testing must keep `tests/test_readme_help_alignment.py` (2/2) green; section count and ten-section ordering are locked.

### Established Patterns
- **Make.com IIFE sandbox** — modules execute as a script body where `input` is injected and the last `output =` assignment becomes the module result. There is no `module`, `require`, `exports`, or `console.log` reliable contract. Dual-export guards must defend both sides.
- **Snake-case tag identifiers** (`CONVENTIONS.md` §Tag naming) — `tags.includes()` is case-sensitive exact-match; the `peri_menu` vs `peri-menu` incident is the canonical landmine. Fixture tag arrays must use exact CONVENTIONS.md spellings.
- **Stdlib-only at runtime** (D-13) — extends to JS: `node:test`, `node:assert`, `node:fs`, `node:path` are the only allowed imports in tests. No `chai`, `sinon`, `nyc`, etc.
- **Synthetic-only fixtures** (T-PII-01) — no values from `docs/quizify-submissions.csv` may appear in test fixtures. Rows 10 and 35 (Karen Retamal, Javielys Mancilla) are explicitly named in CONVENTIONS.md as live-verification respondents — they must NOT be ported into automated fixtures.

### Integration Points
- `pyproject.toml` `[tool.pytest.ini_options]` — append/extend `norecursedirs` to include `"make-scripts"` and `"node_modules"`. Verify no existing tests rely on pytest walking those directories.
- `.github/workflows/` — extend the existing CI workflow with a `make-scripts-test` job rather than creating a new workflow file. Keep PR status checks consolidated.
- `quizify-csv-to-json-webhook/README.md` — `make-scripts/` testing section addition; verify section count matches the locked ten-section list before commit.

</code_context>

<specifics>
## Specific Ideas

- The `Reomoto` typo at `score-calculations.js:157` is inside a `getWorkProfile()` (or equivalent) helper — verify whether this helper's output is exposed in `mapRecord` output. If not directly exposed, the cosmetic-01 test asserts via the downstream consumer (e.g., `out.profile` or `out.work_profile`) that uses the helper's return value.
- The `profile = "profile_base"` initializer at `score-calculations.js:217` is dead because the immediately-following `if (data.has_red_flags) { profile = "red_flags"; } else { ... }` reassigns `profile` on every code path. Removing it must not change any branch's final `profile` value — verify by exhaustive fixture coverage of (`has_red_flags` × `score_level` × `is_postpartum` × `is_peri_meno`) branches.
- Treat `score_total` (JS-recomputed) vs `score-value` (Python pass-through) as out of scope for this phase per CONVENTIONS.md note — defer the audit.

</specifics>

<deferred>
## Deferred Ideas

- **score_total ↔ score-value reconciliation audit** — CONVENTIONS.md §"Tag naming" notes a post-v1.1 audit should confirm agreement between JS-recomputed `score_total` and Python pass-through `score-value`. Out of Phase 10 scope. → v1.3 candidate.
- **eslint / prettier on `make-scripts/`** — would require dev dependencies, violating empty-deps lock. If wanted, gate it behind a future phase that explicitly relaxes the constraint. → v1.3+ candidate.
- **JS coverage tool (c8, nyc)** — same dev-deps blocker as eslint. `node:test` reports basic stats; deeper coverage is deferred. → v1.3+ candidate.
- **`tap`/`junit` reporter for CI** — `node --test`'s default TAP output is acceptable; structured reporter integration deferred. → v1.3+ candidate.

</deferred>

---

*Phase: 10-make-com-hygiene-node-test-harness*
*Context gathered: 2026-05-05*
