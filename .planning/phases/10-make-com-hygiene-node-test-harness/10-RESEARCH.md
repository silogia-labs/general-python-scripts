# Phase 10: Make.com Hygiene & Node Test Harness — Research

**Researched:** 2026-05-05
**Domain:** Node.js stdlib testing (`node:test`) + dual-environment JS modules (Make.com IIFE sandbox ↔ Node `require()`) + Python pytest config + GitHub Actions CI extension
**Confidence:** HIGH

## Summary

Phase 10 is a parallel-safe, low-blast-radius hygiene phase that retrofits a zero-dependency `node:test` harness onto the two co-owned Make.com JS modules (`quizify-mapping.js`, `score-calculations.js`), ships two cosmetic source fixes (Reomoto→Remoto typo at `score-calculations.js:157`; dead `profile = "profile_base"` initializer at `score-calculations.js:217`), and adds CI gates that prevent npm dependency creep. CONTEXT.md already locks 20 implementation decisions (D-10-01..D-10-20) covering module shape, dual-export footer, fixture layout, globalThis snapshot strategy, and CI wiring — research's job here is to verify, not redesign.

The single most important runtime fact: **as of Node 20, `node --test` defaults to process-level test isolation** — each `tests/*.test.js` file runs in a separate child process, so module-level state cannot bleed between files. This is verified [CITED: nodejs.org/docs/latest-v22.x/api/cli.html — `--test-concurrency` doc explicitly states "If `--experimental-test-isolation` is set to 'none', this flag is ignored and concurrency is one. Otherwise, concurrency defaults to `os.availableParallelism() - 1`."]. D-10-14's claim ("Node test runner spawns one worker per file by default") is confirmed.

The second important fact: **the current modules cannot be `require()`d at all** — both depend on the Make.com `input` global at top-level evaluation. I empirically verified this: `node -e 'require("./score-calculations.js")'` throws `ReferenceError: input is not defined` at line 170. The `function mapRecord(record)` extraction (D-10-01) plus the dual-export footer (D-10-02) are the minimum viable change to make the modules testable while keeping Make.com paste-in compatibility. **[VERIFIED: empirical Node 24 run]**

**Primary recommendation:** Land Phase 10 in three commits per ROADMAP success-criterion ordering (D-10-10 RED-before-GREEN trail): (1) RED — add `mapRecord` extractions + dual-export footer + all six test files (`cosmetic-01.test.js` failing on the `Reomoto` literal); (2) GREEN — apply the two source fixes (`Reomoto`→`Remoto`, remove dead `profile_base` init); (3) Wiring — `pyproject.toml norecursedirs`, `make-scripts/package.json`, `.gitignore`, GH Actions job, README addition, Python grep-gate test for empty deps. The third commit is independent of (1)/(2) and can be parallelized.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-10-01 mapRecord extraction shape:** Both modules wrap top-level logic in pure `function mapRecord(record) { ... return out; }`. Top-level body becomes function body; `data`/`tags` derive from the `record` parameter (not `input.data`).

**D-10-02 Dual-export footer (mandatory, identical across both modules):**
```js
if (typeof input !== "undefined") { output = mapRecord(input.data || {}); }
if (typeof module !== "undefined") { module.exports = { mapRecord }; }
```
Both guards required: `input` guard prevents Node `require()` from throwing; `module` guard prevents Make.com IIFE sandbox from breaking on undefined `module` global.

**D-10-03** `"use strict";` is the first non-comment line of every module.

**D-10-04** Only `mapRecord` is exported. Helpers and constants stay module-private.

**D-10-05** Make.com paste-in must remain byte-paste-compatible — operators copy the whole file into Make.com's code module without manual edits.

**D-10-06** Per-requirement test files under `make-scripts/tests/`:
- `tests/contract-01.test.js` — CONTRACT-01
- `tests/make-fix-01.test.js` — MAKE-FIX-01 (`peri_menu` underscore)
- `tests/make-fix-02.test.js` — MAKE-FIX-02 (`activity_profile` non-athlete default)
- `tests/cosmetic-01.test.js` — MAKE-COSMETIC-01 (`Reomoto` → `Remoto`)
- `tests/cosmetic-02.test.js` — MAKE-COSMETIC-02 (`profile_base` does not appear in output)
- `tests/globals.test.js` — globalThis snapshot diff

**D-10-07** Fixtures live as standalone JSON under `tests/fixtures/quizify-mapping/` and `tests/fixtures/score-calculations/`. Format mirrors CONVENTIONS.md inline-JSON paste-in payloads.

**D-10-08** All fixtures synthetic-only (T-PII-01 carry-forward). No values from `docs/quizify-submissions.csv` permitted. Existing v1.1 grep gates that block real PII tokens extend to `make-scripts/tests/fixtures/`.

**D-10-09** Each `node:test` assertion includes inline citation comment naming CONVENTIONS.md line and/or ROADMAP success criterion. No opaque snapshot files.

**D-10-10** RED-before-GREEN ordering for cosmetic fixes — `cosmetic-01.test.js` is committed in a state that **fails against current `score-calculations.js:157`** (`Reomoto`), then the source fix flips it green. Test diff and source diff land in **separate commits** so the failing-then-passing trail is visible in `git log`.

**D-10-11** Snapshot mechanism uses `Reflect.ownKeys(globalThis)` (string + symbol keys), not `Object.keys()`.

**D-10-12** Diff contract: snapshot keys *before* `require(module)`, then exercise the module with the full fixture set, then re-snapshot. Assert leaked keys array is exactly `[]` — no allowlist.

**D-10-13** The snapshot test runs both modules × representative fixture set in the same test file (`tests/globals.test.js`), one `test()` block per module. Each block re-reads the before-snapshot independently.

**D-10-14** Test runs in a single `node --test` process where each `tests/*.test.js` file is its own subtest scope; module-level state from one file does not bleed into another.

**D-10-15** `make-scripts/package.json`: `"private": true`, `"scripts": { "test": "node --test" }`, empty `"dependencies": {}`, empty `"devDependencies": {}`. No other top-level keys beyond `name`, `version`.

