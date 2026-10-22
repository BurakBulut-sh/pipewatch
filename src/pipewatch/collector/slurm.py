"""SLURM environment detection and accounting integration."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SlurmEnv:
    """SLURM environment variables.

    Captures the standard SLURM environment variables that are set when
    running under SLURM job scheduling.
    """

    job_id: str | None = None
    array_task_id: str | None = None
    job_name: str | None = None
    partition: str | None = None
    nodelist: str | None = None
    cpus_per_task: str | None = None
    mem_per_cpu: str | None = None
    submit_dir: str | None = None
    submit_host: str | None = None
    ntasks: str | None = None

    @classmethod
    def from_environment(cls) -> SlurmEnv:
        """Create SlurmEnv from current environment variables."""
        return cls(
            job_id=os.environ.get("SLURM_JOB_ID"),
            array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
            job_name=os.environ.get("SLURM_JOB_NAME"),
            partition=os.environ.get("SLURM_JOB_PARTITION"),
            nodelist=os.environ.get("SLURM_JOB_NODELIST"),
            cpus_per_task=os.environ.get("SLURM_CPUS_PER_TASK"),
            mem_per_cpu=os.environ.get("SLURM_MEM_PER_CPU"),
            submit_dir=os.environ.get("SLURM_SUBMIT_DIR"),
            submit_host=os.environ.get("SLURM_SUBMIT_HOST"),
            ntasks=os.environ.get("SLURM_NTASKS"),
        )

    @property
    def is_slurm(self) -> bool:
        """Check if running under SLURM."""
        return self.job_id is not None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary."""
        return {
            "slurm_job_id": self.job_id,
            "slurm_array_task_id": self.array_task_id,
            "slurm_job_name": self.job_name,
            "slurm_partition": self.partition,
            "slurm_nodelist": self.nodelist,
            "slurm_cpus_per_task": self.cpus_per_task,
            "slurm_mem_per_cpu": self.mem_per_cpu,
        }


@dataclass(frozen=True)
class SacctData:
    """SLURM accounting data from sacct command.

    Provides detailed job accounting information when available.
    """

    job_id: str
    elapsed: str | None = None
    max_rss: str | None = None
    ave_cpu: str | None = None
    total_cpu: str | None = None
    req_mem: str | None = None
    alloc_cpus: str | None = None
    state: str | None = None
    exit_code: str | None = None
    start: str | None = None
    end: str | None = None
    queued_time: str | None = None

    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully."""
        return self.state == "COMPLETED"

    @property
    def max_rss_mb(self) -> int | None:
        """Parse max RSS to MB."""
        if not self.max_rss:
            return None
        value = self.max_rss.strip()
        # Handle suffixes like K, M, G, T
        multipliers = {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}
        for suffix, mult in multipliers.items():
            if value.upper().endswith(suffix):
                try:
                    return int(float(value[:-1]) * mult)
                except ValueError:
                    return None
        try:
            return int(float(value) / 1024)  # Assume bytes if no suffix
        except ValueError:
            return None


class SlurmAccounting:
    """Interface to SLURM accounting commands.

    Provides graceful fallbacks when sacct/sstat are not available
    or when the user doesn't have permission to use them.
    """

    def __init__(self) -> None:
        """Initialize and check command availability."""
        self._sacct_available: bool | None = None
        self._sstat_available: bool | None = None

    def _check_sacct(self) -> bool:
        """Check if sacct is available."""
        if self._sacct_available is None:
            try:
                result = subprocess.run(
                    ["sacct", "--version"],
                    capture_output=True,
                    timeout=5,
                )
                self._sacct_available = result.returncode == 0
            except (subprocess.SubprocessError, FileNotFoundError, PermissionError):
                self._sacct_available = False
        return self._sacct_available

    def _check_sstat(self) -> bool:
        """Check if sstat is available."""
        if self._sstat_available is None:
            try:
                result = subprocess.run(
                    ["sstat", "--version"],
                    capture_output=True,
                    timeout=5,
                )
                self._sstat_available = result.returncode == 0
            except (subprocess.SubprocessError, FileNotFoundError, PermissionError):
                self._sstat_available = False
        return self._sstat_available

    def get_job_stats(self, job_id: str) -> SacctData | None:
        """Get job statistics from sacct.

        Args:
            job_id: SLURM job ID.

        Returns:
            SacctData if available, None otherwise.
        """
        if not self._check_sacct():
            return None

        try:
            # Request specific fields for efficient parsing
            format_str = (
                "JobID,Elapsed,MaxRSS,AveCPU,TotalCPU,ReqMem,AllocCPUS,State,ExitCode,Start,End"
            )
            result = subprocess.run(
                [
                    "sacct",
                    "-j",
                    job_id,
                    "--format",
                    format_str,
                    "--noheader",
                    "-P",  # Parsable output (| delimited)
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            # Parse the first line (main job, not steps)
            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 10:
                    # Main job ID has no step suffix (no .batch, .0, etc.)
                    jid = parts[0].strip()
                    if jid == job_id or jid.startswith(f"{job_id}_"):
                        return SacctData(
                            job_id=jid,
                            elapsed=parts[1] if parts[1] else None,
                            max_rss=parts[2] if parts[2] else None,
                            ave_cpu=parts[3] if parts[3] else None,
                            total_cpu=parts[4] if parts[4] else None,
                            req_mem=parts[5] if parts[5] else None,
                            alloc_cpus=parts[6] if parts[6] else None,
                            state=parts[7] if parts[7] else None,
                            exit_code=parts[8] if parts[8] else None,
                            start=parts[9] if parts[9] else None,
                            end=parts[10] if len(parts) > 10 and parts[10] else None,
                        )
            return None
        except (subprocess.SubprocessError, TimeoutError, PermissionError):
            return None

    def get_running_stats(self, job_id: str) -> dict[str, Any] | None:
        """Get statistics for a running job from sstat.

        Args:
            job_id: SLURM job ID.

        Returns:
            Dictionary of statistics if available, None otherwise.
        """
        if not self._check_sstat():
            return None

        try:
            result = subprocess.run(
                [
                    "sstat",
                    "-j",
                    job_id,
                    "--format",
                    "JobID,MaxRSS,AveCPU",
                    "--noheader",
                    "-P",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None

            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = line.split("|")
                if len(parts) >= 3:
                    return {
                        "job_id": parts[0].strip(),
                        "max_rss": parts[1].strip() if parts[1] else None,
                        "ave_cpu": parts[2].strip() if parts[2] else None,
                    }
            return None
        except (subprocess.SubprocessError, TimeoutError, PermissionError):
            return None
