# Pitfalls Research — v1.2 Delivery & Make.com Hygiene

**Domain:** stdlib-Python CLI adding HTTP egress + NDJSON streaming + Node test harness for co-owned IIFE JS
**Researched:** 2026-05-05
**Confidence:** HIGH (urllib + NDJSON pitfalls are well-documented stdlib behaviors; Node-harness pitfalls verified against the IIFE module shape in `make-scripts/`); MEDIUM where Make.com sandbox specifics are inferred.

This file enumerates pitfalls **specific to ADDING** AUTO-01, STREAM-01, MAKE-TEST-01 (with MAKE-COSMETIC-01/02) to a codebase that already enforces D-13 stdlib-only-at-runtime, T-PII-01 PII-safe stderr, D-05 locked top-level key order, D-11 README ten-section lock, and the VALI-01 `--validate` gate. Generic "use HTTPS" advice is omitted.

---

## Critical Pitfalls

### Pitfall 1: `urllib.request.urlopen()` defaults to NO timeout

**What goes wrong:**
A misbehaving Make.com webhook (TCP-accept-but-never-respond, slow-loris, proxy hang) blocks the CLI forever. Operators see no output, no error, no exit; CI pipelines wedge until the runner kills them.

**Why it happens:**
`urlopen()` uses `socket._GLOBAL_DEFAULT_TIMEOUT`, which is `None` (= block forever) unless explicitly overridden. Tutorials and stackoverflow snippets almost universally omit `timeout=`. Developers expect `requests`-like reasonable defaults; stdlib has none.

**How to avoid:**
- Pass an explicit `timeout=` (seconds, float) on every `urlopen()` call. Recommend a documented default (e.g. 10s) configurable via `--http-timeout` flag.
- Add a unit test that monkeypatches `urlopen` and asserts the `timeout` kwarg was passed (and is finite).
- CI grep gate: `urlopen(` without `timeout=` on the same logical call fails the build.

**Warning signs:**
- Integration test against a deliberately-stalled local server hangs past N seconds.
- Operators report "the script just sits there" with no stderr output.

**Phase to address:** AUTO-01 implementation phase. Set the timeout default + flag in the same plan that introduces `--post`.

---

### Pitfall 2: HTTP error response bodies leaked into stderr (T-PII-01 violation)

**What goes wrong:**
The naive error path logs `e.read().decode()` from `urllib.error.HTTPError`. Make.com's webhook on validation/parse errors echoes back snippets of the submitted payload (or at least the offending field) — meaning email addresses, phone numbers, and free-text answers land in stderr, breaking T-PII-01's negative-substring contract.

**Why it happens:**
- `HTTPError` instances are file-like — `print(e)` plus reading `e` "to debug" is the canonical urllib snippet.
- Webhook services routinely include request-context in 4xx bodies ("invalid field 'email' value 'alice@…'").
- T-PII-01 was written before any HTTP surface existed; nobody has added "HTTP response body" to the negative-substring assertion list.

**How to avoid:**
- **Categorical-only logging.** Log: HTTP status code, status reason phrase, response Content-Type, response body byte length, and a fixed error-class label (`http_4xx_client`, `http_5xx_server`, `network_timeout`, `dns_failure`, `tls_failure`). Never log body bytes, never log request URL query string, never log request headers (may contain auth).
- **Locked PII-safe error template** — extend the existing D-06-19/D-06-20 lock pattern: e.g. `"http POST failed: status=%d reason=%s class=%s body_bytes=%d"`. Treat as immutable once shipped.
- **Negative-substring tests** mirroring the existing T-PII-01 pattern: feed a fake `HTTPError` whose body contains email/phone/free-text fixtures from `quizify-submissions.csv`, capture stderr, assert none of those substrings appear. Add a `TestHTTPErrorPIIsafe` class parallel to `TestValidationFailurePIIsafe`.
- **Verbose mode does NOT bypass this.** `-v`/`--verbose` may add request count, retry attempt, elapsed ms — never body bytes. Document explicitly in README.

**Warning signs:**
- A new log line that interpolates `e.read()`, `e.fp`, `response.read()`, or `response.text` anywhere in the POST path.
- A test that captures stderr and asserts a *positive* substring from a real response — that test is encoding a leak.

**Phase to address:** AUTO-01 — PII-safe error formatter must land in the same plan as the request issuer, not deferred.

---

### Pitfall 3: VALI-01 ↔ AUTO-01 race — POST issued before/instead of validation

**What goes wrong:**
Two failure modes:
(a) `--post` works without `--validate`, allowing schema-invalid payloads to hit the webhook (defeats the AUTO-01 gating premise from the milestone goal).
(b) Validation and POST are wired in the wrong order — POST starts before `_run_schema_validation` returns, or validation runs but its non-zero exit doesn't short-circuit the POST.

