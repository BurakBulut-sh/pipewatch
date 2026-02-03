# Pipewatch - Complete Installation & Testing Guide

This guide will walk you through installing Pipewatch and testing every feature.

---

## 📋 Prerequisites

Before starting, make sure you have:

```bash
# Check Python version (needs 3.11+)
python3 --version

# Check you have pip
pip3 --version

# Check bash (for obsrun)
bash --version

# Optional but recommended: GNU time (for resource tracking)
# On Linux: usually already installed
# On macOS: install with `brew install gnu-time`
```

---

## 🔧 Installation Methods

### Method 1: Install from Source (Recommended for Testing)

```bash
# 1. Clone the repository
cd /Users/burakbulut/projects
git clone https://github.com/pipewatch/pipewatch.git
cd pipewatch

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install in development mode
pip install -e ".[dev]"

# 4. Verify installation
which pipewatch
which obsrun
pipewatch --version
```

### Method 2: Direct pip install (when published)

```bash
pip install pipewatch
```

### Method 3: Docker

```bash
# Build the image
docker build -t pipewatch .

# Run tests
docker run pipewatch
```

---

## 🧪 Quick Smoke Test

Run this to verify everything works:

```bash
# Test 1: Basic obsrun
rm -f pipewatch-events.ndjson
obsrun "echo hello world"
cat pipewatch-events.ndjson | head -2

# Test 2: pipewatch run
rm -f test_events.ndjson
pipewatch run --step-name test --sample-id S001 "echo success" --output test_events.ndjson

# Test 3: Generate report
pipewatch report test_events.ndjson -o quick_test_report --format both
ls -la quick_test_report/

# If all three work, you're good to go! ✅
```

---

## 🧪 Comprehensive Test Suite

### Test 1: Basic obsrun Tests

```bash
#!/bin/bash
# Save as: test_obsrun.sh

echo "========================================"
echo "Test 1: Basic obsrun functionality"
echo "========================================"

# Clean up
rm -f test_basic.ndjson

# Test 1.1: Simple command
echo "Test 1.1: Simple echo command"
PIPEWATCH_EVENTS_FILE=test_basic.ndjson obsrun "echo hello"
if [ -f test_basic.ndjson ]; then
    echo "✓ Events file created"
    count=$(wc -l < test_basic.ndjson)
    echo "  Events recorded: $count"
else
    echo "✗ Events file not created"
fi

# Test 1.2: Command with duration
echo ""
echo "Test 1.2: Command with duration"
rm -f test_duration.ndjson
PIPEWATCH_EVENTS_FILE=test_duration.ndjson obsrun "sleep 1"
duration=$(grep "duration_ms" test_duration.ndjson | tail -1 | grep -o '"duration_ms":[0-9]*' | cut -d: -f2)
if [ "$duration" -gt 900 ]; then
    echo "✓ Duration recorded: ${duration}ms (expected ~1000ms)"
else
    echo "✗ Duration seems wrong: ${duration}ms"
fi

# Test 1.3: Failed command
echo ""
echo "Test 1.3: Failed command capture"
rm -f test_fail.ndjson
PIPEWATCH_EVENTS_FILE=test_fail.ndjson obsrun "exit 42" || true
exit_code=$(grep "exit_code" test_fail.ndjson | tail -1 | grep -o '"exit_code":[0-9]*' | cut -d: -f2)
if [ "$exit_code" -eq 42 ]; then
    echo "✓ Exit code captured: $exit_code"
else
    echo "✗ Exit code not captured correctly: $exit_code"
fi

# Test 1.4: With environment variables
echo ""
echo "Test 1.4: Environment variables"
rm -f test_env.ndjson
PIPEWATCH_EVENTS_FILE=test_env.ndjson \
PIPEWATCH_STEP_NAME=alignment \
PIPEWATCH_SAMPLE_ID=patient_001 \
obsrun "echo test"
if grep -q "alignment" test_env.ndjson; then
    echo "✓ Step name captured"
else
    echo "✗ Step name not captured"
fi
if grep -q "patient_001" test_env.ndjson; then
    echo "✓ Sample ID captured"
else
    echo "✗ Sample ID not captured"
fi

echo ""
echo "========================================"
echo "obsrun tests complete!"
echo "========================================"
```

