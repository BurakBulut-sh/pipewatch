"""HTML report generation for pipeline observability."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipewatch.reporter.analyzer import PipelineAnalyzer, PipelineSummary


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipewatch Report - {{ summary.run_id }}</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-primary: #3b82f6;
            --accent-secondary: #06b6d4;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
            --border: #475569;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }

        h1 {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        h2 {
            font-size: 1.25rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
            color: var(--text-primary);
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 0.875rem;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .metric-card {
            background: var(--bg-secondary);
            border-radius: 0.5rem;
            padding: 1.5rem;
            border: 1px solid var(--border);
        }

        .metric-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .metric-value.success { color: var(--success); }
        .metric-value.warning { color: var(--warning); }
        .metric-value.error { color: var(--error); }

        .section {
            background: var(--bg-secondary);
            border-radius: 0.5rem;
            border: 1px solid var(--border);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }

        .section-header {
            padding: 1rem 1.5rem;
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .section-title {
            font-weight: 600;
            font-size: 1rem;
        }

        .section-content {
            padding: 1.5rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }

        th {
            text-align: left;
            padding: 0.75rem;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }

        td {
            padding: 0.75rem;
            border-bottom: 1px solid var(--bg-tertiary);
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover {
            background: var(--bg-tertiary);
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .badge-success {
            background: rgba(34, 197, 94, 0.2);
            color: var(--success);
        }

        .badge-warning {
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning);
        }

        .badge-error {
            background: rgba(239, 68, 68, 0.2);
            color: var(--error);
        }

        .issue {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-tertiary);
            border-radius: 0.25rem;
            margin-bottom: 0.5rem;
        }

        .issue-icon {
            width: 1.5rem;
            height: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            font-weight: bold;
        }

        .issue-warning .issue-icon {
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning);
        }

        .issue-error .issue-icon {
            background: rgba(239, 68, 68, 0.2);
            color: var(--error);
        }

        .issue-content {
            flex: 1;
        }

        .issue-type {
            font-weight: 600;
            font-size: 0.875rem;
        }

        .issue-message {
            font-size: 0.8125rem;
            color: var(--text-secondary);
        }

        .progress-bar {
            height: 0.5rem;
            background: var(--bg-tertiary);
            border-radius: 0.25rem;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 0.25rem;
            transition: width 0.3s ease;
        }

        .comparison-positive {
            color: var(--success);
        }

        .comparison-negative {
            color: var(--error);
        }

        .empty-state {
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }

        .footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.75rem;
            text-align: center;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .metrics-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            table {
                font-size: 0.75rem;
            }

            th, td {
                padding: 0.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔬 Pipewatch Report</h1>
            <p class="subtitle">Run ID: {{ summary.run_id }} | Generated: {{ generation_time }}</p>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Steps</div>
                <div class="metric-value">{{ summary.total_steps }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Samples</div>
                <div class="metric-value">{{ summary.total_samples }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Duration</div>
                <div class="metric-value">{{ total_duration }}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Failure Rate</div>
                <div class="metric-value {{ 'error' if summary.failure_rate > 0 else 'success' }}">
                    {{ "%.1f"|format(summary.failure_rate * 100) }}%
                </div>
            </div>
        </div>

        {% if summary.issues %}
        <div class="section">
            <div class="section-header">
                <span class="section-title">⚠️ Issues & Warnings</span>
            </div>
            <div class="section-content">
                {% for issue in summary.issues %}
                <div class="issue issue-{{ issue.severity }}">
                    <div class="issue-icon">{{ '!' if issue.severity == 'warning' else '✕' }}</div>
                    <div class="issue-content">
                        <div class="issue-type">{{ issue.type.replace('_', ' ').title() }}</div>
                        <div class="issue-message">{{ issue.message }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="section">
            <div class="section-header">
                <span class="section-title">🐌 Top Slowest Steps</span>
            </div>
            <div class="section-content">
                {% if summary.slowest_steps %}
                <table>
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Avg Duration</th>
                            <th>Distribution</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for step in summary.slowest_steps %}
                        <tr>
                            <td>{{ step.step_name }}</td>
                            <td>{{ "%.2f"|format(step.avg_duration_ms / 1000) }}s</td>
                            <td>
                                <div class="progress-bar" style="width: 200px;">
                                    <div class="progress-fill" style="width: {{ (step.avg_duration_ms / summary.slowest_steps[0].avg_duration_ms * 100) if summary.slowest_steps and summary.slowest_steps[0].avg_duration_ms > 0 else 0 }}%"></div>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty-state">No step data available</div>
                {% endif %}
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <span class="section-title">📊 Per-Sample Runtimes</span>
            </div>
            <div class="section-content">
                {% if summary.sample_stats %}
                <table>
                    <thead>
                        <tr>
                            <th>Sample</th>
                            <th>Steps</th>
                            <th>Total Time</th>
                            <th>Avg Time</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sample in summary.sample_stats[:20] %}
                        <tr>
                            <td>{{ sample.sample_id }}</td>
                            <td>{{ sample.step_count }}</td>
                            <td>{{ "%.2f"|format(sample.total_duration_ms / 1000) }}s</td>
                            <td>{{ "%.2f"|format(sample.avg_duration_ms / 1000) }}s</td>
                            <td>
                                {% if sample.failures == 0 %}
                                <span class="badge badge-success">Success</span>
                                {% else %}
                                <span class="badge badge-error">{{ sample.failures }} Failed</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% if summary.sample_stats|length > 20 %}
                <p style="margin-top: 1rem; color: var(--text-secondary);">
                    ... and {{ summary.sample_stats|length - 20 }} more samples
                </p>
                {% endif %}
                {% else %}
                <div class="empty-state">No sample data available</div>
                {% endif %}
            </div>
        </div>

        {% if summary.failure_clusters %}
        <div class="section">
            <div class="section-header">
                <span class="section-title">🔥 Failure Clustering</span>
            </div>
            <div class="section-content">
                <table>
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Name</th>
                            <th>Failures</th>
                            <th>Exit Codes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for cluster in summary.failure_clusters %}
                        <tr>
                            <td>{{ cluster.category.title() }}</td>
                            <td>{{ cluster.name }}</td>
                            <td>
                                <span class="badge badge-error">{{ cluster.count }}</span>
                            </td>
                            <td>
                                {% for code, count in cluster.exit_codes.items() %}
                                <span class="badge badge-warning" style="margin-right: 0.25rem;">
                                    {{ code }} ({{ count }})
                                </span>
                                {% endfor %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        {% if summary.memory_hogs %}
        <div class="section">
            <div class="section-header">
                <span class="section-title">🧠 Memory Hogs</span>
            </div>
            <div class="section-content">
                <table>
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Peak Memory (MB)</th>
                            <th>Avg Memory (MB)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for step in summary.memory_hogs %}
                        <tr>
                            <td>{{ step.step_name }}</td>
                            <td>{{ "%.1f"|format(step.max_max_rss_kb / 1024) if step.max_max_rss_kb else 'N/A' }}</td>
                            <td>{{ "%.1f"|format(step.avg_max_rss_kb / 1024) if step.avg_max_rss_kb else 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        {% if comparison %}
        <div class="section">
            <div class="section-header">
                <span class="section-title">📈 Run-to-Run Comparison</span>
            </div>
            <div class="section-content">
                <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                    Comparing against baseline: {{ comparison.baseline_run }}
                </p>
                <table>
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Baseline</th>
                            <th>Current</th>
                            <th>Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for comp in comparison.step_comparisons %}
                        <tr>
                            <td>{{ comp.step_name }}</td>
                            <td>{{ "%.2f"|format(comp.baseline_duration_ms / 1000) if comp.baseline_duration_ms else 'N/A' }}s</td>
                            <td>{{ "%.2f"|format(comp.current_duration_ms / 1000) if comp.current_duration_ms else 'N/A' }}s</td>
                            <td>
                                {% if comp.change_pct is not none %}
                                    {% if comp.change_pct > 0 %}
                                    <span class="comparison-negative">+{{ "%.1f"|format(comp.change_pct) }}%</span>
                                    {% else %}
                                    <span class="comparison-positive">{{ "%.1f"|format(comp.change_pct) }}%</span>
                                    {% endif %}
                                {% else %}
                                <span class="badge badge-warning">{{ comp.note }}</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}

        <div class="footer">
            <p>Generated by Pipewatch v{{ version }} | <a href="data.json" style="color: var(--accent-primary);">Download JSON</a></p>
        </div>
    </div>
</body>
</html>
'''


class HTMLReportGenerator:
    """Generate HTML reports from pipeline summaries."""

    def __init__(self, template: str | None = None):
        """Initialize generator with optional custom template.

        Args:
            template: Custom Jinja2 template string. Uses default if not provided.
        """
        self.template_str = template or HTML_TEMPLATE

    def generate(
        self,
        summary: PipelineSummary,
        output_path: Path,
        comparison: dict[str, Any] | None = None,
    ) -> None:
        """Generate HTML report.

        Args:
            summary: Pipeline summary to report on.
            output_path: Path to write HTML file.
            comparison: Optional comparison data from compare_runs().
        """
        from datetime import datetime

        try:
            from jinja2 import Template
        except ImportError:
            # Fallback: write simple HTML without Jinja2
            self._generate_simple_html(summary, output_path)
            return

        template = Template(self.template_str)

        html = template.render(
            summary=summary,
            total_duration=summary._format_duration(summary.total_duration_ms),
            generation_time=datetime.now(timezone.utc).isoformat(),
            comparison=comparison,
            version="0.1.0",
        )

        output_path.write_text(html, encoding="utf-8")

    def _generate_simple_html(self, summary: PipelineSummary, output_path: Path) -> None:
        """Generate simple HTML without Jinja2 dependency."""
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Pipewatch Report - {summary.run_id}</title>
    <style>
        body {{ font-family: sans-serif; margin: 2rem; background: #0f172a; color: #f8fafc; }}
        h1 {{ color: #3b82f6; }}
        .metric {{ display: inline-block; margin: 1rem; padding: 1rem; background: #1e293b; border-radius: 0.5rem; }}
        table {{ width: 100%%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <h1>Pipewatch Report</h1>
    <p>Run: {summary.run_id}</p>
    <div class="metric">
        <strong>Steps:</strong> {summary.total_steps}
    </div>
    <div class="metric">
        <strong>Samples:</strong> {summary.total_samples}
    </div>
    <div class="metric">
        <strong>Duration:</strong> {summary._format_duration(summary.total_duration_ms)}
    </div>
    <div class="metric">
        <strong>Failures:</strong> {summary.total_failures}
    </div>
</body>
</html>'''

        output_path.write_text(html, encoding="utf-8")

    def generate_json(self, summary: PipelineSummary, output_path: Path) -> None:
        """Generate JSON report.

        Args:
            summary: Pipeline summary to report on.
            output_path: Path to write JSON file.
        """
        data = summary.to_dict()
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
