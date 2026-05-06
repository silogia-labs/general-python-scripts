"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { mapRecord } = require("../score-calculations");

test("MAKE-FIX-02: is_athlete undefined → activity_profile === 'non_athlete'", () => {
    const fixture = require("./fixtures/score-calculations/activity-non-athlete.json");
    const out = mapRecord(fixture);
    // CONVENTIONS.md §MAKE-FIX-02 (Pitfall D — undefined is_athlete defaults non_athlete)
    // ROADMAP success criterion #2
    assert.strictEqual(out.activity_profile, "non_athlete");
});

test("MAKE-FIX-02: is_athlete true → activity_profile === 'athlete'", () => {
    const fixture = require("./fixtures/score-calculations/activity-athlete.json");
    const out = mapRecord(fixture);
    // CONVENTIONS.md §MAKE-FIX-02
    assert.strictEqual(out.activity_profile, "athlete");
});
