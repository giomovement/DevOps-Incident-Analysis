'use client';
import { Activity, Cable, History, LayoutDashboard, LogOut, Network, Plus, ShieldCheck } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { ReactNode } from 'react';
import { api } from '@/lib/api';
import { ThemeToggle } from './theme-toggle';

export function AppShell({children,title,eyebrow='INCIDENT COMMAND CENTER',actions}:{children:ReactNode;title:string;eyebrow?:string;actions?:ReactNode}){
  const pathname=usePathname();
  const activeLink=(href:string)=>pathname===href;
  const logout=async()=>{try{await api('/auth/logout',{method:'POST'})}finally{location.href='/login'}};
  return <div className="app-layout">
    <aside className="side-nav">
      <a className="brand" href="/app"><span className="brand-mark"><Network size={19}/></span><span>DevOps <em>IAS</em></span></a>
      <div className="workspace-chip"><span>AP</span><div><b>APEX OPS</b><small>Production workspace</small></div></div>
      <nav><span>COMMAND</span><a className={activeLink('/app')?'active':undefined} aria-current={activeLink('/app')?'page':undefined} href="/app"><LayoutDashboard/>Overview</a><a className={activeLink('/incidents/new')?'active':undefined} aria-current={activeLink('/incidents/new')?'page':undefined} href="/incidents/new"><Plus/>New analysis</a><a className={activeLink('/history')?'active':undefined} aria-current={activeLink('/history')?'page':undefined} href="/history"><History/>Incident history</a><span>SYSTEM</span><a className={activeLink('/settings/integrations')?'active':undefined} aria-current={activeLink('/settings/integrations')?'page':undefined} href="/settings/integrations"><Cable/>Integrations</a><a className={activeLink('/architecture')?'active':undefined} aria-current={activeLink('/architecture')?'page':undefined} href="/architecture"><ShieldCheck/>Architecture</a></nav>
      <div className="side-footer"><div><Activity/><span><b>System operational</b><small>Integrations active</small></span></div><button onClick={logout}><LogOut size={16}/> Log out</button></div>
    </aside>
    <main className="app-main"><header className="app-header"><div><span className="kicker">{eyebrow}</span><h1>{title}</h1></div><div className="app-header-actions">{actions}<ThemeToggle/><button className="avatar" aria-label="Account menu">GO</button></div></header>{children}</main>
  </div>
}
