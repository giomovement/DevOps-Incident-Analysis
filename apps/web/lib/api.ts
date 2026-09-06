export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8010/api/v1';

function cookie(name: string) {
  if (typeof document === 'undefined') return '';
  return document.cookie.split('; ').find((value) => value.startsWith(`${name}=`))?.split('=')[1] || '';
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && init.body && !headers.has('content-type')) headers.set('content-type', 'application/json');
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('x-csrf-token', decodeURIComponent(cookie('dias_csrf')));
  const response = await fetch(`${API_URL}${path}`, { cache: 'no-store', ...init, headers, credentials: 'include' });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText })) as { detail?: string };
    throw new Error(body.detail || 'Request failed');
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function streamApi(path: string, init: RequestInit, onEvent: (event: string, data: Record<string, unknown>) => void) {
  const headers = new Headers(init.headers);
  headers.set('content-type', 'application/json');
  headers.set('x-csrf-token', decodeURIComponent(cookie('dias_csrf')));
  headers.set('accept', 'text/event-stream');
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include' });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({ detail: response.statusText })) as { detail?: string };
    throw new Error(body.detail || 'Request failed');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';
    for (const item of events) {
      const event = item.match(/^event: (.+)$/m)?.[1] || 'message';
      const raw = item.match(/^data: (.+)$/m)?.[1];
      if (raw) onEvent(event, JSON.parse(raw) as Record<string, unknown>);
    }
    if (done) break;
  }
}
