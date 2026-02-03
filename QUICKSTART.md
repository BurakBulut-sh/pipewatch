# Pipewatch Quick Start Guide

## Install & Test in 5 Minutes

### Step 1: Install

```bash
cd /Users/burakbulut/projects/pipewatch
pip3 install -e "." --break-system-packages
```

### Step 2: Run Quick Tests

```bash
# Run everything
bash run_all_tests.sh

# Or run individual test suites
bash test_obsrun.sh    # Tests obsrun wrapper
bash test_cli.sh       # Tests CLI commands
```

### Step 3: Try It Yourself

```bash
# Simple test
obsrun "echo hello world"
cat pipewatch-events.ndjson

# With metadata
pipewatch run --step-name alignment --sample-id S001 "echo processing" --output myevents.ndjson

# Generate report
pipewatch report myevents.ndjson -o report/ --format both

# Generate report with job-based naming (e.g., slurm-12345.html)
pipewatch report myevents.ndjson -o report/ --format both --job-named

# View report
open report/index.html  # On Mac (default naming)
# OR
open report/myevents.html  # On Mac (job-named)
# OR
xdg-open report/index.html  # On Linux
```

### Step 4: Run Full Example

```bash
cd examples/ci-simulation
bash run_tests.sh

# View generated reports
open report/index.html
open report_comparison/index.html
```

## What Each Test Does

| Test | What It Verifies |
|------|------------------|
| `test_obsrun.sh` | Bash wrapper records events correctly |
| `test_cli.sh` | All CLI commands work (wrap, run, report) |
| `pytest tests/` | Python code unit tests (36 tests) |
| `run_tests.sh` | Full CI simulation with 20 samples |

## Expected Output

All tests should show green ✓ marks:

```
========================================
Test Results: 8 passed, 0 failed
========================================
All tests passed! ✓
```

## Troubleshooting

If any test fails:

1. Make sure you're in the pipewatch directory
2. Ensure Python 3.11+ is installed: `python3 --version`
3. Reinstall: `pip3 install -e "." --break-system-packages`
4. Check specific test output for error messages

## Next Steps

Once all tests pass, read:
- `README_ELI5.md` - Easy explanation of how it works
- `HOW_IT_WORKS.md` - Technical details
- `INSTALL_AND_TEST.md` - Comprehensive guide
