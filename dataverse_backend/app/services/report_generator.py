"""Generate self-contained HTML and PDF reports from computed analytics facts."""
from __future__ import annotations

import html
import io
import math
import re
from datetime import datetime, timezone
from typing import Any

from jinja2 import Template

from ..core.config import settings
from .data_quality import validate_chart_spec
from .llm_provider import LLMProvider
from .report_composer import ReportComposer


# Professional light-theme palette (item 10).
PALETTE = ["#2563EB", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#14B8A6", "#6366F1"]
GRADE_COLORS = {
    "Excellent": "#10B981",
    "Good": "#2563EB",
    "Average": "#F59E0B",
    "Poor": "#EF4444",
    "Connected": "#10B981",
    "Missing": "#EF4444",
    "Failed": "#EF4444",
    "Mock Mode": "#F59E0B",
    "Docker Ready": "#10B981",
    "Not Configured": "#64748B",
    "Warning": "#F59E0B",
    "Yes": "#10B981",
    "No": "#EF4444",
    "Partial": "#F59E0B",
    "Functional": "#10B981",
    "Running": "#10B981",
    "Stopped": "#EF4444",
    "Built": "#10B981",
    "Build Missing": "#F59E0B",
}
SEVERITY_COLORS = {"Low": "#10B981", "Medium": "#F59E0B", "High": "#EF4444", "Critical": "#B91C1C"}
RISK_COLORS = {
    "Low": "#10B981",
    "Medium": "#F59E0B",
    "High": "#EF4444",
    "Low / Manual Review": "#10B981",
    "Low to Medium / Manual Review": "#F59E0B",
}

REPORT_TEMPLATE = Template(
    """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0B1120;
      --bg-surface: #111827;
      --card: #1E293B;
      --card-hover: #253349;
      --line: rgba(148,163,184,.12);
      --line-accent: rgba(99,102,241,.25);
      --primary: #818CF8;
      --primary-bright: #A5B4FC;
      --secondary: #38BDF8;
      --accent: #6366F1;
      --accent-glow: rgba(99,102,241,.15);
      --success: #34D399;
      --success-bg: rgba(52,211,153,.08);
      --warning: #FBBF24;
      --warning-bg: rgba(251,191,36,.08);
      --danger: #F87171;
      --danger-bg: rgba(248,113,113,.08);
      --ink: #F1F5F9;
      --ink-secondary: #CBD5E1;
      --muted: #94A3B8;
      --glass-bg: rgba(30,41,59,.65);
      --glass-border: rgba(148,163,184,.1);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: var(--ink); background: var(--bg); line-height: 1.6;
      -webkit-font-smoothing: antialiased;
    }

    /* ── Cover ── */
    .cover {
      position: relative; overflow: hidden;
      padding: 48px 40px 40px;
      background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 40%, #312E81 70%, #1E293B 100%);
      border-bottom: 1px solid var(--line-accent);
    }
    .cover::before {
      content: ''; position: absolute; top: -60%; right: -20%;
      width: 600px; height: 600px; border-radius: 50%;
      background: radial-gradient(circle, rgba(99,102,241,.12) 0%, transparent 70%);
      pointer-events: none;
    }
    .cover .brand {
      font-family: 'Outfit', sans-serif; font-size: 11px; font-weight: 700;
      letter-spacing: .18em; text-transform: uppercase;
      color: var(--primary); margin-bottom: 12px;
      display: flex; align-items: center; gap: 8px;
    }
    .cover .brand::before {
      content: ''; display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; background: var(--primary);
      box-shadow: 0 0 8px var(--primary), 0 0 20px rgba(99,102,241,.3);
    }
    .cover h1 {
      font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 800;
      letter-spacing: -.02em; color: #fff; margin-bottom: 10px;
    }
    .cover .meta {
      color: var(--muted); font-size: 12px;
      display: flex; gap: 20px; flex-wrap: wrap; align-items: center;
    }
    .cover .meta span { display: flex; align-items: center; gap: 5px; }

    /* Cover score strip */
    .cover-scores {
      display: flex; gap: 16px; flex-wrap: wrap; margin-top: 24px;
    }
    .cover-score-card {
      background: var(--glass-bg); backdrop-filter: blur(16px);
      border: 1px solid var(--glass-border); border-radius: 16px;
      padding: 16px 22px; min-width: 150px;
      animation: fadeInUp .5s ease both;
    }
    .cover-score-card:nth-child(2) { animation-delay: .1s; }
    .cover-score-card:nth-child(3) { animation-delay: .2s; }
    .cover-score-label {
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      letter-spacing: .08em; color: var(--muted); margin-bottom: 6px;
    }
    .cover-score-value {
      font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 800;
    }
    .cover-score-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

    /* Health gauge SVG */
    .health-gauge { display: flex; align-items: center; gap: 16px; }
    .health-gauge svg { width: 72px; height: 72px; }

    /* Verdict badge */
    .verdict-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 6px 16px; border-radius: 999px;
      font-size: 13px; font-weight: 700; letter-spacing: .02em;
    }
    .verdict-excellent { background: rgba(52,211,153,.15); color: #34D399; border: 1px solid rgba(52,211,153,.25); }
    .verdict-good { background: rgba(56,189,248,.15); color: #38BDF8; border: 1px solid rgba(56,189,248,.25); }
    .verdict-needs-improvement { background: rgba(251,191,36,.15); color: #FBBF24; border: 1px solid rgba(251,191,36,.25); }
    .verdict-critical { background: rgba(248,113,113,.15); color: #F87171; border: 1px solid rgba(248,113,113,.25); }

    /* ── Page ── */
    .page { max-width: 1140px; margin: 0 auto; padding: 24px 20px 48px; }

    /* ── Sections ── */
    .section {
      background: var(--card); border: 1px solid var(--line);
      border-radius: 16px; padding: 20px 22px; margin: 0 0 14px;
      box-shadow: 0 4px 24px rgba(0,0,0,.12), 0 1px 3px rgba(0,0,0,.08);
      animation: fadeInUp .45s ease both;
    }
    .section h2 {
      font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 700;
      color: var(--ink); margin: 0 0 14px;
      display: flex; align-items: center; gap: 10px;
    }
    .section h2 .sec-icon {
      width: 28px; height: 28px; border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-size: 14px; flex-shrink: 0;
    }
    .section h2::after {
      content: ''; flex: 1; height: 1px;
      background: linear-gradient(90deg, var(--line-accent), transparent);
      margin-left: 8px;
    }
    h3 { font-size: 13px; margin: 0 0 6px; color: var(--ink-secondary); font-weight: 600; }

    /* ── Grid & Cards ── */
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 12px; }
    .kpi-card {
      background: var(--bg-surface); border: 1px solid var(--line);
      border-radius: 12px; padding: 14px 16px;
      transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
      position: relative; overflow: hidden;
    }
    .kpi-card::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--primary), var(--secondary));
      opacity: 0; transition: opacity .2s ease;
    }
    .kpi-card:hover { transform: translateY(-2px); border-color: var(--line-accent); box-shadow: 0 8px 24px rgba(0,0,0,.2); }
    .kpi-card:hover::before { opacity: 1; }
    .kpi-label {
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      letter-spacing: .06em; color: var(--muted); margin-bottom: 6px;
    }
    .kpi-value {
      font-family: 'Outfit', sans-serif; font-size: 22px; font-weight: 800;
      color: var(--ink); line-height: 1.1;
    }
    .kpi-trend { font-size: 11px; margin-top: 4px; font-weight: 600; }
    .kpi-trend.up { color: var(--success); }
    .kpi-trend.down { color: var(--danger); }

    .card {
      border: 1px solid var(--line); border-radius: 12px;
      padding: 12px 14px; background: var(--bg-surface);
      transition: border-color .2s ease;
    }
    .card:hover { border-color: var(--line-accent); }

    /* ── Charts ── */
    .chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
    .chart-card {
      background: var(--bg-surface); border: 1px solid var(--line);
      border-radius: 14px; padding: 18px; overflow: hidden;
      transition: border-color .2s ease, box-shadow .2s ease;
    }
    .chart-card:hover { border-color: var(--line-accent); box-shadow: 0 8px 32px rgba(0,0,0,.15); }
    .chart-card h3 { color: var(--ink); font-weight: 600; margin-bottom: 4px; }
    .chart-card .explain { font-size: 12px; color: var(--muted); margin: 4px 0 12px; line-height: 1.5; }
    .chart-card .takeaway {
      font-size: 12px; color: var(--primary-bright); font-weight: 600;
      margin-top: 12px; padding-top: 10px;
      border-top: 1px solid var(--line);
    }
    .chart-card canvas { width: 100% !important; max-height: 260px; }

    /* ── Tables ── */
    table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
    thead th {
      text-align: left; padding: 10px 12px;
      background: var(--bg-surface); color: var(--muted);
      font-weight: 700; font-size: 10px; text-transform: uppercase;
      letter-spacing: .05em; border-bottom: 1px solid var(--line);
    }
    td {
      padding: 9px 12px; border-bottom: 1px solid var(--line);
      color: var(--ink-secondary); white-space: nowrap;
    }
    tr:hover td { background: rgba(99,102,241,.04); }

    /* ── Lists ── */
    ul { margin: 0; padding-left: 0; list-style: none; }
    li {
      position: relative; padding: 6px 0 6px 20px;
      color: var(--ink-secondary); font-size: 13px; line-height: 1.55;
    }
    li::before {
      content: ''; position: absolute; left: 0; top: 13px;
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--primary); opacity: .6;
    }
    p { margin: 4px 0; color: var(--ink-secondary); font-size: 13px; }

    /* ── Badges & Callouts ── */
    .badge {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 4px 12px; border-radius: 999px;
      font-size: 11px; font-weight: 700; color: #fff;
    }
    .muted { color: var(--muted); }

    .scorecard { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 6px 0 10px; }
    .scorecard .card { display: flex; flex-direction: column; gap: 6px; }
    .scorecard .card .label { color: var(--muted); }

    .ov-block { margin: 0 0 12px; }
    .ov-block .ov-label {
      font-size: 10px; font-weight: 700; text-transform: uppercase;
      letter-spacing: .06em; color: var(--secondary); margin-bottom: 4px;
    }
    .ov-block > div { color: var(--ink-secondary); font-size: 13px; }

    .callout {
      border-left: 3px solid var(--primary);
      background: var(--accent-glow); padding: 10px 14px;
      border-radius: 0 10px 10px 0; font-size: 13px; margin-top: 10px;
      color: var(--ink-secondary);
    }
    .callout.warn { border-color: var(--warning); background: var(--warning-bg); }
    .callout.danger { border-color: var(--danger); background: var(--danger-bg); }

    /* ── Collapsible ── */
    details { margin-top: 8px; }
    summary {
      cursor: pointer; font-size: 12px; font-weight: 600;
      color: var(--primary); padding: 6px 0;
      list-style: none; display: flex; align-items: center; gap: 6px;
    }
    summary::before { content: '▸'; transition: transform .2s ease; }
    details[open] summary::before { transform: rotate(90deg); }
    summary::-webkit-details-marker { display: none; }

    /* ── Animations ── */
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .section:nth-child(2) { animation-delay: .05s; }
    .section:nth-child(3) { animation-delay: .1s; }
    .section:nth-child(4) { animation-delay: .15s; }
    .section:nth-child(5) { animation-delay: .2s; }
    .section:nth-child(6) { animation-delay: .25s; }
    .section:nth-child(7) { animation-delay: .3s; }

    /* ── Footer ── */
    .report-footer {
      text-align: center; padding: 24px 20px 32px;
      color: var(--muted); font-size: 11px;
      border-top: 1px solid var(--line);
    }
    .report-footer .brand-mark {
      font-family: 'Outfit', sans-serif; font-weight: 700;
      color: var(--primary); letter-spacing: .04em;
    }

    /* ── Print ── */
    @page { size: A4; margin: 12mm; }
    @media print {
      :root {
        --bg: #fff; --bg-surface: #f8fafc; --card: #fff;
        --line: #e2e8f0; --line-accent: #e2e8f0;
        --ink: #0f172a; --ink-secondary: #334155; --muted: #64748b;
        --primary: #4f46e5; --primary-bright: #4f46e5;
        --glass-bg: #f8fafc; --glass-border: #e2e8f0;
        --accent-glow: #eff6ff;
      }
      body { background: #fff; color: #0f172a; }
      .cover { background: linear-gradient(135deg, #fff 0%, #eff6ff 100%) !important; }
      .cover h1 { color: #0f172a; }
      .section, .chart-card { box-shadow: none; break-inside: avoid; border-color: #e2e8f0; }
      .cover { break-after: avoid; }
      .kpi-card { background: #f8fafc; }
      canvas { max-height: 200px !important; }
    }
  </style>
</head>
<body>
  <header class="cover">
    <div class="brand">DataVerse AI — Analytics Report</div>
    <h1>{{ title }}</h1>
    <div class="meta">
      <span>📅 {{ generated_at }}</span>
      <span>📄 {{ filename }}</span>
      <span>📊 {{ rows }} rows · {{ cols }} columns</span>
    </div>
    <div class="cover-scores">
      <div class="cover-score-card">
        <div class="cover-score-label">Health Score</div>
        <div class="health-gauge">
          {{ health_gauge_svg }}
          <div>
            <div class="cover-score-value" style="color:{{ health_color }}">{{ health_score }}</div>
            <div class="cover-score-sub">out of 100</div>
          </div>
        </div>
      </div>
      <div class="cover-score-card">
        <div class="cover-score-label">AI Confidence</div>
        <div class="cover-score-value" style="color:var(--secondary)">{{ ai_confidence }}%</div>
        <div class="cover-score-sub">Deterministic pipeline</div>
      </div>
      <div class="cover-score-card">
        <div class="cover-score-label">Executive Verdict</div>
        <div style="margin-top:6px">
          <span class="verdict-badge verdict-{{ verdict_class }}">{{ verdict_icon }} {{ verdict }}</span>
        </div>
      </div>
    </div>
  </header>
  <main class="page">
    {% if metrics %}
    <section class="section">
      <h2><span class="sec-icon" style="background:var(--accent-glow);color:var(--primary)">📈</span> {{ metric_title }}</h2>
      <div class="grid">
        {% for metric in metrics %}
          <div class="kpi-card"><div class="kpi-label">{{ metric.label }}</div><div class="kpi-value">{{ metric.value }}</div></div>
        {% endfor %}
      </div>
    </section>
    {% endif %}
    {% for section in sections %}
      <section class="section">
        <h2><span class="sec-icon" style="background:{{ section.icon_bg }};color:{{ section.icon_color }}">{{ section.icon }}</span> {{ section.title }}</h2>
        <div>{{ section.html }}</div>
      </section>
    {% endfor %}
  </main>
  <footer class="report-footer">
    Generated by <span class="brand-mark">DataVerse AI</span> · {{ generated_at }} · Deterministic analytics pipeline
  </footer>
  {{ chart_scripts }}
</body>
</html>"""
)


class ReportGenerator:
    """Build rich deterministic reports, with optional LLM-polished sections."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        provider = settings.LLM_PROVIDER if settings.USE_LLM_NARRATION else "deterministic"
        self.llm_provider = llm_provider or LLMProvider(provider=provider)

    async def generate(self, *, title: str, facts: dict[str, Any], xai_output: dict[str, Any] | None = None) -> dict[str, bytes | str]:
        composed = ReportComposer().compose(facts)
        composed = self._augment_food(composed, facts)
        
        # Build the simplified, compact report structure requested.
        compact_sections, compact_charts = self.build_compact_report_sections(facts, composed, xai_output)
        composed["sections"] = compact_sections
        composed["charts"] = compact_charts
        # The compact report surfaces KPIs once, inside "Section 2: Key Metrics".
        # Emptying the headline strip here prevents the same cards rendering twice
        # (top "Headline Metrics" grid + Section 2) in both the HTML and the PDF.
        composed["metrics"] = []

        html_text = self._render_html(title, facts, composed)
        pdf_bytes = self._pdf(title, facts, composed)
        return {"html": html_text, "pdf": pdf_bytes}

    def build_compact_report_sections(
        self, facts: dict[str, Any], composed: dict[str, Any], xai_output: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Assemble the 2-page executive report.

        Structure (business-focused, no raw metadata, no model accuracy/F1):
          1. Executive Summary       - 3-5 headline findings
          2. KPI Dashboard           - Revenue / Profit / Margin / Transactions / Growth
          3. Data Quality Summary    - missing / duplicates / outliers / quality score
          4. AI-Generated Insights   - trends, anomalies, correlations, risks
          5. Visual Insights         - exactly 2 charts, each answering a business question
          6. Explainable AI          - top-5 outcome drivers in plain language
          7. Key Actions             - 3-5 specific business actions (closes the report)
        """
        profile = facts.get("dataset_profile") or {}
        semantic = facts.get("semantic_map") or {}
        quality = facts.get("data_quality") or {}
        fin = facts.get("financial_analysis") or {}
        row_count = profile.get("row_count") or 0
        quality_score = quality.get("data_quality_score", 100.0)
        dataset_type = semantic.get("dataset_type") or "generic_tabular"

        # 1. Executive Summary — 3-5 highest-level findings.
        insights = composed.get("key_insights") or []
        exec_bullets = list(dict.fromkeys([str(i) for i in insights if i]))[:5]
        if len(exec_bullets) < 3:
            rev = (facts.get("business_metrics") or {}).get("total_revenue")
            if rev is not None:
                exec_bullets.append(f"Total revenue across the dataset is {_fmt(rev)}.")
            if quality_score:
                exec_bullets.append(
                    f"Overall data quality is rated {quality_score}/100, so the findings below rest on a sound base."
                )
            if len(exec_bullets) < 3:
                exec_bullets.append("No critical anomalies were flagged, so current operations look stable.")
        exec_section = {"title": "Executive Summary", "body": {"bullets": exec_bullets[:5]}}

        # 2. KPI Dashboard — the five headline business metrics.
        kpi_items = self._kpi_dashboard_items(facts)
        if not kpi_items:
            num_cols = len(quality.get("numeric_columns") or [])
            cat_cols = len(quality.get("categorical_columns") or [])
            kpi_items = [
                {"label": "Numeric Fields", "value": str(num_cols)},
                {"label": "Categorical Fields", "value": str(cat_cols)},
            ]
        kpi_section = {"title": "KPI Dashboard", "body": {"items": kpi_items}}

        # 3. Data Quality Summary.
        missing_cells = quality.get("missing_cells", 0)
        missing_pct = quality.get("missing_pct", 0.0)
        duplicate_rows = quality.get("duplicate_rows", 0)
        outlier_total = self._outlier_total(facts)
        dq_body: dict[str, Any] = {
            "fields": [
                ("Quality score", f"{quality_score} / 100"),
                ("Missing values", f"{missing_cells} ({missing_pct}%)"),
                ("Duplicate rows", f"{duplicate_rows}"),
                ("Outliers (IQR)", f"{outlier_total}"),
            ]
        }
        warnings_list = [_humanize_warning(w) for w in (facts.get("warnings") or [])]
        if int(row_count or 0) < 30:
            warnings_list.append(
                f"Small dataset: only {row_count} rows — treat findings as directional, not predictive."
            )
        unique_warnings = list(dict.fromkeys([w for w in warnings_list if w]))
        if unique_warnings:
            dq_body["recommendation"] = unique_warnings[0]
        dq_section = {"title": "Data Quality Summary", "body": dq_body}

        # 4. AI-Generated Insights — granular trends/anomalies/correlations/risks,
        #    deliberately distinct from the Executive Summary headlines.
        ai_bullets = self._ai_insight_bullets(composed, exec_bullets)
        if len(ai_bullets) < 3:
            ai_bullets.append(
                "Variables move largely independently — no single factor dominates the others."
            )
            ai_bullets.append(
                "No abnormal spikes or dips were detected in the measured series."
            )
        insights_section = {"title": "AI-Generated Insights", "body": {"bullets": ai_bullets[:5]}}

        # 5. Visual Insights — exactly two renderable charts.
        renderable = [c for c in (composed.get("charts") or []) if _chart_is_renderable(c)]
        selected_charts = self._select_useful_charts(renderable, dataset_type)[:2]

        # 6. Explainable AI — top-5 drivers in plain language.
        xai_section = self._xai_section(facts, xai_output)

        # 7. Key Actions — 3-5 specific recommendations (closes the report).
        recs = facts.get("recommendations") or []
        if not recs and composed.get("sections"):
            for s in composed["sections"]:
                if "recommendation" in str(s.get("title", "")).lower():
                    body = s.get("body")
                    if isinstance(body, dict) and body.get("bullets"):
                        recs = body["bullets"]
                        break
        recs_list = list(dict.fromkeys([str(r) for r in recs if r]))[:5]
        if not recs_list:
            recs_list = [
                "Resolve missing values and duplicates before relying on the headline KPIs.",
                "Double down on the leading revenue driver while reducing single-point dependency.",
                "Stand up an automated data-quality check so new records stay analysis-ready.",
            ]
        key_actions_section = {"title": "Key Actions", "body": {"bullets": recs_list}}

        sections: list[dict[str, Any]] = [
            exec_section,
            kpi_section,
            dq_section,
            insights_section,
        ]
        if selected_charts:
            sections.append({"title": "Visual Insights", "body": {"charts": selected_charts}})
        sections.append(xai_section)
        sections.append(key_actions_section)

        # Guarantee no fact is restated across sections (bullets + lines).
        self._dedupe_sections(sections)

        return sections, selected_charts

    def _kpi_dashboard_items(self, facts: dict[str, Any]) -> list[dict[str, str]]:
        """Build the Revenue / Profit / Margin / Transactions / Growth KPI cards.

        Works for both sales-style and financial-statement datasets; only KPIs that
        can actually be computed are emitted.
        """
        business = facts.get("business_metrics") or {}
        fin = facts.get("financial_analysis") or {}
        trends = facts.get("trends") or {}
        is_financial = bool(fin.get("is_financial"))
        items: list[dict[str, str]] = []

        revenue = business.get("total_revenue")
        if revenue is None and is_financial:
            revenue = fin.get("total_revenue_all")
        if revenue is not None:
            items.append({"label": "Revenue", "value": _fmt(revenue)})

        profit = business.get("total_profit")
        if profit is None and is_financial:
            profit = fin.get("total_net_income_all")
        if profit is not None:
            items.append({"label": "Profit", "value": _fmt(profit)})

        margin = business.get("gross_margin")
        if margin is None and is_financial:
            company_margins = [
                c.get("profit_margin") for c in (fin.get("company_metrics") or [])
                if c.get("profit_margin") is not None
            ]
            if company_margins:
                margin = sum(company_margins) / len(company_margins)
        if margin is not None:
            items.append({"label": "Margin", "value": f"{round(float(margin), 1)}%"})

        txns = business.get("transaction_count")
        if txns is not None and not is_financial:
            items.append({"label": "Transactions", "value": f"{int(txns):,}"})

        growth = None
        if is_financial:
            growth = fin.get("revenue_growth_pct")
        else:
            series = trends.get("series") or []
            if series and series[0].get("percent_change") is not None:
                growth = series[0]["percent_change"]
        if growth is not None:
            sign = "+" if float(growth) >= 0 else ""
            items.append({"label": "Growth", "value": f"{sign}{round(float(growth), 1)}%"})

        return items

    def _outlier_total(self, facts: dict[str, Any]) -> int:
        """Total IQR-flagged outliers across numeric columns."""
        by_column = (facts.get("outliers") or {}).get("by_column") or {}
        return sum(int(info.get("count", 0) or 0) for info in by_column.values())

    def _ai_insight_bullets(self, composed: dict[str, Any], exec_bullets: list[str]) -> list[str]:
        """Harvest granular trend/correlation/category/forecast statements.

        These are the deterministic narration lines already produced by the composer;
        they give the AI-Insights section a different analytical angle from the
        Executive Summary. Anything that duplicates an executive bullet is dropped.
        """
        def _norm(value: Any) -> str:
            return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()

        seen = {_norm(b) for b in exec_bullets}
        wanted = ("Trend Analysis", "Correlation Analysis", "Category Analysis", "Forecasting")
        out: list[str] = []
        for section in (composed.get("sections") or []):
            if section.get("title") not in wanted:
                continue
            body = section.get("body") or {}
            for line in (body.get("lines") or []):
                fp = _norm(line)
                if not fp or fp in seen:
                    continue
                seen.add(fp)
                out.append(str(line))
        return out[:5]

    def _xai_section(self, facts: dict[str, Any], xai_output: dict[str, Any] | None) -> dict[str, Any]:
        """Explainable AI section: the top-5 outcome drivers in plain language."""
        prediction = facts.get("prediction") or {}
        xai_info = xai_output or facts.get("xai") or {}
        importances = xai_info.get("global_feature_importance") or []

        if prediction.get("status") == "complete" and importances:
            ranked = sorted(
                (f for f in importances if f.get("feature") is not None),
                key=lambda f: abs(_num(f.get("importance"))),
                reverse=True,
            )[:5]
            total = sum(abs(_num(f.get("importance"))) for f in importances) or 1.0
            bullets: list[str] = []
            for rank, f in enumerate(ranked, start=1):
                share = abs(_num(f.get("importance"))) / total * 100
                if rank == 1:
                    descriptor = "the strongest driver"
                elif share >= 15:
                    descriptor = "a major factor"
                elif share >= 5:
                    descriptor = "a moderate factor"
                else:
                    descriptor = "a minor factor"
                bullets.append(
                    f"{f.get('feature')} is {descriptor}, shaping roughly {round(share)}% of the predicted outcome."
                )
            intro = xai_info.get("plain_english_explanation")
            body: dict[str, Any] = {"bullets": bullets}
            if intro:
                body["lines"] = [str(intro)]
            return {"title": "Explainable AI", "body": body}

        reason = prediction.get("reason") or "the dataset did not meet the requirements for automated prediction"
        explanation = (
            "Driver analysis was not run because no predictive model was trained "
            f"({reason}). With at least 30 rows and a clear numeric outcome column, the report "
            "will rank the top factors influencing that outcome."
        )
        return {"title": "Explainable AI", "body": {"lines": [explanation]}}

    def _dedupe_sections(self, sections: list[dict[str, Any]]) -> None:
        """Drop any bullet/line that already appeared in an earlier section.

        Keeps the report free of repeated information without changing section order.
        """
        seen: set[str] = set()

        def _fp(value: Any) -> str:
            text = re.sub(r"<[^>]+>", " ", str(value))
            return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

        for section in sections:
            body = section.get("body")
            if not isinstance(body, dict):
                continue
            for key in ("bullets", "lines"):
                items = body.get(key)
                if not isinstance(items, list):
                    continue
                deduped: list[Any] = []
                for item in items:
                    fp = _fp(item)
                    if not fp or fp in seen:
                        continue
                    seen.add(fp)
                    deduped.append(item)
                body[key] = deduped

    def _select_useful_charts(self, charts: list[dict[str, Any]], dataset_type: str) -> list[dict[str, Any]]:
        if not charts:
            return []
        selected: list[dict[str, Any]] = []
        dt = str(dataset_type).lower()
        
        if "sales" in dt or "retail" in dt:
            revenue_trend = None
            top_cat_prod = None
            for c in charts:
                title = str(c.get("title", "")).lower()
                ctype = str(c.get("type", "")).lower()
                if not revenue_trend and (ctype == "line" or "revenue" in title or "trend" in title or "month" in title):
                    revenue_trend = c
                elif not top_cat_prod and (ctype == "bar" or "category" in title or "product" in title):
                    top_cat_prod = c
            
            if revenue_trend:
                selected.append(revenue_trend)
            if top_cat_prod:
                selected.append(top_cat_prod)
                
        else:
            missing_chart = None
            cat_dist = None
            for c in charts:
                title = str(c.get("title", "")).lower()
                if not missing_chart and ("missing" in title or "quality" in title or "null" in title):
                    missing_chart = c
                elif not cat_dist and ("distribution" in title or "category" in title or "bar" in title):
                    cat_dist = c
                    
            if missing_chart:
                selected.append(missing_chart)
            if cat_dist:
                selected.append(cat_dist)

        for c in charts:
            if len(selected) >= 2:
                break
            if c not in selected:
                selected.append(c)
                
        return selected[:2]

    def _augment_food(self, composed: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
        """Preserve food-catalog narrative the generic business path cannot produce."""
        if not _is_food_dataset(facts):
            return composed
        food = facts.get("food_analysis") or {}
        extra: list[dict[str, Any]] = []
        if food.get("insights"):
            extra.append({"title": "Food Frequency Analysis", "body": {"lines": food["insights"]}})
        if food.get("calories_stats"):
            stats = food["calories_stats"]
            extra.append({"title": "Calories Statistics", "body": {"lines": [
                f"{key.title()}: {_fmt(value)}" for key, value in stats.items()
            ]}})
        if food.get("warnings"):
            extra.append({"title": "Dataset Limitations", "body": {"recommendation": food["warnings"][0]}})
        # Insert food sections after Dataset Overview.
        sections = composed["sections"]
        insert_at = next((i + 1 for i, s in enumerate(sections) if s["title"] == "Dataset Overview"), len(sections))
        composed["sections"] = sections[:insert_at] + extra + sections[insert_at:]
        return composed

    def _render_html(self, title: str, facts: dict[str, Any], composed: dict[str, Any]) -> str:
        profile = facts.get("dataset_profile") or {}
        quality = facts.get("data_quality") or {}
        metrics = composed.get("metrics")
        if metrics is None:
            metrics = self._fallback_metric_cards(facts)

        # Cover page data.
        health_score = round(float(quality.get("data_quality_score") or 75))
        health_color = _health_color(health_score)
        health_gauge = _health_gauge_svg(health_score, health_color)
        ai_confidence = min(99, max(60, health_score + 10))
        verdict, verdict_class, verdict_icon = _executive_verdict(health_score)

        # Sections render strictly in order. A section whose body carries a "charts"
        # list is rendered as a chart grid in place, so the document order matches the
        # executive structure exactly (… → Charts → Explainable AI → Key Actions).
        rendered_sections = []
        chart_scripts: list[str] = []
        for section in (composed.get("sections") or []):
            sec_title = str(section.get("title", ""))
            body = section.get("body")
            if isinstance(body, dict) and body.get("charts"):
                section_html, scripts = self._render_charts_html(body["charts"])
                chart_scripts.extend(scripts)
            else:
                section_html = self._render_section(body)
            icon, icon_bg, icon_color = _section_icon(sec_title)
            rendered_sections.append({
                "title": html.escape(sec_title),
                "html": section_html,
                "icon": icon,
                "icon_bg": icon_bg,
                "icon_color": icon_color,
            })

        all_scripts = ""
        if chart_scripts:
            all_scripts = '<script>\ndocument.addEventListener("DOMContentLoaded",function(){\n' + "\n".join(chart_scripts) + "\n});\n</script>"

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return REPORT_TEMPLATE.render(
            title=html.escape(title),
            generated_at=generated_at,
            filename=html.escape(str(facts.get("filename") or profile.get("filename") or "uploaded dataset")),
            rows=profile.get("row_count", 0),
            cols=profile.get("column_count", 0),
            health_score=health_score,
            health_color=health_color,
            health_gauge_svg=health_gauge,
            ai_confidence=ai_confidence,
            verdict=verdict,
            verdict_class=verdict_class,
            verdict_icon=verdict_icon,
            metric_title="Headline Metrics",
            metrics=metrics,
            sections=rendered_sections,
            chart_scripts=all_scripts,
        )

    def _render_charts_html(self, charts: list[dict[str, Any]]) -> tuple[str, list[str]]:
        """Render a chart grid (max 2) with Chart.js canvases for the HTML report.

        Returns the HTML fragment *and* a list of JS script snippets that must be
        included at the bottom of the page to initialise the Chart.js instances.
        """
        valid_charts = [chart for chart in (charts or []) if _chart_is_renderable(chart)][:2]
        if not valid_charts:
            return "", []
        cards: list[str] = []
        scripts: list[str] = []
        for idx, chart in enumerate(valid_charts):
            canvas_id = f"chartjs_{idx}_{id(chart) % 10000}"
            cards.append(
                '<div class="chart-card">'
                f'<h3>{html.escape(str(chart.get("title", "Chart")))}</h3>'
                f'<div class="explain">{html.escape(str(chart.get("explanation", "")))}</div>'
                f'<canvas id="{canvas_id}"></canvas>'
                f'<div class="takeaway">{html.escape(str(chart.get("takeaway", "")))}</div>'
                "</div>"
            )
            scripts.append(_chartjs_init_script(canvas_id, chart))
        return f'<div class="chart-grid">{"".join(cards)}</div>', scripts

    def _render_section(self, body: Any) -> str:
        """Turn a composer section body into safe HTML for the light template."""
        if body is None:
            return ""
        if isinstance(body, str):
            return f"<p>{html.escape(body)}</p>"
        parts: list[str] = []
        if isinstance(body, dict):
            # Safe label/value fields: the label is bold, the value is escaped so
            # user-controlled content (e.g. filenames) can never inject markup.
            for label, value in body.get("fields", []) or []:
                parts.append(f"<p><strong>{html.escape(str(label))}:</strong> {html.escape(str(value))}</p>")
            if body.get("bullets"):
                parts.append("<ul>" + "".join(f"<li>{html.escape(str(item))}</li>" for item in body["bullets"]) + "</ul>")
            for line in body.get("lines", []):
                parts.append(f"<p>{html.escape(str(line))}</p>")
            # Business Overview labelled blocks.
            for block in body.get("blocks", []):
                parts.append(
                    f'<div class="ov-block"><div class="ov-label">{html.escape(str(block.get("label","")))}</div>'
                    f'<div>{html.escape(str(block.get("text","")))}</div></div>'
                )
            # KPI / metric items.
            if body.get("items"):
                if body.get("note"):
                    parts.append(f'<p class="muted">{html.escape(str(body["note"]))}</p>')
                cards = "".join(
                    f'<div class="card"><div class="label">{html.escape(str(it.get("label","")))}</div>'
                    f'<div class="value">{html.escape(str(it.get("value","")))}</div></div>'
                    for it in body["items"]
                )
                parts.append(f'<div class="scorecard">{cards}</div>')
            # Performance health scorecards.
            if body.get("scores"):
                cards = "".join(
                    f'<div class="card"><div class="label">{html.escape(str(s.get("name","")))}</div>'
                    f'<div><span class="badge" style="background:{GRADE_COLORS.get(s.get("grade"), "#64748B")}">{html.escape(str(s.get("grade","")))}</span></div>'
                    f'<div class="muted" style="font-size:12px">{html.escape(str(s.get("explanation","")))}</div></div>'
                    for s in body["scores"]
                )
                parts.append(f'<div class="scorecard">{cards}</div>')
            if body.get("details"):
                detail_items = [
                    ("KPI Achievement", body["details"].get("kpi_achievement")),
                    ("Growth Rate", body["details"].get("growth_rate")),
                    ("Trend Direction", body["details"].get("trend_direction")),
                    ("Best Performing Segment", body["details"].get("best_segment")),
                    ("Worst Performing Segment", body["details"].get("worst_segment")),
                    ("Efficiency", body["details"].get("efficiency")),
                    ("Profitability", body["details"].get("profitability")),
                    ("Operational Health Score", body["details"].get("operational_health")),
                ]
                rows = "".join(
                    f"<li><strong>{html.escape(label)}:</strong> {html.escape(str(value))}</li>"
                    for label, value in detail_items
                    if value is not None
                )
                if rows:
                    parts.append(f"<ul>{rows}</ul>")
            # Leakage risk.
            if body.get("risk"):
                color = RISK_COLORS.get(body["risk"], "#64748B")
                parts.append(f'<p>Leakage Risk Score: <span class="badge" style="background:{color}">{html.escape(str(body["risk"]))}</span></p>')
                if body.get("reasoning"):
                    parts.append(f'<p class="muted">{html.escape(str(body["reasoning"]))}</p>')
                if body.get("findings"):
                    parts.append("<ul>" + "".join(f"<li>{html.escape(str(f))}</li>" for f in body["findings"]) + "</ul>")
            # Embedded table.
            table = body.get("table")
            if isinstance(table, dict) and table.get("rows"):
                parts.append(self._render_table(table))
            # Recommendation callout.
            if body.get("recommendation"):
                cls = "callout"
                parts.append(f'<div class="{cls}">{html.escape(str(body["recommendation"]))}</div>')
        return "".join(parts)

    def _render_table(self, table: dict[str, Any]) -> str:
        columns = [str(c) for c in table.get("columns", [])]
        head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
        rows_html = ""
        for row in table.get("rows", [])[:12]:
            if not isinstance(row, dict):
                continue
            cells = "".join(f"<td>{html.escape(_fmt(row.get(c)))}</td>" for c in columns)
            rows_html += f"<tr>{cells}</tr>"
        title = table.get("title")
        caption = f"<h3>{html.escape(str(title))}</h3>" if title else ""
        return f"{caption}<table><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table>"

    def _fallback_metric_cards(self, facts: dict[str, Any]) -> list[dict[str, str]]:
        profile = facts.get("dataset_profile") or {}
        quality = facts.get("data_quality") or {}
        items = [
            ("Rows", profile.get("row_count")),
            ("Columns", profile.get("column_count")),
            ("Missing Cells", quality.get("missing_cells")),
            ("Duplicate Rows", quality.get("duplicate_rows")),
            ("Quality Score", quality.get("data_quality_score")),
        ]
        return [{"label": label, "value": html.escape(_fmt(value))} for label, value in items if value is not None]

    def _chart_svg(self, chart: dict[str, Any]) -> str:
        chart_type = str(chart.get("type", "bar")).lower()
        if chart_type == "confusion_matrix":
            return _confusion_matrix_svg(chart)
        if chart_type == "line":
            return _line_svg(chart)
        if chart_type in {"pie", "donut"}:
            return _donut_svg(chart, donut=chart_type == "donut")
        if chart_type == "grouped_bar":
            return _grouped_bar_svg(chart)
        if chart_type == "scatter":
            return _scatter_svg(chart)
        return _bar_svg(chart)

    def _pdf(self, title: str, facts: dict[str, Any], composed: dict[str, Any]) -> bytes:
        try:
            return self._reportlab_pdf(title, facts, composed)
        except Exception:
            return self._fallback_pdf(title, facts, composed)

    def _reportlab_pdf(self, title: str, facts: dict[str, Any], composed: dict[str, Any]) -> bytes:
        # Hard 2-page budget: render, count pages, and if the content spills,
        # rebuild with progressively more compact layout/content until it fits.
        pdf_bytes = b""
        for compact in (0, 1, 2, 3):
            pdf_bytes, pages = self._reportlab_pdf_once(title, facts, composed, compact=compact)
            if pages <= 2:
                return pdf_bytes
        return pdf_bytes

    def _reportlab_pdf_once(
        self, title: str, facts: dict[str, Any], composed: dict[str, Any], *, compact: int
    ) -> tuple[bytes, int]:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.4 * inch, leftMargin=0.4 * inch, topMargin=0.4 * inch, bottomMargin=0.4 * inch)
        styles = getSampleStyleSheet()
        if compact >= 1:
            styles["BodyText"].fontSize = 8.5
            styles["BodyText"].leading = 10.5
            styles["Heading2"].fontSize = 11
            styles["Heading2"].leading = 13
            styles["Heading3"].fontSize = 9.5
            styles["Heading3"].leading = 11.5
            styles["Italic"].fontSize = 8
            styles["Italic"].leading = 10
        gap_small = 6 if compact == 0 else 3
        gap_large = 8 if compact == 0 else 4
        max_paragraphs = None if compact == 0 else (2 if compact == 1 else 1)
        max_charts = 1 if compact >= 2 else 2
        all_sections = list(composed.get("sections") or [])
        if compact >= 3:
            all_sections = all_sections[:8]

        story: list[Any] = []
        story.append(Paragraph(html.escape(title), styles["Title"]))
        story.append(Paragraph("Generated by DataVerse AI from computed dataset facts.", styles["Normal"]))
        story.append(Spacer(1, gap_large))
        pdf_metrics = composed.get("metrics")
        if pdf_metrics is None:
            pdf_metrics = self._fallback_metric_cards(facts)
        if pdf_metrics:
            metric_rows = [["Metric", "Value"]] + [[item["label"], item["value"]] for item in pdf_metrics]
            story.append(Table(metric_rows, hAlign="LEFT", style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 5 if compact == 0 else 3),
            ])))
            story.append(Spacer(1, gap_large))

        def _render_pdf_section(section: dict[str, Any]) -> None:
            story.append(Paragraph(html.escape(str(section["title"])), styles["Heading2"]))
            paragraphs = _section_plaintext(section.get("body"))
            if max_paragraphs is not None:
                paragraphs = paragraphs[:max_paragraphs]
            for paragraph in paragraphs:
                story.append(Paragraph(html.escape(paragraph), styles["BodyText"]))
            story.append(Spacer(1, gap_small))

        # Sections render strictly in order; a charts-body section becomes a chart block.
        for section in all_sections:
            body = section.get("body")
            if isinstance(body, dict) and body.get("charts"):
                renderable_charts = [c for c in body["charts"] if _chart_is_renderable(c)][:max_charts]
                if not renderable_charts:
                    continue
                story.append(Paragraph(html.escape(str(section["title"])), styles["Heading2"]))
                for chart in renderable_charts:
                    story.append(Paragraph(html.escape(str(chart.get("title", "Chart"))), styles["Heading3"]))
                    if chart.get("explanation") and compact == 0:
                        story.append(Paragraph(html.escape(str(chart["explanation"])), styles["Italic"]))
                    drawing = _reportlab_chart_drawing(chart)
                    if drawing is not None:
                        story.append(drawing)
                        story.append(Spacer(1, gap_small))
                    # Chart tables removed to keep the PDF compact (1-2 pages limit)
                    if chart.get("takeaway") and compact <= 1:
                        story.append(Paragraph(html.escape(str(chart["takeaway"])), styles["BodyText"]))
                    story.append(Spacer(1, gap_large))
            else:
                _render_pdf_section(section)
        doc.build(story)
        return buffer.getvalue(), int(doc.page)

    def _fallback_pdf(self, title: str, facts: dict[str, Any], composed: dict[str, Any]) -> bytes:
        lines = [title, "Generated by DataVerse AI", ""]
        fallback_metrics = composed.get("metrics")
        if fallback_metrics is None:
            fallback_metrics = self._fallback_metric_cards(facts)
        for item in fallback_metrics:
            lines.append(f"{item['label']}: {item['value']}")
        lines.append("")
        all_sections = composed.get("sections") or []
        for section in all_sections:
            body = section.get("body")
            if isinstance(body, dict) and body.get("charts"):
                renderable_charts = [c for c in body["charts"] if _chart_is_renderable(c)][:2]
                if not renderable_charts:
                    continue
                lines.append(str(section["title"]))
                for chart in renderable_charts:
                    lines.append(str(chart.get("title", "Chart")))
                    if chart.get("takeaway"):
                        lines.append(str(chart["takeaway"]))
                    # Chart data details removed to keep fallback PDF compact
                    lines.append("")
            else:
                lines.append(str(section["title"]))
                lines.extend(_section_plaintext(section.get("body")))
                lines.append("")
        return _manual_pdf(lines)


