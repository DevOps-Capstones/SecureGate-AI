# Sprint 6 - Local AI Assistant And Remediation Engine

Sprint 6 completes SecureGate AI by adding local AI-assisted security guidance on top of the existing DevSecOps decision platform.

SecureGate AI still keeps the locked architecture:

- CI/CD runs the scanners.
- SecureGate AI receives reports.
- SecureGate AI normalizes findings.
- SecureGate AI calculates score and decision.
- SecureGate AI generates reports, dashboards, notifications, alerts, and AI remediation guidance.

## Sprint 6 Goal

Transform SecureGate AI from a security reporting dashboard into an AI-assisted remediation workspace.

Sprint 6 adds:

- Local Ollama/Gemma integration
- Ask AI Assistant widget
- AI Summary on dashboard and project pages
- AI Security Summary PDF
- AI Remediation Plan JSON and PDF
- P1-P7 remediation priority model
- Estimated fix time
- Production readiness checklist
- Rule-based fallback when Ollama is unavailable
- Audit logs for AI actions

## Why This Matters

Security tools often tell developers what failed, but not what to do next. Sprint 6 closes that gap by translating scan findings into practical remediation guidance.

The developer can ask:

- Why did the latest scan fail?
- What should I fix first?
- What files are affected?
- Is the project ready for deployment?
- How long might remediation take?

SecureGate AI answers using stored scan data and local AI guidance.

## AI Architecture

```text
Scan reports stored in PostgreSQL and storage/
        |
Scan context builder
        |
Deterministic security summary and remediation rules
        |
Optional Ollama/Gemma prompt
        |
AI Summary JSON + PDF
AI Remediation Plan JSON + PDF
AI Assistant chat response
        |
Audit log entry
```

Ollama improves explanation quality, but it is not required for the platform to work. If Ollama or Gemma is unavailable, SecureGate AI returns rule-based guidance.

## Setup Commands

Start all services:

```bash
cd /Users/saimausman/Desktop/securegate-ai
docker compose up -d --build
```

Pull the model once:

```bash
docker compose exec ollama ollama pull gemma3:4b
```

Check available models:

```bash
docker compose exec ollama ollama list
```

Restart backend after environment changes:

```bash
docker compose restart backend
```

View AI/Ollama logs:

```bash
docker compose logs -f ollama
docker compose logs -f backend
```

Run backend and frontend validation:

```bash
python3 -m compileall -q backend/app
cd frontend
npm run build
```

## Environment Variables

Add these to `securegate-ai/.env`:

```bash
AI_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=gemma3:4b
OLLAMA_TIMEOUT_SECONDS=300
```

Important related variables:

```bash
SECUREGATE_API_KEY=replace-with-a-long-token
PUBLIC_BACKEND_URL=http://localhost:8000
SECURITY_SCORE_THRESHOLD=80
BLOCK_HIGH_VULNERABILITIES=true
QUALITY_GATE_REQUIRED=true
SECRET_DETECTION_REQUIRED=true
```

## Sprint 6 API Endpoints

AI insight summary:

```bash
curl -fsS http://localhost:8000/api/v1/ai/scans/SCAN-ID/insights
```

Ask AI assistant:

```bash
curl -fsS -X POST http://localhost:8000/api/v1/ai/scans/SCAN-ID/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Why did the latest scan fail?"}'
```

Get remediation plan JSON:

```bash
curl -fsS http://localhost:8000/api/v1/ai/scans/SCAN-ID/remediation-plan
```

Download AI summary PDF:

```bash
curl -L http://localhost:8000/api/v1/ai/scans/SCAN-ID/summary-report/pdf -o ai-summary.pdf
```

Download AI remediation plan PDF:

```bash
curl -L http://localhost:8000/api/v1/ai/scans/SCAN-ID/remediation-plan/pdf -o ai-remediation-plan.pdf
```

Replace `SCAN-ID` with a real value such as `SCAN-20260705-0002`.

## Frontend Usage

Dashboard:

- Open `http://localhost:5173`
- Review AI Summary section.
- Click AI Summary PDF or AI Remediation PDF.
- Use Ask AI Assistant for scan questions.

Project page:

- Open `Projects`.
- Select a project.
- Review Security Summary, Findings, Pipeline Timeline, and AI Remediation Plan.
- Use `Ask AI` to open the assistant with project context.

Remediation Plan page:

- Open `http://localhost:5173/remediation-plan`
- Choose any completed scan/project.
- Review priority matrix, fix details, readiness checklist, and download PDF.

## P1-P7 Priority Logic

SecureGate AI uses priority levels to guide remediation order.

| Priority | Meaning | Fix Timing |
| --- | --- | --- |
| P1 | Emergency production blocker | Fix immediately before any deployment |
| P2 | Critical security blocker | Fix before release |
| P3 | Quality gate or policy blocker | Fix before release approval |
| P4 | Critical CVE or major dependency issue | Fix before production deployment |
| P5 | High vulnerability or high-risk finding | Fix quickly; deployment usually blocked by strict policy |
| P6 | Important security hygiene or code quality work | Fix soon to maintain project health |
| P7 | Medium/low technical debt or next-cycle remediation | Fix in next remediation cycle, still track until resolved |

Examples:

- GitLeaks secret finding: usually P1 or P2.
- Critical Trivy CVE: usually P2 or P4.
- Failed SonarQube quality gate: usually P3.
- High Semgrep finding: usually P5.
- Medium Semgrep issue such as Flask debug mode: often P7 when no higher blocker exists.

P7 does not mean safe to ignore. It means lower urgency compared with P1-P6.

## AI Remediation Plan Contents

The remediation plan includes:

- Project name
- Repository link
- Branch
- Scan ID
- Security score
- Deployment decision
- Overall priority
- Estimated fix time
- Severity counts
- Top actions
- Fix details
- Production readiness checklist
- Final recommendation

The PDF is intentionally concise so a developer can quickly understand what to fix.

## AI Summary Report Contents

The AI Summary PDF includes:

- Project metadata
- Repository link
- Branch
- Uploaded/generated time
- Security score
- Deployment decision
- AI readiness
- Overall risk
- Executive summary
- AI analysis without raw markdown symbols
- Top recommendations
- Estimated fix time

The project name is emphasized, and rejected decisions are highlighted in red.

## Fallback Behavior

If Ollama is unavailable:

- The dashboard still loads.
- The AI assistant still responds using stored scan data.
- AI reports still generate deterministic guidance.
- The app records audit logs showing fallback usage.

Common model setup fix:

```bash
docker compose exec ollama ollama pull gemma3:4b
docker compose restart backend
```

## Testing Commands

Backend compile:

```bash
python3 -m compileall -q backend/app
```

Frontend build:

```bash
cd frontend
npm run build
```

Health check:

```bash
curl -fsS http://localhost:8000/health
```

AI endpoint check:

```bash
curl -fsS http://localhost:8000/api/v1/ai/scans/SCAN-ID/insights
```

## Sprint 6 Deliverables

Completed:

- Ollama service in Docker Compose
- Gemma model configuration
- AI backend services
- AI API routes
- AI Assistant frontend widget
- AI Summary dashboard section
- AI Remediation Plan page
- AI Summary PDF export
- AI Remediation PDF export
- P1-P7 priority logic
- Rule-based fallback
- Audit logging
- Final project documentation

## Production Notes

For production:

- Use a dedicated AI model host if Ollama needs more CPU/GPU resources.
- Keep AI output advisory; security gate rules remain authoritative.
- Review generated remediation guidance before deployment.
- Protect report downloads behind authentication in a real enterprise deployment.
- Back up PostgreSQL and `storage/` reports.
