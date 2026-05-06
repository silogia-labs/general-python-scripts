# Phase 9: AUTO-01 HTTP POST Delivery - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Promote Phase 7's `_HttpPostSink` stub (currently `__init__(url)` + `write` raises `NotImplementedError`) into a real single-shot HTTPS POST sink that emits the validated JSON-array payload to a webhook. Adds `--post-url URL`, `--header "K: V"` (repeatable), `--timeout SECONDS` (default 30); enforces argparse-time HTTPS-only, `--post-url` requires `--validate`, and CRLF-in-header rejection; uses a custom `urllib` opener with a `_NoRedirectHandler` (rejects ALL redirects) and `ssl.create_default_context()`; emits one categorical PII-safe stderr line on every failure path via a single `_log_http_failure` helper; exits 1 on validation, 2 at argparse, 3 on every HTTP/network failure (timeout, non-2xx, redirect, TLS, DNS, connection refused). No retry. No body bytes ever logged. Stdlib-only at runtime — only `urllib.request`, `urllib.error`, `urllib.parse`, `ssl`, `socket` added.

NDJSON × `--post-url` cross-product is explicitly out of scope (argparse mutex from Phase 8 already rejects it; deferred to v1.3 per REQUIREMENTS Future Requirements).

</domain>

<decisions>
## Implementation Decisions

### Redirect Handling

- **D-09-01 (Reject ALL redirects via `_NoRedirectHandler` subclass):** Custom `urllib.request.HTTPRedirectHandler` subclass whose `redirect_request()` raises `urllib.error.HTTPError(req.full_url, code, "http_unexpected_redirect", headers, fp)` for any 3xx response, regardless of host. AUTO-05 wording is "no cross-host redirects" — Make.com webhooks return 200 directly, so a 3xx on a webhook target is misconfiguration or hostile. Rejecting all redirects is simpler than host comparison, has no edge cases (port differences, IDN, trailing dots, scheme upgrades), and satisfies AUTO-05's spirit AND letter. The `req.full_url` passed to `HTTPError.__init__` is the ORIGINAL request URL — the redirect target URL never enters the error chain (T-PII-01: target URL never logged).

- **D-09-02 (Opener built explicitly, not the urllib default):** `urllib.request.build_opener(_NoRedirectHandler(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))` is constructed inside `_HttpPostSink.__init__` (or a module-level factory) and held on the instance as `self._opener`. The default urllib opener auto-handles redirects via the standard `HTTPRedirectHandler` — building our own is the only way to swap it out. `urlopen()` is NEVER called directly; ALL HTTP traffic goes through `self._opener.open(req, timeout=self._timeout)`.

- **D-09-03 (Reason-class discrimination on raised HTTPError):** When `_NoRedirectHandler` raises an `HTTPError` with code 3xx, the existing `try/except HTTPError` path in `_HttpPostSink` (or a `_classify_http_error(err)` helper) inspects `err.code` and routes: `3xx → reason="http_unexpected_redirect"`, `4xx → reason="http_client_error"`, `5xx → reason="http_server_error"`. The categorical reason string is the only thing that distinguishes the three on stderr — `err.url` and `err.read()` (body) are NEVER touched in the logging path. `body_bytes` reads `err.headers.get("Content-Length", "-")` (or counts `len(err.read())` if needed for the test fixture, but prefer Content-Length to avoid pulling body bytes into memory).

### Headers & CRLF

- **D-09-04 (Argparse `type=_parse_header` callable + `action='append'`):** Custom callable validates each `--header "K: V"` value at parse time. Rejects via `argparse.ArgumentTypeError` (which argparse converts to exit 2 + categorical stderr) on:
  - CRLF (`\r` or `\n`) anywhere in the input → `header_crlf_rejected`
  - missing colon → `header_missing_colon`
  - empty name → `header_empty_name`
  - name not matching RFC 7230 token charset → `header_invalid_name`
  Stored on `args.header: list[tuple[str, str]]` (`default=[]`). Value is `s.partition(":")[2].lstrip()` — no rstrip (RFC 7230 allows trailing OWS but values are passed verbatim to `Request.add_header`, which is fine).

