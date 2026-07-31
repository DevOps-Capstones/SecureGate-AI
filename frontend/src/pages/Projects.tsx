import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ExternalLink, FileText, Folder, FolderPlus, ShieldCheck, Trash2 } from "lucide-react";
import { createProject, deleteProject, listProjects } from "../api/scans";
import type { ProjectSummary } from "../types/scans";

function repositoryHref(repositoryUrl: string) {
  return /^https?:\/\//i.test(repositoryUrl) ? repositoryUrl : `https://${repositoryUrl}`;
}

export function Projects() {
  const [projectName, setProjectName] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ProjectSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  function loadProjects() {
    listProjects().then(setProjects).catch((err: Error) => setError(err.message));
  }

  useEffect(() => { loadProjects(); }, []);

  function cleanError(message: string) {
    try {
      const parsed = JSON.parse(message);
      return parsed.detail ?? message;
    } catch {
      return message;
    }
  }

  async function handleDelete(project: ProjectSummary) {
    const typed = window.prompt(`Type DELETE ${project.project_key} to permanently delete ${project.name}.`);
    if (typed !== `DELETE ${project.project_key}`) return;
    setError(null);
    try {
      await deleteProject(project.project_key);
      if (result?.project_key === project.project_key) setResult(null);
      loadProjects();
    } catch (err) {
      setError(err instanceof Error ? cleanError(err.message) : "Unable to delete project.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setResult(null);
    setError(null);
    try {
      const project = await createProject({ name: projectName, repository_url: repositoryUrl });
      setResult(project);
      setProjectName("");
      setRepositoryUrl("");
      loadProjects();
    } catch (err) {
      setError(err instanceof Error ? cleanError(err.message) : "Unable to register project.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Project Registry</p>
          <h1>Register Your Project</h1>
        </div>
        <span className="status-pill">One project per GitHub repository</span>
      </header>

      <form className="scan-form" onSubmit={handleSubmit}>
        <div className="form-grid two-col-form">
          <label>
            Project Name
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="securegate-demo-app" required />
          </label>
          <label>
            GitHub Repository URL
            <input type="url" value={repositoryUrl} onChange={(event) => setRepositoryUrl(event.target.value)} placeholder="https://github.com/company/securegate-demo-app" required />
          </label>
        </div>
        <button type="submit" disabled={submitting}><FolderPlus size={17} /> {submitting ? "Registering..." : "Register A Project"}</button>
      </form>

      {error && <p className="error-text form-error-text">{error}</p>}

      <article className="section-band guide-panel scan-modern-card project-pipeline-card">
        <div className="scan-card-header">
          <span className="scan-card-icon"><FileText size={22} /></span>
          <div>
            <h2>Add SecureGate AI To Your Pipeline</h2>
            <p>Choose GitHub Actions, Jenkins, GitLab, or generic CI/CD from the manifest library.</p>
          </div>
          <Link className="scan-card-action" to="/manifests">Open Manifest Library <ArrowRight size={16} /></Link>
        </div>
        <p className="muted">After registering a project, choose one runner from the dedicated manifest library. GitHub Actions, Jenkins, GitLab or generic CI/CD.</p>
      </article>

      {result && (
        <article className="section-band">
          <div className="section-title">
            <h2>Project registered</h2>
            <Link to={`/projects/${result.project_key}`}>Open project health</Link>
          </div>
          <div className="summary-grid">
            <span>Project ID</span><strong>{result.project_key}</strong>
            <span>Name</span><strong>{result.name}</strong>
            <span>Repository</span><strong className="truncate"><a className="repo-link" href={repositoryHref(result.repository_url)} target="_blank" rel="noreferrer">{result.repository_url}</a></strong>
          </div>
        </article>
      )}

      <div className="section-band scan-modern-card projects-modern-card">
        <div className="scan-card-header">
          <span className="scan-card-icon"><Folder size={22} /></span>
          <div>
            <h2>Registered Projects</h2>
            <p>One registered project is allowed for each GitHub repository URL.</p>
          </div>
          <span className="scan-card-count">{projects.length} Projects</span>
        </div>
        {projects.length === 0 ? <p className="muted">No projects registered yet.</p> : <div className="project-list modern-project-list">
          {projects.map((project) => (
            <div className="project-row project-row-actions modern-project-row" key={project.project_key}>
              <Link className="project-main-link modern-project-main-link" to={`/projects/${project.project_key}`}>
                <span className="project-avatar"><ShieldCheck size={19} /></span>
                <div className="project-copy"><strong>{project.name}</strong><span>{project.project_key}</span></div>
                <span className="truncate project-repo-url">{project.repository_url}</span>
                <span className="project-open-icon"><ExternalLink size={17} /></span>
              </Link>
              <button className="icon-danger" type="button" title="Delete Project" onClick={() => handleDelete(project)}><Trash2 size={16} /></button>
            </div>
          ))}
        </div>}
      </div>
    </section>
  );
}
