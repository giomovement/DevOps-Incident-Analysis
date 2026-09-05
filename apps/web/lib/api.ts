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
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, credentials: 'include' });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText })) as { detail?: string };
    throw new Error(body.detail || 'Request failed');
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
