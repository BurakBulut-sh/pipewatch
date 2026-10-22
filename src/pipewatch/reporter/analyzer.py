"""Analysis engine for pipeline events.

Computes statistics and aggregations from collected events to answer
key observability questions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipewatch.collector.events import EventType, RunEvent, load_events


@dataclass(frozen=True)
class StepStats:
    """Statistics for a single step across all runs."""

    step_name: str
    count: int
    total_duration_ms: int
    avg_duration_ms: float
    min_duration_ms: int
    max_duration_ms: int
    failures: int
    avg_max_rss_kb: float | None = None
    max_max_rss_kb: int | None = None


@dataclass(frozen=True)
class SampleStats:
    """Statistics for a single sample across all steps."""

    sample_id: str
    step_count: int
    total_duration_ms: int
    avg_duration_ms: float
    min_duration_ms: int
    max_duration_ms: int
    failures: int


@dataclass(frozen=True)
class FailureCluster:
    """Cluster of failures by step or sample."""

    category: str  # "step" or "sample"
    name: str
    count: int
    exit_codes: dict[int, int] = field(default_factory=dict)
    recent_errors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PipelineSummary:
    """Summary of a pipeline run or set of runs.

    This is the main output of the analyzer, containing all computed
    statistics that can be rendered into various report formats.
    """

    # Basic info
    run_id: str
    total_steps: int
    total_samples: int
    total_duration_ms: int
    start_time: str | None = None
    end_time: str | None = None

    # Step statistics
    step_stats: list[StepStats] = field(default_factory=list)
    slowest_steps: list[StepStats] = field(default_factory=list)

    # Sample statistics
    sample_stats: list[SampleStats] = field(default_factory=list)
    sample_durations: list[SampleStats] = field(default_factory=list)

    # Failure analysis
    total_failures: int = 0
    failure_rate: float = 0.0
    failure_clusters: list[FailureCluster] = field(default_factory=list)
    failures_by_step: dict[str, int] = field(default_factory=dict)
    failures_by_sample: dict[str, int] = field(default_factory=dict)

    # Resource usage
    memory_hogs: list[StepStats] = field(default_factory=list)
    resource_summary: dict[str, Any] = field(default_factory=dict)

    # Queue vs run time (if SLURM data available)
    queue_time_stats: dict[str, Any] | None = None

    # Issues and warnings
    issues: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "total_steps": self.total_steps,
            "total_samples": self.total_samples,
            "total_duration_ms": self.total_duration_ms,
            "total_duration_human": self._format_duration(self.total_duration_ms),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "step_stats": [
                {
                    "step_name": s.step_name,
                    "count": s.count,
                    "avg_duration_ms": s.avg_duration_ms,
                    "avg_duration_human": self._format_duration(int(s.avg_duration_ms)),
                    "max_duration_ms": s.max_duration_ms,
                    "max_duration_human": self._format_duration(s.max_duration_ms),
                    "failures": s.failures,
                    "avg_max_rss_mb": round(s.avg_max_rss_kb / 1024, 2)
                    if s.avg_max_rss_kb
                    else None,
                    "max_max_rss_mb": round(s.max_max_rss_kb / 1024, 2)
                    if s.max_max_rss_kb
                    else None,
                }
                for s in self.step_stats
            ],
            "slowest_steps": [
                {
                    "step_name": s.step_name,
                    "avg_duration_ms": s.avg_duration_ms,
                    "avg_duration_human": self._format_duration(int(s.avg_duration_ms)),
                }
                for s in self.slowest_steps
            ],
            "sample_stats": [
                {
                    "sample_id": s.sample_id,
                    "step_count": s.step_count,
                    "total_duration_ms": s.total_duration_ms,
                    "total_duration_human": self._format_duration(s.total_duration_ms),
                    "failures": s.failures,
                }
                for s in self.sample_stats
            ],
            "failures": {
                "total": self.total_failures,
                "rate": round(self.failure_rate, 2),
                "by_step": self.failures_by_step,
                "by_sample": self.failures_by_sample,
            },
            "memory_hogs": [
                {
                    "step_name": s.step_name,
                    "max_rss_mb": round(s.max_max_rss_kb / 1024, 2) if s.max_max_rss_kb else None,
                    "avg_rss_mb": round(s.avg_max_rss_kb / 1024, 2) if s.avg_max_rss_kb else None,
                }
                for s in self.memory_hogs
            ],
            "resource_summary": self.resource_summary,
            "issues": self.issues,
        }

    @staticmethod
    def _format_duration(ms: int) -> str:
        """Format duration in milliseconds to human readable string."""
        if ms < 1000:
            return f"{ms}ms"
        seconds = ms / 1000
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f}m"
        hours = minutes / 60
        return f"{hours:.2f}h"


class PipelineAnalyzer:
    """Analyzes pipeline events to produce summary statistics.

    This class takes one or more event files and computes various
    aggregations and statistics useful for observability.
    """

    def __init__(self, event_paths: list[Path]):
        """Initialize analyzer with event files.

        Args:
            event_paths: Paths to NDJSON event files to analyze.
        """
        self.event_paths = event_paths
        self.all_events: list[RunEvent] = []
        self._load_events()

    def _load_events(self) -> None:
        """Load all events from the specified files."""
        for path in self.event_paths:
            if path.exists():
                self.all_events.extend(load_events(path))

    def analyze(self) -> PipelineSummary:
        """Analyze all events and produce a summary.

        Returns:
            PipelineSummary with computed statistics.
        """
        if not self.all_events:
            return PipelineSummary(
                run_id="empty", total_steps=0, total_samples=0, total_duration_ms=0
            )

        summary = PipelineSummary(
            run_id=self._derive_run_id(),
            total_steps=self._count_unique_steps(),
            total_samples=self._count_unique_samples(),
            total_duration_ms=self._compute_total_duration(),
            start_time=self._find_start_time(),
            end_time=self._find_end_time(),
        )

        # Compute step statistics
        summary.step_stats = self._compute_step_stats()
        summary.slowest_steps = sorted(
            summary.step_stats,
            key=lambda s: s.avg_duration_ms,
            reverse=True,
        )[:10]

        # Compute sample statistics
        summary.sample_stats = self._compute_sample_stats()
        summary.sample_durations = sorted(
            summary.sample_stats,
            key=lambda s: s.total_duration_ms,
            reverse=True,
        )

        # Failure analysis
        summary.total_failures = self._count_failures()
        # Count all end events (both END and STEP_END) for failure rate calculation
        all_end_events = [
            e for e in self.all_events if e.event_type in (EventType.END, EventType.STEP_END)
        ]
        summary.failure_rate = (
            summary.total_failures / len(all_end_events) if all_end_events else 0.0
        )
        summary.failures_by_step = self._failures_by_step()
        summary.failures_by_sample = self._failures_by_sample()
        summary.failure_clusters = self._compute_failure_clusters()

        # Memory analysis
        summary.memory_hogs = sorted(
            [s for s in summary.step_stats if s.max_max_rss_kb],
            key=lambda s: s.max_max_rss_kb or 0,
            reverse=True,
        )[:10]

        summary.resource_summary = self._compute_resource_summary()
        summary.issues = self._detect_issues()

        return summary

    def _derive_run_id(self) -> str:
        """Derive a run ID from events or paths."""
        # Try to get from first event
        for event in self.all_events:
            if event.slurm_job_id:
                return f"slurm-{event.slurm_job_id}"
        # Fall back to path-based ID
        if self.event_paths:
            return self.event_paths[0].stem
        return "unknown"

    def _count_unique_steps(self) -> int:
        """Count unique step names."""
        steps = set()
        for e in self.all_events:
            if e.step_name:
                steps.add(e.step_name)
        return len(steps)

    def _count_unique_samples(self) -> int:
        """Count unique sample IDs."""
        samples = set()
        for e in self.all_events:
            if e.sample_id:
                samples.add(e.sample_id)
        return len(samples)

    def _compute_total_duration(self) -> int:
        """Compute total duration across all runs."""
        total = 0
        for e in self.all_events:
            if e.duration_ms:
                total += e.duration_ms
        return total

    def _find_start_time(self) -> str | None:
        """Find earliest start timestamp."""
        timestamps = [e.timestamp for e in self.all_events if e.event_type == EventType.START]
        return min(timestamps) if timestamps else None

    def _find_end_time(self) -> str | None:
        """Find latest end timestamp."""
        timestamps = [e.timestamp for e in self.all_events if e.event_type == EventType.END]
        return max(timestamps) if timestamps else None

    def _compute_step_stats(self) -> list[StepStats]:
        """Compute statistics per step."""
        from collections import defaultdict

        step_data: dict[str, list[RunEvent]] = defaultdict(list)

        # Collect end events by step name
        # Only include events that have a step_name (skip generic END events without step_name)
        for e in self.all_events:
            if e.event_type == EventType.STEP_END or (
                e.event_type == EventType.END and e.step_name
            ):
                name = e.step_name or "unnamed"
                step_data[name].append(e)

        stats = []
        for step_name, events in step_data.items():
            durations = [e.duration_ms for e in events if e.duration_ms is not None]
            rss_values = [e.max_rss_kb for e in events if e.max_rss_kb is not None]
            failures = sum(1 for e in events if e.exit_code != 0)

            stats.append(
                StepStats(
                    step_name=step_name,
                    count=len(events),
                    total_duration_ms=sum(durations) if durations else 0,
                    avg_duration_ms=sum(durations) / len(durations) if durations else 0,
                    min_duration_ms=min(durations) if durations else 0,
                    max_duration_ms=max(durations) if durations else 0,
                    failures=failures,
                    avg_max_rss_kb=sum(rss_values) / len(rss_values) if rss_values else None,
                    max_max_rss_kb=max(rss_values) if rss_values else None,
                )
            )

        return sorted(stats, key=lambda s: s.total_duration_ms, reverse=True)

    def _compute_sample_stats(self) -> list[SampleStats]:
        """Compute statistics per sample."""
        from collections import defaultdict

        sample_data: dict[str, list[RunEvent]] = defaultdict(list)

        for e in self.all_events:
            if e.event_type in (EventType.END, EventType.STEP_END) and e.sample_id:
                sample_data[e.sample_id].append(e)

        stats = []
        for sample_id, events in sample_data.items():
            durations = [e.duration_ms for e in events if e.duration_ms is not None]
            failures = sum(1 for e in events if e.exit_code != 0)

            stats.append(
                SampleStats(
                    sample_id=sample_id,
                    step_count=len({e.step_name for e in events if e.step_name}),
                    total_duration_ms=sum(durations) if durations else 0,
                    avg_duration_ms=sum(durations) / len(durations) if durations else 0,
                    min_duration_ms=min(durations) if durations else 0,
                    max_duration_ms=max(durations) if durations else 0,
                    failures=failures,
                )
            )

        return sorted(stats, key=lambda s: s.total_duration_ms, reverse=True)

    def _count_failures(self) -> int:
        """Count total number of failures."""
        return sum(
            1
            for e in self.all_events
            if e.event_type in (EventType.END, EventType.STEP_END)
            and e.exit_code is not None
            and e.exit_code != 0
        )

    def _failures_by_step(self) -> dict[str, int]:
        """Count failures grouped by step."""
        from collections import defaultdict

        counts: dict[str, int] = defaultdict(int)

        for e in self.all_events:
            if (
                e.event_type in (EventType.END, EventType.STEP_END)
                and e.exit_code is not None
                and e.exit_code != 0
            ):
                name = e.step_name or "unnamed"
                counts[name] += 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def _failures_by_sample(self) -> dict[str, int]:
        """Count failures grouped by sample."""
        from collections import defaultdict

        counts: dict[str, int] = defaultdict(int)

        for e in self.all_events:
            if (
                e.event_type in (EventType.END, EventType.STEP_END)
                and e.exit_code is not None
                and e.exit_code != 0
                and e.sample_id
            ):
                counts[e.sample_id] += 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    def _compute_failure_clusters(self) -> list[FailureCluster]:
        """Compute failure clusters by step and sample."""
        clusters = []

        # Cluster by step
        for step_name, count in list(self._failures_by_step().items())[:5]:
            exit_codes: dict[int, int] = {}
            for e in self.all_events:
                if e.step_name == step_name and e.exit_code is not None and e.exit_code != 0:
                    exit_codes[e.exit_code] = exit_codes.get(e.exit_code, 0) + 1

            clusters.append(
                FailureCluster(
                    category="step",
                    name=step_name,
                    count=count,
                    exit_codes=exit_codes,
                )
            )

        # Cluster by sample
        for sample_id, count in list(self._failures_by_sample().items())[:5]:
            sample_exit_codes: dict[int, int] = {}
            for e in self.all_events:
                if e.sample_id == sample_id and e.exit_code is not None and e.exit_code != 0:
                    sample_exit_codes[e.exit_code] = sample_exit_codes.get(e.exit_code, 0) + 1

            if count > 0:
                clusters.append(
                    FailureCluster(
                        category="sample",
                        name=sample_id,
                        count=count,
                        exit_codes=sample_exit_codes,
                    )
                )

        return clusters

    def _compute_resource_summary(self) -> dict[str, Any]:
        """Compute overall resource usage summary."""
        all_rss = [e.max_rss_kb for e in self.all_events if e.max_rss_kb is not None]
        all_user_time = [e.user_time_s for e in self.all_events if e.user_time_s is not None]
        all_sys_time = [e.sys_time_s for e in self.all_events if e.sys_time_s is not None]

        return {
            "total_samples_with_memory": len(all_rss),
            "peak_memory_kb": max(all_rss) if all_rss else None,
            "avg_memory_kb": sum(all_rss) / len(all_rss) if all_rss else None,
            "total_user_time_s": sum(all_user_time) if all_user_time else None,
            "total_sys_time_s": sum(all_sys_time) if all_sys_time else None,
        }

    def _detect_issues(self) -> list[dict[str, Any]]:
        """Detect issues and warnings in the data."""
        issues = []

        # Check for missing resource metrics
        end_events = [
            e for e in self.all_events if e.event_type in (EventType.END, EventType.STEP_END)
        ]
        events_without_memory = sum(1 for e in end_events if e.max_rss_kb is None)
        if events_without_memory:
            pct = events_without_memory / len(end_events) * 100 if end_events else 0
            if pct > 50:
                issues.append(
                    {
                        "severity": "warning",
                        "type": "missing_memory_metrics",
                        "message": f"{pct:.0f}% of events lack memory metrics. Consider using /usr/bin/time -v.",
                    }
                )

        # Check for pipelines failing in pipes
        pipe_failures = [e for e in end_events if e.exit_code != 0 and e.exit_code != 1]
        if len(pipe_failures) > len(end_events) * 0.1:
            issues.append(
                {
                    "severity": "warning",
                    "type": "unusual_exit_codes",
                    "message": f"{len(pipe_failures)} events have unusual exit codes. Check pipefail settings.",
                }
            )

        return issues

    def compare_runs(self, other: PipelineAnalyzer) -> dict[str, Any]:
        """Compare this run with another run.

        Args:
            other: Another PipelineAnalyzer to compare against.

        Returns:
            Comparison dictionary with regression analysis.
        """
        this_summary = self.analyze()
        other_summary = other.analyze()

        # Compare step durations
        this_steps = {s.step_name: s for s in this_summary.step_stats}
        other_steps = {s.step_name: s for s in other_summary.step_stats}

        comparisons = []
        for step_name in set(this_steps.keys()) | set(other_steps.keys()):
            this_step = this_steps.get(step_name)
            other_step = other_steps.get(step_name)

            if this_step and other_step:
                change_pct = (
                    (this_step.avg_duration_ms - other_step.avg_duration_ms)
                    / other_step.avg_duration_ms
                    * 100
                    if other_step.avg_duration_ms > 0
                    else 0
                )
                comparisons.append(
                    {
                        "step_name": step_name,
                        "baseline_duration_ms": other_step.avg_duration_ms,
                        "current_duration_ms": this_step.avg_duration_ms,
                        "change_pct": round(change_pct, 2),
                        "regression": change_pct > 10,  # More than 10% slower
                        "improvement": change_pct < -10,  # More than 10% faster
                    }
                )
            elif this_step:
                comparisons.append(
                    {
                        "step_name": step_name,
                        "baseline_duration_ms": None,
                        "current_duration_ms": this_step.avg_duration_ms,
                        "change_pct": None,
                        "regression": False,
                        "improvement": False,
                        "note": "New step",
                    }
                )
            else:
                comparisons.append(
                    {
                        "step_name": step_name,
                        "baseline_duration_ms": other_step.avg_duration_ms if other_step else None,
                        "current_duration_ms": None,
                        "change_pct": None,
                        "regression": False,
                        "improvement": False,
                        "note": "Removed step",
                    }
                )

        return {
            "baseline_run": other_summary.run_id,
            "current_run": this_summary.run_id,
            "step_comparisons": sorted(
                comparisons, key=lambda x: x.get("change_pct") or 0, reverse=True
            ),
            "total_duration_change_ms": this_summary.total_duration_ms
            - other_summary.total_duration_ms,
            "failure_rate_change": round(this_summary.failure_rate - other_summary.failure_rate, 4),
        }