**Why it happens:**
- `--validate` was originally an *exit-code* gate (return 1, end of program). Re-using it as a *control-flow* gate inside the same invocation is a different shape.
- argparse mutual-requirement enforcement is easy to forget; argparse has no native "requires" relation.
- When refactoring main flow to `validate → emit → post`, a developer may keep the old `sys.exit(1)` inside the validator and skip moving the POST call below it — fragile integration.

**How to avoid:**
- argparse post-parse check: `if args.post and not args.validate: parser.error("--post requires --validate")`. Add a CLI test asserting this exact error.
- Single linear control-flow function: `payload = build(...); validate_or_exit(payload, args); if args.post: post_or_exit(payload, args)`. No callbacks, no threads.
- Integration test: invoke the CLI with `--post` against a deliberately malformed CSV that fails schema; assert (1) exit code non-zero, (2) the mock HTTP server received zero requests. The "zero requests" assertion is the load-bearing one.
- Symmetric test: `--post` against the 42-row sample with a mock server; assert exactly one request was issued.

**Warning signs:**
- Test for "POST succeeds" exists but no test for "POST is suppressed on schema failure."
- `--post` accepted standalone in `--help` without mentioning `--validate`.

**Phase to address:** AUTO-01. The mock-HTTP-server harness must land in the same plan; "zero requests on invalid payload" is a phase-exit criterion.

---

### Pitfall 4: SSL verification accidentally disabled or weakened

**What goes wrong:**
A developer hits a corporate-proxy or self-signed-cert issue while testing against a staging webhook, googles the error, and pastes `ssl._create_unverified_context()` or `context.check_hostname = False; context.verify_mode = ssl.CERT_NONE` into the POST helper. It ships that way. Production traffic (PII!) is now MITM-vulnerable.

**Why it happens:**
- urllib's TLS error messages are cryptic ("CERTIFICATE_VERIFY_FAILED"); the fastest path past them is to disable verification.
- No big red flag in stdlib for "you just turned off the security you were trying to add."
- Easy to assume "Make.com handles the TLS, we're fine" and not realize the *client side* is the one being downgraded.

**How to avoid:**
- Use `ssl.create_default_context()` (or just let `urlopen` default) — never `_create_unverified_context`.
- Reject `http://` URLs at argparse-parse time with a hard error: `--post-url` must start with `https://`. Add a CLI test.
- CI grep gate: presence of `CERT_NONE`, `_create_unverified_context`, `check_hostname = False`, or `verify=False` anywhere in the file fails the build.

**Warning signs:**
- Commit message or PR description containing "fix SSL", "ignore cert", "self-signed".
- A new `import ssl` line whose only purpose is constructing a context.

**Phase to address:** AUTO-01.

---

### Pitfall 5: urllib follows redirects silently — including HTTPS→HTTP downgrades and cross-host

**What goes wrong:**
A misconfigured webhook returns 301/302 to a different host (or worse, to an `http://` URL). `urllib.request.HTTPRedirectHandler` follows it transparently, the operator sees a "200 OK" from a URL they didn't ask to talk to, and PII has been delivered to the wrong endpoint.

**Why it happens:**
Default `OpenerDirector` includes `HTTPRedirectHandler`. There's no audit log of the redirect chain; `response.geturl()` returns the final URL but nobody calls it.

**How to avoid:**
- Build a custom opener with a redirect handler that refuses all redirects (raises) — Make.com webhooks should not redirect in normal operation; refusing is safer than allowing same-host hops.
- Always assert `response.geturl() == request_url` after the call; log a categorical `http_unexpected_redirect` (never the redirect target — could itself contain PII tokens) and exit non-zero if mismatched.
- Test with a local mock server that returns 302 to a different host; assert the CLI refuses and exits non-zero.

**Warning signs:**
- `response.status == 200` against a webhook that operators think is dead.
- Latency higher than expected for a simple POST (extra round-trip).

**Phase to address:** AUTO-01.

---

### Pitfall 6: NDJSON trailing-newline ambiguity breaks downstream parsers

**What goes wrong:**
Some emitters write `record\n` per line (correct); some emit `\n`-separated (last record has no trailing newline, breaks `wc -l`-style consumers); some write CRLF on Windows; some emit a final blank line that downstream `json.loads` chokes on.

**Why it happens:**
- `print()` adds `\n` but flushes lazily; `file.write(json.dumps(obj))` forgets the newline; `json.dump(obj, file); file.write("\n")` is the only correct stdlib pattern and is non-obvious.
- `json.dumps` defaults can emit non-ASCII as `\uXXXX` escapes — fine for NDJSON validity but surprising in diffs against the v1.0 golden fixture.
- `open(path, "w")` on Windows turns `\n` into `\r\n` (universal newline translation); NDJSON consumers that split on `\n` see trailing `\r`.

