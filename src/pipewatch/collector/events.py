"""Event model and collector for pipeline observability.

Defines a strict event model with deterministic ordering and stable schema version.
Events are emitted as NDJSON (newline-delimited JSON) for easy streaming and parsing.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, TextIO


class EventType(Enum):
    """Types of events that can be recorded in a pipeline run."""

    START = "start"
    END = "end"
    STEP_START = "step_start"
    STEP_END = "step_end"


@dataclass(frozen=True)
class RunEvent:
    """A single event in a pipeline run.

    This is the core data structure for the event model. Events are immutable
    and can be serialized to/from JSON.

    Attributes:
        schema_version: Version of the event schema for compatibility checking.
        event_type: Type of event (start, end, step_start, step_end).
        timestamp: ISO 8601 timestamp when the event occurred.
        hostname: Hostname where the event was recorded.
        cwd: Current working directory.
        command: The command being executed.
        exit_code: Exit code of the command (only for end events).
        step_name: Optional name of the step (for multi-step workflows).
        sample_id: Optional sample identifier (for array tasks).
        slurm_job_id: SLURM_JOB_ID if available.
        slurm_array_task_id: SLURM_ARRAY_TASK_ID if available.
        slurm_job_name: SLURM_JOB_NAME if available.
        git_commit: Git commit hash if available.
        git_branch: Git branch name if available.
        duration_ms: Duration in milliseconds (for end events).
        max_rss_kb: Maximum resident set size in KB (if captured).
        user_time_s: User CPU time in seconds (if captured).
        sys_time_s: System CPU time in seconds (if captured).
        wall_time_s: Wall clock time in seconds (if captured).
        stdout_path: Path to stdout log file.
        stderr_path: Path to stderr log file.
        metadata: Additional arbitrary metadata.
    """

    schema_version: str = "1.0.0"
    event_type: EventType = EventType.START
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    hostname: str = field(default_factory=lambda: os.uname().nodename)
    cwd: str = field(default_factory=os.getcwd)
    command: str = ""
    exit_code: int | None = None
    step_name: str | None = None
    sample_id: str | None = None
    slurm_job_id: str | None = None
    slurm_array_task_id: str | None = None
    slurm_job_name: str | None = None
    git_commit: str | None = None
    git_branch: str | None = None
    duration_ms: int | None = None
    max_rss_kb: int | None = None
    user_time_s: float | None = None
    sys_time_s: float | None = None
    wall_time_s: float | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return json.dumps(data, separators=(",", ":"))

    @classmethod
    def from_json(cls, json_str: str) -> RunEvent:
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        data["event_type"] = EventType(data["event_type"])
        return cls(**data)

    def __post_init__(self) -> None:
        """Convert string event_type to enum after initialization."""
        if isinstance(self.event_type, str):
            object.__setattr__(self, "event_type", EventType(self.event_type))


class EventCollector:
    """Collects and writes events to an NDJSON file.

    This class provides a context manager for recording events in a pipeline run.
    Events are written immediately to the output file for durability.

    Example:
        with EventCollector("run.ndjson") as collector:
            collector.record_start()
            # ... run command ...
            collector.record_end(exit_code=0)
    """

    def __init__(
        self,
        output_path: str | Path,
        stdout_path: str | None = None,
        stderr_path: str | None = None,
    ):
        """Initialize the event collector.

        Args:
            output_path: Path to the NDJSON output file.
            stdout_path: Path to stdout log file (optional).
            stderr_path: Path to stderr log file (optional).
        """
        self.output_path = Path(output_path)
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self._file: TextIO | None = None
        self._start_time: datetime | None = None
        self._git_info: dict[str, str | None] = {}
        self._current_step_name: str | None = None
        self._current_sample_id: str | None = None

    def __enter__(self) -> EventCollector:
        """Open the output file and return self."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.output_path, "w")
        self._git_info = self._detect_git_info()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the output file."""
        if self._file:
            self._file.close()
            self._file = None

    def _detect_git_info(self) -> dict[str, str | None]:
        """Detect git commit and branch information."""
        try:
            import subprocess

            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                cwd=self.cwd,
            )
            if result.returncode != 0:
                return {"commit": None, "branch": None}

            # Get commit hash
            commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.cwd,
            )
            commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None

            # Get branch name
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.cwd,
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

            return {"commit": commit, "branch": branch}
        except Exception:
            return {"commit": None, "branch": None}

    @property
    def cwd(self) -> str:
        """Get current working directory."""
        return os.getcwd()

    @property
    def slurm_env(self) -> dict[str, str | None]:
        """Get SLURM environment variables."""
        return {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
            "slurm_job_name": os.environ.get("SLURM_JOB_NAME"),
        }

    def _write_event(self, event: RunEvent) -> None:
        """Write an event to the output file."""
        if self._file is None:
            raise RuntimeError("EventCollector not opened")
        self._file.write(event.to_json() + "\n")
        self._file.flush()

    def record_start(
        self,
        command: str,
        step_name: str | None = None,
        sample_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunEvent:
        """Record a start event.

        Args:
            command: The command being executed.
            step_name: Optional name of the step.
            sample_id: Optional sample identifier.
            metadata: Additional metadata to include.

        Returns:
            The recorded event.
        """
        self._start_time = datetime.now(UTC)
        self._current_step_name = step_name
        self._current_sample_id = sample_id
        event = RunEvent(
            event_type=EventType.START,
            command=command,
            step_name=step_name,
            sample_id=sample_id,
            git_commit=self._git_info.get("commit"),
            git_branch=self._git_info.get("branch"),
            stdout_path=self.stdout_path,
            stderr_path=self.stderr_path,
            slurm_job_id=self.slurm_env["slurm_job_id"],
            slurm_array_task_id=self.slurm_env["slurm_array_task_id"],
            slurm_job_name=self.slurm_env["slurm_job_name"],
            metadata=metadata or {},
        )
        self._write_event(event)
        return event

    def record_end(
        self,
        exit_code: int,
        resource_usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunEvent:
        """Record an end event.

        Args:
            exit_code: Exit code of the command.
            resource_usage: Resource usage metrics from /usr/bin/time or similar.
            metadata: Additional metadata to include.

        Returns:
            The recorded event.
        """
        duration_ms = None
        if self._start_time:
            duration = datetime.now(UTC) - self._start_time
            duration_ms = int(duration.total_seconds() * 1000)

        event = RunEvent(
            event_type=EventType.END,
            exit_code=exit_code,
            step_name=self._current_step_name,
            sample_id=self._current_sample_id,
            duration_ms=duration_ms,
            max_rss_kb=resource_usage.get("max_rss_kb") if resource_usage else None,
            user_time_s=resource_usage.get("user_time_s") if resource_usage else None,
            sys_time_s=resource_usage.get("sys_time_s") if resource_usage else None,
            wall_time_s=resource_usage.get("wall_time_s") if resource_usage else None,
            metadata=metadata or {},
        )
        self._write_event(event)
        return event

    def record_step_start(
        self,
        command: str,
        step_name: str,
        sample_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunEvent:
        """Record a step start event (for multi-step workflows).

        Args:
            command: The command being executed.
            step_name: Name of the step.
            sample_id: Optional sample identifier.
            metadata: Additional metadata to include.

        Returns:
            The recorded event.
        """
        event = RunEvent(
            event_type=EventType.STEP_START,
            command=command,
            step_name=step_name,
            sample_id=sample_id,
            git_commit=self._git_info.get("commit"),
            git_branch=self._git_info.get("branch"),
            stdout_path=self.stdout_path,
            stderr_path=self.stderr_path,
            slurm_job_id=self.slurm_env["slurm_job_id"],
            slurm_array_task_id=self.slurm_env["slurm_array_task_id"],
            slurm_job_name=self.slurm_env["slurm_job_name"],
            metadata=metadata or {},
        )
        self._write_event(event)
        return event

    def record_step_end(
        self,
        step_name: str,
        exit_code: int,
        resource_usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunEvent:
        """Record a step end event (for multi-step workflows).

        Args:
            step_name: Name of the step.
            exit_code: Exit code of the command.
            resource_usage: Resource usage metrics from /usr/bin/time or similar.
            metadata: Additional metadata to include.

        Returns:
            The recorded event.
        """
        event = RunEvent(
            event_type=EventType.STEP_END,
            step_name=step_name,
            exit_code=exit_code,
            max_rss_kb=resource_usage.get("max_rss_kb") if resource_usage else None,
            user_time_s=resource_usage.get("user_time_s") if resource_usage else None,
            sys_time_s=resource_usage.get("sys_time_s") if resource_usage else None,
            wall_time_s=resource_usage.get("wall_time_s") if resource_usage else None,
            metadata=metadata or {},
        )
        self._write_event(event)
        return event


def load_events(path: str | Path) -> list[RunEvent]:
    """Load events from an NDJSON file.

    Args:
        path: Path to the NDJSON file.

    Returns:
        List of RunEvent objects.
    """
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(RunEvent.from_json(line))
    return events
