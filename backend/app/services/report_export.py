from collections import Counter
from io import BytesIO
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.repository import safe_repository_url

INK = colors.HexColor("#17362D")
ACCENT = colors.HexColor("#5D8B38")
LIGHT = colors.HexColor("#EEF3ED")
RED = colors.HexColor("#9B1C1C")
EXPECTED_TOOLS = ["gitleaks", "semgrep", "trivy-fs", "sonarqube", "unit-tests", "trivy-image"]
TOOL_LABELS = {"gitleaks": "GitLeaks", "semgrep": "Semgrep", "trivy-fs": "Trivy FS", "trivy-image": "Trivy Image", "sonarqube": "SonarQube", "unit-tests": "Unit Tests"}


def _pdf_text(value, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
    if limit and len(text) > limit:
        text = text[: max(0, limit - 1)].rstrip() + "..."
    return escape(text)


def _cell_paragraph(value, style, limit: int | None = None) -> Paragraph:
    return Paragraph(_pdf_text(value, limit), style)


def _risk_count_paragraph(value, style, limit: int | None = None) -> Paragraph:
    text = _pdf_text(value, limit)
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        count = 0
    if count > 0:
        return Paragraph(f'<font color="#9B1C1C"><b>{text}</b></font>', style)
    return Paragraph(text, style)


def _pdf_link_markup(url: str) -> str:
    href = escape(url, {'"': '&quot;', "'": '&apos;'})
    label = _pdf_text(url)
    return f'<font color="#16813F"><link href="{href}">{label}</link></font>'


def _pdf_repository_link(repository_url: str | None, style, label: str = "Repository") -> Paragraph:
    url = safe_repository_url(repository_url)
    value = _pdf_link_markup(url) if url.startswith(("http://", "https://")) else _pdf_text(url)
    return Paragraph(f"<b>{label}:</b> {value}", style)


def _pdf_metadata_block(project_name: str | None, repository_url: str | None, branch: str | None, uploaded_at, style) -> list:
    return [
        Paragraph(f"<b>Project:</b> {_pdf_text(project_name or 'Not available')}", style),
        _pdf_repository_link(repository_url, style),
        Paragraph(f"<b>Branch:</b> {_pdf_text(branch or 'Not available')}", style),
        Paragraph(f"<b>Uploaded:</b> {_pdf_text(uploaded_at or 'Not available')}", style),
    ]


def _add_docx_hyperlink(paragraph, url: str, text: str):
    relationship_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "16813F")
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.append(color)
    properties.append(underline)
    run.append(properties)
    text_element = OxmlElement("w:t")
    text_element.text = text
    run.append(text_element)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _add_repository_docx_paragraph(document, repository_url: str | None, label: str = "Repository") -> None:
    url = safe_repository_url(repository_url)
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.add_run(f"{label}: ").bold = True
    if url.startswith(("http://", "https://")):
        _add_docx_hyperlink(paragraph, url, url)
    else:
        paragraph.add_run(url)


def _style_docx_risk_count(cell, value) -> None:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        count = 0
    if count <= 0 or not cell.paragraphs or not cell.paragraphs[0].runs:
        return
    run = cell.paragraphs[0].runs[0]
    run.bold = True
    run.font.color.rgb = RGBColor(155, 28, 28)


def _add_docx_metadata_block(document, project_name: str | None, repository_url: str | None, branch: str | None, uploaded_at) -> None:
    for label, value in [("Project", project_name or "Not available")]:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(5)
        paragraph.add_run(f"{label}: ").bold = True
        paragraph.add_run(str(value))
    _add_repository_docx_paragraph(document, repository_url)
    for label, value in [("Branch", branch or "Not available"), ("Uploaded", uploaded_at or "Not available")]:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(5)
        paragraph.add_run(f"{label}: ").bold = True
        paragraph.add_run(str(value))


def _footer_label(label: str):
    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#66756F"))
        canvas.drawString(0.7 * inch, 0.45 * inch, f"SecureGate AI - {label}")
        canvas.drawCentredString(4.25 * inch, 0.45 * inch, "Confidential security assessment")
        canvas.drawRightString(7.8 * inch, 0.45 * inch, f"Page {document.page}")
        canvas.restoreState()
    return footer


