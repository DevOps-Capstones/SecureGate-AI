from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.scan import Alert, Finding, Notification, Scan
from app.services.alert_policies import channels_for_alert, channels_for_scan

RUNBOOK_URL = "https://runbooks.example.com/securegate/{alert_type}"


def _channels_for_severity(severity: str) -> list[str]:
    severity = severity.upper()
    channels = ["dashboard", "slack"]
    if severity in {"CRITICAL", "HIGH"}:
        channels.append("email")
    return channels


def _alert_id() -> str:
    return f"ALT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"


def _open_alert_exists(db: Session, scan: Scan, alert_type: str) -> bool:
    return db.execute(
        select(Alert).where(Alert.scan_pk == scan.id, Alert.alert_type == alert_type, Alert.status == "OPEN")
    ).scalar_one_or_none() is not None


def create_alert(db: Session, scan: Scan, severity: str, alert_type: str, description: str, recommendation: str) -> Alert:
    if _open_alert_exists(db, scan, alert_type):
        return db.execute(select(Alert).where(Alert.scan_pk == scan.id, Alert.alert_type == alert_type, Alert.status == "OPEN")).scalar_one()
    alert = Alert(
        alert_id=_alert_id(),
        scan_pk=scan.id,
        scan_id=scan.scan_id,
        project_name=scan.project_name,
        repository=scan.repository_url,
        branch=scan.branch,
        severity=severity.upper(),
        alert_type=alert_type,
        status="OPEN",
        notification_channels=channels_for_scan(db, scan, severity),
        description=description,
        recommendation=recommendation,
        runbook_url=RUNBOOK_URL.format(alert_type=alert_type.lower().replace("_", "-")),
        escalation_level=0,
        escalation_history=[],
    )
    db.add(alert)
    db.flush()
    return alert


def evaluate_scan_alerts(db: Session, scan: Scan) -> list[Alert]:
    alerts: list[Alert] = []
    counts = Counter(finding.severity.upper() for finding in scan.findings)
    secrets = sum(1 for finding in scan.findings if finding.tool == "gitleaks")
    if counts.get("CRITICAL", 0) > settings.critical_vulnerability_threshold:
        alerts.append(create_alert(db, scan, "CRITICAL", "CRITICAL_VULNERABILITY_DETECTED", f"{counts.get('CRITICAL', 0)} critical vulnerabilities exceeded threshold {settings.critical_vulnerability_threshold}.", "Fix or patch critical vulnerabilities before deployment."))
    if counts.get("HIGH", 0) > settings.high_vulnerability_threshold:
        alerts.append(create_alert(db, scan, "HIGH", "HIGH_VULNERABILITY_THRESHOLD_REACHED", f"{counts.get('HIGH', 0)} high vulnerabilities exceeded threshold {settings.high_vulnerability_threshold}.", "Prioritize high vulnerabilities and decide whether deployment should remain blocked by policy."))
    if settings.secret_detection_required and secrets:
        alerts.append(create_alert(db, scan, "CRITICAL", "SECRETS_DETECTED", "Secrets or credentials were detected in the repository.", "Remove exposed secrets, rotate credentials, and move values into GitHub Secrets or a vault."))
    if scan.security_score is not None and scan.security_score < settings.security_score_threshold:
        alerts.append(create_alert(db, scan, "HIGH", "SECURITY_SCORE_BELOW_THRESHOLD", f"Security score is {scan.security_score}, below threshold {settings.security_score_threshold}.", "Resolve high-impact findings until the score reaches the configured threshold."))
    if scan.deployment_decision == "REJECTED":
        alerts.append(create_alert(db, scan, "CRITICAL", "DEPLOYMENT_BLOCKED", "SecureGate AI blocked this deployment.", "Review the master report and fix blocking findings before retrying."))
    if settings.quality_gate_required and scan.sonar_quality_gate not in {"OK", "UNKNOWN"}:
        alerts.append(create_alert(db, scan, "HIGH", "QUALITY_GATE_FAILURE", f"SonarQube quality gate is {scan.sonar_quality_gate}.", "Fix SonarCloud quality gate issues and rerun the pipeline."))
    return alerts


def escalate_open_alerts(db: Session) -> int:
    now = datetime.now(timezone.utc)
    escalated = 0
    alerts = db.execute(select(Alert).where(Alert.status == "OPEN", Alert.severity == "CRITICAL")).scalars().all()
    for alert in alerts:
        age_minutes = (now - alert.created_at).total_seconds() / 60 if alert.created_at else 0
        if age_minutes >= settings.alert_escalation_minutes and alert.escalation_level < 1:
            history = list(alert.escalation_history or [])
            history.append({"level": 1, "channel": "email", "at": now.isoformat(), "note": "Critical alert escalated after wait period."})
            alert.escalation_history = history
            alert.escalation_level = 1
            escalated += 1
    return escalated


