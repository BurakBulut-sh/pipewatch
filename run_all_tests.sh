#!/bin/bash
# Comprehensive test runner for pipewatch

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           PIPEWATCH COMPREHENSIVE TEST SUITE               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Track overall results
total_passed=0
total_failed=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to run a test suite
run_suite() {
    local name=$1
    local script=$2
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if bash "$script"; then
        ((total_passed++))
        echo -e "${GREEN}✓ $name PASSED${NC}"
    else
        ((total_failed++))
        echo -e "${RED}✗ $name FAILED${NC}"
    fi
}

# Check we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from pipewatch root directory${NC}"
    echo "cd /path/to/pipewatch"
    exit 1
fi

# Check Python
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "Found Python $python_version"

# Check pipewatch is installed
echo ""
echo "Checking pipewatch installation..."
if ! which pipewatch > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ pipewatch not found in PATH${NC}"
    echo "Installing from current directory..."
    pip install -e "." --quiet
fi

if which pipewatch > /dev/null 2>&1; then
    echo -e "${GREEN}✓ pipewatch installed: $(which pipewatch)${NC}"
    pipewatch --version
else
    echo -e "${RED}✗ pipewatch installation failed${NC}"
    exit 1
fi

# Run test suites
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                     TEST EXECUTION                         ║"
echo "╚════════════════════════════════════════════════════════════╝"

run_suite "obsrun tests" "test_obsrun.sh"
run_suite "CLI tests" "test_cli.sh"

# Run Python unit tests
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running: Python unit tests (pytest)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if python3 -m pytest tests/ -q --tb=line 2>/dev/null; then
    ((total_passed++))
    echo -e "${GREEN}✓ Python unit tests PASSED${NC}"
else
    ((total_failed++))
    echo -e "${RED}✗ Python unit tests FAILED${NC}"
fi

# Run CI simulation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running: CI simulation example"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd examples/ci-simulation
if bash run_tests.sh > /tmp/ci_simulation.log 2>&1; then
    ((total_passed++))
    echo -e "${GREEN}✓ CI simulation PASSED${NC}"
    echo "  - Generated reports in examples/ci-simulation/report/"
else
    ((total_failed++))
    echo -e "${RED}✗ CI simulation FAILED${NC}"
    echo "  - See /tmp/ci_simulation.log for details"
fi
cd ../..

# Final summary
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                      FINAL RESULTS                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ $total_failed -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🎉 ALL TESTS PASSED! ($total_passed suites)               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Pipewatch is ready to use! Try these commands:"
    echo "  obsrun 'echo hello'"
    echo "  pipewatch run --step-name test 'echo test'"
    echo "  pipewatch report pipewatch-events.ndjson -o report/"
    echo ""
    echo "See INSTALL_AND_TEST.md for more examples."
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠ SOME TESTS FAILED ($total_failed of $((total_passed + total_failed)) suites)       ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Check the output above for details."
    exit 1
fi
