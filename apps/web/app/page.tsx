'use client';

import { ArrowRight, Braces, CheckCircle2, ChevronRight, FileSearch, Fingerprint, Gauge, GitBranch, LockKeyhole, MessageSquareText, Moon, Network, ShieldCheck, Sun, TicketCheck, Workflow, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';

const ticker = ['STRUCTURED LOGS', 'EVIDENCE LINKED', 'HUMAN APPROVAL', 'SLACK READY', 'JIRA READY', 'AUDITABLE'];
const workflow = ['Upload', 'Parse', 'Classify', 'Correlate', 'Recommend', 'Review', 'Deliver', 'Cookbook'];
const features = [
  { icon: FileSearch, title: 'Evidence, not guesses', body: 'Every finding resolves to its original file, timestamp, and exact line range.', large: true },
  { icon: GitBranch, title: 'Agent orchestration', body: 'Typed shared state keeps specialist agents aligned and traceable.' },
  { icon: ShieldCheck, title: 'Human approval', body: 'Nothing leaves the system until a responder approves the exact payload.' },
  { icon: MessageSquareText, title: 'Incident-aware chat', body: 'Ask what failed first and receive answers grounded in cited log evidence.' },
  { icon: TicketCheck, title: 'Slack + Jira ready', body: 'Preview delivery, prevent duplicates, and preserve every external reference.' },
  { icon: Braces, title: 'Reusable cookbooks', body: 'Turn analysis into an ordered response checklist with risks and rollback steps.' },
];

function ThemeToggle() {
  const [dark, setDark] = useState(true);
  useEffect(() => {
    const saved = localStorage.getItem('dias-theme');
    const nextDark = saved ? saved === 'dark' : true;
    setDark(nextDark);
    document.documentElement.classList.toggle('dark', nextDark);
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('dias-theme', next ? 'dark' : 'light');
  };
  return <button className="icon-button" onClick={toggle} aria-label={`Switch to ${dark ? 'light' : 'dark'} mode`}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button>;
}

export default function Home() {
  return (
    <main>
      <header className="nav-shell">
        <a className="brand" href="#top" aria-label="DevOps Incident Analysis Suite home"><span className="brand-mark"><Network size={19} /></span><span>DevOps <em>IAS</em></span></a>
        <nav aria-label="Primary navigation"><a href="#product">Product</a><a href="#workflow">Workflow</a><a href="#security">Security</a><a href="#integrations">Integrations</a></nav>
        <div className="nav-actions"><ThemeToggle /><a className="login-link" href="/login">Log in</a><a className="pill-button small" href="/signup">Get started <ArrowRight size={17} /></a></div>
      </header>

      <section className="hero" id="top">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-copy">
          <div className="eyebrow"><span /> HUMAN-APPROVED INCIDENT INTELLIGENCE</div>
          <h1>Turn raw logs into <span>response-ready incidents.</span></h1>
          <p>Detect what matters, trace every conclusion to evidence, and move from recommended fixes to approved Slack updates, Jira tickets, and incident cookbooks.</p>
          <div className="hero-actions"><a className="pill-button" href="/signup">Analyze an incident <span className="button-icon"><ArrowRight size={18} /></span></a><a className="pill-button outline" href="#workflow">Explore the workflow <ChevronRight size={18} /></a></div>
          <div className="trust-row"><span><LockKeyhole size={15} /> Server-side secrets</span><span><Fingerprint size={15} /> Evidence provenance</span><span><ShieldCheck size={15} /> No autonomous fixes</span></div>
        </div>
      </section>

      <section className="ticker" aria-label="Product capabilities"><div>{[...ticker, ...ticker].map((item, index) => <span key={`${item}-${index}`}><i className={index % 2 ? 'cyan' : ''} />{item}</span>)}</div></section>

      <section className="section workflow-section" id="workflow">
        <div className="section-heading"><div><span className="kicker">ONE CONTROLLED PIPELINE</span><h2>From signal to action,<br /><span>without losing the evidence.</span></h2></div><p>Specialist agents work over one typed incident state. The graph can retry, pause, resume, and surface partial failures without hiding what happened.</p></div>
        <div className="workflow-rail">{workflow.map((step, index) => <div className={step === 'Review' ? 'active' : ''} key={step}><span>{String(index + 1).padStart(2, '0')}</span><strong>{step}</strong>{index < workflow.length - 1 && <ChevronRight size={15} />}</div>)}</div>
      </section>

      <section className="section dashboard-section" id="product">
        <div className="metrics-copy"><span className="kicker">LIVE INCIDENT COMMAND</span><h2>See the system think.<br /><span>Keep humans in control.</span></h2><div className="metric-pair"><div><strong>07</strong><span>Specialist workflow stages</span></div><div><strong>100%</strong><span>Externally written actions reviewed</span></div></div></div>
        <div className="tilt-wrap"><div className="dashboard-card"><div className="dash-head"><div><span className="status-dot" /> INCIDENT // INC-2048</div><span>DEMO DATA</span></div><div className="dash-grid">
          <div className="incident-main"><div className="alert-title"><div><span>SEV-1</span><h3>Checkout latency regression</h3></div><b>94% CONFIDENCE</b></div><div className="chart" aria-label="Demo error rate trend">{[28,34,31,42,48,57,51,72,88,76,93,82,66,54].map((height, i) => <i key={i} style={{height: `${height}%`}} className={i > 7 ? 'hot' : ''} />)}</div><div className="chart-labels"><span>12:42 UTC</span><span>Error rate · 18.4%</span><span>12:56 UTC</span></div></div>
          <div className="agent-panel"><span>AGENT EXECUTION</span>{['Parse logs','Classify events','Correlate traces','Recommend fixes'].map((item, i) => <div key={item}><CheckCircle2 size={15} /><span>{item}</span><b>{[1.2,3.8,2.1,4.4][i]}s</b></div>)}<div className="pending"><Gauge size={15} /><span>Human review</span><b>PENDING</b></div></div>
          <div className="evidence-panel"><span>EVIDENCE</span><code>payment-api.log:884–912</code><p>Connection pool exhausted after deployment <b>deploy-7c91</b>.</p></div>
          <div className="approval-panel"><span>EXTERNAL ACTION</span><strong>Slack incident update</strong><button>Review payload <ArrowRight size={14} /></button></div>
        </div></div></div>
      </section>

      <section className="section" id="integrations"><div className="section-heading compact"><div><span className="kicker">INCIDENT INTELLIGENCE, CONNECTED</span><h2>A complete response surface.</h2></div></div><div className="bento-grid">{features.map(({ icon: Icon, title, body, large }) => <article className={`feature-card ${large ? 'feature-large' : ''}`} key={title}><Icon className="feature-icon" /><div><h3>{title}</h3><p>{body}</p></div>{large && <Zap className="watermark" />}</article>)}</div></section>

      <section className="section security-card" id="security"><div><span className="kicker">BUILT AROUND THE APPROVAL BOUNDARY</span><h2>Recommendations are not execution.</h2><p>Operational logs stay incident-scoped. Credentials never enter prompts. Slack messages and Jira tickets are immutable drafts until an authorized responder approves the exact content.</p></div><div className="security-list">{['Role-based access','Exact-line provenance','Immutable approval hashes','Complete audit history'].map(item => <span key={item}><CheckCircle2 size={18} />{item}</span>)}</div></section>

      <section className="section final-cta"><div className="cta-glow" /><span className="kicker">READY FOR THE NEXT INCIDENT</span><h2>Move from alert noise to<br /><span>an approved response plan.</span></h2><div className="hero-actions"><a className="pill-button" href="/signup">Get started <span className="button-icon"><ArrowRight size={18} /></span></a><a className="pill-button outline" href="/architecture">View architecture</a></div></section>
      <footer><a className="brand" href="#top"><span className="brand-mark"><Workflow size={19} /></span><span>DevOps <em>IAS</em></span></a><p>Human-approved incident intelligence.</p><div><a href="#security">Security</a><a href="#workflow">Workflow</a><a href="/login">Log in</a></div><small>© 2026 DevOps Incident Analysis Suite</small></footer>
    </main>
  );
}
