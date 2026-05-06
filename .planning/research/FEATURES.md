# Feature Research

**Domain:** CLI utility — CSV→JSON converter with HTTP delivery, streaming output, and a tiny co-owned JS module set
**Researched:** 2026-05-05
**Confidence:** HIGH (well-trodden CLI conventions; sources verified for HTTPie/curl, jq/NDJSON, and `node:test`)
**Scope:** v1.2 features only — AUTO-01 (HTTP POST), STREAM-01 (NDJSON streaming), MAKE-COSMETIC-01/02 (typo + dead code), MAKE-TEST-01 (Node test harness)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Per-feature minimums for a v1.2 release that does not "feel half-shipped."

#### AUTO-01 — HTTP POST delivery mode

| Capability | Why Expected | Complexity | Notes / Existing-feature dependency |
|---|---|---|---|
| `--post-url URL` (or `--webhook-url`) | Primary trigger; activates POST mode | S | Must be mutually compatible with `-o PATH` (write + send) and `--dry-run` (skip send). Depends on **VALI-01** — refuse to send unless schema-valid. |
| Default `Content-Type: application/json` for array payload | curl/HTTPie/`fetch` all assume this for JSON bodies | S | Switch to `application/x-ndjson` automatically when STREAM-01 mode is active (per NDJSON.com tools guide). |
| `--header "Key: Value"` (repeatable) | Universal curl/HTTPie convention | S | argparse `action="append"`. Validate `Key: Value` shape; reject CRLF (header injection). |
| `--timeout SECONDS` | curl `--max-time` / HTTPie `--timeout` (default 30s) is the de-facto baseline | S | Use `urllib.request.urlopen(req, timeout=...)`; D-13 stdlib-preserved. |
| Non-2xx → non-zero exit | Operators chain CLIs in shell; silent failure is a footgun | S | New exit code `3` (HTTP failure) — keeps `1` semantics (input/layout) clean. |
| PII-safe failure stderr | T-PII-01 carry-forward (status code + categorical reason only; never request/response body bytes) | S | Locked template style mirroring D-06-19. |
| Auth via `--header "Authorization: Bearer ..."` | curl/HTTPie idiom; no separate `--auth` flag needed in MVP | S | Avoid building a credential surface in v1.2; let operators wire bearer/HMAC via `--header`. |

**Existing-feature dependencies:**

- **AUTO-01 strictly depends on VALI-01** (`--validate` schema gate). Egress only after `_run_schema_validation` returns clean. Failed validation → no POST attempt → exit 1 (validation), not 3 (HTTP).
- **AUTO-01 must coexist with `-o`/`--output`:** writing to disk AND posting in one invocation is a common operator workflow (audit trail + delivery).
- **AUTO-01 must short-circuit on `--dry-run`:** dry-run is "describe layout, no I/O of any kind"; HTTP POST is I/O. Stderr should announce the URL it *would* have hit (host-only or scheme+host, never query string with creds).

#### STREAM-01 — NDJSON / streaming output

| Capability | Why Expected | Complexity | Notes / Existing-feature dependency |
|---|---|---|---|
| `--ndjson` flag | Standard name across the ecosystem; `jq -c` emits NDJSON; "JSON Lines" / "JSONL" / "NDJSON" / "LDJSON" are interchangeable per Wikipedia "JSON streaming" and NDJSON FAQ | M | Mutually exclusive with default array emission for the same output target. |
| One JSON object per line, no array wrapper, LF terminator | NDJSON spec | S | `json.dumps(row, ensure_ascii=False) + "\n"` per row; flush per row. |
| Compose with `-o PATH` | Writing 50k rows to stdout is hostile; file output is normal | S | Open in text mode UTF-8; stream rows as built rather than building full list. |
| Compose with `--post-url` | Stream the POST body chunked OR send-per-row — pick one | M | **Recommend send-per-row** for v1.2: simpler, retry-per-row is cleaner, matches typical webhook semantics. `Content-Type: application/x-ndjson` only if the receiver is known to accept it (defer; out of scope). |
| Memory-bounded | The whole point — never materialize 50k rows in memory | M | Refactor `build_payload` to a generator; serialize as we go. |