Run it:
```bash
bash test_obsrun.sh
```

---

### Test 2: CLI Tests

```bash
#!/bin/bash
# Save as: test_cli.sh

echo "========================================"
echo "Test 2: CLI functionality"
echo "========================================"

# Test 2.1: Wrap command
echo "Test 2.1: pipewatch wrap"
cat > /tmp/simple_script.sh << 'EOF'
#!/bin/bash
echo "Step 1"
echo "Step 2"
EOF
chmod +x /tmp/simple_script.sh

pipewatch wrap /tmp/simple_script.sh -o /tmp/wrapped_script.sh
if [ -f /tmp/wrapped_script.sh ]; then
    echo "✓ Wrapped script created"
    if grep -q "pipewatch" /tmp/wrapped_script.sh; then
        echo "✓ Pipewatch instrumentation present"
    fi
else
    echo "✗ Wrapped script not created"
fi

# Test 2.2: Run command
echo ""
echo "Test 2.2: pipewatch run"
rm -f /tmp/cli_run.ndjson
pipewatch run --step-name my_step --sample-id S001 --output /tmp/cli_run.ndjson "echo test"
if [ -f /tmp/cli_run.ndjson ]; then
    echo "✓ Events file created"
    count=$(grep -c "event_type" /tmp/cli_run.ndjson)
    echo "  Event count: $count"
else
    echo "✗ Events file not created"
fi

# Test 2.3: Report command
echo ""
echo "Test 2.3: pipewatch report"
rm -rf /tmp/cli_report
pipewatch report /tmp/cli_run.ndjson -o /tmp/cli_report --format both
if [ -f /tmp/cli_report/index.html ]; then
    echo "✓ HTML report created"
else
    echo "✗ HTML report not created"
fi
if [ -f /tmp/cli_report/data.json ]; then
    echo "✓ JSON data created"
else
    echo "✗ JSON data not created"
fi

# Test 2.4: Multiple files
echo ""
echo "Test 2.4: Multiple event files"
rm -f /tmp/multi_1.ndjson /tmp/multi_2.ndjson
pipewatch run --step-name step1 --output /tmp/multi_1.ndjson "echo file1"
pipewatch run --step-name step2 --output /tmp/multi_2.ndjson "echo file2"
rm -rf /tmp/multi_report
pipewatch report /tmp/multi_1.ndjson /tmp/multi_2.ndjson -o /tmp/multi_report
if [ -f /tmp/multi_report/index.html ]; then
    echo "✓ Multi-file report created"
else
    echo "✗ Multi-file report failed"
fi

echo ""
echo "========================================"
echo "CLI tests complete!"
echo "========================================"
```

Run it:
```bash
bash test_cli.sh
```

---

### Test 3: Run Python Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
cd /Users/burakbulut/projects/pipewatch
python3 -m pytest tests/ -v

# Run with coverage report
python3 -m pytest tests/ --cov=pipewatch --cov-report=html
```

---

### Test 4: Example Workflows

#### 4.1 CI Simulation (Fastest)

```bash
cd /Users/burakbulut/projects/pipewatch/examples/ci-simulation

# Run the complete test suite
bash run_tests.sh

# You should see:
# - 2 simulated pipeline runs generated
# - Individual report for run B
# - Comparison report (B vs A)
# - All verification checks passing

# Check the outputs
ls -la events/
ls -la report/
ls -la report_comparison/

# View the JSON data
cat report/data.json | python3 -m json.tool | head -30
```

#### 4.2 Multi-Step Workflow

```bash
cd /Users/burakbulut/projects/pipewatch/examples/multi-step-workflow

# Read the example scripts
cat run.sh
cat run_instrumented.sh

# Note: This won't actually run without bcftools/vep installed,
# but you can see how the instrumentation works
```

#### 4.3 Slurm Array Example

```bash
cd /Users/burakbulut/projects/pipewatch/examples/slurm-bwa-samtools

# Read the example
cat run.sh
cat run_instrumented.sh
cat samples.txt
```

---

## 🔬 Advanced Testing

### Test Resource Capture (Linux only)

On Linux systems with GNU time:

```bash
# Check if you have GNU time
/usr/bin/time --version | head -1

# If yes, test resource capture
rm -f /tmp/resource_test.ndjson
obsrun "python3 -c 'import time; time.sleep(2)'"

