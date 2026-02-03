#!/bin/bash
# Test script for pipewatch CLI

echo "========================================"
echo "Pipewatch CLI Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

tests_passed=0
tests_failed=0

# Test 1: Version check
echo "Test 1: Version check"
if pipewatch --version | grep -q "0.1.0"; then
    echo -e "${GREEN}✓${NC} Version command works"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Version command failed"
    ((tests_failed++))
fi

# Test 2: Wrap command
echo ""
echo "Test 2: pipewatch wrap"
cat > /tmp/simple_script.sh << 'EOF'
#!/bin/bash
echo "Step 1"
echo "Step 2"
EOF
chmod +x /tmp/simple_script.sh

rm -f /tmp/wrapped_script.sh
pipewatch wrap /tmp/simple_script.sh -o /tmp/wrapped_script.sh 2>/dev/null
if [ -f /tmp/wrapped_script.sh ]; then
    if grep -q "pipewatch\|obsrun" /tmp/wrapped_script.sh; then
        echo -e "${GREEN}✓${NC} Wrap creates instrumented script"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} Wrapped script missing instrumentation"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} Wrap failed to create output"
    ((tests_failed++))
fi

# Test 3: Run command
echo ""
echo "Test 3: pipewatch run"
rm -f /tmp/cli_run.ndjson
pipewatch run --step-name my_step --sample-id S001 --output /tmp/cli_run.ndjson "echo test" 2>/dev/null
if [ -f /tmp/cli_run.ndjson ]; then
    count=$(grep -c "event_type" /tmp/cli_run.ndjson)
    if [ "$count" -eq 2 ]; then
        echo -e "${GREEN}✓${NC} Run command creates events ($count events)"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} Wrong number of events: $count"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} Run command failed"
    ((tests_failed++))
fi

# Test 4: Report HTML generation
echo ""
echo "Test 4: HTML report generation"
rm -rf /tmp/cli_report
pipewatch report /tmp/cli_run.ndjson -o /tmp/cli_report --format html 2>/dev/null
if [ -f /tmp/cli_report/index.html ]; then
    if grep -q "Pipewatch" /tmp/cli_report/index.html; then
        echo -e "${GREEN}✓${NC} HTML report generated"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} HTML report content incorrect"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} HTML report not created"
    ((tests_failed++))
fi

# Test 5: Report JSON generation
echo ""
echo "Test 5: JSON report generation"
rm -rf /tmp/cli_report_json
pipewatch report /tmp/cli_run.ndjson -o /tmp/cli_report_json --format json 2>/dev/null
if [ -f /tmp/cli_report_json/data.json ]; then
    if python3 -c "import json; json.load(open('/tmp/cli_report_json/data.json'))" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} JSON report generated and valid"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} JSON report invalid"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} JSON report not created"
    ((tests_failed++))
fi

# Test 6: Both formats
echo ""
echo "Test 6: Both formats"
rm -rf /tmp/cli_report_both
pipewatch report /tmp/cli_run.ndjson -o /tmp/cli_report_both --format both 2>/dev/null
if [ -f /tmp/cli_report_both/index.html ] && [ -f /tmp/cli_report_both/data.json ]; then
    echo -e "${GREEN}✓${NC} Both formats generated"
    ((tests_passed++))
else
    echo -e "${RED}✗${NC} Both formats not created"
    ((tests_failed++))
fi

# Test 7: Multiple files
echo ""
echo "Test 7: Multiple event files"
rm -f /tmp/multi_1.ndjson /tmp/multi_2.ndjson
pipewatch run --step-name step1 --output /tmp/multi_1.ndjson "echo file1" 2>/dev/null
pipewatch run --step-name step2 --output /tmp/multi_2.ndjson "echo file2" 2>/dev/null
rm -rf /tmp/multi_report
pipewatch report /tmp/multi_1.ndjson /tmp/multi_2.ndjson -o /tmp/multi_report 2>/dev/null
if [ -f /tmp/multi_report/index.html ]; then
    steps=$(grep -o '"step_name": "[^"]*"' /tmp/multi_report/data.json 2>/dev/null | sort -u | wc -l)
    if [ "$steps" -ge 2 ]; then
        echo -e "${GREEN}✓${NC} Multiple files processed ($steps unique steps)"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} Not all steps captured"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} Multi-file report failed"
    ((tests_failed++))
fi

# Test 8: Report data content
echo ""
echo "Test 8: Report data content"
if [ -f /tmp/cli_report_json/data.json ]; then
    run_id=$(python3 -c "import json; print(json.load(open('/tmp/cli_report_json/data.json'))['run_id'])" 2>/dev/null)
    if [ -n "$run_id" ]; then
        echo -e "${GREEN}✓${NC} Report has run_id: $run_id"
        ((tests_passed++))
    else
        echo -e "${RED}✗${NC} Report missing run_id"
        ((tests_failed++))
    fi
else
    echo -e "${RED}✗${NC} Cannot check content, JSON missing"
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
