#!/bin/bash
# CI test runner for pipewatch
# Simulates pipeline runs and verifies report generation

set -euo pipefail

cd "$(dirname "$0")"

echo "========================================"
echo "Pipewatch CI Simulation"
echo "========================================"

# Clean up previous runs
rm -rf events/ report/

echo ""
echo "[1/5] Simulating pipeline run A (baseline)..."
python3 simulate_pipeline.py -n 20 -o events/run_a.ndjson --seed 100
echo "✓ Generated run A with 20 samples"

echo ""
echo "[2/5] Simulating pipeline run B (current, slightly slower)..."
python3 simulate_pipeline.py -n 20 -o events/run_b.ndjson --seed 200
echo "✓ Generated run B with 20 samples"

echo ""
echo "[3/5] Generating report for run B..."
pipewatch report events/run_b.ndjson -o report/ --format both
echo "✓ Report generated in report/"

echo ""
echo "[4/5] Generating comparison report (B vs A)..."
pipewatch report events/run_b.ndjson -o report_comparison/ --format both --compare-with events/run_a.ndjson
echo "✓ Comparison report generated in report_comparison/"

echo ""
echo "[5/5] Verifying outputs..."

# Check HTML report
if [ -f "report/index.html" ]; then
    echo "✓ HTML report exists"
else
    echo "✗ HTML report missing"
    exit 1
fi

# Check JSON data
if [ -f "report/data.json" ]; then
    echo "✓ JSON data exists"
    # Verify it's valid JSON
    python3 -c "import json; json.load(open('report/data.json'))"
    echo "✓ JSON is valid"
else
    echo "✗ JSON data missing"
    exit 1
fi

# Check comparison report
if [ -f "report_comparison/index.html" ]; then
    echo "✓ Comparison HTML report exists"
else
    echo "✗ Comparison HTML report missing"
    exit 1
fi

echo ""
echo "========================================"
echo "All CI tests passed!"
echo "========================================"
echo ""
echo "View reports:"
echo "  open report/index.html"
echo "  open report_comparison/index.html"