def alert_statistics(db: Session) -> dict:
    alerts = db.execute(select(Alert)).scalars().all()
    by_severity = Counter(alert.severity for alert in alerts)
    by_status = Counter(alert.status for alert in alerts)
    by_type = Counter(alert.alert_type for alert in alerts)
    return {
        "total_alerts": len(alerts),
        "open_alerts": by_status.get("OPEN", 0),
        "resolved_alerts": by_status.get("RESOLVED", 0),
        "escalated_alerts": sum(1 for alert in alerts if alert.escalation_level > 0),
        "by_severity": dict(by_severity),
        "by_status": dict(by_status),
        "by_type": dict(by_type),
    }


def notification_analytics(db: Session) -> dict:
    notifications = db.execute(select(Notification)).scalars().all()
    slack = [item for item in notifications if item.notification_type == "SLACK"]
    email = [item for item in notifications if item.notification_type == "EMAIL"]
    sent = [item for item in notifications if item.status == "SENT"]
    return {
        "slack_delivery_count": sum(1 for item in slack if item.status == "SENT"),
        "slack_failures": sum(1 for item in slack if item.status == "FAILED"),
        "email_delivery_count": sum(1 for item in email if item.status == "SENT"),
        "email_failures": sum(1 for item in email if item.status == "FAILED"),
        "notification_volume": len(notifications),
        "notification_success_rate": round((len(sent) / len(notifications)) * 100, 2) if notifications else 100.0,
        "average_delivery_time": 0,
    }


def _alertmanager_alert_id(item: dict) -> str:
    fingerprint = str(item.get("fingerprint") or "").strip()
    labels = item.get("labels", {}) if isinstance(item.get("labels"), dict) else {}
    starts_at = str(item.get("startsAt") or "")
    if fingerprint:
        return f"AM-{fingerprint[:32]}"
    raw = f"{labels.get('alertname', 'AlertmanagerAlert')}:{labels.get('severity', 'INFO')}:{starts_at}"
    return f"AM-{uuid4().hex[:8].upper()}-{abs(hash(raw)) % 100000}"


def _recommendation_for_alert_type(alert_type: str) -> str:
    mapping = {
        "CriticalVulnerabilityDetected": "Patch critical vulnerabilities before deployment.",
        "HighVulnerabilityThresholdReached": "Prioritize high vulnerabilities and review deployment policy.",
        "SecretsDetected": "Remove exposed secrets, rotate credentials, and use GitHub Secrets or a vault.",
        "QualityGateFailure": "Fix SonarCloud quality gate issues and rerun the pipeline.",
        "DeploymentBlocked": "Review the master report and fix blocking findings before retrying.",
        "ReportGenerationFailure": "Check report generation logs and storage permissions.",
        "NotificationDeliveryFailure": "Verify Slack webhook and SMTP settings.",
    }
    return mapping.get(alert_type, "Review the SecureGate AI dashboard and resolve the alert condition.")


def process_alertmanager_webhook(db: Session, payload: dict) -> dict:
    from app.services.notifications import send_alert_notifications

    processed = 0
    delivered = 0
    alerts_payload = payload.get("alerts", []) if isinstance(payload, dict) else []
    for item in alerts_payload:
        if not isinstance(item, dict):
            continue
        labels = item.get("labels", {}) if isinstance(item.get("labels"), dict) else {}
        annotations = item.get("annotations", {}) if isinstance(item.get("annotations"), dict) else {}
        status = str(item.get("status") or "firing").upper()
        alert_id = _alertmanager_alert_id(item)
        alert = db.execute(select(Alert).where(Alert.alert_id == alert_id)).scalar_one_or_none()
        if alert and status == "RESOLVED":
            alert.status = "RESOLVED"
            alert.resolved_at = datetime.now(timezone.utc)
            if alert.created_at:
                alert.resolution_time = int((alert.resolved_at - alert.created_at).total_seconds())
            processed += 1
            continue
        if alert:
            processed += 1
            continue
        alert_type = str(labels.get("alertname") or "ALERTMANAGER_ALERT")
        severity = str(labels.get("severity") or "INFO").upper()
        alert = Alert(
            alert_id=alert_id,
            scan_id=labels.get("scan_id"),
            project_name=str(labels.get("project") or labels.get("project_name") or "SecureGate AI"),
            repository=labels.get("repository"),
            branch=labels.get("branch"),
            severity=severity,
            alert_type=alert_type,
            status="OPEN",
            notification_channels=_channels_for_severity(severity),
            description=str(annotations.get("description") or annotations.get("summary") or alert_type),
            recommendation=str(annotations.get("recommendation") or _recommendation_for_alert_type(alert_type)),
            runbook_url=str(annotations.get("runbook_url") or RUNBOOK_URL.format(alert_type=alert_type.lower().replace("_", "-"))),
            escalation_level=0,
            escalation_history=[],
        )
        db.add(alert)
        db.flush()
        alert.notification_channels = channels_for_alert(db, alert, severity)
        notifications = send_alert_notifications(db, alert, "Alertmanager")
        delivered += len(notifications)
        processed += 1
    db.commit()
    return {"status": "received", "processed_alerts": processed, "notifications": delivered}