**D-10-16** Empty-deps gate enforced by Python pytest test (extends Phase 9's grep-gate pattern, runs in existing pytest CI without requiring Node) at `quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py`.

**D-10-17** New GH Actions job runs `cd quizify-csv-to-json-webhook/make-scripts && node --test` on `actions/setup-node@v4` with `node-version: "20"`. Added to existing CI workflow (not a new file). Runs in parallel with pytest job.

**D-10-18** `pyproject.toml` `[tool.pytest.ini_options]` adds `norecursedirs = ["make-scripts", "node_modules"]`. Existing entries preserved.

**D-10-19** `make-scripts/.gitignore` blocks `node_modules/` and `coverage/`. No other entries.

**D-10-20** Local-dev invocation: `node --test quizify-csv-to-json-webhook/make-scripts/` is the canonical form; `npm test` is the equivalent shorthand for operators inside `make-scripts/`.

### Claude's Discretion

- Exact wording of README addition for `make-scripts/` testing (must respect D-11 ten-section lock + drift test).
- Exact `node-version` minor (`"20"` is fine; bump to LTS `"22"` acceptable if `node:test` parity verified).
- Whether `cosmetic-01.test.js` asserts `out.context_profile !== "Reomoto"` (negative) or `=== "Remoto"` (positive) — both satisfy criterion #1. Default: positive assertion plus negative regression assertion that literal `"Reomoto"` does not appear in any fixture's output.
- Number of fixtures per module (minimum: one happy-path + one edge per branch covered by an assertion).

### Deferred Ideas (OUT OF SCOPE)

- `score_total ↔ score-value` reconciliation audit → v1.3.
- eslint / prettier on `make-scripts/` (would require dev deps, violating empty-deps lock) → v1.3+.
- JS coverage tool (c8, nyc) — same dev-deps blocker → v1.3+.
- `tap` / `junit` reporter for CI — `node --test`'s default TAP output is acceptable → v1.3+.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAKE-COSMETIC-01 | `Reomoto` → `Remoto` typo at `score-calculations.js:157` | Verified — typo is in `calculateContextProfile` `if (work.includes("remoto")) return "Reomoto";` (line 157). Helper output flows into `out.context_profile` (line 276), so `cosmetic-01.test.js` asserts via `out.context_profile`. |
| MAKE-COSMETIC-02 | Dead `profile = "profile_base"` initializer at `score-calculations.js:217` removed | Verified — line 217 `let profile = "profile_base";` is unconditionally reassigned by `if (data.has_red_flags) { profile = "red_flags"; } else { ... }` (lines 220-233). Every code path overwrites it. Removing the initializer changes nothing functionally; test asserts `out.profile !== "profile_base"` and the literal string never appears in `mapRecord` output across full fixture sweep. |
| MAKE-TEST-01 | `node --test` harness with regression coverage for CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02, MAKE-COSMETIC-01/02 | Six per-requirement test files under D-10-06; CI gate enforces empty deps via D-10-16. |
| MAKE-TEST-02 | Pure `mapRecord(record)`; `module.exports` guarded by `typeof module !== "undefined"`; `"use strict";`; globalThis snapshot test | D-10-01..D-10-04 + D-10-11..D-10-13 cover this verbatim. |
| MAKE-TEST-03 | `pyproject.toml norecursedirs` + `make-scripts/.gitignore` | D-10-18 + D-10-19 cover this. Note: project has TWO `pyproject.toml` files — root has none; only `quizify-csv-to-json-webhook/pyproject.toml` exists with no current `[tool.pytest.ini_options]` section. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `mapRecord()` pure transform | Make.com runtime (production) | Node CLI (test only) | Production target is Make.com IIFE sandbox; Node is a test harness. Dual-export footer (D-10-02) reconciles both. |
| `node:test` runner | Local dev + CI (GH Actions) | — | Stdlib-only — no test framework deps. |
| Empty-deps enforcement | Python pytest (CI gate) | — | Existing Python test suite already runs in CI without Node; gate test reads `package.json` as JSON. Pattern reuse from `tests/test_security_grep_gates.py`. |
| globalThis leak detection | `node:test` (`tests/globals.test.js`) | — | Per-process snapshot diff via `Reflect.ownKeys(globalThis)` before/after `require()`. |
| pytest collection scope | `pyproject.toml` `[tool.pytest.ini_options]` | — | Single config table — currently empty in `quizify-csv-to-json-webhook/pyproject.toml`; this phase creates it. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `node:test` | stdlib (Node 20+ stable) | Test runner with TAP output, file isolation, hooks | Stdlib — D-13 stdlib-only-at-runtime extends to JS per D-10-15. Stable since Node 20.0. [CITED: nodejs.org/docs/latest-v22.x/api/test.html] |
| `node:assert` | stdlib | Assertions (`strictEqual`, `deepStrictEqual`, `notStrictEqual`) | Stdlib companion to `node:test`. |
| `node:fs` | stdlib | Read JSON fixtures (alternative to `require()`) | Stdlib. |
| `node:path` | stdlib | Resolve fixture paths from `__dirname` | Stdlib. |
| `actions/setup-node` | v4 | GH Actions Node setup | [CITED: github.com/actions/setup-node — v4 is current major]. With empty deps, no `cache: 'npm'` needed (no lockfile, no `npm install`). |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `node:test` `describe`/`it` | stdlib | BDD-style aliases for `suite()`/`test()` | Optional — D-10 examples use `test()` directly. Either is fine; pick one and stay consistent across files. [CITED: nodejs.org/docs/latest-v22.x/api/test.html — describe/it are aliases for suite/test] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `node:test` | `vitest`, `jest`, `mocha+chai` | Adds dev-deps; violates D-10-15 empty-`devDependencies` lock and D-13 stdlib-only ethos. Already explicitly rejected in REQUIREMENTS.md "Out of Scope" table. |
| globalThis snapshot via `Reflect.ownKeys` | `Object.keys(globalThis)` | `Object.keys` skips symbol-keyed and non-enumerable properties; would miss `Symbol(nodejs.util.promisify.custom)` and similar Node-internal leak vectors. D-10-11 already locks `Reflect.ownKeys`. |
| `actions/setup-node@v4` `node-version: 20` | `node-version: 22` | Both fine — `node:test` is stable in 20+. Sticking with 20 is safer because it's current LTS and matches the most-deployed runtime; bump to 22 only if a feature is needed (none required here). |

**Installation:** None — every dep is stdlib. `make-scripts/package.json` ships with `"dependencies": {}` and `"devDependencies": {}` and the CI gate enforces this.

**Version verification:**
- Node `node:test` stable status: stable since v20.0.0 [CITED: nodejs.org/docs/latest-v22.x/api/test.html]
- Local dev environment: Node v24.14.1 detected on this machine [VERIFIED: `node --version`]; CI will pin to 20.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────┐
                    │  Make.com IIFE sandbox (prod)    │
                    │   input → mapRecord(input.data)  │
                    │   output = mapRecord(...)        │
                    │   (no module, no require)        │
                    └──────────────▲───────────────────┘
                                   │  byte-paste-compatible
                                   │  (D-10-05)
                                   │
        ┌──────────────────────────┴──────────────────────────────┐
        │  quizify-mapping.js  /  score-calculations.js           │
        │  ─ "use strict";                                        │
        │  ─ function mapRecord(record) { ... return out; }       │
        │  ─ Helpers + constants (module-private)                 │
        │  ─ Dual-export footer:                                  │
        │      if (typeof input !== "undefined") output = ...     │
        │      if (typeof module !== "undefined") module.exports  │
        └──────────────▲──────────────────────────────────────────┘
                       │  require("./quizify-mapping")
                       │
        ┌──────────────┴───────────────┐    ┌─────────────────────┐
        │  node --test (CI + local)    │    │  pytest (existing)  │
        │   tests/contract-01.test.js  │    │   test_make_scripts │
        │   tests/make-fix-01.test.js  │    │     _no_deps.py     │
        │   tests/make-fix-02.test.js  │    │   (reads            │
        │   tests/cosmetic-01.test.js  │    │    package.json,    │
        │   tests/cosmetic-02.test.js  │    │    asserts deps={}) │
        │   tests/globals.test.js      │    └─────────────────────┘
        │   tests/fixtures/{module}/   │
        │     *.json (synthetic only)  │
        └──────────────────────────────┘
```

Data flow:
- **Production:** Make.com injects `input` → footer line 1 fires → `mapRecord(input.data)` → `output` global → next module.
- **Test:** Node `require()` skips footer line 1 (`input` undefined) → fires footer line 2 → `module.exports = { mapRecord }` → tests call `mapRecord(fixture)` directly.

### Recommended Project Structure

```
quizify-csv-to-json-webhook/
├── make-scripts/
│   ├── CONVENTIONS.md                  # existing
│   ├── quizify-mapping.js              # MODIFIED — wrap in mapRecord + footer
│   ├── score-calculations.js           # MODIFIED — wrap + footer + 2 cosmetic fixes
│   ├── package.json                    # NEW — D-10-15
│   ├── .gitignore                      # NEW — D-10-19
│   └── tests/
│       ├── contract-01.test.js         # NEW
│       ├── make-fix-01.test.js         # NEW
│       ├── make-fix-02.test.js         # NEW
│       ├── cosmetic-01.test.js         # NEW (RED-then-GREEN per D-10-10)
│       ├── cosmetic-02.test.js         # NEW
│       ├── globals.test.js             # NEW
│       └── fixtures/
│           ├── quizify-mapping/
│           │   ├── happy-path.json
│           │   └── peri-meno-row.json
│           └── score-calculations/
│               ├── happy-path-low-score.json
│               ├── red-flags-row.json
│               ├── peri-meno-row.json
│               ├── activity-non-athlete.json
│               ├── activity-athlete.json
│               └── work-remoto.json   # exercises the Reomoto/Remoto branch
├── pyproject.toml                      # MODIFIED — add [tool.pytest.ini_options] norecursedirs
└── tests/
    └── test_make_scripts_no_deps.py    # NEW — D-10-16

.github/workflows/
└── <existing-ci-workflow>.yml          # MODIFIED — add make-scripts-test job
```

### Pattern 1: Dual-Export Footer (D-10-02)

**What:** A two-line footer at the bottom of every Make.com module that reconciles two incompatible runtime contracts.

**When to use:** Any JS file that must run both as a Make.com IIFE module body (where `input` is injected, `module` is undefined) and as a Node `require()` target (where `module` is defined, `input` is undefined).

**Example:**
```js
// Source: CONTEXT.md D-10-02 (verbatim)
"use strict";

function mapRecord(record) {
    // ... all module logic, parameterized by `record` (not `input.data`) ...
    return out;
}

// Dual-export footer — must be byte-identical in both modules.
if (typeof input !== "undefined") { output = mapRecord(input.data || {}); }
if (typeof module !== "undefined") { module.exports = { mapRecord }; }
```

**Why both guards:**
- `typeof input !== "undefined"` — without this, Node `require()` fires line 1 and throws `ReferenceError: input is not defined` [VERIFIED: empirical Node 24 run against current `score-calculations.js`]. Confirmed via `typeof` (not direct reference) because Node forbids reading undeclared identifiers in strict mode.
- `typeof module !== "undefined"` — Make.com IIFE sandbox does not provide `module` / `exports`; bare `module.exports = ...` would throw at paste time.

### Pattern 2: globalThis Leak Snapshot (D-10-11..D-10-13)

**What:** Capture `Reflect.ownKeys(globalThis)` before `require()`, exercise the module with the full fixture set, re-snapshot, and assert leaked keys are exactly `[]`.

**Example:**
```js
// Source: CONTEXT.md D-10-11..D-10-13 (verbatim contract)
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
    const before = new Set(Reflect.ownKeys(globalThis));
    const { mapRecord } = require("../score-calculations");
    for (const fixture of loadFixtures("score-calculations")) {
        mapRecord(fixture);
    }
    const after = Reflect.ownKeys(globalThis);
    const leaked = after.filter(k => !before.has(k));
    assert.deepStrictEqual(leaked, [],
        `score-calculations.js leaked ${leaked.length} global keys: ${String(leaked)}`);
});

