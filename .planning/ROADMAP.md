# Roadmap: Quizify CSV → Webhook JSON

## Overview

Deliver a stdlib-friendly Python CLI that reads Quizify CSV exports and emits JSON payloads shaped like the checked-in webhook example: first nail ingestion and column classification, then row mapping and answer shaping, then scoring metadata, `quiz_title`, and documentation.

## Phases

- [ ] **Phase 1: CSV ingestion & column layout** — Reliable parsing and classification of fixed vs dynamic columns
- [ ] **Phase 2: Core webhook mapping** — Contact fields, questions/answers/tags, entity decoding
- [ ] **Phase 3: Scoring metadata & packaging** — Score columns, quiz title flag, README / requirements

## Phase Details

### Phase 1: CSV ingestion & column layout

**Goal**: Read exports deterministically and compute ordered question indices.

**Depends on**: Nothing (first phase)

**Requirements**: CONV-01, CONV-02

**Success Criteria** (what must be TRUE):

1. Running the tool against `quizify-csv-to-json-webhook/docs/quizify-submissions.csv` classifies headers into contact, dynamic question, and trailing analytic groups without manual column indexes.
2. Output preview (dry-run or debug mode) lists detected question count matching the CSV header layout.
3. Parser tolerates UTF-8 and quoted cells present in the sample export.

**Plans**: TBD

Plans:

- [ ] 01-01: Implement CSV reader + header scanner with configurable trailer column names
- [ ] 01-02: Smoke-test against sample CSV row count

### Phase 2: Core webhook mapping

**Goal**: Emit JSON objects per row matching baseline webhook keys and answer shapes.

**Depends on**: Phase 1

**Requirements**: CONV-03, CONV-04, CONV-05, CONV-06, WEB-01, WEB-02, WEB-03

**Success Criteria** (what must be TRUE):

1. For at least one complete sample row, emitted JSON contains correct `firstName`, `lastName`, `email`, `phone`, `status`, `statusDate`.
2. Each dynamic column produces matching `question-N`, `answers-N`, and `answers-tags-N` keys in order.
3. HTML entities from CSV cells appear decoded in JSON strings.

**Plans:** 2 plans

Plans:

- [ ] 02-01-PLAN.md — Row builder + answer typing (CONV-03..06, WEB-01..03) with CLI JSON emission
- [ ] 02-02-PLAN.md — Golden-file structural diff + sample-CSV invariants (WEB-02, WEB-03)

### Phase 3: Scoring metadata & packaging

**Goal**: Finish scoring-related fields, quiz title handling, and operator docs.

**Depends on**: Phase 2

**Requirements**: WEB-04, WEB-05, OPS-01

**Success Criteria** (what must be TRUE):

1. `Result logic` / `Score category` / `Score value` map into documented webhook fields without silent data loss.
2. CLI exposes `--quiz-title` (or equivalent) and documents precedence vs CSV.
3. README in `quizify-csv-to-json-webhook/` explains usage, limitations (missing IDs), and privacy notes.

**Plans:** 2 plans

Plans:

- [x] 03-01-PLAN.md — Scoring/placeholder keys + --quiz-title precedence (TDD; WEB-04, WEB-05)
- [x] 03-02-PLAN.md — Operator README + --help drift smoke test (OPS-01)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. CSV ingestion & column layout | 0/TBD | Not started | - |
| 2. Core webhook mapping | 0/TBD | Not started | - |
| 3. Scoring metadata & packaging | 2/2 | Complete | 2026-05-03 |
