"""Tests for event collection and serialization."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pipewatch.collector.events import (
    EventCollector,
    EventType,
    RunEvent,
    load_events,
)


class TestRunEvent:
    """Tests for RunEvent dataclass."""

    def test_basic_creation(self) -> None:
        """Test basic event creation."""
        event = RunEvent(
            event_type=EventType.START,
            command="echo hello",
        )
        assert event.event_type == EventType.START
        assert event.command == "echo hello"
        assert event.schema_version == "1.0.0"

    def test_serialization(self) -> None:
        """Test JSON serialization/deserialization."""
        event = RunEvent(
            event_type=EventType.END,
            command="echo hello",
            exit_code=0,
            duration_ms=1000,
            max_rss_kb=1024,
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["event_type"] == "end"
        assert data["command"] == "echo hello"
        assert data["exit_code"] == 0
        assert data["duration_ms"] == 1000
        assert data["max_rss_kb"] == 1024

    def test_deserialization(self) -> None:
        """Test deserialization from JSON."""
        json_str = json.dumps(
            {
                "schema_version": "1.0.0",
                "event_type": "start",
                "timestamp": "2024-01-01T00:00:00",
                "hostname": "test-host",
                "cwd": "/tmp",
                "command": "ls -la",
                "step_name": "list",
                "sample_id": "S001",
            }
        )

        event = RunEvent.from_json(json_str)
        assert event.event_type == EventType.START
        assert event.command == "ls -la"
        assert event.step_name == "list"
        assert event.sample_id == "S001"

    def test_slurm_env_capture(self) -> None:
        """Test SLURM environment variable capture."""
        env_vars = {
            "SLURM_JOB_ID": "12345",
            "SLURM_ARRAY_TASK_ID": "10",
            "SLURM_JOB_NAME": "test_job",
        }

        with pytest.MonkeyPatch().context() as mp:
            for key, value in env_vars.items():
                mp.setenv(key, value)

            event = RunEvent(
                event_type=EventType.START,
                command="test",
                slurm_job_id=os.environ.get("SLURM_JOB_ID"),
                slurm_array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
                slurm_job_name=os.environ.get("SLURM_JOB_NAME"),
            )

            assert event.slurm_job_id == "12345"
            assert event.slurm_array_task_id == "10"
            assert event.slurm_job_name == "test_job"


class TestEventCollector:
    """Tests for EventCollector."""

    def test_basic_collection(self, tmp_path: Path) -> None:
        """Test basic event collection."""
        output_file = tmp_path / "events.ndjson"

        with EventCollector(str(output_file)) as collector:
            collector.record_start(command="echo hello")
            collector.record_end(exit_code=0)

        assert output_file.exists()
        events = load_events(output_file)
        assert len(events) == 2
        assert events[0].event_type == EventType.START
        assert events[1].event_type == EventType.END

    def test_step_events(self, tmp_path: Path) -> None:
        """Test step-specific event recording."""
        output_file = tmp_path / "events.ndjson"

        with EventCollector(str(output_file)) as collector:
            collector.record_start(command="pipeline")
            collector.record_step_start(
                command="step1",
                step_name="align",
                sample_id="S001",
            )
            collector.record_step_end(
                step_name="align",
                exit_code=0,
                resource_usage={"max_rss_kb": 2048, "user_time_s": 1.5},
            )
            collector.record_end(exit_code=0)

        events = load_events(output_file)
        assert len(events) == 4

        step_start = events[1]
        assert step_start.event_type == EventType.STEP_START
        assert step_start.step_name == "align"
        assert step_start.sample_id == "S001"

        step_end = events[2]
        assert step_end.event_type == EventType.STEP_END
        assert step_end.max_rss_kb == 2048
        assert step_end.user_time_s == 1.5

    def test_duration_calculation(self, tmp_path: Path) -> None:
        """Test that duration is calculated correctly."""
        output_file = tmp_path / "events.ndjson"

        with EventCollector(str(output_file)) as collector:
            collector.record_start(command="sleep 0.1")
            import time

            time.sleep(0.1)
            collector.record_end(exit_code=0)

        events = load_events(output_file)
        end_event = events[1]
        assert end_event.duration_ms is not None
        assert end_event.duration_ms >= 100  # At least 100ms

    def test_resource_usage(self, tmp_path: Path) -> None:
        """Test resource usage recording."""
        output_file = tmp_path / "events.ndjson"

        resource_usage = {
            "max_rss_kb": 4096,
            "user_time_s": 2.5,
            "sys_time_s": 0.5,
            "wall_time_s": 3.0,
        }

        with EventCollector(str(output_file)) as collector:
            collector.record_start(command="heavy_task")
            collector.record_end(exit_code=0, resource_usage=resource_usage)

        events = load_events(output_file)
        end_event = events[1]
        assert end_event.max_rss_kb == 4096
        assert end_event.user_time_s == 2.5
        assert end_event.sys_time_s == 0.5
        assert end_event.wall_time_s == 3.0

    def test_file_creation_in_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        output_file = tmp_path / "subdir" / "nested" / "events.ndjson"

        with EventCollector(str(output_file)) as collector:
            collector.record_start(command="test")
            collector.record_end(exit_code=0)

        assert output_file.exists()


class TestLoadEvents:
    """Tests for load_events function."""

    def test_load_empty_file(self, tmp_path: Path) -> None:
        """Test loading from empty file."""
        output_file = tmp_path / "empty.ndjson"
        output_file.write_text("")

        events = load_events(output_file)
        assert events == []

    def test_load_multiple_events(self, tmp_path: Path) -> None:
        """Test loading multiple events."""
        output_file = tmp_path / "events.ndjson"

        events_data = [
            {
                "schema_version": "1.0.0",
                "event_type": "start",
                "timestamp": "2024-01-01T00:00:00",
                "hostname": "h1",
                "cwd": "/tmp",
                "command": "cmd1",
            },
            {
                "schema_version": "1.0.0",
                "event_type": "end",
                "timestamp": "2024-01-01T00:00:01",
                "hostname": "h1",
                "cwd": "/tmp",
                "command": "cmd1",
                "exit_code": 0,
            },
            {
                "schema_version": "1.0.0",
                "event_type": "start",
                "timestamp": "2024-01-01T00:00:02",
                "hostname": "h1",
                "cwd": "/tmp",
                "command": "cmd2",
            },
            {
                "schema_version": "1.0.0",
                "event_type": "end",
                "timestamp": "2024-01-01T00:00:03",
                "hostname": "h1",
                "cwd": "/tmp",
                "command": "cmd2",
                "exit_code": 1,
            },
        ]

        with open(output_file, "w") as f:
            for event in events_data:
                f.write(json.dumps(event) + "\n")

        events = load_events(output_file)
        assert len(events) == 4
        assert events[0].event_type == EventType.START
        assert events[1].exit_code == 0
        assert events[3].exit_code == 1
