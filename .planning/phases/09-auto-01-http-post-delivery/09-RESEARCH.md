# Phase 9: AUTO-01 HTTP POST Delivery — Research

**Researched:** 2026-05-05
**Domain:** Python stdlib HTTP egress (`urllib.request`/`error`/`parse`, `ssl`, `socket`) wired into an existing sink Protocol
**Confidence:** HIGH (urllib + ssl behaviors verified by inspecting Python 3.10 source on this machine; cross-version behavior cited from CPython release notes)

## Summary

This is an **implementation-grade research pass** — not a domain survey. All architectural decisions are locked in `09-CONTEXT.md` (D-09-01..18) and PROJECT carry-forwards (D-05, D-11, D-13, T-PII-01). The job here is to (a) confirm the locked skeletons compile and behave as the decision rationale assumes, (b) close the ten implementation questions surfaced by the orchestrator, and (c) lock the test-fixture discipline for the "exactly one request, no retry" assertion.

**Primary recommendation:** Implement the locked skeletons verbatim. The five places where this research adds prescriptive guidance beyond what CONTEXT.md says are: (1) URLError reason classification order, (2) socket.timeout vs TimeoutError catch shape on Python 3.10+, (3) `Request.has_header("Content-Type")` instead of pre-resolving the user header list, (4) the mock-server fixture's `server_close()`-after-`shutdown()` discipline + `allow_reuse_address` for port-flake avoidance, (5) the 302-test request-count assertion (it must equal 1, NOT 0 — the rejected-redirect request still hits `do_POST` once).

`<user_constraints>`
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-09-01 through D-09-18 (verbatim, see 09-CONTEXT.md `<decisions>` block — quoted by ID below where each item drives a research recommendation). Carry-forwards: D-05 tail-key order, D-06-2x stderr templates, D-07-04 `_HttpPostSink` stub depth, D-07-10 `-o/--post-url` mutex, D-08-01..15 sink Protocol + `_ValidatingSink` decorator (NOT used here per D-09-11), D-11 ten-section README lock, D-13 stdlib-only-at-runtime, T-PII-01 PII-safe stderr.

### Claude's Discretion (from CONTEXT.md)

- Exact regex for the four CI grep gates in D-09-18.
- `_HttpPostSink` internal storage of headers (`list[tuple[str,str]]` vs normalized `dict`).
- Whether `flush_and_post()` is a separate method or inlined in `__exit__`.
- Whether `_https_url` rejects userinfo (`https://user:pass@host`) — recommended yes.
- Test file naming/placement.
- Timeout test mechanism (real-socket sleep vs opener mock) — both acceptable.
- `--timeout` rejection shape (`type=_positive_float` vs post-parse `parser.error`).
- `args.header` default (`[]` vs `None`).
- `_log_http_failure` parameter naming.

### Deferred Ideas (OUT OF SCOPE)

`--retry N`, `--idempotency-key`, `$QUIZIFY_WEBHOOK_URL`/`--post-url-env`, NDJSON×`--post-url`, same-host redirect tolerance, OAuth flows, persistent retry queue, `--post-body-from-file`, argparse-level URL suppression, `_log_http_failure` extension to non-HTTP failures.
`</user_constraints>`

`<phase_requirements>`
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| AUTO-01 | `--post-url URL` single-shot POST of array body; mutex with `-o/--output` | D-09-10 buffer-and-POST shape; D-09-12 single `open()` call; Q1, Q2, Q5, Q10 below |
| AUTO-02 | `--post-url` requires `--validate`; argparse exit 2 on violation | D-09-13 post-parse `parser.error`; pre-`with sink:` batch validation timing (D-09-11) |
| AUTO-03 | Repeatable `--header "K: V"`; CRLF rejected at argparse | D-09-04 `_parse_header` callable; Q6 case-insensitive Content-Type override |
| AUTO-04 | `--timeout SECONDS` (default 30); timeout exits 3 with PII-safe stderr | D-09-12 timeout passed on every `open()`; Q3 timeout exception classification |
| AUTO-05 | HTTPS-only at argparse; `ssl.create_default_context()`; no cross-host redirects; CI grep gate | D-09-01 `_NoRedirectHandler`; D-09-02 explicit opener; Q1 (build_opener verified); Q8 ssl invariants |
| AUTO-06 | Non-2xx exit 3 + categorical stderr (status + class + body bytes); negative-substring T-PII-01 tests | D-09-07/08 locked vocabulary + format; D-09-17 `TestHTTPErrorPIIsafe`; Q2 body draining; Q10 request-count |
`</phase_requirements>`

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| HTTPS POST egress (single-shot, batch JSON-array body) | Sink layer (`_HttpPostSink`) | — | Sink Protocol is the established egress boundary (Phase 7/8) |
| Custom redirect rejection | `urllib` opener (`_NoRedirectHandler`) | — | Stdlib provides the override hook; subclassing `HTTPRedirectHandler` is the canonical pattern |
| Argparse-time URL/header/timeout validation | Argparse `type=` callables + post-parse `parser.error` | — | Phase 8 precedent (D-08-11); fails before any socket touched |
| Pre-egress schema validation (gate) | Existing batch `_run_schema_validation` | — | D-09-11: array-mode is batch; `_ValidatingSink` (per-row) NOT used |
| Categorical stderr | `_log_http_failure` helper (single path) | `logging.error` (configured by `configure_logging`) | D-09-07: single helper makes the CI grep gate enforceable |
| Exit-code mapping | `convert()` post-`with sink:` `if/elif` chain | `_HttpDeliveryError` sentinel exception | D-09-09: 1=validation, 2=argparse, 3=HTTP/network |

## Standard Stack

