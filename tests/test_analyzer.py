"""Tests for pipeline analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipewatch.collector.events import EventType, RunEvent
from pipewatch.reporter.analyzer import (
    FailureCluster,
    PipelineAnalyzer,
    PipelineSummary,
    SampleStats,
    StepStats,
)


class TestStepStats:
    """Tests for StepStats."""

    def test_creation(self) -> None:
        """Test creating StepStats."""
        stats = StepStats(
            step_name="align",
            count=10,
            total_duration_ms=50000,
            avg_duration_ms=5000.0,
            min_duration_ms=3000,
            max_duration_ms=8000,
            failures=1,
            avg_max_rss_kb=4096.0,
            max_max_rss_kb=8192,
        )
        
        assert stats.step_name == "align"
        assert stats.count == 10
        assert stats.avg_duration_ms == 5000.0
        assert stats.failures == 1


class TestPipelineAnalyzer:
    """Tests for PipelineAnalyzer."""

    @pytest.fixture
    def sample_events_file(self, tmp_path: Path) -> Path:
        """Create a sample events file for testing."""
        events = [
            # Sample 1 - Step 1
            RunEvent(
                event_type=EventType.STEP_START,
                timestamp="2024-01-01T00:00:00",
                command="align S1",
                step_name="align",
                sample_id="S1",
            ),
            RunEvent(
                event_type=EventType.STEP_END,
                timestamp="2024-01-01T00:00:10",
                step_name="align",
                sample_id="S1",
                exit_code=0,
                duration_ms=10000,
                max_rss_kb=4096,
            ),
            # Sample 1 - Step 2
            RunEvent(
                event_type=EventType.STEP_START,
                timestamp="2024-01-01T00:00:10",
                command="sort S1",
                step_name="sort",
                sample_id="S1",
            ),
            RunEvent(
                event_type=EventType.STEP_END,
                timestamp="2024-01-01T00:00:15",
                step_name="sort",
                sample_id="S1",
                exit_code=0,
                duration_ms=5000,
                max_rss_kb=2048,
            ),
            # Sample 2 - Step 1 (failure)
            RunEvent(
                event_type=EventType.STEP_START,
                timestamp="2024-01-01T00:00:00",
                command="align S2",
                step_name="align",
                sample_id="S2",
            ),
            RunEvent(
                event_type=EventType.STEP_END,
                timestamp="2024-01-01T00:00:05",
                step_name="align",
                sample_id="S2",
                exit_code=1,
                duration_ms=5000,
            ),
            # Sample 2 - Step 2
            RunEvent(
                event_type=EventType.STEP_START,
                timestamp="2024-01-01T00:00:05",
                command="sort S2",
                step_name="sort",
                sample_id="S2",
            ),
            RunEvent(
                event_type=EventType.STEP_END,
                timestamp="2024-01-01T00:00:12",
                step_name="sort",
                sample_id="S2",
                exit_code=0,
                duration_ms=7000,
                max_rss_kb=2048,
            ),
        ]
        
        file_path = tmp_path / "events.ndjson"
        with open(file_path, "w") as f:
            for event in events:
                f.write(event.to_json() + "\n")
        
        return file_path

    def test_analyze_basic(self, sample_events_file: Path) -> None:
        """Test basic analysis."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        assert summary.total_steps == 2  # align, sort
        assert summary.total_samples == 2  # S1, S2
        assert summary.total_duration_ms == 27000  # Sum of all durations

    def test_step_stats(self, sample_events_file: Path) -> None:
        """Test step statistics calculation."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        # Find align stats
        align_stats = next(s for s in summary.step_stats if s.step_name == "align")
        assert align_stats.count == 2
        assert align_stats.avg_duration_ms == 7500.0  # (10000 + 5000) / 2
        assert align_stats.failures == 1
        
        # Find sort stats
        sort_stats = next(s for s in summary.step_stats if s.step_name == "sort")
        assert sort_stats.count == 2
        assert sort_stats.failures == 0

    def test_sample_stats(self, sample_events_file: Path) -> None:
        """Test sample statistics calculation."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        # Find S1 stats
        s1_stats = next(s for s in summary.sample_stats if s.sample_id == "S1")
        assert s1_stats.step_count == 2
        assert s1_stats.total_duration_ms == 15000
        assert s1_stats.failures == 0
        
        # Find S2 stats
        s2_stats = next(s for s in summary.sample_stats if s.sample_id == "S2")
        assert s2_stats.failures == 1

    def test_slowest_steps(self, sample_events_file: Path) -> None:
        """Test slowest steps identification."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        # align should be slower than sort
        assert len(summary.slowest_steps) == 2
        assert summary.slowest_steps[0].step_name == "align"
        assert summary.slowest_steps[1].step_name == "sort"

    def test_failure_analysis(self, sample_events_file: Path) -> None:
        """Test failure analysis."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        assert summary.total_failures == 1
        assert summary.failure_rate == 0.25  # 1 failure out of 4 end events
        assert summary.failures_by_step.get("align") == 1

    def test_memory_hogs(self, sample_events_file: Path) -> None:
        """Test memory hog identification."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        assert len(summary.memory_hogs) == 2
        # align has higher memory
        assert summary.memory_hogs[0].step_name == "align"

    def test_empty_events(self, tmp_path: Path) -> None:
        """Test analysis with no events."""
        empty_file = tmp_path / "empty.ndjson"
        empty_file.write_text("")
        
        analyzer = PipelineAnalyzer([empty_file])
        summary = analyzer.analyze()
        
        assert summary.total_steps == 0
        assert summary.total_samples == 0

    def test_summary_to_dict(self, sample_events_file: Path) -> None:
        """Test summary dictionary conversion."""
        analyzer = PipelineAnalyzer([sample_events_file])
        summary = analyzer.analyze()
        
        data = summary.to_dict()
        
        assert data["run_id"] == "events"  # from filename
        assert data["total_steps"] == 2
        assert data["total_samples"] == 2
        assert "step_stats" in data
        assert "slowest_steps" in data
        assert "failures" in data


class TestPipelineComparison:
    """Tests for run-to-run comparison."""

    @pytest.fixture
    def baseline_file(self, tmp_path: Path) -> Path:
        """Create baseline events."""
        events = [
            RunEvent(
                event_type=EventType.STEP_END,
                step_name="align",
                exit_code=0,
                duration_ms=10000,
            ),
            RunEvent(
                event_type=EventType.STEP_END,
                step_name="sort",
                exit_code=0,
                duration_ms=5000,
            ),
        ]
        
        file_path = tmp_path / "baseline.ndjson"
        with open(file_path, "w") as f:
            for event in events:
                f.write(event.to_json() + "\n")
        
        return file_path

    @pytest.fixture
    def current_file(self, tmp_path: Path) -> Path:
        """Create current events (slower)."""
        events = [
            RunEvent(
                event_type=EventType.STEP_END,
                step_name="align",
                exit_code=0,
                duration_ms=12000,  # 20% slower
            ),
            RunEvent(
                event_type=EventType.STEP_END,
                step_name="sort",
                exit_code=0,
                duration_ms=6000,  # 20% slower
            ),
        ]
        
        file_path = tmp_path / "current.ndjson"
        with open(file_path, "w") as f:
            for event in events:
                f.write(event.to_json() + "\n")
        
        return file_path

    def test_comparison(self, baseline_file: Path, current_file: Path) -> None:
        """Test run-to-run comparison."""
        baseline = PipelineAnalyzer([baseline_file])
        current = PipelineAnalyzer([current_file])
        
        comparison = current.compare_runs(baseline)
        
        assert comparison["baseline_run"] == "baseline"
        assert comparison["current_run"] == "current"
        assert comparison["total_duration_change_ms"] == 3000  # (12000+6000) - (10000+5000)
        
        # Check step comparisons
        align_comp = next(c for c in comparison["step_comparisons"] if c["step_name"] == "align")
        assert align_comp["baseline_duration_ms"] == 10000
        assert align_comp["current_duration_ms"] == 12000
        assert align_comp["change_pct"] == 20.0  # (12000-10000)/10000 * 100
        assert align_comp["regression"] == True  # > 10%

        sort_comp = next(c for c in comparison["step_comparisons"] if c["step_name"] == "sort")
        assert sort_comp["change_pct"] == 20.0
