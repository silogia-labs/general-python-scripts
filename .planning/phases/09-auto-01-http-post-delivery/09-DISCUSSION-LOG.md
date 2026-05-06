# Phase 9: AUTO-01 HTTP POST Delivery - Discussion Log

> **Audit trail only.** Decisions are captured in CONTEXT.md.

**Date:** 2026-05-05
**Phase:** 09-auto-01-http-post-delivery
**Areas discussed:** Redirect handling, Header parsing & CRLF rejection, Stderr templates & exit codes, Mock-server test approach

---

## Redirect handling

| Option | Description | Selected |
|--------|-------------|----------|
| Reject ALL redirects via custom `_NoRedirectHandler` | Subclass `HTTPRedirectHandler.redirect_request` to raise `HTTPError` for any 3xx; categorical reason `http_unexpected_redirect`. | ✓ |
| Allow same-host only | Parse `newurl`, compare host/scheme. Tolerates legitimate same-origin redirects but adds edge-case logic. | |
| `max_redirects=0` | Less explicit; resulting error class doesn't distinguish "any redirect" from "too many". | |

**User's choice:** Reject ALL redirects.
**Notes:** `req.full_url` (original URL) flows into `HTTPError`; redirect target URL never enters the error chain (T-PII-01 invariant).

---

## Header parsing & CRLF rejection

| Option | Description | Selected |
|--------|-------------|----------|
| argparse `type=_parse_header` + `action='append'` | Validation in custom callable; argparse exits 2 on `ArgumentTypeError`. Stored as `list[tuple[str, str]]`. | ✓ |
| `action='append'` + post-parse validation | Raw strings stored; validate later. Less idiomatic. | |
| Custom `argparse.Action` subclass | Most explicit but verbose. | |

**User's choice:** `type=_parse_header` callable.
**Follow-up — Content-Type precedence:** User-supplied Content-Type wins (case-insensitive name match); sink injects `application/json` only if absent.

---

## Stderr templates & exit codes

| Option | Description | Selected |
|--------|-------------|----------|
| Single helper `_log_http_failure(reason, **kwargs)` with key=value categorical format | One function, fixed reason vocabulary, all four keys always present (use `-` for unknown). Greppable, PII-safe by construction. Exit 3 always. | ✓ |
| Three independent `logging.error` calls per failure class | Flexible but drift-prone; each path needs its own PII audit. | |
| JSON-line stderr | Machine-parseable but inconsistent with Phase 6's plain-text D-06-2x stderr. | |

**User's choice:** Single helper, key=value.
**Notes:** Locked vocabulary of 8 reasons (`network_timeout`, `http_unexpected_redirect`, `http_client_error`, `http_server_error`, `tls_error`, `dns_error`, `connection_refused`, `network_error`). Exit codes: 1 = validation, 2 = argparse, 3 = HTTP/network.

---

## Mock-server test approach

| Option | Description | Selected |
|--------|-------------|----------|
| Stdlib `http.server.HTTPServer` per-test on `127.0.0.1:0` | Real socket; only way to prove "exactly one request, no retry" (AUTO-06 SC#1). Stdlib-only; tests bypass argparse HTTPS gate by calling `_HttpPostSink` directly. | ✓ |
| `unittest.mock.patch('OpenerDirector.open')` | Faster, no socket. Misses real `_NoRedirectHandler`/`HTTPSHandler` chain. | |
| Mix: mock for unit, http.server for integration | Hybrid; more code surface. | |

**User's choice:** Stdlib `http.server` per-test fixture.
**Notes:** Argparse HTTPS-only rejection gets its own pure-unit test that doesn't hit the network. PII-safe negative-substring suite (`TestHTTPErrorPIIsafe`) mirrors Phase 6's `TestValidationFailurePIIsafe` shape and asserts response-body-marker bytes never reach stderr.

---

## Claude's Discretion

- Exact CI grep gate regex (four invariants: no `CERT_NONE`/`_create_unverified_context`/`verify=False`; exactly 1 `ssl.create_default_context()`; exactly 1 `self._opener.open(`; no `requests` import).
- Whether `_HttpPostSink` stores headers as list-of-tuples or normalized dict.
- Whether `_https_url` validator also rejects `userinfo@` URLs.
- Test file naming and split.
- Timeout test mechanism (real `time.sleep` in handler vs mocked socket.timeout).
- Whether to suppress argparse's default URL reproduction in `parser.error` output.

## Deferred Ideas

- `--retry N` exponential backoff (v1.3+).
- `--idempotency-key` (v1.3+).
- `$QUIZIFY_WEBHOOK_URL` / `--post-url-env` (defer until operator pain).
- NDJSON × `--post-url` cross-product (v1.3+).
- OAuth / built-in auth flows (out of scope; `--header "Authorization: ..."` covers it).
- Persistent retry queue / multi-URL fan-out (out of scope).
- Argparse-level URL suppression (default behavior accepted; runtime PII-safe path is what T-PII-01 actually constrains).
- `_log_http_failure` extension to non-HTTP failures (Phase 9 helper is HTTP-only).
