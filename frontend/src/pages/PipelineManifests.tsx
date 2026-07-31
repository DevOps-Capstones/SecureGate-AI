import { useState } from "react";
import { CalendarClock, Check, Copy, FileCode2, Github, Gitlab, Settings2, SquareTerminal } from "lucide-react";

const manifests = [
  {
    name: "GitHub Actions",
    file: ".github/workflows/securegate.yml",
    description: "Use this when GitHub Actions should scan every branch push and upload reports to SecureGate AI.",
    code: "name: SecureGate AI Security Gate\n\non:\n  push:\n    branches:\n      - \"**\"\n  workflow_dispatch:\n\njobs:\n  securegate-security-check:\n    runs-on: ubuntu-latest\n\n    env:\n      SECUREGATE_URL: ${{ secrets.SECUREGATE_URL }}\n      SECUREGATE_API_KEY: ${{ secrets.SECUREGATE_API_KEY }}\n      SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}\n      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}\n      SONAR_PROJECT_KEY: ${{ secrets.SONAR_PROJECT_KEY }}\n      SONAR_ORGANIZATION: ${{ secrets.SONAR_ORGANIZATION }}\n      DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}\n      DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}\n      PROJECT_NAME: ${{ github.event.repository.name }}\n      REPOSITORY_URL: ${{ github.server_url }}/${{ github.repository }}\n      BRANCH_NAME: ${{ github.ref_name }}\n      PIPELINE_RUN_ID: ${{ github.run_id }}\n      REPOSITORY_OWNER: ${{ github.repository_owner }}\n\n    steps:\n      - name: Checkout repository\n        uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd\n\n      - name: Detect current commit SHA\n        run: |\n          CURRENT_COMMIT_SHA=$(git rev-parse HEAD)\n          echo \"COMMIT_SHA=$CURRENT_COMMIT_SHA\" >> \"$GITHUB_ENV\"\n          echo \"Current commit SHA: $CURRENT_COMMIT_SHA\"\n\n      - name: Setup Node.js 24\n        uses: actions/setup-node@a0853c24544627f65ddf259abe73b1d18a591444\n        with:\n          node-version: \"24\"\n\n      - name: Validate SecureGate AI URL\n        run: |\n          if [ -z \"$SECUREGATE_URL\" ]; then\n            echo \"SECUREGATE_URL GitHub secret is missing.\"\n            exit 1\n          fi\n\n          if echo \"$SECUREGATE_URL\" | grep -Eq '\\[|\\]|\\(|\\)| '; then\n            echo \"SECUREGATE_URL is malformed.\"\n            echo \"Save it as a plain URL only, for example: https://citric-pliable-baggie.ngrok-free.dev\"\n            echo \"Do not use Markdown format like [https://...](https://...).\"\n            exit 1\n          fi\n\n          case \"$SECUREGATE_URL\" in\n            http://*|https://*) ;;\n            *)\n              echo \"SECUREGATE_URL must start with http:// or https://\"\n              exit 1\n              ;;\n          esac\n\n      - name: Start SecureGate AI scan\n        id: securegate_start\n        run: |\n          if echo \"$REPOSITORY_URL\" | grep -Eq '\\[|\\]|\\(|\\)'; then\n            echo \"REPOSITORY_URL is malformed. It must be a plain URL, not a Markdown link: $REPOSITORY_URL\"\n            exit 1\n          fi\n\n          START_PAYLOAD=$(jq -nc \\\n            --arg project_name \"$PROJECT_NAME\" \\\n            --arg repository_url \"$REPOSITORY_URL\" \\\n            --arg branch \"$BRANCH_NAME\" \\\n            --arg commit_sha \"$COMMIT_SHA\" \\\n            --arg pipeline_run_id \"$PIPELINE_RUN_ID\" \\\n            '{project_name:$project_name, repository_url:$repository_url, branch:$branch, commit_sha:$commit_sha, pipeline_run_id:$pipeline_run_id}')\n\n          echo \"SecureGate start payload:\"\n          echo \"$START_PAYLOAD\" | jq .\n\n          HTTP_STATUS=$(curl -sS -o securegate-start-response.json -w \"%{http_code}\" -X POST \"${SECUREGATE_URL%/}/api/v1/pipeline/start\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data \"$START_PAYLOAD\")\n\n          echo \"SecureGate start response status: $HTTP_STATUS\"\n          cat securegate-start-response.json\n          if [ \"$HTTP_STATUS\" -lt 200 ] || [ \"$HTTP_STATUS\" -ge 300 ]; then\n            echo \"SecureGate AI rejected the pipeline start request. Check the validation details above.\"\n            exit 1\n          fi\n\n          RESPONSE=$(cat securegate-start-response.json)\n          SCAN_ID=$(echo \"$RESPONSE\" | jq -r .scan_id)\n          if [ -z \"$SCAN_ID\" ] || [ \"$SCAN_ID\" = \"null\" ]; then\n            echo \"SecureGate AI did not return a scan_id\"\n            exit 1\n          fi\n          echo \"scan_id=$SCAN_ID\" >> \"$GITHUB_OUTPUT\"\n\n      - name: Run GitLeaks secret scan\n        run: |\n          docker run --rm \\\n            -v \"$PWD:/repo\" \\\n            zricethezav/gitleaks:latest detect \\\n            --source=/repo \\\n            --report-format=json \\\n            --report-path=/repo/gitleaks-report.json \\\n            --no-git || true\n\n          test -f gitleaks-report.json || echo \"[]\" > gitleaks-report.json\n\n      - name: Run Semgrep SAST scan\n        run: |\n          docker run --rm -v \"$PWD:/src\" returntocorp/semgrep:latest semgrep scan --config auto --json --output /src/semgrep-report.json /src || true\n          test -f semgrep-report.json || echo '{\"results\":[]}' > semgrep-report.json\n\n      - name: Run Trivy filesystem scan\n        uses: aquasecurity/trivy-action@df678dbccf677bc6937338d569ba0da18964a8cc\n        with:\n          scan-type: fs\n          scan-ref: .\n          format: json\n          output: trivy-fs-report.json\n          exit-code: 0\n\n      - name: Ensure Trivy filesystem report exists\n        run: |\n          test -f trivy-fs-report.json || echo '{\"Results\":[]}' > trivy-fs-report.json\n\n      - name: Run SonarQube scan\n        if: env.SONAR_HOST_URL != '' && env.SONAR_TOKEN != '' && env.SONAR_PROJECT_KEY != '' && env.SONAR_ORGANIZATION != ''\n        uses: SonarSource/sonarqube-scan-action@fd88b7d7ccbaefd23d8f36f73b59db7a3d246602 # nosemgrep: generic.secrets.security.detected-sonarqube-docs-api-key.detected-sonarqube-docs-api-key\n        env:\n          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}\n          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}\n        with:\n          args: >\n            -Dsonar.projectKey=${{ secrets.SONAR_PROJECT_KEY }}\n            -Dsonar.organization=${{ secrets.SONAR_ORGANIZATION }}\n            -Dsonar.sources=.\n            -Dsonar.exclusions=.github/workflows/securegate.yml,.github/workflows/securegate-ai.yml,SecureGate.Dockerfile\n\n      - name: Fetch SonarQube quality gate and issues\n        if: env.SONAR_HOST_URL != '' && env.SONAR_TOKEN != '' && env.SONAR_PROJECT_KEY != '' && env.SONAR_ORGANIZATION != ''\n        run: |\n          curl -sS \\\n            -H \"Authorization: Bearer $SONAR_TOKEN\" \\\n            \"$SONAR_HOST_URL/api/qualitygates/project_status?projectKey=$SONAR_PROJECT_KEY&organization=$SONAR_ORGANIZATION\" \\\n            -o sonar-gate.json\n\n          curl -sS \\\n            -H \"Authorization: Bearer $SONAR_TOKEN\" \\\n            \"$SONAR_HOST_URL/api/issues/search?componentKeys=$SONAR_PROJECT_KEY&organization=$SONAR_ORGANIZATION&resolved=false&ps=500\" \\\n            -o sonar-issues.json\n\n          jq -n \\\n            --slurpfile gate sonar-gate.json \\\n            --slurpfile issues sonar-issues.json \\\n            '{projectStatus: $gate[0].projectStatus, issues: ($issues[0].issues // [])}' \\\n            > sonarqube-report.json\n\n      - name: Create SonarQube placeholder report\n        if: env.SONAR_HOST_URL == '' || env.SONAR_TOKEN == '' || env.SONAR_PROJECT_KEY == '' || env.SONAR_ORGANIZATION == ''\n        run: |\n          cat > sonarqube-report.json <<EOF\n          {\n            \"projectStatus\": {\n              \"status\": \"UNKNOWN\"\n            },\n            \"issues\": []\n          }\n          EOF\n\n      - name: Detect and run unit tests\n        run: |\n          STATUS=\"SKIPPED\"\n          FRAMEWORK=\"none\"\n          REASON=\"No supported unit test configuration found\"\n          TOTAL=0\n          FAILED=0\n\n          if [ -f package.json ] && jq -e '.scripts.test and .scripts.test != \"\"' package.json >/dev/null 2>&1; then\n            FRAMEWORK=\"node\"\n            if npm test; then STATUS=\"PASSED\"; REASON=\"Node test script passed\"; else STATUS=\"FAILED\"; REASON=\"Node test script failed\"; FAILED=1; fi\n          elif [ -d tests ] || [ -f pytest.ini ] || grep -q \"pytest\" pyproject.toml setup.cfg 2>/dev/null; then\n            FRAMEWORK=\"pytest\"\n            python -m pip install --upgrade pip >/dev/null 2>&1 || true\n            if [ -f requirements.txt ]; then python -m pip install -r requirements.txt >/dev/null 2>&1 || true; fi\n            if [ -f requirements-dev.txt ]; then python -m pip install -r requirements-dev.txt >/dev/null 2>&1 || true; fi\n            python -m pip install pytest >/dev/null 2>&1 || true\n            if python -m pytest; then STATUS=\"PASSED\"; REASON=\"pytest passed\"; else STATUS=\"FAILED\"; REASON=\"pytest failed\"; FAILED=1; fi\n          fi\n\n          jq -n --arg status \"$STATUS\" --arg framework \"$FRAMEWORK\" --arg reason \"$REASON\" --argjson total \"$TOTAL\" --argjson failed \"$FAILED\" \\\n            '{status:$status, framework:$framework, reason:$reason, total:$total, failed:$failed}' > unit-tests-report.json\n\n      - name: Prepare Dockerfile when missing\n        id: dockerfile\n        run: |\n          if [ -f Dockerfile ]; then\n            echo \"Using repository Dockerfile.\"\n            echo \"path=Dockerfile\" >> \"$GITHUB_OUTPUT\"\n            exit 0\n          fi\n\n          echo \"No Dockerfile found. Creating SecureGate.Dockerfile for image scanning.\"\n          echo \"path=SecureGate.Dockerfile\" >> \"$GITHUB_OUTPUT\"\n\n          if [ -f package.json ]; then\n            cat > SecureGate.Dockerfile <<'EOF'\n          FROM node:24-alpine\n          WORKDIR /app\n          COPY package*.json ./\n          RUN npm install\n          COPY . .\n          CMD [\"npm\", \"start\"]\n          EOF\n          elif [ -f requirements.txt ]; then\n            cat > SecureGate.Dockerfile <<'EOF'\n          FROM python:3.12-alpine\n          WORKDIR /app\n          COPY requirements.txt ./\n          RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt\n          COPY . .\n          CMD [\"python\", \"app.py\"]\n          EOF\n          else\n            cat > SecureGate.Dockerfile <<'EOF'\n          FROM alpine:3.20\n          WORKDIR /app\n          COPY . .\n          CMD [\"sh\", \"-c\", \"ls -la /app && sleep 30\"]\n          EOF\n          fi\n\n      - name: Build Docker image for image vulnerability scan\n        id: image_build\n        run: |\n          IMAGE_NAMESPACE=\"${DOCKERHUB_USERNAME:-$REPOSITORY_OWNER}\"\n          IMAGE_REPOSITORY=\"$PROJECT_NAME\"\n          IMAGE_REPO=$(echo \"$IMAGE_NAMESPACE/$IMAGE_REPOSITORY\" | tr '[:upper:]' '[:lower:]')\n          SHORT_COMMIT_SHA=\"${COMMIT_SHA:0:8}\"\n          IMAGE_SHA_REF=\"$IMAGE_REPO:$SHORT_COMMIT_SHA\"\n          IMAGE_LATEST_REF=\"$IMAGE_REPO:latest\"\n\n          echo \"SecureGate AI Docker image path: $IMAGE_SHA_REF\"\n          echo \"Docker Hub repository will be created automatically on first push when credentials allow it: $IMAGE_REPO\"\n\n          docker build -f \"${{ steps.dockerfile.outputs.path }}\" -t \"$IMAGE_SHA_REF\" .\n          docker tag \"$IMAGE_SHA_REF\" \"$IMAGE_LATEST_REF\"\n\n          echo \"image_ref=$IMAGE_SHA_REF\" >> \"$GITHUB_OUTPUT\"\n          echo \"latest_ref=$IMAGE_LATEST_REF\" >> \"$GITHUB_OUTPUT\"\n          echo \"image_repo=$IMAGE_REPO\" >> \"$GITHUB_OUTPUT\"\n\n      - name: Check Docker Hub image tag freshness\n        id: image_freshness\n        if: env.DOCKERHUB_USERNAME != '' && env.DOCKERHUB_TOKEN != ''\n        env:\n          IMAGE_REF: ${{ steps.image_build.outputs.image_ref }}\n        run: |\n          if docker manifest inspect \"$IMAGE_REF\" >/dev/null 2>&1; then\n            echo \"changed=false\" >> \"$GITHUB_OUTPUT\"\n            echo \"Image already exists on Docker Hub for this short commit tag. Push will be skipped.\"\n          else\n            echo \"changed=true\" >> \"$GITHUB_OUTPUT\"\n            echo \"No existing Docker Hub image found for this short commit tag. Push is needed.\"\n          fi\n\n      - name: Run Trivy image scan\n        uses: aquasecurity/trivy-action@df678dbccf677bc6937338d569ba0da18964a8cc\n        with:\n          image-ref: ${{ steps.image_build.outputs.image_ref }}\n          format: json\n          output: trivy-image-report.json\n          exit-code: 0\n\n      - name: Ensure Trivy image report exists\n        run: |\n          test -f trivy-image-report.json || echo '{\"Results\":[]}' > trivy-image-report.json\n\n      - name: Upload GitLeaks report\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/gitleaks\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @gitleaks-report.json\n\n      - name: Upload Semgrep report\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/semgrep\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @semgrep-report.json\n\n      - name: Upload Trivy filesystem report\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/trivy-fs\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @trivy-fs-report.json\n\n      - name: Upload Trivy image report\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/trivy-image\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @trivy-image-report.json\n\n      - name: Upload SonarQube report\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/sonarqube\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @sonarqube-report.json\n\n      - name: Upload unit-test report\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/unit-tests\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @unit-tests-report.json\n\n      - name: Check SecureGate AI deployment decision\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          RESPONSE=$(curl -fsS \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID\")\n          echo \"$RESPONSE\"\n\n          DECISION=$(echo \"$RESPONSE\" | jq -r .deployment_decision)\n          SCORE=$(echo \"$RESPONSE\" | jq -r .security_score)\n          SONAR_GATE=$(echo \"$RESPONSE\" | jq -r .sonar_quality_gate)\n          FINDING_COUNTS=$(echo \"$RESPONSE\" | jq -c .finding_counts)\n          TOOL_STATUS=$(echo \"$RESPONSE\" | jq -c .tool_status)\n\n          echo \"SecureGate AI Decision: $DECISION\"\n          echo \"Security Score: $SCORE\"\n          echo \"SonarQube Gate: $SONAR_GATE\"\n          echo \"Finding Counts: $FINDING_COUNTS\"\n          echo \"Tool Status: $TOOL_STATUS\"\n\n          if [ \"$DECISION\" != \"APPROVED\" ]; then\n            echo \"SecureGate AI rejected this build.\"\n            if [ \"$SONAR_GATE\" != \"OK\" ] && [ \"$SONAR_GATE\" != \"UNKNOWN\" ]; then\n              echo \"Rejection reason: SonarQube quality gate is $SONAR_GATE. Check SonarCloud Quality Gate conditions.\"\n            fi\n            echo \"Top findings causing/relevant to rejection:\"\n            echo \"$RESPONSE\" | jq -r '.findings[:10][] | \"- [\\(.tool)] \\(.severity) \\(.title) in \\(.file // \"N/A\")\"'\n            exit 1\n          fi\n\n          echo \"SecureGate AI approved this build.\"\n          echo \"The code is safe to deploy the Docker image and push it to Docker Hub.\"\n          echo \"Repository, filesystem, image, secrets, and Sonar quality checks passed SecureGate AI policy.\"\n\n      - name: Push approved Docker image to Docker Hub when configured\n        if: env.DOCKERHUB_USERNAME != '' && env.DOCKERHUB_TOKEN != '' && steps.image_freshness.outputs.changed == 'true'\n        env:\n          IMAGE_REF: ${{ steps.image_build.outputs.image_ref }}\n          LATEST_REF: ${{ steps.image_build.outputs.latest_ref }}\n        run: |\n          echo \"$DOCKERHUB_TOKEN\" | docker login -u \"$DOCKERHUB_USERNAME\" --password-stdin\n          docker push \"$IMAGE_REF\"\n          docker push \"$LATEST_REF\"\n          echo \"Docker image pushed to Docker Hub:\"\n          echo \"  $IMAGE_REF\"\n          echo \"  $LATEST_REF\"\n\n      - name: Rescan pushed Docker image\n        if: env.DOCKERHUB_USERNAME != '' && env.DOCKERHUB_TOKEN != '' && steps.image_freshness.outputs.changed == 'true'\n        uses: aquasecurity/trivy-action@df678dbccf677bc6937338d569ba0da18964a8cc\n        with:\n          image-ref: ${{ steps.image_build.outputs.image_ref }}\n          format: json\n          output: trivy-image-report.json\n          exit-code: 0\n\n      - name: Upload post-push image rescan to SecureGate AI\n        if: env.DOCKERHUB_USERNAME != '' && env.DOCKERHUB_TOKEN != '' && steps.image_freshness.outputs.changed == 'true'\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n        run: |\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/scans/$SCAN_ID/trivy-image\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            --data-binary @trivy-image-report.json\n          echo \"Pushed Docker image was rescanned and SecureGate AI dashboard was updated.\"\n\n      - name: Docker Hub image unchanged\n        if: env.DOCKERHUB_USERNAME != '' && env.DOCKERHUB_TOKEN != '' && steps.image_freshness.outputs.changed == 'false'\n        run: |\n          echo \"SecureGate AI approved this build, but Docker Hub push was skipped because this commit image already exists.\"\n\n      - name: Docker Hub push not configured\n        if: env.DOCKERHUB_USERNAME == '' || env.DOCKERHUB_TOKEN == ''\n        run: |\n          echo \"SecureGate AI approved this build, but Docker Hub push was skipped because DOCKERHUB_USERNAME or DOCKERHUB_TOKEN is not configured.\"\n\n      - name: Complete SecureGate AI pipeline\n        if: always() && steps.securegate_start.outputs.scan_id != ''\n        env:\n          SCAN_ID: ${{ steps.securegate_start.outputs.scan_id }}\n          JOB_STATUS: ${{ job.status }}\n        run: |\n          STATUS=\"SUCCESS\"\n\n          if [ \"$JOB_STATUS\" != \"success\" ]; then\n            STATUS=\"FAILED\"\n          fi\n\n          curl -fsS -X POST \"${SECUREGATE_URL%/}/api/v1/pipeline/complete\" \\\n            -H \"Authorization: Bearer $SECUREGATE_API_KEY\" \\\n            -H \"Content-Type: application/json\" \\\n            -d \"{\n              \\\"scan_id\\\":\\\"$SCAN_ID\\\",\n              \\\"status\\\":\\\"$STATUS\\\"\n            }\"\n"
  },
  {
    name: "Jenkins",
    file: "Jenkinsfile",
    description: "Use this when Jenkins is the main CI/CD runner for scans, image build, image scan, and optional Docker Hub push.",
    code: `pipeline {
  agent any
  environment {
    SECUREGATE_URL = credentials('securegate-url')
    SECUREGATE_API_KEY = credentials('securegate-api-key')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Start Scan') {
      steps {
        sh '''RESPONSE=$(curl -fsS -X POST "\${SECUREGATE_URL%/}/api/v1/pipeline/start" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" -d "{\"project_name\":\"$JOB_NAME\",\"repository_url\":\"$GIT_URL\",\"branch\":\"$BRANCH_NAME\",\"commit_sha\":\"$GIT_COMMIT\",\"pipeline_run_id\":\"$BUILD_NUMBER\"}")
echo "$RESPONSE" | jq -r .scan_id > .securegate-scan-id'''
      }
    }
    stage('Security Scans') {
      steps {
        sh 'gitleaks detect --report-format json --report-path gitleaks-report.json || true'
        sh 'semgrep scan --config auto --json --output semgrep-report.json || true'
        sh 'trivy fs --format json --output trivy-fs-report.json . || true'
        sh 'echo '{"status":"SKIPPED","framework":"auto","reason":"No unit-test command configured in this sample","total":0,"failed":0}' > unit-tests-report.json'
      }
    }
    stage('Upload Reports') {
      steps {
        sh '''SCAN_ID=$(cat .securegate-scan-id)
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/gitleaks" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @gitleaks-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/semgrep" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @semgrep-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/trivy-fs" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @trivy-fs-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/unit-tests" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @unit-tests-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/pipeline/complete" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" -d "{\"scan_id\":\"$SCAN_ID\",\"status\":\"SUCCESS\"}"'''
      }
    }
  }
}`
  },
  {
    name: "GitLab CI",
    file: ".gitlab-ci.yml",
    description: "Use this when GitLab CI should send scan reports into SecureGate AI.",
    code: `stages: [security]

securegate_security:
  image: alpine:3.20
  stage: security
  before_script:
    - apk add --no-cache curl jq git
  script:
    - |
      RESPONSE=$(curl -fsS -X POST "\${SECUREGATE_URL%/}/api/v1/pipeline/start" \
        -H "Authorization: Bearer $SECUREGATE_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"project_name\":\"$CI_PROJECT_NAME\",\"repository_url\":\"$CI_PROJECT_URL\",\"branch\":\"$CI_COMMIT_BRANCH\",\"commit_sha\":\"$CI_COMMIT_SHA\",\"pipeline_run_id\":\"$CI_PIPELINE_ID\"}")
      SCAN_ID=$(echo "$RESPONSE" | jq -r .scan_id)
      curl -fsS -X POST "$SECUREGATE_URL/api/v1/pipeline/complete" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" -d "{\"scan_id\":\"$SCAN_ID\",\"status\":\"SUCCESS\"}"`
  },
  {
    name: "Generic CI/CD cURL",
    file: "securegate-pipeline.sh",
    description: "Use this contract from any runner that can execute shell and upload JSON reports.",
    code: `#!/usr/bin/env bash
set -euo pipefail

RESPONSE=$(curl -fsS -X POST "\${SECUREGATE_URL%/}/api/v1/pipeline/start" \
  -H "Authorization: Bearer $SECUREGATE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"project_name\":\"$PROJECT_NAME\",\"repository_url\":\"$REPOSITORY_URL\",\"branch\":\"$BRANCH\",\"commit_sha\":\"$COMMIT_SHA\",\"pipeline_run_id\":\"$PIPELINE_RUN_ID\"}")
SCAN_ID=$(echo "$RESPONSE" | jq -r .scan_id)

curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/gitleaks" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @gitleaks-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/semgrep" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @semgrep-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/trivy-fs" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @trivy-fs-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/sonarqube" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @sonarqube-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/scans/$SCAN_ID/unit-tests" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" --data-binary @unit-tests-report.json || true
curl -fsS -X POST "$SECUREGATE_URL/api/v1/pipeline/complete" -H "Authorization: Bearer $SECUREGATE_API_KEY" -H "Content-Type: application/json" -d "{\"scan_id\":\"$SCAN_ID\",\"status\":\"SUCCESS\"}"`
  },
  {
    name: "Scheduled Summaries",
    file: ".github/workflows/securegate-summary.yml",
    description: "Use this to automatically send daily and weekly SecureGate AI summary alerts with GitHub Actions cron.",
    code: `name: SecureGate AI Scheduled Summaries

on:
  schedule:
    - cron: "0 18 * * *"
    - cron: "30 18 * * 1"
  workflow_dispatch:
    inputs:
      period:
        description: "Summary period to send"
        required: true
        default: "daily"
        type: choice
        options: [daily, weekly]

jobs:
  daily-summary:
    if: github.event_name == 'workflow_dispatch' && inputs.period == 'daily' || github.event_name == 'schedule' && github.event.schedule == '0 18 * * *'
    runs-on: ubuntu-latest
    steps:
      - name: Send SecureGate AI daily summary
        env:
          SECUREGATE_URL: \${{ secrets.SECUREGATE_URL }}
          SECUREGATE_API_KEY: \${{ secrets.SECUREGATE_API_KEY }}
        run: |
          curl -fsS -X POST "\${SECUREGATE_URL%/}/api/v1/notifications/summary/daily" -H "Authorization: Bearer $SECUREGATE_API_KEY"

  weekly-summary:
    if: github.event_name == 'workflow_dispatch' && inputs.period == 'weekly' || github.event_name == 'schedule' && github.event.schedule == '30 18 * * 1'
    runs-on: ubuntu-latest
    steps:
      - name: Send SecureGate AI weekly summary
        env:
          SECUREGATE_URL: \${{ secrets.SECUREGATE_URL }}
          SECUREGATE_API_KEY: \${{ secrets.SECUREGATE_API_KEY }}
        run: |
          curl -fsS -X POST "\${SECUREGATE_URL%/}/api/v1/notifications/summary/weekly" -H "Authorization: Bearer $SECUREGATE_API_KEY"`
  },
];

