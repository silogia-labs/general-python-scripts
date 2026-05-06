"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { mapRecord } = require("../score-calculations");
const fixture = require("./fixtures/score-calculations/work-remoto.json");

test("MAKE-COSMETIC-01: work=remoto → context_profile === 'Remoto'", () => {
    const out = mapRecord(fixture);
    // ROADMAP success criterion #1 — score-calculations.js:157
    assert.strictEqual(out.context_profile, "Remoto");
});

test("MAKE-COSMETIC-01 negative regression: literal 'Reomoto' never appears in any fixture output", () => {
    const dir = path.join(__dirname, "fixtures", "score-calculations");
    for (const f of fs.readdirSync(dir).filter(x => x.endsWith(".json"))) {
        const fix = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
        const out = mapRecord(fix);
        // D-10-09 negative-regression citation: ROADMAP SC #1
        assert.notStrictEqual(out.context_profile, "Reomoto",
            `fixture ${f} regressed to typo`);
    }
});
