import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Bot, MessageCircle, Send, X } from "lucide-react";
import { askAiAssistant, getDashboardSummary, getProject, getScan } from "../api/scans";

type Message = { role: "user" | "assistant"; text: string };

const faqQuestions = [
  "Why did the latest scan fail?",
  "What should I fix first?",
  "Is this repository ready for deployment?",
];

export function AIAssistant() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", text: "Ask me about the current SecureGate scan. I use the selected scan context when you are on a scan or project page." }]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    const applyContext = (nextScanId: string | null, nextProjectName: string | null) => {
      if (!active) return;
      setScanId(nextScanId);
      setProjectName(nextProjectName);
    };

    const scanMatch = location.pathname.match(/^\/scans\/([^/]+)/);
    if (scanMatch) {
      const currentScanId = decodeURIComponent(scanMatch[1]);
      applyContext(currentScanId, "Scan context");
      getScan(currentScanId)
        .then((scan) => applyContext(scan.scan_id, scan.project_name))
        .catch(() => applyContext(currentScanId, "Scan context"));
      return () => { active = false; };
    }

    const projectMatch = location.pathname.match(/^\/projects\/([^/]+)/);
    if (projectMatch) {
      const projectKey = decodeURIComponent(projectMatch[1]);
      getProject(projectKey)
        .then((project) => applyContext(project.latest_scan?.scan_id ?? null, project.name))
        .catch(() => applyContext(null, null));
      return () => { active = false; };
    }

    getDashboardSummary()
      .then((summary) => {
        const latest = summary.recent_scans[0];
        applyContext(latest?.scan_id ?? null, latest?.project_name ?? summary.active_project_name ?? null);
      })
      .catch(() => applyContext(null, null));
    return () => { active = false; };
  }, [location.pathname]);

  useEffect(() => {
    if (open) panelRef.current?.scrollTo({ top: panelRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open]);

  useEffect(() => {
    const openAssistant = () => setOpen(true);
    window.addEventListener("securegate:open-ai-assistant", openAssistant);
    return () => window.removeEventListener("securegate:open-ai-assistant", openAssistant);
  }, []);

  async function send(value: string) {
    const trimmed = value.trim();
    if (!trimmed || loading) return;
    if (!scanId) {
      setMessages((current) => [...current, { role: "assistant", text: "No scan context is available yet. Register a project, run a scan, then ask me about the results." }]);
      return;
    }
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setQuestion("");
    setLoading(true);
    try {
      const response = await askAiAssistant(scanId, trimmed);
      setMessages((current) => [...current, { role: "assistant", text: response.answer }]);
    } catch (error) {
      setMessages((current) => [...current, { role: "assistant", text: error instanceof Error ? error.message : "AI assistant is unavailable." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`ai-assistant-shell ${open ? "open" : ""}`}>
      {!open && <button className="ai-assistant-toggle" type="button" onClick={() => setOpen(true)} aria-label="Open AI assistant">
        <MessageCircle size={18} /><span>Ask AI Assistant</span>
      </button>}
      {open && <aside className="ai-assistant-panel" aria-label="SecureGate AI assistant">
        <header>
          <span><Bot size={20} /></span>
          <div><strong>SecureGate AI Assistant</strong><small>{projectName ? `Latest scan: ${projectName}` : "Waiting for scan context"}</small></div>
          <button className="ai-assistant-close" type="button" onClick={() => setOpen(false)} aria-label="Close AI assistant"><X size={17} /></button>
        </header>
        <div className="ai-faq-row">
          {faqQuestions.map((item) => <button key={item} type="button" onClick={() => send(item)} disabled={!scanId || loading}>{item}</button>)}
        </div>
        <div className="ai-message-list" ref={panelRef}>
          {messages.map((message, index) => <div className={`ai-message ${message.role}`} key={`${message.role}-${index}`}>{message.text}</div>)}
          {loading && <div className="ai-message assistant">Thinking through the latest scan...</div>}
        </div>
        <form onSubmit={(event) => { event.preventDefault(); send(question); }}>
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={scanId ? "Ask about this scan..." : "Run a scan first"} disabled={loading} />
          <button type="submit" disabled={loading || !question.trim()} aria-label="Send AI question"><Send size={16} /></button>
        </form>
      </aside>}
    </div>
  );
}
