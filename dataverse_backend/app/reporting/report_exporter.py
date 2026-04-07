from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path
from typing import Any, Dict, List
from xml.sax.saxutils import escape as xml_escape


class ReportExporter:
    """Export structured report data to shareable files."""

    def __init__(self, output_dir: str = "./report_exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, report_data: Dict[str, Any], session_id: str, output_format: str) -> Dict[str, Any]:
        """Export a report in the requested format and return metadata."""
        fmt = (output_format or "html").lower()
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_stem = f"dataverse_report_{session_id}_{timestamp}"

        if fmt == "json":
            file_path = session_dir / f"{file_stem}.json"
            file_path.write_text(json.dumps(report_data, indent=2, default=str), encoding="utf-8")
            media_type = "application/json"
        elif fmt in {"md", "markdown"}:
            file_path = session_dir / f"{file_stem}.md"
            file_path.write_text(self._render_markdown(report_data), encoding="utf-8")
            media_type = "text/markdown"
        elif fmt == "html":
            file_path = session_dir / f"{file_stem}.html"
            file_path.write_text(self._render_html(report_data), encoding="utf-8")
            media_type = "text/html"
        elif fmt == "docx":
            file_path = session_dir / f"{file_stem}.docx"
            self._write_docx(report_data, file_path)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            raise ValueError(f"Unsupported report format: {output_format}")

        return {
            "format": fmt,
            "path": str(file_path),
            "filename": file_path.name,
            "media_type": media_type,
            "size_bytes": file_path.stat().st_size,
        }

    def _render_markdown(self, report_data: Dict[str, Any]) -> str:
        """Render report data as markdown."""
        overview = report_data.get("dataset_overview", {})
        findings = report_data.get("key_findings", [])
        recommendations = report_data.get("recommendations", [])
        tables = report_data.get("tables", [])
        narratives = report_data.get("narratives", [])
        filters = overview.get("active_filters", [])

        lines = [
            f"# {report_data.get('title', 'DataVerse Analysis Report')}",
            "",
            f"Generated: {report_data.get('generated_at', '')}",
            "",
            "## Executive Summary",
            report_data.get("executive_summary", "No executive summary available."),
            "",
            "## Dataset Overview",
            f"- Rows: {overview.get('rows', 0)}",
            f"- Columns: {overview.get('columns', 0)}",
            f"- Active filters: {len(filters)}",
            f"- Messages analyzed: {overview.get('message_count', 0)}",
            "",
            "## Recommendations",
        ]

        if recommendations:
            lines.extend([f"- {item}" for item in recommendations])
        else:
            lines.append("- No recommendations generated.")

        lines.extend(["", "## Key Findings"])
        if findings:
            for finding in findings:
                lines.append(
                    f"- `{finding.get('tool', 'unknown')}`: {finding.get('summary', 'No summary available.')}"
                )
        else:
            lines.append("- No findings captured.")

        if narratives:
            lines.extend(["", "## Narrative Highlights"])
            for narrative in narratives:
                lines.append(f"- {narrative}")

        if tables:
            lines.extend(["", "## Tables"])
            for table in tables:
                columns = table.get("columns", [])
                rows = table.get("data", [])
                title = table.get("title", "Table")
                lines.extend(["", f"### {title}"])
                if columns:
                    lines.append("| " + " | ".join(columns) + " |")
                    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
                    for row in rows[:10]:
                        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")

        return "\n".join(lines).strip() + "\n"

    def _render_html(self, report_data: Dict[str, Any]) -> str:
        """Render report data as a polished HTML document."""
        overview = report_data.get("dataset_overview", {})
        findings = report_data.get("key_findings", [])
        recommendations = report_data.get("recommendations", [])
        charts = report_data.get("visualizations", [])
        tables = report_data.get("tables", [])
        narratives = report_data.get("narratives", [])
        filters = overview.get("active_filters", [])

        def render_list(items: List[str], empty_text: str) -> str:
            if not items:
                return f"<p class='empty'>{html_escape(empty_text)}</p>"
            return "<ul>" + "".join(f"<li>{html_escape(str(item))}</li>" for item in items) + "</ul>"

        def render_findings() -> str:
            if not findings:
                return "<p class='empty'>No key findings were captured for this session.</p>"
            cards = []
            for finding in findings:
                cards.append(
                    "<article class='card'>"
                    f"<div class='eyebrow'>{html_escape(str(finding.get('tool', 'tool')))}</div>"
                    f"<h3>{html_escape(str(finding.get('purpose') or finding.get('tool', 'Analysis step')))}</h3>"
                    f"<p>{html_escape(str(finding.get('summary', 'No summary available.')))}</p>"
                    "</article>"
                )
            return "<div class='card-grid'>" + "".join(cards) + "</div>"

        def render_tables() -> str:
            if not tables:
                return "<p class='empty'>No tabular report sections available.</p>"
            chunks: List[str] = []
            for table in tables[:5]:
                title = html_escape(str(table.get("title", "Table")))
                columns = table.get("columns", [])
                rows = table.get("data", [])[:10]
                header = "".join(f"<th>{html_escape(str(col))}</th>" for col in columns)
                body_rows = []
                for row in rows:
                    body_rows.append(
                        "<tr>"
                        + "".join(f"<td>{html_escape(str(row.get(col, '')))}</td>" for col in columns)
                        + "</tr>"
                    )
                chunks.append(
                    "<section class='table-block'>"
                    f"<h3>{title}</h3>"
                    "<div class='table-wrap'><table><thead><tr>"
                    + header
                    + "</tr></thead><tbody>"
                    + "".join(body_rows)
                    + "</tbody></table></div></section>"
                )
            return "".join(chunks)

        chart_list = [
            f"{item.get('title', 'Chart')} ({item.get('type', 'chart')})" for item in charts
        ]
        column_names = overview.get("column_names", [])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html_escape(str(report_data.get('title', 'DataVerse Analysis Report')))}</title>
  <style>
    :root {{
      --ink: #10243f;
      --muted: #5f718b;
      --line: #d7e0ec;
      --panel: #ffffff;
      --soft: #eef5fb;
      --accent: #0c6b58;
      --accent-soft: #dff4ee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #dff4ee 0, rgba(223, 244, 238, 0) 28%),
        linear-gradient(180deg, #f7fbff 0%, #eef4fa 100%);
      line-height: 1.6;
    }}
    .shell {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 40px 20px 64px;
    }}
    .hero {{
      background: linear-gradient(135deg, #0d223d 0%, #144f68 55%, #0c6b58 100%);
      color: white;
      border-radius: 28px;
      padding: 32px;
      box-shadow: 0 25px 60px rgba(16, 36, 63, 0.18);
    }}
    .hero h1 {{ margin: 0 0 10px; font-size: 32px; }}
    .hero p {{ margin: 6px 0; color: rgba(255,255,255,0.88); }}
    .section {{
      margin-top: 24px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 12px 35px rgba(16, 36, 63, 0.06);
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 20px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }}
    .stat {{
      background: var(--soft);
      border-radius: 18px;
      padding: 16px;
    }}
    .stat .label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .stat .value {{
      display: block;
      margin-top: 8px;
      font-size: 24px;
      font-weight: 700;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fbfd 100%);
    }}
    .card h3 {{ margin: 8px 0 10px; font-size: 17px; }}
    .eyebrow {{
      color: var(--accent);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .pill-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .pill {{
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 999px;
      padding: 6px 12px;
      font-size: 13px;
      font-weight: 600;
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f5f8fb;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 11px;
    }}
    .empty {{
      color: var(--muted);
      margin: 0;
    }}
    .table-block + .table-block {{
      margin-top: 16px;
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>{html_escape(str(report_data.get('title', 'DataVerse Analysis Report')))}</h1>
      <p><strong>Session:</strong> {html_escape(str(report_data.get('session_id', 'unknown')))}</p>
      <p><strong>Generated:</strong> {html_escape(str(report_data.get('generated_at', '')))}</p>
      <p>{html_escape(str(report_data.get('executive_summary', 'No executive summary available.')))}</p>
    </section>

    <section class="section">
      <h2>Dataset Overview</h2>
      <div class="stats">
        <div class="stat"><span class="label">Rows</span><span class="value">{overview.get('rows', 0)}</span></div>
        <div class="stat"><span class="label">Columns</span><span class="value">{overview.get('columns', 0)}</span></div>
        <div class="stat"><span class="label">Filters</span><span class="value">{len(filters)}</span></div>
        <div class="stat"><span class="label">Messages</span><span class="value">{overview.get('message_count', 0)}</span></div>
      </div>
      <div style="margin-top: 18px;">
        <div class="eyebrow">Columns</div>
        <div class="pill-row">{''.join(f"<span class='pill'>{html_escape(str(col))}</span>" for col in column_names[:20]) or "<span class='pill'>No columns captured</span>"}</div>
      </div>
    </section>

    <section class="section">
      <h2>Recommendations</h2>
      {render_list(recommendations, "No recommendations generated.")}
    </section>

    <section class="section">
      <h2>Key Findings</h2>
      {render_findings()}
    </section>

    <section class="section">
      <h2>Visualizations</h2>
      {render_list(chart_list, "No visualization specs were captured in this session.")}
    </section>

    <section class="section">
      <h2>Narrative Highlights</h2>
      {render_list(narratives, "No narrative highlights were stored.")}
    </section>

    <section class="section">
      <h2>Tables</h2>
      {render_tables()}
    </section>
  </div>
</body>
</html>
"""

    def _write_docx(self, report_data: Dict[str, Any], file_path: Path) -> None:
        """Write a minimal DOCX file without requiring extra dependencies."""
        document_xml = self._build_docx_document(report_data)
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        core_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_escape(str(report_data.get('title', 'DataVerse Analysis Report')))}</dc:title>
  <dc:creator>DataVerse AI</dc:creator>
  <cp:lastModifiedBy>DataVerse AI</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>"""

        app_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>DataVerse AI</Application>
</Properties>"""

        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

        package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

        document_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>"""

        with zipfile.ZipFile(file_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", package_rels)
            archive.writestr("docProps/core.xml", core_xml)
            archive.writestr("docProps/app.xml", app_xml)
            archive.writestr("word/document.xml", document_xml)
            archive.writestr("word/_rels/document.xml.rels", document_rels)

    def _build_docx_document(self, report_data: Dict[str, Any]) -> str:
        """Build WordprocessingML document content."""
        overview = report_data.get("dataset_overview", {})
        findings = report_data.get("key_findings", [])
        recommendations = report_data.get("recommendations", [])
        tables = report_data.get("tables", [])
        narratives = report_data.get("narratives", [])
        charts = report_data.get("visualizations", [])
        filters = overview.get("active_filters", [])

        body_parts: List[str] = []
        body_parts.append(self._docx_paragraph(report_data.get("title", "DataVerse Analysis Report"), size=34, bold=True))
        body_parts.append(
            self._docx_paragraph(
                f"Generated: {report_data.get('generated_at', '')} | Session: {report_data.get('session_id', 'unknown')}",
                size=20,
            )
        )
        body_parts.append(self._docx_heading("Executive Summary"))
        body_parts.append(self._docx_paragraph(report_data.get("executive_summary", "No executive summary available.")))

        body_parts.append(self._docx_heading("Dataset Overview"))
        overview_lines = [
            f"Rows: {overview.get('rows', 0)}",
            f"Columns: {overview.get('columns', 0)}",
            f"Messages analyzed: {overview.get('message_count', 0)}",
            f"Active filters: {len(filters)}",
            "Column names: " + ", ".join(str(col) for col in overview.get("column_names", [])[:20]),
        ]
        for line in overview_lines:
            body_parts.append(self._docx_paragraph(line))

        body_parts.append(self._docx_heading("Recommendations"))
        if recommendations:
            for item in recommendations:
                body_parts.append(self._docx_paragraph(f"- {item}"))
        else:
            body_parts.append(self._docx_paragraph("No recommendations generated."))

        body_parts.append(self._docx_heading("Key Findings"))
        if findings:
            for finding in findings:
                heading = f"{finding.get('tool', 'tool')}: {finding.get('purpose') or finding.get('tool', 'Analysis step')}"
                body_parts.append(self._docx_paragraph(heading, bold=True))
                body_parts.append(self._docx_paragraph(finding.get("summary", "No summary available.")))
        else:
            body_parts.append(self._docx_paragraph("No findings captured."))

        body_parts.append(self._docx_heading("Narrative Highlights"))
        if narratives:
            for narrative in narratives:
                body_parts.append(self._docx_paragraph(f"- {narrative}"))
        else:
            body_parts.append(self._docx_paragraph("No narrative highlights were stored."))

        body_parts.append(self._docx_heading("Visualizations"))
        if charts:
            for chart in charts:
                body_parts.append(
                    self._docx_paragraph(
                        f"- {chart.get('title', 'Chart')} ({chart.get('type', 'chart')})"
                    )
                )
        else:
            body_parts.append(self._docx_paragraph("No visualization specs were captured in this session."))

        body_parts.append(self._docx_heading("Tables"))
        if tables:
            for table in tables[:3]:
                body_parts.append(self._docx_paragraph(table.get("title", "Table"), bold=True))
                body_parts.append(self._docx_table(table.get("columns", []), table.get("data", [])[:10]))
        else:
            body_parts.append(self._docx_paragraph("No tabular sections available."))

        body_parts.append(
            "<w:sectPr>"
            "<w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
            "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
            "</w:sectPr>"
        )

        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<w:document xmlns:wpc=\"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas\""
            " xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\""
            " xmlns:o=\"urn:schemas-microsoft-com:office:office\""
            " xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\""
            " xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\""
            " xmlns:v=\"urn:schemas-microsoft-com:vml\""
            " xmlns:wp14=\"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing\""
            " xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\""
            " xmlns:w10=\"urn:schemas-microsoft-com:office:word\""
            " xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\""
            " xmlns:w14=\"http://schemas.microsoft.com/office/word/2010/wordml\""
            " xmlns:wpg=\"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup\""
            " xmlns:wpi=\"http://schemas.microsoft.com/office/word/2010/wordprocessingInk\""
            " xmlns:wne=\"http://schemas.microsoft.com/office/2006/wordml\""
            " xmlns:wps=\"http://schemas.microsoft.com/office/word/2010/wordprocessingShape\""
            " mc:Ignorable=\"w14 wp14\">"
            "<w:body>"
            + "".join(body_parts)
            + "</w:body></w:document>"
        )

    def _docx_heading(self, text: str) -> str:
        return self._docx_paragraph(text, size=28, bold=True)

    def _docx_paragraph(self, text: str, size: int = 22, bold: bool = False) -> str:
        safe_text = xml_escape(str(text or ""))
        run_props = []
        if bold:
            run_props.append("<w:b/>")
        run_props.append(f"<w:sz w:val=\"{size}\"/>")
        run_props.append(f"<w:szCs w:val=\"{size}\"/>")
        return (
            "<w:p><w:r><w:rPr>"
            + "".join(run_props)
            + "</w:rPr><w:t xml:space=\"preserve\">"
            + safe_text
            + "</w:t></w:r></w:p>"
        )

    def _docx_table(self, columns: List[Any], rows: List[Dict[str, Any]]) -> str:
        if not columns:
            return self._docx_paragraph("No columns available for this table.")

        def cell(text: Any, bold: bool = False) -> str:
            props = "<w:rPr><w:b/></w:rPr>" if bold else ""
            return (
                "<w:tc><w:tcPr><w:tcW w:w=\"0\" w:type=\"auto\"/></w:tcPr>"
                "<w:p><w:r>"
                + props
                + "<w:t xml:space=\"preserve\">"
                + xml_escape(str(text))
                + "</w:t></w:r></w:p></w:tc>"
            )

        header_row = "<w:tr>" + "".join(cell(column, bold=True) for column in columns) + "</w:tr>"
        body_rows = []
        for row in rows:
            body_rows.append("<w:tr>" + "".join(cell(row.get(column, "")) for column in columns) + "</w:tr>")

        borders = (
            "<w:tblBorders>"
            "<w:top w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"auto\"/>"
            "<w:left w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"auto\"/>"
            "<w:bottom w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"auto\"/>"
            "<w:right w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"auto\"/>"
            "<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
            "<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"auto\"/>"
            "</w:tblBorders>"
        )

        return (
            "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>"
            + borders
            + "</w:tblPr>"
            + header_row
            + "".join(body_rows)
            + "</w:tbl>"
        )
