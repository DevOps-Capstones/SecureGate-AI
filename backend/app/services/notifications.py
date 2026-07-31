import json
import smtplib
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Iterable
from urllib import request

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.scan import Finding, Notification, Scan
from app.services.repository import safe_repository_url
from app.services.alert_policies import channels_for_alert, channels_for_scan


def _report_link(scan_id: str, report_type: str = "pdf") -> str:
    return f"{settings.public_backend_url}/api/v1/reports/{scan_id}/{report_type}"


def _slack_recipient_label() -> str:
    return settings.slack_channel_name or "Slack channel configured"


def _recommendation_summary(report: dict) -> str:
    recommendations: Iterable[dict] = report.get("recommendations", [])
    titles = [item.get("title", "Review security finding") for item in list(recommendations)[:5]]
    return "\n".join(f"- {title}" for title in titles) or "- Continue monitoring and keep dependencies patched."


def _severity_context(report: dict) -> tuple[str, str]:
    summary = report.get("vulnerability_summary", {}) or {}
    critical = int(summary.get("CRITICAL", 0) or 0)
    high = int(summary.get("HIGH", 0) or 0)
    secrets = int(summary.get("secrets", 0) or 0)
    sonar_gate = str(summary.get("sonarqube_quality_gate", "UNKNOWN"))
    if secrets or critical or sonar_gate not in {"OK", "UNKNOWN"}:
        return "CRITICAL", "Immediate action required: blocking security findings were detected."
    if high:
        return "HIGH", "High severity vulnerabilities were detected; prioritize remediation."
    if int(summary.get("MEDIUM", 0) or 0):
        return "MEDIUM", "Medium severity findings were detected; plan remediation."
    return "INFO", "No blocking vulnerability findings were detected."


def _severity_icon(severity: str, decision: str | None = None) -> str:
    if decision == "APPROVED":
        return "✅"
    return {
        "CRITICAL": "🚨",
        "HIGH": "⚠️",
        "MEDIUM": "🟡",
        "LOW": "🟢",
        "INFO": "✅",
    }.get(severity.upper(), "🔎")


def _severity_label(severity: str, decision: str | None = None) -> str:
    labels = {
        "CRITICAL": "Critical Risk",
        "HIGH": "High Risk",
        "MEDIUM": "Medium Risk",
        "LOW": "Low Risk",
        "INFO": "Clean",
    }
    if decision == "APPROVED":
        return "Clean / Approved"
    return labels.get(severity.upper(), "Review Needed")


def _summary_subject_icon(severity: str, failed_scans: int = 0) -> str:
    if failed_scans:
        return "❌"
    return _severity_icon(severity)


def _severity_counts_line(report: dict) -> str:
    summary = report.get("vulnerability_summary", {}) or {}
    return (
        f"🚨 Critical: {int(summary.get('CRITICAL', 0) or 0)} | "
        f"⚠️ High: {int(summary.get('HIGH', 0) or 0)} | "
        f"🟡 Medium: {int(summary.get('MEDIUM', 0) or 0)} | "
        f"🟠 Low: {int(summary.get('LOW', 0) or 0)}"
    )


def _create_notification(db: Session, scan: Scan | None, notification_type: str, recipient: str, category: str, severity: str, message: str, summary_period: str | None = None) -> Notification:
    notification = Notification(
        scan_pk=scan.id if scan else None,
        notification_type=notification_type,
        recipient=recipient,
        status="PENDING",
        category=category,
        severity_level=severity,
        summary_period=summary_period,
        message=message,
    )
    db.add(notification)
    db.flush()
    return notification


def _send_slack(notification: Notification) -> None:
    if not settings.slack_webhook_url:
        notification.status = "SKIPPED"
        notification.error_message = "SLACK_WEBHOOK_URL is not configured."
        return
    try:
        payload = json.dumps({"text": notification.message}).encode("utf-8")
        req = request.Request(settings.slack_webhook_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=10) as response:
            notification.status = "SENT" if response.status < 400 else "FAILED"
            notification.sent_at = None if notification.status == "FAILED" else datetime.now(timezone.utc)
    except Exception as exc:
        notification.status = "FAILED"
        notification.error_message = str(exc)


