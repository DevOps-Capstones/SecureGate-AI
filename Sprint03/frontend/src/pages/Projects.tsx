import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { createScan } from "../api/scans";
import type { CreateScanResponse } from "../types/scans";

export function Projects() {
  const [projectName, setProjectName] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [commitSha, setCommitSha] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CreateScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setResult(null);
    setError(null);

    try {
      const scan = await createScan({
        project_name: projectName,
        repository_url: repositoryUrl,
        branch,
        commit_sha: commitSha
      });
      setResult(scan);
      setProjectName("");
      setRepositoryUrl("");
      setBranch("main");
      setCommitSha("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit scan metadata.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Projects</p>
          <h1>Register CI scan metadata</h1>
        </div>
      </header>

      <form className="scan-form" onSubmit={handleSubmit}>
        <div className="form-grid">
          <label>
            Project Name
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="payment-service" required />
          </label>
          <label>
            Repository URL
            <input type="url" value={repositoryUrl} onChange={(event) => setRepositoryUrl(event.target.value)} placeholder="https://github.com/company/payment-service" required />
          </label>
          <label>
            Branch
            <input value={branch} onChange={(event) => setBranch(event.target.value)} placeholder="main" required />
          </label>
          <label>
            Commit SHA
            <input value={commitSha} onChange={(event) => setCommitSha(event.target.value)} placeholder="abc123" required />
          </label>
        </div>
        <button type="submit" disabled={submitting}>{submitting ? "Submitting..." : "Create Scan Record"}</button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <article className="section-band">
          <div className="section-title">
            <h2>Scan metadata received</h2>
            <Link to={`/scans/${result.scan_id}`}>View details</Link>
          </div>
          <div className="summary-grid">
            <span>Scan ID</span>
            <strong>{result.scan_id}</strong>
            <span>Status</span>
            <strong className={`status-text ${result.status.toLowerCase()}`}>{result.status}</strong>
          </div>
        </article>
      )}
    </section>
  );
}