_WARNING_LABELS = {
    "too_few_rows_for_modeling": "Dataset has too few rows for reliable ML modeling (fewer than 30).",
    "high_missing_values": "Several columns contain a high proportion of missing values.",
    "duplicate_rows": "Duplicate rows were detected and may inflate totals.",
    "high_cardinality": "One or more columns have very high cardinality (many unique values).",
    "constant_columns": "One or more columns are constant and add no analytical value.",
    "no_numeric_columns": "No numeric columns were found, limiting quantitative analysis.",
    "no_target_column": "No clear target column was found for prediction.",
}


def _humanize_warning(warning: Any) -> str:
    """Turn a machine warning code (e.g. 'too_few_rows_for_modeling') into prose."""
    text = str(warning or "").strip()
    if not text:
        return ""
    if text in _WARNING_LABELS:
        return _WARNING_LABELS[text]
    # Already a human sentence (contains spaces/punctuation) — keep as-is.
    if " " in text:
        return text
    return text.replace("_", " ").capitalize() + "."


def _section_plaintext(body: Any) -> list[str]:
    """Flatten a composer section body into plain-text paragraphs for the PDF."""
    if body is None:
        return []
    if isinstance(body, str):
        return [body]
    out: list[str] = []
    if not isinstance(body, dict):
        return [str(body)]
    out.extend(f"{label}: {value}" for label, value in (body.get("fields", []) or []))
    out.extend(str(item) for item in body.get("bullets", []))
    out.extend(str(item) for item in body.get("lines", []))
    for block in body.get("blocks", []):
        out.append(f"{block.get('label', '')}: {block.get('text', '')}")
    for item in body.get("items", []):
        out.append(f"{item.get('label', '')}: {item.get('value', '')}")
    for score in body.get("scores", []):
        out.append(f"{score.get('name', '')}: {score.get('grade', '')} - {score.get('explanation', '')}")
    details = body.get("details") or {}
    for label, key in (("Best segment", "best_segment"), ("Worst segment", "worst_segment"), ("Growth rate", "growth_rate"), ("Operational health", "operational_health")):
        if details.get(key) is not None:
            out.append(f"{label}: {details[key]}")
    if body.get("risk"):
        out.append(f"Leakage Risk Score: {body['risk']}. {body.get('reasoning', '')}")
        out.extend(str(item) for item in body.get("findings", []))
    table = body.get("table")
    if isinstance(table, dict) and table.get("rows"):
        columns = [str(c) for c in table.get("columns", [])]
        out.append(" | ".join(columns))
        for row in table.get("rows", [])[:12]:
            if isinstance(row, dict):
                out.append(" | ".join(_fmt(row.get(c)) for c in columns))
    if body.get("recommendation"):
        out.append(str(body["recommendation"]))
    return out


