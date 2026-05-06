# Phase 9: AUTO-01 HTTP POST Delivery — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 5 (1 EDIT prod, 1 EDIT docs, 3+ NEW tests + conftest extension)
**Analogs found:** 5 / 5 (every new surface has a near-exact in-repo analog)

## File Classification

| File | Action | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (`_HttpPostSink`) | EDIT (replace stub body) | sink (egress) | batch buffer-and-POST (single-shot) | `_FileSink` (lines 74–94) | exact (buffer shape) + delta (urlopen instead of `json.dump` to fp) |
| `quizify_csv_ingest.py` (`_NoRedirectHandler` class) | NEW (module-level) | utility (urllib handler) | event-driven (callback-on-3xx) | none in-repo — first urllib subclass | no analog (locked verbatim in CONTEXT) |
| `quizify_csv_ingest.py` (`_log_http_failure`) | NEW (module-level helper) | utility (logging facade) | request-response (call → stderr write) | `_format_validation_error` (lines 595–616) + `_run_schema_validation` `print(..., file=sys.stderr)` (line 662) | role-match (categorical PII-safe stderr formatter) |
| `quizify_csv_ingest.py` (`_parse_header`, `_https_url`, optional `_positive_float`) | NEW (argparse `type=` callables) | utility (argparse validators) | transform (str → tuple/str/float, raise on invalid) | none — phase pioneers `type=` callables; closest precedent is built-in `type=Path`/`type=float` already on argparse | no analog (locked verbatim in CONTEXT `<specifics>`) |
| `quizify_csv_ingest.py` (`main()` argparse block, lines 749–787) | EDIT (extend) | config (CLI parsing) | request-response | existing `--ndjson` post-parse `parser.error` block (lines 783–787) | exact (locked shape) |
| `quizify_csv_ingest.py` (`convert()` / `_select_sink`) | EDIT (thread headers, timeout; HTTP error → exit 3) | controller / dispatch | request-response | existing `_run_schema_validation` rc-routing inside `convert()` (lines 735–738) + `with sink:` block (lines 703–717) | exact |
| `quizify-csv-to-json-webhook/README.md` | EDIT (extend table) | docs | — | existing `## CLI reference` table (line 36+) including `--ndjson` row (line 51) | exact |
| `tests/conftest.py` (`mock_webhook` fixture + handler classes) | EDIT (append) | test fixture | event-driven (real socket) | existing `csv_with_bad_row_at_50` fixture (lines 175–198) for "tmp_path-based factory" shape | role-match (different domain — HTTP server vs CSV file) |
| `tests/test_http_post.py` | NEW | integration test | request-response (real socket) | `tests/test_sink_layer.py` (Phase 7/8 integration shape) | role-match |
| `tests/test_http_post_pii.py` | NEW | unit test (negative-substring) | transform (run + assert stderr) | `tests/test_schema_validation.py::TestValidationFailurePIIsafe` (lines 81–238) | exact (mirror class shape) |
| `tests/test_argparse_post_url.py` | NEW | unit test (argparse rejection) | request-response | `tests/test_argparse_ndjson.py` (entire file) | exact (mirror shape) |
| `tests/test_security_grep_gates.py` (planner's discretion) | NEW | unit test (grep gate) | transform (read prod file, regex assert) | none in-repo — Phase 9 introduces grep-gate tests | no analog |

## Pattern Assignments

### `_HttpPostSink` (replace Phase 7 stub body in `quizify_csv_ingest.py:97-114`)

**Analog:** `_FileSink` (lines 74–94) for the buffer-and-emit-on-close shape.

**Buffer shape pattern** (lines 74–94 — copy structure, swap emit):
```python
class _FileSink:
    def __init__(self, output: Path) -> None:
        self._output = output
        self._rows: list[dict] = []
    def write(self, row: dict) -> None:
        self._rows.append(row)
    def close(self) -> None:
        with self._output.open("w", encoding="utf-8") as out_fh:
            json.dump(self._rows, out_fh, indent=2, ensure_ascii=False)
            out_fh.write("\n")
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        self.close(); return False
```

**Delta for `_HttpPostSink`** (locked in CONTEXT `<specifics>` D-09-10/12):
- `__init__(url, headers, timeout)` — three params, not one Path.
- `__exit__` runs `_flush_and_post()` ONLY IFF `exc_type is None and self._rows` (D-09-10 — exception path skips POST; this is the key delta from `_FileSink` which always emits).
- `close()` becomes a no-op (Protocol compliance only); the with-statement is the canonical entry. Mirrors `_NdjsonFileSink.close` (line 149–150).
- Emit body: `urllib.request.Request(url, data=json.dumps(self._rows, ensure_ascii=False).encode("utf-8"), method="POST")` + `self._opener.open(req, timeout=self._timeout)` instead of `json.dump(...)`.

**No-suppress invariant** carry-forward from `_NdjsonFileSink.__exit__` (line 147): `return False  # never suppress`.

---

### `_log_http_failure` helper (NEW, module-level)

**Analog:** `_format_validation_error` (lines 595–616) + `_run_schema_validation`'s `print(_format_validation_error(err), file=sys.stderr)` (line 662) as the categorical-stderr precedent.

**Pattern to mirror — categorical-only, never user data** (line 595–616 docstring):
```python
"""Uses ONLY categorical attributes — NEVER `err.message` / `err.value` / `str(err)`,
which echo cell content (Pitfall 17, T-PII-01)."""
```

**Stderr write mechanism — `logging.error` via `configure_logging`** (line 557–559):
```python
def configure_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(message)s", stream=sys.stderr, force=True)
```
`_log_http_failure` writes via `logging.error("http_failure reason=%s status=%s reason_class=%s body_bytes=%s", ...)` — matches the project's existing `logging.error("CSV is empty")` (line 707), `logging.error("%s", err)` (line 710), `logging.error("cannot open CSV: %s", err)` (line 713) idiom. Format string locked in CONTEXT D-09-07.

**NOTE:** `_run_schema_validation` uses `print(..., file=sys.stderr)` (line 662) for the formatted-pointer line, while `convert()` uses `logging.error(...)` for categorical errors. CONTEXT D-09-07 locks `_log_http_failure` to `logging.error` (so `caplog.text` capture works in tests per RESEARCH Q9).

---

### `_parse_header`, `_https_url` (NEW argparse `type=` callables)

**Analog:** None in-repo (this phase pioneers `type=` callables). Skeleton locked verbatim in CONTEXT `<specifics>`.

**Pattern — `argparse.ArgumentTypeError(categorical_string)`:** the message is the categorical reason code (`header_crlf_rejected`, `post_url_https_required`, etc.) — NEVER include the offending input value. argparse will append `... value: '<input>'` automatically (D-09-14 accepted leak surface).

---

### Argparse extensions in `main()` (`quizify_csv_ingest.py:749-787`)

**Analog:** Existing `--ndjson` post-parse mutex block (lines 783–787):
```python
args = parser.parse_args(argv)

# D-08-11: post-parse mutex checks (locked categorical messages, T-PII-01).
if args.ndjson and args.post_url:
    parser.error("--ndjson cannot be combined with --post-url")
if args.ndjson and not args.output:
    parser.error("--ndjson requires -o/--output (no stdout NDJSON)")
```

**Pattern to copy — append three new checks in the SAME block** (locked in CONTEXT D-09-13):
```python
if args.post_url and not args.validate:
    parser.error("post_url_requires_validate")
if args.timeout <= 0:
    parser.error("timeout_invalid")
# (HTTPS gate is enforced by type=_https_url; no post-parse line needed.)
```

**Pattern — extend existing `-o/--post-url` mutex group** (lines 756–760): `--post-url` gets `type=_https_url` added (Phase 7 left it bare); `--header` and `--timeout` are SIBLINGS to the mutex group (not inside it), parallel to `--ndjson`'s placement (lines 776–780).

**Naming reuse:** Existing categorical messages use kebab-flag prose (`"--ndjson cannot be combined with --post-url"`). New messages use snake_case reason codes (`"post_url_requires_validate"`, `"timeout_invalid"`) per CONTEXT D-09-13. Both shapes coexist; pick by what `parser.error` emits cleanly.

---

### `convert()` HTTP error → exit 3 routing (`quizify_csv_ingest.py:668-746`)

**Analog:** Existing validation-rc routing in `convert()` lines 735–738:
```python
if validate:
    rc = _run_schema_validation(results, SCHEMA_PATH)
    if rc != 0:
        return rc
```
And NDJSON-path exception routing lines 706–717:
```python
except _EmptyCsvError:
    logging.error("CSV is empty"); return 1
except LayoutError as err:
    logging.error("%s", err); return 1
except _RowValidationError as exc:
    print(exc.pointer_message, file=sys.stderr); return 1
```

**Pattern to copy — sentinel exception with rc-mapping at sink-block edge:** Add `_HttpDeliveryError` sentinel (parallel to `_RowValidationError`, lines 153–158); catch around the `with sink:`/`sink.close()` block in the array-mode path (lines 740–745) and `return _EXIT_HTTP` (=3). The single `try/finally` at lines 741–745 currently doesn't catch — extend with `except _HttpDeliveryError: return 3`.

**Constants** (CONTEXT D-09-09): expose `_EXIT_VALIDATION = 1`, `_EXIT_HTTP = 3` at module scope for grep-ability. (Argparse's exit 2 is set by argparse itself.)

---

### `_select_sink` thread-through (`quizify_csv_ingest.py:198-213`)

**Current** (line 204–205):
```python
if args.post_url is not None:
    return _HttpPostSink(args.post_url)
```

**Pattern (D-08-12: pass `args` namespace):** extend to `_HttpPostSink(args.post_url, args.header, args.timeout)`. The `sink_args` Namespace built in `convert()` (lines 684–686) must be widened to include `header` and `timeout`:
```python
sink_args = argparse.Namespace(
    output=output, post_url=post_url, ndjson=ndjson, validate=validate,
    header=headers, timeout=timeout,   # NEW
)
```
And `convert()` signature gains `headers: list[tuple[str,str]] | None = None`, `timeout: float = 30.0`. `main()` (line 804–807) threads them through.

---

### `README.md` — extend `## CLI reference` table (line 36+)

**Analog:** existing rows for `--validate`, `--post-url`, `--ndjson` (lines 49–51).

**Pattern (locked D-11 ten-section README):** add three rows in the SAME table; no new H2.
```markdown
| `--post-url URL` | `—` | HTTPS URL for single-shot webhook POST. Requires `--validate`. Mutually exclusive with `-o/--output` and `--ndjson`. CRLF/HTTP rejected at argparse. | — |
| `--header "K: V"` | `[]` | Repeatable: add request header (e.g., `Authorization: Bearer ...`). CRLF rejected. Used only with `--post-url`. | — |
| `--timeout SECONDS` | `30.0` | HTTP request timeout (must be > 0). Used only with `--post-url`. | — |
```
Update existing `--post-url` row (line 50) — drop "Stub in v1.2 Phase 7; raises NotImplementedError" wording.
Add usage example to the existing examples section (no new H2).

---

### `tests/conftest.py` — `mock_webhook` fixture (extension)

**Analog:** Existing `csv_with_bad_row_at_50` fixture (lines 175–198) for the "self-contained factory yielding a target the test exercises against" shape; existing `SYNTHETIC_PII_TOKENS` constant (line 127) for the negative-substring pattern.

**Pattern — append-only at end of file** (matches existing comment at line 120: `# Phase 8 (Plan 08-01) — synthetic 100-row CSV factory + PII-token list. Append-only; no existing fixture is mutated.`).

**Skeleton (locked, refined in RESEARCH §Code Examples):**
```python
import http.server, threading
class _ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True
class _BaseHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        self.server.received.append(("POST", self.rfile.read(n)))
        self._respond()
    def log_message(self, *a, **kw): pass
@pytest.fixture
def mock_webhook():
    servers = []
    def factory(respond_fn):
        klass = type("H", (_BaseHandler,), {"_respond": respond_fn})
        server = _ReusableHTTPServer(("127.0.0.1", 0), klass)
        server.received = []
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        servers.append((server, thread))
        return f"http://127.0.0.1:{server.server_address[1]}", server.received, server
    yield factory
    for server, thread in servers:
        server.shutdown(); server.server_close(); thread.join(timeout=2.0)
```

**Reuse `SYNTHETIC_PII_TOKENS`** (line 127) for the PII negative-substring suite — NEW: add `b"server_response_marker"` constant alongside it for body-leak detection.

---

### `tests/test_argparse_post_url.py` (NEW)

**Analog:** `tests/test_argparse_ndjson.py` (entire file, 85 lines) — copy shape verbatim.

**Pattern to mirror — `pytest.raises(SystemExit)` + `capsys.readouterr().err` + categorical assertion** (lines 24–32):
```python
def test_ndjson_rejects_post_url(capsys):
    from quizify_csv_ingest import main  # noqa: PLC0415
    with pytest.raises(SystemExit) as exc:
        main(["--ndjson", "--post-url", "https://x", "in.csv"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--ndjson cannot be combined with --post-url" in err
```

**Lazy import of `main`** (`from quizify_csv_ingest import main  # noqa: PLC0415` inside test body) — copy verbatim. Avoids module-level import failures during collection.

**PII negative-substring pattern** (lines 44–64, `test_argparse_rejection_pii_safe`): assert each `SYNTHETIC_PII_TOKENS` entry NOT in stderr after argparse rejection.

**New tests to add (per RESEARCH §Validation Architecture):**
- `test_post_url_requires_validate` — `["--post-url", "https://x", "in.csv"]` (no `--validate`) → exit 2, `"post_url_requires_validate"` in stderr.
- `test_http_rejected` — `["--post-url", "http://x", "--validate", "in.csv"]` → exit 2, `"post_url_https_required"` in stderr.
- `test_https_no_netloc_rejected` — `--post-url https://` → exit 2.
- `test_header_crlf_rejected` — `--header "X: a\r\nY: b"` → exit 2, `"header_crlf_rejected"`.
- `test_header_malformed_rejected` — parametrize over missing-colon, empty-name, invalid-token-char.
- `test_timeout_invalid` — `--timeout 0` and `--timeout -5` → exit 2, `"timeout_invalid"`.

---

### `tests/test_http_post_pii.py` (NEW)

**Analog:** `tests/test_schema_validation.py::TestValidationFailurePIIsafe` (lines 81–238) — mirror class shape.

**Pattern to mirror — class-grouped negative-substring suite** (lines 81–163):
```python
class TestValidationFailurePIIsafe:
    """VALI-02 + T-PII-01 / D-06-20 / D-06-25(c) / Pitfall 17.
    Deliberately malformed payload → exact D-06-20 stderr template, NO cell content."""

    def _build_payload_with_pii(self, leak_email, leak_phone, leak_name) -> list[dict]:
        # Build a structurally-valid row carrying KNOWN-PII tokens, then drop a
        # required key to trigger a 'required' violation on a DIFFERENT field —
        # this stresses Pitfall 17 (the offending-value attribute would otherwise
        # echo the email/phone/name).
        ...

    def test_failure_stderr_does_not_leak_cell_content(self, capsys):
        ...
        err = capsys.readouterr().err
        # Pitfall 17 / T-PII-01: NO cell content in stderr.
        assert leak_email not in err, f"email leaked into stderr: {err!r}"
        assert leak_phone not in err
        assert leak_name not in err
```

**Delta for Phase 9:**
- Class name: `TestHTTPErrorPIIsafe` (CONTEXT D-09-17).
- Inputs: instead of malformed schema payload, use `mock_webhook` fixture with `_respond_502`/`_respond_302`/`_respond_hang`/`_respond_4xx` handlers + a synthetic input row containing `SYNTHETIC_PII_TOKENS`.
- Capture surface: **`caplog.text` (NOT `capsys`)** per RESEARCH Q9 — `_log_http_failure` writes via `logging.error`.
- Negative-substring set:
  - All four `SYNTHETIC_PII_TOKENS` entries.
  - `b"server_response_marker"` (proves response body never reaches stderr).
  - The 302 `Location: http://other.example.test/x` target host (`"other.example.test"`).
  - The mock URL itself (proves target URL not logged at runtime — D-09-14).
- Coverage (per RESEARCH Open Question 3): test the four leak-prone paths individually (`http_unexpected_redirect`, `http_client_error`, `http_server_error`, `network_timeout`); parameterize the four others (`tls_error`, `dns_error`, `connection_refused`, `network_error`) into one test.

---

### `tests/test_http_post.py` (NEW integration tests)

**Analog:** No exact predecessor; closest is `tests/test_sink_layer.py` (Phase 7/8 sink integration). Direct call shape comes from RESEARCH §Q10:
```python
def test_redirect_rejected(mock_webhook, caplog):
    url, received, server = mock_webhook(_respond_302)
    rc = convert(post_url=url, validate=True, ...)  # bypass argparse HTTPS gate
    assert rc == 3
    assert len(received) == 1
    assert "http_unexpected_redirect" in caplog.text
    assert "other.example.test" not in caplog.text
```

**Locked critical assertion (D-09-16):** every test asserts `len(received) == N` where N is 0 for validation-pre-egress and 1 for everything else (including 302). RESEARCH Pitfall 7 makes this the SC#1 "no retry" gate.

---

### `tests/test_security_grep_gates.py` (NEW; planner's discretion on existence)

**Analog:** None in-repo — Phase 9 introduces grep-gate tests. Pattern: read `quizify_csv_ingest.py` source as text and assert regex match counts.

**Locked invariants (CONTEXT D-09-18):**
1. `! grep -nE "CERT_NONE|_create_unverified_context|verify=False"` (zero matches).
2. `grep -c "ssl.create_default_context()"` == 1.
3. `grep -c "self._opener.open("` == 1.
4. `! grep -E "^import requests|^from requests"` (zero matches).

Optional fifth gate (RESEARCH Open Question 1): `Request(method="POST")` count == 1.

## Shared Patterns

### Lazy import inside test body
**Source:** `tests/test_argparse_ndjson.py:26` `from quizify_csv_ingest import main  # noqa: PLC0415`.
**Apply to:** All NEW test files. Reason: module-level imports during pytest collection mask `ImportError` paths under test.

### Categorical PII-safe stderr
**Source:** `_format_validation_error` docstring (lines 597–599) + `_run_schema_validation` print sites (lines 639, 649, 656, 662) + `_log_http_failure` (CONTEXT D-09-07 skeleton).
**Apply to:** `_log_http_failure` (sole new prod stderr path) and every PII test assertion. Rule: format string built from constants only; never `str(err)`, never `err.read()`, never `err.url`.

### `with sink:` no-suppress
**Source:** `_NdjsonFileSink.__exit__` (line 147) `return False  # never suppress`.
**Apply to:** `_HttpPostSink.__exit__` — must return False so `_HttpDeliveryError` propagates to `convert()`'s rc-routing.

### Append-only conftest extensions
**Source:** comment at `tests/conftest.py:120` ("Append-only; no existing fixture is mutated").
**Apply to:** `mock_webhook` fixture + handler classes + `SERVER_RESPONSE_MARKER` constant — append at end; do not modify existing fixtures.

### Lazy `import` for stdlib-but-large modules
**Source:** `_ValidatingSink.__init__` (line 170) `import fastjsonschema  # lazy, D-13`.
**Does NOT apply** to Phase 9 — `urllib.request`, `urllib.error`, `urllib.parse`, `ssl`, `socket`, `re` are tiny stdlib; CONTEXT D-13 carry-forward states top-level imports OK.

### Single mutex group on output-targets
**Source:** `main()` lines 756–760 — `-o/--output` and `--post-url` share an `add_mutually_exclusive_group()`.
**Apply to:** PRESERVE. Phase 9 adds `type=_https_url` to existing `--post-url` line; does NOT add new flags to the mutex group.

## No Analog Found

| Surface | Reason |
|---|---|
| `_NoRedirectHandler` (urllib subclass) | First urllib handler subclass in repo. Skeleton locked verbatim in CONTEXT D-09-01 / `<specifics>`. |
| `_HttpDeliveryError` sentinel | Parallel-by-shape to `_RowValidationError` (line 153) but not a direct copy — different domain (HTTP failure vs validation failure). |
| Argparse `type=` callables (`_parse_header`, `_https_url`, `_positive_float`) | First project-defined `type=` callables. Skeletons locked verbatim in CONTEXT `<specifics>`. |
| `tests/test_security_grep_gates.py` shape | First grep-gate test file in repo. Planner picks idiom (read `Path(__file__).parent.parent / "quizify_csv_ingest.py"`, regex assertions). |
| Real-socket `http.server` test fixture | First in repo. Skeleton locked + refined in RESEARCH §Code Examples. |

## Metadata

**Analog search scope:**
- `quizify-csv-to-json-webhook/quizify_csv_ingest.py` (sinks lines 49–213; argparse 749–787; convert 668–746; logging helpers 555–665).
- `quizify-csv-to-json-webhook/tests/test_argparse_ndjson.py` (full file).
- `quizify-csv-to-json-webhook/tests/test_schema_validation.py` (lines 81–238 — `TestValidationFailurePIIsafe`).
- `quizify-csv-to-json-webhook/tests/conftest.py` (full file).
- `quizify-csv-to-json-webhook/README.md` (CLI reference table).

**Files scanned:** 5 source files + RESEARCH.md + CONTEXT.md (locked skeletons treated as authoritative for surfaces with no in-repo analog).

**Pattern extraction date:** 2026-05-05.
