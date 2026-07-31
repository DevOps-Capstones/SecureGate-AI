from io import BytesIO
import os
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


INK = colors.HexColor("#17362D")
ACCENT = colors.HexColor("#16813F")
LIGHT = colors.HexColor("#EEF7E8")
RED = colors.HexColor("#9B1C1C")


def _report_symbol_font() -> str:
    candidates = [
        "/System/Library/Fonts/Apple Symbols.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                if "SecureGateSymbols" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("SecureGateSymbols", font_path))
                return "SecureGateSymbols"
            except Exception:
                continue
    return "Helvetica"


def clean(value) -> str:
    return escape(" ".join(str(value or "Not available").replace("\n", " ").split()))


def risk_count_markup(value) -> str:
    text = clean(value)
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        count = 0
    if count > 0:
        return f'<font color="#9B1C1C"><b>{text}</b></font>'
    return text


def link_markup(url: str) -> str:
    safe = escape(url, {'"': '&quot;', "'": '&apos;'})
    return f'<font color="#16813F"><link href="{safe}">{clean(url)}</link></font>'


def footer(label: str):
    def draw(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#66756F"))
        canvas.drawString(0.7 * inch, 0.45 * inch, f"SecureGate AI - {label}")
        canvas.drawCentredString(4.25 * inch, 0.45 * inch, "AI-assisted security guidance. Validate before production use.")
        canvas.drawRightString(7.8 * inch, 0.45 * inch, f"Page {document.page}")
        canvas.restoreState()
    return draw


def metadata_story(payload: dict, styles) -> list:
    repo = payload.get("repository_url") or "Not available"
    repo_value = link_markup(repo) if str(repo).startswith(("http://", "https://")) else clean(repo)
    return [
        Paragraph(f"<b>Project:</b> {clean(payload.get('project_name'))}", styles["Meta"]),
        Paragraph(f"<b>Repository:</b> {repo_value}", styles["Meta"]),
        Paragraph(f"<b>Branch:</b> {clean(payload.get('branch'))}", styles["Meta"]),
        Paragraph(f"<b>Uploaded:</b> {clean(payload.get('generated_at'))}", styles["Meta"]),
    ]


def strip_markdown_markers(value: str) -> str:
    text = str(value or "Not available").strip()
    text = re.sub(r"^\s*[-•*]+\s*", "", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text)
    text = text.replace("**", "").replace("__", "")
    return " ".join(text.split())


def split_ai_points(value, limit: int = 8) -> list[str]:
    raw = str(value or "Not available").replace("\r", "").strip()
    if not raw:
        return ["Not available"]
    lines = [strip_markdown_markers(line) for line in raw.split("\n") if strip_markdown_markers(line)]
    if len(lines) <= 1:
        lines = [strip_markdown_markers(part) for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", raw) if strip_markdown_markers(part)]
    return lines[:limit] or [strip_markdown_markers(raw)]


def bold_prefix(value: str) -> str:
    text = strip_markdown_markers(value)
    if ":" not in text:
        return clean(text)
    prefix, rest = text.split(":", 1)
    if len(prefix) <= 90:
        return f"<b>{clean(prefix.upper())}:</b> {clean(rest)}"
    return clean(text)


def executive_summary_markup(payload: dict) -> str:
    text = clean(payload.get("executive_summary"))
    project = str(payload.get("project_name") or "").strip()
    if project:
        text = re.sub(re.escape(clean(project)), f"<b>{clean(project)}</b>", text, count=1)
    decision = str(payload.get("deployment_decision") or "").strip().upper()
    if decision:
        color = "#9B1C1C" if decision == "REJECTED" else "#16813F" if decision == "APPROVED" else "#17362D"
        text = re.sub(rf"\b{re.escape(decision)}\b", f'<font color="{color}"><b>{decision}</b></font>', text, count=1)
    return text


def highlight_final_text(value: str) -> str:
    text = clean(value)
    replacements = {
        "approved": "<b>APPROVED</b>",
        "rejected": "<b>REJECTED</b>",
        "critical": "<b>CRITICAL</b>",
        "high": "<b>HIGH</b>",
        "medium": "<b>MEDIUM</b>",
        "low": "<b>LOW</b>",
        "fix": "<b>FIX</b>",
        "rerun": "<b>RERUN</b>",
        "re-run": "<b>RE-RUN</b>",
    }
    for word, marked in replacements.items():
        text = re.sub(rf"\b{re.escape(word)}\b", marked, text, flags=re.IGNORECASE)
    return text


def generate_ai_summary_pdf(payload: dict) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.7 * inch, leftMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch, title="SecureGate AI Summary Report")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Title2", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=INK, alignment=TA_CENTER, spaceAfter=14))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=INK, spaceBefore=16, spaceAfter=8))
    styles.add(ParagraphStyle(name="Meta", parent=styles["BodyText"], fontSize=9.5, leading=15, textColor=colors.HexColor("#10231D"), spaceAfter=6))
    styles.add(ParagraphStyle(name="AnalysisPoint", parent=styles["BodyText"], fontSize=9.2, leading=14, leftIndent=12, firstLineIndent=-8, spaceAfter=7, textColor=colors.HexColor("#10231D")))
    styles["BodyText"].fontSize = 9.5
    styles["BodyText"].leading = 13
    story = [Paragraph("SecureGate AI | AI Security Summary", styles["Title2"]), *metadata_story(payload, styles), Spacer(1, 0.12 * inch)]
    story.append(Table([["Security Score", "Decision", "AI Readiness", "Risk"], [f"{payload.get('security_score', 'N/A')}/100", payload.get("deployment_decision", "N/A"), payload.get("ai_readiness", "N/A"), payload.get("overall_risk", "N/A")]], colWidths=[1.45 * inch, 1.45 * inch, 2.0 * inch, 1.45 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, 0), INK), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8D3")), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)])))
    story += [Paragraph("Executive Summary", styles["Section"]), Paragraph(executive_summary_markup(payload), styles["BodyText"]), Paragraph("AI Analysis", styles["Section"])]
    for point in split_ai_points(payload.get("ai_text"), limit=7):
        story.append(Paragraph(f"• {bold_prefix(point)}", styles["AnalysisPoint"]))
    story.append(Paragraph("Top Recommendations", styles["Section"]))
    for item in payload.get("top_recommendations", []):
        story.append(Paragraph(f"• {bold_prefix(item)}", styles["AnalysisPoint"]))
    story += [Paragraph("Estimated Fix Time", styles["Section"]), Paragraph(clean(payload.get("estimated_fix_time")), styles["BodyText"])]
    document.build(story, onFirstPage=footer("AI Summary Report"), onLaterPages=footer("AI Summary Report"))
    return buffer.getvalue()


def generate_remediation_pdf(payload: dict) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.58 * inch,
        leftMargin=0.58 * inch,
        topMargin=0.78 * inch,
        bottomMargin=0.7 * inch,
        title="Vulnerabilities Evaluation Report - Remediation Plan by SecureGate AI",
    )
    styles = getSampleStyleSheet()
    symbol_font = _report_symbol_font()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=31, textColor=INK, alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name="Subtitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=12.5, leading=17, textColor=colors.HexColor("#60746D"), alignment=TA_CENTER, spaceAfter=18))
    styles.add(ParagraphStyle(name="CenteredSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13.2, leading=17, textColor=INK, alignment=TA_CENTER, spaceBefore=12, spaceAfter=10))
    styles.add(ParagraphStyle(name="CenterBody", parent=styles["BodyText"], fontSize=9.8, leading=15, textColor=colors.HexColor("#10231D"), alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13.2, leading=17, textColor=INK, spaceBefore=12, spaceAfter=8))
    styles.add(ParagraphStyle(name="ToolSection", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11.2, leading=15, textColor=INK, spaceBefore=9, spaceAfter=6))
    styles.add(ParagraphStyle(name="TocItem", parent=styles["BodyText"], fontSize=9.7, leading=16, textColor=colors.HexColor("#10231D"), spaceAfter=7))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=9, leading=12.8, textColor=colors.HexColor("#10231D"), spaceAfter=5))
    styles.add(ParagraphStyle(name="ReportBullet", parent=styles["Body"], leftIndent=14, firstLineIndent=-10, spaceAfter=4))
    styles.add(ParagraphStyle(name="Checklist", parent=styles["Body"], leftIndent=16, firstLineIndent=-12, spaceAfter=4))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=8.1, leading=10.8, wordWrap="CJK"))
    styles.add(ParagraphStyle(name="HeaderCell", parent=styles["Cell"], fontName="Helvetica-Bold", textColor=colors.white))
    body = styles["Body"]
    bullet = styles["ReportBullet"]
    checklist_style = styles["Checklist"]
    cell = styles["Cell"]
    header_cell = styles["HeaderCell"]

    counts = payload.get("finding_counts", {}) or {}
    details = payload.get("detailed_remediation", []) or []
    total_count = int(payload.get("total_findings") or sum(int(counts.get(key, 0) or 0) for key in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]))
    repo = payload.get("repository_url") or "Not available"
    generated_raw = str(payload.get("generated_at") or "Not available")
    generated_date = generated_raw[:10] if re.match(r"\d{4}-\d{2}-\d{2}", generated_raw) else generated_raw
    scan_id = payload.get("scan_id") or "Not available"
    public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000").rstrip("/")
    scan_url = f"{public_backend_url}/api/v1/scans/{scan_id}" if scan_id != "Not available" else ""
    escaped_scan_url = escape(scan_url, {'"': '&quot;', "'": '&apos;'}) if scan_url else ""
    scan_link = f'<font color="#16813F"><link href="{escaped_scan_url}">{clean(scan_id)}</link></font>' if scan_url else clean(scan_id)
    image_items = [item for item in details if str(item.get("source_tool") or "").lower() == "trivy-image"]
    image_count = 1 if image_items else 0
    repo_count = 1 if repo != "Not available" else 0

    def draw_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DCE6DF"))
        canvas.setLineWidth(0.6)
        canvas.line(0.58 * inch, 10.35 * inch, 7.92 * inch, 10.35 * inch)
        canvas.setFont("Helvetica-Bold", 8.2)
        canvas.setFillColor(INK)
        canvas.drawString(0.58 * inch, 10.48 * inch, "SecureGate AI | Vulnerability Remediation Plan")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(RED)
        canvas.drawRightString(7.92 * inch, 10.48 * inch, "RESTRICTED / INTERNAL SECURITY ONLY")
        canvas.setStrokeColor(colors.HexColor("#DCE6DF"))
        canvas.line(0.58 * inch, 0.62 * inch, 7.92 * inch, 0.62 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#66756F"))
        canvas.drawString(0.58 * inch, 0.42 * inch, "SecureGate AI Security Operations Team")
        canvas.drawCentredString(4.25 * inch, 0.42 * inch, "Remediation Plan by SecureGate AI")
        canvas.drawRightString(7.92 * inch, 0.42 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def table(rows, widths):
        return Table(rows, colWidths=widths, repeatRows=1, style=TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFD8D3")),
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

    def md(text: str, style=body):
        return Paragraph(text, style)

    def section_break():
        return [
            Spacer(1, 0.16 * inch),
            Table([[""]], colWidths=[6.75 * inch], rowHeights=[0.01 * inch], style=TableStyle([
                ("LINEABOVE", (0, 0), (-1, -1), 0.55, colors.HexColor("#DCE6DF")),
            ])),
            Spacer(1, 0.16 * inch),
        ]

    def checkbox(text: str):
        return Table(
            [["", Paragraph(clean(text), checklist_style)]],
            colWidths=[0.18 * inch, 6.25 * inch],
            style=TableStyle([
                ("BOX", (0, 0), (0, 0), 0.75, INK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]),
        )

    def section(text: str, anchor: str | None = None):
        prefix = f'<a name="{anchor}"/>' if anchor else ""
        return Paragraph(prefix + clean(text), styles["Section"])

    def toc(number: int, text: str, anchor: str):
        return Paragraph(f'<link href="#{anchor}"><font color="#16813F"><b>{number}. {clean(text)}</b></font></link>', styles["TocItem"])

    def items_for(tool: str, severities: set[str] | None = None):
        filtered = [item for item in details if str(item.get("source_tool") or "").lower() == tool]
        if severities:
            filtered = [item for item in filtered if str(item.get("severity") or "").upper() in severities]
        return filtered

    def assigned_team(item: dict, default: str = "Application Security Team") -> str:
        tool = str(item.get("source_tool") or "").lower()
        if tool == "gitleaks":
            return "Security Operations Team"
        if tool == "trivy-image":
            return "DevOps / Infrastructure Team"
        if tool == "trivy-fs":
            return "Product Engineering Team"
        if tool == "sonarqube":
            return "Application Quality Team"
        return default

    def first_cve(text: str) -> str:
        match = re.search(r"CVE-\d{4}-\d{4,}", str(text or ""), re.IGNORECASE)
        return match.group(0).upper() if match else "CVE details available in the uploaded tool report"

    def package_name(item: dict) -> str:
        text = str(item.get("issue_name") or item.get("issue") or "Package finding")
        return clean(text.split(":", 1)[0][:80])

    def fix_version(item: dict) -> str:
        return clean(item.get("recommended_version") or "See fixed version in Trivy report")

    def one_sentence_risk() -> str:
        if int(counts.get("secrets", 0) or 0):
            return "Exposed credentials can allow unauthorized access and must be rotated immediately."
        if int(counts.get("CRITICAL", 0) or 0):
            return "Critical vulnerabilities can create immediate production compromise risk."
        if int(counts.get("HIGH", 0) or 0):
            return "High-risk findings can weaken the application and must be prioritized before release."
        if int(counts.get("MEDIUM", 0) or 0):
            return "Medium findings indicate security hardening work required before the next production cycle."
        return "No active high-impact vulnerability is visible; continue scheduled monitoring and branch scans."

    def no_findings(label: str):
        return md(f"*   <b>No active {clean(label)} findings were present in this scan snapshot.</b>", bullet)

    def gitleaks_block(items: list[dict]):
        if not items:
            return [no_findings("Gitleaks secret")]
        blocks = []
        for item in items[:5]:
            blocks.extend([
                md(f"*   <b>Target Repository:</b> `{clean(repo)}`", bullet),
                md(f"*   <b>Location:</b> `{clean(payload.get('commit_sha') or 'latest commit')}` | `{clean(item.get('affected_file') or item.get('location'))}`", bullet),
                md(f"*   <b>Assigned Team:</b> <b>[{assigned_team(item)}]</b>", bullet),
                md("*   <b>Immediate Action Required:</b>", bullet),
                md("    1. Revoke and rotate the leaked credentials everywhere immediately.", bullet),
                md("    2. Purge the Git history using `git-filter-repo` or BFG Repo-Cleaner.", bullet),
                md("    3. <i>Note: Do not simply delete the line and commit again; the secret remains in history.</i>", bullet),
                Spacer(1, 0.035 * inch),
            ])
        return blocks

    def trivy_image_block(items: list[dict]):
        if not items:
            return [no_findings("Trivy Image critical")]
        blocks = []
        for item in items[:5]:
            blocks.extend([
                md(f"*   <b>Target Container:</b> `{clean(payload.get('image_full_path') or payload.get('project_name') or 'container image')}`", bullet),
                md(f"*   <b>Vulnerability ID:</b> <b>{first_cve(item.get('issue_name'))}</b>", bullet),
                md(f"*   <b>Assigned Team:</b> <b>[{assigned_team(item)}]</b>", bullet),
                md("*   <b>Immediate Action Required:</b>", bullet),
                md("    1. Update the parent image tag in the project `Dockerfile`.", bullet),
                md("    2. Rebuild, test, and push the updated image to production.", bullet),
                Spacer(1, 0.035 * inch),
            ])
        return blocks

    def semgrep_block(items: list[dict]):
        if not items:
            return [no_findings("Semgrep")]
        blocks = []
        for item in items[:5]:
            blocks.extend([
                md(f"*   <b>Target Repository:</b> `{clean(repo)}`", bullet),
                md(f"*   <b>Rule Triggered:</b> `{clean(item.get('issue_name'))}`", bullet),
                md(f"*   <b>File Path:</b> `{clean(item.get('affected_file') or item.get('location'))}`", bullet),
                md(f"*   <b>Assigned Team:</b> <b>[{assigned_team(item)}]</b>", bullet),
                md("*   <b>Action Required:</b> Rewrite the code block to use parameterized queries, approved framework sanitizers, or secure configuration controls.", bullet),
                Spacer(1, 0.035 * inch),
            ])
        return blocks

    def sonar_block(items: list[dict]):
        if not items:
            return [no_findings("SonarCloud")]
        blocks = []
        for item in items[:5]:
            blocks.extend([
                md(f"*   <b>Target Repository:</b> `{clean(repo)}`", bullet),
                md(f"*   <b>Issue Type:</b> <b>{clean(item.get('severity'))}</b> - {clean(item.get('issue_name'))}", bullet),
                md(f"*   <b>Assigned Team:</b> <b>[{assigned_team(item)}]</b>", bullet),
                md("*   <b>Action Required:</b> Resolve the hardcoded cryptographic configuration, insecure communication protocol, quality gate, or hotspot flagged by the tool.", bullet),
                Spacer(1, 0.035 * inch),
            ])
        return blocks

    def trivy_fs_block(items: list[dict]):
        if not items:
            return [no_findings("Trivy FS")]
        blocks = []
        for item in items[:6]:
            blocks.extend([
                md(f"*   <b>Target Repository:</b> `{clean(repo)}`", bullet),
                md(f"*   <b>Vulnerable Package:</b> `{package_name(item)}` (Current: `See report` -&gt; Required Minimum: `{fix_version(item)}`)", bullet),
                md(f"*   <b>Assigned Team:</b> <b>[{assigned_team(item)}]</b>", bullet),
                md("*   <b>Action Required:</b>", bullet),
                md("    1. Update the dependency file (e.g., package.json, pom.xml, go.mod, requirements.txt).", bullet),
                md("    2. Run local integration tests to verify no breaking changes exist before merging.", bullet),
                Spacer(1, 0.035 * inch),
            ])
        return blocks

    story = []
    story.extend([
        Spacer(1, 1.55 * inch),
        Paragraph("Vulnerabilities Evaluation Report", styles["ReportTitle"]),
        Paragraph("Remediation Plan by SecureGate AI", styles["Subtitle"]),
        Spacer(1, 0.22 * inch),
        Paragraph(f"<b>Project:</b> {clean(payload.get('project_name'))}", styles["CenterBody"]),
        Paragraph(f"<b>Repository:</b> {link_markup(repo) if str(repo).startswith(('http://', 'https://')) else clean(repo)}", styles["CenterBody"]),
        Paragraph(f"<b>Branch:</b> {clean(payload.get('branch'))}", styles["CenterBody"]),
        Paragraph("<b>Target Environment:</b> GitHub Repository &amp; Docker Image Registry", styles["CenterBody"]),
        Paragraph("<b>Document Classification:</b> RESTRICTED / INTERNAL SECURITY ONLY", styles["CenterBody"]),
        Paragraph(f"<b>Generated On:</b> {clean(generated_date)}", styles["CenterBody"]),
        Paragraph(f"<b>Data Evaluation Snapshot:</b> `{scan_link}`", styles["CenterBody"]),
        Spacer(1, 0.55 * inch),
        Paragraph("Document Control &amp; Approvals", styles["CenteredSection"]),
        table([
            [Paragraph("Version", header_cell), Paragraph("Date", header_cell), Paragraph("Author", header_cell), Paragraph("Reviewer", header_cell), Paragraph("Status", header_cell)],
            [Paragraph("v1.0", cell), Paragraph(clean(generated_date), cell), Paragraph("Security Dashboard Operations", cell), Paragraph("SecOps Team Lead", cell), Paragraph("<b>Action Required</b>", cell)],
        ], [0.75 * inch, 1.05 * inch, 2.05 * inch, 1.55 * inch, 1.25 * inch]),
        PageBreak(),
    ])

    story.extend([
        Paragraph("TABLE OF CONTENTS &amp; SUMMARY", styles["Section"]),
        Paragraph("Table of Contents", styles["ToolSection"]),
        toc(1, "Executive Summary & Blast Radius", "section1"),
        toc(2, "Immediate Threat Response (Tier 1 / 24-Hour SLA)", "section2"),
        toc(3, "Application Security Remediation (Tier 2 / 7-Day SLA)", "section3"),
        toc(4, "Dependency Security Remediation (Tier 3 / 15-Day SLA)", "section4"),
        toc(5, "Remediation Progress Checklist", "section5"),
        toc(6, "Escalation & False Positive Policy", "section6"),
        toc(7, "Closure & Verification Process", "section7"),
        Spacer(1, 0.16 * inch),
        *section_break(),
        section("1. Executive Summary & Blast Radius", "section1"),
        md("This report contains aggregated vulnerability data evaluated by the central security dashboard. The targeted engineering teams must execute the remediation steps outlined below according to assigned severities and service level agreements."),
        md(f"-   <b>Total Risk Exposure:</b> {risk_count_markup(total_count)} Open Vulnerabilities", bullet),
        md(f"-   <b>Scope:</b> {repo_count} GitHub Repositories | {image_count} Docker Images Evaluated", bullet),
        md(f"-   <b>Core Threat Vector:</b> {clean(one_sentence_risk())}", bullet),
        Paragraph("[SLA] Service Level Agreements (SLA) for Fixes", styles["ToolSection"]),
        md("-   <b>Tier 1 (Critical):</b> Fix within <b>24 Hours</b>", bullet),
        md("-   <b>Tier 2 (High):</b> Fix within <b>7 Days</b>", bullet),
        md("-   <b>Tier 3 (Medium/Low):</b> Fix within <b>15 Days / Next Sprint</b>", bullet),
        PageBreak(),
    ])

    story.extend([
        section("2. Immediate Threat Response (Tier 1 / 24-Hour SLA)", "section2"),
        Paragraph("[KEY] Gitleaks: Secrets Exposed", styles["ToolSection"]),
        *gitleaks_block(items_for("gitleaks")),
        *section_break(),
        Paragraph("[IMG] Trivy Image: OS-Level Critical Vulnerabilities", styles["ToolSection"]),
        *trivy_image_block(items_for("trivy-image", {"CRITICAL"})),
        *section_break(),
        section("3. Application Security Remediation (Tier 2 / 7-Day SLA)", "section3"),
        Paragraph("[CODE] Semgrep: Custom Rule &amp; Logic Flaws", styles["ToolSection"]),
        *semgrep_block(items_for("semgrep")),
        *section_break(),
        Paragraph("[SONAR] SonarCloud: Quality Gate &amp; Code Flaws", styles["ToolSection"]),
        *sonar_block(items_for("sonarqube")),
        PageBreak(),
    ])

    story.extend([
        section("4. Dependency Security Remediation (Tier 3 / 15-Day SLA)", "section4"),
        Paragraph("[PKG] Trivy FS: Software Composition Analysis (SCA)", styles["ToolSection"]),
        *trivy_fs_block(items_for("trivy-fs")),
        *section_break(),
        section("5. Remediation Progress Checklist", "section5"),
        md("<i>Engineering Leads must use this checklist to track individual project remediation paths toward baseline completion.</i>"),
        Paragraph("[TRIAGE] Phase 1: Isolation &amp; Triage (First 12 Hours)", styles["ToolSection"]),
        checkbox("Identify all high-risk repositories and locate owners for assigned actions."),
        checkbox("Verify that fake/dummy testing keys flagged by Gitleaks are explicitly skipped in `gitleaks.toml`."),
        checkbox("Review open Trivy reports to filter out unfixable upstream OS vulnerabilities."),
        Paragraph("[PATCH] Phase 2: Patching &amp; Implementation (Before SLA Deadline)", styles["ToolSection"]),
        checkbox("Revoke, rotate, and scrub all active credentials leaked via Git historical commits."),
        checkbox("Update Dockerfiles to pull from verified minimal, Alpine, or Distroless parent image tags."),
        checkbox("Refactor application logic violating Semgrep injection and configuration constraints."),
        checkbox("Bump vulnerable open-source dependencies (Trivy FS) to compliant versions."),
        Paragraph("[TEST] Phase 3: Validation &amp; Deploy (Post-Remediation)", styles["ToolSection"]),
        checkbox("Run localized test suites to ensure security changes did not introduce breaking code behavior."),
        checkbox("Push clean code modifications and newly validated container builds into default pipelines."),
        checkbox("Monitor the centralized security dashboard to confirm that target assets transition to a Passed status."),
        *section_break(),
        section("6. Escalation & False Positive Policy", "section6"),
        md("If an engineering team cannot patch an item within the designated SLA window, they must execute one of the following official overrides:"),
        md("*   <b>False Positives:</b> Flag the vulnerability directly inside the central dashboard interface. Provide a written technical justification (e.g., \"Code is only used in local unit test environment\").", bullet),
        md("*   <b>Risk Acceptance:</b> If a patch breaks production stability, submit a formal <b>Risk Acceptance Request</b> via the security portal. This requires explicit sign-off from the Engineering Director and expires in <b>90 days</b>.", bullet),
        PageBreak(),
    ])

    story.extend([
        Spacer(1, 0.65 * inch),
        section("7. Closure & Verification Process", "section7"),
        Paragraph("[SYNC] Automatic Verification", styles["ToolSection"]),
        md("Once a code fix is merged into the default branch or an updated Docker image is pushed to the registry, the security dashboard will automatically re-evaluate the target during its next scheduled cycle. Successfully resolved vulnerabilities will clear from the active tracking view automatically."),
        *section_break(),
        Paragraph("[ALERT] Emergency Escalation Contact", styles["ToolSection"]),
        md("For automated dashboard sync errors, immediate manual cache purges, or emergency production blocking overrides, contact the Security Operations team:"),
        md("*   <b>Internal Slack Channel:</b> `#securegate-ai`", bullet),
        md("*   <b>Emergency Hotline:</b> Ext. 5555", bullet),
        md("*   <b>Ticketing Desk:</b> `https://security-support.internal`", bullet),
        Spacer(1, 0.8 * inch),
        Paragraph("[END OF REPORT]", styles["Section"]),
        md("<b>SecureGate AI Security Operations Team</b>"),
        md("<i>Let’s safeguard our repositories, images, and infrastructure.</i>"),
    ])

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()

