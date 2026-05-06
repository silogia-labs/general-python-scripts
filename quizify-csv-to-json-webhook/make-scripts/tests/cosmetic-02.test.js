"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { mapRecord } = require("../score-calculations");

test("MAKE-COSMETIC-02: 'profile_base' never appears in mapRecord output across all fixtures", () => {
    const dir = path.join(__dirname, "fixtures", "score-calculations");
    const files = fs.readdirSync(dir).filter(f => f.endsWith(".json"));
    assert.ok(files.length >= 5, "need fixtures covering all profile branches (red_flags, severo, moderado, leve)");
    for (const f of files) {
        const fix = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
        const out = mapRecord(fix);
        // ROADMAP success criterion #1 — score-calculations.js:217 dead init removed
        assert.notStrictEqual(out.profile, "profile_base",
            `fixture ${f}: profile fell through to dead init`);
        assert.ok(!JSON.stringify(out).includes("profile_base"),
            `fixture ${f}: 'profile_base' string found anywhere in output`);
    }
});
