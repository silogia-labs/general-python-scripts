# Requirements: Quizify CSV → Webhook JSON

**Defined:** 2026-05-03  
**Core Value:** CSV submission rows become webhook-compatible JSON objects without manual restructuring.

## v1 Requirements

### CLI & ingestion

- [ ] **CONV-01**: The tool accepts an input CSV path (UTF-8) and produces JSON output (single array file or stdout), suitable for piping into webhook receivers or saving for replay.
- [ ] **CONV-02**: Fixed columns are distinguished from dynamic quiz question columns using the known export layout (contact fields first, `Result logic` … `Date` trailer block); remaining headers map to `question-N` indices in order.

### Contact & subscription fields

- [ ] **CONV-03**: Maps `First name` → `firstName`, `Last name` → `lastName`, `Email` → `email`, `Phone` → `phone`.
- [ ] **CONV-04**: Maps newsletter/subscription column values to `status` (e.g. subscribed vs unsubscribed) consistently with the example payload semantics.
- [ ] **CONV-05**: Maps submission `Date` to `statusDate` using ISO `YYYY-MM-DD` (or documented timezone assumptions if needed).

### Normalization & answers

- [ ] **CONV-06**: Decodes HTML entities in CSV cell text so JSON strings match human-readable quiz answers (e.g. `&gt;` → `>`).
- [ ] **WEB-01**: Builds `tags`, including a Quizify source marker aligned with the example, and merges parsed values from the `Answer tags` column where present.
- [ ] **WEB-02**: For each dynamic question index `N`, emits `question-N` (verbatim header text), `answers-N`, and `answers-tags-N` when appropriate.
- [ ] **WEB-03**: Chooses answer representation per row: plain string for free-text / composite answers; array of objects with `answer_name` (and optional `answer_img`, `answer_tag`) when modeling discrete choices—omit unknown `id` rather than guessing.

### Scoring & metadata

- [x] **WEB-04**: Maps `Result logic`, `Score category`, and `Score value` into the webhook fields used for recommendations (e.g. `product-recommendation`) following conventions illustrated by the example and documented in the script README.
- [x] **WEB-05**: Supports setting `quiz_title` via CLI flag or env when the CSV does not include a dedicated column.

### Documentation

- [ ] **OPS-01**: Adds a concise README beside the script describing usage, column assumptions, and limitations (missing IDs, encoding).

## v2 Requirements

### Automation

- **AUTO-01**: Optional HTTP POST mode to send each payload directly to a webhook URL (batch + retries).

### Validation

- **VALI-01**: Optional JSON Schema validation against a checked-in schema derived from the example file.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Interactive Quizify authentication / scraping | Exports are manual CSV downloads; stay offline-first |
| GUI | Utility script only |
| Multi-tenant Quiz configuration UI | Single-quiz mapping driven by headers is sufficient for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONV-01 | Phase 1 | Pending |
| CONV-02 | Phase 1 | Pending |
| CONV-03 | Phase 2 | Pending |
| CONV-04 | Phase 2 | Pending |
| CONV-05 | Phase 2 | Pending |
| CONV-06 | Phase 2 | Pending |
| WEB-01 | Phase 2 | Pending |
| WEB-02 | Phase 2 | Pending |
| WEB-03 | Phase 2 | Pending |
| WEB-04 | Phase 3 | Complete |
| WEB-05 | Phase 3 | Complete |
| OPS-01 | Phase 3 | Pending |

**Coverage:**

- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-03*  
*Last updated: 2026-05-03 after roadmap creation*
