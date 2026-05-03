# Phase 3: Scoring metadata & packaging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 3-Scoring metadata & packaging
**Areas discussed:** Scoring field mapping, quiz_title source & precedence, Score value typing & emptiness, README scope & content

---

## Scoring field mapping

### Q1: How should the three CSV scoring trailer fields map into webhook keys?

| Option | Description | Selected |
|--------|-------------|----------|
| Pass-through to new keys | Verbatim under `result-logic` / `score-category` / `score-value`; emit example's 4 placeholder keys as `null`/`""` since CSV can't supply real product-link data. Zero data loss, no invented values. | ✓ |
| Category → product-recommendation | Emit `product-recommendation = Score category`, `score-value` verbatim, drop `Result logic`. Mimics example shape but renames. | |
| Static lookup table | Hard-coded `Score category → product-recommendation` map. Matches example output literally but invents mapping policy without authoritative source. | |
| You decide | Claude picks based on Phase 2 'omit fallback' precedent. | |

**User's choice:** Pass-through to new keys
**Notes:** Aligns with PROJECT.md "omit fallback" / Phase 2 D-07. No invented mappings.

### Q2: For the 4 example-payload placeholder keys, what should we emit?

| Option | Description | Selected |
|--------|-------------|----------|
| Emit all 4 with example defaults | `product-recommendation: null`, `product-link-type: null`, `title: ""`, `type-page-url: ""`. Preserves example shape. README documents as "reserved — not derivable from CSV export". | ✓ |
| Omit them entirely | Skip these 4 keys. Risk: receivers expecting the keys may fail. | |
| CLI-overridable defaults | Expose `--product-recommendation`, `--title` flags. Adds CLI surface area for v1. | |

**User's choice:** Emit all 4 with example defaults
**Notes:** Preserves contract with consumers expecting the keys.

### Q3: Empty/missing scoring cells?

| Option | Description | Selected |
|--------|-------------|----------|
| Empty string verbatim | `score-category: ""`, `score-value: ""`. Consistent with Phase 2 D-08/D-09. | ✓ |
| null for empty | Distinguishes 'truly absent' from 'empty string', but inconsistent with Phase 2's uniform `""` policy. | |
| Warn on empty | Emit `""` plus stderr WARNING. Noisy if empty is expected. | |

**User's choice:** Empty string verbatim
**Notes:** Uniform with Phase 2 always-emit-key policy.

### Q4: Where do the new keys land in key ordering?

| Option | Description | Selected |
|--------|-------------|----------|
| Match example exactly | `quiz_title` after `tags`, then question triples, then pass-through scoring, then 4 placeholders at end. | ✓ |
| Pass-through after placeholders | Pass-through scoring keys come AFTER the 4 placeholders. | |
| All scoring at end, no placeholders interleaved | Group scoring + placeholders together at the end. | |

**User's choice:** Match example exactly

---

## quiz_title source & precedence

### Q1: Required, optional, fallback?

| Option | Description | Selected |
|--------|-------------|----------|
| Optional, default to empty string | If neither CLI nor env supplied, emit `quiz_title: ""`. | ✓ |
| Optional, default to CSV filename stem | Derive from input path. Couples output identity to filename. | |
| Required — error if missing | Forces explicit titling but annoys ad-hoc users. | |
| Optional, omit key if unset | Diverges from example shape. | |

**User's choice:** Optional, default to empty string

### Q2: Precedence order?

| Option | Description | Selected |
|--------|-------------|----------|
| CLI > env > future CSV column > default | Operator can always override; future-proof for a CSV column. | ✓ |
| CSV column > CLI > env > default | CSV-as-truth. Riskier — typos propagate. | |
| CLI only — ignore env, ignore future CSV column | Simplest. Drops env support. | |

**User's choice:** CLI > env > future CSV column > default

### Q3: Naming?

| Option | Description | Selected |
|--------|-------------|----------|
| `--quiz-title` + `QUIZIFY_QUIZ_TITLE` | Roadmap exact wording; `QUIZIFY_` prefix avoids collision. | ✓ |
| `--quiz-title` + `QUIZ_TITLE` | Shorter env var; collision risk in shared shells. | |
| `-t` / `--title` + `QUIZIFY_QUIZ_TITLE` | Confusable with example's separate `"title": ""` placeholder. | |

**User's choice:** `--quiz-title` + `QUIZIFY_QUIZ_TITLE`

---

## Score value typing & emptiness

### Q1: How should `Score value` be typed?

| Option | Description | Selected |
|--------|-------------|----------|
| String verbatim | `score-value: "500"`. Consistent with Phase 2 verbatim policy. | ✓ |
| Coerce to int when numeric, string otherwise | More 'correct' typing but mixed types complicate receivers. | |
| Always coerce to number; warn on non-numeric | Strict but loses information when scores are categorical-numeric. | |

**User's choice:** String verbatim

### Q2: Should `Result logic` and `Score category` follow same string-verbatim typing?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — string verbatim, empty→"" | Uniform with Phase 2; decoded via `html.unescape`. | ✓ |
| Lowercase result-logic, verbatim category | Tiny normalization; diverges from verbatim policy. | |

**User's choice:** Yes — string verbatim, empty→""

---

## README scope & content

### Q1: README content?

| Option | Description | Selected |
|--------|-------------|----------|
| Full operator doc | Purpose / Quickstart / CLI ref / Column assumptions / Output shape / Limitations / Privacy / Exit codes. | ✓ |
| Minimal usage only | Just Quickstart + flag reference. | |
| Full doc + worked example | Adds runnable worked example. Risk: example drifts from code. | |

**User's choice:** Full operator doc

### Q2: Dependencies file policy?

| Option | Description | Selected |
|--------|-------------|----------|
| No `requirements.txt`; keep `requirements-dev.txt` | Stdlib-only runtime; empty file is misleading. | ✓ |
| Empty `requirements.txt` placeholder | Signal/convention for downstream tooling. | |
| Pin Python version only | `.python-version` file but no requirements file. | |

**User's choice:** No `requirements.txt`; keep `requirements-dev.txt`

### Q3: README format for flag/env precedence?

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown table | Single 'Configuration' table; scannable; renders on GitHub. | ✓ |
| Prose paragraph per setting | More narrative, less scannable. | |

**User's choice:** Markdown table

---

## Claude's Discretion

- Whether `quiz_title` resolution lives inline in `main()` or in a small helper.
- Whether to factor a `SCORING_PLACEHOLDERS` constant dict or inline the four keys in `build_row`.
- Exact wording of README prose, paragraph ordering within sections, code-fence language tags.
- Whether the README's CLI reference is auto-generated from `argparse` `--help` or hand-written.
- Whether to add `pyproject.toml` / `setup.cfg` for the helper folder.

## Deferred Ideas

- Future CSV `Quiz title` column lookup — stub today; implement when a real export proves the column name.
- CLI flags for the 4 reserved placeholder keys — defer until a downstream consumer needs non-null placeholders.
- `Score value` numeric coercion — revisit when a consumer breaks on string typing.
- WARNING on empty scoring cells — defer until anomaly is observed.
- README worked-example code block — link to fixtures instead.
- Auto-generating README CLI reference from `argparse --help`.
- `pyproject.toml` / packaging.
- Carry-overs from prior phases: HTTP POST mode (AUTO-01 v2), JSON Schema validation (VALI-01 v2), subcommands, ID recovery from external sources.
