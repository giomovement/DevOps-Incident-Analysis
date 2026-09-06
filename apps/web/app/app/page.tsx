'use client';
import { AlertTriangle, ArrowRight, Bot, CheckCircle2, ChevronDown, ChevronUp, FileText, LoaderCircle, Plus, TimerReset, Zap } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { AppShell } from '@/components/app-shell';
import { SystemStateRows } from '@/components/system-state';
import { api } from '@/lib/api';

type Incident={id:string;title:string;service?:string;environment?:string;status:string;severity?:string;created_at:string;finding_count:number;file_count:number};
type DashboardMetrics={active_incidents:number;critical_findings:number;mean_time_to_detect_seconds:null;mean_time_to_resolve_seconds:number|null;resolved_sample_size:number;event_volume:{buckets:number[];start:string|null;end:string|null;total:number}};

function duration(seconds:number|null){
  if(seconds===null)return 'N/A';
  if(seconds<3600)return `${Math.round(seconds/60)}m`;
  if(seconds<86400)return `${(seconds/3600).toFixed(1)}h`;
  return `${(seconds/86400).toFixed(1)}d`;
}

function timeLabel(value:string|null,fallback:string){
  return value?new Date(value).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):fallback;
}

function midpointTimeLabel(start:string|null,end:string|null){
  if(!start||!end)return '-12h';
  return timeLabel(new Date((new Date(start).getTime()+new Date(end).getTime())/2).toISOString(),'-12h');
}

