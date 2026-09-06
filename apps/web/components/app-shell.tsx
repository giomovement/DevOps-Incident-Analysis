'use client';
import { Activity, Cable, History, LayoutDashboard, LogOut, Network, Plus, UserRound } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { SystemStateRows } from './system-state';
import { ThemeToggle } from './theme-toggle';

export function AppShell({children,title,eyebrow='INCIDENT COMMAND CENTER',actions}:{children:ReactNode;title:string;eyebrow?:string;actions?:ReactNode}){
  const pathname=usePathname();
  const [displayName,setDisplayName]=useState('User');
  useEffect(()=>{api<{display_name:string}>('/auth/me').then(user=>setDisplayName(user.display_name)).catch(()=>{})},[]);
  const activeLink=(href:string)=>pathname===href;
  const logout=async()=>{try{await api('/auth/logout',{method:'POST'})}finally{location.href='/login'}};
  return <div className="app-layout">
    <aside className="side-nav">
      <a className="brand" href="/app"><span className="brand-mark"><Network size={19}/></span><span>DevOps <em>Labs</em></span></a>
      <div className="workspace-chip"><span><UserRound size={16}/></span><div><b>{displayName}</b><small>Production workspace</small></div></div>
      <nav><span>COMMAND</span><a className={activeLink('/app')?'active':undefined} aria-current={activeLink('/app')?'page':undefined} href="/app"><LayoutDashboard/>Overview</a><a className={activeLink('/incidents/new')?'active':undefined} aria-current={activeLink('/incidents/new')?'page':undefined} href="/incidents/new"><Plus/>New analysis</a><a className={activeLink('/history')?'active':undefined} aria-current={activeLink('/history')?'page':undefined} href="/history"><History/>Incident history</a><span>SYSTEM</span><a className={activeLink('/settings/integrations')?'active':undefined} aria-current={activeLink('/settings/integrations')?'page':undefined} href="/settings/integrations"><Cable/>Integrations</a></nav>
      <div className="side-footer"><div className="side-state-heading"><Activity/><span><b>System state</b><small>Runtime &amp; integrations</small></span></div><SystemStateRows compact/><button onClick={logout}><LogOut size={16}/> Log out</button></div>
    </aside>
    <main className="app-main"><header className="app-header"><div><span className="kicker">{eyebrow}</span><h1>{title}</h1></div><div className="app-header-actions">{actions}<ThemeToggle/><button className="avatar" aria-label="Account menu">GO</button></div></header>{children}</main>
  </div>
}
