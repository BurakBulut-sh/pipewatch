#!/usr/bin/env bash
# obsrun - Lightweight bash wrapper for pipeline observability
# 
# This script wraps arbitrary commands and emits structured run events
# for consumption by pipewatch report.
#
# Usage:
#   obsrun "command to execute"
#   PIPEWATCH_STEP_NAME=align PIPEWATCH_SAMPLE_ID=S1 obsrun "bwa mem ref.fa reads.fq"
#
# Environment variables:
#   PIPEWATCH_EVENTS_FILE    Output file for events (default: pipewatch-events.ndjson)
#   PIPEWATCH_STEP_NAME      Name of the step being executed
#   PIPEWATCH_SAMPLE_ID      Sample identifier
#   PIPEWATCH_STDOUT_PATH    Path to stdout log file
#   PIPEWATCH_STDERR_PATH    Path to stderr log file
#   PIPEWATCH_CAPTURE_TIME   Set to "1" to capture time output (default: 1)
#   PIPEWATCH_TIME_CMD       Path to time command (default: /usr/bin/time)

set -euo pipefail

# Configuration
EVENTS_FILE="${PIPEWATCH_EVENTS_FILE:-pipewatch-events.ndjson}"
STEP_NAME="${PIPEWATCH_STEP_NAME:-}"
SAMPLE_ID="${PIPEWATCH_SAMPLE_ID:-${SLURM_ARRAY_TASK_ID:-}}"
STDOUT_PATH="${PIPEWATCH_STDOUT_PATH:-}"
STDERR_PATH="${PIPEWATCH_STDERR_PATH:-}"
CAPTURE_TIME="${PIPEWATCH_CAPTURE_TIME:-1}"
TIME_CMD="${PIPEWATCH_TIME_CMD:-/usr/bin/time}"

# Command to execute
COMMAND="$1"
shift || true

# Detect if we have GNU time (supports -v) or BSD time (macOS)
has_gnu_time() {
    if [[ "$($TIME_CMD --version 2>&1)" == *"GNU"* ]]; then
        return 0
    else
        return 1
    fi
}

# Generate ISO 8601 timestamp (cross-platform)
timestamp() {
    # Try different methods for millisecond precision
    if date -u +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null | grep -q "T"; then
        # BSD/macOS date
        local ts
        ts=$(date -u +"%Y-%m-%dT%H:%M:%S")
        # Add milliseconds using perl or python if available
        if command -v python3 >/dev/null 2>&1; then
            local ms
            ms=$(python3 -c "import time; print(f'{time.time():.3f}'.split('.')[1])" 2>/dev/null || echo "000")
            echo "${ts}.${ms}Z"
        elif command -v perl >/dev/null 2>&1; then
            local ms
            ms=$(perl -MTime::HiRes=time -e 'printf "%03d", (time - int(time)) * 1000' 2>/dev/null || echo "000")
            echo "${ts}.${ms}Z"
        else
            echo "${ts}.000Z"
        fi
    else
        # Fallback to simple format
        date -u +"%Y-%m-%dT%H:%M:%SZ"
    fi
}

# Get current time in milliseconds (cross-platform)
get_time_ms() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c "import time; print(int(time.time() * 1000))"
    elif command -v perl >/dev/null 2>&1; then
        perl -MTime::HiRes=time -e 'print int(time * 1000)'
    else
        # Fallback to seconds * 1000 (less precise)
        echo $(($(date +%s) * 1000))
    fi
}

# Escape string for JSON
json_escape() {
    local str="$1"
    str="${str//\\/\\\\}"
    str="${str//\"/\\\"}"
    str="${str//$'\n'/\\n}"
    str="${str//$'\r'/}"
    str="${str//$'\t'/\\t}"
    printf '%s' "$str"
}

# Get git commit if available
git_commit() {
    git rev-parse HEAD 2>/dev/null || echo "null"
}

# Get git branch if available
git_branch() {
    git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "null"
}