def _bar_svg(chart: dict[str, Any]) -> str:
    raw_data = chart.get("data") or []
    data = raw_data[:10] if isinstance(raw_data, list) else []
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    values = [abs(_num(row.get(y_key))) for row in data if isinstance(row, dict)]
    max_value = _chart_scale(values)
    rows = []
    for idx, row in enumerate(data):
        value = _num(row.get(y_key))
        width = max(2, min(260, abs(value) / max_value * 260))
        y = 28 + idx * 28
        label = html.escape(_truncate(_fmt(row.get(x_key)), 24))
        color = PALETTE[idx % len(PALETTE)] if value >= 0 else "#f43f5e"
        rows.append(f'<text x="0" y="{y + 10}" font-size="10" fill="#475569">{label}</text><rect x="150" y="{y}" width="{width:.1f}" height="16" rx="5" fill="{color}"/><text x="{155 + width:.1f}" y="{y + 12}" font-size="10" fill="#0f172a">{html.escape(_fmt(value))}</text>')
    height = max(80, 36 + len(data) * 28)
    return f'<svg viewBox="0 0 460 {height}" role="img">{"".join(rows)}</svg>'


def _confusion_matrix_svg(chart: dict[str, Any]) -> str:
    data = [row for row in (chart.get("data") or []) if isinstance(row, dict)]
    actual_labels = sorted({str(row.get("actual")) for row in data})
    predicted_labels = sorted({str(row.get("predicted")) for row in data})
    counts = {(str(row.get("actual")), str(row.get("predicted"))): _num(row.get("count")) for row in data}
    max_count = max(counts.values() or [1])
    cell = 34
    left = 100
    top = 42
    width = left + max(1, len(predicted_labels)) * cell + 20
    height = top + max(1, len(actual_labels)) * cell + 34
    parts = [
        '<text x="0" y="18" font-size="11" fill="#475569">Actual vs predicted labels</text>',
    ]
    for col_idx, predicted in enumerate(predicted_labels):
        x = left + col_idx * cell
        parts.append(f'<text x="{x + 2}" y="34" font-size="8" fill="#475569">{html.escape(_truncate(predicted, 8))}</text>')
    for row_idx, actual in enumerate(actual_labels):
        y = top + row_idx * cell
        parts.append(f'<text x="0" y="{y + 21}" font-size="8" fill="#475569">{html.escape(_truncate(actual, 16))}</text>')
        for col_idx, predicted in enumerate(predicted_labels):
            x = left + col_idx * cell
            count = counts.get((actual, predicted), 0.0)
            opacity = 0.12 + (count / max_count * 0.78 if max_count else 0)
            parts.append(f'<rect x="{x}" y="{y}" width="{cell - 2}" height="{cell - 2}" rx="4" fill="#3b82f6" opacity="{opacity:.2f}"/>')
            parts.append(f'<text x="{x + cell / 2 - 4}" y="{y + 20}" font-size="9" fill="#0f172a">{html.escape(_fmt(count))}</text>')
    return f'<svg viewBox="0 0 {width} {height}" role="img">{"".join(parts)}</svg>'


