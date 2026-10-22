"""Tests for output parsers."""

from __future__ import annotations

from pipewatch.parsers.time_v import TimeVData, TimeVParser


class TestTimeVParser:
    """Tests for /usr/bin/time -v parser."""

    # Sample output from /usr/bin/time -v
    SAMPLE_OUTPUT = """
	Command being timed: "sleep 1"
	User time (seconds): 0.00
	System time (seconds): 0.00
	Percent of CPU this job got: 0%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.00
	Average shared text size (kbytes): 0
	Average unshared data size (kbytes): 0
	Average stack size (kbytes): 0
	Average total size (kbytes): 0
	Maximum resident set size (kbytes): 2048
	Average resident set size (kbytes): 0
	Major (requiring I/O) page faults: 0
	Minor (reclaiming a frame) page faults: 153
	Voluntary context switches: 2
	Involuntary context switches: 0
	Swaps: 0
	File system inputs: 0
	File system outputs: 0
	Socket messages sent: 0
	Socket messages received: 0
	Signals delivered: 0
	Page size (bytes): 4096
	Exit status: 0
"""

    LONG_RUNNING_OUTPUT = """
	Command being timed: "sleep 123"
	User time (seconds): 0.01
	System time (seconds): 0.02
	Percent of CPU this job got: 0%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 2:03.00
	Maximum resident set size (kbytes): 8192
	Exit status: 0
"""

    def test_parse_basic(self) -> None:
        """Test parsing basic time -v output."""
        data = TimeVParser.parse(self.SAMPLE_OUTPUT)

        assert data.user_time_s == 0.00
        assert data.system_time_s == 0.00
        assert data.elapsed_time_s == 1.0  # 0:01.00
        assert data.max_rss_kb == 2048
        assert data.exit_status == 0

    def test_parse_long_running(self) -> None:
        """Test parsing output with longer elapsed time."""
        data = TimeVParser.parse(self.LONG_RUNNING_OUTPUT)

        assert data.user_time_s == 0.01
        assert data.system_time_s == 0.02
        # 2:03.00 = 123 seconds
        assert data.elapsed_time_s == 123.0
        assert data.max_rss_kb == 8192

    def test_parse_empty(self) -> None:
        """Test parsing empty output."""
        data = TimeVParser.parse("")

        assert data.user_time_s is None
        assert data.max_rss_kb is None
        assert data.exit_status is None

    def test_parse_partial(self) -> None:
        """Test parsing partial output."""
        partial = """
	User time (seconds): 5.5
	Maximum resident set size (kbytes): 10240
"""
        data = TimeVParser.parse(partial)

        assert data.user_time_s == 5.5
        assert data.max_rss_kb == 10240
        assert data.system_time_s is None
        assert data.elapsed_time_s is None

    def test_elapsed_time_formats(self) -> None:
        """Test various elapsed time formats."""
        # H:MM:SS format
        output1 = "Elapsed (wall clock) time (h:mm:ss or m:ss): 1:30:45"
        data1 = TimeVParser.parse(output1)
        assert data1.elapsed_time_s == 5445.0  # 1*3600 + 30*60 + 45

        # M:SS format
        output2 = "Elapsed (wall clock) time (h:mm:ss or m:ss): 5:30.5"
        data2 = TimeVParser.parse(output2)
        assert data2.elapsed_time_s == 330.5  # 5*60 + 30.5

        # Just seconds
        output3 = "Elapsed (wall clock) time (h:mm:ss or m:ss): 45.123"
        data3 = TimeVParser.parse(output3)
        assert data3.elapsed_time_s == 45.123

    def test_to_resource_usage(self) -> None:
        """Test conversion to resource usage dict."""
        data = TimeVParser.parse(self.SAMPLE_OUTPUT)
        usage = data.to_resource_usage()

        assert usage["user_time_s"] == 0.00
        assert usage["sys_time_s"] == 0.00
        assert usage["wall_time_s"] == 1.0
        assert usage["max_rss_kb"] == 2048


class TestTimeVData:
    """Tests for TimeVData dataclass."""

    def test_creation(self) -> None:
        """Test creating TimeVData."""
        data = TimeVData(
            user_time_s=1.5,
            system_time_s=0.5,
            max_rss_kb=4096,
        )

        assert data.user_time_s == 1.5
        assert data.system_time_s == 0.5
        assert data.max_rss_kb == 4096

    def test_optional_fields(self) -> None:
        """Test that fields are optional."""
        data = TimeVData()

        assert data.user_time_s is None
        assert data.max_rss_kb is None
