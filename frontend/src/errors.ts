function describe(value: unknown): string | null {
  if (typeof value === 'string') return value.trim() || null;
  if (Array.isArray(value)) {
    const messages = value.map(describe).filter((item): item is string => Boolean(item));
    return messages.length ? messages.join('; ') : null;
  }
  if (!value || typeof value !== 'object') return null;

  const issue = value as Record<string, unknown>;
  if (typeof issue.msg === 'string') {
    const location = Array.isArray(issue.loc)
      ? issue.loc.filter((part) => part !== 'body' && part !== 'query').join('.')
      : '';
    return location ? `${location}: ${issue.msg}` : issue.msg;
  }
  for (const key of ['detail', 'message', 'error']) {
    if (issue[key] !== undefined) {
      const message = describe(issue[key]);
      if (message) return message;
    }
  }
  try {
    return JSON.stringify(value);
  } catch {
    return null;
  }
}

export function formatError(error: unknown, apiBaseUrl = 'http://127.0.0.1:8010/api'): string {
  if (import.meta.env.DEV) console.error('CivicPulse request failed:', error);

  const maybe = error && typeof error === 'object' ? error as Record<string, unknown> : null;
  const response = maybe?.response && typeof maybe.response === 'object'
    ? maybe.response as Record<string, unknown>
    : null;
  const payload = response?.data ?? maybe?.payload ?? maybe;
  const detail = describe(payload);
  const safeDetail = detail && !detail.includes('[object Object]') ? detail : null;
  const message = error instanceof Error ? error.message : describe(error);
  const combined = [detail, message].filter((item): item is string => Boolean(item)).join(' ');

  if (/failed to fetch|network(error| request failed)?|econnrefused|connection refused|load failed/i.test(combined)) {
    return `Cannot reach the CivicPulse API at ${apiBaseUrl}. Check that the backend is running and VITE_API_URL points to it.`;
  }

  if (safeDetail && (!message || message === '[object Object]' || message.includes('[object Object]'))) {
    const status = typeof maybe?.status === 'number' ? ` (HTTP ${maybe.status})` : '';
    return `Request failed${status}: ${safeDetail}`;
  }
  if (message && message !== '[object Object]' && !message.includes('[object Object]')) return message;
  return safeDetail || 'Something went wrong. Please retry.';
}
