'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Integration={provider:string;status:string};
type OpenRouterSettings={configured:boolean;status:string};
type IntegrationChange={provider:'openrouter'|'slack';configured?:boolean;status?:string};

export function SystemStateRows({compact=false}:{compact?:boolean}){
  const [integrations,setIntegrations]=useState<Integration[]|null>(null);
  const [openrouter,setOpenrouter]=useState<OpenRouterSettings|null>(null);

  useEffect(()=>{
    const refresh=()=>Promise.all([api<Integration[]>('/integrations'),api<OpenRouterSettings>('/integrations/openrouter')])
      .then(([providerItems,aiSettings])=>{setIntegrations(providerItems);setOpenrouter(aiSettings)})
      .catch(()=>{setIntegrations([]);setOpenrouter({configured:false,status:'unavailable'})});
    const refreshWhenVisible=()=>{if(document.visibilityState==='visible')refresh()};
    const applyIntegrationChange=(event:Event)=>{
      const change=(event as CustomEvent<IntegrationChange>).detail;
      if(change?.provider==='openrouter'&&typeof change.configured==='boolean')setOpenrouter({configured:change.configured,status:change.status||(change.configured?'configured':'deterministic')});
      if(change?.provider==='slack'&&change.status)setIntegrations(current=>(current||[]).map(item=>item.provider==='slack'?{...item,status:change.status as string}:item));
      refresh();
    };
    refresh();
    const timer=window.setInterval(refresh,15000);
    window.addEventListener('focus',refresh);
    window.addEventListener('dias:integrations-changed',applyIntegrationChange);
    document.addEventListener('visibilitychange',refreshWhenVisible);
    return()=>{window.clearInterval(timer);window.removeEventListener('focus',refresh);window.removeEventListener('dias:integrations-changed',applyIntegrationChange);document.removeEventListener('visibilitychange',refreshWhenVisible)};
  },[]);

  const loaded=integrations!==null&&openrouter!==null;
  const llmConnected=openrouter?.status==='connected';
  const providerStatus=(provider:string)=>integrations?.find(item=>item.provider===provider)?.status||'not configured';
  const providerOn=(provider:string)=>loaded&&['configured','connected'].includes(providerStatus(provider));
  const rows=loaded?[
    {name:'LLM config',value:openrouter.status.toUpperCase(),on:openrouter.configured,state:openrouter.status.replace(' ','-')},
    {name:'Analysis mode',value:llmConnected?'LLM':'DETERMINISTIC',on:llmConnected,state:llmConnected?'connected':'not-configured'},
    {name:'Slack integration',value:providerStatus('slack').toUpperCase(),on:providerOn('slack'),state:providerStatus('slack').replace(' ','-')},
    {name:'Jira integration',value:providerStatus('jira').toUpperCase(),on:providerOn('jira'),state:providerStatus('jira').replace(' ','-')},
  ]:[
    {name:'LLM config',value:'LOADING',on:false,state:'loading'},
    {name:'Analysis mode',value:'LOADING',on:false,state:'loading'},
    {name:'Slack integration',value:'LOADING',on:false,state:'loading'},
    {name:'Jira integration',value:'LOADING',on:false,state:'loading'},
  ];

  return <div className={`system-state-list${compact?' compact':''}`}>{rows.map(item=><div className={`agent-row ${item.state}`} key={item.name}><span className={item.on?'live':''}/><b>{item.name}</b><em className={item.on?'on':''}>{item.value}</em></div>)}</div>;
}
