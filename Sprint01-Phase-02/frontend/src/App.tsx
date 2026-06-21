import { NavLink, Route, Routes } from "react-router-dom";
import {
  BarChart3,
  FileText,
  FolderKanban,
  LayoutDashboard,
  Settings,
  ShieldCheck
} from "lucide-react";
import { Dashboard } from "./pages/Dashboard";
import { Projects } from "./pages/Projects";
import { Reports } from "./pages/Reports";
import { SettingsPage } from "./pages/Settings";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings }
];

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <strong>SecureGate AI</strong>
            <span>DevSecOps foundation</span>
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
          <BarChart3 size={18} />
          <span>Sprint 1 validation</span>
        </div>
      </aside>

      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
