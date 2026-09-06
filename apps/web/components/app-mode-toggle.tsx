'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type AppMode = 'prod' | 'test';
type ModeResponse = {mode: AppMode; label: string};

export function AppModeToggle({onModeChange}:{onModeChange?:(mode:AppMode)=>void|Promise<void>}={}){
  const [mode,setMode]=useState<AppMode|null>(null);
  const [switching,setSwitching]=useState(false);

  useEffect(()=>{api<ModeResponse>('/mode').then(result=>setMode(result.mode)).catch(()=>setMode('prod'))},[]);

  const select=async(next:AppMode)=>{
    if(mode===null||next===mode||switching)return;
    setSwitching(true);
    try{
      const result=await api<ModeResponse>('/mode',{method:'PATCH',body:JSON.stringify({mode:next})});
      setMode(result.mode);
      window.dispatchEvent(new CustomEvent('dias-mode-changed',{detail:result}));
      await onModeChange?.(result.mode);
    }finally{setSwitching(false)}
  };

  return <fieldset className={`app-mode-toggle ${mode??'loading'}`} aria-label="Data mode" aria-busy={mode===null||switching}>
    <button type="button" className={mode==='prod'?'active':undefined} aria-pressed={mode==='prod'} disabled={mode===null||switching} onClick={()=>select('prod')}>Prod</button>
    <button type="button" className={mode==='test'?'active':undefined} aria-pressed={mode==='test'} disabled={mode===null||switching} onClick={()=>select('test')}>Test</button>
  </fieldset>;
}