- **D-09-05 (`Content-Type: application/json` injection — user wins):** `_HttpPostSink.write()` (or `flush_and_post()` on close) builds the `Request` with user-supplied headers from `args.header` first, THEN injects `Content-Type: application/json` ONLY if no user header has the same name (case-insensitive `name.lower() == "content-type"`). This lets operators override for niche webhook content-types (e.g., `application/vnd.api+json`). Make.com is `application/json`-only — the override pathway is unused in the primary use case but exists for forward compatibility. NEVER log header values (T-PII-01: `Authorization: Bearer ...` would otherwise leak via verbose logging).

- **D-09-06 (Header parser is a module-level helper, not a method):** `_parse_header(s: str) -> tuple[str, str]` lives at module scope so it's reusable from tests without instantiating a sink. Exists alongside `_log_http_failure` and the `_NoRedirectHandler` class.

### Stderr Templates & Exit Codes

- **D-09-07 (Single helper `_log_http_failure(reason, **kwargs)` is the ONLY stderr path for HTTP/network failures):** All AUTO-04/05/06 stderr writes go through this one function. CI grep gate (planner's call on exact regex) on the production module to ensure no other `logging.error`/`sys.stderr.write`/`print(... file=sys.stderr)` paths exist for HTTP failures. Format (locked verbatim, key=value, space-separated):
  ```
  http_failure reason=<R> status=<N|-> reason_class=<3xx|4xx|5xx|-> body_bytes=<N|->
  ```
  All four keys ALWAYS present (use `-` for unknown/inapplicable). Greppable, machine-parseable, PII-safe by construction (no URL, no body bytes, no headers, no host).

- **D-09-08 (Locked `reason` vocabulary):**
  | reason | Trigger | status | reason_class | body_bytes |
  |---|---|---|---|---|
  | `network_timeout` | `socket.timeout` raised by `urlopen(timeout=...)` | `-` | `-` | `-` |
  | `http_unexpected_redirect` | 3xx response (any host, any code) | `<int>` | `3xx` | `<int|->` |
  | `http_client_error` | 4xx response | `<int>` | `4xx` | `<int|->` |
  | `http_server_error` | 5xx response | `<int>` | `5xx` | `<int|->` |
  | `tls_error` | `ssl.SSLError` / `ssl.SSLCertVerificationError` | `-` | `-` | `-` |
  | `dns_error` | `socket.gaierror` (URLError reason) | `-` | `-` | `-` |
  | `connection_refused` | `ConnectionRefusedError` (URLError reason) | `-` | `-` | `-` |
  | `network_error` | catch-all `URLError` not classified above | `-` | `-` | `-` |

  Planner may add granularity but MUST NOT remove any of the eight or change the spelling. Each reason has an associated negative-substring test in the PII-safe-stderr suite.

- **D-09-09 (Exit codes locked):** Validation failure → 1 (existing D-06-21 carry-forward). Argparse rejection → 2 (Python argparse default; covers AUTO-02 missing `--validate`, AUTO-03 CRLF, AUTO-05 non-HTTPS, malformed `--header`, malformed URL). HTTP/network failure → 3 (every reason in D-09-08). The exit-code function is a single `if/elif` chain at the top of `convert()`'s post-`_HttpPostSink` error handling; planner exposes it as `_EXIT_HTTP = 3`, `_EXIT_VALIDATION = 1` constants for grep-ability.

### `_HttpPostSink` Shape

- **D-09-10 (Buffer-and-POST, NOT streaming — array-body single-shot):** `_HttpPostSink` mirrors `_StdoutSink`/`_FileSink`'s buffering shape, NOT `_NdjsonFileSink`'s context-manager streaming shape. `__init__(url, headers, timeout)` stores config; `__enter__` returns `self`; `write(row)` appends to `self._rows: list[dict]`; `__exit__(exc_type, ...)` and `close()` perform the POST exactly once IFF `exc_type is None` AND rows is non-empty. On exception inside the `with` block (validation failure, generator error, KeyboardInterrupt), NO POST is sent — STREAM-04's "no partial state escapes" invariant carries forward to AUTO-01 as "no partial / invalid payload escapes the process".

- **D-09-11 (Validation-gate placement — argparse + existing batch path):** AUTO-02 ("`--post-url` requires `--validate`") is enforced at argparse (post-parse `parser.error()` check, same shape as Phase 8's `--ndjson` gates). The validation timing itself is the existing batch path (`_run_schema_validation(results, SCHEMA_PATH)` after `list(iter_rows(...))`, BEFORE `with sink:`). `_ValidatingSink` (Phase 8 decorator) is NOT used for AUTO-01 — array-body POST is a batch operation, not per-row. Locked: `_HttpPostSink` is wired into `_select_sink` exactly as Phase 8 already wires it (no `_ValidatingSink` wrap).

- **D-09-12 (`urlopen` call shape):** `req = urllib.request.Request(self._url, data=payload_bytes, method="POST", headers=resolved_headers)` followed by `with self._opener.open(req, timeout=self._timeout) as resp: status = resp.status; resp.read(); ...`. Exactly ONE `open()` call per `flush_and_post()`; the SC#1 "exactly one request, no retry" invariant is locked by code structure (no loop, no retry handler) plus the test-fixture `assert len(received) == 1`. `payload_bytes = json.dumps(self._rows, ensure_ascii=False).encode("utf-8")` — same encoding as `_StdoutSink`/`_FileSink` minus `indent=2` (compact for wire efficiency; Make.com accepts both).

### Argparse

- **D-09-13 (`--post-url`, `--header`, `--timeout` peer flags + 3 post-parse `parser.error()` checks):** Phase 7 already added `--post-url` to the existing `-o/--post-url` mutex group (D-07-10); that stays. Phase 9 adds:
  - **Custom `type=_https_url` callable on `--post-url`** that validates `urlsplit(s).scheme == "https"` AND non-empty netloc; rejects via `ArgumentTypeError("post_url_https_required")`. AUTO-05 HTTPS gate.
  - **`--header`** as documented in D-09-04.
  - **`--timeout`** as `type=float, default=30.0`; `parser.error("timeout_invalid")` if `<= 0` post-parse (no `type=` rejection because `argparse` converts before our callable sees it; or use a custom `type=_positive_float`).
  - **Post-parse check:** if `args.post_url and not args.validate`: `parser.error("post_url_requires_validate")` (AUTO-02). This sits alongside Phase 8's two `--ndjson` post-parse checks; planner consolidates them in one block at the top of `main()` after `parse_args()`.

- **D-09-14 (URL never logged, even at argparse rejection):** When `_https_url` rejects a value, the `ArgumentTypeError` message is the categorical reason string (`post_url_https_required`) — NOT the offending URL. argparse will include the user's input in its `error: argument --post-url: invalid _https_url value: 'http://...'` message; this is a known argparse behavior. Planner's call: accept argparse's default behavior (URL appears once at argparse level, before any logging path) OR override `parser.error` to suppress. Recommend ACCEPT — the URL only appears in the immediate stderr message at argparse level; the `_log_http_failure` PII-safe path is what AUTO-05/T-PII-01 actually constrain (no URL during runtime errors). Document this in `<deferred>`.

### Testing

- **D-09-15 (Stdlib `http.server` per-test fixture for AUTO-01..06 integration tests):** A `mock_webhook` pytest fixture spins up `http.server.HTTPServer(("127.0.0.1", 0), handler_factory)` on a random port in a daemon thread; yields `(url, received_log)`; calls `server.shutdown()` on teardown. Per-test `BaseHTTPRequestHandler` subclasses parametrize behavior:
  - `_Handler200` — read body, append, return 200.
  - `_Handler502` — read body, append, return 502 with bounded body (e.g., `b"Bad Gateway!!"`).
  - `_Handler302` — return 302 with `Location: http://other.example.test/x`.
  - `_HandlerHang` — sleep > timeout and never respond.

  Tests POST to `http://127.0.0.1:<port>` directly via `_HttpPostSink(url, ...)` or `convert(post_url=url, ...)`, BYPASSING the argparse HTTPS-only gate. The argparse gate gets its own pure-unit test (`test_argparse_post_url.py`) that asserts `parser.parse_args(["--post-url", "http://x", ...])` raises `SystemExit` with `post_url_https_required` in stderr — no socket touched.

- **D-09-16 (Critical "exactly one request" assertion):** Every success and every failure-mode test asserts `len(received) == 1` (or `0` for the validation-fail-pre-egress test). This is the single highest-value test for AUTO-06 SC#1 — only a real socket can prove absence of retry. Mocks can't.

- **D-09-17 (`TestHTTPErrorPIIsafe` negative-substring suite):** Mirrors Phase 6's `TestValidationFailurePIIsafe` shape. Synthetic fixture row contains tokens (e.g., `marker_email_50@example.test`, `+15555550042`, `marker_freetext_xyzzy`); test asserts NONE of those tokens appear in captured stderr after each failure mode. The mock handler's response body also contains a marker token (e.g., `b"server_response_marker"`); test asserts that marker NEVER appears in stderr (proves body bytes aren't surfaced). T-PII-01 carry-forward, AUTO-06 SC#3 negative-substring requirement.

- **D-09-18 (CI grep gates listed in must_haves):** Locked grep assertions (planner exposes as test cases or `tests/test_security_grep_gates.py`):
  - `! grep -nE "CERT_NONE|_create_unverified_context|verify=False" quizify-csv-to-json-webhook/quizify_csv_ingest.py` (AUTO-05).
  - `grep -c "ssl.create_default_context()" quizify-csv-to-json-webhook/quizify_csv_ingest.py` should be exactly 1 (AUTO-05 default context constructed once).
  - `grep -c "self._opener.open(" quizify-csv-to-json-webhook/quizify_csv_ingest.py` should be 1 (AUTO-04: timeout passed on every urlopen call — only one call site).
  - `! grep -E "^import requests|^from requests" quizify-csv-to-json-webhook/quizify_csv_ingest.py` (D-13 stdlib-only; no `requests` library introduced).

### Carry-forward (locked, not re-asked)

- **D-05 (locked tail-key order):** `_HttpPostSink` reuses `build_row` output; key order preserved in the POST body. `ensure_ascii=False`.
- **D-06-2x:** Validation-failure exit code 1 + PII-safe stderr unchanged. AUTO-02 argparse rejection adopts the same exit-2 + categorical-stderr shape as Phase 8's `--ndjson` post-parse checks.
- **D-07-04 (`_HttpPostSink` stub depth):** Phase 7's stub `__init__(url)` is REPLACED in this phase by `__init__(url, headers, timeout)`. The `NotImplementedError` raise in `write()` is replaced by the buffer-and-POST body. Phase 7's mutex group on `-o/--post-url` STAYS.
- **D-08-01..D-08-15 (Phase 8 sink Protocol + decorator):** `_HttpPostSink` conforms to the same `_Sink` Protocol (`write(row)`, `close()`, `__enter__/__exit__`). NOT wrapped by `_ValidatingSink` (D-09-11). `convert()`'s `with sink:` loop is unchanged.
- **D-11 (10-section README lock):** README updates land inside existing sections only. Likely additions: `--post-url`, `--header`, `--timeout` rows in `## CLI reference` table; usage example in existing examples section. NO new H2.
- **D-13 (stdlib-only at runtime):** Only `urllib.request`, `urllib.error`, `urllib.parse`, `ssl`, `socket` added. No `requests`, no `httpx`, no `aiohttp`. Lazy imports NOT required (these are all stdlib and tiny); top-level imports OK.
- **T-PII-01:** All new stderr surfaces are categorical. Negative-substring suite (D-09-17) is the structural enforcement.

### Claude's Discretion

- Exact regex for the CI grep gate (planner's call as long as the four invariants in D-09-18 are enforceable).
- Whether `_HttpPostSink` exposes `headers` as a list-of-tuples or a normalized `dict[str, str]` internally — Protocol-side it doesn't matter; tests work against the wire.
- Whether `flush_and_post()` is a separate method called by both `__exit__` and `close()` (recommended for testability) or inlined.
- Whether `_https_url` validation also rejects URLs with a userinfo segment (e.g., `https://user:pass@host`) — recommended yes (avoid auth-in-URL anti-pattern), but planner's call.
- Test file naming and placement (extend `tests/test_argparse_ndjson.py` vs new `tests/test_argparse_post_url.py`; new `tests/test_http_post.py` for integration; new `tests/test_http_post_pii.py` for the PII-safe negative-substring suite).
- Whether the timeout test uses `_HandlerHang` with `time.sleep` or a `socket.timeout` simulation via mocking the opener directly — both satisfy AUTO-04; real-socket sleep is more honest but adds ~1s to the test suite (acceptable).
- Whether `args.timeout` validation is `type=_positive_float` or a post-parse `if args.timeout <= 0: parser.error(...)` check — both reach exit 2.
- Whether `args.header` defaults to `[]` or `None` and is normalized to `[]` in `convert()` — preference: `default=[]` to avoid `None` checks downstream.
- Whether `_log_http_failure` accepts positional `reason` only or also kwargs `status`/`reason_class`/`body_bytes` — locked positional + kwargs in D-09-07; planner picks parameter names.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and acceptance criteria
- `.planning/ROADMAP.md` §"Phase 9: AUTO-01 HTTP POST Delivery" — phase goal, dependencies (Phase 8), six success criteria.
- `.planning/REQUIREMENTS.md` §"Delivery — HTTP POST (AUTO)" — AUTO-01..06 verbatim text.

### Project decisions and constraints
- `.planning/PROJECT.md` §"Key Decisions" — D-05 (tail-key order), D-11 (10-section README lock), D-13 (stdlib-only at runtime).
- `.planning/PROJECT.md` §"Constraints" — T-PII-01 (PII-safe stderr).

### Phase 8 carry-forwards (immediate predecessor)
- `.planning/phases/08-stream-01-ndjson-output/08-CONTEXT.md` — D-08-01 (`_Sink` Protocol shape; `_HttpPostSink` conforms), D-08-03 (CM shims on all sinks), D-08-11 (post-parse `parser.error()` argparse pattern — AUTO-02/05 reuse this shape), D-08-13 (per-row validation is opt-in only — array-mode batch path applies to AUTO-01).

### Phase 7 carry-forwards
- `.planning/phases/07-refactor-scaffolding-no-op/07-CONTEXT.md` — D-07-04 (`_HttpPostSink` stub: `__init__(url)` only, `write` raises NotImplementedError — Phase 9 REPLACES this), D-07-10 (Phase 7 `-o/--post-url` mutex group preserved).

### Phase 6 carry-forwards (validation surfaces)
- `.planning/milestones/v1.1-phases/06-json-schema-validation/06-CONTEXT.md` — D-06-16 (post-build pre-write timing for batch validation; AUTO-01 reuses), D-06-2x stderr templates (AUTO-06 stderr templates align in shape).

### v1.2 milestone research
- `.planning/research/SUMMARY.md`, `.planning/research/STACK.md`, `.planning/research/FEATURES.md`, `.planning/research/PITFALLS.md`, `.planning/research/ARCHITECTURE.md` — v1.2 research outputs (sink abstraction, NDJSON, HTTP POST). Phase 9 implements the AUTO portion.

### Pitfalls and known landmines
- `.planning/research/PITFALLS.md` §"Pitfall 16" — keep tests at unit level; integration tests via real `http.server` are the justified exception when proving "exactly one request, no retry" (AUTO-06 SC#1).
- `.planning/research/PITFALLS.md` §"Pitfall 17" — never forward exception messages with potentially-sensitive content; `HTTPError.__str__` includes the URL, so the logging path uses `err.code` + a fixed reason string only.

### Files being edited or created
- **EDITED:** `quizify-csv-to-json-webhook/quizify_csv_ingest.py` — replace `_HttpPostSink` body (Phase 7 stub) with real implementation; add `_NoRedirectHandler` class; add `_log_http_failure(reason, **kwargs)` helper; add `_parse_header(s)` callable; add `_https_url(s)` callable for argparse `type=`; extend argparse with `--header`, `--timeout` (and the third post-parse `parser.error` check for `--post-url requires --validate`); thread `headers` and `timeout` through `convert()` (or a `_HttpPostSink(url, headers, timeout)` constructor); update `_select_sink` to pass headers/timeout to `_HttpPostSink`. ALL changes scoped to this single file (D-06-04 single-file rule).
- **EDITED:** `quizify-csv-to-json-webhook/README.md` — add `--post-url`, `--header`, `--timeout` rows to existing `## CLI reference` table; add usage example with `--post-url --validate`. NO new H2 (D-11).
- **NEW (planner's discretion on filenames):** `tests/test_http_post.py` (happy path, request-count, non-2xx, 302, timeout integration tests via `mock_webhook` fixture); `tests/test_http_post_pii.py` (negative-substring suite); `tests/test_argparse_post_url.py` (argparse HTTPS-only, `--post-url` requires `--validate`, `--header` CRLF rejection, `--timeout` invalid; pure unit, no socket); `tests/conftest.py` extension (`mock_webhook` fixture + handler factories).
- **NOT EDITED:** `_run_schema_validation`, `_format_validation_error`, `build_row`, `classify_headers`, `iter_rows`/`_RowStream`, `_StdoutSink`/`_FileSink`/`_NdjsonFileSink`/`_ValidatingSink`, schema artifact `webhook-schema.json`.

### Sample / verification fixtures
- `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` — 42-row real export. Happy-path POST sends this to `_Handler200`; received body decoded and asserted to match the v1.1 golden array.
- Synthetic CSV-derived PII tokens (`marker_email_<idx>@example.test`, `+15555550<NN>`, `marker_freetext_xyzzy`) — generated in test fixtures (T-PII-01-safe).
- Mock server response-body marker (`b"server_response_marker"`) — proves body bytes never reach stderr.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_HttpPostSink` (`quizify_csv_ingest.py:97`) — Phase 7 stub. `__init__(url)` body REPLACED with `__init__(url, headers, timeout)`; `write` body REPLACED with `self._rows.append(row)`; new `__enter__`/`__exit__`/`close` for buffer-and-POST shape.
- `_StdoutSink` / `_FileSink` (lines 54–95) — analog buffering shape (`self._rows: list[dict]` + `json.dump` once on close); `_HttpPostSink` mirrors with `urlopen` instead of `json.dump`.
- `_select_sink(args, schema_path)` (line 198) — already routes `args.post_url` to `_HttpPostSink`. Signature change: pass `args.header` and `args.timeout` through (or pass `args` as already designed in D-08-12).
- `_run_schema_validation` (Phase 6, body untouched) — existing batch validation that gates AUTO-01 emit.
- `convert()` (line 670+) — `with sink:` loop unchanged. Validation already happens before `with sink:`. `_HttpPostSink` slots in via `_select_sink` with no convert() body changes.
- Phase 8's `--ndjson` post-parse `parser.error` checks (lines 784–789) — direct analog for AUTO-02 / AUTO-03 / AUTO-05 argparse rejections; consolidate all post-parse checks in one block.

### Established Patterns
- Single-file CLI by design (D-06-04). All new code lands in `quizify_csv_ingest.py`.
- Lazy / conditional imports for OPTIONAL extras (D-13 + Phase 6 `fastjsonschema`). HTTP imports are stdlib so they go top-level — no laziness needed.
- First-only / once-only side effects: `ssl.create_default_context()` constructed once per `_HttpPostSink` instance; opener built once per instance; one `urlopen()` call per `flush_and_post()`.
- Argparse `type=` callable for parse-time validation (Phase 8's `--ndjson` precedent for post-parse; this phase pioneers `type=` callables).
- Categorical key=value stderr (Phase 6 D-06-2x; this phase extends with the locked vocabulary in D-09-08).

### Integration Points
- `convert()` signature: `post_url: str | None`, `headers: list[tuple[str, str]] | None`, `timeout: float = 30.0` (or accept the args namespace through `_select_sink(args)` per D-08-12). Planner picks one shape; CONTEXT prefers explicit named parameters for testability.
- `_select_sink(args)`: `if args.post_url is not None: return _HttpPostSink(args.post_url, args.header, args.timeout)`. Validation is enforced by the argparse `--post-url requires --validate` gate (D-09-13) — `_select_sink` does not need to assert validation.
- Argparse: 3 new flags (`--header`, `--timeout`, plus `type=_https_url` on existing `--post-url`); 1 new post-parse check (`--post-url requires --validate`) added to the existing post-parse-checks block.
- Test fixtures: `mock_webhook` lives in `tests/conftest.py`; integration tests live in new `tests/test_http_post*.py` files; argparse tests reuse the existing pure-unit pattern from `tests/test_argparse_ndjson.py`.

</code_context>

<specifics>
## Specific Ideas

- **`_NoRedirectHandler` skeleton (locked verbatim):**
  ```python
  class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
      def redirect_request(self, req, fp, code, msg, headers, newurl):
          # AUTO-05: reject ALL redirects categorically; original URL only
          raise urllib.error.HTTPError(
              req.full_url, code, "http_unexpected_redirect", headers, fp,
          )
  ```

- **`_log_http_failure` skeleton (locked verbatim):**
  ```python
  def _log_http_failure(reason: str, *,
                        status: int | None = None,
                        reason_class: str | None = None,
                        body_bytes: int | None = None) -> None:
      def _or_dash(v): return str(v) if v is not None else "-"
      logging.error(
          "http_failure reason=%s status=%s reason_class=%s body_bytes=%s",
          reason, _or_dash(status), _or_dash(reason_class), _or_dash(body_bytes),
      )
  ```

- **`_parse_header` skeleton (locked shape; planner may tweak regex per RFC 7230):**
  ```python
  _HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")

  def _parse_header(s: str) -> tuple[str, str]:
      if "\r" in s or "\n" in s:
          raise argparse.ArgumentTypeError("header_crlf_rejected")
      if ":" not in s:
          raise argparse.ArgumentTypeError("header_missing_colon")
      name, _, value = s.partition(":")
      name = name.strip()
      if not name:
          raise argparse.ArgumentTypeError("header_empty_name")
      if not _HEADER_NAME_RE.match(name):
          raise argparse.ArgumentTypeError("header_invalid_name")
      return name, value.lstrip()
  ```

- **`_https_url` skeleton (locked shape):**
  ```python
  def _https_url(s: str) -> str:
      parts = urllib.parse.urlsplit(s)
      if parts.scheme != "https" or not parts.netloc:
          raise argparse.ArgumentTypeError("post_url_https_required")
      return s
  ```

- **`_HttpPostSink` skeleton (locked structural shape; planner picks attribute names):**
  ```python
  class _HttpPostSink:
      def __init__(self, url: str, headers: list[tuple[str, str]] | None, timeout: float):
          self._url = url
          self._headers = list(headers or [])
          self._timeout = timeout
          self._rows: list[dict] = []
          self._opener = urllib.request.build_opener(
              _NoRedirectHandler(),
              urllib.request.HTTPSHandler(context=ssl.create_default_context()),
          )

      def __enter__(self): return self
      def write(self, row: dict) -> None: self._rows.append(row)

      def __exit__(self, exc_type, exc, tb):
          if exc_type is None and self._rows:
              self._flush_and_post()
          return False  # never suppress

      def close(self) -> None:
          # convert() uses `with sink:`; close() called by Protocol but is now a no-op.
          pass

      def _flush_and_post(self) -> None:
          payload = json.dumps(self._rows, ensure_ascii=False).encode("utf-8")
          resolved = list(self._headers)
          if not any(name.lower() == "content-type" for name, _ in resolved):
              resolved.append(("Content-Type", "application/json"))
          req = urllib.request.Request(self._url, data=payload, method="POST")
          for name, value in resolved:
              req.add_header(name, value)
          try:
              with self._opener.open(req, timeout=self._timeout) as resp:
                  resp.read()  # drain; status already 2xx if we reach here
              return
          except urllib.error.HTTPError as err:
              # 3xx (via _NoRedirectHandler), 4xx, or 5xx
              cls = "3xx" if 300 <= err.code < 400 else "4xx" if 400 <= err.code < 500 else "5xx"
              reason = {
                  "3xx": "http_unexpected_redirect",
                  "4xx": "http_client_error",
                  "5xx": "http_server_error",
              }[cls]
              body_bytes_hint = err.headers.get("Content-Length")
              _log_http_failure(reason, status=err.code, reason_class=cls,
                                body_bytes=int(body_bytes_hint) if body_bytes_hint else None)
              raise _HttpDeliveryError(reason)
          except socket.timeout:
              _log_http_failure("network_timeout")
              raise _HttpDeliveryError("network_timeout")
          except urllib.error.URLError as err:
              # classify err.reason: ssl.SSLError, socket.gaierror, ConnectionRefusedError, generic
              ...
              _log_http_failure(reason)
              raise _HttpDeliveryError(reason)
  ```

  `_HttpDeliveryError` is a sentinel exception caught by `convert()` to produce exit code 3.

- **Argparse additions (locked):**
  ```python
  group.add_argument("--post-url", default=None, type=_https_url,
      help="HTTPS URL for single-shot webhook POST (requires --validate). Mutually exclusive with -o/--output and --ndjson.")
  parser.add_argument("--header", action="append", default=[], type=_parse_header,
      help='Repeatable: add "Name: Value" header (e.g., "Authorization: Bearer ..."). CRLF rejected.')
  parser.add_argument("--timeout", type=float, default=30.0,
      help="HTTP request timeout in seconds (default: 30.0). Applies only with --post-url.")

  args = parser.parse_args()
  # existing Phase 8 checks ...
  if args.post_url and not args.validate:
      parser.error("post_url_requires_validate")
  if args.timeout <= 0:
      parser.error("timeout_invalid")
  ```

- **Mock server fixture (locked structural shape):**
  ```python
  @pytest.fixture
  def mock_webhook():
      received: list[tuple[str, bytes]] = []
      class Handler(http.server.BaseHTTPRequestHandler):
          def do_POST(self):
              n = int(self.headers.get("Content-Length", "0"))
              received.append(("POST", self.rfile.read(n)))
              # subclasses override this to set response
              self._respond()
          def log_message(self, *a, **kw): pass  # silence test output
      def factory(respond_fn):
          klass = type("H", (Handler,), {"_respond": respond_fn})
          server = http.server.HTTPServer(("127.0.0.1", 0), klass)
          thread = threading.Thread(target=server.serve_forever, daemon=True)
          thread.start()
          url = f"http://127.0.0.1:{server.server_address[1]}"
          return url, received, server
      yield factory
      # caller responsible for server.shutdown() in test teardown
  ```

</specifics>

<deferred>
## Deferred Ideas

- **`--retry N` with exponential backoff** — v1.3+ per REQUIREMENTS Future Requirements. Make.com idempotency unverified; v1.2 is fail-fast.
- **`--idempotency-key`** — v1.3+; Make.com support unverified.
- **`$QUIZIFY_WEBHOOK_URL` / `--post-url-env`** — defer unless operator pain reported (T-PII-01: log host-only, never full URL, when this lands).
- **NDJSON × `--post-url` cross-product** — v1.3+; Make.com webhook content-type is `application/json` of an array.
- **Same-host redirect tolerance** — explicitly rejected (D-09-01). Webhooks shouldn't redirect; enforcing zero-redirects is simpler and safer.
- **OAuth / built-in auth flows** — out of scope per REQUIREMENTS; `--header "Authorization: Bearer ..."` collapses every realistic auth scheme.
- **Persistent retry queue / multi-URL fan-out** — out of utility-script scope.
- **`--post-body-from-file`** — out of scope; CSV is the source of truth.
- **Argparse-level URL suppression in stderr** — argparse's default `error: argument --post-url: invalid _https_url value: 'http://...'` includes the URL once at argparse-level. Accepted as documented behavior; D-09-14 marks this as a known stderr-leak surface separate from the runtime PII-safe path. Future enhancement: override `parser.error` to suppress the value reproduction.
- **Top-level `_log_http_failure` extension to non-HTTP failures** — e.g., disk-full on `_FileSink`. Out of scope; Phase 9 helper is HTTP-only.
- **Make.com hygiene + node:test harness** — Phase 10. Independent.

</deferred>

---

*Phase: 09-auto-01-http-post-delivery*
*Context gathered: 2026-05-05*
