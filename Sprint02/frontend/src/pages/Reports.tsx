export function Reports() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Reports</p>
          <h1>Report ingestion endpoints</h1>
        </div>
      </header>
      <div className="section-band">
        <div className="summary-grid">
          <span>GitLeaks</span>
          <strong>POST /api/v1/scans/:scanId/gitleaks</strong>
          <span>Trivy FS</span>
          <strong>POST /api/v1/scans/:scanId/trivy-fs</strong>
          <span>Trivy Image</span>
          <strong>POST /api/v1/scans/:scanId/trivy-image</strong>
          <span>SonarQube</span>
          <strong>POST /api/v1/scans/:scanId/sonarqube</strong>
        </div>
      </div>
    </section>
  );
}