def _send_email(notification: Notification, subject: str) -> None:
    if not settings.smtp_host or not settings.smtp_from:
        notification.status = "SKIPPED"
        notification.error_message = "SMTP_HOST and SMTP_FROM must be configured."
        return
    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.smtp_from
        message["To"] = notification.recipient
        message.set_content(notification.message)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        notification.status = "SENT"
        notification.sent_at = datetime.now(timezone.utc)
    except Exception as exc:
        notification.status = "FAILED"
        notification.error_message = str(exc)


def send_slack_notification(db: Session, scan: Scan, report: dict) -> Notification:
    severity, severity_message = _severity_context(report)
    recipient = _slack_recipient_label() if settings.slack_webhook_url else "SLACK_WEBHOOK_URL not configured"
    icon = _severity_icon(severity, scan.deployment_decision)
    decision = scan.deployment_decision or "PENDING"
    score = scan.security_score if scan.security_score is not None else "Pending"
    next_action = (
        "Code is safe to prepare for deployment."
        if decision == "APPROVED"
        else "Fix the listed findings, then run the scan again."
    )
    text = (
        f"Project: {scan.project_name}\n"
        f"{icon} SecureGate AI Scan {decision}\n"
        f"Scan ID: {scan.scan_id}\n"
        f"Repository: {safe_repository_url(scan.repository_url)}\n"
        f"Branch: {scan.branch or 'Not provided'}\n"
        f"Security Score: {score}/100\n"
        f"Deployment Decision: {decision}\n"
        f"Severity Counts: {_severity_counts_line(report)}\n"
        f"Summary: {severity_message}\n"
        f"Next Step: {next_action}\n"
        f"Docker Image: {scan.image_full_path or 'Not pushed yet'}\n"
        f"Master Report: {_report_link(scan.scan_id)}\n"
        f"Dashboard: {settings.public_backend_url}"
    )
    notification = _create_notification(db, scan, "SLACK", recipient, "SCAN", severity, text)
    _send_slack(notification)
    return notification


def send_email_notification(db: Session, scan: Scan, report: dict) -> Notification:
    severity, severity_message = _severity_context(report)
    recipient = settings.smtp_username or settings.smtp_from or "SMTP recipient not configured"
    decision = scan.deployment_decision or "PENDING"
    score = scan.security_score if scan.security_score is not None else "Pending"
    next_action = (
        "Code is safe to prepare for deployment."
        if decision == "APPROVED"
        else "Fix the listed findings, then run the scan again."
    )
    subject = f"{_severity_icon(severity, decision)} SecureGate AI Scan {decision} - {scan.project_name}"
    body = (
        f"Project: {scan.project_name}\n"
        f"Scan ID: {scan.scan_id}\n"
        f"Repository: {safe_repository_url(scan.repository_url)}\n"
        f"Branch: {scan.branch or 'Not provided'}\n"
        f"Security Score: {score}/100\n"
        f"Deployment Decision: {decision}\n"
        f"Severity Counts: {_severity_counts_line(report)}\n"
        f"Summary: {severity_message}\n"
        f"Next Step: {next_action}\n"
        f"Docker Image: {scan.image_full_path or 'Not pushed yet'}\n"
        f"Timestamp: {report.get('report_metadata', {}).get('generated_at', datetime.now(timezone.utc).isoformat())}\n\n"
        f"Master Security Report Links:\n"
        f"PDF: {_report_link(scan.scan_id, 'pdf')}\n"
        f"DOCX: {_report_link(scan.scan_id, 'docx')}\n"
        f"JSON: {_report_link(scan.scan_id, 'json')}\n\n"
        f"Dashboard: {settings.public_backend_url}\n"
    )
    notification = _create_notification(db, scan, "EMAIL", recipient, "SCAN", severity, body)
    _send_email(notification, subject)
    return notification


