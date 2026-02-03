#!/bin/bash
# Multi-step variant calling workflow
# INSTRUMENTED VERSION with pipewatch observability

set -euo pipefail

# === Pipewatch instrumentation ===
OBSRUN_PATH="${OBSRUN_PATH:-$(which obsrun 2>/dev/null || echo '../../src/pipewatch/obsrun.sh')}"
export PIPEWATCH_EVENTS_FILE="${PIPEWATCH_EVENTS_FILE:-./pipewatch-events/run.ndjson}"

# Ensure events directory exists
mkdir -p "$(dirname "$PIPEWATCH_EVENTS_FILE")"

# Wrapper function for observability
run_observed() {
    local step_name="$1"
    shift
    local cmd="$*"
    
    if [ -x "$OBSRUN_PATH" ]; then
        PIPEWATCH_STEP_NAME="$step_name" \
        PIPEWATCH_SAMPLE_ID="${SAMPLE_ID:-}" \
        "$OBSRUN_PATH" "$cmd"
    else
        echo "Warning: obsrun not found, running without observability" >&2
        eval "$cmd"
    fi
}
# === End Pipewatch instrumentation ===

# Configuration
INPUT_VCF="$1"
OUTPUT_PREFIX="${2:-output}"
REFERENCE="${REFERENCE:-/reference/hg38.fa}"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_PREFIX")"

echo "========================================"
echo "Variant Calling Pipeline (Instrumented)"
echo "Input: $INPUT_VCF"
echo "Output prefix: $OUTPUT_PREFIX"
echo "Reference: $REFERENCE"
echo "Events: $PIPEWATCH_EVENTS_FILE"
echo "========================================"

# Step 1: Normalize variants
echo "[Step 1/5] Normalizing variants..."
run_observed "normalize" "
    bcftools norm \\
        -f '${REFERENCE}' \\
        -m -any \\
        -O z \\
        -o '${OUTPUT_PREFIX}.norm.vcf.gz' \\
        '${INPUT_VCF}' && \\
    bcftools index '${OUTPUT_PREFIX}.norm.vcf.gz'
"
echo "[Step 1/5] Complete: ${OUTPUT_PREFIX}.norm.vcf.gz"

# Step 2: Filter by quality
echo "[Step 2/5] Filtering by quality..."
run_observed "filter" "
    bcftools filter \\
        -i 'QUAL>30 && INFO/DP>10' \\
        -O z \\
        -o '${OUTPUT_PREFIX}.filtered.vcf.gz' \\
        '${OUTPUT_PREFIX}.norm.vcf.gz' && \\
    bcftools index '${OUTPUT_PREFIX}.filtered.vcf.gz'
"
echo "[Step 2/5] Complete: ${OUTPUT_PREFIX}.filtered.vcf.gz"

# Step 3: Annotate with VEP
echo "[Step 3/5] Annotating variants..."
run_observed "annotate" "
    vep \\
        --input_file '${OUTPUT_PREFIX}.filtered.vcf.gz' \\
        --output_file '${OUTPUT_PREFIX}.vep.vcf.gz' \\
        --vcf \\
        --compress_output bgzip \\
        --cache \\
        --assembly GRCh38 \\
        --offline \\
        --force_overwrite
"
echo "[Step 3/5] Complete: ${OUTPUT_PREFIX}.vep.vcf.gz"

# Step 4: Extract sample statistics
echo "[Step 4/5] Extracting statistics..."
run_observed "stats" "
    bcftools stats \\
        '${OUTPUT_PREFIX}.filtered.vcf.gz' \\
        > '${OUTPUT_PREFIX}.stats.txt'
"
echo "[Step 4/5] Complete: ${OUTPUT_PREFIX}.stats.txt"

# Step 5: Generate summary report
echo "[Step 5/5] Generating summary report..."

# Create the Python script
python_script=$(cat << 'PYTHON_SCRIPT'
import json
import sys

output_prefix = sys.argv[1]

# Parse stats file
stats = {}
with open(f"{output_prefix}.stats.txt") as f:
    for line in f:
        if line.startswith("SN"):
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                key = parts[2].replace(":", "").replace(" ", "_")
                value = parts[2] if len(parts) == 3 else parts[3]
                stats[key] = value

# Write JSON summary
with open(f"{output_prefix}.summary.json", "w") as f:
    json.dump(stats, f, indent=2)
PYTHON_SCRIPT
)

run_observed "report" "
    python3 -c '${python_script}' '${OUTPUT_PREFIX}'
"
echo "[Step 5/5] Complete: ${OUTPUT_PREFIX}.summary.json"

echo "========================================"
echo "Pipeline complete!"
echo "Events written to: $PIPEWATCH_EVENTS_FILE"
echo "Generate report: pipewatch report $PIPEWATCH_EVENTS_FILE -o report/"
echo "========================================"
