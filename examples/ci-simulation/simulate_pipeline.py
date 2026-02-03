#!/usr/bin/env python3
"""
Simulated pipeline for CI testing.

This script simulates a bioinformatics pipeline with realistic timing
and resource patterns, generating events without needing actual tools
like BWA or Slurm.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def generate_event(
    event_type: str,
    timestamp: datetime,
    step_name: str | None = None,
    sample_id: str | None = None,
    exit_code: int | None = None,
    duration_ms: int | None = None,
    max_rss_kb: int | None = None,
    **extra,
) -> dict:
    """Generate a single event."""
    event = {
        "schema_version": "1.0.0",
        "event_type": event_type,
        "timestamp": timestamp.isoformat() + "Z",
        "hostname": "ci-node-01",
        "cwd": str(Path.cwd()),
        "command": extra.get("command", f"step_{step_name}"),
        "git_commit": "abc123def456",
        "git_branch": "main",
    }
    
    if step_name:
        event["step_name"] = step_name
    if sample_id:
        event["sample_id"] = sample_id
    if exit_code is not None:
        event["exit_code"] = exit_code
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    if max_rss_kb is not None:
        event["max_rss_kb"] = max_rss_kb
    
    event.update(extra)
    return event


def simulate_step(
    step_name: str,
    sample_id: str,
    start_time: datetime,
    base_duration_ms: int,
    base_memory_kb: int,
    failure_rate: float = 0.05,
) -> tuple[list[dict], datetime]:
    """Simulate a single step for a sample."""
    events = []
    
    # Add some random variation
    duration_ms = int(base_duration_ms * random.uniform(0.8, 1.5))
    max_rss_kb = int(base_memory_kb * random.uniform(0.9, 1.2))
    
    # Determine if this step fails
    failed = random.random() < failure_rate
    exit_code = 1 if failed else 0
    
    # Record start
    events.append(generate_event(
        "start",
        start_time,
        step_name=step_name,
        sample_id=sample_id,
        command=f"{step_name} --sample {sample_id}",
    ))
    
    # Record end
    end_time = start_time + timedelta(milliseconds=duration_ms)
    events.append(generate_event(
        "end",
        end_time,
        step_name=step_name,
        sample_id=sample_id,
        exit_code=exit_code,
        duration_ms=duration_ms,
        max_rss_kb=max_rss_kb if not failed else None,
        user_time_s=duration_ms / 1000 * 0.8,
        sys_time_s=duration_ms / 1000 * 0.2,
        wall_time_s=duration_ms / 1000,
    ))
    
    return events, end_time


def simulate_pipeline(
    num_samples: int,
    output_path: Path,
    seed: int = 42,
) -> None:
    """Simulate a complete pipeline run."""
    random.seed(seed)
    
    # Define steps with realistic characteristics
    steps = [
        ("qc", 5000, 512 * 1024, 0.02),      # 5s, 512MB, 2% failure
        ("trim", 8000, 1024 * 1024, 0.01),   # 8s, 1GB, 1% failure
        ("align", 60000, 4096 * 1024, 0.05), # 60s, 4GB, 5% failure
        ("sort", 30000, 2048 * 1024, 0.02),  # 30s, 2GB, 2% failure
        ("markdup", 45000, 3072 * 1024, 0.03), # 45s, 3GB, 3% failure
        ("bqsr", 20000, 1536 * 1024, 0.01),  # 20s, 1.5GB, 1% failure
        ("hc", 120000, 5120 * 1024, 0.08),   # 120s, 5GB, 8% failure (HaplotypeCaller is slow)
    ]
    
    all_events = []
    current_time = datetime.now(timezone.utc)
    
    for sample_idx in range(1, num_samples + 1):
        sample_id = f"S{sample_idx:03d}"
        sample_start = current_time
        
        # Simulate array job offset
        sample_start += timedelta(seconds=random.randint(0, 30))
        
        step_time = sample_start
        
        for step_name, base_duration, base_memory, failure_rate in steps:
            # Simulate occasional skipped steps due to prior failure
            if step_time > sample_start + timedelta(minutes=5):
                break
            
            events, step_time = simulate_step(
                step_name,
                sample_id,
                step_time,
                base_duration,
                base_memory,
                failure_rate,
            )
            all_events.extend(events)
            
            # Add small gap between steps
            step_time += timedelta(milliseconds=random.randint(100, 500))
    
    # Sort events by timestamp
    all_events.sort(key=lambda e: e["timestamp"])
    
    # Write NDJSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for event in all_events:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")
    
    # Print summary
    num_events = len(all_events)
    num_failures = sum(1 for e in all_events if e.get("exit_code", 0) != 0)
    print(f"Simulated {num_samples} samples, {len(steps)} steps each")
    print(f"Generated {num_events} events ({num_failures} failures)")
    print(f"Output: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate pipeline for CI testing"
    )
    parser.add_argument(
        "-n", "--num-samples",
        type=int,
        default=10,
        help="Number of samples to simulate (default: 10)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("events.ndjson"),
        help="Output file path (default: events.ndjson)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    
    args = parser.parse_args()
    simulate_pipeline(args.num_samples, args.output, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
