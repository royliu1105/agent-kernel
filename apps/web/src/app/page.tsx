const navItems = ["Dashboard", "Agents", "Runs", "Approvals", "Knowledge", "Evals", "Settings"];

const metrics = [
  ["Runs", "0"],
  ["Pending approvals", "0"],
  ["Estimated cost", "$0.00"],
];

export default function Home() {
  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">Agent Kernel</div>
        <nav className="nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </nav>
      </aside>
      <section className="content">
        <p className="eyebrow">Agent Workbench</p>
        <h1 className="title">Production-grade agent runtime foundation</h1>
        <p className="summary">
          Day 1 starts with the control console shell. The product center is run visibility,
          approvals, knowledge, evals, and cost-aware operations rather than a generic chat page.
        </p>
        <div className="grid">
          {metrics.map(([label, value]) => (
            <article className="metric" key={label}>
              <p className="metric-label">{label}</p>
              <p className="metric-value">{value}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
