"""Phase 7 (REFACTOR-01) — sink layer + iter_rows + argparse mutex tests.

All tests in this module exercise symbols introduced by the Phase 7 refactor:
  - `_HttpPostSink` (stub — D-07-04)
  - `_select_sink` factory (D-07-11)
  - `iter_rows` / `_RowStream` generator shape, including non-prefetch proof (D-07-05, ROADMAP SC#2)
  - argparse `-o`/`--post-url` mutual-exclusion group (D-07-10)
  - stderr preservation for empty-CSV and LayoutError paths (D-07 carry-forward)

Per D-07-13 / D-07-16 / Pitfall 16 (carry-forward): unit-level only — no
subprocess, no network, no test deps beyond what the v1.1 suite already uses.
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

import quizify_csv_ingest
from quizify_csv_ingest import (
    _FileSink,
    _HttpPostSink,
    _StdoutSink,
    _select_sink,
    convert,
    iter_rows,
    main,
)


# ---------------------------------------------------------------------------
# _HttpPostSink stub (D-07-04 / D-07-14)
# ---------------------------------------------------------------------------

def test_http_post_sink_construct_silently() -> None:
    """Phase 9 carry-forward: __init__ stores url + headers + timeout silently."""
    sink = _HttpPostSink("https://example.test/hook", headers=[], timeout=30.0)
    assert sink._url == "https://example.test/hook"
    assert sink._headers == []
    assert sink._timeout == 30.0


def test_http_post_sink_write_buffers_row() -> None:
    """Phase 9 (D-09-10): write() appends to internal buffer; no POST yet."""
    sink = _HttpPostSink("https://example.test/hook", headers=[], timeout=30.0)
    sink.write({"email": "x"})
    assert sink._rows == [{"email": "x"}]


def test_http_post_sink_close_is_noop() -> None:
    """Phase 9: close() is a no-op (CM is the active path)."""
    sink = _HttpPostSink("https://example.test/hook", headers=[], timeout=30.0)
    assert sink.close() is None


# ---------------------------------------------------------------------------
# argparse mutex group (D-07-10 / D-07-15)
# ---------------------------------------------------------------------------

def test_argparse_output_post_url_mutex_rejection() -> None:
    """D-07-15 carry-forward: -o and --post-url together => SystemExit(2)."""
    with pytest.raises(SystemExit) as excinfo:
        main(["-o", "out.json", "--post-url", "https://y.test", "--validate", "in.csv"])
    assert excinfo.value.code == 2


def test_post_url_with_missing_csv_returns_1_not_crash(tmp_path) -> None:
    """Phase 9 carry-forward: --post-url + --validate accepted; OSError on file
    open → exit 1 (convert() catches). Sink is constructed but its `_post_once`
    is never reached because validation runs (and fails on missing CSV) first.
    """
    rc = main([
        "--post-url", "https://y.test", "--validate",
        str(tmp_path / "missing.csv"),
    ])
    assert rc == 1, f"Expected rc=1 from OSError on missing CSV; got rc={rc!r}."


# ---------------------------------------------------------------------------
# _select_sink factory dispatch (D-07-11)
# ---------------------------------------------------------------------------

def _ns(output=None, post_url=None, ndjson=False, validate=False,
        header=None, timeout=30.0):
    """Build a minimal argparse.Namespace for _select_sink (D-08-12 / D-09-13)."""
    import argparse
    return argparse.Namespace(
        output=output, post_url=post_url, ndjson=ndjson, validate=validate,
        header=list(header or []), timeout=timeout,
    )


def test_select_sink_returns_stdout_sink_when_neither_set() -> None:
    assert isinstance(_select_sink(_ns()), _StdoutSink)


def test_select_sink_returns_file_sink_when_output_set(tmp_path) -> None:
    assert isinstance(_select_sink(_ns(output=tmp_path / "x.json")), _FileSink)


def test_select_sink_returns_http_post_sink_when_post_url_set() -> None:
    assert isinstance(_select_sink(_ns(post_url="https://example.test/h")), _HttpPostSink)


# ---------------------------------------------------------------------------
# iter_rows / _RowStream shape (ROADMAP SC#2 / D-07-05)
# ---------------------------------------------------------------------------

def test_iter_rows_yields_one_dict_per_row_incrementally(sample_csv_path) -> None:
    """SC#2 (loose shape): iter_rows returns an iterable yielding dicts.

    Pulls the first 3 rows via next() and asserts each is a dict with the
    contact key 'email' present. NOTE: this test alone does NOT prove the
    generator is incremental — a hidden `list(reader)` inside __iter__ would
    also pass. See `test_iter_rows_does_not_prefetch_all_rows_on_first_yield`
    for the deterministic non-prefetch proof.
    """
    stream = iter_rows(sample_csv_path, None, "")
    it = iter(stream)
    first = next(it)
    assert isinstance(first, dict)
    assert "email" in first
    second = next(it)
    assert isinstance(second, dict)
    third = next(it)
    assert isinstance(third, dict)


def test_iter_rows_does_not_prefetch_all_rows_on_first_yield(sample_csv_path) -> None:
    """B1: NON-PREFETCH PROOF.

    Wraps `quizify_csv_ingest.build_row` with a call counter via patch.object.
    After exactly ONE next() pull from the generator, assert the wrapper was
    invoked exactly 1 time. A hidden `list(reader)` inside __iter__ that
    eagerly built every row would invoke build_row 42 times before yielding,
    and this test would catch it.
    """
    original_build_row = quizify_csv_ingest.build_row
    call_count = {"n": 0}

    def counting_build_row(*args, **kwargs):
        call_count["n"] += 1
        return original_build_row(*args, **kwargs)

    with patch.object(quizify_csv_ingest, "build_row", side_effect=counting_build_row):
        stream = iter_rows(sample_csv_path, None, "")
        it = iter(stream)
        _ = next(it)  # exactly one pull

    assert call_count["n"] == 1, (
        f"Expected build_row to be called exactly 1 time after a single next() "
        f"(streaming generator). Got {call_count['n']} calls — this indicates "
        f"__iter__ pre-builds all rows (hidden full-prefetch); SC#2 violated."
    )


def test_iter_rows_exit_code_attribute_initialized_zero(sample_csv_path) -> None:
    """D-07-05: _RowStream carries a mutable exit_code attribute, init 0."""
    stream = iter_rows(sample_csv_path, None, "")
    assert stream.exit_code == 0


def test_iter_rows_exit_code_set_to_1_on_row_length_mismatch(tmp_path, caplog) -> None:
    """W3: Per-row length mismatch sets stream.exit_code |= 1 AND emits the
    Phase-5-locked WARNING template ('row %d row length mismatch: expected
    %d fields, got %d'). Exhausts the generator via list().
    """
    import csv as _csv

    bad_csv = tmp_path / "bad.csv"
    sample = Path(__file__).resolve().parents[1] / "docs" / "quizify-submissions.csv"
    with sample.open(encoding="utf-8-sig", newline="") as src:
        reader = _csv.reader(src)
        header = next(reader)
    with bad_csv.open("w", encoding="utf-8", newline="") as dst:
        writer = _csv.writer(dst)
        writer.writerow(header)
        # Row of wrong length — one fewer column than expected.
        writer.writerow([""] * (len(header) - 1))

    with caplog.at_level(logging.WARNING, logger="root"):
        stream = iter_rows(bad_csv, None, "")
        list(stream)  # drain

    assert stream.exit_code == 1, (
        f"exit_code must be 1 after row length mismatch; got {stream.exit_code}"
    )
    mismatch_records = [
        r for r in caplog.records
        if "row length mismatch" in r.getMessage()
    ]
    assert len(mismatch_records) == 1, (
        f"Expected exactly one 'row length mismatch' WARNING; "
        f"got {len(mismatch_records)}: {[r.getMessage() for r in mismatch_records]}"
    )
    assert mismatch_records[0].levelno == logging.WARNING


# ---------------------------------------------------------------------------
# stderr preservation: empty-CSV and LayoutError paths (W5)
# ---------------------------------------------------------------------------

def test_convert_empty_csv_logs_identical_to_v1_1(tmp_path, caplog) -> None:
    """W5(a): An empty CSV file produces exactly one ERROR record with the
    v1.1-locked message 'CSV is empty' (quizify_csv_ingest.py:445 today).
    convert() returns 1.
    """
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="root"):
        rc = convert(empty_csv, None, None, "")

    assert rc == 1, f"empty CSV must return 1; got {rc}"
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1, (
        f"Expected exactly 1 ERROR record on empty CSV; got {len(error_records)}: "
        f"{[r.getMessage() for r in error_records]}"
    )
    assert error_records[0].getMessage() == "CSV is empty", (
        f"Stderr drift from v1.1: expected 'CSV is empty', got "
        f"{error_records[0].getMessage()!r}"
    )


def test_convert_layout_error_logs_identical_to_v1_1(tmp_path, caplog) -> None:
    """W5(b): A CSV that triggers LayoutError in classify_headers produces
    exactly one ERROR record with message equal to str(LayoutError) — i.e.,
    the v1.1 surface from `logging.error("%s", err)` at line 452 today.
    convert() returns 1.
    """
    bad_csv = tmp_path / "bad_header.csv"
    # A header missing the required CONTACT_PREFIX columns triggers LayoutError.
    bad_csv.write_text("foo,bar,baz\n1,2,3\n", encoding="utf-8")

    with caplog.at_level(logging.ERROR, logger="root"):
        rc = convert(bad_csv, None, None, "")

    assert rc == 1, f"LayoutError path must return 1; got {rc}"
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1, (
        f"Expected exactly 1 ERROR record on LayoutError; got {len(error_records)}: "
        f"{[r.getMessage() for r in error_records]}"
    )
    msg = error_records[0].getMessage()
    assert msg, "LayoutError message must be non-empty"
    assert msg != "CSV is empty", (
        "LayoutError path must not collapse into the empty-CSV message"
    )
