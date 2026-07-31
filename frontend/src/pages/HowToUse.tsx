import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, FileCode2, FolderPlus, KeyRound, PlayCircle, Route, Settings, UploadCloud } from "lucide-react";

const steps = [
  { icon: FolderPlus, title: "Register A Project", text: "Create one SecureGate AI project for one GitHub repository. The project ID is generated automatically." },
  { icon: Settings, title: "Configure Secrets", text: "Add SecureGate API URL, API key, SonarCloud, Slack, email, Docker Hub, and optional Jenkins values in your CI/CD secret store." },
  { icon: FileCode2, title: "Add A Pipeline Manifest", text: "Open the Pipeline Manifest Library, choose GitHub Actions, Jenkins, GitLab CI, or generic cURL, then commit the selected manifest into the repository you want to scan." },
  { icon: PlayCircle, title: "Run The Scan", text: "Push to the configured branch or run the CI job manually. GitLeaks, Semgrep, Trivy, SonarQube, unit tests, and image scanning run in the pipeline." },
  { icon: UploadCloud, title: "Upload Reports", text: "The pipeline sends each tool report to SecureGate AI, where findings are normalized and stored for dashboard history." },
  { icon: CheckCircle2, title: "Review The Decision", text: "Open the Dashboard, Scan Details, or Reports pages to review score, approval status, findings, and downloadable reports." },
];

export function HowToUse() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">User Guide</p>
          <h1>How To Use SecureGate-AI</h1>
        </div>
        <Link className="status-pill" to="/projects">Register A Project</Link>
      </header>

      <div className="section-band guide-panel scan-modern-card user-guide-card">
        <div className="scan-card-header">
          <span className="scan-card-icon"><Route size={22} /></span>
          <div>
            <h2>End-To-End Scan Flow</h2>
            <p>Follow these steps to connect a repository and start receiving security reports.</p>
          </div>
          <span className="scan-card-count">{steps.length} Steps</span>
        </div>
        <div className="help-steps">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <article className="help-step" key={step.title}>
                <div className="help-step-icon"><Icon size={20} /></div>
                <div>
                  <span>Step {index + 1}</span>
                  <strong>{step.title}</strong>
                  <p>{step.text}</p>
                </div>
              </article>
            );
          })}
        </div>
      </div>



      <div className="section-band api-key-guide scan-modern-card user-guide-card">
        <div className="scan-card-header">
          <span className="scan-card-icon"><KeyRound size={22} /></span>
          <div>
            <h2>Generate A SecureGate API Key</h2>
            <p>Use the same key in SecureGate AI and in your CI/CD secret store.</p>
          </div>
          <span className="scan-card-count">3 Actions</span>
        </div>
        <div className="api-key-grid">
          <div>
            <strong>1. Generate The Key</strong>
            <pre><code>openssl rand -hex 32</code></pre>
            <p className="muted">Alternative: run <code>python3 -c "import secrets; print(secrets.token_urlsafe(32))"</code>.</p>
          </div>
          <div>
            <strong>2. Save It In SecureGate AI</strong>
            <pre><code>SECUREGATE_API_KEY=your_generated_key_here</code></pre>
            <p className="muted">Place it in your SecureGate AI <code>.env</code>, then restart the backend container.</p>
          </div>
          <div>
            <strong>3. Save It In CI/CD</strong>
            <pre><code>SECUREGATE_API_KEY=your_generated_key_here</code></pre>
            <p className="muted">Add it as a GitHub Actions secret, Jenkins credential, GitLab CI variable, or your runner's equivalent secret.</p>
          </div>
        </div>
      </div>

      <div className="dashboard-grid guide-path-grid">
        <div className="section-band scan-modern-card guide-path-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><FileCode2 size={22} /></span>
            <div><h2>GitHub Actions Path</h2><p>Run security checks on every push or pull request before images are prepared.</p></div>
          </div>
          <Link className="inline-action" to="/manifests">View GitHub Manifest <ArrowRight size={15} /></Link>
        </div>
        <div className="section-band scan-modern-card guide-path-card">
          <div className="scan-card-header">
            <span className="scan-card-icon"><Settings size={22} /></span>
            <div><h2>Jenkins Path</h2><p>Use Jenkins when your release process controls image publishing and deployment checks.</p></div>
          </div>
          <Link className="inline-action" to="/manifests">View Jenkinsfile <ArrowRight size={15} /></Link>
        </div>
      </div>
    </section>
  );
}
