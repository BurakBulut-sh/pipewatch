# CI Simulation Example

This example provides fast, deterministic pipeline simulation for continuous integration testing.

## Purpose

- **Fast**: Completes in seconds, not hours
- **Deterministic**: Same seed = same results
- **Realistic**: Simulates timing/memory patterns of real bioinformatics tools
- **No dependencies**: No BWA, samtools, or SLURM needed

## Simulated Steps

The simulation models a typical variant calling pipeline:

| Step | Base Duration | Base Memory | Failure Rate |
|------|---------------|-------------|--------------|
| qc | 5s | 512 MB | 2% |
| trim | 8s | 1 GB | 1% |
| align | 60s | 4 GB | 5% |
| sort | 30s | 2 GB | 2% |
| markdup | 45s | 3 GB | 3% |
| bqsr | 20s | 1.5 GB | 1% |
| hc | 120s | 5 GB | 8% |

## Usage

### Quick simulation:
```bash
python3 simulate_pipeline.py -n 10 -o events.ndjson
```

### With report generation:
```bash
./run_tests.sh
```

This will:
1. Generate two simulated runs (baseline + current)
2. Create HTML/JSON reports
3. Generate comparison report
4. Verify all outputs

### Custom simulation:
```bash
# More samples
python3 simulate_pipeline.py -n 100 -o large_run.ndjson --seed 42

# Different seed for variation
python3 simulate_pipeline.py -n 50 -o varied.ndjson --seed 999

# Generate report
pipewatch report varied.ndjson -o report/
```

## GitHub Actions Integration

See `.github/workflows/ci.yml` in the repository root for example CI configuration.