test("quizify-mapping leaks no globals", () => {
    const before = new Set(Reflect.ownKeys(globalThis));
    const { mapRecord } = require("../quizify-mapping");
    for (const fixture of loadFixtures("quizify-mapping")) {
        mapRecord(fixture);
    }
    const after = Reflect.ownKeys(globalThis);
    const leaked = after.filter(k => !before.has(k));
    assert.deepStrictEqual(leaked, [],
        `quizify-mapping.js leaked ${leaked.length} global keys: ${String(leaked)}`);
});
```

**Notes:**
- Use a `Set` for `before` — array `.includes()` is O(n) per lookup; with potentially hundreds of pre-existing global keys this matters for CI speed (minor but free win).
- `Reflect.ownKeys` returns string + symbol keys. `Object.keys` would miss symbol-keyed leaks like accidental writes to `Symbol(nodejs.something)`.
- D-10-12 mandates **no allowlist** — any new key fails the test. This is correct because `mapRecord` is pure-functional with no documented globals; any leak is a bug.

### Pattern 3: Per-Requirement Test File with Inline Citations (D-10-09)

**Example:**
```js
// Source: CONTEXT.md D-10-09 + ROADMAP success criterion #2
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { mapRecord } = require("../score-calculations");
const fixture = require("./fixtures/score-calculations/peri-meno-row.json");

