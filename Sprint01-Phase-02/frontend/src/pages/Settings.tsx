const settings = [
  { name: "Severity threshold", value: "High and Critical" },
  { name: "Default scanner mode", value: "Manual validation" },
  { name: "Notification channels", value: "Not configured in Sprint 1" },
  { name: "CI/CD blocking", value: "Out of scope until Sprint 2" }
];

export function SettingsPage() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Platform configuration</h1>
        </div>
      </header>
      <div className="settings-list">
        {settings.map((setting) => (
          <div className="setting-row" key={setting.name}>
            <span>{setting.name}</span>
            <strong>{setting.value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
