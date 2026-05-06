"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

function loadFixtures(moduleName) {
    const dir = path.join(__dirname, "fixtures", moduleName);
    return fs.readdirSync(dir)
        .filter(f => f.endsWith(".json"))
        .map(f => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")));
}

test("score-calculations leaks no globals", () => {
    const before = new Set(Reflect.ownKeys(globalThis));
    const { mapRecord } = require("../score-calculations");
    for (const fixture of loadFixtures("score-calculations")) mapRecord(fixture);
    const leaked = Reflect.ownKeys(globalThis).filter(k => !before.has(k));
    assert.deepStrictEqual(leaked, [], `score-calculations.js leaked: ${String(leaked)}`);
});

test("quizify-mapping leaks no globals", () => {
    const before = new Set(Reflect.ownKeys(globalThis));
    const { mapRecord } = require("../quizify-mapping");
    for (const fixture of loadFixtures("quizify-mapping")) mapRecord(fixture);
    const leaked = Reflect.ownKeys(globalThis).filter(k => !before.has(k));
    assert.deepStrictEqual(leaked, [], `quizify-mapping.js leaked: ${String(leaked)}`);
});