test("MAKE-FIX-01: peri_menu (underscore) → is_peri_meno + life_stage_profile=peri_menopause_menopause", () => {
    const out = mapRecord(fixture);
    // CONVENTIONS.md:18 — peri_menu (underscore, not hyphen)
    // ROADMAP success criterion #2
    assert.strictEqual(out.life_stage_profile, "peri_menopause_menopause");
});
```

### Pattern 4: Python Grep-Gate Test for Empty Deps (D-10-16)

**Example (extends pattern from `tests/test_security_grep_gates.py`):**
```python
# quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py
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
        "make-scripts/package.json must be marked private to prevent accidental publish"
```

### Anti-Patterns to Avoid

- **Top-level reads of `input`** — current state of both modules. Breaks `require()` at evaluation time. Mitigated by D-10-01 (`mapRecord(record)` extraction).
- **Bare `module.exports = ...`** — would throw in Make.com IIFE where `module` is undefined. Mitigated by D-10-02 guard.
- **`if (input)` instead of `if (typeof input !== "undefined")`** — bare `input` reference throws ReferenceError in strict mode under Node before the check can short-circuit. Always use `typeof` for guard checks against undeclared identifiers.
- **Snapshot files (`.snap`)** — D-10-09 explicitly forbids opaque snapshots. Every assertion must cite a CONVENTIONS.md line or ROADMAP criterion in a comment.
- **Allowlisting "known" globals in the leak test** — D-10-12 mandates leaked-keys array equals `[]`. An allowlist would let real leaks slip through under symbol-keyed innocuous-looking names.
- **Putting `package-lock.json` in git** — empty deps means no lockfile is needed; if one is generated, `.gitignore` should exclude it. (Not in D-10-19 currently — flag for plan-checker; either add `package-lock.json` to `.gitignore` or document that no lockfile will ever be created because `npm install` is never run.)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test runner | Custom `assert.js` framework | `node:test` + `node:assert/strict` | Stdlib since Node 20; TAP output integrates with CI; file-level isolation built in. |
| Fixture loading | Custom YAML/CSV fixture format | JSON via `require()` or `fs.readFileSync` | JSON files double as Make.com paste-in test inputs (D-10-07). |
| Globals leak detection | Iterating `for ... in globalThis` | `Reflect.ownKeys(globalThis)` set diff | Symbol-keyed leaks invisible to enumeration. |
| Empty-deps CI enforcement | Bash `jq` gate in GH Actions | Python pytest reading `package.json` (D-10-16) | Pytest job already runs; reusing it avoids requiring Node in a second gate-only job. |

**Key insight:** Phase 10's value is **lock-in**, not feature delivery. The two source fixes are 4 LOC; the harness exists to prevent regression and dependency creep over the next year. Every "don't hand-roll" entry above protects that future-proofing surface.

## Runtime State Inventory

This is a code-only refactor + harness addition. No databases, services, OS-registered state, or build artifacts are renamed.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Make.com modules are stateless transforms; no DB/cache writes from `make-scripts/`. | None |
| Live service config | **Make.com scenario(s) consuming these modules** — operators paste the new module body into the live Make.com Code module(s). This is documented as D-10-05 (byte-paste-compatible). The deployment step lives in operator instructions, NOT in git/CI. | Document in README addition: after merge, paste updated `score-calculations.js` and `quizify-mapping.js` into Make.com Code modules; rerun the inline-JSON CONVENTIONS.md verification (CONTRACT-01 / MAKE-FIX-01 / MAKE-FIX-02) once. |
| OS-registered state | None | None |
| Secrets / env vars | None — modules read no secrets; `email` synthesis at lines 178-184 of `quizify-mapping.js` uses `Math.random` only. | None |
| Build artifacts / installed packages | `node_modules/` (currently does not exist; will never exist if D-10-15 holds). `.gitignore` blocks it preemptively per D-10-19. | None — `.gitignore` is the action. |

**Canonical question — "After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?":** Make.com's live Code modules contain a paste-in copy of the JS source. The live deployment will continue running the OLD `Reomoto` and dead-init code until an operator manually pastes the new module body. This is a **manual deployment step** — the README addition must call this out explicitly so the operator knows the merge is necessary but not sufficient for production.

## Common Pitfalls

### Pitfall 1: Strict-mode `typeof` guard semantics

**What goes wrong:** Writing `if (input) { ... }` instead of `if (typeof input !== "undefined") { ... }` throws `ReferenceError: input is not defined` in Node strict mode before the truthy check evaluates.

**Why it happens:** ES strict mode forbids reading undeclared identifiers. `typeof` is the only operator that can probe undeclared identifiers safely.

**How to avoid:** D-10-02 mandates `typeof` form. Code review checklist: any guard against a Make.com-injected global must use `typeof X !== "undefined"`.

**Warning signs:** First `node --test` run after extraction throws `ReferenceError` instead of running tests.

### Pitfall 2: Make.com IIFE re-paste drift

**What goes wrong:** Operator hand-edits the module after pasting (e.g., comments out the `module` guard "because it looks weird") — next git pull silently overwrites the live behavior next time someone re-pastes.

**Why it happens:** Make.com Code modules are opaque text boxes; there is no diff against the canonical file in git.

**How to avoid:** D-10-05 byte-paste-compatibility. CONVENTIONS.md verification fixtures (CONTRACT-01 / MAKE-FIX-01 / MAKE-FIX-02) must be re-run after every Make.com paste — these catch operator drift.

**Warning signs:** Live Make.com test interface output disagrees with `node --test` output for the same fixture.

### Pitfall 3: pyproject.toml `norecursedirs` syntax

**What goes wrong:** Adding `norecursedirs = "make-scripts node_modules"` (string) instead of `norecursedirs = ["make-scripts", "node_modules"]` (TOML array) — pytest may parse it as a single directory name.

**Why it happens:** pytest accepts both space-separated string and list forms historically, but TOML-native config in pyproject.toml expects a TOML array per [pytest docs](https://docs.pytest.org/en/stable/reference/customize.html#pyproject-toml).

**How to avoid:** Use TOML array literal exactly as D-10-18 specifies.

**Verification:** After change, run `pytest --collect-only` from `quizify-csv-to-json-webhook/` and confirm zero `*.test.js` files appear in the collection tree, and existing 158 Python tests still collect.

### Pitfall 4: GH Actions setup-node cache without lockfile

**What goes wrong:** Adding `cache: 'npm'` to `actions/setup-node@v4` without a `package-lock.json` causes the action to fail with "Dependencies lock file is not found".

**Why it happens:** The cache feature requires a lockfile to compute the cache key.

**How to avoid:** Omit `cache:` entirely. With empty deps there's no `npm install` step and nothing to cache. The job is just `setup-node` + `node --test`.

**Warning signs:** First CI run fails before reaching `node --test`.

### Pitfall 5: D-11 README ten-section drift

**What goes wrong:** Adding a new "## Make.com testing" section to README.md to document `node --test` invocation breaks `tests/test_readme_help_alignment.py::test_readme_has_all_required_sections` because it's not in the locked `REQUIRED_SECTIONS` tuple — but worse, adding a new top-level `##` section breaks the locked count of 10.