# Emit event to file
emit_event() {
    local event_type="$1"
    local exit_code="${2:-null}"
    local duration_ms="${3:-null}"
    local max_rss_kb="${4:-null}"
    local user_time_s="${5:-null}"
    local sys_time_s="${6:-null}"
    local wall_time_s="${7:-null}"
    
    # Create events directory if needed
    local events_dir
    events_dir="$(dirname "$EVENTS_FILE")"
    if [[ "$events_dir" != "." && ! -d "$events_dir" ]]; then
        mkdir -p "$events_dir"
    fi
    
    # Build JSON event
    local json
    json="{"
    json+='"schema_version":"1.0.0"'
    json+=',"event_type":"'"$event_type"'"'
    json+=',"timestamp":"'"$(timestamp)"'"'
    json+=',"hostname":"'"$(hostname)"'"'
    json+=',"cwd":"'"$(pwd)"'"'
    json+=',"command":"'"$(json_escape "$COMMAND")"'"'
    
    if [[ "$exit_code" != "null" ]]; then
        json+=',"exit_code":'"$exit_code"
    fi
    
    if [[ -n "$STEP_NAME" ]]; then
        json+=',"step_name":"'"$(json_escape "$STEP_NAME")"'"'
    fi
    
    if [[ -n "$SAMPLE_ID" ]]; then
        json+=',"sample_id":"'"$(json_escape "$SAMPLE_ID")"'"'
    fi
    
    if [[ -n "${SLURM_JOB_ID:-}" ]]; then
        json+=',"slurm_job_id":"'"$SLURM_JOB_ID"'"'
    fi
    
    if [[ -n "${SLURM_ARRAY_TASK_ID:-}" ]]; then
        json+=',"slurm_array_task_id":"'"$SLURM_ARRAY_TASK_ID"'"'
    fi
    
    if [[ -n "${SLURM_JOB_NAME:-}" ]]; then
        json+=',"slurm_job_name":"'"$(json_escape "$SLURM_JOB_NAME")"'"'
    fi
    
    local git_commit_val
    git_commit_val=$(git_commit)
    if [[ "$git_commit_val" != "null" ]]; then
        json+=',"git_commit":"'"$git_commit_val"'"'
    fi
    
    local git_branch_val
    git_branch_val=$(git_branch)
    if [[ "$git_branch_val" != "null" ]]; then
        json+=',"git_branch":"'"$git_branch_val"'"'
    fi
    
    if [[ "$duration_ms" != "null" ]]; then
        json+=',"duration_ms":'"$duration_ms"
    fi
    
    if [[ "$max_rss_kb" != "null" && -n "$max_rss_kb" ]]; then
        json+=',"max_rss_kb":'"$max_rss_kb"
    fi
    
    if [[ "$user_time_s" != "null" && -n "$user_time_s" ]]; then
        json+=',"user_time_s":'"$user_time_s"
    fi
    
    if [[ "$sys_time_s" != "null" && -n "$sys_time_s" ]]; then
        json+=',"sys_time_s":'"$sys_time_s"
    fi
    
    if [[ "$wall_time_s" != "null" && -n "$wall_time_s" ]]; then
        json+=',"wall_time_s":'"$wall_time_s"
    fi
    
    if [[ -n "$STDOUT_PATH" ]]; then
        json+=',"stdout_path":"'"$(json_escape "$STDOUT_PATH")"'"'
    fi
    
    if [[ -n "$STDERR_PATH" ]]; then
        json+=',"stderr_path":"'"$(json_escape "$STDERR_PATH")"'"'
    fi
    
    json+="}"
    
    # Append to events file
    echo "$json" >> "$EVENTS_FILE"
}

# Parse GNU time -v output
parse_gnu_time_output() {
    local time_file="$1"
    
    if [[ ! -f "$time_file" ]]; then
        echo "null null null null"
        return
    fi
    
    local max_rss user_time sys_time wall_time
    
    # Extract max RSS (in KB)
    max_rss=$(grep -i "Maximum resident set size" "$time_file" 2>/dev/null | sed 's/.*: //' | tr -d ' ' || echo "null")
    
    # Extract user time (in seconds)
    user_time=$(grep -i "User time" "$time_file" 2>/dev/null | sed 's/.*: //' | tr -d ' ' || echo "null")
    
    # Extract system time (in seconds)
    sys_time=$(grep -i "System time" "$time_file" 2>/dev/null | sed 's/.*: //' | tr -d ' ' || echo "null")
    
    # Extract elapsed wall clock time
    wall_time_raw=$(grep -i "Elapsed (wall clock)" "$time_file" 2>/dev/null | sed 's/.*: //' | tr -d ' ' || echo "")
    
    # Convert wall time to seconds
    wall_time="null"
    if [[ -n "$wall_time_raw" ]]; then
        # Count colons to determine format
        local colons
        colons=$(echo "$wall_time_raw" | tr -cd ':' | wc -c | tr -d ' ')
        
        if [[ "$colons" -eq 2 ]]; then
            # H:MM:SS format
            local h m s
            IFS=: read -r h m s <<< "$wall_time_raw"
            # Use integer arithmetic where possible
            h=$(echo "$h" | sed 's/^0*//'); h=${h:-0}
            m=$(echo "$m" | sed 's/^0*//'); m=${m:-0}
            s=$(echo "$s" | sed 's/^0*//'); s=${s:-0}
            wall_time=$((h * 3600 + m * 60 + s))
        elif [[ "$colons" -eq 1 ]]; then
            # M:SS format
            local m s
            IFS=: read -r m s <<< "$wall_time_raw"
            m=$(echo "$m" | sed 's/^0*//'); m=${m:-0}
            s=$(echo "$s" | sed 's/^0*//'); s=${s:-0}
            wall_time=$((m * 60 + s))
        else
            # Just seconds
            wall_time="$wall_time_raw"
        fi
    fi
    
    echo "$max_rss $user_time $sys_time $wall_time"
}

# Main execution
main() {
    # Emit start event
    emit_event "start"
    
    # Record start time
    local start_time end_time duration_ms
    start_time=$(get_time_ms)
    
    # Check if we can use GNU time for resource capture
    local time_file=""
    local use_time=false
    if [[ "$CAPTURE_TIME" == "1" ]] && has_gnu_time; then
        time_file=$(mktemp)
        use_time=true
    fi
    
    # Execute command
    local exit_code=0
    if [[ "$use_time" == true ]]; then
        # Run with GNU time -v
        $TIME_CMD -v -o "$time_file" bash -c 'set -euo pipefail; '"$COMMAND" || exit_code=$?
    else
        # Run without time (no resource capture)
        bash -c 'set -euo pipefail; '"$COMMAND" || exit_code=$?
    fi
    
    # Calculate duration
    end_time=$(get_time_ms)
    duration_ms=$((end_time - start_time))
    
    # Parse time output if available
    local max_rss="null" user_time="null" sys_time="null" wall_time="null"
    if [[ -n "$time_file" && -f "$time_file" ]]; then
        read -r max_rss user_time sys_time wall_time <<< "$(parse_gnu_time_output "$time_file")"
        rm -f "$time_file"
    fi
    
    # Emit end event
    emit_event "end" "$exit_code" "$duration_ms" "$max_rss" "$user_time" "$sys_time" "$wall_time"
    
    return $exit_code
}

main "$@"
