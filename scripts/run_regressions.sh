#!/bin/bash

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/.regression-output/latest"

SCRIPTS=(
  "scripts/check_posthoc_semantic_fixes.py"
  "scripts/check_proposition_regressions.py"
  "scripts/check_response_verification.py"
  "scripts/check_response_robustness.py"
  "scripts/check_chatgpt_real_responses.py"
)

rm -rf "$OUT"
mkdir -p "$OUT"

SUMMARY="$OUT/summary.txt"
FULL="$OUT/full.log"

: > "$SUMMARY"
: > "$FULL"

echo "Waiting for API..."

for i in {1..30}; do
  if curl -sf http://localhost:8000/health >/dev/null; then
    break
  fi

  sleep 1
done

if ! curl -sf http://localhost:8000/health >/dev/null; then
  echo "❌ API is not available at http://localhost:8000"
  exit 1
fi

echo "API ready"
echo

TOTAL=0
PASSED=0
FAILED=0

for SCRIPT in "${SCRIPTS[@]}"; do
  NAME="$(basename "$SCRIPT" .py)"
  LOG="$OUT/$NAME.log"

  TOTAL=$((TOTAL + 1))

  python3 "$ROOT/$SCRIPT" >"$LOG" 2>&1
  CODE=$?

  {
    echo
    echo "================================================================================"
    echo "$NAME"
    echo "================================================================================"
    cat "$LOG"
  } >> "$FULL"

  if [ "$CODE" -eq 0 ]; then
    STATUS="✅ PASS"
    PASSED=$((PASSED + 1))
  else
    STATUS="❌ FAIL"
    FAILED=$((FAILED + 1))
  fi

  echo "$STATUS  $NAME" | tee -a "$SUMMARY"

  grep -E \
    '^(POST-HOC|cases:|CASES:|RESULT|RESULTS|SUMMARY|.*[0-9]+/[0-9]+.*|.*passed.*|.*failed.*)' \
    "$LOG" \
    | tail -5 \
    | sed 's/^/    /' \
    | tee -a "$SUMMARY"

  if grep -q '^FAIL ' "$LOG"; then
    echo "    Failed cases:" | tee -a "$SUMMARY"

    grep '^FAIL ' "$LOG" \
      | sed 's/^/      /' \
      | tee -a "$SUMMARY"
  fi
done

{
  echo
  echo "Regression suite: $PASSED/$TOTAL scripts passed"
  echo "Failed scripts: $FAILED"
} | tee -a "$SUMMARY"

echo
echo "============================================================"
cat "$SUMMARY"
echo "============================================================"
echo
echo "Files:"
echo "  Summary: $SUMMARY"
echo "  Full log: $FULL"
echo
echo "Opening results folder in Finder..."

cat "$SUMMARY" | pbcopy
open "$OUT"

echo
echo "Summary copied to clipboard."
echo "Drag full.log into ChatGPT if you want me to inspect everything."

if [ "$FAILED" -gt 0 ]; then
  exit 1
fi
