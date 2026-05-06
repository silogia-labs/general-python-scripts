---
phase: 10
slug: make-com-hygiene-node-test-harness
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-05
audited: 2026-05-06
audit_notes: |
  All 16 rows green. node --test 9/0; pytest gates 7/7 + 5/5.
  Row 10-03-04 reclassified manual→automated (CI workflow now ships make-scripts-test job).
  Row 10-03-06 path corrected: test_grep_gates.py → test_security_grep_gates.py.
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | `node:test` (Node 20 stdlib) + pytest 7.x (existing) |
| **Config files** | `quizify-csv-to-json-webhook/make-scripts/package.json`, `quizify-csv-to-json-webhook/pyproject.toml` |
| **Quick run command (JS)** | `cd quizify-csv-to-json-webhook/make-scripts && node --test` |
| **Quick run command (Py)** | `cd quizify-csv-to-json-webhook && pytest tests/test_make_scripts_no_deps.py tests/test_readme_help_alignment.py -q` |
| **Full suite command** | `cd quizify-csv-to-json-webhook && pytest -q && cd make-scripts && node --test` |
| **Estimated runtime** | ~3s JS + ~8s Python = ~11s |

---

## Sampling Rate

- **After every task commit:** Run quick command for the touched runtime (JS or Py).
- **After every plan wave:** Run full suite (both runtimes).
- **Before `/gsd-verify-work`:** Full suite green; D-11 README drift test green; v1.1 grep gates green.
- **Max feedback latency:** 15 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | MAKE-TEST-03 | T-PII-01 carry-forward | No PII tokens in fixtures | unit (grep) | `pytest tests/test_make_scripts_no_pii.py -q` | ❌ W0 | ✅ green |
| 10-01-02 | 01 | 1 | MAKE-TEST-01 | — | mapRecord exported, paste-in unchanged | unit | `node --test make-scripts/tests/contract-01.test.js` | ❌ W0 | ✅ green |
| 10-01-03 | 01 | 1 | MAKE-TEST-02 | — | peri_menu underscore drives life_stage | unit | `node --test make-scripts/tests/make-fix-01.test.js` | ❌ W0 | ✅ green |
| 10-01-04 | 01 | 1 | MAKE-TEST-02 | — | activity_profile defaults non_athlete | unit | `node --test make-scripts/tests/make-fix-02.test.js` | ❌ W0 | ✅ green |
| 10-01-05 | 01 | 1 | MAKE-COSMETIC-01 | — | RED: Reomoto fails before fix | unit (RED) | `node --test make-scripts/tests/cosmetic-01.test.js` (expected to fail) | ❌ W0 | ✅ green |
| 10-01-06 | 01 | 1 | MAKE-COSMETIC-02 | — | profile_base absent from output | unit | `node --test make-scripts/tests/cosmetic-02.test.js` | ❌ W0 | ✅ green |
| 10-01-07 | 01 | 1 | MAKE-TEST-01 | — | Reflect.ownKeys diff == [] | unit | `node --test make-scripts/tests/globals.test.js` | ❌ W0 | ✅ green |
| 10-02-01 | 02 | 2 | MAKE-TEST-01 | — | Both modules export mapRecord; "use strict" at top | source | `node --test make-scripts/` | ❌ W0 | ✅ green |
| 10-02-02 | 02 | 2 | MAKE-COSMETIC-01 | — | GREEN: Remoto in source, Reomoto absent | unit | `node --test make-scripts/tests/cosmetic-01.test.js` | ❌ W0 | ✅ green |
| 10-02-03 | 02 | 2 | MAKE-COSMETIC-02 | — | profile_base initializer removed | unit | `node --test make-scripts/tests/cosmetic-02.test.js` | ❌ W0 | ✅ green |
| 10-03-01 | 03 | 2 | MAKE-TEST-03 | — | Empty deps enforced | grep-gate | `pytest tests/test_make_scripts_no_deps.py -q` | ❌ W0 | ✅ green |
| 10-03-02 | 03 | 2 | MAKE-TEST-03 | — | norecursedirs covers make-scripts/node_modules | config | `pytest --collect-only quizify-csv-to-json-webhook/make-scripts 2>&1 \| grep -c "collected 0 items"` | ❌ W0 | ✅ green |
| 10-03-03 | 03 | 2 | MAKE-TEST-03 | — | .gitignore blocks node_modules/coverage | grep | `grep -E "^node_modules/?\|^coverage/?" make-scripts/.gitignore` | ❌ W0 | ✅ green |
| 10-03-04 | 03 | 2 | MAKE-TEST-01 | — | GH Actions runs node --test | CI | CI: `.github/workflows/ci.yml` `make-scripts-test` job (auto on push/PR) | ❌ W0 | ✅ green |
| 10-03-05 | 03 | 2 | MAKE-TEST-03 | — | README ten-section drift test green | regression | `pytest tests/test_readme_help_alignment.py -q` | ✅ | ✅ green |
| 10-03-06 | 03 | 2 | (carry-forward) | T-PII-01 | v1.1 grep gates remain green | regression | `pytest tests/test_security_grep_gates.py -q` | ✅ | ✅ green |

*Status: ✅ green · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `quizify-csv-to-json-webhook/make-scripts/package.json` — private package, empty deps, test script
- [ ] `quizify-csv-to-json-webhook/make-scripts/.gitignore` — node_modules/, coverage/
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/fixtures/quizify-mapping/` — synthetic JSON fixtures
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/fixtures/score-calculations/` — synthetic JSON fixtures
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/contract-01.test.js` — RED stub
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/make-fix-01.test.js` — RED stub
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/make-fix-02.test.js` — RED stub
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/cosmetic-01.test.js` — RED stub (intentionally fails until cosmetic fix)
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/cosmetic-02.test.js` — RED stub
- [ ] `quizify-csv-to-json-webhook/make-scripts/tests/globals.test.js` — Reflect.ownKeys diff
- [ ] `quizify-csv-to-json-webhook/tests/test_make_scripts_no_deps.py` — Python grep-gate
- [ ] `quizify-csv-to-json-webhook/tests/test_make_scripts_no_pii.py` — fixtures PII grep-gate
- [ ] `quizify-csv-to-json-webhook/pyproject.toml` — fresh `[tool.pytest.ini_options]` with `norecursedirs = ["make-scripts", "node_modules"]`
- [ ] `.github/workflows/<existing>.yml` — `make-scripts-test` job (path resolved at plan-time per RESEARCH.md Open Question #1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Make.com paste-in unchanged | MAKE-TEST-01 (D-10-05) | Live Make.com sandbox not scriptable from CI | After merge, paste each module into Make.com test interface; run inline-JSON fixtures from CONVENTIONS.md §CONTRACT-01 / §MAKE-FIX-01 / §MAKE-FIX-02; confirm outputs match. |
| `"use strict";` honored by Make.com IIFE | MAKE-TEST-01 (RESEARCH A2) | Sandbox semantics undocumented | Paste a module into Make.com test interface; confirm scenario runs without runtime errors. |
| `typeof module === "undefined"` in IIFE | MAKE-TEST-01 (RESEARCH A3) | Sandbox semantics undocumented | Same paste-in test verifies the dual-export footer is inert in Make.com. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags (raw `node --test`, no `--watch`)
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
