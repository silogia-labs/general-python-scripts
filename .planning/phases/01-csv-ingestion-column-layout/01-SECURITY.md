---
phase: 1
slug: csv-ingestion-column-layout
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-03
---

# Phase 1 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Operator workstation → local Python process | User runs CLI with explicit path to CSV on disk | **High sensitivity** — Quizify exports contain PII (names, emails, phones, health-related answers) |
| Process → stderr / stdout | Diagnostics vs future JSON | Stderr: counts + header labels only in `--dry-run`; stdout reserved for Phase 2 JSON |
| Test subprocess | pytest invokes `sys.executable` with argv list | Fixture path is constant Path objects — no shell interpolation |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01-01 | Information disclosure | `quizify_csv_ingest.py` `dry_run()` | mitigate | `--dry-run` prints only `Questions (dynamic):`, `Dynamic: <header>`, `Rows (data):`; loops over rows count rows only — **never** prints cell values. Logging WARNING for row-length uses counts only. | closed |
| T-01-02 | Tampering / unintended read | `main()` / `dry_run()` | mitigate | `path.open(...)` read-only via `Path`; user-supplied path is explicit positional — no URL or `-` stdin in Phase 1. | closed |
| T-01-03 | Injection | `--trailer-columns` | mitigate | `parse_trailer_arg`: split on comma, strip, reject empty list → exit 2 + stderr `invalid trailer-columns`. | closed |
| T-01-04 | Elevation / shell injection | `tests/test_layout.py` | mitigate | `subprocess.run([sys.executable, str(SCRIPT), ...])` — argv list, **no** `shell=True`. | closed |

*Disposition: mitigate (implemented)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|-----------------|--------|------|--------|
| 2026-05-03 | 4 | 4 | 0 | gsd-secure-phase (orchestrator verification against PLAN `<threat_model>` + code review) |

### Verification notes (evidence)

- **T-01-01:** `dry_run()` lines 97–112 print only `dynamic` header strings (from header row) and aggregate counts; no `print(row)` or cell iteration for display. `test_dry_run_stderr_row_count` asserts `@` not in stderr on fixture.
- **T-01-02:** `path.open` default read mode; no write/exec.
- **T-01-03:** `parse_trailer_arg` + `ValueError` → exit code 2 in `main`.
- **T-01-04:** `test_layout.py` subprocess uses explicit argument list.

---

## Sign-Off

- [x] All threats have a disposition (mitigate)
- [x] Accepted risks documented (none)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-03