def _footer(canvas, document) -> None:
    _footer_label("Master Security Report")(canvas, document)


def _tool_summary_rows(report: dict) -> list[dict]:
    summary = report.get("tool_findings_summary", {}) or {}
    statuses = report.get("tool_status_summary", {}) or {}
    rows = []
    for tool in EXPECTED_TOOLS:
        values = summary.get(tool, {}) or {}
        status = values.get("status") or statuses.get(tool)
        if not status:
            status = "UPLOADED" if tool in summary else "NOT_UPLOADED"
        rows.append(
            {
                "tool": TOOL_LABELS.get(tool, tool),
                "status": str(status).replace("_", " "),
                "critical": values.get("CRITICAL", 0),
                "high": values.get("HIGH", 0),
                "medium": values.get("MEDIUM", 0),
                "low": values.get("LOW", 0),
            }
        )
    return rows


def _plain_language_summary(report: dict) -> list[str]:
    summary = report.get("vulnerability_summary", {}) or {}
    decision = report.get("deployment_decision", {}) or {}
    decision_value = decision.get("decision", "PENDING")
    score = (report.get("security_score", {}) or {}).get("score", "Pending")
    lines = [f"Overall result: deployment is {decision_value} with a security score of {score}/100."]

    blockers = decision.get("reasons") or []
    if blockers:
        lines.append("Why it needs attention: " + " ".join(str(item) for item in blockers))
    elif decision_value == "APPROVED":
        lines.append("No blocking issue was found. Keep monitoring dependencies and code quality on every push.")

    issue_counts = [
        ("critical", int(summary.get("CRITICAL", 0) or 0)),
        ("high", int(summary.get("HIGH", 0) or 0)),
        ("medium", int(summary.get("MEDIUM", 0) or 0)),
        ("low", int(summary.get("LOW", 0) or 0)),
    ]
    visible_counts = [f"{count} {name}" for name, count in issue_counts if count]
    if visible_counts:
        lines.append("Issue count in simple terms: " + ", ".join(visible_counts) + " findings were reported.")

    secrets = int(summary.get("secrets", 0) or 0)
    if secrets:
        lines.append("Secrets were detected. Remove them from the repository, rotate the exposed values, and store replacements in GitHub Secrets or a vault.")

    sonar_gate = str(summary.get("sonarqube_quality_gate", "UNKNOWN"))
    if sonar_gate not in {"OK", "UNKNOWN"}:
        lines.append(f"SonarQube quality gate is {sonar_gate}. Review SonarCloud issues and fix code quality or reliability problems before deployment.")

    for finding in report.get("top_findings", [])[:6]:
        severity = str(finding.get("severity") or "Finding").title()
        tool = TOOL_LABELS.get(str(finding.get("tool") or "").lower(), finding.get("tool") or "Security tool")
        target = finding.get("file") or "the affected file or image"
        title = finding.get("title") or finding.get("description") or "Security issue detected"
        lines.append(f"Fix in {target}: {severity} issue from {tool} - {title}")

    if len(lines) == 1:
        lines.append("No specific issue details were available in the selected findings. Review the tool reports for deeper evidence if needed.")
    return lines


