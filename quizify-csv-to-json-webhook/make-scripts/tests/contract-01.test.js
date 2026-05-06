"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { mapRecord } = require("../quizify-mapping");
const fixture = require("./fixtures/quizify-mapping/happy-path.json");

test("CONTRACT-01: product_recommendation populated; product_result absent", () => {
    const out = mapRecord(fixture);
    // CONVENTIONS.md §CONTRACT-01 verification — snake_case key
    // ROADMAP success criterion #2
    assert.ok(typeof out.product_recommendation === "string" && out.product_recommendation.length > 0);
    assert.strictEqual("product_result" in out, false, "old hyphen key must not appear");
});
