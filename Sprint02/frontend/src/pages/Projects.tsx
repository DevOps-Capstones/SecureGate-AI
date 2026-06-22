import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { createScan } from "../api/scans";
import type { CreateScanResponse } from "../types/scans";

export function Projects() {
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CreateScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setResult(null);
    setError(null);

    try {
      const scan = await createScan(repositoryUrl);
      setResult(scan);
      setRepositoryUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit scan.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Projects</p>
          <h1>Submit repository scan</h1>
        </div>
      </header>

      <form className="scan-form" onSubmit={handleSubmit}>
        <label htmlFor="repository_url">Repository URL</label>
        <div className="form-row">
          <input
            id="repository_url"
            type="url"
            placeholder="https://github.com/org/project"
            value={repositoryUrl}
            onChange={(event) => setRepositoryUrl(event.target.value)}
            required
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Scanning..." : "Submit Scan"}
          </button>
        </div>
      </form>

      {error && <p className="error-text">{error}</p>}

      {result && (
        <article className="section-band">
          <div className="section-title">
            <h2>Scan submitted</h2>
            <Link to={`/scans/${result.scan_id}`}>View details</Link>
          </div>
          <div className="summary-grid">
            <span>Scan ID</span>
            <strong>{result.scan_id}</strong>
            <span>Status</span>
            <strong className={`status-text ${result.status.toLowerCase()}`}>{result.status}</strong>
            <span>Deployment</span>
            <strong>{result.deployment_approved ? "Approved" : "Blocked"}</strong>
            <span>Critical</span>
            <strong>{result.critical_count}</strong>
            <span>High</span>
            <strong>{result.high_count}</strong>
            <span>Secrets</span>
            <strong>{result.secrets_count}</strong>
          </div>
        </article>
      )}
    </section>
  );
}