def generate_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="SecureGate AI Deployment Approval",
        author="SecureGate AI",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=28, textColor=INK, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=INK, spaceBefore=14, spaceAfter=7))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#50615B"), spaceBefore=0, spaceAfter=0))
    styles.add(ParagraphStyle(name="ReportMeta", parent=styles["BodyText"], fontSize=9.2, leading=14, textColor=colors.HexColor("#10231D"), spaceBefore=0, spaceAfter=6))
    styles.add(ParagraphStyle(name="Emphasis", parent=styles["BodyText"], fontSize=9, leading=12.5, textColor=INK, leftIndent=8, spaceBefore=2, spaceAfter=4))
    styles.add(ParagraphStyle(name="ToolCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=colors.black, wordWrap="CJK", spaceBefore=0, spaceAfter=0))
    styles.add(ParagraphStyle(name="ToolHeaderCell", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=colors.white, wordWrap="CJK", spaceBefore=0, spaceAfter=0))
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 12.5
    styles["BodyText"].spaceAfter = 4

    score = report["security_score"]["score"]
    decision = report["deployment_decision"]["decision"]
    executive_summary = report["executive_summary"]["summary"]
    summary = report["vulnerability_summary"]
    metadata = report["report_metadata"]
    uploaded_at = metadata.get("uploaded_at") or metadata.get("received_at") or metadata.get("generated_at")
    story = [
        Paragraph("SECUREGATE AI | COMPANY LOGO", styles["Small"]),
        Spacer(1, 0.04 * inch),
        Paragraph("Master Security Report", styles["ReportTitle"]),
        Paragraph(f"Scan ID: {report['executive_summary']['scan_id']}", styles["Small"]),
        Spacer(1, 0.12 * inch),
        *_pdf_metadata_block(metadata.get("project_name"), metadata.get("repository_url"), metadata.get("branch"), uploaded_at, styles["ReportMeta"]),
        Spacer(1, 0.16 * inch),
        Table(
            [["SECURITY SCORE", "DEPLOYMENT DECISION"], [f"{score}/100", decision]],
            colWidths=[3.25 * inch, 3.25 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (-1, 1), 18),
                ("TEXTCOLOR", (1, 1), (1, 1), ACCENT if decision == "APPROVED" else RED),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#C9D4CE")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCE3DF")),
                ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        ),
        Paragraph("1. EXECUTIVE SUMMARY", styles["Section"]),
        Paragraph(f"<b>DECISION CONTEXT:</b> {executive_summary}", styles["BodyText"]),
        Spacer(1, 0.04 * inch),
        Paragraph("2. VULNERABILITY SUMMARY", styles["Section"]),
        Table(
            [["Critical", "High", "Medium", "Secrets", "Sonar Gate"], [_risk_count_paragraph(summary.get("CRITICAL", 0), styles["BodyText"]), _risk_count_paragraph(summary.get("HIGH", 0), styles["BodyText"]), _risk_count_paragraph(summary.get("MEDIUM", 0), styles["BodyText"]), _risk_count_paragraph(summary["secrets"], styles["BodyText"]), summary["sonarqube_quality_gate"]]],
            colWidths=[1.05 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch, 2.3 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8D3")),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]),
        ),
        Spacer(1, 0.04 * inch),
        Paragraph("3. DEPLOYMENT DECISION", styles["Section"]),
    ]
    reasons = report["deployment_decision"]["reasons"] or ["All deployment approval conditions passed."]
    for reason in reasons:
        story.append(Paragraph(f"<b>GATE RESULT:</b> {reason}", styles["Emphasis"]))

    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("4. TOOL FINDINGS SUMMARY", styles["Section"]))
    tool_rows = [["Tool", "Status", "Critical", "High", "Medium", "Low"]]
    for row in _tool_summary_rows(report):
        tool_rows.append([row["tool"], row["status"], _risk_count_paragraph(row["critical"], styles["BodyText"]), _risk_count_paragraph(row["high"], styles["BodyText"]), _risk_count_paragraph(row["medium"], styles["BodyText"]), _risk_count_paragraph(row["low"], styles["BodyText"])])
    story.append(Table(tool_rows, colWidths=[1.45 * inch, 1.55 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8D3")),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("FONTSIZE", (0, 0), (-1, -1), 8),
    ])))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("5. BLOCKING AND TOP FINDINGS", styles["Section"]))
    top_finding_rows = [[
        _cell_paragraph("Tool", styles["ToolHeaderCell"]),
        _cell_paragraph("Severity", styles["ToolHeaderCell"]),
        _cell_paragraph("File/Target", styles["ToolHeaderCell"]),
        _cell_paragraph("Finding", styles["ToolHeaderCell"]),
    ]]
    for finding in report.get("top_findings", [])[:8]:
        top_finding_rows.append([
            _cell_paragraph(finding.get("tool"), styles["ToolCell"], 55),
            _cell_paragraph(finding.get("severity"), styles["ToolCell"], 35),
            _cell_paragraph(finding.get("file") or "N/A", styles["ToolCell"], 130),
            _cell_paragraph(finding.get("title") or "No title provided", styles["ToolCell"], 360),
        ])
    if len(top_finding_rows) == 1:
        top_finding_rows.append([_cell_paragraph("-", styles["ToolCell"]), _cell_paragraph("-", styles["ToolCell"]), _cell_paragraph("-", styles["ToolCell"]), _cell_paragraph("No blocking findings were selected for this report.", styles["ToolCell"])])
    story.append(LongTable(top_finding_rows, colWidths=[0.85 * inch, 0.75 * inch, 1.6 * inch, 3.3 * inch], repeatRows=1, splitByRow=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8D3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("6. SUMMARY", styles["Section"]))
    for item in _plain_language_summary(report):
        story.append(Paragraph(f"<b>WHAT TO FIX:</b> {item}", styles["Emphasis"]))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("7. PRIORITIZED RECOMMENDATIONS", styles["Section"]))
    for item in report["recommendations"][:8]:
        actions = " ".join(item["actions"])
        story.append(Paragraph(f"<b>PRIORITY P{item['priority']} - {item['title'].upper()}:</b> {actions}", styles["Emphasis"]))
    story.append(Spacer(1, 0.02 * inch))
    story.append(Paragraph("8. REPORT METADATA", styles["Section"]))
    story.append(Paragraph(
        f"<b>PROJECT:</b> {metadata['project_name']} | <b>BRANCH:</b> {metadata['branch']} | <b>COMMIT:</b> {metadata['commit_sha']}<br/><b>GENERATED:</b> {metadata['generated_at']} | <b>REPORT VERSION:</b> {metadata['report_version']}",
        styles["Small"],
    ))
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _set_cell_fill(cell, fill: str) -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shading)


