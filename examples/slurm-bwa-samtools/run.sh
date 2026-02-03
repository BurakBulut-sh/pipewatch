#!/bin/bash
# BWA-MEM + Samtools sort workflow for Slurm job arrays
# 
# Usage:
#   sbatch --array=1-10 run.sh samples.txt reference.fa
#
# samples.txt format (one per line):
#   sample1	/path/to/sample1_R1.fq.gz	/path/to/sample1_R2.fq.gz
#   sample2	/path/to/sample2_R1.fq.gz	/path/to/sample2_R2.fq.gz

set -euo pipefail

# Input validation
if [ $# -lt 2 ]; then
    echo "Usage: $0 <samples.txt> <reference.fa>"
    echo ""
    echo "samples.txt format (tab-delimited):"
    echo "  sample_id    path_to_R1    path_to_R2"
    exit 1
fi

SAMPLES_FILE="$1"
REFERENCE="$2"
OUTPUT_DIR="${OUTPUT_DIR:-./output}"

# Create output directory
mkdir -p "$OUTPUT_DIR/logs"

# Get sample info for this array task
if [ -n "${SLURM_ARRAY_TASK_ID:-}" ]; then
    # Running as array job
    SAMPLE_LINE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$SAMPLES_FILE")
else
    # Running as single job (for testing)
    SAMPLE_LINE=$(head -n1 "$SAMPLES_FILE")
fi

# Parse sample info
SAMPLE_ID=$(echo "$SAMPLE_LINE" | cut -f1)
R1=$(echo "$SAMPLE_LINE" | cut -f2)
R2=$(echo "$SAMPLE_LINE" | cut -f3)

echo "Processing sample: $SAMPLE_ID"
echo "R1: $R1"
echo "R2: $R2"
echo "Reference: $REFERENCE"

# Define output files
SORTED_BAM="$OUTPUT_DIR/${SAMPLE_ID}.sorted.bam"
STATS_FILE="$OUTPUT_DIR/${SAMPLE_ID}.flagstat"

# Step 1: Align with BWA and sort with samtools
# This is the critical step we'll want to observe
echo "[$SAMPLE_ID] Starting alignment..."

srun \
    --job-name="align_${SAMPLE_ID}" \
    --output="$OUTPUT_DIR/logs/${SAMPLE_ID}_align.log" \
    --error="$OUTPUT_DIR/logs/${SAMPLE_ID}_align.err" \
    bash -c "
        set -euo pipefail
        bwa mem -t \"\${SLURM_CPUS_PER_TASK:-4}\" \"${REFERENCE}\" \"${R1}\" \"${R2}\" | \\
            samtools sort -@ \"\${SLURM_CPUS_PER_TASK:-4}\" -m 2G -o \"${SORTED_BAM}\" -
        samtools index \"${SORTED_BAM}\"
    "

echo "[$SAMPLE_ID] Alignment complete: $SORTED_BAM"

# Step 2: Generate statistics
echo "[$SAMPLE_ID] Generating statistics..."

srun \
    --job-name="stats_${SAMPLE_ID}" \
    --output="$OUTPUT_DIR/logs/${SAMPLE_ID}_stats.log" \
    --error="$OUTPUT_DIR/logs/${SAMPLE_ID}_stats.err" \
    bash -c "
        samtools flagstat \"${SORTED_BAM}\" > \"${STATS_FILE}\"
        samtools idxstats \"${SORTED_BAM}\" > \"${OUTPUT_DIR}/${SAMPLE_ID}.idxstats\"
    "

echo "[$SAMPLE_ID] Statistics written to: $STATS_FILE"
echo "[$SAMPLE_ID] Processing complete!"
