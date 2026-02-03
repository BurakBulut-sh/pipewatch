#!/bin/bash
# Multi-step variant calling workflow
# A typical legacy bash pipeline with sequential steps

set -euo pipefail

# Configuration
INPUT_VCF="$1"
OUTPUT_PREFIX="${2:-output}"
REFERENCE="${REFERENCE:-/reference/hg38.fa}"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_PREFIX")"

echo "========================================"
echo "Variant Calling Pipeline"
echo "Input: $INPUT_VCF"
echo "Output prefix: $OUTPUT_PREFIX"
echo "Reference: $REFERENCE"
echo "========================================"

# Step 1: Normalize variants
echo "[Step 1/5] Normalizing variants..."
bcftools norm \
    -f "$REFERENCE" \
    -m -any \
    -O z \
    -o "${OUTPUT_PREFIX}.norm.vcf.gz" \
    "$INPUT_VCF"
bcftools index "${OUTPUT_PREFIX}.norm.vcf.gz"
echo "[Step 1/5] Complete: ${OUTPUT_PREFIX}.norm.vcf.gz"

# Step 2: Filter by quality
echo "[Step 2/5] Filtering by quality..."
bcftools filter \
    -i 'QUAL>30 && INFO/DP>10' \
    -O z \
    -o "${OUTPUT_PREFIX}.filtered.vcf.gz" \
    "${OUTPUT_PREFIX}.norm.vcf.gz"
bcftools index "${OUTPUT_PREFIX}.filtered.vcf.gz"
echo "[Step 2/5] Complete: ${OUTPUT_PREFIX}.filtered.vcf.gz"

# Step 3: Annotate with VEP
echo "[Step 3/5] Annotating variants..."
vep \
    --input_file "${OUTPUT_PREFIX}.filtered.vcf.gz" \
    --output_file "${OUTPUT_PREFIX}.vep.vcf.gz" \
    --vcf \
    --compress_output bgzip \
    --cache \
    --assembly GRCh38 \
    --offline \
    --force_overwrite
echo "[Step 3/5] Complete: ${OUTPUT_PREFIX}.vep.vcf.gz"

# Step 4: Extract sample statistics
echo "[Step 4/5] Extracting statistics..."
bcftools stats \
    "${OUTPUT_PREFIX}.filtered.vcf.gz" \
    > "${OUTPUT_PREFIX}.stats.txt"
echo "[Step 4/5] Complete: ${OUTPUT_PREFIX}.stats.txt"

# Step 5: Generate summary report
echo "[Step 5/5] Generating summary report..."
python3 << EOF
import json

# Parse stats file
stats = {}
with open("${OUTPUT_PREFIX}.stats.txt") as f:
    for line in f:
        if line.startswith("SN"):
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                key = parts[2].replace(":", "").replace(" ", "_")
                stats[key] = parts[2] if len(parts) == 3 else parts[3]

# Write JSON summary
with open("${OUTPUT_PREFIX}.summary.json", "w") as f:
    json.dump(stats, f, indent=2)
EOF
echo "[Step 5/5] Complete: ${OUTPUT_PREFIX}.summary.json"

echo "========================================"
echo "Pipeline complete!"
echo "Output files:"
echo "  - ${OUTPUT_PREFIX}.norm.vcf.gz"
echo "  - ${OUTPUT_PREFIX}.filtered.vcf.gz"
echo "  - ${OUTPUT_PREFIX}.vep.vcf.gz"
echo "  - ${OUTPUT_PREFIX}.stats.txt"
echo "  - ${OUTPUT_PREFIX}.summary.json"
echo "========================================"