function manifestVisual(name: string) {
  if (name === "GitHub Actions") return <Github size={24} />;
  if (name === "GitLab CI") return <Gitlab size={24} />;
  if (name === "Jenkins") return <span className="brand-letter jenkins-brand">J</span>;
  if (name === "Generic CI/CD cURL") return <SquareTerminal size={24} />;
  if (name === "Scheduled Summaries") return <CalendarClock size={24} />;
  return <FileCode2 size={24} />;
}

export function PipelineManifests() {
  const [copiedManifest, setCopiedManifest] = useState<string | null>(null);

  const copyManifest = async (manifestName: string, code: string) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = code;
        textArea.setAttribute("readonly", "");
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      setCopiedManifest(manifestName);
      window.setTimeout(() => setCopiedManifest(null), 1800);
    } catch {
      setCopiedManifest(null);
    }
  };

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Pipeline Library</p>
          <h1>SecureGate-AI Pipeline Manifests</h1>
        </div>
      </header>
      <div className="section-band guide-panel scan-modern-card manifests-modern-card">
        <div className="scan-card-header">
          <span className="scan-card-icon"><Settings2 size={22} /></span>
          <div>
            <h2>Choose Your CI/CD Runner</h2>
            <p>Select the manifest that matches your pipeline platform, then add the required secrets before running it.</p>
          </div>
          <span className="scan-card-count">{manifests.length} Manifests</span>
        </div>
        <div className="manifest-grid modern-manifest-grid">
          {manifests.map((manifest) => {
            const isCopied = copiedManifest === manifest.name;
            return (
              <details className="manifest-card modern-manifest-card" key={manifest.name}>
                <summary>
                  <span className="manifest-platform-icon">{manifestVisual(manifest.name)}</span>
                  <span className="manifest-summary-copy">
                    <strong>{manifest.name}</strong>
                    <small>{manifest.description}</small>
                  </span>
                  <code>{manifest.file}</code>
                </summary>
                <div className="manifest-description-row">
                  <span>{manifest.description}</span>
                </div>
                <div className="manifest-code-panel">
                  <button
                    type="button"
                    className={`copy-snippet-button${isCopied ? " is-copied" : ""}`}
                    onClick={() => copyManifest(manifest.name, manifest.code)}
                    aria-label={`Copy ${manifest.name} manifest`}
                    title={`Copy ${manifest.name} manifest`}
                  >
                    {isCopied ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                  <pre><code>{manifest.code}</code></pre>
                </div>
              </details>
            );
          })}
        </div>
      </div>
    </section>
  );
}
