const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request(path, init) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }

  return response.json();
}

export function getHealth() {
  return request('/health');
}

export function getMediaMetadata(input) {
  return request('/scraper', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getTranscript(input) {
  return request('/scraper/transcript', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}
