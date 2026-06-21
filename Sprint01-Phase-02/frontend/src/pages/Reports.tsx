const reports = [
  { id: "SG-RPT-001", type: "Trivy image", path: "reports/mock/python-3-7.html", created: "Sprint 1 placeholder" },
  { id: "SG-RPT-002", type: "Trivy filesystem", path: "reports/mock/workspace.html", created: "Sprint 1 placeholder" },
  { id: "SG-RPT-003", type: "GitLeaks", path: "reports/mock/secrets.html", created: "Sprint 1 placeholder" }
];

export function Reports() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Reports</p>
          <h1>Report placeholders</h1>
        </div>
      </header>
      <div className="section-band">
        <div className="table">
          <div className="table-row table-head">
            <span>Report ID</span>
            <span>Type</span>
            <span>Path</span>
            <span>Created</span>
          </div>
          {reports.map((report) => (
            <div className="table-row" key={report.id}>
              <span>{report.id}</span>
              <span>{report.type}</span>
              <span>{report.path}</span>
              <span>{report.created}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