### Core (stdlib only — D-13)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `urllib.request` | stdlib (3.9+) | `Request`, `build_opener`, `HTTPSHandler`, `HTTPRedirectHandler` | Locked by D-13; `requests` would violate stdlib-only invariant |
| `urllib.error` | stdlib (3.9+) | `HTTPError`, `URLError` exception hierarchy | Required for classification (D-09-08 vocabulary) |
| `urllib.parse` | stdlib (3.9+) | `urlsplit` for `_https_url` callable | Cleaner than regex; consistent with stdlib URL semantics |
| `ssl` | stdlib (3.9+) | `create_default_context()` only | D-09-02 lock; D-09-18 grep gate forbids `_create_unverified_context` etc. |
| `socket` | stdlib (3.9+) | `socket.timeout` (TimeoutError alias 3.10+), `socket.gaierror`, `ConnectionRefusedError` discrimination | Required for `URLError.reason` isinstance branching |
| `re` | stdlib | `_HEADER_NAME_RE` for RFC 7230 token charset | Single regex; no library overhead |
| `json` | stdlib | `json.dumps(rows, ensure_ascii=False).encode("utf-8")` | Already used by `_StdoutSink`/`_FileSink`; identical encoding |
| `logging` | stdlib | `_log_http_failure` writes via `logging.error` | Existing `configure_logging` precedent (Phase 6 D-06-2x) |

### Test Stack (existing)

| Module | Purpose |
|--------|---------|
| `pytest` | Existing test runner |
| `http.server` (stdlib) | `HTTPServer` + `BaseHTTPRequestHandler` for the `mock_webhook` fixture (D-09-15) |
| `threading` (stdlib) | Daemon thread for `serve_forever()` |
| `pytest`'s `caplog` / `capsys` | Stderr capture for negative-substring suite |

**No new dependencies.** D-13 preserved. CI grep gate `! grep -E "^import requests|^from requests"` (D-09-18) verifies.

**Version verification:** `urllib.request.Request(method=...)` keyword has been available since Python 3.4 (per CPython release notes); supported on all 3.9+ targets. `socket.timeout` aliased to `TimeoutError` in Python 3.10+ (PEP 657 / 3.10 release notes). `ssl.create_default_context()` defaults verified locally on Python 3.10.19: `check_hostname=True`, `verify_mode=CERT_REQUIRED`, `minimum_version=TLSv1_2` — confirmed on the dev machine. No registry version-pinning needed (stdlib only).

## Architecture Patterns

### System Architecture Diagram

```
                                                  ┌─────────────────────────┐
                                                  │ argparse                │
                                                  │  type=_https_url        │  → exit 2 (categorical)
                                                  │  type=_parse_header     │
                                                  │  type=float / post-parse│
                                                  └────────────┬────────────┘
                                                               │ args (post_url, header, timeout, validate)
                                                               ▼
                                                  ┌─────────────────────────┐
                              CSV ──► iter_rows ─►│ list(stream)            │
                                                  │ + build_row             │
                                                  └────────────┬────────────┘
                                                               │ rows: list[dict]
                                                               ▼
                                                  ┌─────────────────────────┐
                                                  │ _run_schema_validation  │  → exit 1 (D-06-19/20)
                                                  │ (BATCH; pre-with-sink)  │
                                                  └────────────┬────────────┘
                                                               │ validated rows
                                                               ▼
                                            ┌──────────────────────────────────┐
                                            │ with _HttpPostSink(url,h,t):     │
                                            │     for row in rows:             │
                                            │         sink.write(row)          │
                                            │     # __exit__: flush_and_post() │
                                            └──────────────┬───────────────────┘
                                                           │ payload = json.dumps(rows)
                                                           ▼
                                            ┌──────────────────────────────────┐
                                            │ self._opener.open(req,           │
                                            │   timeout=self._timeout)         │
                                            │   • _NoRedirectHandler (3xx→err) │
                                            │   • HTTPSHandler(default ssl ctx)│
                                            └──────────────┬───────────────────┘
                                            ┌──────────────┴───────────────┐
                                       2xx  │                              │  HTTPError / URLError /
                                            ▼                              ▼  socket.timeout
                                       ┌────────┐               ┌──────────────────────┐
                                       │ return │               │ _log_http_failure(.) │ → exit 3
                                       └────────┘               │ raise _HttpDeliveryE │
                                                                └──────────────────────┘
```

### Pattern 1: Custom opener with `_NoRedirectHandler` first

**What:** `build_opener(_NoRedirectHandler(), HTTPSHandler(context=ssl.create_default_context()))` — order does NOT matter for correctness; `build_opener` handles ordering internally.

**Why this works (verified):** `urllib.request.build_opener()` (CPython 3.10 source, identical pattern through 3.9..3.13) iterates its `default_classes` list; when ANY user-supplied handler is a subclass of a default class, the default is **skipped**. `_NoRedirectHandler(urllib.request.HTTPRedirectHandler)` therefore replaces the default `HTTPRedirectHandler` cleanly — both are NOT installed. [VERIFIED: inspected `urllib.request.build_opener` source on Python 3.10.19; `default_classes` includes `HTTPRedirectHandler` and the skip-set logic uses `issubclass`.]

```python
# Source: CPython urllib/request.py build_opener (3.10.19, verified on dev machine)
# default_classes = [ProxyHandler, UnknownHandler, HTTPHandler, HTTPDefaultErrorHandler,
#                    HTTPRedirectHandler, FTPHandler, ...]
# for klass in default_classes:
#     for check in handlers:
#         if issubclass(check, klass): skip.add(klass)   # ← _NoRedirectHandler triggers this
```

### Pattern 2: `Request.has_header()` for case-insensitive Content-Type override

**What:** Use `Request.has_header("Content-Type")` (urllib normalizes header names to title-case internally) AFTER adding user headers, instead of pre-resolving the list with manual `name.lower()` checks.