def send_scan_notifications(db: Session, scan: Scan, report: dict) -> list[Notification]:
    severity, _ = _severity_context(report)
    channels = channels_for_scan(db, scan, severity)
    notifications: list[Notification] = []
    if "slack" in channels:
        notifications.append(send_slack_notification(db, scan, report))
    if "email" in channels:
        notifications.append(send_email_notification(db, scan, report))
    return notifications


def send_alert_notifications(db: Session, alert, source: str = "Alertmanager") -> list[Notification]:
    severity = str(alert.severity).upper()
    timestamp = datetime.now(timezone.utc).isoformat()
    icon = _severity_icon(severity)
    deployment_status = "BLOCKED" if severity == "CRITICAL" else "REVIEW"
    dashboard_link = settings.public_backend_url
    message = (
        f"Project: {alert.project_name}\n"
        f"Repository: {safe_repository_url(alert.repository)}\n"
        f"Scan ID: {alert.scan_id or 'Not linked'}\n"
        f"{icon} SecureGate AI {source} Alert\n"
        f"Alert Severity: {severity}\n"
        f"Deployment Status: {deployment_status}\n"
        f"Security Score: See SecureGate dashboard\n"
        f"Short Summary: {alert.description}\n"
        f"Dashboard Link: {dashboard_link}\n"
        f"Timestamp: {timestamp}"
    )
    channels = channels_for_alert(db, alert, severity)
    notifications: list[Notification] = []
    if "slack" in channels:
        slack = _create_notification(
            db,
            None,
            "SLACK",
            _slack_recipient_label() if settings.slack_webhook_url else "SLACK_WEBHOOK_URL not configured",
            "ALERT",
            severity,
            message,
        )
        _send_slack(slack)
        notifications.append(slack)
    if "email" in channels:
        email_message = (
            f"Project: {alert.project_name}\n"
            f"Repository: {safe_repository_url(alert.repository)}\n"
            f"Scan ID: {alert.scan_id or 'Not linked'}\n"
            f"Alert Severity: {severity}\n"
            f"Deployment Status: {deployment_status}\n"
            f"Security Score: See SecureGate dashboard\n"
            f"Summary: {alert.description}\n"
            f"Recommendation: {alert.recommendation}\n"
            f"Timestamp: {timestamp}\n"
            f"Master Security Report Link: {dashboard_link}\n"
        )
        email = _create_notification(
            db,
            None,
            "EMAIL",
            settings.smtp_username or settings.smtp_from or "SMTP recipient not configured",
            "ALERT",
            severity,
            email_message,
        )
        _send_email(email, f"{_severity_icon(severity)} SecureGate AI {severity.title()} Alert - {alert.alert_type.replace('_', ' ').title()}")
        notifications.append(email)
    return notifications


def _summary_window(period: str) -> tuple[str, int, str]:
    normalized = period.upper()
    if normalized == "MONTHLY":
        return normalized, 30, "last 30 days"
    if normalized == "WEEKLY":
        return normalized, 7, "last 7 days"
    return "DAILY", 1, "last 24 hours"