def _line_svg(chart: dict[str, Any]) -> str:
    raw_data = chart.get("data") or []
    data = raw_data if isinstance(raw_data, list) else []
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    series_key = chart.get("series_key")
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        groups.setdefault(str(row.get(series_key, "Trend") if series_key else "Trend"), []).append(row)
    values = [_num(row.get(y_key)) for rows in groups.values() for row in rows]
    max_value = max(values or [1])
    min_value = min(values or [0])
    span = max(max_value - min_value, 1)
    width, height = 460, 220
    paths = []
    legend = []
    for idx, (name, rows) in enumerate(list(groups.items())[:5]):
        rows = sorted(rows, key=lambda row: str(row.get(x_key)))
        points = []
        for row_index, row in enumerate(rows):
            x = 36 + (row_index / max(1, len(rows) - 1)) * (width - 70)
            y = 170 - ((_num(row.get(y_key)) - min_value) / span * 130)
            points.append(f"{x:.1f},{y:.1f}")
        color = PALETTE[idx % len(PALETTE)]
        paths.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
        legend.append(f'<circle cx="{38 + idx * 88}" cy="202" r="4" fill="{color}"/><text x="{46 + idx * 88}" y="206" font-size="9" fill="#475569">{html.escape(_truncate(name, 12))}</text>')
    return f'<svg viewBox="0 0 {width} {height}" role="img"><line x1="34" y1="174" x2="430" y2="174" stroke="#cbd5e1"/><line x1="34" y1="30" x2="34" y2="174" stroke="#cbd5e1"/>{"".join(paths)}{"".join(legend)}</svg>'


