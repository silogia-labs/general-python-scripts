# Phase 10: Make.com Hygiene & Node Test Harness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 10-make-com-hygiene-node-test-harness
**Areas discussed:** mapRecord extraction shape, Test layout & fixtures, globalThis snapshot strategy, CI gates & runner wiring

---

## mapRecord Extraction Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Function wrap + IIFE invoke | Wrap top-level logic in `mapRecord(record)`; dual `typeof input` and `typeof module` guards at footer. | ✓ |
| Guard top-level with typeof input | Wrap existing top-level in `if (typeof input !== 'undefined')`; thin mapRecord wrapper. | |
| Top-level try/catch + lazy export | Try-read input.data; on ReferenceError no-op; lazy mapRecord re-runs body. | |

**User's choice:** Function wrap + IIFE invoke (preview-locked code shape).
**Notes:** Pure function; Make.com paste-in unchanged; both `input` and `module` guards required for cross-environment safety.

---

| Option | Description | Selected |
|--------|-------------|----------|
| mapRecord only | Test through public surface; helpers stay private. | ✓ |
| Export named helpers too | `module.exports = { mapRecord, scorePainIntensity, hasTag, ... }`. | |
| mapRecord + SCORE_RULES constants | Function plus tunable constants. | |

**User's choice:** mapRecord only.
**Notes:** Refactors of helpers must not break tests; matches Make.com integration boundary.

---

## Test Layout & Fixtures

| Option | Description | Selected |
|--------|-------------|----------|
| Per-requirement files | `tests/contract-01.test.js`, `make-fix-01.test.js`, etc.; one file per ROADMAP requirement. | ✓ |
| Per-module files | `tests/quizify-mapping.test.js` + `tests/score-calculations.test.js`. | |
| Flat by-concern | `tests/cosmetic.test.js`, `tests/contract.test.js`, etc. | |

**User's choice:** Per-requirement files (preview-locked tree).
**Notes:** Maintains 1:1 ROADMAP traceability; failures self-locate to a requirement.

---

| Option | Description | Selected |
|--------|-------------|----------|
| `tests/fixtures/*.json` files | Standalone JSON files mirroring CONVENTIONS.md inline-JSON paste-in format. | ✓ |
| Inline literals | `const fixture = {...}` inside each .test.js. | |
| Single fixtures.js module | Centralized `tests/fixtures.js` with named exports. | |

**User's choice:** `tests/fixtures/<module>/*.json` files.
**Notes:** Fixtures double as Make.com test interface payloads; single source of truth.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Inline comment per assertion | `// CONVENTIONS.md:18 — peri_menu underscore` above each assert. | ✓ |
| Citation in test name | `test("MAKE-FIX-01 [CONVENTIONS.md:18] ...", ...)`. | |
| Helper that takes citation arg | `citedAssert('CONVENTIONS.md:18', () => assert.equal(...))`. | |

**User's choice:** Inline comment per assertion (preview-locked).
**Notes:** Grep-friendly; reviewer can jump from assertion to spec line.

---

## globalThis Snapshot Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Exact diff, fail on any new key | `Reflect.ownKeys(globalThis)` before/after; assert leaked == []. | ✓ |
| Allowlist of accepted leaks | Maintain allowlist of known-safe leaks. | |
| `Object.keys` only (string keys) | Skip symbol-keyed state. | |

**User's choice:** Exact diff with `Reflect.ownKeys` (preview-locked).
**Notes:** No allowlist — strictest possible enforcement; symbol keys included.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Both modules × representative fixture set | Iterate every fixture under `tests/fixtures/<module>/`. | ✓ |
| One smoke fixture per module | Single happy-path each. | |
| Empty + smoke + edge fixtures | Curated trio per module. | |

**User's choice:** Both modules × representative fixture set.
**Notes:** Catches branch-conditional global writes.

---

## CI Gates & Runner Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Python grep-gate test | `tests/test_make_scripts_no_deps.py` reads package.json; asserts deps == {}. | ✓ |
| GitHub Action only | New `.github/workflows/make-scripts.yml` greps package.json. | |
| Both Python gate + GH Action | Defense in depth. | |

**User's choice:** Python grep-gate test (preview-locked code).
**Notes:** Extends Phase 9 grep-gate pattern; runs in existing pytest CI; no Node required for the gate itself.

---

| Option | Description | Selected |
|--------|-------------|----------|
| npm script + GH Action job | `package.json` test script + new CI job running `node --test`. | ✓ |
| Direct node --test, no CI now | Document `node --test make-scripts/` in README; defer CI wiring. | |
| Direct node --test + CI now, no npm script | Skip npm script; add GH Action; raw command in README. | |

**User's choice:** npm script + GH Action job (preview-locked YAML + JSON).
**Notes:** Add to existing CI workflow (not a new file); Node 20 LTS; runs in parallel with pytest job.

---

## Claude's Discretion

- Exact wording of README addition for `make-scripts/` testing (must respect D-11 ten-section drift test).
- Exact `node-version` minor (default `"20"`; `"22"` LTS acceptable).
- Cosmetic-01 assertion phrasing (positive vs negative); default = positive + global negative-regression check.
- Number of fixtures per module (minimum: one happy-path + one edge per asserted branch).

## Deferred Ideas

- `score_total` (JS-recomputed) vs `score-value` (Python pass-through) reconciliation audit → v1.3 candidate.
- eslint / prettier on `make-scripts/` (blocked by empty-deps lock) → v1.3+ candidate.
- JS coverage tool (c8, nyc) (blocked by empty-deps lock) → v1.3+ candidate.
- `tap`/`junit` reporter for CI → v1.3+ candidate.
