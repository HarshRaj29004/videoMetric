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
  return request('/ingestion/data-ingest', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function askSessionQuestion(input) {
  return request('/ingestion/data-retreive', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function askGraphChat(input) {
  // The backend exposes a streaming chat at POST /ingestion (SSE/text stream).
  // Perform a fetch and stream tokens, assembling them into a single answer string.
  return (async () => {
    const res = await fetch(`${API_URL}/ingestion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });

    if (!res.ok) {
      const message = await res.text();
      throw new Error(message || `Request failed with ${res.status}`);
    }

    if (!res.body) {
      // No streaming body — fall back to reading as text
      const text = await res.text();
      return { answer: text };
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let answer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE messages are typically separated by a double newline. Parse any complete messages.
      const parts = buffer.split('\n\n');
      buffer = parts.pop(); // remainder
      for (const part of parts) {
        // each part can contain lines like 'data: <token>'
        for (const line of part.split('\n')) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith('data:')) {
            const data = trimmed.slice(5).trim();
            if (data === '[DONE]') continue;
            // append data to answer
            answer += data;
          } else {
            // fallback: append raw line
            answer += trimmed;
          }
        }
      }
    }

    // flush any remaining buffer
    if (buffer) {
      for (const line of buffer.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        if (trimmed.startsWith('data:')) {
          const data = trimmed.slice(5).trim();
          if (data !== '[DONE]') answer += data;
        } else {
          answer += trimmed;
        }
      }
    }

    return { answer };
  })();
}

export function clearSessionVectorDb() {
  return request('/ingestion/data-delete', {
    method: 'DELETE',
  });
}