# Check if memory was captured
grep "max_rss_kb" pipewatch-events.ndjson
```

### Test Run-to-Run Comparison

```bash
#!/bin/bash
# Save as: test_comparison.sh

echo "Testing run comparison..."

# Create "baseline" run
rm -f /tmp/baseline.ndjson
for i in {1..5}; do
    PIPEWATCH_EVENTS_FILE=/tmp/baseline.ndjson \
        PIPEWATCH_STEP_NAME=step_$i \
        obsrun "sleep 0.1"
done

# Create "current" run (slightly different)
rm -f /tmp/current.ndjson
for i in {1..5}; do
    PIPEWATCH_EVENTS_FILE=/tmp/current.ndjson \
        PIPEWATCH_STEP_NAME=step_$i \
        obsrun "sleep 0.15"  # Slightly slower
done

# Generate comparison report
rm -rf /tmp/comparison_report
pipewatch report /tmp/current.ndjson -o /tmp/comparison_report --compare-with /tmp/baseline.ndjson

# Check results
echo "Comparison report files:"
ls -la /tmp/comparison_report/

# Look for comparison indicators in HTML
if grep -q "comparison" /tmp/comparison_report/index.html; then
    echo "✓ Comparison section present in HTML"
fi

echo "Done! Open /tmp/comparison_report/index.html to see the comparison"
```

---

## 🐛 Troubleshooting

### Issue: "obsrun: command not found"

```bash
# Make sure the package is installed
pip show pipewatch

# Check your PATH
echo $PATH

# If using a virtual environment, make sure it's activated
source venv/bin/activate

# Try running with full path
python3 -m pipewatch.obsrun "echo test"
```

### Issue: "No events being recorded"

```bash
# Check the events file path
echo $PIPEWATCH_EVENTS_FILE

# Set it explicitly
export PIPEWATCH_EVENTS_FILE=/tmp/my_events.ndjson
obsrun "echo test"
cat /tmp/my_events.ndjson
```

### Issue: "Report generation fails"

```bash
# Check if event file exists and has content
ls -la your_events.ndjson
wc -l your_events.ndjson

# Validate JSON
head -1 your_events.ndjson | python3 -c "import sys, json; print(json.loads(sys.stdin.read()))"

# Run with verbose output
pipewatch report your_events.ndjson -o output/ --format both
```

### Issue: Permission denied on obsrun.sh

```bash
# Make it executable
chmod +x /path/to/obsrun.sh

# Or use the Python wrapper instead
export PIPEWATCH_OBSRUN_PATH=/path/to/obsrun.sh
```

---

## ✅ Final Verification Checklist

Run through this checklist to ensure everything works:

- [ ] `pipewatch --version` shows version
- [ ] `obsrun --help` or `obsrun` shows usage
- [ ] `obsrun "echo test"` creates pipewatch-events.ndjson
- [ ] Events file contains valid JSON lines
- [ ] `pipewatch run` works with --step-name and --sample-id
- [ ] `pipewatch wrap` creates instrumented script
- [ ] `pipewatch report` generates HTML and JSON
- [ ] HTML report opens in browser and looks correct
- [ ] Report shows correct step/sample information
- [ ] All pytest tests pass (36 tests)
- [ ] CI simulation example runs successfully

---

## 🎯 Quick Test Commands

Want to test everything fast? Run this:

```bash
cd /Users/burakbulut/projects/pipewatch

# 1. Python tests
python3 -m pytest tests/ -q

# 2. CLI smoke test
rm -f /tmp/smoke.ndjson && \
pipewatch run --step-name smoke --sample-id TEST "echo smoke test" --output /tmp/smoke.ndjson && \
pipewatch report /tmp/smoke.ndjson -o /tmp/smoke_report && \
echo "✓ Smoke test passed"

# 3. Full CI simulation
cd examples/ci-simulation && bash run_tests.sh
```

---

## 📞 Getting Help

If something doesn't work:

1. Check this troubleshooting section
2. Look at the examples in `examples/`
3. Run with verbose output to see errors
4. Check the GitHub issues

---

## 🎉 You're Ready!

Once all tests pass, you're ready to use Pipewatch on your real pipelines!

Start with the CI simulation example, then try instrumenting one of your existing scripts.