**Existing-feature dependencies:**

- **STREAM-01 must compose with VALI-01:** validate per-row (not whole-array) when streaming, so malformed row N is caught without buffering rows 0..N-1. Schema is already per-row-shaped.
- **STREAM-01 inverts the relationship with AUTO-01:** array mode = one POST with full body; NDJSON mode = either one chunked POST or N POSTs. v1.2 ships array+single-POST and NDJSON+file-only as the supported matrix; NDJSON+POST flagged as "future" to keep complexity bounded.
- **STREAM-01 preserves D-05 key order** per row (no change to row shape).

#### MAKE-COSMETIC-01 / MAKE-COSMETIC-02 — JS hygiene

| Capability | Why Expected | Complexity | Notes / Existing-feature dependency |
|---|---|---|---|
| Fix `Reomoto` → `Remoto` typo at `score-calculations.js:157` | String comparisons are case- and spelling-sensitive (same class of bug as MAKE-FIX-01 `peri_menu`) | XS | Verify the typo isn't load-bearing (i.e., upstream Quizify cell value isn't *also* `Reomoto`). Read the surrounding `if`/`switch` and grep `quizify-submissions.csv` for `Reomoto` and `Remoto` before touching. |
| Remove dead `profile = "profile_base"` initializer at `score-calculations.js:217` | Dead code masks intent and survives reviews | XS | Verify no later branch reads `profile` before assignment after removal (i.e., it really is dead, not a default fallback). |

**Existing-feature dependencies:**

- Both ride on **MAKE-FIX-03 / `make-scripts/CONVENTIONS.md`** verification protocol (synthetic inline-JSON fixtures in Make.com test interface — T-PII-01 preserved). No new fixtures needed.

#### MAKE-TEST-01 — Node test harness

| Capability | Why Expected | Complexity | Notes / Existing-feature dependency |
|---|---|---|---|
| `node --test` runner (built-in `node:test`) | Zero-dep, ships with Node ≥18; matches v1.0 stdlib-only ethos for the JS side | S | Per Node.js Test Runner docs and Node.js Learn "Using test runner". No Jest/Vitest/Mocha. |
| `node:assert/strict` | Zero-dep, ships with Node | XS | `assert.deepStrictEqual` for output shape, `assert.strictEqual` for scalars. |
| Synthetic inline-JSON fixtures (no real PII) | T-PII-01 carry-forward; matches `CONVENTIONS.md` MAKE-FIX-01/02/03 verification style | S | Same fixture style already documented for CONTRACT-01. Co-locate as `make-scripts/tests/fixtures/*.json` or inline `const fixture = { ... }`. |
| Test the **IIFE return value** by exposing the mapper as a pure function under test conditions | The current files are Make.com IIFEs that read `record` / `data` from Make's runtime | M | Two viable shapes: (a) wrap the IIFE body in a function that the test imports while the deployed file remains an IIFE (single source via dual-export guard), or (b) keep IIFE as-is and copy the pure logic into a sibling `*.lib.js` exported for tests. **Recommend (a)** — single source of truth; deployed file still pastes into Make.com unchanged. |
| `package.json` with `{"scripts": {"test": "node --test make-scripts/tests"}}` | Standard npm convention | XS | Lives in `quizify-csv-to-json-webhook/make-scripts/package.json` (or repo root if preferred). No `dependencies`, no `devDependencies`. |
| Cover the three already-fixed bugs (regression net) | Prevents MAKE-FIX-01/02 + CONTRACT-01 from silently regressing | M | Specifically: `peri_menu` underscore tag, `activity_profile` non-athlete default, `record["product-recommendation"]` read. |
| Cover the cosmetic fixes (MAKE-COSMETIC-01/02) | "Land tests with the fix" is the standard pattern | S | `Remoto` branch test; "no `profile_base` literal anywhere in module output" assertion. |