**How to avoid:**
- Lock the emit pattern: `out.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")`. Document in code comment + README.
- Open files with `open(path, "w", encoding="utf-8", newline="\n")` to disable newline translation.
- Test asserts: file ends with exactly one `\n`; no `\r` byte appears anywhere; `len(file.read().split(b"\n")) == row_count + 1`.
- Round-trip test: read NDJSON back via `for line in f: json.loads(line)`; record count and structural equality with the JSON-array emit path.

**Warning signs:**
- Downstream consumer reports "extra blank record" or "last record truncated."
- File size differs by exactly N bytes from expected (CRLF translation indicator).

**Phase to address:** STREAM-01.

---

### Pitfall 7: Streaming output is not atomic — partial files on crash get consumed as "complete"

**What goes wrong:**
The CLI streams 50k rows to `output.ndjson`. On row 37,412 a CSV decode error or a SIGINT aborts the run. The file on disk has 37,412 well-formed NDJSON lines; downstream automation sees the file, processes it, and silently drops 12.5k respondents.

**Why it happens:**
- Streaming's whole point is "don't buffer the whole thing in RAM," which means the file is observable mid-write.
- Default `open(path, "w")` truncates immediately, then writes incrementally — there's no "complete" signal.
- Unlike the v1.0/v1.1 emit-once-at-end path, no natural moment where "file written" == "all rows succeeded."

**How to avoid:**
- Write to `output.ndjson.tmp` (or `.partial`); on success, `os.replace(tmp, final)` (atomic on POSIX and Windows). On any exception, leave the `.tmp` in place and exit non-zero.
- Document the temp-file extension in README so operators / watchers can ignore it.
- Test: SIGINT mid-stream, assert final path does not exist and `.tmp` does.

**Warning signs:**
- Downstream pipelines occasionally process truncated record counts; correlation with CSV errors or operator Ctrl-C.

**Phase to address:** STREAM-01 — atomic-rename pattern in the same plan as the streaming writer.

---

### Pitfall 8: Per-row validation vs whole-stream validation semantic split

**What goes wrong:**
VALI-01 was designed to validate the *whole array* shape (`type: "array"`, `items: {...}`). When streaming, the array boundary disappears — there's no "the document" anymore, just a sequence of items. Two failure modes:
(a) Validator run on each row using the array schema → every row fails with `"is not of type 'array'"`.
(b) Validator run only on the first/last row, or not at all in stream mode → the AUTO-01 gate is bypassed for large inputs.

**Why it happens:**
The v1.1 schema is rooted at `array`. Switching emit modes silently switches the schema target; the path through `_run_schema_validation` doesn't know which mode is active.