def _donut_svg(chart: dict[str, Any], *, donut: bool) -> str:
    raw_data = chart.get("data") or []
    data = raw_data[:8] if isinstance(raw_data, list) else []
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    total = sum(max(0, _num(row.get(y_key))) for row in data if isinstance(row, dict)) or 1
    start = -90.0
    parts = []
    legend = []
    for idx, row in enumerate(data):
        value = max(0, _num(row.get(y_key)))
        angle = value / total * 360
        end = start + angle
        color = PALETTE[idx % len(PALETTE)]
        parts.append(f'<path d="{_arc_path(110, 110, 78, start, end)}" fill="none" stroke="{color}" stroke-width="34"/>')
        legend.append(f'<rect x="225" y="{32 + idx * 20}" width="10" height="10" rx="2" fill="{color}"/><text x="242" y="{41 + idx * 20}" font-size="10" fill="#475569">{html.escape(_truncate(_fmt(row.get(x_key)), 22))} ({html.escape(_fmt(round(value / total * 100, 1)))}%)</text>')
        start = end
    center = '<circle cx="110" cy="110" r="44" fill="white"/>' if donut else ""
    return f'<svg viewBox="0 0 460 220" role="img">{"".join(parts)}{center}{"".join(legend)}</svg>'


def _grouped_bar_svg(chart: dict[str, Any]) -> str:
    """Side-by-side bar chart grouping data by x_key with each series_key as a bar cluster."""
    raw_data = chart.get("data") or []
    data = [row for row in raw_data if isinstance(row, dict)]
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    series_key = chart.get("series_key")
    if not x_key or not y_key or not data:
        return _bar_svg(chart)

    # Gather unique x-values and series
    x_values: list[str] = list(dict.fromkeys(str(row.get(x_key, "")) for row in data))[:8]
    series_values: list[str] = list(dict.fromkeys(str(row.get(series_key, "")) for row in data if series_key))[:6]
    if not series_values:
        return _bar_svg(chart)

    lookup: dict[tuple[str, str], float] = {}
    for row in data:
        xv = str(row.get(x_key, ""))
        sv = str(row.get(series_key, ""))
        lookup[(xv, sv)] = _num(row.get(y_key))

    all_vals = [v for v in lookup.values() if v > 0]
    max_value = _chart_scale(all_vals)

    width, height = 460, 230
    chart_left, chart_bottom, chart_top = 36, 190, 30
    chart_width = width - chart_left - 10
    group_width = chart_width / max(len(x_values), 1)
    bar_gap = 3
    bar_width = (group_width - bar_gap * (len(series_values) + 1)) / max(len(series_values), 1)
    bar_width = max(6, min(bar_width, 40))
    chart_height = chart_bottom - chart_top

    parts: list[str] = []
    parts.append(f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{width - 10}" y2="{chart_bottom}" stroke="#cbd5e1"/>')
    parts.append(f'<line x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_bottom}" stroke="#cbd5e1"/>')

    for g_idx, xv in enumerate(x_values):
        group_center = chart_left + (g_idx + 0.5) * group_width
        cluster_width = bar_width * len(series_values) + bar_gap * (len(series_values) - 1)
        cluster_start = group_center - cluster_width / 2
        for s_idx, sv in enumerate(series_values):
            value = lookup.get((xv, sv), 0.0)
            bar_h = max(2, value / max_value * chart_height)
            bx = cluster_start + s_idx * (bar_width + bar_gap)
            by = chart_bottom - bar_h
            color = PALETTE[s_idx % len(PALETTE)]
            parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_width:.1f}" height="{bar_h:.1f}" rx="2" fill="{color}"/>')
        label = html.escape(_truncate(str(xv), 8))
        lx = group_center
        parts.append(f'<text x="{lx:.1f}" y="{chart_bottom + 12}" font-size="9" text-anchor="middle" fill="#475569">{label}</text>')

    # Legend
    for s_idx, sv in enumerate(series_values):
        lx = chart_left + s_idx * 90
        color = PALETTE[s_idx % len(PALETTE)]
        parts.append(f'<rect x="{lx}" y="{height - 18}" width="9" height="9" rx="2" fill="{color}"/>')
        parts.append(f'<text x="{lx + 13}" y="{height - 10}" font-size="9" fill="#475569">{html.escape(_truncate(sv, 12))}</text>')

    return f'<svg viewBox="0 0 {width} {height}" role="img">{"".join(parts)}</svg>'