**Existing-feature dependencies:**

- **MAKE-TEST-01 lands with MAKE-COSMETIC-01/02** per milestone scoping ("no longer gated on LOC").
- **MAKE-TEST-01 retroactively covers v1.1 fixes** (CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02). This is the regression net the v1.1 retrospective implicitly called for.

---

### Differentiators (Competitive Advantage)

Above-table-stakes capabilities that make this CLI feel polished without bloating scope.

| Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|
| `--retry N` with exponential backoff | curl `--retry 3` is the universal idiom; webhook endpoints flap. | M | Stdlib `time.sleep(2**attempt)`, cap at 3 attempts. Retry only on 5xx + connection errors; never on 4xx. Honor `Retry-After` header if present. |
| `--idempotency-key VALUE` (or auto-generated UUID per invocation) | Webhook receivers commonly de-dup on this header; retrying without it can double-bill. | S | UUID4 default; `--idempotency-key` override for replay scenarios. Inject as `Idempotency-Key: <val>` header. |
| `--post-url-from-env VAR` / `$QUIZIFY_WEBHOOK_URL` env fallback | Mirrors `--quiz-title` / `$QUIZIFY_QUIZ_TITLE` precedence (CLI > env > none). Keeps URLs out of shell history. | S | Fits the existing precedence pattern verbatim. |
| Print response status + content-length to stderr (PII-safe) | Operators want a one-line "POSTed N rows → 202 Accepted, 0 bytes" confirmation | S | Status code + content-length only. Never log response body unless `-v`. Even with `-v`, log only the first 200 chars and only if `Content-Type` is `application/json` or `text/plain`. |
| `--ndjson` works with stdout (not just `-o`) for piping into `jq -c`, `curl --data-binary @-`, etc. | Composability with the broader Unix toolchain | S | Already implied by table-stakes "stream as built." |

---

### Anti-Features (Commonly Requested, Often Problematic)

Things that look like obvious next steps but cost more than they're worth at v1.2.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| Built-in OAuth / OIDC token acquisition | "Real auth" feels mandatory for HTTP delivery | Requires HTTP server callback for code flow, secret storage, refresh-token persistence — explodes scope and breaks D-13 (would pull in `requests-oauthlib` or similar) | `--header "Authorization: Bearer $TOKEN"` lets operators wire any auth scheme via shell; bearer/HMAC/basic all collapse to one mechanism |
| `--retry-on 4xx` or unconditional retry | Maximally aggressive delivery feels safer | Retries 400/401/422 amplify bad payloads and waste rate-limit budget; mask real validation failures | Retry only 5xx + transport errors. Document that 4xx == operator fix, not transport flake |
| Persistent queue / outbox / disk-backed retry across invocations | "What if my laptop crashes mid-send?" | This is a daemon, not a CLI utility. Conflicts with stateless invocation model | Document the `-o file.json + curl --data-binary @file.json` recovery pattern in README |
| Multiple webhook URLs (`--post-url A --post-url B`) | "Send to staging AND production" | Partial-success semantics are a tarpit; what's the exit code if A=200 and B=500? | Document `tee` / two invocations / Make.com router pattern |
| JSON-Streaming RFC 7464 (record separator-prefixed, `0x1E` framed) | Surfaces in spec searches alongside NDJSON | Almost zero ecosystem adoption; no Make.com support; jq doesn't emit it | Stick to NDJSON (line-delimited LF) per Wikipedia "JSON streaming" |
| Custom test framework / Jest / Vitest for `make-scripts/` | Familiarity to JS devs | Pulls in `node_modules/`, lockfile, supply-chain surface — for ~400 LOC of IIFE | `node:test` is built-in, zero-dep, and matches v1.0's stdlib-only ethos |
| Mocking `fetch` / network in JS tests | "Real" integration tests | The IIFEs do no network I/O — they're pure record→record transforms. Mocking is unnecessary | Test the pure transform with synthetic inline fixtures (matches `CONVENTIONS.md` MAKE-FIX verification style) |
| `--post-body-from-file` (read pre-built JSON and POST without converting) | "I just want to use this as a curl wrapper" | Out of scope — this is a CSV→webhook tool, not a generic poster | `curl --data-binary @file.json` exists |
| Streaming validation that emits partial JSON before validation runs | "Don't make me wait for validation on huge files" | Breaks the AUTO-01 invariant ("validate before egress"). Half-validated output corrupts downstream contracts | Per-row validate inline with per-row emit (already proposed under STREAM-01) |

