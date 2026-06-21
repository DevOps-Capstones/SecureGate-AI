const projects = [
  { name: "Payment API", repository: "https://github.com/example/payment-api", scans: 12, status: "Observed" },
  { name: "Customer Portal", repository: "https://github.com/example/customer-portal", scans: 8, status: "Observed" },
  { name: "Data Worker", repository: "https://github.com/example/data-worker", scans: 5, status: "Observed" }
];

export function Projects() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Projects</p>
          <h1>Application inventory</h1>
        </div>
      </header>
      <div className="project-grid">
        {projects.map((project) => (
          <article className="item-card" key={project.name}>
            <div>
              <h2>{project.name}</h2>
              <p>{project.repository}</p>
            </div>
            <div className="card-meta">
              <span>{project.scans} mock scans</span>
              <strong>{project.status}</strong>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
