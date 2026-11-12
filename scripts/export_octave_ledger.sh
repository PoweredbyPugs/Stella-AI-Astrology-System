#!/bin/sh
# Dump the Octave page's text tables (ledger.js + briefs.js) to JSON for Stella's Python port.
# Read only on the octave repo. Usage: sh scripts/export_octave_ledger.sh [out.json]
STELLA="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$STELLA/data/octave_ledger.json}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
cd "${OCTAVE_REPO:-/Volumes/Shirahoshi/HermesNode/octave}" || exit 1
OUT="$OUT" node -e '
const fs = require("node:fs"), vm = require("node:vm"), cp = require("node:child_process");
const NAMES = ["BRIEF","CONDITION","COND_CLAUSE","HOUSES","RELATION_WORD","FLOW_WORD","PAIRS","VERB","TENDING","STAR","LPOINTS","LLINKS","LRULES","LREADINGS","LLOG","LARCHIVE"];
// STAR is a closure constant in briefs.js, not a global: defined here from the spec.
const STAR = { 1: "White Water", 2: "Black Earth", 3: "Jade Wood", 4: "Green Wood", 5: "Yellow Earth", 6: "White Metal", 7: "Red Metal", 8: "White Earth", 9: "Purple Fire" };
// Same technique as lib/forecast.js texts(): both files in one bare context; names that are not globals come back null.
const probe = NAMES.map(n => `typeof ${n} === "undefined" ? null : ${n}`).join(",");
const src = fs.readFileSync("src/ledger.js", "utf8") + "\n" + fs.readFileSync("src/briefs.js", "utf8") + "\n;([" + probe + "])";
const vals = vm.runInNewContext(src, {}, { filename: "briefs.js" });
const out = {};
NAMES.forEach((n, i) => { out[n] = vals[i]; });
if (out.STAR === null) out.STAR = STAR;
out.exported = new Date().toISOString();
out.source = cp.execSync("git rev-parse --short HEAD").toString().trim();
fs.writeFileSync(process.env.OUT, JSON.stringify(out, null, 1) + "\n");
'
