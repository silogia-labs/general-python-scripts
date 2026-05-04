# Roadmap: Quizify CSV → Webhook JSON

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-05-03) — see [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-05-03</summary>

- [x] Phase 1: CSV ingestion & column layout (1/1 plans) — completed 2026-05-03
- [x] Phase 2: Core webhook mapping (2/2 plans) — completed 2026-05-03
- [x] Phase 3: Scoring metadata & packaging (2/2 plans) — completed 2026-05-03

</details>

### 📋 Next milestone (planning)

Run `/gsd-new-milestone` to scope v1.1 (or v2.0 if breaking changes are expected). Candidate seeds carried forward in PROJECT.md:

- AUTO-01 — optional HTTP POST mode with batch + retries
- VALI-01 — JSON Schema validation against the webhook example
- Streaming/NDJSON output for large CSVs (>50k rows)
- `--trailer-columns` name-based scoring lookup (currently positional `[0..2]`)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. CSV ingestion & column layout | v1.0 | 1/1 | Complete | 2026-05-03 |
| 2. Core webhook mapping | v1.0 | 2/2 | Complete | 2026-05-03 |
| 3. Scoring metadata & packaging | v1.0 | 2/2 | Complete | 2026-05-03 |