---

## Feature Dependencies

```
v1.0 / v1.1 (shipped)
├── CONV-01..06 (CSV→records)
├── WEB-01..05  (webhook shape, D-05 key order)
├── VALI-01     (--validate, schema gate)
└── make-scripts/ (CONTRACT-01, MAKE-FIX-01..03)

v1.2 (this milestone)

  AUTO-01 (HTTP POST)
      └──requires──> VALI-01 (--validate must pass before egress)
      └──compatible──> -o/--output (write AND send)
      └──short-circuits──> --dry-run (no I/O)
      └──enhanced-by──> --retry, --idempotency-key, --header (Authorization)

  STREAM-01 (NDJSON)
      └──refactors──> build_payload() into a row generator
      └──compatible──> -o/--output (file mode is the supported target)
      └──compatible──> VALI-01 (per-row validation when streaming)
      └──conflicts──> AUTO-01 single-POST mode (NDJSON+POST deferred)

  MAKE-COSMETIC-01/02
      └──verified-by──> make-scripts/CONVENTIONS.md (existing protocol)
      └──lands-with──> MAKE-TEST-01

  MAKE-TEST-01
      └──covers──> CONTRACT-01, MAKE-FIX-01, MAKE-FIX-02 (regression net)
      └──covers──> MAKE-COSMETIC-01/02 (concurrent fixes)
      └──requires──> minor refactor: expose IIFE body as testable pure fn
```

### Dependency Notes

- **AUTO-01 → VALI-01:** Hard dependency. Without `--validate`, AUTO-01 can still POST, but the milestone goal explicitly gates egress on schema validity. Recommend AUTO-01 *implicitly enables* `--validate` (or refuses without it) — operator should not be able to POST unvalidated payloads. Decide as ADR.
- **STREAM-01 ↔ AUTO-01:** Compose-but-not-cross-product. v1.2 ships {array+POST, NDJSON+file, array+file}; defers {NDJSON+POST}.
- **MAKE-TEST-01 ↔ MAKE-COSMETIC-01/02:** Land together — every cosmetic fix gets a test in the same commit, establishing the pattern for future JS work.
- **All v1.2 features preserve D-13** (stdlib-only at runtime): `urllib.request` for POST, `json` for NDJSON, `node:test` + `node:assert` for JS. No new Python or npm runtime deps.
- **All v1.2 features preserve T-PII-01** (PII-safe stderr): HTTP error logging uses status + categorical reason only; per-row validation errors use JSON Pointer paths only; JS test fixtures are synthetic.

---

## MVP Definition

### Launch With (v1.2)

Minimum viable for the milestone — everything below is in scope per `MILESTONES.md` deferred bucket and `PROJECT.md` Current Milestone.

- [ ] **AUTO-01** — `--post-url`, `--header` (repeatable), `--timeout`, gated on `--validate` success, exit code `3` on non-2xx, PII-safe stderr — **MEDIUM** complexity
- [ ] **STREAM-01** — `--ndjson` flag, generator-backed row emission, file output composition, per-row validation — **MEDIUM** complexity
- [ ] **MAKE-COSMETIC-01** — `Reomoto` → `Remoto` (one-line) — **TRIVIAL**
- [ ] **MAKE-COSMETIC-02** — remove dead `profile = "profile_base"` initializer (one-line) — **TRIVIAL**
- [ ] **MAKE-TEST-01** — `node --test`-based harness, synthetic fixtures, regression coverage for v1.1 fixes + v1.2 cosmetic fixes, `package.json` with `test` script — **MEDIUM** complexity (wrapping IIFEs for testability is the non-trivial part)

