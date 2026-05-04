# Phase 1: CSV ingestion & column layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 1-CSV ingestion & column layout
**Areas discussed:** Preview / debug UX, Trailer block detection, Header matching strictness, CLI entry shape

---

## Preview / debug UX

| Option | Description | Selected |
|--------|-------------|----------|
| A — Stderr diagnostics, stdout reserved for data | Matches Unix piping; stderr for `--dry-run` summary and logs | ✓ |
| B — stdout for everything | Simpler typing; breaks `tool \| jq` in Phase 2 | |
| C — Separate log file only | Extra operator friction for a small helper | |

**User's choice:** User selected area **1** for discussion; alignment with **PROJECT.md** privacy rule (no verbose row logging) and common CLI practice led to **A** + structured `--dry-run` without cell values.

**Notes:** Brief external cues: stderr for diagnostics when stdout carries pipeable output is widely recommended for Unix CLIs.

---

## Trailer block detection

| Option | Description | Selected |
|--------|-------------|----------|
| A — Default Quizify trailer list + `--trailer-columns` override | Stable defaults with escape hatch when exports evolve | ✓ |
| B — Config file only | Heavier than needed for v1 | |
| C — Fully inferred from data without defaults | Risky; violates deterministic classification goal | |

**User's choice:** Area **2** selected; **A** locks behavior to sample export while allowing ordered overrides.

---

## Header matching strictness

| Option | Description | Selected |
|--------|-------------|----------|
| A — Strip + NFC only; preserve raw labels for output | Handles BOM/spacing drift without fuzzy collisions | ✓ |
| B — Case-insensitive match | Risk of mis-classifying distinct headers | |
| C — Exact bytes only | Fragile on BOM / NFC equivalence | |

**User's choice:** Area **3** selected; **A** with **utf-8-sig** reader.

---

## CLI entry shape

| Option | Description | Selected |
|--------|-------------|----------|
| A — Single argparse command + flags for Phase 1 | Matches small-helper scope; subcommands deferred | ✓ |
| B — Subcommands (`scan`, `convert`) now | Premature before JSON conversion exists | |

**User's choice:** Area **4** selected; **A** until multiple verbs are clearly needed.

---

## Claude's Discretion

- Exact metavar/help text for `--trailer-columns`; optional quiet flag — polish during implementation.

## Deferred Ideas

- Subcommands when Phase 2 adds distinct output modes; optional case-fold flag if exports drift.
