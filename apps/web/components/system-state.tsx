'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Integration={provider:string;status:string};
type OpenRouterSettings={configured:boolean};

export function SystemStateRows({compact=false}:{compact?:boolean}){
  const [integrations,setIntegrations]=useState<Integration[]|null>(null);
  const [openrouter,setOpenrouter]=useState<OpenRouterSettings|null>(null);

  useEffect(()=>{
    Promise.all([api<Integration[]>('/integrations'),api<OpenRouterSettings>('/integrations/openrouter')])
      .then(([providerItems,aiSettings])=>{setIntegrations(providerItems);setOpenrouter(aiSettings)})
      .catch(()=>{setIntegrations([]);setOpenrouter({configured:false})});
  },[]);

  const loaded=integrations!==null&&openrouter!==null;
  const providerOn=(provider:string)=>loaded&&['configured','connected'].includes(integrations.find(item=>item.provider===provider)?.status||'');
  const rows=loaded?[
    {name:'LLM config',value:openrouter.configured?'ON':'OFF',on:openrouter.configured},
    {name:'Analysis mode',value:openrouter.configured?'LLM':'DETERMINISTIC',on:openrouter.configured},
    {name:'Slack integration',value:providerOn('slack')?'ON':'OFF',on:providerOn('slack')},
    {name:'Jira integration',value:providerOn('jira')?'ON':'OFF',on:providerOn('jira')},
  ]:[
    {name:'LLM config',value:'LOADING',on:false},
    {name:'Analysis mode',value:'LOADING',on:false},
    {name:'Slack integration',value:'LOADING',on:false},
    {name:'Jira integration',value:'LOADING',on:false},
  ];

  return <div className={`system-state-list${compact?' compact':''}`}>{rows.map(item=><div className="agent-row" key={item.name}><span className={item.on?'live':''}/><b>{item.name}</b><em className={item.on?'on':''}>{item.value}</em></div>)}</div>;
}
