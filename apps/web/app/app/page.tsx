'use client';
import { AlertTriangle, ArrowRight, Bot, CheckCircle2, Clock3, FileText, LoaderCircle, Plus, Radio, TicketCheck, TimerReset, Zap } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { AppShell } from '@/components/app-shell';
import { api } from '@/lib/api';

type Incident={id:string;title:string;service?:string;environment?:string;status:string;severity?:string;created_at:string;finding_count:number;file_count:number};
const demoTrend=[22,31,27,38,34,51,47,63,58,76,69,82,73,61];

export default function Dashboard(){
  const [incidents,setIncidents]=useState<Incident[]>([]);const [loading,setLoading]=useState(true);
  useEffect(()=>{api<Incident[]>('/incidents').then(setIncidents).catch(()=>{location.href='/login'}).finally(()=>setLoading(false))},[]);
  const active=incidents.filter(i=>!['resolved','monitoring'].includes(i.status));const critical=incidents.filter(i=>i.severity==='critical');
  const severity=useMemo(()=>['critical','high','medium','low'].map(level=>({level,count:incidents.filter(i=>i.severity===level).length})),[incidents]);
  return <AppShell title="Operational overview" actions={<a className="app-cta" href="/incidents/new"><Plus size={17}/>New analysis</a>}>
    <section className="overview-strip"><div><span>ACTIVE INCIDENTS</span><strong>{String(active.length).padStart(2,'0')}</strong><small><Radio/> Live workspace</small></div><div><span>CRITICAL FINDINGS</span><strong className="red">{String(critical.length).padStart(2,'0')}</strong><small><AlertTriangle/> Human review required</small></div><div><span>MEAN TIME TO DETECT</span><strong>—</strong><small><Clock3/> Calculated from event evidence</small></div><div><span>MEAN TIME TO RESOLVE</span><strong>—</strong><small><TimerReset/> Available after resolution</small></div></section>
    <section className="command-grid">
      <article className="command-card trend-card"><div className="card-title"><div><span>ERROR-RATE SIGNAL</span><h2>Log volume & anomalies</h2></div><b>DEMO BASELINE</b></div><div className="large-chart">{demoTrend.map((v,i)=><i key={i} style={{height:`${v}%`}} className={i>8?'hot':''}/>)}</div><div className="axis"><span>-60m</span><span>Normalized event volume</span><span>now</span></div></article>
      <article className="command-card severity-card"><div className="card-title"><div><span>SEVERITY DISTRIBUTION</span><h2>{incidents.length?`${incidents.length} tracked incidents`:'No incidents yet'}</h2></div></div><div className="severity-bars">{severity.map(item=><div key={item.level}><span>{item.level}</span><i><b style={{width:`${Math.max(item.count*22,item.count?12:2)}%`}}/></i><em>{item.count}</em></div>)}</div></article>
      <article className="command-card alert-card"><div className="card-title"><div><span>CRITICAL ISSUE ALERTS</span><h2>{critical.length?'Response review required':'All clear'}</h2></div><Zap/></div>{critical.length?critical.slice(0,2).map(i=><a href={`/incidents/${i.id}`} key={i.id}><span>SEV-1</span><div><b>{i.title}</b><small>{i.service||'Unknown service'} · {i.environment||'Unknown environment'}</small></div><ArrowRight/></a>):<div className="clear-state"><CheckCircle2/><p>No critical incidents are awaiting review.</p></div>}</article>
      <article className="command-card agent-card"><div className="card-title"><div><span>AGENT EXECUTION</span><h2>Orchestrator state</h2></div><Bot/></div>{['Log reader & classifier','Remediation','Notification','Cookbook synthesizer','Jira ticket'].map((name,i)=><div className="agent-row" key={name}><span className={i<2?'live':''}/><b>{name}</b><em>{i<2?'READY':'IDLE'}</em></div>)}</article>
      <article className="command-card recent-card"><div className="card-title"><div><span>RECENT ANALYSIS RUNS</span><h2>Incident history</h2></div><a href="/history">View all <ArrowRight/></a></div>{loading?<div className="loading-row"><LoaderCircle className="spin"/>Loading incidents…</div>:incidents.length?incidents.slice(0,5).map(item=><a className="incident-row" href={`/incidents/${item.id}`} key={item.id}><span className={`severity-dot ${item.severity||'low'}`}/><div><b>{item.title}</b><small>{item.service||'Unassigned'} · {item.file_count} file(s) · {item.finding_count} finding(s)</small></div><em>{item.status.replace('_',' ')}</em><ArrowRight/></a>):<div className="empty-command"><FileText/><h3>No incidents in this workspace</h3><p>Upload operational logs to begin a traceable analysis.</p><a className="app-cta" href="/incidents/new"><Plus/>Create first analysis</a></div>}</article>
      <article className="command-card integrations-card"><div className="card-title"><div><span>DELIVERY STATUS</span><h2>External actions</h2></div><TicketCheck/></div><div className="integration-state"><span className="integration-logo">S</span><div><b>Slack</b><small>Mock adapter connected</small></div><em>READY</em></div><div className="integration-state"><span className="integration-logo jira">J</span><div><b>Jira Cloud</b><small>Mock adapter connected</small></div><em>READY</em></div><p>Every delivery requires responder approval.</p></article>
    </section>
  </AppShell>
}
