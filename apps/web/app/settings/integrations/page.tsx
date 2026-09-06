'use client';

import { Bot, CheckCircle2, CircleAlert, Cloud, Hash, KeyRound, LoaderCircle, MessageSquareText, PlugZap, Save, ShieldCheck, TicketCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AppShell } from '@/components/app-shell';
import { api } from '@/lib/api';

type Integration = { provider: string; status: string; mode: string; display_name: string; destination?: string };
type OpenRouterSettings = { provider: string; status: string; configured: boolean; model: string; key_hint?: string };
type SlackSettings = { provider: string; status: string; configured: boolean; channel_id: string; token_hint?: string };
type ConnectionState = 'idle' | 'testing' | 'connected' | 'failed';

export default function Integrations() {
  const [items, setItems] = useState<Integration[]>([]);
  const [openrouter, setOpenrouter] = useState<OpenRouterSettings | null>(null);
  const [slack, setSlack] = useState<SlackSettings | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [slackToken, setSlackToken] = useState('');
  const [channelId, setChannelId] = useState('');
  const [jiraToken, setJiraToken] = useState('');
  const [jiraCloudId, setJiraCloudId] = useState('');
  const [testing, setTesting] = useState('');
  const [saving, setSaving] = useState(false);
  const [savingSlack, setSavingSlack] = useState(false);
  const [connection, setConnection] = useState<ConnectionState>('idle');
  const [providerStatuses, setProviderStatuses] = useState<Record<string, ConnectionState>>({});
  const [messageFailed, setMessageFailed] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    Promise.all([api<Integration[]>('/integrations'), api<OpenRouterSettings>('/integrations/openrouter'), api<SlackSettings>('/integrations/slack')])
      .then(([integrations, settings, slackSettings]) => { setItems(integrations); setOpenrouter(settings); setModel(settings.model); setSlack(slackSettings); setChannelId(slackSettings.channel_id); })
      .catch(() => (location.href = '/login'));
  }, []);

  async function saveOpenRouter(clearApiKey = false) {
    setSaving(true); setMessage(''); setConnection('idle');
    try {
      const result = await api<OpenRouterSettings>('/integrations/openrouter', {
        method: 'PUT', body: JSON.stringify({ api_key: apiKey || null, model, clear_api_key: clearApiKey }),
      });
      setOpenrouter(result); setApiKey('');
      window.dispatchEvent(new CustomEvent('dias:integrations-changed',{detail:{provider:'openrouter',configured:result.configured,status:result.status}}));
      setMessage(result.configured ? 'OpenRouter settings saved. Test the connection to verify them.' : 'Deterministic mode enabled. The app will run without AI calls.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save OpenRouter settings');
    } finally { setSaving(false); }
  }

  async function saveSlack() {
    setSavingSlack(true); setMessage('');
    try {
      const result = await api<SlackSettings>('/integrations/slack', {
        method: 'PUT', body: JSON.stringify({ bot_token: slackToken || null, channel_id: channelId }),
      });
      setSlack(result); setSlackToken('');
      setProviderStatuses((current) => { const next = { ...current }; delete next.slack; return next; });
      setItems((current) => current.map((item) => item.provider === 'slack' ? { ...item, status: result.status, mode: result.status, destination: result.channel_id } : item));
      window.dispatchEvent(new CustomEvent('dias:integrations-changed',{detail:{provider:'slack',status:result.status}}));
      setMessage(result.configured ? 'Slack settings saved. Test the connection to verify them.' : 'Slack is not configured. The rest of the app remains available.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save Slack settings');
    } finally { setSavingSlack(false); }
  }

  async function test(provider: string) {
    setTesting(provider); setMessage(''); setMessageFailed(false);
    setProviderStatuses((current) => ({ ...current, [provider]: 'testing' }));
    if (provider === 'openrouter') setConnection('testing');
    try {
      const result = await api<{ status: string; model?: string; workspace?: string; channel?: string }>(`/integrations/${provider}/test`, { method: 'POST' });
      setProviderStatuses((current) => ({ ...current, [provider]: 'connected' }));
      if (provider === 'openrouter') setConnection('connected');
      if (provider !== 'openrouter') setItems((current) => current.map((item) => item.provider === provider ? { ...item, status: result.status } : item));
      window.dispatchEvent(new CustomEvent('dias:integrations-changed',{detail:{provider,status:result.status,configured:true}}));
      const target = result.model ? ` with ${result.model}` : result.channel ? ` to #${result.channel}` : '';
      setMessage(`${provider === 'openrouter' ? 'OpenRouter' : 'Slack'} ${result.status}${target} — no external write was performed.`);
    } catch (error) {
      setProviderStatuses((current) => ({ ...current, [provider]: 'failed' }));
      setMessageFailed(true);
      if (provider === 'openrouter') setConnection('failed');
      window.dispatchEvent(new CustomEvent('dias:integrations-changed',{detail:{provider,status:'failed',configured:true}}));
      setMessage(error instanceof Error ? error.message : 'Test failed');
    } finally { setTesting(''); }
  }

  const status = connection !== 'idle' ? connection : openrouter?.status || (openrouter?.configured ? 'configured' : 'deterministic');

  return <AppShell title="Configure Integrations" eyebrow="ADMINISTRATIVE CONNECTIONS">
    <section className="integration-intro"><div><ShieldCheck /><span><h2>Test connections before running the app.</h2><p>The app still works without integrations. Without OpenRouter, it defaults to deterministic mode with no LLM use.</p></span></div></section>

    <section className="openrouter-card">
      <header><Bot /><span><b>OpenRouter</b><small>Optional AI reasoning provider</small></span><em className={`provider-status ${status}`}><i />{status}</em></header>
      <div className="openrouter-copy"><h2>AI model connection</h2><p>Add a key and model to enable AI-assisted recommendations, summaries, cookbooks, and incident chat. Without a key, every feature uses deterministic local functions.</p></div>
      <div className="openrouter-fields">
        <label><span><KeyRound />API KEY</span><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={openrouter?.key_hint || 'sk-or-v1-…'} autoComplete="off" /></label>
        <label><span><Bot />MODEL</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder="provider/model-name" /></label>
      </div>
      <footer><div><button onClick={() => saveOpenRouter(false)} disabled={saving || !model.trim()}>{saving ? <LoaderCircle className="spin" /> : <Save />}Save settings</button><button onClick={() => test('openrouter')} disabled={!!testing || !openrouter?.configured}>{testing === 'openrouter' ? <LoaderCircle className="spin" /> : <PlugZap />}Test connection</button></div>{openrouter?.configured && <button className="text-button" onClick={() => saveOpenRouter(true)} disabled={saving}>Remove key &amp; use deterministic mode</button>}</footer>
    </section>

    {message && <div className={`integration-message ${messageFailed ? 'failed' : ''}`}>{messageFailed ? <CircleAlert /> : <CheckCircle2 />}{message}</div>}

    <section className="integration-grid">{items.map((item) => <article key={item.provider}>
      <header>{item.provider === 'slack' ? <MessageSquareText /> : <TicketCheck />}<span><b>{item.provider === 'slack' ? 'Slack' : 'Jira (on the roadmap)'}</b><small>{item.display_name}</small></span><em className={`provider-status ${(providerStatuses[item.provider] || item.status).replace(' ', '-')}`}><i />{item.provider === 'jira' ? 'Not available for config' : providerStatuses[item.provider] || item.status}</em></header>
      {item.provider === 'slack' && <div className="integration-fields">
        <label><span><KeyRound />BOT TOKEN</span><input type="password" value={slackToken} onChange={(event) => setSlackToken(event.target.value)} placeholder={slack?.token_hint || 'xoxb-…'} autoComplete="off" /></label>
        <label><span><Hash />CHANNEL ID</span><input value={channelId} onChange={(event) => setChannelId(event.target.value)} placeholder="C0123456789" /></label>
      </div>}
      {item.provider === 'jira' && <div className="integration-fields">
        <label><span><KeyRound />ACCESS TOKEN</span><input type="password" value={jiraToken} onChange={(event) => setJiraToken(event.target.value)} placeholder="Enter Jira access token" autoComplete="off" disabled /></label>
        <label><span><Cloud />CLOUD ID</span><input value={jiraCloudId} onChange={(event) => setJiraCloudId(event.target.value)} placeholder="Enter Jira Cloud ID" disabled /></label>
      </div>}
      <footer><div>
        {item.provider === 'slack'
          ? <button className="save-button" onClick={saveSlack} disabled={savingSlack || !channelId.trim()}>{savingSlack ? <LoaderCircle className="spin" /> : <Save />}Save settings</button>
          : <button className="save-button" disabled><Save />Save settings</button>}
        <button onClick={() => test(item.provider)} disabled={!!testing || item.provider === 'jira' || item.status === 'not configured'}>{testing === item.provider ? <LoaderCircle className="spin" /> : <PlugZap />}Test connection</button>
      </div></footer>
    </article>)}</section>
  </AppShell>;
}
