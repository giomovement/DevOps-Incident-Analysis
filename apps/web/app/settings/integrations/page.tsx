'use client';

import { Bot, CheckCircle2, CircleAlert, ExternalLink, KeyRound, LoaderCircle, LockKeyhole, MessageSquareText, PlugZap, Save, ShieldCheck, TicketCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AppShell } from '@/components/app-shell';
import { api } from '@/lib/api';

type Integration = { provider: string; status: string; mode: string; display_name: string; destination?: string };
type OpenRouterSettings = { provider: string; status: string; configured: boolean; model: string; key_hint?: string };
type ConnectionState = 'idle' | 'testing' | 'connected' | 'failed';

export default function Integrations() {
  const [items, setItems] = useState<Integration[]>([]);
  const [openrouter, setOpenrouter] = useState<OpenRouterSettings | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [testing, setTesting] = useState('');
  const [saving, setSaving] = useState(false);
  const [connection, setConnection] = useState<ConnectionState>('idle');
  const [message, setMessage] = useState('');

  useEffect(() => {
    Promise.all([api<Integration[]>('/integrations'), api<OpenRouterSettings>('/integrations/openrouter')])
      .then(([integrations, settings]) => { setItems(integrations); setOpenrouter(settings); setModel(settings.model); })
      .catch(() => (location.href = '/login'));
  }, []);

  async function saveOpenRouter(clearApiKey = false) {
    setSaving(true); setMessage(''); setConnection('idle');
    try {
      const result = await api<OpenRouterSettings>('/integrations/openrouter', {
        method: 'PUT', body: JSON.stringify({ api_key: apiKey || null, model, clear_api_key: clearApiKey }),
      });
      setOpenrouter(result); setApiKey('');
      setMessage(result.configured ? 'OpenRouter settings saved. Test the connection to verify them.' : 'Deterministic mode enabled. The app will run without AI calls.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not save OpenRouter settings');
    } finally { setSaving(false); }
  }

  async function test(provider: string) {
    setTesting(provider); setMessage('');
    if (provider === 'openrouter') setConnection('testing');
    try {
      const result = await api<{ status: string; model?: string }>(`/integrations/${provider}/test`, { method: 'POST' });
      if (provider === 'openrouter') setConnection('connected');
      setMessage(`${provider === 'openrouter' ? 'OpenRouter' : provider} ${result.status}${result.model ? ` with ${result.model}` : ''} — no external write was performed.`);
    } catch (error) {
      if (provider === 'openrouter') setConnection('failed');
      setMessage(error instanceof Error ? error.message : 'Test failed');
    } finally { setTesting(''); }
  }

  const official = items.some((item) => item.provider === 'slack' && item.mode === 'official');
  const status = connection === 'connected' ? 'connected' : connection === 'failed' ? 'failed' : openrouter?.configured ? 'configured' : 'deterministic';

  return <AppShell title="Integrations" eyebrow="ADMINISTRATIVE CONNECTIONS">
    <section className="integration-intro"><div><ShieldCheck /><span><h2>Preview first. Approve every write.</h2><p>Credentials remain server-side and are never exposed to agents or log evidence.</p></span></div><em><LockKeyhole />{official ? 'Official Slack mode' : 'Mock sandbox mode'}</em></section>

    <section className="openrouter-card">
      <header><Bot /><span><b>OpenRouter</b><small>Optional AI reasoning provider</small></span><em className={`provider-status ${status}`}><i />{status}</em></header>
      <div className="openrouter-copy"><h2>AI model connection</h2><p>Add a key and model to enable AI-assisted recommendations, summaries, cookbooks, and incident chat. Without a key, every feature uses deterministic local functions.</p></div>
      <div className="openrouter-fields">
        <label><span><KeyRound />API KEY</span><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={openrouter?.key_hint || 'sk-or-v1-…'} autoComplete="off" /></label>
        <label><span><Bot />MODEL</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder="provider/model-name" /></label>
      </div>
      <footer><div><button onClick={() => saveOpenRouter(false)} disabled={saving || !model.trim()}>{saving ? <LoaderCircle className="spin" /> : <Save />}Save settings</button><button onClick={() => test('openrouter')} disabled={!!testing || !openrouter?.configured}>{testing === 'openrouter' ? <LoaderCircle className="spin" /> : <PlugZap />}Test connection</button></div>{openrouter?.configured && <button className="text-button" onClick={() => saveOpenRouter(true)} disabled={saving}>Remove key &amp; use deterministic mode</button>}</footer>
    </section>

    {message && <div className={`integration-message ${connection === 'failed' ? 'failed' : ''}`}>{connection === 'failed' ? <CircleAlert /> : <CheckCircle2 />}{message}</div>}

    <section className="integration-grid">{items.map((item) => <article key={item.provider}>
      <header>{item.provider === 'slack' ? <MessageSquareText /> : <TicketCheck />}<span><b>{item.provider === 'slack' ? 'Slack' : 'Jira Cloud'}</b><small>{item.display_name}</small></span><em><i />{item.status}</em></header>
      <div><span>ADAPTER MODE</span><b>{item.mode}</b></div>{item.destination && <div><span>CHANNEL</span><b>{item.destination}</b></div>}<div><span>EXTERNAL WRITES</span><b>Human approval required</b></div><div><span>{item.provider === 'slack' ? 'SCOPE' : 'SCOPES'}</span><b>{item.provider === 'slack' ? 'chat:write' : 'read:jira-work · write:jira-work'}</b></div>
      <footer><button onClick={() => test(item.provider)} disabled={!!testing}>{testing === item.provider ? <LoaderCircle className="spin" /> : <PlugZap />}Test connection</button><a href="/architecture">Security model <ExternalLink /></a></footer>
    </article>)}</section>
  </AppShell>;
}