export default function Dashboard(){
  const [incidents,setIncidents]=useState<Incident[]>([]);const [metrics,setMetrics]=useState<DashboardMetrics|null>(null);const [loading,setLoading]=useState(true);const [criticalPage,setCriticalPage]=useState(0);
  useEffect(()=>{Promise.all([api<Incident[]>('/incidents'),api<DashboardMetrics>('/dashboard')]).then(([incidentItems,dashboard])=>{setIncidents(incidentItems);setMetrics(dashboard)}).catch(()=>{location.href='/login'}).finally(()=>setLoading(false))},[]);
  const recentIncidents=useMemo(()=>[...incidents].sort((a,b)=>new Date(b.created_at).getTime()-new Date(a.created_at).getTime()),[incidents]);
  const critical=recentIncidents.filter(i=>i.severity==='critical'&&i.status!=='resolved');
  const criticalPageCount=Math.max(1,Math.ceil(critical.length/3));
  const visibleCritical=critical.slice(criticalPage*3,criticalPage*3+3);
  useEffect(()=>setCriticalPage(current=>Math.min(current,criticalPageCount-1)),[criticalPageCount]);
  const resolved=incidents.filter(i=>i.status==='resolved').length;
  const totalFiles=incidents.reduce((total,item)=>total+item.file_count,0);const totalFindings=incidents.reduce((total,item)=>total+item.finding_count,0);
  const severity=useMemo(()=>['critical','high','medium','low'].map(level=>({level,count:incidents.filter(i=>i.severity===level).length})),[incidents]);
  const maxSeverity=Math.max(...severity.map(item=>item.count),1);const eventBuckets=metrics?.event_volume.buckets??Array(24).fill(0);const maxEvents=Math.max(...eventBuckets,1);
  return <AppShell title="Operational overview" actions={<a className="app-cta" href="/incidents/new"><Plus size={17}/>New analysis</a>}>
    <section className="overview-strip"><div><span>RESOLVED INCIDENTS</span><strong className="ratio-value">{resolved} / {incidents.length}</strong><small><CheckCircle2/> {incidents.length?`${Math.round(resolved/incidents.length*100)}% Resolution Rate`:'No Incidents Yet'}</small></div><div><span>EVIDENCE TOTALS</span><strong className="ratio-value">{totalFiles} / {totalFindings}</strong><small><FileText/> Files / Alerts</small></div><div><span>CRITICAL ALERTS</span><strong className="red">{String(metrics?.critical_findings??0).padStart(2,'0')}</strong><small><AlertTriangle/> Human Review Required</small></div><div><span>MEAN TIME TO RESOLVE</span><strong>{duration(metrics?.mean_time_to_resolve_seconds??null)}</strong><small><TimerReset/> {metrics?.resolved_sample_size?`${metrics.resolved_sample_size} Resolved Incident${metrics.resolved_sample_size===1?'':'s'}`:'No Resolved Incidents'}</small></div></section>
    <section className="command-grid">
      <article className="command-card trend-card"><div className="card-title"><div><span>LOG EVENT VOLUME</span><h2>Events over the latest 24 hours</h2></div><b>{metrics?.event_volume.total?`${metrics.event_volume.total} EVENTS`:'NO TIMED EVENTS'}</b></div><figure className="event-chart" aria-label={`Log events by hour. Y axis ranges from 0 to ${maxEvents} events. X axis covers the latest 24 hours.`}><span className="y-axis-title">Events</span><div className="y-axis-scale" aria-hidden="true"><span>{maxEvents}</span><span>{Math.round(maxEvents/2)}</span><span>0</span></div><div className="chart-area"><div className="chart-grid" aria-hidden="true"><i/><i/><i/></div><div className="large-chart">{eventBuckets.map((value,index)=><i key={index} title={`${value} event${value===1?'':'s'}`} style={{height:value?`${Math.max(value/maxEvents*100,4)}%`:'2px'}} className={value===maxEvents&&value>0?'hot':''}/>)}</div></div><div className="x-axis-ticks"><span>{timeLabel(metrics?.event_volume.start??null,'-24h')}</span><span>{midpointTimeLabel(metrics?.event_volume.start??null,metrics?.event_volume.end??null)}</span><span>{timeLabel(metrics?.event_volume.end??null,'Latest')}</span></div><figcaption className="x-axis-title">Time (one-hour buckets)</figcaption></figure></article>
      <article className="command-card severity-card"><div className="card-title"><div><span>SEVERITY DISTRIBUTION</span><h2>{incidents.length?`${incidents.length} tracked incidents`:'No incidents yet'}</h2></div></div><div className="severity-bars">{severity.map(item=><div key={item.level}><span>{item.level}</span><i><b className={item.level} style={{width:item.count?`${item.count/maxSeverity*100}%`:'0'}}/></i><em>{item.count}</em></div>)}</div></article>
      <div className="dashboard-half-row">
        <article className="command-card alert-card"><div className="card-title"><div><span>CRITICAL ISSUE ALERTS</span><h2>{critical.length?'Human review required':'All clear'}</h2></div><div className="alert-card-tools"><Zap/>{critical.length>3&&<div className="alert-scroll-controls"><button type="button" aria-label="Show previous critical incidents" disabled={criticalPage===0} onClick={()=>setCriticalPage(page=>Math.max(0,page-1))}><ChevronUp/></button><span>{criticalPage+1}/{criticalPageCount}</span><button type="button" aria-label="Show next critical incidents" disabled={criticalPage>=criticalPageCount-1} onClick={()=>setCriticalPage(page=>Math.min(criticalPageCount-1,page+1))}><ChevronDown/></button></div>}</div></div>{critical.length?visibleCritical.map(i=><a className="incident-row alert-incident-row" href={`/incidents/${i.id}`} key={i.id}><span className="severity-dot critical"/><div><b>{i.title}</b><small>{i.service||'Unassigned'} · {i.file_count} file(s) · {i.finding_count} finding(s)</small></div><em className={i.status}>{i.status.replace('_',' ')}</em><ArrowRight/></a>):<div className="clear-state"><CheckCircle2/><p>No active critical incidents are awaiting review.</p></div>}</article>
        <article className="command-card agent-card"><div className="card-title"><div><span>SYSTEM STATE</span><h2>Runtime &amp; integrations</h2></div><Bot/></div><SystemStateRows/></article>
      </div>
      <article className="command-card recent-card"><div className="card-title"><div><span>RECENT ANALYSIS RUNS</span><h2>Incident history</h2></div><a href="/history">View all <ArrowRight/></a></div>{loading?<div className="loading-row"><LoaderCircle className="spin"/>Loading incidents…</div>:recentIncidents.length?recentIncidents.slice(0,5).map(item=><a className="incident-row" href={`/incidents/${item.id}`} key={item.id}><span className={`severity-dot ${item.severity||'low'}`}/><div><b>{item.title}</b><small>{item.service||'Unassigned'} · {item.file_count} file(s) · {item.finding_count} finding(s)</small></div><em className={item.status}>{item.status.replace('_',' ')}</em><ArrowRight/></a>):<div className="empty-command"><FileText/><h3>No incidents in this workspace</h3><p>Upload operational logs to begin a traceable analysis.</p><a className="app-cta" href="/incidents/new"><Plus/>Create first analysis</a></div>}</article>
    </section>
  </AppShell>
}