### Add After Validation (v1.3 candidates)

- [ ] **AUTO-RETRY** — `--retry N` with exponential backoff and `Retry-After` honoring (differentiator; trigger: first reported transport flake against a real webhook)
- [ ] **AUTO-IDEMPOTENCY** — `--idempotency-key` flag + auto-UUID default (trigger: first reported double-delivery)
- [ ] **STREAM-POST** — NDJSON-over-HTTP (chunked or per-row); requires deciding partial-success semantics (trigger: a real CSV >50k rows that needs delivery, not just file output)
- [ ] **`$QUIZIFY_WEBHOOK_URL` env fallback** — mirror `--quiz-title` precedence pattern (trigger: operator request to remove URLs from shell history)

### Future Consideration (post-v1.x)

- [ ] OAuth/OIDC built-in (defer indefinitely — `--header "Authorization: Bearer $TOKEN"` covers it)
- [ ] Persistent retry queue (defer indefinitely — out of model)
- [ ] Multi-URL fan-out (defer indefinitely — composition belongs in shell or Make.com)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| AUTO-01 (POST core: `--post-url`, `--timeout`, `--header`, exit-3-on-non-2xx) | HIGH | MEDIUM | P1 |
| AUTO-01 dependency on `--validate` | HIGH | LOW | P1 |
| STREAM-01 (`--ndjson`, generator refactor, file-mode) | HIGH | MEDIUM | P1 |
| MAKE-COSMETIC-01 (`Reomoto` typo) | MEDIUM (categorical bug class) | TRIVIAL | P1 |
| MAKE-COSMETIC-02 (dead initializer) | LOW (cosmetic) | TRIVIAL | P1 |
| MAKE-TEST-01 (`node:test` harness + regression net) | HIGH (prevents future MAKE-FIX-class bugs) | MEDIUM | P1 |
| `--retry N` exponential backoff | MEDIUM | LOW-MEDIUM | P2 |
| `--idempotency-key` | MEDIUM | LOW | P2 |
| `$QUIZIFY_WEBHOOK_URL` env fallback | LOW-MEDIUM | TRIVIAL | P2 |
| Response status/content-length to stderr (PII-safe) | MEDIUM | LOW | P2 |
| NDJSON+POST composition | LOW (no current >50k delivery use case) | HIGH (partial-success semantics) | P3 |
| OAuth/OIDC built-in | LOW | HIGH | Anti-feature |
| Persistent outbox | LOW | HIGH | Anti-feature |

**Priority key:**
- P1: In scope for v1.2.
- P2: Differentiators — add as roadmap allows; stop-gap with `--header` + shell composition.
- P3: Defer; reassess once a real use case lands.

---

## Competitor / Peer Analysis

The peer set for AUTO-01 + STREAM-01 patterns is (a) generic HTTP CLIs (curl, HTTPie) and (b) data-pipeline CLIs (jq, csvkit). For MAKE-TEST-01 it is the broader Node ecosystem (`node:test` vs Mocha vs Jest vs Vitest).

