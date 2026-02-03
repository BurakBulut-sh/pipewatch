# Dockerfile for local Pipewatch demo

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bash \
    time \
    bc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy source code
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install pipewatch
RUN pip install --no-cache-dir -e "."

# Copy examples
COPY examples/ ./examples/

# Make scripts executable
RUN chmod +x examples/ci-simulation/*.sh \
    examples/slurm-bwa-samtools/*.sh \
    examples/multi-step-workflow/*.sh \
    src/pipewatch/obsrun.sh

# Create a non-root user
RUN useradd -m -u 1000 pipewatch && \
    chown -R pipewatch:pipewatch /app
USER pipewatch

# Set environment variables
ENV PIPEWATCH_EVENTS_DIR=/app/events
ENV PATH="/app/src/pipewatch:${PATH}"

# Default command runs the CI simulation
CMD ["bash", "-c", "cd /app/examples/ci-simulation && bash run_tests.sh && echo 'Report available at /app/examples/ci-simulation/report/'"]
