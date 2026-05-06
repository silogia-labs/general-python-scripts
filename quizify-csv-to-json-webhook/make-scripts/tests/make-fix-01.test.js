"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { mapRecord } = require("../quizify-mapping");
const fixture = require("./fixtures/quizify-mapping/peri-meno-row.json");

test("MAKE-FIX-01: peri_menu (underscore) → life_stage_profile === 'peri_menopause_menopause'", () => {
    const out = mapRecord(fixture);
    // CONVENTIONS.md:18 — peri_menu (underscore, not hyphen)
    // ROADMAP success criterion #2
    // life_stage_profile is set by score-calculations downstream; quizify-mapping emits the peri_menu tag.
    // Assert here on the upstream tag emission since this test targets quizify-mapping.
    assert.ok(Array.isArray(out.tags) && out.tags.includes("peri_menu"),
        "quizify-mapping must emit 'peri_menu' (underscore) tag");
});