def build_summary_message(db: Session, period: str) -> tuple[str, str]:
    normalized, days, window_label = _summary_window(period)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    scans = list(db.execute(select(Scan).where(Scan.received_at >= since)).scalars().all())
    scan_ids = [scan.id for scan in scans]
    findings = list(db.execute(select(Finding).where(Finding.scan_pk.in_(scan_ids))).scalars().all()) if scan_ids else []

    scan_by_id = {scan.id: scan for scan in scans}
    project_names = sorted({scan.project_name for scan in scans})
    decisions = Counter(scan.deployment_decision for scan in scans)
    statuses = Counter(scan.status for scan in scans)
    failed_scans = decisions.get("REJECTED", 0) + sum(1 for scan in scans if scan.status == "FAILED")
    passed_scans = decisions.get("APPROVED", 0)
    severities = Counter(finding.severity.upper() for finding in findings)
    informational = severities.get("INFO", 0) + severities.get("INFORMATIONAL", 0) + severities.get("UNKNOWN", 0)
    pending = sum(1 for finding in findings if finding.resolution_status == "PENDING")
    resolved = sum(1 for finding in findings if finding.resolution_status == "RESOLVED")
    secrets = sum(1 for finding in findings if finding.tool == "gitleaks")
    scores = [scan.security_score for scan in scans if scan.security_score is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0
    deployment_success_rate = round((passed_scans / len(scans)) * 100, 2) if scans else 100.0
    pipeline_success_rate = round((statuses.get("COMPLETED", 0) / len(scans)) * 100, 2) if scans else 100.0
    quality_gate_stats = Counter(scan.sonar_quality_gate for scan in scans)

    project_data: dict[str, dict] = defaultdict(lambda: {
        "scans": 0,
        "passed": 0,
        "failed": 0,
        "severity": Counter(),
        "pending": 0,
        "resolved": 0,
        "secrets": 0,
    })
    for scan in scans:
        data = project_data[scan.project_name]
        data["scans"] += 1
        if scan.deployment_decision == "APPROVED":
            data["passed"] += 1
        if scan.deployment_decision == "REJECTED" or scan.status == "FAILED":
            data["failed"] += 1
    for finding in findings:
        scan = scan_by_id.get(finding.scan_pk)
        project_name = scan.project_name if scan else "Unknown Project"
        data = project_data[project_name]
        data["severity"][finding.severity.upper()] += 1
        if finding.tool == "gitleaks":
            data["secrets"] += 1
        if finding.resolution_status == "RESOLVED":
            data["resolved"] += 1
        else:
            data["pending"] += 1

    severity = "CRITICAL" if severities.get("CRITICAL", 0) else "HIGH" if severities.get("HIGH", 0) else "MEDIUM" if severities.get("MEDIUM", 0) else "LOW" if severities.get("LOW", 0) else "INFO"
    icon = _summary_subject_icon(severity, failed_scans)
    ranked_projects = sorted(
        project_data.items(),
        key=lambda item: (item[1]["severity"].get("CRITICAL", 0), item[1]["severity"].get("HIGH", 0), item[1]["failed"], item[1]["secrets"]),
        reverse=True,
    )
    project_lines = []
    for project_name, data in ranked_projects[:8]:
        counts = data["severity"]
        project_icon = "❌" if data["failed"] else "✅"
        project_lines.append(
            f"{project_icon} {project_name}: {data['scans']} scan(s), {data['passed']} passed, {data['failed']} failed. "
            f"Critical {counts.get('CRITICAL', 0)}, High {counts.get('HIGH', 0)}, Medium {counts.get('MEDIUM', 0)}, "
            f"Low {counts.get('LOW', 0)}, Info {counts.get('INFO', 0) + counts.get('INFORMATIONAL', 0) + counts.get('UNKNOWN', 0)}, "
            f"Secrets {data['secrets']}, Pending {data['pending']}, Resolved {data['resolved']}."
        )
    if not project_lines:
        project_lines.append("- No projects were scanned in this period.")

    top_vulnerabilities = Counter(finding.title for finding in findings if finding.severity.upper() in {"CRITICAL", "HIGH"}).most_common(5)
    top_vulnerability_lines = [f"- {title}: {count}" for title, count in top_vulnerabilities] or ["- No critical or high vulnerabilities in this period."]
    top_cves = Counter(str((finding.raw_data or {}).get("VulnerabilityID") or (finding.raw_data or {}).get("cve") or finding.title) for finding in findings if finding.tool.startswith("trivy")).most_common(5)
    top_cve_lines = [f"- {title}: {count}" for title, count in top_cves] or ["- No CVE data found in this period."]

    header = (
        f"{icon} SecureGate AI {normalized.title()} Security Summary - {_severity_label(severity)}\n"
        f"Period: {window_label}\n"
        f"Projects scanned: {len(project_names)}\n"
        f"Total scans: {len(scans)}\n"
        f"✅ Passed deployments: {passed_scans}\n"
        f"❌ Failed or rejected deployments: {failed_scans}\n"
        f"Average security score: {average_score}\n"
        f"Vulnerabilities found: Critical {severities.get('CRITICAL', 0)}, High {severities.get('HIGH', 0)}, "
        f"Medium {severities.get('MEDIUM', 0)}, Low {severities.get('LOW', 0)}, Informational {informational}\n"
        f"Secrets detected: {secrets}\n"
        f"Finding status: {pending} pending, {resolved} resolved\n"
    )

    if normalized == "DAILY":
        detail = (
            "\nDaily operations view:\n"
            f"- Total scans: {len(scans)}\n"
            f"- Passed deployments: {passed_scans}\n"
            f"- Failed deployments: {failed_scans}\n"
            f"- Security score average: {average_score}\n"
            f"- Top affected projects:\n{chr(10).join(project_lines)}\n"
        )
    elif normalized == "WEEKLY":
        score_trend = "Improving" if len(scores) >= 2 and scores[-1] >= scores[0] else "Needs review" if scores else "No score data"
        detail = (
            "\nWeekly trend view:\n"
            f"- Security score trend: {score_trend}\n"
            f"- Deployment success rate: {deployment_success_rate}%\n"
            f"- Pipeline success rate: {pipeline_success_rate}%\n"
            f"- Quality gate statistics: {dict(quality_gate_stats)}\n"
            f"- Top vulnerabilities:\n{chr(10).join(top_vulnerability_lines)}\n"
            f"- Most vulnerable projects:\n{chr(10).join(project_lines)}\n"
        )
    else:
        posture = "Healthy" if severity in {"LOW", "INFO"} and failed_scans == 0 else "At Risk" if severity in {"CRITICAL", "HIGH"} else "Needs Attention"
        technical_debt = quality_gate_stats.get("ERROR", 0) + quality_gate_stats.get("FAILED", 0)
        detail = (
            "\nMonthly executive view:\n"
            f"- Overall security posture: {posture}\n"
            f"- Compliance trend: {deployment_success_rate}% deployments approved\n"
            f"- Average security score: {average_score}\n"
            f"- Top CVEs:\n{chr(10).join(top_cve_lines)}\n"
            f"- Most vulnerable projects:\n{chr(10).join(project_lines)}\n"
            f"- Technical debt trend: {technical_debt} quality gate issue signal(s)\n"
            f"- Secret detection trend: {secrets} secret finding(s)\n"
            f"- Deployment success rate: {deployment_success_rate}%\n"
            f"- Executive summary: {posture}. Review failed projects first, then reduce critical and high vulnerabilities.\n"
        )

    message = (
        header
        + detail
        + "\nWhat this means: Review failed or rejected projects first. Fix critical and high vulnerabilities before deployment.\n"
        + f"Dashboard: {settings.public_backend_url}"
    )
    return severity, message


def send_summary_notifications(db: Session, period: str) -> list[Notification]:
    normalized, _, _ = _summary_window(period)
    severity, message = build_summary_message(db, normalized)
    slack = _create_notification(db, None, "SLACK", _slack_recipient_label() if settings.slack_webhook_url else "SLACK_WEBHOOK_URL not configured", "SUMMARY", severity, message, normalized)
    email = _create_notification(db, None, "EMAIL", settings.smtp_username or settings.smtp_from or "SMTP recipient not configured", "SUMMARY", severity, message, normalized)
    _send_slack(slack)
    _send_email(email, f"{_severity_icon(severity)} SecureGate AI {normalized.title()} Security Summary - {_severity_label(severity)}")
    db.commit()
    return [slack, email]
