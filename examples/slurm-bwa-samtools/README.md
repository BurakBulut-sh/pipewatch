# BWA + Samtools Slurm Array Example

This example demonstrates instrumenting a typical bioinformatics workflow that uses:
- Slurm job arrays for parallel sample processing
- `srun` for resource allocation
- BWA-MEM for alignment
- Samtools for sorting and indexing

## Files

- `run.sh` - Original workflow script
- `run_instrumented.sh` - Instrumented version with pipewatch
- `samples.txt` - Sample manifest

## Instrumentation Approach

The instrumented version wraps each `srun` command with `obsrun` to capture:
- Step name (align, stats)
- Sample ID (from SLURM_ARRAY_TASK_ID)
- Timestamps and duration
- Resource usage (via `/usr/bin/time -v`)
- Exit codes
- SLURM job metadata

## Usage

### Original workflow:
```bash
sbatch --array=1-5 run.sh samples.txt /reference/hg38.fa
```

### Instrumented workflow:
```bash
# Set up obsrun path
export OBSRUN_PATH=/path/to/obsrun

# Submit array job
sbatch --array=1-5 run_instrumented.sh samples.txt /reference/hg38.fa

# Generate report after completion
pipewatch report pipewatch-events/*.ndjson -o report/
```

## Generating the Instrumented Script

Alternatively, you can auto-generate the instrumented script:

```bash
pipewatch wrap run.sh -o run_instrumented.sh
```

Note: Manual review and adjustment may be needed for complex pipelines.