**Why it happens:** The drift test asserts presence of the 10 named sections (no count assertion currently — verified at line 18-29 of test file), but D-11 LOCKS the count at 10 conceptually. Adding an 11th `## ...` heading violates D-11 even if the test currently doesn't catch it.

**How to avoid:** Document `node --test` invocation as a **subsection** of `## Development` (e.g., `### Make.com module tests` or as a paragraph under `## Development`). Do NOT add a new top-level `##` heading. The 10 locked sections are: Purpose, Quickstart, CLI reference, Configuration, Column assumptions, Output shape, Limitations, Privacy notes, Exit codes, Development. [VERIFIED: `quizify-csv-to-json-webhook/README.md` `grep "^## "` returns exactly these 10.]

**Warning signs:** Section count goes to 11; or a new section heading the test doesn't recognize.

### Pitfall 6: cosmetic-01 RED commit assertion shape

**What goes wrong:** Writing `cosmetic-01.test.js` with assertion `assert.strictEqual(out.context_profile, "Remoto")` and committing it BEFORE wrapping the module in `mapRecord` + footer. Test will fail with `ReferenceError: input is not defined` (module crashes at require), not with the desired "Reomoto !== Remoto" mismatch — making the RED→GREEN signal noisy.

**Why it happens:** Two changes (extraction + cosmetic fix) must land in correct order.

**How to avoid:** Sequence the RED commit as:
1. Wrap both modules in `mapRecord` + dual-export footer (no source-logic changes — `Reomoto` typo and `profile_base` init are PRESERVED in this commit).
2. Add all six test files including `cosmetic-01.test.js` asserting `out.context_profile === "Remoto"`. At this point ONLY `cosmetic-01` and `cosmetic-02` should fail; the other 4 (contract-01, make-fix-01/02, globals) should already pass.
3. GREEN commit: apply the two cosmetic fixes (`Reomoto`→`Remoto` line 157; remove `let profile = "profile_base";` line 217 → `let profile;`).

This way the failing test's diagnostic is `Expected "Remoto" got "Reomoto"` — perfect RED signal — instead of a require-time crash.

**Warning signs:** RED commit's failure message doesn't name the typo.

## Code Examples

### Example 1: `score-calculations.js` shape after extraction (skeleton)

```js
"use strict";

// === CONFIG: scoring rules ===
const SCORE_RULES = { /* ... unchanged ... */ };
const SLEEP_MAP = { /* ... unchanged ... */ };
const TOTAL_SCORE_LEVELS = [ /* ... unchanged ... */ ];

// === HELPERS (module-private per D-10-04) ===
function toNumber(value) { /* ... unchanged ... */ }
function includesAny(haystack, patterns) { /* ... unchanged ... */ }
function scorePainIntensity(value) { /* ... unchanged ... */ }
// ... all other helpers unchanged ...
function calculateContextProfile({ age_range, work_shift_type, /* ... */ }) {
    // ...
    if (work.includes("remoto")) return "Remoto"; // FIX MAKE-COSMETIC-01 (was "Reomoto")
    // ...
}

// === MAIN ===
function mapRecord(record) {
    const data = record || {};
    const out = { ...data };
    const tags = Array.isArray(data.tags) ? data.tags : [];

    // ... all current top-level logic, unchanged but parameterized by `record` ...

    // FIX MAKE-COSMETIC-02: was `let profile = "profile_base";`
    let profile;
    let email_template_id = "9199514";

    if (data.has_red_flags) {
        profile = "red_flags";
    } else if (score_level === "severo") {
        profile = "high_complexity";
        email_template_id = "9199525";
    } else if (score_level === "moderado") {
        profile = "moderate_complexity";
        email_template_id = "9199522";
    } else {
        profile = "low_complexity";
        email_template_id = "9199514";
    }

    // ... rest unchanged ...

    return out;
}

// === DUAL-EXPORT FOOTER (D-10-02) ===
if (typeof input !== "undefined") { output = mapRecord(input.data || {}); }
if (typeof module !== "undefined") { module.exports = { mapRecord }; }
```

### Example 2: `quizify-mapping.js` shape after extraction (skeleton)

The current top-level reads `input.quiz_response` (line 90); after extraction `mapRecord(record)` accepts the record directly. The Make.com input adapter sits in the footer:

```js
"use strict";

const QUESTION_CONFIG = { /* ... unchanged ... */ };

function toStringArrayFromCsv(str) { /* ... unchanged ... */ }
function extractAnswer(record, index, fieldType) { /* ... unchanged ... */ }

function mapRecord(record) {
    // record is the un-arrayed quiz_response (current line 91 logic moves here)
    // Caller is responsible for unwrapping arrays before passing in.
    const output = {
        email: record.email || null,
        // ... all top-level logic unchanged ...
    };

    // ... process questions, derived tags, dedupe, email-randomization ...

    return output;
}

// === DUAL-EXPORT FOOTER (D-10-02) ===
if (typeof input !== "undefined") {
    const raw = input.quiz_response;
    const record = Array.isArray(raw) ? raw[0] : raw;
    output = mapRecord(record);
}
if (typeof module !== "undefined") { module.exports = { mapRecord }; }
```

**Note:** quizify-mapping's input adapter is slightly more involved than score-calculations' (it has to unwrap `Array.isArray(raw) ? raw[0] : raw`). D-10-02 says the footer is "identical across both modules" but the spirit is identical SHAPE — both have a `typeof input !== "undefined"` guard line and a `typeof module !== "undefined"` guard line. The IIFE-side body inside the input guard differs because the Make.com input shape differs (Module 1 receives `quiz_response`; Module 2 receives `data`). Plan-phase should clarify this with the user; the conservative read of D-10-02 is "guards are identical; bodies adapt to each module's input shape." This is consistent with current Module 1 line 90-91 and Module 2 line 170 reading different `input.*` properties.

### Example 3: GH Actions job addition

```yaml
# Append to existing CI workflow (NOT a new workflow file — D-10-17)
  make-scripts-test:
    name: make-scripts node:test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          # NO `cache: 'npm'` — empty deps, no lockfile (Pitfall 4)
      - name: Run node:test
        working-directory: quizify-csv-to-json-webhook/make-scripts
        run: node --test
```

