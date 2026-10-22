"""Parser for /usr/bin/time -v output.

Parses the verbose output format from GNU time to extract resource usage metrics.
This is more portable than sacct and works on most Linux systems.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class TimeVData:
    """Resource usage data from /usr/bin/time -v.

    Fields are None if not available in the output.
    """

    # Time metrics
    user_time_s: float | None = None
    system_time_s: float | None = None
    elapsed_time_s: float | None = None
    cpu_percent: float | None = None

    # Memory metrics
    max_rss_kb: int | None = None
    avg_rss_kb: int | None = None
    avg_total_mem_kb: int | None = None
    avg_unshared_data_kb: int | None = None
    avg_stack_kb: int | None = None
    avg_shared_text_kb: int | None = None
    page_size_bytes: int | None = None

    # I/O metrics
    major_page_faults: int | None = None
    minor_page_faults: int | None = None
    voluntary_context_switches: int | None = None
    involuntary_context_switches: int | None = None
    swaps: int | None = None
    fs_inputs: int | None = None
    fs_outputs: int | None = None
    socket_msgs_sent: int | None = None
    socket_msgs_received: int | None = None
    signals_delivered: int | None = None

    # Exit status
    exit_status: int | None = None

    def to_resource_usage(self) -> dict[str, Any]:
        """Convert to the resource usage format expected by EventCollector."""
        return {
            "user_time_s": self.user_time_s,
            "sys_time_s": self.system_time_s,
            "wall_time_s": self.elapsed_time_s,
            "max_rss_kb": self.max_rss_kb,
        }


class TimeVParser:
    """Parser for /usr/bin/time -v output.

    Example usage:
        parser = TimeVParser()
        data = parser.parse(output_text)
        if data.max_rss_kb:
            print(f"Max RSS: {data.max_rss_kb} KB")
    """

    # Mapping of time-v output patterns to field names and converters
    PATTERNS: ClassVar[dict[str, Any]] = {
        # Time metrics
        r"User time \(seconds\): ([\d.]+)": ("user_time_s", float),
        r"System time \(seconds\): ([\d.]+)": ("system_time_s", float),
        r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)": (
            "elapsed_time_s",
            "elapsed",
        ),
        r"Percent of CPU this job got: (\d+)%": ("cpu_percent", int),
        # Memory metrics
        r"Maximum resident set size \(kbytes\): (\d+)": ("max_rss_kb", int),
        r"Average resident set size \(kbytes\): (\d+)": ("avg_rss_kb", int),
        r"Average total \(data\+stack\+text\) memory use \(kbytes\): (\d+)": (
            "avg_total_mem_kb",
            int,
        ),
        r"Average unshared data size \(kbytes\): (\d+)": ("avg_unshared_data_kb", int),
        r"Average stack size \(kbytes\): (\d+)": ("avg_stack_kb", int),
        r"Average shared text size \(kbytes\): (\d+)": ("avg_shared_text_kb", int),
        r"Page size \(bytes\): (\d+)": ("page_size_bytes", int),
        # I/O metrics
        r"Major \(requiring I/O\) page faults: (\d+)": ("major_page_faults", int),
        r"Minor \(reclaiming a frame\) page faults: (\d+)": ("minor_page_faults", int),
        r"Voluntary context switches: (\d+)": ("voluntary_context_switches", int),
        r"Involuntary context switches: (\d+)": ("involuntary_context_switches", int),
        r"Swaps: (\d+)": ("swaps", int),
        r"File system inputs: (\d+)": ("fs_inputs", int),
        r"File system outputs: (\d+)": ("fs_outputs", int),
        r"Socket messages sent: (\d+)": ("socket_msgs_sent", int),
        r"Socket messages received: (\d+)": ("socket_msgs_received", int),
        r"Signals delivered: (\d+)": ("signals_delivered", int),
        # Exit status
        r"Exit status: (\d+)": ("exit_status", int),
    }

    @classmethod
    def parse(cls, output: str) -> TimeVData:
        """Parse /usr/bin/time -v output.

        Args:
            output: The text output from /usr/bin/time -v.

        Returns:
            TimeVData object with extracted metrics.
        """
        data: dict[str, Any] = {}

        for pattern, (field_name, converter) in cls.PATTERNS.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                value_str = match.group(1)
                try:
                    if converter == "elapsed":
                        data[field_name] = cls._parse_elapsed_time(value_str)
                    elif callable(converter):
                        data[field_name] = converter(value_str)
                except (ValueError, TypeError):
                    # Skip values that can't be converted
                    pass

        return TimeVData(**data)

    @staticmethod
    def _parse_elapsed_time(time_str: str) -> float | None:
        """Parse elapsed time from time -v format.

        Handles formats like:
        - "1:23:45.67" (hours:minutes:seconds.decimals)
        - "23:45.67" (minutes:seconds.decimals)
        - "45.67" (seconds.decimals)
        """
        try:
            parts = time_str.split(":")
            if len(parts) == 3:
                # h:mm:ss
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                # m:ss
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                # Just seconds
                return float(parts[0])
        except (ValueError, IndexError):
            return None


def parse_time_v_output(output: str) -> dict[str, Any]:
    """Convenience function to parse time -v output to resource usage dict.

    Args:
        output: The text output from /usr/bin/time -v.

    Returns:
        Dictionary suitable for EventCollector.record_end().
    """
    data = TimeVParser.parse(output)
    return data.to_resource_usage()