**How to avoid:**
- Refactor: extract the per-item subschema (`schema["items"]`) and validate **per row** in stream mode. Whole-array validation continues for non-stream mode (byte-identical to v1.1).
- Compiled validator built once per invocation (preserve VALI-01's perf shape — fastjsonschema compile is the expensive part).
- Test: stream-mode + `--validate` against a malformed row in position 50 of a 100-row CSV; assert exit non-zero, JSON Pointer references the row index, atomic-rename did not happen, no POST issued (if `--post` set).
- Re-run byte-identity regression: stream the 42-row sample, then `jq -s . output.ndjson` should equal the v1.1 golden fixture.

**Warning signs:**
- `--validate` in stream mode either always passes or always fails — neither result sensitive to input.
- Per-row-validation tests don't include a "good rows before, bad row in middle, good rows after" fixture.

**Phase to address:** STREAM-01, with explicit cross-reference to VALI-01 plan from v1.1.

---

### Pitfall 9: `make-scripts/` IIFE shape is not directly importable — tests end up testing a copy-paste

**What goes wrong:**
`quizify-mapping.js` and `score-calculations.js` are Make.com IIFE / sandbox modules — they read from a global `record` (or `bundle`/`output`) and write to another global, with no `module.exports`. A naive Node test harness either (a) copy-pastes function bodies into `*.test.js` (tests drift from reality) or (b) `eval()`s the file (sandbox semantics differ from Node's).

**Why it happens:**
Make.com's runtime injects globals into the IIFE scope; there is no public surface to require. The two files were never written with testability in mind (correctly so for v1.0/v1.1).

**How to avoid:**
- **Refactor JS into two-layer shape:** a pure function (`mapRecord(record) → output`) at top of file, then a thin Make.com adapter at the bottom (`output = mapRecord(record);` inside the IIFE) — adapter is 1–3 lines, pure function is the rest. The adapter is what Make.com runs; the pure function is what the harness imports.
- Use Node's built-in `node:test` + `node:assert` (Node ≥ 18 LTS) to keep the toolchain minimal — no jest, no mocha, no babel. Matches the spirit of D-13's stdlib-only ethos.
- Export via a conditional `if (typeof module !== "undefined") module.exports = { mapRecord };` at the very bottom, **after** the Make.com adapter, guarded so Make.com's sandbox does not see it. Verify in a sandbox-equivalent test: `delete global.module; require(...)` does not throw.
- Test fixtures must be **synthetic only** (T-PII-01 — `make-scripts/CONVENTIONS.md` already documents this pattern); no PII from `quizify-submissions.csv` in `make-scripts/__tests__/`.

**Warning signs:**
- Test file contains a literal copy of a function from the source.
- Tests pass but a manual run-in-Make.com sanity check fails.
- The pure function references `record` as a free variable instead of a parameter.

**Phase to address:** MAKE-TEST-01 (lands with MAKE-COSMETIC-01/02). Refactor-to-extract-pure-function is the first plan in that phase; cosmetic fixes ride along inside the now-testable pure function.

---

### Pitfall 10: Node test harness pollutes Make.com runtime via accidental global writes

**What goes wrong:**
The pure-function refactor accidentally introduces an implicit global — forgets `let`/`const` on a loop variable, or assigns to `output` at module top-level for "convenience." In Node it works (sloppy mode); in Make.com it silently overwrites the runtime's reserved names and breaks the scenario.

**Why it happens:**
Make.com's IIFE wrapper hides scoping issues — the `output` name is *expected* to be assigned. Node-side tests pass because they construct a fresh module each time.

**How to avoid:**
- Top of every JS file: `"use strict";` — turns implicit-global writes into TypeErrors. Both Node and Make.com sandboxes respect strict mode.
- Lint gate: a tiny `eslint:recommended` config (or hand-rolled grep) flagging `var` usage and undeclared identifiers.
- Test asserts that calling `mapRecord(fixture)` does not mutate `globalThis`: snapshot `Object.keys(globalThis).sort()` before and after; assert equality.
- Document expected globals in `make-scripts/CONVENTIONS.md` (extend the existing v1.1 file).

**Warning signs:**
- A function that "works in tests" produces empty/wrong output in Make.com.
- `globalThis` snapshot test fails after a refactor.

**Phase to address:** MAKE-TEST-01.

---

### Pitfall 11: `package.json` accidentally commits runtime dependencies, violating the spirit of D-13

**What goes wrong:**
A contributor adds `lodash`, `chalk`, or — most plausibly — `ajv` ("we're testing JSON, surely we need a JSON validator") to `package.json` `dependencies`. The Make.com runtime can't load npm packages, so it crashes when transitive `require()`s fire; or the Python side gains a soft expectation that node_modules is on disk.

**Why it happens:**
- `npm install some-pkg` defaults to writing to `dependencies`, not `devDependencies`.
- Test-tooling drift — someone adds a "small helper" without thinking about Make.com's zero-deps constraint.
- `package-lock.json` gets committed alongside, locking in a 200-package transitive tree from one helper.

**How to avoid:**
- Lock `make-scripts/package.json` to: empty `dependencies`, empty `devDependencies` (use built-in `node:test`), `scripts.test = "node --test make-scripts/__tests__"`, `engines.node = ">=18"`. Ship this exact shape in MAKE-TEST-01.
- CI gate: a test asserting `JSON.parse(package.json).dependencies` is `{}` and `devDependencies` is `{}`. JS-side analog of `pyproject.toml`'s empty `[project.dependencies]`.
- README addition (within D-11 ten-section lock — likely under "Development"): "make-scripts/ runs zero-dependency Node tests; do not add npm packages."
- Do not commit `package-lock.json` if there are no deps; if a dep is justified later, the PR adding it must update the README + CI gate.

**Warning signs:**
- A new top-level `node_modules/` appears in git status.
- `package-lock.json` size growth.
- `require()` of a non-`node:` builtin in any `make-scripts/*.js`.

**Phase to address:** MAKE-TEST-01 — same plan that introduces `package.json`.

---

### Pitfall 12: Snapshot/fixture drift in JS tests masks real regressions

**What goes wrong:**
The Node harness uses snapshot-style tests (`assert.deepStrictEqual(actual, expected)` with `expected` as inline literal). A contributor changes mapping behavior and updates the snapshot to match — the test passes, the regression ships.

**Why it happens:**
Snapshot-update is a 30-second action; reviewing whether the new snapshot is *correct* requires re-deriving the expected mapping from `make-scripts/CONVENTIONS.md`. Reviewers don't.

**How to avoid:**
- Write tests against **derived expectations**, not snapshots: `assert.equal(out["product-recommendation"], "peri_menu")` — each assertion ties back to a documented contract line in `CONVENTIONS.md`.
- Where snapshots are unavoidable (full output object), require the snapshot file to be paired with a comment block citing the CONVENTIONS.md section that justifies it; PR review enforces.
- Cross-check: at least one Python-side test should round-trip the CLI output through a Node child-process invocation of `mapRecord` and assert structural expectations. Optional but high-value for v1.2 since `make-scripts/` is now co-owned.

**Warning signs:**
- Snapshot diff in PR with no corresponding CONVENTIONS.md change.
- Reviewer comment "looks good, snapshot updated" without explanation.

**Phase to address:** MAKE-TEST-01.

---

### Pitfall 13: `--validate` semantics drift between non-stream + stream + post modes

**What goes wrong:**
Three emit paths — JSON-array (default), NDJSON stream, HTTP POST — each with `--validate`. Subtle differences creep in: array mode validates whole document; stream mode validates per row (Pitfall 8); POST mode validates… which? Per request? Whole batch? Different exit codes? Different stderr templates?

**Why it happens:**
Each mode is implemented in its own plan; the shared validator helper grows mode-specific branches; locked PII-safe stderr templates from D-06-19/D-06-20 are reused without re-locking for new modes.

**How to avoid:**
- Single contract: per-row item validation is canonical; whole-array validation in default mode is a thin wrapper that iterates. Both modes use the same `_validate_item` function with the same error template.
- POST mode: validate the whole batch first (using the shared per-row iteration), then POST. POST never partially-succeeds-then-validates.
- Lock new stderr templates as D-06-2x additions in the v1.2 decision register.
- Cross-mode test matrix: same malformed fixture × `{array, ndjson, post}` × `{--validate, no --validate}` = 6 cells. Assert exit codes + stderr templates form a coherent table.

**Warning signs:**
- A test only covers `--validate` in one emit mode.
- Stderr template strings appear duplicated in source (drift waiting to happen).

**Phase to address:** AUTO-01 + STREAM-01 — explicitly in the integration check between the two phases (mirroring v1.1's `INTEGRATION-CHECK.md` pattern).

---

### Pitfall 14: HTTP retries amplify PII exposure and duplicate webhook deliveries

**What goes wrong:**
Naive retry-on-network-error retries on 5xx and timeouts. If Make.com received the request but its response was lost (proxy timeout, partial TLS close), the retry creates a duplicate scenario run — two emails to the same respondent, double-counted scoring. Worse: if the first request leaked PII to a wrong endpoint (Pitfall 5), the retry leaks again.

**Why it happens:**
"Resilient" feels like the right default; `urllib3`/`tenacity`-style retry recipes are everywhere; nobody pauses to ask "is POST idempotent on this endpoint?"

**How to avoid:**
- **No retries by default** in v1.2. AUTO-01 ships single-shot POST. Document explicitly.
- If retries are added later, require either (a) idempotency-key header support on the Make.com side (currently unverified — flag for research) or (b) operator-confirmed `--retry N` flag with dry-run preview.
- Test asserts: a 503 response from the mock server produces exactly one request, exit non-zero.

**Warning signs:**
- Loop-with-sleep in the POST helper.
- Operator reports duplicate scenarios in Make.com history.

**Phase to address:** AUTO-01.

---

### Pitfall 15: Make.com webhook URL leaked via shell history, process listing, or error logs

**What goes wrong:**
The webhook URL contains a secret hook ID (`https://hook.eu2.make.com/abc123XYZ...`). If passed as `--post-url $URL` on the command line, it shows up in `ps aux`, shell history, CI logs, and crash reports. Anyone with the URL can POST scenario-triggering payloads.

**Why it happens:**
It looks like a regular URL, not a secret. Operators paste it into READMEs, scripts, Slack.

**How to avoid:**
- Support `--post-url-env QUIZIFY_WEBHOOK_URL` (read URL from named env var) as a first-class alternative to `--post-url`. Document this as the preferred form in README.
- Refuse to log the URL in stderr (categorical: log host only, not path). Add to PII-safe template lock.
- Document in README that `--post-url` is acceptable for one-off testing only; production should use the env-var form.

**Warning signs:**
- Webhook URL grep-able in commit history, `~/.bash_history`, CI logs.
- Operator reports unexpected scenario triggers.

**Phase to address:** AUTO-01.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Inline `urlopen(url, data=payload)` with no helper | One fewer function | Timeout/SSL/redirect/retry policy scattered or missing; PII-safe error path duplicated | Never — extract `_post_payload(url, payload, *, timeout, opener)` helper from the start |
| Skip atomic-rename for streaming output | Saves ~10 lines | Silent data corruption in pipelines on any mid-stream error | Never for STREAM-01 (data integrity is the feature) |
| Snapshot-only JS tests (no derived assertions) | Fast initial coverage | Real regressions ship behind passing tests (Pitfall 12) | MVP only — must convert to property-based assertions before MAKE-TEST-01 phase exit |
| `--validate` only in array mode (skip stream-mode integration) | Shorter STREAM-01 plan | AUTO-01 gating premise breaks at scale (>50k CSVs bypass validation) | Never — VALI-01 contract from v1.1 is non-negotiable |
| Add `ajv` to `package.json` for JS-side schema check | Free extra coverage | Violates D-13-spirit, breaks Make.com runtime, npm transitive-tree bloat | Never |
| Log full HTTP error response body behind `--verbose` | Easier debugging | T-PII-01 violation gated on a flag is still a violation | Never — categorical only, `--verbose` adds counts not contents |
| Reuse v1.1 PII-safe stderr templates verbatim for HTTP errors | Consistency | They were locked for *validation* error shape — HTTP errors have different fields (status, reason, class) | Never — lock new D-06-2x templates for HTTP surfaces |
| Single `--post-url` flag without env-var alternative | Smaller surface | Webhook URL leaks via shell history / `ps aux` (Pitfall 15) | Never for production; CLI-only acceptable for `--dry-run` previews |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Make.com webhook | Treat `200 OK` as "scenario ran successfully" | Make.com 200s on receipt, not on scenario completion; document this — any per-record outcome must come from a separate channel or be validated client-side via `--validate` before send |
| Make.com webhook | Send NDJSON to a webhook expecting a JSON array | Webhook content-type is `application/json` of an array — POST mode in v1.2 sends the **JSON-array form** of the batch, not NDJSON. NDJSON is for file output (`-o`); HTTP is array-bodied. Lock this in AUTO-01 plan |
| `urllib.error.URLError` | Catch only `HTTPError` | `URLError` is the parent (DNS, connection refused, TLS); `HTTPError` is the subclass (4xx/5xx). Catch `(HTTPError, URLError)` with class-aware branching |
| `http.client.RemoteDisconnected` | Not caught by `URLError` handler in older Pythons | Add to except tuple; emit categorical `network_disconnect` |
| Make.com IIFE sandbox | Use `console.log` for debug | Make.com sandbox redirects/strips `console`; debug via `output` shape only — document in `CONVENTIONS.md` |
| `node:test` | Assume Jest-style globals (`describe`, `it`, `expect`) | Use `import {test} from "node:test"; import assert from "node:assert/strict"` — different API surface |
| `pyproject.toml` `[validate]` extra | Add `urllib3` or `requests` for AUTO-01 | D-13 says stdlib at runtime — AUTO-01 uses `urllib`. No new dependencies. The `[validate]` extra remains the only optional |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Whole-array validation in stream mode | RAM spike to multi-GB on >50k rows; defeats STREAM-01 | Per-row validation against `schema["items"]` (Pitfall 8) | At ~50k rows on typical CI runner (~2GB RAM) |
| `json.dumps` with default `indent=2` in stream mode | NDJSON lines contain embedded newlines → unparseable | Force `indent=None, separators=(",", ":")` in stream emit | Immediately on first stream emit |
| fastjsonschema schema recompilation per row | 100x slowdown | Compile once outside the row loop (already correct in v1.1; preserve in stream refactor) | At ~1k rows |
| Synchronous POST per row (if anyone proposes it) | 50k POSTs × 200ms RTT = 2.7 hours, 50k webhook invocations | POST the whole batch as a single JSON array; if Make.com has size limits, chunk explicitly with operator-visible flag | At any rate beyond test scale |
| Reading entire CSV into memory before streaming | Negates STREAM-01 | Use `csv.DictReader(file)` iterator pattern; never `list(reader)` in stream path | At ~100k rows |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| HTTP error body logged to stderr (Pitfall 2) | PII leak via response echoes | Categorical-only template; negative-substring tests against fixture PII |
| Webhook URL on command line (Pitfall 15) | Secret leaks via `ps`, history, CI logs | `--post-url-env` env-var form documented as preferred |
| TLS verification disabled (Pitfall 4) | MITM exposes PII in transit | `ssl.create_default_context()`; HTTPS-only URL check; CI grep gate |
| Following redirects silently (Pitfall 5) | PII delivered to attacker-controlled host on hijacked DNS or misconfigured webhook | Custom redirect handler that refuses or restricts |
| `--validate` bypassed in POST mode | Schema-invalid PII payload sent to Make.com | argparse mutual-requirement check; "zero requests on invalid payload" integration test |
| JS test fixtures using real PII from `quizify-submissions.csv` | PII committed to git in test files | Synthetic fixtures only; extend `CONVENTIONS.md` rule (already present from v1.1) to test directory |
| `package-lock.json` commits transitive dep tree without review | Supply-chain risk in `make-scripts/` | Zero-dep policy (Pitfall 11); CI gate on empty `dependencies`/`devDependencies` |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `--post` succeeds silently with no confirmation of what was sent | Operator can't audit what hit Make.com | Print categorical summary to stderr: "POST sent: rows=N bytes=M status=200" — counts only, never content |
| `--post` requires `--validate` but error message is generic argparse | Confusion, support burden | Custom `parser.error("--post requires --validate (AUTO-01 gates POST on schema validity)")` |
| Streaming output silently overwrites existing file | Data loss when re-running | If `-o path` exists and `--force` not passed, refuse and exit non-zero — document in README |
| NDJSON file looks valid but has CRLF line endings | Downstream pipelines on Linux/Mac break in non-obvious ways | Force `newline="\n"` in `open()`; test asserts no `\r` bytes (Pitfall 6) |
| `--help` text doesn't mention AUTO-01 ↔ VALI-01 dependency | Operators try `--post` standalone, get cryptic error | argparse epilog explains the gating contract; D-11 README drift test catches doc gaps |
| Make.com side fix lands but operators don't know they need to update the scenario | JS module changes ship but Make.com still runs the old one | Document Make.com side update steps in README "Deployment" or `CONVENTIONS.md` |

## "Looks Done But Isn't" Checklist

- [ ] **AUTO-01 POST helper:** Often missing explicit `timeout=` — verify grep `urlopen(` in source has `timeout=` on every call.
- [ ] **AUTO-01 PII-safe error logger:** Often missing negative-substring test against real-shape error bodies — verify `TestHTTPErrorPIIsafe` exists with email/phone/free-text fixtures.
- [ ] **AUTO-01 ↔ VALI-01 gate:** Often missing "zero requests on invalid payload" integration test — verify mock-server test exists with `assert mock.request_count == 0`.
- [ ] **AUTO-01 redirect/SSL hardening:** Often missing — verify (a) HTTPS-only URL check at argparse, (b) custom redirect handler refusing cross-host, (c) no `_create_unverified_context` in source (CI grep gate).
- [ ] **STREAM-01 atomic write:** Often missing — verify `os.replace(tmp, final)` pattern and SIGINT mid-stream test.
- [ ] **STREAM-01 NDJSON correctness:** Often missing — verify final `\n`, no `\r`, round-trip read+parse, byte-identity vs v1.1 golden when re-aggregated.
- [ ] **STREAM-01 + VALI-01:** Often missing — verify per-row validation uses `schema["items"]`; test with malformed row mid-stream.
- [ ] **MAKE-TEST-01 IIFE refactor:** Often missing — verify pure function `mapRecord(record)` is exported and the Make.com adapter is the only thing referencing globals.
- [ ] **MAKE-TEST-01 `package.json`:** Often missing — verify zero `dependencies`, zero `devDependencies` (uses `node:test`), CI gate enforces.
- [ ] **MAKE-TEST-01 globals snapshot test:** Often missing — verify `globalThis` keys are unchanged across `mapRecord(fixture)` calls.
- [ ] **MAKE-COSMETIC-01/02:** Often "fixed" but not test-locked — verify a test would fail if the typo / dead init were re-introduced.
- [ ] **D-11 README ten-section lock:** Often broken when documenting `--post`/`-o ndjson` — verify `tests/test_readme_help_alignment.py` still 2/2 green and section count unchanged.
- [ ] **D-05 top-level key order:** Often perturbed when adding fields for HTTP response metadata — verify v1.1 golden fixture byte-identity test still passes (no new top-level keys added to records).
- [ ] **T-PII-01:** Often missed for new HTTP surfaces — verify negative-substring tests cover stderr from POST path with realistic error-body fixtures.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| HTTP error body leaked PII to stderr (Pitfall 2) shipped to operators | HIGH | Treat as security incident: scrub CI logs, rotate webhook URL with Make.com, patch + emergency release, add the leaked-fixture pattern to permanent regression suite |
| TLS verification disabled in shipped release (Pitfall 4) | HIGH | Rotate webhook URL; assume MITM possible for the exposed window; patch + emergency release |
| Streaming partial-file consumed downstream (Pitfall 7) | MEDIUM | Replay original CSV with fixed atomic-rename build; reconcile downstream state by row count; add atomic-rename pattern + SIGINT test |
| NDJSON CRLF/trailing-newline issue (Pitfall 6) | LOW | Re-emit with corrected writer; one-shot fix; add byte-pattern test |
| Make.com IIFE refactor broke production scenario (Pitfall 9/10) | MEDIUM | Revert the JS file; fix; redeploy with strict-mode + globals-snapshot test |
| `package.json` runtime deps committed (Pitfall 11) | LOW | Revert; restore zero-dep policy; CI gate prevents recurrence |
| `--validate`/`--post` race shipped a schema-invalid POST (Pitfall 3) | HIGH | Audit Make.com scenario history for invalid invocations; patch with mutual-requirement gate + integration test; cut release |
| Webhook URL leaked via command line (Pitfall 15) | MEDIUM | Rotate webhook URL with Make.com; ship `--post-url-env` form; document in README |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. urllib no-timeout | AUTO-01 | grep CI gate + unit test asserts `timeout=` kwarg |
| 2. Error body leaks PII | AUTO-01 | `TestHTTPErrorPIIsafe` negative-substring test against PII fixtures |
| 3. VALI-01↔AUTO-01 race | AUTO-01 (with VALI-01 cross-ref) | mock-server integration test: 0 requests on schema failure |
| 4. SSL disabled | AUTO-01 | grep CI gate (`CERT_NONE`, `_create_unverified_context`); HTTPS-only argparse check |
| 5. Silent redirects | AUTO-01 | Mock-server test: 302 cross-host → exit non-zero |
| 6. NDJSON newline | STREAM-01 | Byte-pattern test (final `\n`, no `\r`); round-trip parse |
| 7. Partial-write atomicity | STREAM-01 | SIGINT mid-stream test; assert `.tmp` exists, final does not |
| 8. Per-row vs whole-stream validation | STREAM-01 (cross-ref VALI-01) | Cross-mode test matrix; malformed-row-in-position-50 test |
| 9. IIFE not importable | MAKE-TEST-01 | Pure-function refactor lands first; sandbox-equivalent test |
| 10. Globals pollution | MAKE-TEST-01 | `"use strict"` + `globalThis`-keys snapshot test |
| 11. `package.json` deps creep | MAKE-TEST-01 | CI gate: empty `dependencies`/`devDependencies` |
| 12. Snapshot drift | MAKE-TEST-01 | Property-based assertions citing CONVENTIONS.md sections |
| 13. `--validate` semantics drift | AUTO-01 + STREAM-01 integration check | Cross-mode 6-cell test matrix in `INTEGRATION-CHECK.md` |
| 14. Retry duplicates | AUTO-01 | No-retry-default test: 503 → exactly one request |
| 15. Webhook URL leak | AUTO-01 | `--post-url-env` form documented; URL not logged |

## T-PII-01 Carry-Forward (Explicit)

T-PII-01 was scoped in v1.0 to *stderr from CSV-decode and validation paths*. v1.2 introduces new stderr-emitting surfaces; each must inherit the contract:

| New surface (v1.2) | T-PII-01 obligation | Test class to add |
|---|---|---|
| HTTP success log line | Status code + byte count only; no URL path, no response body | `TestHTTPSuccessPIIsafe` |
| HTTP error log line (4xx/5xx) | Status + reason + categorical class + body byte length; never body bytes, never request body, never URL path | `TestHTTPErrorPIIsafe` |
| HTTP network-failure log line (timeout/DNS/TLS/disconnect) | Categorical class only (`network_timeout`, `dns_failure`, `tls_failure`, `network_disconnect`); never original URL, never partial response data | `TestHTTPNetworkFailurePIIsafe` |
| Streaming partial-file warning on abort | Path of `.tmp` file (acceptable — operator-supplied), row count progressed, categorical reason; never row content | `TestStreamAbortPIIsafe` |
| Per-row validation failure in stream mode | JSON Pointer + row index; never cell content (matches existing VALI-01 D-06-19 template, applied per-item) | `TestStreamValidationPIIsafe` |

**Lock new templates as D-06-2x decisions in the v1.2 plan register**, parallel to v1.1's D-06-19/D-06-20 lock for validation stderr. Negative-substring assertions against email/phone/free-text fixtures from `quizify-submissions.csv` are the canonical verification.

## Sources

- Python stdlib documentation: `urllib.request`, `urllib.error`, `http.client`, `ssl`, `csv`, `json`, `os.replace` — verified against Python 3.7+ behavior; HIGH confidence on documented defaults (no-timeout, redirect handler, default SSL context).
- ndjson.org spec — line-delimited JSON convention; HIGH confidence on `\n` termination requirement.
- Node.js `node:test` and `node:assert` (Node 18+ LTS) — built-in test runner removes need for jest/mocha; HIGH confidence on availability.
- Make.com (Integromat) IIFE sandbox shape — inferred from existing `make-scripts/quizify-mapping.js` and `score-calculations.js` structure plus `make-scripts/CONVENTIONS.md` from v1.1; MEDIUM confidence on exact sandbox semantics — MAKE-TEST-01 plan should validate empirically before locking the conditional-export pattern.
- `.planning/PROJECT.md` (T-PII-01, D-05, D-11, D-13, VALI-01 lineage) — HIGH confidence (in-repo source of truth).
- `.planning/MILESTONES.md` v1.1 entry (deferred items list, D-06-19/D-06-20 stderr template lock pattern) — HIGH confidence.

---
*Pitfalls research for: stdlib-Python CLI adding HTTP egress + NDJSON streaming + Node test harness, v1.2 milestone*
*Researched: 2026-05-05*