### Example 4: pyproject.toml addition

Currently `quizify-csv-to-json-webhook/pyproject.toml` has NO `[tool.pytest.ini_options]` section. Add it fresh:

```toml
[tool.pytest.ini_options]
norecursedirs = ["make-scripts", "node_modules"]
```

[VERIFIED: `grep -n "tool.pytest\|norecursedirs" pyproject.toml` returns no matches — fresh section.]

### Example 5: `make-scripts/package.json`

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

### Example 6: `make-scripts/.gitignore`

```
node_modules/
coverage/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-edit Make.com Code modules + manual paste verification only | `node:test` regression net + dual-export pattern | This phase | Catches typos and global leaks before paste; CONVENTIONS.md verification still happens once per Make.com deploy, not per code change. |
| `experimental-test-isolation` flag (Node 18) | Default process-level isolation (Node 20+ stable) | Node 20.0 | D-10-14 holds without flags. |
| `Object.keys(globalThis)` for leak detection | `Reflect.ownKeys(globalThis)` | Pattern lock D-10-11 | Catches symbol-keyed leaks. |

**Deprecated/outdated:**
- `assert` (CommonJS bare module) — use `node:assert/strict` for stricter equality semantics (`assert.strictEqual` not `assert.equal`). [CITED: nodejs.org/docs/latest-v22.x/api/assert.html]
- `tap`/`tape`/`ava` test runners — superseded by stdlib `node:test` for greenfield modules.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Node `node:test` (stdlib, stable since Node 20) + `node:assert/strict`; Python `pytest` (existing) for the empty-deps grep gate |
| Config file | `make-scripts/package.json` `"scripts": { "test": "node --test" }` (D-10-15); `pyproject.toml` `[tool.pytest.ini_options]` (D-10-18, currently absent — created in this phase) |
| Quick run command | `node --test quizify-csv-to-json-webhook/make-scripts/` (single suite, ~6 files, < 2s) |
| Full suite command | `pytest quizify-csv-to-json-webhook/tests/ && node --test quizify-csv-to-json-webhook/make-scripts/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MAKE-COSMETIC-01 | `out.context_profile === "Remoto"` (positive) and string `"Reomoto"` does not appear in any fixture's `mapRecord` output (negative regression) | unit | `node --test quizify-csv-to-json-webhook/make-scripts/tests/cosmetic-01.test.js` | ❌ Wave 0 |
| MAKE-COSMETIC-02 | `out.profile !== "profile_base"` for all branches (red_flags, severo, moderado, leve) | unit | `node --test .../tests/cosmetic-02.test.js` | ❌ Wave 0 |
| MAKE-TEST-01 (CONTRACT-01) | `out.product_recommendation` populated; no `product_result` key | unit | `node --test .../tests/contract-01.test.js` | ❌ Wave 0 |
| MAKE-TEST-01 (MAKE-FIX-01) | `out.life_stage_profile === "peri_menopause_menopause"` for `peri_menu` tag fixture | unit | `node --test .../tests/make-fix-01.test.js` | ❌ Wave 0 |
| MAKE-TEST-01 (MAKE-FIX-02) | `out.activity_profile === "non_athlete"` when `is_athlete` undefined; `=== "athlete"` when true | unit | `node --test .../tests/make-fix-02.test.js` | ❌ Wave 0 |
| MAKE-TEST-02 (mapRecord export) | `typeof require("./quizify-mapping").mapRecord === "function"` and same for `score-calculations` | unit (covered implicitly by other tests successfully `require()`-ing) | `node --test .../tests/contract-01.test.js` | ❌ Wave 0 |
| MAKE-TEST-02 (`"use strict";`) | Source-level grep gate — first non-comment, non-blank line is `"use strict";` | source-level grep (Python pytest) | extend `tests/test_security_grep_gates.py` or add to `test_make_scripts_no_deps.py` | ❌ Wave 0 |
| MAKE-TEST-02 (globalThis snapshot) | `Reflect.ownKeys(globalThis)` set diff before/after `require + mapRecord(fixture)` is `[]` | unit | `node --test .../tests/globals.test.js` | ❌ Wave 0 |
| MAKE-TEST-03 (empty deps) | `package.json` `dependencies` and `devDependencies` are both `{}` | unit (Python pytest) | `pytest quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py` | ❌ Wave 0 |
| MAKE-TEST-03 (norecursedirs) | `pytest --collect-only` from `quizify-csv-to-json-webhook/` does not collect any `*.test.js` file | unit (existing pytest collection; verified empirically post-merge) | `pytest --collect-only quizify-csv-to-json-webhook/ \| grep -c "\.test\.js"` returns 0 | manual verify |
| MAKE-TEST-03 (.gitignore) | `make-scripts/.gitignore` contains `node_modules/` and `coverage/` | source-level (low value to automate; one-time check) | manual at PR review | manual verify |
| Regression: 158 existing pytest tests | All pre-existing tests still green | integration | `pytest quizify-csv-to-json-webhook/tests/` | ✅ exists |
| Regression: D-11 README drift | `tests/test_readme_help_alignment.py` 2/2 green after README addition | integration | `pytest quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` | ✅ exists |

### Sampling Rate

- **Per task commit:** `node --test quizify-csv-to-json-webhook/make-scripts/` (≤ 2s) + `pytest quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py quizify-csv-to-json-webhook/tests/test_readme_help_alignment.py` (~1s)
- **Per wave merge:** Full pytest suite + `node --test` (≤ 5s combined)
- **Phase gate:** Both suites green before `/gsd-verify-work`; 5/5 ROADMAP success criteria mapped to assertions.

### Wave 0 Gaps