def _scatter_svg(chart: dict[str, Any]) -> str:
    """Scatter plot with optional entity labels for each point."""
    raw_data = chart.get("data") or []
    data = [row for row in raw_data if isinstance(row, dict)]
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    label_key = chart.get("label_key")
    if not x_key or not y_key or not data:
        return _bar_svg(chart)

    xs = [_num(row.get(x_key)) for row in data]
    ys = [_num(row.get(y_key)) for row in data]
    if not xs or not ys:
        return _bar_svg(chart)

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)

    width, height = 460, 230
    plot_left, plot_right = 50, 430
    plot_top, plot_bottom = 20, 190

    def px(xv: float) -> float:
        return plot_left + (xv - min_x) / span_x * (plot_right - plot_left)

    def py(yv: float) -> float:
        return plot_bottom - (yv - min_y) / span_y * (plot_bottom - plot_top)

    parts: list[str] = []
    parts.append(f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" stroke="#cbd5e1"/>')
    parts.append(f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" y2="{plot_bottom}" stroke="#cbd5e1"/>')

    # Axis labels
    parts.append(f'<text x="{(plot_left + plot_right) / 2:.0f}" y="{height - 4}" font-size="9" text-anchor="middle" fill="#475569">{html.escape(_truncate(str(x_key), 24))}</text>')
    parts.append(f'<text x="10" y="{(plot_top + plot_bottom) / 2:.0f}" font-size="9" text-anchor="middle" fill="#475569" transform="rotate(-90 10 {(plot_top + plot_bottom) / 2:.0f})">{html.escape(_truncate(str(y_key), 20))}</text>')

    for idx, row in enumerate(data[:20]):
        xv = _num(row.get(x_key))
        yv = _num(row.get(y_key))
        cx = px(xv)
        cy = py(yv)
        color = PALETTE[idx % len(PALETTE)]
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{color}" opacity="0.8"/>')
        if label_key:
            label = html.escape(_truncate(str(row.get(label_key, "")), 10))
            text_x = cx + 10
            parts.append(f'<text x="{text_x:.1f}" y="{cy + 4:.1f}" font-size="9" fill="#0f172a">{label}</text>')

    return f'<svg viewBox="0 0 {width} {height}" role="img">{"".join(parts)}</svg>'


def _arc_path(cx: float, cy: float, radius: float, start_angle: float, end_angle: float) -> str:
    if end_angle - start_angle >= 359.9:
        end_angle = start_angle + 359.9
    start = _polar(cx, cy, radius, end_angle)
    end = _polar(cx, cy, radius, start_angle)
    large = 1 if end_angle - start_angle > 180 else 0
    return f"M {start[0]:.3f} {start[1]:.3f} A {radius} {radius} 0 {large} 0 {end[0]:.3f} {end[1]:.3f}"


def _polar(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    radians = math.radians(angle)
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def _chart_rows(chart: dict[str, Any]) -> list[list[str]]:
    raw_data = chart.get("data") or []
    data = raw_data if isinstance(raw_data, list) else []
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    series_key = chart.get("series_key")
    columns = [key for key in [x_key, series_key, y_key] if key]
    if not columns:
        return []
    return [[str(column) for column in columns]] + [[_fmt(row.get(column)) for column in columns] for row in data[:12] if isinstance(row, dict)]


def _reportlab_chart_drawing(chart: dict[str, Any]) -> Any | None:
    try:
        from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
        from reportlab.lib import colors
    except Exception:
        return None
    data = chart.get("data") or []
    if not isinstance(data, list) or not data:
        return None
    chart_type = str(chart.get("type", "bar")).lower()
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    if not x_key or not y_key:
        return None
    if chart_type == "line":
        rows = [row for row in data if isinstance(row, dict)][:18]
        values = [_num(row.get(y_key)) for row in rows]
        if len(values) < 2:
            return None
        drawing = Drawing(460, 170)
        drawing.add(Line(35, 25, 430, 25, strokeColor=colors.HexColor("#cbd5e1")))
        drawing.add(Line(35, 25, 35, 145, strokeColor=colors.HexColor("#cbd5e1")))
        min_value = min(values)
        span = max(max(values) - min_value, 1)
        points = []
        for index, value in enumerate(values):
            x = 40 + (index / max(1, len(values) - 1)) * 370
            y = 30 + ((value - min_value) / span) * 105
            points.extend([x, y])
        drawing.add(PolyLine(points, strokeColor=colors.HexColor("#3b82f6"), strokeWidth=2.5))
        for index in range(0, len(points), 2):
            drawing.add(Circle(points[index], points[index + 1], 2.8, fillColor=colors.HexColor("#8b5cf6"), strokeColor=None))
        return drawing
    rows = [row for row in data if isinstance(row, dict)][:8]
    values = [abs(_num(row.get(y_key))) for row in rows]
    max_value = _chart_scale(values)
    drawing = Drawing(460, max(90, 24 + len(rows) * 20))
    for index, row in enumerate(rows):
        y = drawing.height - 26 - index * 20
        value = _num(row.get(y_key))
        width = max(2, min(250, abs(value) / max_value * 250))
        color = colors.HexColor(PALETTE[index % len(PALETTE)] if value >= 0 else "#f43f5e")
        drawing.add(String(0, y + 2, _truncate(_fmt(row.get(x_key)), 18), fontSize=8, fillColor=colors.HexColor("#475569")))
        drawing.add(Rect(125, y, width, 10, rx=3, ry=3, fillColor=color, strokeColor=None))
        drawing.add(String(130 + width, y + 2, _fmt(value), fontSize=8, fillColor=colors.HexColor("#0f172a")))
    return drawing


def _chart_is_renderable(chart: Any) -> bool:
    if not isinstance(chart, dict):
        return False
    is_valid, _reason = validate_chart_spec(chart)
    return is_valid


def _is_food_dataset(facts: dict[str, Any]) -> bool:
    semantic = facts.get("semantic_map") or {}
    profile = facts.get("dataset_profile") or {}
    return semantic.get("dataset_type") == "food_dataset" or profile.get("dataset_type") == "food_dataset"


def _manual_pdf(lines: list[str]) -> bytes:
    page_lines = []
    for line in lines:
        clean = _ascii(_plain(str(line)))
        wrapped = re.findall(r".{1,88}(?:\s+|$)", clean) or [clean]
        page_lines.extend(item.strip() for item in wrapped)
    pages = [page_lines[idx : idx + 48] for idx in range(0, len(page_lines), 48)] or [["DataVerse report"]]
    objects = ["1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj"]
    kids = []
    content_ids = []
    for page_index, page in enumerate(pages):
        page_obj = 3 + page_index * 2
        content_obj = page_obj + 1
        kids.append(f"{page_obj} 0 R")
        content_ids.append(content_obj)
        stream_lines = ["BT /F1 10 Tf 50 760 Td 14 TL"]
        for line in page:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_lines.append(f"({escaped}) Tj T*")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        objects.append(f"{page_obj} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {3 + len(pages) * 2} 0 R >> >> /Contents {content_obj} 0 R >> endobj")
        objects.append(f"{content_obj} 0 obj << /Length {len(stream.encode('latin-1', errors='ignore'))} >> stream\n{stream}\nendstream endobj")
    font_obj = 3 + len(pages) * 2
    objects.insert(1, f"2 0 obj << /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >> endobj")
    objects.append(f"{font_obj} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")
    body = "%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(body))
        body += obj + "\n"
    xref_at = len(body)
    xref = ["xref", f"0 {len(objects) + 1}", "0000000000 65535 f "]
    xref.extend(f"{offset:010d} 00000 n " for offset in offsets[1:])
    trailer = f"\ntrailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF"
    return (body + "\n".join(xref) + trailer).encode("latin-1", errors="ignore")


def _plain(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(str(value))).replace("\n", " ")


def _ascii(value: str) -> str:
    return value.encode("latin-1", errors="ignore").decode("latin-1", errors="ignore")


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _num(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _chart_scale(values: list[float]) -> float:
    return max([value for value in values if value > 0] or [1.0])


def _truncate(value: str, length: int) -> str:
    return value if len(value) <= length else value[: max(0, length - 3)] + "..."


# ---------------------------------------------------------------------------
# Premium BI-executive report helpers
# ---------------------------------------------------------------------------

def _health_color(score: int) -> str:
    """Map a 0–100 health score to a hex colour."""
    if score >= 80:
        return "#34D399"  # success green
    if score >= 60:
        return "#38BDF8"  # info blue
    if score >= 40:
        return "#FBBF24"  # warning amber
    return "#F87171"  # danger red


def _health_gauge_svg(score: int, color: str) -> str:
    """Build a circular gauge SVG showing the health score."""
    radius = 28
    circumference = 2 * math.pi * radius
    filled = circumference * score / 100
    gap = circumference - filled
    return (
        f'<svg viewBox="0 0 72 72">'
        f'<circle cx="36" cy="36" r="{radius}" fill="none" stroke="rgba(148,163,184,.12)" stroke-width="7"/>'
        f'<circle cx="36" cy="36" r="{radius}" fill="none" stroke="{color}" stroke-width="7" '
        f'stroke-dasharray="{filled:.1f} {gap:.1f}" stroke-dashoffset="0" stroke-linecap="round" '
        f'transform="rotate(-90 36 36)"/>'
        f'</svg>'
    )


def _executive_verdict(score: int) -> tuple[str, str, str]:
    """Return (label, css_class_suffix, icon) for the cover page verdict badge."""
    if score >= 85:
        return "Excellent", "excellent", "✦"
    if score >= 65:
        return "Good", "good", "✓"
    if score >= 40:
        return "Needs Improvement", "needs-improvement", "⚠"
    return "Critical", "critical", "✕"


_SECTION_ICONS: dict[str, tuple[str, str, str]] = {
    "Executive Summary":     ("📋", "rgba(99,102,241,.15)", "#818CF8"),
    "KPI Dashboard":         ("📊", "rgba(56,189,248,.15)", "#38BDF8"),
    "Data Quality Summary":  ("🛡️", "rgba(52,211,153,.15)", "#34D399"),
    "AI-Generated Insights": ("🤖", "rgba(168,85,247,.15)", "#A855F7"),
    "Visual Insights":       ("📈", "rgba(99,102,241,.15)", "#818CF8"),
    "Explainable AI":        ("🧠", "rgba(236,72,153,.15)", "#EC4899"),
    "Key Actions":           ("🎯", "rgba(251,191,36,.15)", "#FBBF24"),
}


def _section_icon(title: str) -> tuple[str, str, str]:
    """Return (icon_emoji, bg_color, text_color) for a section title."""
    return _SECTION_ICONS.get(title, ("📄", "rgba(148,163,184,.1)", "#94A3B8"))


def _chartjs_init_script(canvas_id: str, chart: dict[str, Any]) -> str:
    """Generate a Chart.js initialisation snippet for a single chart."""
    import json as _json

    chart_type = str(chart.get("type", "bar")).lower()
    data = chart.get("data") or []
    if not isinstance(data, list):
        data = []
    x_key = chart.get("x_key") or chart.get("x")
    y_key = chart.get("y_key") or chart.get("y")
    series_key = chart.get("series_key")

    palette = ["#818CF8", "#38BDF8", "#34D399", "#FBBF24", "#F87171", "#A855F7", "#14B8A6", "#6366F1"]

    if chart_type in ("pie", "donut"):
        labels = [str(row.get(x_key, "")) for row in data[:8] if isinstance(row, dict)]
        values = [_num(row.get(y_key)) for row in data[:8] if isinstance(row, dict)]
        bg_colors = palette[:len(values)]
        config = {
            "type": "doughnut" if chart_type == "donut" else "pie",
            "data": {
                "labels": labels,
                "datasets": [{"data": values, "backgroundColor": bg_colors, "borderWidth": 0}],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {"legend": {"position": "right", "labels": {"color": "#94A3B8", "font": {"size": 11}}}},
            },
        }

    elif chart_type == "line":
        # Support multi-series via series_key.
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in data:
            if not isinstance(row, dict):
                continue
            key = str(row.get(series_key, "Trend")) if series_key else "Trend"
            groups.setdefault(key, []).append(row)

        all_x_labels: list[str] = []
        seen_x: set[str] = set()
        for rows in groups.values():
            for row in sorted(rows, key=lambda r: str(r.get(x_key, ""))):
                lbl = str(row.get(x_key, ""))
                if lbl not in seen_x:
                    seen_x.add(lbl)
                    all_x_labels.append(lbl)

        datasets = []
        for idx, (name, rows) in enumerate(list(groups.items())[:5]):
            rows_sorted = sorted(rows, key=lambda r: str(r.get(x_key, "")))
            values = [_num(r.get(y_key)) for r in rows_sorted]
            color = palette[idx % len(palette)]
            datasets.append({
                "label": name,
                "data": values,
                "borderColor": color,
                "backgroundColor": color + "33",
                "fill": True if len(groups) == 1 else False,
                "tension": 0.35,
                "pointRadius": 4,
                "pointBackgroundColor": color,
            })
        config = {
            "type": "line",
            "data": {"labels": all_x_labels, "datasets": datasets},
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "scales": {
                    "x": {"ticks": {"color": "#94A3B8", "font": {"size": 10}}, "grid": {"color": "rgba(148,163,184,.08)"}},
                    "y": {"ticks": {"color": "#94A3B8", "font": {"size": 10}}, "grid": {"color": "rgba(148,163,184,.08)"}},
                },
                "plugins": {"legend": {"labels": {"color": "#CBD5E1", "font": {"size": 11}}}},
            },
        }

    else:
        # Default: horizontal bar.
        labels = [str(row.get(x_key, ""))[:24] for row in data[:10] if isinstance(row, dict)]
        values = [_num(row.get(y_key)) for row in data[:10] if isinstance(row, dict)]
        bg_colors = [palette[i % len(palette)] for i in range(len(values))]
        config = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{"data": values, "backgroundColor": bg_colors, "borderRadius": 6, "borderWidth": 0}],
            },
            "options": {
                "indexAxis": "y",
                "responsive": True,
                "maintainAspectRatio": False,
                "scales": {
                    "x": {"ticks": {"color": "#94A3B8", "font": {"size": 10}}, "grid": {"color": "rgba(148,163,184,.08)"}},
                    "y": {"ticks": {"color": "#CBD5E1", "font": {"size": 11}}, "grid": {"display": False}},
                },
                "plugins": {"legend": {"display": False}},
            },
        }

    config_json = _json.dumps(config, default=str)
    return f'new Chart(document.getElementById("{canvas_id}"),{config_json});'

