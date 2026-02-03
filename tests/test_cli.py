"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pipewatch.cli import main, obsreport_main


class TestWrapCommand:
    """Tests for wrap command."""

    def test_wrap_basic(self, tmp_path: Path) -> None:
        """Test basic wrap functionality."""
        runner = CliRunner()
        
        # Create a simple script
        script = tmp_path / "run.sh"
        script.write_text("#!/bin/bash\nsrun bash -c 'echo hello'\n")
        
        output = tmp_path / "run_instrumented.sh"
        
        result = runner.invoke(main, ["wrap", str(script), "-o", str(output)])
        
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert "pipewatch" in content or "obsrun" in content

    def test_wrap_default_output(self, tmp_path: Path) -> None:
        """Test wrap with default output path."""
        runner = CliRunner()
        
        script = tmp_path / "run.sh"
        script.write_text("#!/bin/bash\necho hello\n")
        
        result = runner.invoke(main, ["wrap", str(script)])
        
        assert result.exit_code == 0
        assert (tmp_path / "run.instrumented.sh").exists()


class TestReportCommand:
    """Tests for report command."""

    @pytest.fixture
    def sample_events_file(self, tmp_path: Path) -> Path:
        """Create a sample events file."""
        from pipewatch.collector.events import EventCollector, EventType
        
        file_path = tmp_path / "events.ndjson"
        
        with EventCollector(str(file_path)) as collector:
            collector.record_start(command="test")
            collector.record_step_start(
                command="step1",
                step_name="align",
                sample_id="S1",
            )
            collector.record_step_end(
                step_name="align",
                exit_code=0,
                resource_usage={"max_rss_kb": 4096, "duration_ms": 10000},
            )
            collector.record_end(exit_code=0)
        
        return file_path

    def test_report_html(self, sample_events_file: Path, tmp_path: Path) -> None:
        """Test HTML report generation."""
        runner = CliRunner()
        
        output_dir = tmp_path / "report"
        result = runner.invoke(main, [
            "report",
            str(sample_events_file),
            "-o", str(output_dir),
            "--format", "html"
        ])
        
        assert result.exit_code == 0
        assert (output_dir / "index.html").exists()

    def test_report_json(self, sample_events_file: Path, tmp_path: Path) -> None:
        """Test JSON report generation."""
        runner = CliRunner()
        
        output_dir = tmp_path / "report"
        result = runner.invoke(main, [
            "report",
            str(sample_events_file),
            "-o", str(output_dir),
            "--format", "json"
        ])
        
        assert result.exit_code == 0
        assert (output_dir / "data.json").exists()
        
        # Verify it's valid JSON
        data = json.loads((output_dir / "data.json").read_text())
        assert "run_id" in data

    def test_report_both_formats(self, sample_events_file: Path, tmp_path: Path) -> None:
        """Test generation of both formats."""
        runner = CliRunner()
        
        output_dir = tmp_path / "report"
        result = runner.invoke(main, [
            "report",
            str(sample_events_file),
            "-o", str(output_dir),
            "--format", "both"
        ])
        
        assert result.exit_code == 0
        assert (output_dir / "index.html").exists()
        assert (output_dir / "data.json").exists()

    def test_report_directory_input(self, sample_events_file: Path, tmp_path: Path) -> None:
        """Test report generation from directory."""
        runner = CliRunner()
        
        # Move events to a subdirectory
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        sample_events_file.rename(events_dir / "run.ndjson")
        
        output_dir = tmp_path / "report"
        result = runner.invoke(main, [
            "report",
            str(events_dir),
            "-o", str(output_dir),
        ])
        
        assert result.exit_code == 0
        assert (output_dir / "index.html").exists()


class TestObsreportCommand:
    """Tests for obsreport legacy command."""

    def test_obsreport_basic(self, tmp_path: Path) -> None:
        """Test basic obsreport functionality."""
        from pipewatch.collector.events import EventCollector
        
        runner = CliRunner()
        
        # Create sample events
        events_file = tmp_path / "events.ndjson"
        with EventCollector(str(events_file)) as collector:
            collector.record_start(command="test")
            collector.record_end(exit_code=0)
        
        output = tmp_path / "report.html"
        result = runner.invoke(obsreport_main, [
            str(events_file),
            "-o", str(output)
        ])
        
        assert result.exit_code == 0
        assert output.exists()
        assert (tmp_path / "report.json").exists()