- [ ] `make-scripts/tests/contract-01.test.js` — covers MAKE-TEST-01 (CONTRACT-01)
- [ ] `make-scripts/tests/make-fix-01.test.js` — covers MAKE-TEST-01 (MAKE-FIX-01)
- [ ] `make-scripts/tests/make-fix-02.test.js` — covers MAKE-TEST-01 (MAKE-FIX-02)
- [ ] `make-scripts/tests/cosmetic-01.test.js` — covers MAKE-COSMETIC-01 (RED-then-GREEN per D-10-10)
- [ ] `make-scripts/tests/cosmetic-02.test.js` — covers MAKE-COSMETIC-02
- [ ] `make-scripts/tests/globals.test.js` — covers MAKE-TEST-02 (globalThis leak)
- [ ] `make-scripts/tests/fixtures/quizify-mapping/*.json` — synthetic, ≥ 2 fixtures (happy + peri-meno edge)
- [ ] `make-scripts/tests/fixtures/score-calculations/*.json` — synthetic, ≥ 5 fixtures covering all `profile` branches + Reomoto/Remoto branch + activity_profile branches
- [ ] `make-scripts/package.json` — D-10-15
- [ ] `make-scripts/.gitignore` — D-10-19
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — D-10-18 (fresh section; verified absent)
- [ ] `quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py` — D-10-16
- [ ] Optional: source-level `"use strict";` grep gate (extend `test_security_grep_gates.py` or add to `test_make_scripts_no_deps.py`)
- [ ] GH Actions workflow modification — D-10-17 (need to discover existing workflow file path; see Open Question #1)
- [ ] README addition for `make-scripts/` testing — under `## Development` section to preserve D-11 ten-section lock (Pitfall 5)

## Project Constraints (from CLAUDE.md / .planning/PROJECT.md)

- **D-13 stdlib-only-at-runtime** — extends to JS in this phase: only `node:test`, `node:assert`, `node:fs`, `node:path` allowed. No `chai`, `sinon`, `c8`, `nyc`, `eslint`, `prettier`. CI gate enforces empty `dependencies` AND `devDependencies`.
- **D-11 README ten-section lock** — README additions for `make-scripts/` testing MUST be a subsection (or paragraph) under one of the 10 locked top-level sections. Recommended location: under `## Development`. Drift test (`tests/test_readme_help_alignment.py`, 2/2) must stay green.
- **T-PII-01 synthetic-fixtures-only** — no values from `docs/quizify-submissions.csv` permitted in any fixture under `make-scripts/tests/fixtures/`. Use `Test User`, `test@example.com`. Existing PII grep gates extend.
- **D-05 JSON top-level key order** — not directly relevant (this phase doesn't touch Python output), but Make.com modules' `mapRecord` output ordering should match the Make.com-side contract documented in CONVENTIONS.md.
- **TRAIL-03 default-order golden-fixture** — not touched by this phase (Python only); regression remains green by construction.
- **Co-owned consumer surface invariant** — both JS files must remain byte-paste-compatible with Make.com (D-10-05). The footer is the only "weird" addition; document it in CONVENTIONS.md.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js (local dev) | `node --test` | ✓ | v24.14.1 [VERIFIED] | — |
| Node.js (CI) | GH Actions job | ✗ (not yet wired) | will be 20 LTS via `actions/setup-node@v4` | — |
| Python pytest | existing test suite + new D-10-16 gate | ✓ | (running 158 tests in CI) | — |
| GitHub Actions runner | CI | ✓ assumed | ubuntu-latest | — |

**Missing dependencies with no fallback:** None — local dev has Node 24 (newer than CI's 20, but `node:test` is stable in both). Plan-phase needs to confirm CI baseline node-version (D-10-17 says `"20"`; verify).

**Missing dependencies with fallback:** None.

**Open question (resolved by plan-phase):** Where does the existing GH Actions CI workflow live? `find .github` returned no results in this repo's working tree — either the workflow file is not yet in git, or it's at a path not surfaced by `find`. Plan-phase must locate the existing workflow file before drafting the D-10-17 job addition. If no workflow exists yet, this phase creates one (and D-10-17's "added to the existing CI workflow" guidance becomes "create the CI workflow file" — a different task shape).

## Security Domain

The phase is internal-tooling-only (no network surface, no auth, no secrets), so most ASVS categories don't apply. Two categories do:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes (mild) | `mapRecord(record)` should defensively handle `record == null` (return empty `out` or throw with categorical message). Current modules use `data || {}` and `Array.isArray(data.tags) ? data.tags : []` — already defensive. Tests should include a null-record fixture. |
| V14.2 Dependency Management | yes | Empty `dependencies` and `devDependencies` enforced by Python grep gate (D-10-16). This is the "supply-chain footprint unjustified" rationale from REQUIREMENTS.md "Out of Scope" table — explicit dep-creep prevention. |
| V2/V3/V4/V6 (Auth/Session/Access/Crypto) | no | Make.com modules are pure transforms — no auth, no sessions, no crypto. |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain attack via transitive npm dep | Tampering | Empty `dependencies` + `devDependencies`; `package-lock.json` not generated (no `npm install` run); CI gate fails the build if either becomes non-empty. |
| PII leak via test fixture commit | Information Disclosure | T-PII-01 synthetic-only fixture rule; existing PII grep gates extend to `make-scripts/tests/fixtures/`. |
| Accidental global write breaking Make.com sandbox | Tampering | globalThis snapshot test (D-10-11..D-10-13) — diff before/after `mapRecord(fixture)` must be `[]`. |
| `Reomoto` typo silently misclassifying users in production | Tampering (data quality) | RED-before-GREEN test commit trail (D-10-10) makes the bug-then-fix visible in `git log`; future regressions blocked by `cosmetic-01.test.js`. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Existing GH Actions CI workflow file exists somewhere in the repo and just wasn't surfaced by my `find .github` (or the user's CI is configured externally). D-10-17 says "added to the **existing** CI workflow." | Environment Availability | If no workflow exists, plan needs to create one (different task shape). Plan-phase should run `find .github -type f` (or check root) before drafting D-10-17 task. |
| A2 | Make.com IIFE sandbox honors `"use strict";` at file top. CONTEXT.md notes this as a "carried flag" requiring empirical verification. | Pattern 1 | If strict mode is rejected by Make.com's eval context, `"use strict";` would need to move inside `mapRecord(record)` only (function-level strict) — still satisfies D-10-03 in spirit. Mitigation: live test post-merge as part of D-10-05 byte-paste verification. |
| A3 | Make.com IIFE sandbox treats `module` as undefined (so `typeof module !== "undefined"` returns false). If Make.com's wrapper exposes a CommonJS-like `module` object, the export footer would fire in production and could cause unexpected behavior. | Pattern 1 / D-10-02 | Mitigation: live test post-merge — if `module` IS defined in Make.com, the right side `module.exports = { mapRecord }` is harmless (a property assignment to an object Make.com discards). The risk is purely conceptual cleanliness, not behavioral. |
| A4 | `output =` at top level (no `var`/`let`/`const`) creates a global binding in Make.com's IIFE that becomes the module's return value. This is established Make.com convention but not officially documented in this repo's notes. | Pattern 1 | Mitigation: current modules use this pattern (`return out;` and `return output;` at end of script body) and v1.1 verification confirmed correct production behavior. The footer's `output = mapRecord(...)` line preserves the same idiom. |
| A5 | The `Reomoto` typo at line 157 actually flows through to a user-visible field. Verified: `calculateContextProfile` returns the value to caller (line 253-260 invocation), assigned to `out.context_profile` (line 276), and pushed to `tags` (line 281). So `out.context_profile === "Remoto"` is the correct test surface. | Phase Requirements | If wrong, test would pass for a different reason — but I traced the dataflow line-by-line, so confidence is HIGH. |
| A6 | Removing `let profile = "profile_base";` (line 217) and replacing with bare `let profile;` causes no behavioral change because every code path reassigns. Verified by branch enumeration: `if (data.has_red_flags)` covers one branch; `else { if/else if/else }` over `score_level` covers all three classifyTotalScore returns ("severo" / "moderado" / fallthrough → "low_complexity"). `classifyTotalScore` always returns a valid level. So `profile` is always reassigned. | Phase Requirements | If `classifyTotalScore` ever returned `"unknown"` (line 98 fallthrough), the `else` chain would fall to `low_complexity`. Branch is covered. Confidence: HIGH. |
| A7 | `tests/test_readme_help_alignment.py` does NOT currently assert section count, only section presence. Adding a subsection under `## Development` is safe. | Pitfall 5 | If a count assertion is added later (or another drift test exists), this could regress. Mitigation: keep README addition as paragraph or `### subsection` only — never add a new top-level `## Heading`. |
| A8 | The `quizify-mapping.js` Make.com input adapter (`Array.isArray(raw) ? raw[0] : raw`) is correct to keep INSIDE the footer's `typeof input` guard, not inside `mapRecord`. Rationale: `mapRecord(record)` should receive an already-unwrapped record so tests can pass one synthetic JSON object directly. | Code Examples / Example 2 | If user prefers `mapRecord` to accept either array or object, that's a Claude-discretion call; default is "caller unwraps." Plan-phase can clarify. |
| A9 | D-10-09's "every assertion has an inline citation comment" extends to negative assertions (e.g., the regression check that `"Reomoto"` does not appear in fixtures). Default reading: yes. | Code Examples | Low risk — adding citation comments costs nothing. |

**Summary:** 9 assumptions logged. Highest-impact assumptions (A1, A2, A3) are about external systems (GH Actions workflow location, Make.com sandbox semantics) that the plan-phase or execution-phase can resolve cheaply via direct verification.

## Open Questions

1. **Where is the existing GitHub Actions CI workflow file?**
   - What we know: `find .github -type f` returned empty in current working tree. Phase 9 documentation references "5/5 CI grep gates pass" implying CI runs.
   - What's unclear: Workflow file path; whether it's tracked in git.
   - Recommendation: Plan-phase runs `gh api repos/<owner>/<repo>/actions/workflows` or `git ls-files .github/` to locate. If genuinely no CI file exists, Phase 10 creates one.

2. **What's the Make.com IIFE sandbox's exact behavior under `"use strict";`?**
   - What we know: CONTEXT.md flags this as a "carried flag" (STATE.md "research-phase flags" section).
   - What's unclear: Whether Make.com's `eval`/`new Function` wrapper honors directive-prologue strict mode.
   - Recommendation: Empirical post-merge verification per D-10-05 (paste in, run inline-JSON CONVENTIONS.md fixture). If strict mode breaks Make.com, fall back to function-level strict (`function mapRecord(record) { "use strict"; ... }`) — D-10-03 still satisfied semantically.

3. **Should the cosmetic-02 test sweep all fixtures or just one?**
   - What we know: D-10-12 says globalThis test sweeps full fixture set; D-10-09 says assertions cite specific spec lines.
   - What's unclear: cosmetic-02 ("`profile_base` does not appear in `mapRecord` output for any fixture") implies a sweep.
   - Recommendation: Sweep all `score-calculations` fixtures with one `for` loop; cite ROADMAP success criterion #1 in the comment. Default = exhaustive sweep.

4. **Does the empty-deps gate need a `devDependencies` allowlist for the future?**
   - Current state: D-10-15 says strict empty `{}`. Future-proofing might want `devDependencies` allowlist (e.g., type definitions).
   - Recommendation: Stay strict per D-10-15. If future need arises, that's a v1.3+ phase decision (deferred bucket already lists eslint/prettier as v1.3+ candidates).

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/nodejs_latest-v22_x_api` — `node:test` runner CLI, isolation defaults, `describe`/`it`/`before`/`after` hooks, `--test-concurrency` semantics. [Fetched 2026-05-05]
- Empirical `node --version` (v24.14.1) and `node -e 'require("./score-calculations.js")'` showing `ReferenceError: input is not defined` at line 170. [VERIFIED 2026-05-05]
- Empirical `grep "^## "` of `quizify-csv-to-json-webhook/README.md` showing exactly 10 top-level sections matching D-11 lock. [VERIFIED 2026-05-05]
- Empirical `grep "tool.pytest\|norecursedirs" pyproject.toml` showing no existing config — fresh section creation. [VERIFIED 2026-05-05]
- Read of `score-calculations.js` lines 152-164 (Reomoto typo) and 217-233 (dead init + reassignment). [VERIFIED 2026-05-05]
- Read of `tests/test_security_grep_gates.py` for grep-gate idiom (Pattern 4 source). [VERIFIED 2026-05-05]
- Read of `tests/test_readme_help_alignment.py` confirming it asserts section presence (not count). [VERIFIED 2026-05-05]

### Secondary (MEDIUM confidence)
- nodejs.org/docs/latest-v22.x/api/test.html — `node:test` API surface (read via Context7).
- nodejs.org/docs/latest-v22.x/api/cli.html — `--test-concurrency`, `--experimental-test-isolation` semantics (read via Context7).
- github.com/actions/setup-node — v4 is current major; `cache: 'npm'` requires lockfile (Pitfall 4).

### Tertiary (LOW confidence)
- Make.com IIFE sandbox semantics under `"use strict";` and `module` global handling — these are inferred from existing module behavior and CONVENTIONS.md, not from official Make.com docs (which are sparse on Code module internals). Flagged in Assumptions Log A2/A3 for empirical post-merge verification.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `node:test` is stdlib, no external deps, version-stable.
- Architecture (dual-export footer + mapRecord extraction): HIGH for Node side (verified empirically); MEDIUM for Make.com side (assumes IIFE behavior — flagged A2/A3).
- Pitfalls: HIGH — most are derived from existing v1.1 patterns (grep gates, README drift) or empirically verified Node behavior.
- CI wiring: MEDIUM — Open Question #1 (workflow file location) needs resolution at plan time.

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (30 days — `node:test` is stable; only watch item is CI workflow file location).

---

*Phase: 10-make-com-hygiene-node-test-harness*
*Research complete — ready for planning.*