| Capability | curl | HTTPie | jq | csvkit (`csvjson`) | **Our v1.2 approach** |
|---|---|---|---|---|---|
| HTTP POST flag | `-X POST -d @file` | `http POST URL key=val` | (out of scope) | (out of scope) | `--post-url URL` (subject + verb implied) |
| Timeout | `--max-time SEC` | `--timeout SEC` (default 30) | — | — | `--timeout SEC` (HTTPie naming; default 30) |
| Retry | `--retry N`, `--retry-delay`, `--retry-max-time` | (none built-in) | — | — | Defer to v1.3; document curl-wrapper recovery for v1.2 |
| Custom header | `-H "K: V"` (repeatable) | `K:V` positional | — | — | `--header "K: V"` (repeatable; argparse `append`) |
| Auth | `-u user:pass`, `-H "Authorization: ..."` | `--auth user:pass`, `K:V` | — | — | `--header "Authorization: ..."` only (no dedicated `--auth` in v1.2) |
| NDJSON emission | n/a | n/a | `-c` (compact, line-per-record) | n/a (emits array) | `--ndjson` flag |
| Streaming input | n/a | n/a | streams by default | buffers | Generator-backed; streams by default once `--ndjson` is on |
| Test runner | n/a | n/a | n/a | n/a | `node --test` (built-in `node:test`); zero deps |

**Sources (verified):**

- HTTP flag conventions:
  - HTTPie 3.2.4 docs — https://httpie.io/docs/cli
  - Ubuntu manpage: httpie — https://manpages.ubuntu.com/manpages/focal/man1/http.1.html
  - Essential Curl Options — https://www.ipfly.net/blog/essential-curl-options-master-http-requests/
- NDJSON / JSONL conventions:
  - JSON streaming — Wikipedia — https://en.wikipedia.org/wiki/JSON_streaming
  - JSONL FAQ — https://ndjson.com/faq/
  - JSONL Tools & CLI Guide — https://ndjson.com/tools/
- jq NDJSON behavior (`-c`, default streaming):
  - jq 1.8 Manual — https://jqlang.org/manual/
- Node test runner:
  - Node.js test API — https://nodejs.org/api/test.html
  - Node.js Learn — Using test runner — https://nodejs.org/learn/test-runner/using-test-runner
  - Better Stack — Node.js Test Runner guide — https://betterstack.com/community/guides/testing/nodejs-test-runner/
  - AppSignal — Advanced Node test runner — https://blog.appsignal.com/2024/08/07/advanced-use-cases-of-the-nodejs-native-test-runner.html

---

## Confidence & Open Questions

**HIGH confidence:**
- AUTO-01 flag shape (`--post-url`, `--header`, `--timeout`) — directly mirrors curl/HTTPie conventions.
- STREAM-01 flag name (`--ndjson`) and per-line LF encoding — NDJSON has dominant ecosystem mindshare.
- MAKE-TEST-01 toolchain (`node:test` + `node:assert/strict`) — built-in, zero-dep, ethos-aligned.
- AUTO-01 → VALI-01 hard dependency — explicit in `PROJECT.md` and `MILESTONES.md`.

**MEDIUM confidence (decide in roadmap / ADR):**
- Whether AUTO-01 *implicitly enables* `--validate` or *requires* it as a precondition (operator-facing semantics differ; recommend implicit-enable for ergonomics).
- Whether NDJSON+POST ships in v1.2 or defers to v1.3 (recommend defer — partial-success semantics are a real design tarpit).
- Whether the IIFE testability refactor (MAKE-TEST-01) uses the dual-export guard pattern or a `*.lib.js` sibling (recommend dual-export — single source of truth).

**Open questions for plan phase:**
- New exit code `3` for HTTP failure — confirm no clash with shell conventions (none observed; `2` is argparse usage, `1` is generic, `3` is free).
- Per-row validation in STREAM-01: emit row N before validating row N+1 (true streaming) or buffer-of-1 with lookahead? Recommend straight-through (faster + simpler; row N error means rows 0..N-1 already shipped — document explicitly).
- `make-scripts/package.json` location: in `make-scripts/` or repo root? Recommend `make-scripts/` (co-located with the JS modules; matches `quizify-csv-to-json-webhook/pyproject.toml` co-location pattern).

---
*Feature research for: Quizify CSV→Webhook v1.2 — HTTP delivery, NDJSON streaming, JS hygiene*
*Researched: 2026-05-05*
