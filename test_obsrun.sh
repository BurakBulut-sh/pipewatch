#!/bin/bash
# Test script for obsrun functionality

echo "========================================"
echo "Pipewatch obsrun Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

tests_passed=0
tests_failed=0

# Test 1: Basic echo command
echo "Test 1: Simple echo command"
rm -f /tmp/test_basic.ndjson
PIPEWATCH_EVENTS_FILE=/tmp/test_basic.ndjson obsrun "echo hello world" > /dev/null 2>&1
if [ -f /tmp/test_basic.ndjson ] && [ -s /tmp/test_basic.ndjson ]; then
    count=$(wc -l < /tmp/test_basic.ndjson)
    if [ "$count" -eq 2 ]; then
        echo -e "${GREEN}✓${NC} Events file created with $count events"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} Expected 2 events, got $count"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} Events file not created or empty"
    ((tests_failed++))
fi

# Test 2: Command duration
echo ""
echo "Test 2: Command with duration"
rm -f /tmp/test_duration.ndjson
PIPEWATCH_EVENTS_FILE=/tmp/test_duration.ndjson obsrun "sleep 0.5" > /dev/null 2>&1
duration=$(grep -o '"duration_ms":[0-9]*' /tmp/test_duration.ndjson | tail -1 | cut -d: -f2)
if [ -n "$duration" ] && [ "$duration" -gt 400 ]; then
    echo -e "${GREEN}✓${NC} Duration recorded: ${duration}ms (expected >400ms)"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Duration not recorded correctly: ${duration}ms"
    ((tests_failed++))
fi

# Test 3: Failed command
echo ""
echo "Test 3: Failed command capture"
rm -f /tmp/test_fail.ndjson
PIPEWATCH_EVENTS_FILE=/tmp/test_fail.ndjson obsrun "exit 42" > /dev/null 2>&1 || true
exit_code=$(grep -o '"exit_code":[0-9]*' /tmp/test_fail.ndjson | tail -1 | cut -d: -f2)
if [ "$exit_code" -eq 42 ]; then
    echo -e "${GREEN}✓${NC} Exit code captured: $exit_code"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Exit code not captured correctly: $exit_code"
    ((tests_failed++))
fi

# Test 4: Environment variables - step name
echo ""
echo "Test 4: Environment variables (step name)"
rm -f /tmp/test_env.ndjson
PIPEWATCH_EVENTS_FILE=/tmp/test_env.ndjson \
PIPEWATCH_STEP_NAME=alignment \
PIPEWATCH_SAMPLE_ID=patient_001 \
obsrun "echo test" > /dev/null 2>&1
if grep -q '"step_name":"alignment"' /tmp/test_env.ndjson; then
    echo -e "${GREEN}✓${NC} Step name captured"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Step name not captured"
    ((tests_failed++))
fi

# Test 5: Environment variables - sample ID
echo ""
echo "Test 5: Environment variables (sample ID)"
if grep -q '"sample_id":"patient_001"' /tmp/test_env.ndjson; then
    echo -e "${GREEN}✓${NC} Sample ID captured"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Sample ID not captured"
    ((tests_failed++))
fi

# Test 6: JSON validity
echo ""
echo "Test 6: JSON validity"
if python3 -c "import json; [json.loads(l) for l in open('/tmp/test_basic.ndjson')]" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} All events are valid JSON"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Invalid JSON found"
    ((tests_failed++))
fi

# Test 7: Schema version present
echo ""
echo "Test 7: Schema version"
if grep -q '"schema_version":"1.0.0"' /tmp/test_basic.ndjson; then
    echo -e "${GREEN}✓${NC} Schema version present"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Schema version missing"
    ((tests_failed++))
fi

# Test 8: Command string preserved
echo ""
echo "Test 8: Command string"
if grep -q '"command":"echo hello world"' /tmp/test_basic.ndjson; then
    echo -e "${GREEN}✓${NC} Command string preserved"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Command string not preserved"
    ((tests_failed++))
fi

# Summary
echo ""
echo "========================================"
echo "Test Results: $tests_passed passed, $tests_failed failed"
echo "========================================"

if [ $tests_failed -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed! ✗${NC}"
    exit 1
fi
