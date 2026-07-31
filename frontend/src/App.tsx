import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  AlertTriangle,
  BarChart3,
  FileText,
  FolderKanban,
  Wrench,
  HelpCircle,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Activity
} from "lucide-react";
import { Dashboard } from "./pages/Dashboard";
import { ProjectDetailsPage } from "./pages/ProjectDetails";
import { ProjectFindingsPage } from "./pages/ProjectFindings";
import { ProjectAnalyticsPage } from "./pages/ProjectAnalytics";
import { Projects } from "./pages/Projects";
import { Reports } from "./pages/Reports";
import { RemediationPlanPage } from "./pages/RemediationPlan";
import { ScanDetailsPage } from "./pages/ScanDetails";
import { SettingsPage } from "./pages/Settings";
import { HowToUse } from "./pages/HowToUse";
import { PipelineManifests } from "./pages/PipelineManifests";
import { Monitoring } from "./pages/Monitoring";
import { AlertsPage } from "./pages/Alerts";
import { SecurityAnalytics } from "./pages/SecurityAnalytics";
import { AIAssistant } from "./components/AIAssistant";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/remediation-plan", label: "Remediation Plan", icon: Wrench },
  { to: "/monitoring", label: "Monitoring", icon: Activity },
  { to: "/alerts", label: "Alerts", icon: AlertTriangle },
  { to: "/security-analytics", label: "Analytics", icon: BarChart3 },
  { to: "/how-to-use", label: "User Guide", icon: HelpCircle },
  { to: "/settings", label: "Settings", icon: Settings }
];

const footerContext = {
  "/": { text: "Dashboard overview", icon: BarChart3 },
  "/projects": { text: "Project registry", icon: FolderKanban },
  "/reports": { text: "Report history", icon: FileText },
  "/remediation-plan": { text: "Remediation work queue", icon: Wrench },
  "/monitoring": { text: "Security operations monitoring", icon: Activity },
  "/alerts": { text: "Alert history", icon: AlertTriangle },
  "/security-analytics": { text: "Historical analytics", icon: BarChart3 },
  "/how-to-use": { text: "User guide", icon: HelpCircle },
  "/manifests": { text: "Pipeline manifest library", icon: FileText },
  "/settings": { text: "Integration settings", icon: Settings },
};

function App() {
  const location = useLocation();
  const contextKey = Object.keys(footerContext).filter((path) => location.pathname === path || (path !== "/" && location.pathname.startsWith(path))).sort((a, b) => b.length - a.length)[0] ?? "/";
  const FooterIcon = footerContext[contextKey as keyof typeof footerContext].icon;
  const footerText = footerContext[contextKey as keyof typeof footerContext].text;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <strong>SecureGate AI</strong>
            <span>Security decision engine</span>
          </div>
        </div>
        <nav className="navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} end={item.to === "/"}>
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <FooterIcon size={18} />
          <span>{footerText}</span>
        </div>
      </aside>

      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:projectKey" element={<ProjectDetailsPage />} />
          <Route path="/projects/:projectKey/findings" element={<ProjectFindingsPage />} />
          <Route path="/projects/:projectKey/analytics" element={<ProjectAnalyticsPage />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/remediation-plan" element={<RemediationPlanPage />} />
          <Route path="/monitoring" element={<Monitoring />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/security-analytics" element={<SecurityAnalytics />} />
          <Route path="/how-to-use" element={<HowToUse />} />
          <Route path="/manifests" element={<PipelineManifests />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/scans/:scanId" element={<ScanDetailsPage />} />
        </Routes>
        <footer className="app-footer">
          <span>Copyright © 2026 SecureGate AI.</span>
          <span>All Rights Reserved.</span>
        </footer>
      </main>
      <AIAssistant />
    </div>
  );
}

export default App;
