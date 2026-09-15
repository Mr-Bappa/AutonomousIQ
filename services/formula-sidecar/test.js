/**
 * Manual smoke test. This sandbox has no npm registry access (same
 * constraint noted throughout the repo for pip), so this hasn't been run
 * against a real `npm install`. Run for real with:
 *   npm install && node test.js
 */
const formulajs = require("@formulajs/formulajs");

const cases = [
  { fn: "SUM", args: [1, 2, 3], expect: 6 },
  { fn: "AVERAGE", args: [2, 4, 6], expect: 4 },
  { fn: "IF", args: [true, "yes", "no"], expect: "yes" },
  { fn: "MAX", args: [3, 9, 1], expect: 9 },
];

let failures = 0;
for (const { fn, args, expect } of cases) {
  const impl = formulajs[fn];
  const result = impl(...args);
  const ok = result === expect;
  if (!ok) failures += 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${fn}(${args.join(", ")}) -> ${result} (expected ${expect})`);
}

if (failures > 0) {
  console.error(`${failures} failure(s)`);
  process.exit(1);
}
console.log("all smoke cases passed");
