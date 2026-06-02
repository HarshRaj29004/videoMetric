import { useEffect, useState } from 'react';
import { askGraphChat, clearSessionVectorDb, getHealth, ingestTranscript } from './api';

const INITIAL_ASSISTANT_MESSAGE = {
  role: 'assistant',
  text: 'Provide two video URLs, start the session, and then ask questions about the stored transcripts.',
};

const STORAGE_KEY = 'Local_storage_key';

function formatError(error) {
  return error instanceof Error ? error.message : 'Request failed';
}

function ChatMessage({ message }) {
  return (
    <article className={`chat-message ${message.role}`}>
      <span className="message-role">{message.role === 'user' ? 'You' : 'Assistant'}</span>
      <p>{message.text}</p>
      {message.context ? (
        <div className="mini-panel">
          <strong>Context</strong>
          <pre>{message.context}</pre>
        </div>
      ) : null}
      {Array.isArray(message.sources) && message.sources.length ? (
        <div className="source-list">
          {message.sources.map((source) => (
            <article key={source.id}>
              <strong>{source.title}</strong>
              <span>{source.content}</span>
            </article>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function App() {
  const [userId] = useState(() => {
    const USER_ID_KEY = 'videometric_user_id';
    const existing = window.localStorage.getItem(USER_ID_KEY);
    if (existing) return existing;
    const created = window.crypto.randomUUID();
    window.localStorage.setItem(USER_ID_KEY, created);
    return created;
  });
  const [chatId] = useState(() => window.crypto.randomUUID());
  const [health, setHealth] = useState(null);
  const [videoUrls, setVideoUrls] = useState({
    first: '',
    second: '',
  });
  const [ingestedVideos, setIngestedVideos] = useState(() => {
    const cached = window.localStorage.getItem(STORAGE_KEY);
    return cached ? JSON.parse(cached) : [];
  });
  const [sessionReady, setSessionReady] = useState(() => {
    return window.localStorage.getItem(STORAGE_KEY) !== null;
  });
  const [sessionStatus, setSessionStatus] = useState(() => {
    return window.localStorage.getItem(STORAGE_KEY) ? 'ready' : 'idle';
  });
  const [statusMessage, setStatusMessage] = useState(() => {
    return window.localStorage.getItem(STORAGE_KEY) 
      ? 'Restored session from cache. Two videos are stored in the vector database. Chat is enabled.' 
      : 'No session is active.';
  });
  const [messages, setMessages] = useState(() => {
    const cached = window.localStorage.getItem(STORAGE_KEY);
    return cached 
      ? [
          INITIAL_ASSISTANT_MESSAGE,
          {
            role: 'assistant',
            text: 'Active session restored. Ask about either transcript and I will ground the response in the stored chunks.',
          }
        ]
      : [INITIAL_ASSISTANT_MESSAGE];
  });

  const [question, setQuestion] = useState('');
  const [loadingSession, setLoadingSession] = useState(false);
  const [sendingChat, setSendingChat] = useState(false);
  const [endingSession, setEndingSession] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    getHealth()
      .then((status) => {
        if (active) {
          setHealth(status);
        }
      })
      .catch(() => {
        if (active) {
          setHealth(null);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function startSession(event) {
    event.preventDefault();

    const trimmedFirst = videoUrls.first.trim();
    const trimmedSecond = videoUrls.second.trim();

    if (!trimmedFirst || !trimmedSecond) {
      setError('Both video URLs are required.');
      return;
    }

    setError('');
    setLoadingSession(true);
    setSessionStatus('preparing');
    setStatusMessage('Clearing any previous session data...');

    try {
      await clearSessionVectorDb();

      setStatusMessage('Ingesting the first video...');
      const firstResult = await ingestTranscript({ url: trimmedFirst });

      setStatusMessage('Ingesting the second video...');
      const secondResult = await ingestTranscript({ url: trimmedSecond });

      const firstVidId = firstResult?.video_id ?? null;
      const secondVidId = secondResult?.video_id ?? null;

      const updatedVideos = [
        { url: trimmedFirst, video_id: firstVidId, result: firstResult },
        { url: trimmedSecond, video_id: secondVidId, result: secondResult },
      ];

      // Cache the entire result object containing source, video_id, and title to localStorage
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedVideos));

      setIngestedVideos(updatedVideos);
      // setSelectedVideoId(firstVidId || secondVidId);
      setSessionReady(true);
      setSessionStatus('ready');
      setStatusMessage('Two videos are stored in the vector database. Chat is now enabled.');
      setMessages([
        INITIAL_ASSISTANT_MESSAGE,
        {
          role: 'assistant',
          text: 'The session is ready. Ask about either transcript and I will ground the response in the stored chunks.',
        },
      ]);
      setQuestion('');
    } catch (submissionError) {
      setSessionReady(false);
      setSessionStatus('idle');
      setStatusMessage('No session is active.');
      setIngestedVideos([]);
      setMessages([INITIAL_ASSISTANT_MESSAGE]);
      setError(formatError(submissionError));
    } finally {
      setLoadingSession(false);
    }
  }

  async function sendChat(event) {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (!sessionReady || !trimmedQuestion) {
      return;
    }

    setError('');
    setSendingChat(true);

    try {
      setMessages((currentMessages) => [
        ...currentMessages,
        { role: 'user', text: trimmedQuestion },
      ]);

      const userContent = ingestedVideos

      if (userContent.length < 2) {
        throw new Error('Both ingested video IDs were not found. Re-ingest the videos and try again.');
      }

      const response = await askGraphChat({
        query: trimmedQuestion,
        userContent: userContent,
        user_id: userId,
        chat_id: chatId,
      });

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          text: response.answer || 'No answer returned.',
        },
      ]);
      setQuestion('');
    } catch (submissionError) {
      setError(formatError(submissionError));
    } finally {
      setSendingChat(false);
    }
  }

  async function endSession() {
    setError('');
    setEndingSession(true);

    try {
      await clearSessionVectorDb();
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (submissionError) {
      setError(formatError(submissionError));
      return;
    } finally {
      setEndingSession(false);
    }

    setSessionReady(false);
    setSessionStatus('ended');
    setStatusMessage('Session ended and vector data was deleted.');
    setIngestedVideos([]);
    setMessages([INITIAL_ASSISTANT_MESSAGE]);
    setQuestion('');
  }

  return (
    <main className="shell">
      <header className="hero session-hero">
        <div>
          <p className="eyebrow">videoMetric session workspace</p>
          <h1>Load two videos, then chat against the stored transcripts.</h1>
          <p className="hero-copy">
            The session flow now matches the backend ingestion router: submit two URLs, store their transcripts and metadata in the vector database,
            chat while the session is active, and clear the data when the session ends.
          </p>
        </div>
        <div className="hero-panel">
          <div>
            <span>Backend</span>
            <strong>{health ? `Connected: ${health.status}` : 'Offline or not reachable'}</strong>
          </div>
          <div>
            <span>Session</span>
            <strong>{sessionStatus}</strong>
          </div>
          <div>
            <span>Storage</span>
            <strong>{sessionReady ? 'Vector DB populated' : 'No active session data'}</strong>
          </div>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}

      <section className="layout-shell">
        <aside className="card sidebar-card">
          <div className="card-header">
            <h2>Video setup</h2>
            <p>Add two URLs to unlock chat.</p>
          </div>

          <form className="form" onSubmit={startSession}>
            <label>
              Video URL 1
              <input
                value={videoUrls.first}
                onChange={(event) => setVideoUrls((current) => ({ ...current, first: event.target.value }))}
                placeholder="https://www.youtube.com/watch?v=..."
              />
            </label>
            <label>
              Video URL 2
              <input
                value={videoUrls.second}
                onChange={(event) => setVideoUrls((current) => ({ ...current, second: event.target.value }))}
                placeholder="https://www.youtube.com/watch?v=..."
              />
            </label>
            <button type="submit" disabled={loadingSession}>
              {loadingSession ? 'Starting session...' : 'Ingest 2 videos'}
            </button>
          </form>

          <div className="context-block status-block">
            <h3>Session status</h3>
            <p>{statusMessage}</p>
          </div>

          {ingestedVideos.length ? (
            <div className="sources-block">
              <h3>Stored videos</h3>
              <div className="stack">
                {ingestedVideos.map((entry, index) => (
                  <article className="route-card" key={`${entry.url}-${index}`}>
                    <strong>Video {index + 1}</strong>
                    <span>{entry.url}</span>
                    <pre>{JSON.stringify(entry.result, null, 2)}</pre>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </aside>

        <article className="card chat-panel main-chat-panel">
          <div className="card-header">
            <h2>Chat</h2>
            <p>{sessionReady ? 'Ask questions about the loaded videos.' : 'Chat becomes available after both videos are stored.'}</p>
          </div>

          <div className={`chat-status ${sessionReady ? 'ready' : 'disabled'}`}>
            {sessionReady ? 'Chat is enabled.' : 'Chat is disabled until the session is ready.'}
          </div>

          <form className="form chat-form" onSubmit={sendChat}>
            <label>
              Your question
              <textarea
                rows={4}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What are the main points covered across both videos?"
                disabled={!sessionReady}
              />
            </label>
            {/* <label>
              Select video (optional)
              <select value={selectedVideoId ?? ''} onChange={(e) => setSelectedVideoId(e.target.value || null)} disabled={!sessionReady}>
                <option value="">All videos</option>
                {ingestedVideos.map((v, i) => (
                  <option key={`${v.video_id}-${i}`} value={v.video_id || ''}>
                    {v.video_id ? `${v.video_id} — ${v.url}` : `Video ${i + 1} — ${v.url}`}
                  </option>
                ))}
              </select>
            </label> */}
            <div className="button-row">
              <button type="submit" disabled={!sessionReady || sendingChat}>
                {sendingChat ? 'Sending...' : 'Send question'}
              </button>
              <button type="button" className="secondary-button" onClick={endSession} disabled={!sessionReady || endingSession}>
                {endingSession ? 'Ending...' : 'End session and clear data'}
              </button>
            </div>
          </form>

          <div className="chat-thread">
            {messages.map((message, index) => (
              <ChatMessage key={`${message.role}-${index}-${message.text.slice(0, 20)}`} message={message} />
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}

export default App;
