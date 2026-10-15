#!/bin/bash
# Usage: trexsim-save-result.sh <alphaNum> <json-file-or-stdin>
# Reads metrics JSON and updates markdown
set -e
N="$1"
JSON="$2"
if [ -z "$N" ] || [ -z "$JSON" ]; then echo "Usage: $0 <num> <json-file>"; exit 1; fi
DIR="$(cd "$(dirname "$0")/.." && pwd)"
id=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.id||'')")
IR=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.IR||'n/a')")
if [ -z "$id" ] || [ "$id" = "undefined" ]; then echo "No ID for alpha $N"; exit 1; fi
window=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.window||'n/a')")
TVR=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.TVR||'n/a')")
DD=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.DD||'n/a')")
Ret=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.Ret||'n/a')")
IRSqrt=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.IRSqrt||'n/a')")
Booksize=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.Booksize||'n/a')")
NumStks=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.NumStks||'n/a')")
Liq=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.Liq||'n/a')")
LiqN=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.LiqN||'n/a')")
Region=$(node -e "const j=JSON.parse(require('fs').readFileSync('$JSON','utf8')); console.log(j.Region||'n/a')")
clears=$(node -e "const ir=parseFloat('$IR'); console.log(ir>0.07?'clears':'does not clear')")
note="Fast OS run completed; IR $IR $clears the 0.07 qualifying bar."
node "$DIR/scripts/trexsim-update-results.js" "$N" "$id" "$window" "$IR" "$TVR" "$DD" "$Ret" "$IRSqrt" "$Booksize" "$NumStks" "$Liq" "$LiqN" "$Region" "$note"
