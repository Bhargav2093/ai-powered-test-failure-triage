"""Renders a TriageResult (+ per-cluster narratives) as HTML, JSON, or Markdown."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from jinja2 import Template

from triage.models import Category, TriageResult

_HTML_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Test Failure Triage Report</title>
<style>
  body { font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; margin: 2rem; color: #1a1a1a; background: #fafafa; }
  h1 { margin-bottom: 0.25rem; }
  .generated { color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }
  .summary { display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
  .summary-card { background: white; border-radius: 8px; padding: 1rem 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 140px; }
  .summary-card .count { font-size: 1.8rem; font-weight: 700; }
  .summary-card .label { font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.03em; }
  .cluster { background: white; border-radius: 8px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 5px solid #999; }
  .cluster.flaky { border-left-color: #d9a441; }
  .cluster.infra { border-left-color: #a44141; }
  .cluster.regression { border-left-color: #4169a4; }
  .cluster-header { display: flex; justify-content: space-between; align-items: baseline; }
  .badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: white; }
  .badge.flaky { background: #d9a441; }
  .badge.infra { background: #a44141; }
  .badge.regression { background: #4169a4; }
  .confidence { color: #666; font-size: 0.8rem; }
  .narrative { margin: 0.75rem 0; line-height: 1.5; }
  .affected { font-size: 0.85rem; color: #333; }
  .affected code { background: #f0f0f0; padding: 0.1rem 0.3rem; border-radius: 4px; }
  .trace { background: #1e1e1e; color: #d4d4d4; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.78rem; overflow-x: auto; white-space: pre-wrap; }
</style>
</head>
<body>
<h1>Test Failure Triage Report</h1>
<div class="generated">Generated {{ generated_at }} - {{ total_failures }} failure(s) in {{ clusters|length }} cluster(s)</div>

<div class="summary">
  {% for category, count in counts.items() %}
  <div class="summary-card">
    <div class="count">{{ count }}</div>
    <div class="label">{{ category }}</div>
  </div>
  {% endfor %}
</div>

{% for cluster in clusters %}
<div class="cluster {{ cluster.category }}">
  <div class="cluster-header">
    <span class="badge {{ cluster.category }}">{{ cluster.category }}</span>
    <span class="confidence">confidence: {{ cluster.confidence }}</span>
  </div>
  <p class="narrative">{{ cluster.narrative }}</p>
  <p class="affected"><strong>{{ cluster.size }} test(s):</strong>
    {% for name in cluster.affected %}<code>{{ name }}</code>{% if not loop.last %}, {% endif %}{% endfor %}
  </p>
  <details>
    <summary>Representative stack trace ({{ cluster.representative_name }})</summary>
    <pre class="trace">{{ cluster.representative_trace }}</pre>
  </details>
</div>
{% endfor %}

</body>
</html>
"""
)

_MARKDOWN_TEMPLATE = Template(
    """# Test Failure Triage Report

_Generated {{ generated_at }} - {{ total_failures }} failure(s) in {{ clusters|length }} cluster(s)_

| Category | Count |
|---|---|
{% for category, count in counts.items() -%}
| {{ category }} | {{ count }} |
{% endfor %}
{% for cluster in clusters %}
## [{{ cluster.category|upper }}] {{ cluster.representative_name }} (+{{ cluster.size - 1 }} more)

- **Confidence:** {{ cluster.confidence }}
- **Affected tests ({{ cluster.size }}):** {% for name in cluster.affected %}`{{ name }}`{% if not loop.last %}, {% endif %}{% endfor %}

{{ cluster.narrative }}
{% endfor %}
"""
)


@dataclass
class ReportCluster:
    category: str
    confidence: str
    size: int
    affected: list[str]
    representative_name: str
    representative_trace: str
    narrative: str


def build_report_context(result: TriageResult, narratives: dict[int, str]) -> dict:
    """Assemble the plain-dict/dataclass context shared by all three renderers."""
    counts = {category.value: result.count_by_category(category) for category in Category}
    clusters = [
        ReportCluster(
            category=cluster.category.value,
            confidence=cluster.representative.classification.confidence.value,
            size=cluster.size,
            affected=[m.record.full_name for m in cluster.members],
            representative_name=cluster.representative.record.full_name,
            representative_trace=cluster.representative.record.stack_trace,
            narrative=narratives.get(cluster.id, ""),
        )
        for cluster in result.clusters
    ]
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_failures": result.total_failures,
        "counts": counts,
        "clusters": clusters,
    }


def render_html(result: TriageResult, narratives: dict[int, str]) -> str:
    return _HTML_TEMPLATE.render(**build_report_context(result, narratives))


def render_markdown(result: TriageResult, narratives: dict[int, str]) -> str:
    return _MARKDOWN_TEMPLATE.render(**build_report_context(result, narratives))


def render_json(result: TriageResult, narratives: dict[int, str]) -> str:
    context = build_report_context(result, narratives)
    context["clusters"] = [vars(c) for c in context["clusters"]]
    return json.dumps(context, indent=2)