**When to use:** D-09-05's case-insensitive Content-Type injection. The locked skeleton does an explicit `any(name.lower() == "content-type" for name, _ in resolved)` — that's correct but slightly redundant; `req.has_header("Content-Type")` is equivalent and matches urllib's own normalization. Either is fine; **the locked skeleton wins** for grep-clarity.

```python
# Source: locked skeleton (CONTEXT.md <specifics>) — RECOMMENDED VERBATIM
req = urllib.request.Request(self._url, data=payload, method="POST")
for name, value in resolved:        # resolved already filtered for Content-Type duplicate
    req.add_header(name, value)
```

### Pattern 3: `_NoRedirectHandler` fp-stream invariant

**What:** When `redirect_request` raises `HTTPError(req.full_url, code, "http_unexpected_redirect", headers, fp)`, the `fp` is a still-open response stream. Python's `HTTPError` is `addinfourl`-derived and inherits `__exit__`/`close()`; the `try: ... except HTTPError as err:` block in `_flush_and_post` should NEVER read `err.read()` (D-09-03 / Pitfall 17 / T-PII-01). The garbage collector closes the fp when the `HTTPError` instance is dropped; this is observable as a `ResourceWarning` only under `-W error::ResourceWarning`. Recommend: NEVER touch `err.read()`/`err.fp`; rely on `err.headers.get("Content-Length")` for the `body_bytes` field, falling back to `"-"` when absent.

```python
# Recommended err-handling shape (extends locked skeleton)
except urllib.error.HTTPError as err:
    cls = "3xx" if 300 <= err.code < 400 else "4xx" if 400 <= err.code < 500 else "5xx"
    reason = {"3xx": "http_unexpected_redirect",
              "4xx": "http_client_error",
              "5xx": "http_server_error"}[cls]
    cl = err.headers.get("Content-Length") if err.headers else None
    body_bytes = int(cl) if (cl is not None and cl.isdigit()) else None
    _log_http_failure(reason, status=err.code, reason_class=cls, body_bytes=body_bytes)
    # Best-effort close (suppress ResourceWarning under strict warnings):
    try: err.close()
    except Exception: pass
    raise _HttpDeliveryError(reason)
```

### Anti-Patterns to Avoid

