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

export function ingestTranscript(input) {
  return request('/ingestion/', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function askSessionQuestion(input) {
  return request('/ingestion/chat', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function clearSessionVectorDb() {
  return request('/ingestion/vector-db', {
    method: 'DELETE',
  });
}
