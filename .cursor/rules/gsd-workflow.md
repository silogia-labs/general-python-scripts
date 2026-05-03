<!-- GSD:project-start source:PROJECT.md -->
## Project

**Quizify CSV → Webhook JSON**

This initiative lives inside the `general-python-scripts` utilities repository. It adds a small Python helper that turns Quizify.io CSV exports (from https://app.quizify.io) into JSON payloads shaped like `quizify-csv-to-json-webhook/docs/webhook-quizify-format-example.json`, so integrations that expect webhook-style records can consume exports without manual rework.

**Core Value:** Each CSV submission row becomes one webhook-compatible JSON object with correct contact fields, ordered `question-N` / `answers-N` / `answers-tags-N` keys, scoring-related fields, and tags—including sensible behavior when Quizify omits answer IDs or encodes characters as HTML entities.

### Constraints

- **Technology**: Python 3; prefer standard library; add dependencies only when justified
- **Data quality**: Cells may contain HTML entities (`&gt;`, `&lt;`) that must appear as plain characters in JSON strings
- **Privacy**: Treat exports as PII; avoid verbose logging of row contents by default
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