- **`urlopen(req, timeout=...)` directly** — bypasses our custom opener; `_NoRedirectHandler` would not be installed and 3xx would be silently followed. D-09-02 lock: ALL traffic via `self._opener.open(...)`. CI grep gate (D-09-18) verifies exactly one `self._opener.open(` call site exists.
- **Reading `err.read()` for body content** — Pitfall 2 / Pitfall 17. Even "for the byte count" violates T-PII-01 because the bytes pass through Python memory and a future debug log line could surface them.
- **`requests` library** — D-13 violation; CI grep gate (D-09-18) blocks.
- **Per-row POST in a loop** — D-09-10 lock: single-shot batch. Pitfall 4 in research/PITFALLS.md (50k POSTs × 200ms = 2.7h).
- **`response.geturl() == request_url` redirect-detection idiom** — works but is a fallback; `_NoRedirectHandler` already turns redirects into `HTTPError` before `response.geturl()` is reachable. Skip the assert.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Redirect rejection | Manual `Location:` header parsing post-response | Subclass `HTTPRedirectHandler.redirect_request` → raise | Stdlib hooks into the opener BEFORE the redirect is followed; manual approach is racy |
| Case-insensitive header dedup | Lowercase-then-compare loop | `Request.has_header(name)` (urllib normalizes internally) | One method call vs four lines; matches urllib's own internal logic |
| URL parsing for HTTPS gate | `s.startswith("https://")` | `urllib.parse.urlsplit(s).scheme == "https"` AND `parts.netloc` | Catches `https://` (no host) and userinfo edge cases |
| Header name validation | Hand-rolled char loop | RFC 7230 token regex `[!#$%&'*+\-.^_`|~0-9A-Za-z]+` | Locked in D-09-04 specifics; covered by jsonschema-precedent for charset definitions |
| Timeout enforcement | `signal.alarm(timeout)` wrapper | `urlopen(timeout=...)` / `opener.open(timeout=...)` | Stdlib threads timeout into the socket; portable to Windows |
| Mock HTTP server | `unittest.mock.patch` on `urlopen` | `http.server.HTTPServer` real socket | "Exactly one request, no retry" can ONLY be proven on a real socket counting handler invocations (Pitfall 16 carry-forward) |

**Key insight:** Every problem in the AUTO-01 surface has a stdlib hook. Hand-rolling any of them either weakens security (manual redirect handling) or weakens test honesty (mocked sockets can't prove no-retry).

## Runtime State Inventory

> Phase 9 is greenfield (new feature) — not a rename/refactor/migration. **Section omitted.**

## Common Pitfalls

### Pitfall 1: `urlopen` global-default timeout (Pitfall 1 carry-forward)

**What goes wrong:** `urlopen(req)` without `timeout=` blocks forever (`socket._GLOBAL_DEFAULT_TIMEOUT` is `None`).

**How to avoid:** D-09-12 lock: `self._opener.open(req, timeout=self._timeout)`. CI grep gate (D-09-18) asserts exactly one `self._opener.open(` callsite — making "is timeout passed" auditable by inspection.

### Pitfall 2: Daemon-thread leak in mock-server fixture

**What goes wrong:** `serve_forever()` daemon thread survives test teardown; `_HandlerHang`'s `time.sleep(...)` keeps a handler in-flight; `server.shutdown()` blocks on the in-flight handler. Subsequent tests see port-bind failures or stderr noise from the leaked thread.

**Why it happens:** `HTTPServer.shutdown()` waits for `serve_forever`'s loop iteration to complete, which waits for the current handler. A `time.sleep(60)` handler blocks shutdown for 60s.

**How to avoid:**
- **`server.socket.settimeout(0.5)` BEFORE `serve_forever()`** so accept loop polls; OR
- **`server.shutdown()` then `server.server_close()`** in fixture teardown; AND
- For the timeout test specifically: `_HandlerHang` should sleep for `timeout + 0.5s` (not infinite); tests use `--timeout 0.5` (or sink-timeout 0.5) so the test itself takes ~0.5s; client gets `socket.timeout` first, server's `time.sleep(1)` then completes naturally and `shutdown()` returns.
- pytest-timeout plugin if available; otherwise `threading.Timer(5.0, server.socket.close)` as a watchdog.

**Warning signs:** Test suite hangs at the timeout test; `lsof -i :PORT` shows leaked listener.

### Pitfall 3: `urlsplit("https://").scheme` returns `"https"` but netloc is empty

**Verified:** `urllib.parse.urlsplit("https://")` returns `SplitResult(scheme='https', netloc='', path='', ...)`. The locked `_https_url` check `parts.scheme != "https" or not parts.netloc` correctly rejects this. [VERIFIED: stdlib behavior consistent 3.9–3.13.]

### Pitfall 4: Case-insensitive header injection vs urllib's internal normalization

**What:** `Request.add_header("content-type", "...")` — urllib stores it title-cased internally as `Content-Type`. Subsequent `req.has_header("content-type")` returns True (it lowercases the lookup). The locked skeleton's `name.lower() == "content-type"` pre-check is correct AND matches urllib semantics. No action needed beyond keeping the lock.

### Pitfall 5: `socket.timeout` vs `TimeoutError` (Python 3.10+ alias)

**What:** Python 3.10 made `socket.timeout` an alias for the builtin `TimeoutError` (PEP 657-adjacent change). For 3.9–3.13 catch shape:

```python
except socket.timeout:        # Works on all 3.9+ — alias still exists
    _log_http_failure("network_timeout")
```

**Why safe:** On 3.10+, `socket.timeout is TimeoutError`, so the except clause catches `TimeoutError` too. On 3.9, `socket.timeout` is its own subclass of `OSError`. Either way, this clause runs first (before the broader `URLError`) and routes correctly.

**Important:** `urlopen(timeout=...)` raises `socket.timeout` (NOT wrapped in `URLError`) when the timeout fires during `recv`. It IS wrapped in `URLError` if the timeout fires during connect on some platforms. Recommend the catch order:

```python
except socket.timeout:                       # bare timeout
    ...
except urllib.error.HTTPError as err:        # 3xx via _NoRedirectHandler / 4xx / 5xx
    ...
except urllib.error.URLError as err:         # everything else; classify err.reason
    if isinstance(err.reason, socket.timeout):       # connect-time timeout on some platforms
        reason = "network_timeout"
    elif isinstance(err.reason, ssl.SSLError):
        reason = "tls_error"
    elif isinstance(err.reason, ConnectionRefusedError):
        reason = "connection_refused"
    elif isinstance(err.reason, socket.gaierror):
        reason = "dns_error"
    else:
        reason = "network_error"
    _log_http_failure(reason)
    raise _HttpDeliveryError(reason)
```

**Order matters:** `HTTPError` is a subclass of `URLError`, so `HTTPError` MUST be caught first. `socket.timeout` MUST be caught before `URLError` because some platforms wrap it and some don't — bare clause first catches both shapes.

### Pitfall 6: Argparse URL leak surface (D-09-14 accepted)

**What:** `argparse.ArgumentTypeError("post_url_https_required")` produces:
```
error: argument --post-url: invalid _https_url value: 'http://evil.example/x'
```

**Decision (locked D-09-14):** Accept. The leak is bounded to one stderr line at argparse-level, BEFORE any `_log_http_failure` path runs. Future hardening (override `parser.error`) deferred. Recommend: rename the type-callable from `_https_url` to a name that reads cleaner in the error message — e.g., `https_post_url` so the message reads `invalid https_post_url value: ...`. **Trivial improvement, not blocking.**

### Pitfall 7: `_NoRedirectHandler` 302 → request count discipline

**What:** When the mock server returns 302, the request DID reach the handler exactly once (handler counts `len(received) == 1`). `_NoRedirectHandler.redirect_request` runs **client-side** AFTER receiving the 302; it raises before any second request fires. So:

- 200 happy path: `assert len(received) == 1`
- 302 reject: `assert len(received) == 1` (NOT 0 — the original POST was received and 302'd)
- Validation-fails-pre-egress: `assert len(received) == 0`
- Timeout: `assert len(received) == 1` (server got the request, just never finished responding)
- 502: `assert len(received) == 1`

This **is** the AUTO-06 SC#1 "no retry" assertion. If a future bug introduced a retry handler, `len(received)` would be 2.

### Pitfall 8: Pitfall 16/17 carry-forward (PITFALLS.md)

- **Pitfall 16:** Integration via real `http.server` is the justified exception to "tests at unit level"; D-09-15/16 lock this.
- **Pitfall 17:** `HTTPError.__str__` includes the URL → `_log_http_failure` builds the format string itself; never `str(err)`, never `err.url`, never `err.read()`.

### Pitfall 9: `BaseHTTPRequestHandler.log_message` stderr pollution

**What:** Default handler logs every request to stderr (`127.0.0.1 - - [date] "POST / HTTP/1.0" 200 -`). Pollutes pytest's `capsys`/`caplog` and could confuse the negative-substring suite (the request-line itself contains the test URL).

**How to avoid:** `def log_message(self, *a, **kw): pass` on the test handler base class (locked in D-09-15 fixture skeleton). Verify by running fixture in isolation and confirming clean stderr.

### Pitfall 10: `allow_reuse_address` for port flake under fast pytest reruns

**What:** `HTTPServer` defaults to `allow_reuse_address = 0` on some platforms; rapid teardown/setup cycles (parametrized tests) hit `OSError: [Errno 98] Address already in use` even on port 0 (TIME_WAIT lingering accepts on the OS-assigned port).

**How to avoid:**
```python
class _ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True
```
Use this in the fixture. Port 0 + reuse_address gives best test resilience.

## Code Examples

### `_log_http_failure` (locked verbatim — D-09-07 skeleton)

```python
# Source: CONTEXT.md <specifics>; T-PII-01 negative-substring suite verifies
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

### `_NoRedirectHandler` (locked verbatim — D-09-01)

```python
# Source: CONTEXT.md <specifics>
class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # AUTO-05: reject ALL redirects; original URL only (T-PII-01)
        raise urllib.error.HTTPError(
            req.full_url, code, "http_unexpected_redirect", headers, fp,
        )
```

### Mock-server fixture (refined from D-09-15 skeleton)

```python
# Source: CONTEXT.md <specifics>, refined per Pitfalls 2/9/10 above
import http.server, threading, pytest

class _ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

class _BaseHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        self.server.received.append(("POST", self.rfile.read(n)))
        self._respond()
    def log_message(self, *a, **kw): pass  # silence stderr (Pitfall 9)

@pytest.fixture
def mock_webhook():
    servers = []
    def factory(respond_fn):
        klass = type("H", (_BaseHandler,), {"_respond": respond_fn})
        server = _ReusableHTTPServer(("127.0.0.1", 0), klass)
        server.received = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        url = f"http://127.0.0.1:{server.server_address[1]}"
        return url, server.received, server
    yield factory
    for server, thread in servers:
        server.shutdown()       # waits for handler-in-flight to finish
        server.server_close()   # releases the listening socket
        thread.join(timeout=2.0)
```

### Per-handler response factories

```python
def _respond_200(handler):
    handler.send_response(200); handler.end_headers()
    handler.wfile.write(b"server_response_marker")  # T-PII-01 negative-substring sentinel

def _respond_502(handler):
    handler.send_response(502); handler.send_header("Content-Length", "13"); handler.end_headers()
    handler.wfile.write(b"Bad Gateway!!")  # 13 bytes — exact for body_bytes assertion

def _respond_302(handler):
    handler.send_response(302)
    handler.send_header("Location", "http://other.example.test/x")
    handler.end_headers()

def _respond_hang(handler):
    import time
    time.sleep(2.0)  # > test --timeout 0.5; client times out, then handler returns naturally
    handler.send_response(200); handler.end_headers()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `urllib2.urlopen` (Py2) | `urllib.request.urlopen` (Py3) | Python 3.0 | N/A (Py3-only project) |
| `socket.timeout` exception | Aliased to `TimeoutError` | Python 3.10 | Catch `socket.timeout` works on both old and new |
| `Request(url, data, headers, method=...)` keyword | Same | Python 3.4 | `method="POST"` keyword always available on 3.9+ |
| `requests` library third-party | stdlib `urllib.request` | N/A | D-13 forces stdlib; no migration |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | All Phase 9 code | ✓ (3.10.19 on dev box) | 3.10.19 | — |
| stdlib `urllib`/`ssl`/`socket`/`http.server` | runtime + tests | ✓ | bundled | — |
| pytest | tests | ✓ (project standard) | per project | — |
| `fastjsonschema` (optional `[validate]` extra) | `_run_schema_validation` (pre-egress gate) | ✓ when installed; tests use the standard fixture | per project | — |

**No missing dependencies.** All Phase 9 surfaces are stdlib-only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_http_post.py tests/test_argparse_post_url.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTO-01 | Happy-path POST: 42-row sample → mock 200 → 1 request, body == golden array bytes | integration | `pytest tests/test_http_post.py::test_happy_path_one_request -x` | ❌ Wave 0 |
| AUTO-01 | Mutex: `--post-url` + `-o` rejected at argparse | unit | `pytest tests/test_argparse_post_url.py::test_post_url_output_mutex -x` | ✅ (Phase 7) |
| AUTO-02 | `--post-url` without `--validate` → exit 2 | unit | `pytest tests/test_argparse_post_url.py::test_post_url_requires_validate -x` | ❌ Wave 0 |
| AUTO-02 | Validation-fails-pre-egress → 0 requests, exit 1 | integration | `pytest tests/test_http_post.py::test_invalid_payload_zero_requests -x` | ❌ Wave 0 |
| AUTO-03 | `--header "K: V"` accepted, sent on wire | integration | `pytest tests/test_http_post.py::test_header_added -x` | ❌ Wave 0 |
| AUTO-03 | CRLF in `--header` value rejected at argparse | unit | `pytest tests/test_argparse_post_url.py::test_header_crlf_rejected -x` | ❌ Wave 0 |
| AUTO-03 | Missing colon, empty name, invalid chars rejected | unit | `pytest tests/test_argparse_post_url.py::test_header_malformed_rejected -x` | ❌ Wave 0 |
| AUTO-03 | User Content-Type override wins | integration | `pytest tests/test_http_post.py::test_user_content_type_wins -x` | ❌ Wave 0 |
| AUTO-04 | `--timeout` invalid (≤0) rejected | unit | `pytest tests/test_argparse_post_url.py::test_timeout_invalid -x` | ❌ Wave 0 |
| AUTO-04 | Hung server → exit 3, `network_timeout` reason, exactly 1 request reached server | integration | `pytest tests/test_http_post.py::test_timeout_one_request -x` | ❌ Wave 0 |
| AUTO-05 | `http://` URL rejected at argparse | unit | `pytest tests/test_argparse_post_url.py::test_http_rejected -x` | ❌ Wave 0 |
| AUTO-05 | URL without netloc rejected | unit | `pytest tests/test_argparse_post_url.py::test_https_no_netloc_rejected -x` | ❌ Wave 0 |
| AUTO-05 | 302 → exit 3, `http_unexpected_redirect`, target URL not in stderr | integration | `pytest tests/test_http_post.py::test_redirect_rejected -x` | ❌ Wave 0 |
| AUTO-05 | Grep gate: no `CERT_NONE`/`_create_unverified_context`/`verify=False` | unit (grep) | `pytest tests/test_security_grep_gates.py::test_no_cert_disabling -x` | ❌ Wave 0 |
| AUTO-05 | Grep gate: exactly one `ssl.create_default_context()` | unit (grep) | `pytest tests/test_security_grep_gates.py::test_one_default_ssl_context -x` | ❌ Wave 0 |
| AUTO-05 | Grep gate: exactly one `self._opener.open(` | unit (grep) | `pytest tests/test_security_grep_gates.py::test_one_opener_open_callsite -x` | ❌ Wave 0 |
| AUTO-05 | Grep gate: no `import requests` | unit (grep) | `pytest tests/test_security_grep_gates.py::test_no_requests_lib -x` | ❌ Wave 0 |
| AUTO-06 | 502 → exit 3, body_bytes=13, status=502, reason_class=4xx/5xx | integration | `pytest tests/test_http_post.py::test_502_exit_3 -x` | ❌ Wave 0 |
| AUTO-06 | 4xx → exit 3, status + class only | integration | `pytest tests/test_http_post.py::test_4xx_exit_3 -x` | ❌ Wave 0 |
| AUTO-06 | T-PII-01 negative-substring: no PII tokens / no `server_response_marker` in stderr after 502/302/timeout/4xx | integration | `pytest tests/test_http_post_pii.py -x` | ❌ Wave 0 |
| AUTO-06 | D-13: only stdlib imports added | unit (grep) | `pytest tests/test_security_grep_gates.py::test_no_requests_lib -x` (same as AUTO-05) | (same) |
| Carry | TRAIL-03 byte-identity stays green | regression | `pytest tests/test_byte_identity.py -x` | ✅ (existing) |
| Carry | D-11 README ten-section drift | regression | `pytest tests/test_readme_help_alignment.py -x` | ✅ (existing) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_http_post.py tests/test_argparse_post_url.py tests/test_http_post_pii.py tests/test_security_grep_gates.py -x` (~3-5s)
- **Per wave merge:** `pytest -x` (full suite; ~10-15s incl. integration)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — extend with `mock_webhook` fixture + `_ReusableHTTPServer` + 4 response factories (`_respond_200`, `_respond_502`, `_respond_302`, `_respond_hang`)
- [ ] `tests/test_http_post.py` — happy path, request count, 502, 302, timeout, validation-pre-egress, header-on-wire, user-Content-Type-wins
- [ ] `tests/test_http_post_pii.py` — `TestHTTPErrorPIIsafe` negative-substring suite (mirrors Phase 6 `TestValidationFailurePIIsafe`)
- [ ] `tests/test_argparse_post_url.py` — pure-unit argparse rejections (HTTPS gate, --validate dependency, header CRLF/malformed, --timeout invalid)
- [ ] `tests/test_security_grep_gates.py` — four CI grep gates (D-09-18) + extension grep that `Request(method="POST")` appears exactly once

## Security Domain

> `security_enforcement` is enabled (default). Phase 9 introduces an HTTP egress surface — required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes (operator-supplied via `--header "Authorization: Bearer ..."`) | Header values never logged (T-PII-01) |
| V3 Session Management | no | Single-shot POST; no session |
| V4 Access Control | no | Operator-controlled CLI |
| V5 Input Validation | yes | `_https_url`, `_parse_header`, `_positive_float` argparse callables; `_run_schema_validation` pre-egress |
| V6 Cryptography | yes | `ssl.create_default_context()` (TLS 1.2 minimum on Py3.10+; verified on dev box) — never hand-rolled |
| V9 Communications | yes | HTTPS-only argparse gate; CI grep gate on `CERT_NONE`/`verify=False`; `_NoRedirectHandler` rejects all 3xx |
| V10 Malicious Code | no | Stdlib only |
| V14 Configuration | yes | D-09-18 grep gates lock against future weakening |

### Known Threat Patterns for stdlib-Python HTTP egress

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Header injection via CRLF in `--header "Foo: bar\r\nX-Inject: ..."` | Tampering | `_parse_header` rejects CRLF (D-09-04 → `header_crlf_rejected`) |
| MITM via disabled TLS verification | Information Disclosure | `ssl.create_default_context()` (default verify_mode=CERT_REQUIRED, check_hostname=True); CI grep gate (D-09-18) |
| PII leak via response-body echo in stderr | Information Disclosure | `_log_http_failure` is sole stderr path; never reads `err.read()`; `TestHTTPErrorPIIsafe` negative-substring tests |
| PII delivered to wrong host via silent redirect | Information Disclosure | `_NoRedirectHandler` rejects ALL 3xx; target URL never reaches log path |
| PII leak via URL on command line / `ps aux` | Information Disclosure | OUT OF SCOPE for Phase 9 (deferred `--post-url-env`); D-09-14 documents argparse-error URL appearance as accepted |
| Schema-invalid PII payload sent to webhook | Information Disclosure | `--post-url` requires `--validate` (D-09-13); `_run_schema_validation` runs BEFORE `with sink:` (D-09-11) |
| Retry duplicates webhook deliveries / amplifies leak | Repudiation | No retry in v1.2 (D-09-12 single `open()` call; CI grep gate verifies one callsite) |
| Authentication bypass via untrusted `Authorization` header | Tampering | Operator-controlled; out of scope (header values never logged either way) |

## Per-Question Implementation Recommendations

### Q1. `HTTPRedirectHandler` ordering

**Verified (CPython 3.10.19 source):** `build_opener(*handlers)` skips any default class for which a user-supplied handler is a subclass (uses `issubclass` check). `_NoRedirectHandler(HTTPRedirectHandler)` therefore **replaces** the default redirect handler — both are NOT installed. Argument order to `build_opener` is irrelevant.

**Recommendation:** Locked skeleton verbatim. No further action.

### Q2. `HTTPError` body draining + `body_bytes` extraction

**Recommendation:**
- **Never call `err.read()`** (T-PII-01 / Pitfall 17).
- For `body_bytes` field: `cl = err.headers.get("Content-Length") if err.headers else None; body_bytes = int(cl) if cl and cl.isdigit() else None`. Pass `None` → `_log_http_failure` renders `-`.
- Best-effort `err.close()` in a `try/except: pass` after logging (suppresses `ResourceWarning` under `-W error::ResourceWarning`; not strictly required for tests but tidy).
- For 3xx via `_NoRedirectHandler`: the `fp` carries no `Content-Length` typically (it's the redirect-response). `body_bytes = None` → `-` is the expected line shape for redirect cases.
- Make.com 502s typically include `Content-Length`; tests use a fixed-13-byte body to lock the assertion.

### Q3. `socket.timeout` vs `URLError` across Python versions

**Recommendation:** Catch `socket.timeout` BEFORE `URLError`. On 3.10+ this also catches `TimeoutError` (alias). On all platforms, also classify `URLError.reason` for the connect-time-timeout edge case. Locked catch order in Pattern 3 above.

### Q4. `URLError.reason` classification

**Recommendation (locked order — most-specific first):**
1. `isinstance(err.reason, socket.timeout)` → `network_timeout` (handles connect-time wrapping)
2. `isinstance(err.reason, ssl.SSLError)` → `tls_error` (also catches `SSLCertVerificationError`, which is `SSLError`-subclass)
3. `isinstance(err.reason, ConnectionRefusedError)` → `connection_refused`
4. `isinstance(err.reason, socket.gaierror)` → `dns_error`
5. else → `network_error`

**Cross-platform note:** On Windows, `socket.gaierror` and `ConnectionRefusedError` are still raised through `URLError.reason` (they're `OSError` subclasses; `WinError` codes are mapped automatically by Python's socket layer to standard exception classes). `isinstance` checks remain reliable.

### Q5. `http.server.HTTPServer` test fixture lifecycle

**Recommendation (locked above in Code Examples):**
- `_ReusableHTTPServer(allow_reuse_address=True)` to avoid TIME_WAIT flake.
- `serve_forever()` in daemon thread.
- Sequential (not `ThreadingMixIn`); "exactly one request" tests benefit from sequential semantics.
- `log_message` overridden to `pass` (Pitfall 9).
- Teardown: `server.shutdown()` then `server.server_close()`, then `thread.join(timeout=2.0)`.
- Hung-handler safeguard: `_HandlerHang` sleeps for `timeout + 1.5s`, NOT infinite — this lets `shutdown()` return cleanly.

### Q6. `Request.add_header` case-insensitive Content-Type

**Recommendation:** Locked skeleton's `any(name.lower() == "content-type" for name, _ in resolved)` is correct. Equivalent to `req.has_header("Content-Type")` AFTER all user headers are added; both are fine. Keep the locked skeleton verbatim — it's slightly more grep-friendly.

### Q7. Argparse URL leak

**Recommendation:** Accept (D-09-14 lock). Optional polish: rename type-callable `_https_url` → `https_post_url` so the argparse error reads `invalid https_post_url value: '...'` instead of `invalid _https_url value: '...'`. Minor UX win; planner's call.

### Q8. `ssl.create_default_context()` invariants

**Verified locally on Python 3.10.19:**
- `check_hostname=True` ✓
- `verify_mode=CERT_REQUIRED` ✓
- `minimum_version=TLSv1_2` ✓ (CPython default since 3.10; relevant CPython release notes confirm)

**Recommendation:** **Do NOT explicitly set `minimum_version=TLSv1_2`.** The default is already TLS 1.2 on 3.10+; explicit setting just adds noise + a future-deprecation footgun (when 1.3-min becomes default, our explicit-1.2 line would weaken the floor). Trust the stdlib default.

**Environment overrides:** `SSL_CERT_FILE` / `SSL_CERT_DIR` env vars affect the default trust store. Acceptable — operator can point at internal CA bundle for staging webhooks. T-PII-01 not affected.

### Q9. Phase-9-specific pitfalls

Documented above (Pitfalls 1–10). Highlights beyond carry-forward:
- **Pitfall 2:** Daemon-thread leak → `_HandlerHang` finite sleep + `server.shutdown()`/`server_close()` discipline.
- **Pitfall 7:** 302 test → `len(received) == 1` (NOT 0).
- **Pitfall 10:** `allow_reuse_address = True` for port flake.
- **Encoding:** `json.dumps(..., ensure_ascii=False).encode("utf-8")` on the wire is fine; Make.com webhooks accept non-ASCII bytes (the existing file output path has been emitting non-ASCII for v1.0/v1.1).
- **Stderr capture:** Use **`caplog`** (not `capsys`) for the negative-substring suite. `_log_http_failure` writes via `logging.error` → `caplog.text` is the canonical capture surface and is decoupled from `sys.stderr` redirection. `capsys` works too but only if `configure_logging` routes to a `StreamHandler(sys.stderr)`. Locking on `caplog` is more robust.

### Q10. "Exactly one request, no retry" assertion

**Recommendation:** `assert len(received) == 1` after every failure-mode test EXCEPT `validation-fails-pre-egress` (which asserts `len(received) == 0`). The 302 path: `len(received) == 1` because the original POST IS received by the server before the 302 is returned; `_NoRedirectHandler` raises client-side after seeing the 302, so no follow-up request fires. Confirmed by inspection of `urllib.request.HTTPRedirectHandler.http_error_302` — it calls `self.parent.open(new)` only if `redirect_request` returns a new Request; raising from `redirect_request` short-circuits.

**Test architecture for 302:**
```python
def test_redirect_rejected(mock_webhook, caplog):
    url, received, server = mock_webhook(_respond_302)
    rc = convert(post_url=url, validate=True, ...)  # bypasses argparse HTTPS gate
    assert rc == 3
    assert len(received) == 1                       # one POST received, then 302'd
    assert "http_unexpected_redirect" in caplog.text
    assert "other.example.test" not in caplog.text  # target URL never logged (T-PII-01)
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python 3.10+ aliases `socket.timeout` to `TimeoutError` | Q3, Pitfall 5 | LOW — verified by CPython 3.10 release notes; if wrong, locked catch order still works (catches both shapes either way) |
| A2 | `URLError.reason` `isinstance` checks reliable across Linux/macOS/Windows for `gaierror`/`ConnectionRefusedError`/`SSLError` | Q4 | LOW — these are `OSError` subclasses raised directly by Python's socket layer; cross-platform behavior is well-documented stdlib |
| A3 | Make.com webhooks return `Content-Length` on 5xx error bodies | Pattern 3, Pitfall, AUTO-06 test fixtures | NONE for production — fallback to `body_bytes=None`/`-` is graceful. For the test fixture, `_respond_502` writes a known fixed-byte body so `body_bytes=13` is asserted exactly |
| A4 | `_NoRedirectHandler.redirect_request` raising prevents follow-up request | Q10, Pitfall 7 | LOW — verified by reading `HTTPRedirectHandler.http_error_302` source; raise from `redirect_request` propagates up through `OpenerDirector.open` |
| A5 | `argparse.ArgumentTypeError` message format includes the offending value | Q7, D-09-14 | NONE — well-documented argparse behavior; the lock just accepts it |

If A1 or A2 turns out wrong on some target platform, the runtime symptom is "exit 3 with `network_error` reason instead of `tls_error`/`dns_error`/etc." — categorical-but-less-specific. Not a security-affecting failure.

## Open Questions

1. **Should the planner add a fifth grep gate for `Request(method="POST")` count == 1?**
   - What we know: D-09-18 enumerates four grep gates.
   - What's unclear: A regression where a developer adds a second POST callsite (e.g., for retry) would be caught by the existing `self._opener.open(` count==1 gate. Adding a `Request(method="POST")` count==1 gate is duplicative but cheap.
   - Recommendation: ADD as a fifth gate. ~1 line of test code; locks the "single-shot" structural invariant from another angle.

2. **Should `_HandlerHang` sleep for `timeout + N` or use `socket.shutdown()` to force-close?**
   - What we know: D-09 doesn't mandate either.
   - What's unclear: Real-socket sleep is more honest but adds wall-clock to test suite. Force-closing the socket simulates a network drop, not a timeout.
   - Recommendation: Real-socket sleep with **`--timeout 0.5` + sleep 1.5s** = ~0.5s per timeout test. Acceptable.

3. **Should the negative-substring suite test ALL 8 reasons or sample?**
   - What we know: D-09-17 says "mirrors Phase 6's `TestValidationFailurePIIsafe`."
   - What's unclear: How many reason-codes need their own PII test.
   - Recommendation: Test the four most-likely-PII-leak paths: `http_unexpected_redirect` (target URL leak risk), `http_client_error` (response body leak risk), `http_server_error` (response body leak risk), `network_timeout` (no obvious PII surface but locks the categorical-only contract). The other four (`tls_error`, `dns_error`, `connection_refused`, `network_error`) share the same `_log_http_failure` path; one parameterized test covering all four is sufficient.

## Sources

### Primary (HIGH confidence)
- CPython 3.10.19 `urllib.request.build_opener` source — verified locally; default-class skip via `issubclass` confirmed.
- CPython 3.10.19 `ssl.create_default_context()` — verified locally: `check_hostname=True`, `verify_mode=CERT_REQUIRED`, `minimum_version=TLSv1_2`.
- `.planning/phases/09-auto-01-http-post-delivery/09-CONTEXT.md` — D-09-01..18 + locked skeletons (in-repo SoT).
- `.planning/REQUIREMENTS.md` AUTO-01..06 — verbatim.
- `.planning/ROADMAP.md` Phase 9 — six success criteria.
- `.planning/research/PITFALLS.md` Pitfalls 1–5, 13–15, 16, 17 — v1.2 carry-forward.
- `.planning/PROJECT.md` — D-05, D-11, D-13, T-PII-01.
- `.planning/phases/07-refactor-scaffolding-no-op/07-CONTEXT.md` — D-07-04 stub depth, D-07-10 mutex.
- `.planning/phases/08-stream-01-ndjson-output/08-CONTEXT.md` — sink Protocol, post-parse `parser.error` precedent.
- Existing `quizify_csv_ingest.py:97` `_HttpPostSink` stub; `:198` `_select_sink`; `:781-787` argparse post-parse pattern.

### Secondary (MEDIUM confidence)
- Python release notes for 3.10 (`socket.timeout` → `TimeoutError` alias) — well-documented.
- Make.com webhook content-type/idempotency assumptions — inferred from existing v1.0/v1.1 production traffic notes; flagged in research/PITFALLS.md as MEDIUM.

### Tertiary (LOW confidence)
- None — all critical claims verified.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, all behaviors verified locally.
- Architecture: HIGH — every decision traces to a locked D-09-NN or carry-forward.
- Pitfalls: HIGH — Pitfalls 1–5, 13–15 are documented carry-forwards; Pitfalls 6–10 here are stdlib-test-fixture mechanics that the orchestrator's question list flagged.
- Test fixture: HIGH — `mock_webhook` skeleton in CONTEXT.md is sound; refinements (`allow_reuse_address`, `server_close()`, finite sleep) are pure stdlib hygiene.
- Cross-version (3.9/3.10/3.11/3.12/3.13): HIGH for the locked catch order; LOW-risk where any divergence would degrade categorical-stderr granularity, not security or T-PII-01.

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (30 days — stdlib surfaces are very stable)

## RESEARCH COMPLETE
