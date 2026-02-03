# Multi-Step Variant Calling Workflow

This example demonstrates instrumenting a sequential multi-step pipeline that doesn't use Slurm arrays but has distinct processing stages.

## Workflow Steps

1. **Normalize** - Normalize variants with bcftools norm
2. **Filter** - Filter by quality and depth
3. **Annotate** - Annotate with VEP
4. **Statistics** - Extract statistics with bcftools stats
5. **Report** - Generate summary JSON report

## Instrumentation Pattern

This example uses a `run_observed` function that wraps each step:

```bash
run_observed() {
    local step_name="$1"
    shift
    local cmd="$*"
    
    PIPEWATCH_STEP_NAME="$step_name" \
    "$OBSRUN_PATH" "$cmd"
}
```

Each step is executed as:
```bash
run_observed "step_name" "command_to_run"
```

## Usage

```bash
# Run with observability
export OBSRUN_PATH=/path/to/obsrun
./run_instrumented.sh input.vcf.gz output/prefix

# Generate report
pipewatch report pipewatch-events/run.ndjson -o report/
```

## Benefits

With this instrumentation, you can answer questions like:
- Which step is the bottleneck? (Step 3: VEP annotation typically)
- How does normalization affect file sizes?
- What's the memory profile of each step?
- Which steps fail most often?