def generate_docx(report: dict) -> bytes:
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Inches(1)
    section.header_distance = section.footer_distance = Inches(0.492)

    normal = document.styles["Normal"]
    normal.font.name, normal.font.size, normal.font.color.rgb = "Calibri", Pt(10.5), RGBColor(25, 39, 34)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12
    for style_name, size, color in [("Heading 1", 15, "2E7453"), ("Heading 2", 13, "2E7453"), ("Heading 3", 12, "214E3E")]:
        style = document.styles[style_name]
        style.font.name, style.font.size, style.font.bold = "Calibri", Pt(size), True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(16)
        style.paragraph_format.space_after = Pt(8)
        style.paragraph_format.keep_with_next = True

    header = section.header.paragraphs[0]
    header.text = "SecureGate AI | Master Security Report"
    header.runs[0].font.size = Pt(8)
    header.runs[0].font.color.rgb = RGBColor(95, 112, 105)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("Confidential security assessment")
    footer.runs[0].font.size = Pt(8)

    logo = document.add_paragraph()
    logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo_run = logo.add_run("SECUREGATE AI | COMPANY LOGO")
    logo_run.bold, logo_run.font.size, logo_run.font.color.rgb = True, Pt(9), RGBColor(95, 112, 105)
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(4)
    title_run = title.add_run("Master Security Report")
    title_run.bold, title_run.font.size, title_run.font.color.rgb = True, Pt(22), RGBColor(23, 54, 45)
    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(f"SCAN ID: {report['executive_summary']['scan_id']}").bold = True
    document.add_paragraph()
    metadata = report["report_metadata"]
    uploaded_at = metadata.get("uploaded_at") or metadata.get("received_at") or metadata.get("generated_at")
    _add_docx_metadata_block(document, metadata.get("project_name"), metadata.get("repository_url"), metadata.get("branch"), uploaded_at)
    document.add_paragraph()

    score_table = document.add_table(rows=2, cols=2)
    score_table.autofit = False
    for row in score_table.rows:
        row.cells[0].width = row.cells[1].width = Inches(3.25)
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    score_table.cell(0, 0).text, score_table.cell(0, 1).text = "SECURITY SCORE", "DEPLOYMENT DECISION"
    score_table.cell(1, 0).text = f"{report['security_score']['score']}/100"
    score_table.cell(1, 1).text = report["deployment_decision"]["decision"]
    for cell in score_table.rows[0].cells:
        _set_cell_fill(cell, "EEF3ED")
        cell.paragraphs[0].runs[0].bold = True
    for cell in score_table.rows[1].cells:
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(17)

    document.add_heading("1 EXECUTIVE SUMMARY", level=1)
    paragraph = document.add_paragraph()
    paragraph.add_run("DECISION CONTEXT: ").bold = True
    paragraph.add_run(report["executive_summary"]["summary"])
    document.add_heading("2 SECURITY SCORE AND DEPLOYMENT DECISION", level=1)
    reasons = report["deployment_decision"]["reasons"] or ["All deployment approval conditions passed."]
    decision_paragraph = document.add_paragraph()
    decision_paragraph.add_run("GATE RESULT: ").bold = True
    decision_paragraph.add_run(" ".join(reasons))
    document.add_heading("3 VULNERABILITY SUMMARY", level=1)
    summary = report["vulnerability_summary"]
    summary_paragraph = document.add_paragraph()
    for label, value in [("CRITICAL", summary.get("CRITICAL", 0)), ("HIGH", summary.get("HIGH", 0)), ("MEDIUM", summary.get("MEDIUM", 0)), ("SECRETS", summary["secrets"]), ("SONARQUBE GATE", summary["sonarqube_quality_gate"])]:
        run = summary_paragraph.add_run(f"{label}: ")
        run.bold = True
        value_run = summary_paragraph.add_run(f"{value}   ")
        if label in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "SECRETS"}:
            try:
                count = int(value or 0)
            except (TypeError, ValueError):
                count = 0
            if count > 0:
                value_run.bold = True
                value_run.font.color.rgb = RGBColor(155, 28, 28)
    document.add_heading("4 TOOL FINDINGS SUMMARY", level=1)
    table = document.add_table(rows=1, cols=6)
    table.autofit = False
    widths = [Inches(1.45), Inches(1.55), Inches(0.85), Inches(0.85), Inches(0.85), Inches(0.85)]
    for index, label in enumerate(["Tool", "Status", "Critical", "High", "Medium", "Low"]):
        table.cell(0, index).text = label
        table.cell(0, index).width = widths[index]
        _set_cell_fill(table.cell(0, index), "17362D")
        table.cell(0, index).paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        table.cell(0, index).paragraphs[0].runs[0].bold = True
    for row in _tool_summary_rows(report):
        cells = table.add_row().cells
        values = [row["tool"], row["status"], row["critical"], row["high"], row["medium"], row["low"]]
        for index, value in enumerate(values):
            cells[index].text, cells[index].width = str(value), widths[index]
            cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cells[index].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if index in {0, 1} else WD_ALIGN_PARAGRAPH.CENTER
            if index >= 2:
                _style_docx_risk_count(cells[index], value)
    document.add_paragraph()
    document.add_heading("5 BLOCKING AND TOP FINDINGS", level=1)
    finding_table = document.add_table(rows=1, cols=4)
    finding_table.autofit = False
    finding_widths = [Inches(0.85), Inches(0.75), Inches(1.7), Inches(3.2)]
    for index, label in enumerate(["Tool", "Severity", "File/Target", "Finding"]):
        finding_table.cell(0, index).text = label
        finding_table.cell(0, index).width = finding_widths[index]
        _set_cell_fill(finding_table.cell(0, index), "17362D")
        finding_table.cell(0, index).paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        finding_table.cell(0, index).paragraphs[0].runs[0].bold = True
    selected_findings = report.get("top_findings", [])[:8] or [{"tool": "-", "severity": "-", "file": "-", "title": "No blocking findings were selected for this report."}]
    for finding in selected_findings:
        cells = finding_table.add_row().cells
        values = [finding.get("tool", "-"), finding.get("severity", "-"), finding.get("file") or "N/A", finding.get("title") or "No title provided"]
        for index, value in enumerate(values):
            cells[index].text = str(value)
            cells[index].width = finding_widths[index]
            cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            for paragraph in cells[index].paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.size = Pt(8)
    document.add_paragraph()
    document.add_heading("6 SUMMARY", level=1)
    for item in _plain_language_summary(report):
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.add_run("WHAT TO FIX: ").bold = True
        paragraph.add_run(item)
    document.add_paragraph()
    document.add_heading("7 PRIORITIZED RECOMMENDATIONS", level=1)
    for item in report["recommendations"][:8]:
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.add_run(f"PRIORITY P{item['priority']} - {item['title'].upper()}: ").bold = True
        paragraph.add_run(" ".join(item["actions"]))
    document.add_paragraph()
    document.add_heading("8 REPORT METADATA", level=1)
    document.add_paragraph(
        f"PROJECT: {metadata['project_name']} | BRANCH: {metadata['branch']} | COMMIT: {metadata['commit_sha']}"
    )
    document.add_paragraph(
        f"GENERATED: {metadata['generated_at']} | VERSION: {metadata['report_version']}"
    )
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def generate_tool_report_pdf(scan, tool_report, findings: list) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{tool_report.tool_name} Report",
        author="SecureGate AI",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ToolTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="ToolMeta", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=14, textColor=colors.HexColor("#10231D"), spaceBefore=0, spaceAfter=6))
    styles.add(ParagraphStyle(name="ToolSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=INK, spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="ToolCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=colors.black, wordWrap="CJK", spaceBefore=0, spaceAfter=0))
    styles.add(ParagraphStyle(name="ToolHeaderCell", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=colors.white, wordWrap="CJK", spaceBefore=0, spaceAfter=0))
    styles["BodyText"].fontSize = 8.5
    styles["BodyText"].leading = 11
    counts = Counter(item.severity.upper() for item in findings)
    story = [
        Paragraph("SECUREGATE AI | COMPANY LOGO", styles["BodyText"]),
        Spacer(1, 0.04 * inch),
        Paragraph("SecureGate AI Tool Report", styles["ToolTitle"]),
        Paragraph(f"Tool: <b>{_pdf_text(tool_report.tool_name)}</b>", styles["ToolMeta"]),
        Paragraph(f"Scan ID: <b>{_pdf_text(scan.scan_id)}</b>", styles["ToolMeta"]),
        *_pdf_metadata_block(scan.project_name, scan.repository_url, scan.branch, tool_report.uploaded_at, styles["ToolMeta"]),
        Spacer(1, 0.14 * inch),
        Paragraph("Severity Summary", styles["ToolSection"]),
        Table([["Critical", "High", "Medium", "Low", "Total"], [_risk_count_paragraph(counts.get("CRITICAL", 0), styles["ToolCell"]), _risk_count_paragraph(counts.get("HIGH", 0), styles["ToolCell"]), _risk_count_paragraph(counts.get("MEDIUM", 0), styles["ToolCell"]), _risk_count_paragraph(counts.get("LOW", 0), styles["ToolCell"]), _risk_count_paragraph(len(findings), styles["ToolCell"])]], colWidths=[1.1 * inch] * 5, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8D3")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])),
        Paragraph("Top Findings", styles["ToolSection"]),
    ]
    rows = [[
        _cell_paragraph("Severity", styles["ToolHeaderCell"]),
        _cell_paragraph("File/Target", styles["ToolHeaderCell"]),
        _cell_paragraph("Finding", styles["ToolHeaderCell"]),
    ]]
    for item in findings[:30]:
        detail = item.title or item.description or "No finding title provided."
        rows.append([
            _cell_paragraph(item.severity, styles["ToolCell"], 40),
            _cell_paragraph(item.file or "N/A", styles["ToolCell"], 180),
            _cell_paragraph(detail, styles["ToolCell"], 520),
        ])
    if len(rows) == 1:
        rows.append([
            _cell_paragraph("-", styles["ToolCell"]),
            _cell_paragraph("-", styles["ToolCell"]),
            _cell_paragraph("No normalized findings for this report.", styles["ToolCell"]),
        ])
    story.append(LongTable(rows, colWidths=[0.75 * inch, 1.85 * inch, 3.9 * inch], repeatRows=1, splitByRow=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8D3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])))
    document.build(story, onFirstPage=_footer_label("Tool Security Report"), onLaterPages=_footer_label("Tool Security Report"))
    return buffer.getvalue()
