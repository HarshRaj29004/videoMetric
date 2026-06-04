import { useEffect, useState, useRef } from 'react';
import { askGraphChat, clearSessionVectorDb, getHealth, ingestTranscript } from './api';

const INITIAL_ASSISTANT_MESSAGE = {
  role: 'assistant',
  text: 'Provide two video URLs in the sidebar, start the session, and ask questions about the stored transcripts here.',
};

const STORAGE_KEY = 'Local_storage_key';

function formatError(error) {
  return error instanceof Error ? error.message : 'Request failed';
}

function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`chat-message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? 'U' : 'A'}
      </div>
      <div className="bubble">
        <p>{message.text}</p>
        {message.context ? (
          <div className="mini-panel" style={{ marginTop: '0.75rem' }}>
            <strong style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Source Context Excerpt</strong>
            <pre>{message.context}</pre>
          </div>
        ) : null}
        {Array.isArray(message.sources) && message.sources.length ? (
          <div className="source-list" style={{ marginTop: '0.75rem' }}>
            {message.sources.map((source) => (
              <article key={source.id} style={{ padding: '0.65rem', borderRadius: '8px', background: 'rgba(0,0,0,0.2)' }}>
                <strong style={{ fontSize: '0.8rem', display: 'block' }}>{source.title}</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{source.content}</span>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </div>
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
  
  // Expand/collapse state for raw metadata viewer
  const [expandedVideo, setExpandedVideo] = useState({ 0: false, 1: false });
  const [workflowSteps, setWorkflowSteps] = useState([]);

  const chatEndRef = useRef(null);
  const chatThreadContainerRef = useRef(null);

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

  // Auto-scroll chat window to bottom
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, sendingChat]);

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

      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedVideos));

      setIngestedVideos(updatedVideos);
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
    if (event) {
      event.preventDefault();
    }

    const trimmedQuestion = question.trim();
    if (!sessionReady || !trimmedQuestion || sendingChat) {
      return;
    }

    setError('');
    setSendingChat(true);
    setQuestion('');
    setWorkflowSteps([]);

    try {
      setMessages((currentMessages) => [
        ...currentMessages,
        { role: 'user', text: trimmedQuestion },
      ]);

      const userContent = ingestedVideos;

      if (userContent.length < 2) {
        throw new Error('Both ingested video IDs were not found. Re-ingest the videos and try again.');
      }

      const response = await askGraphChat({
        query: trimmedQuestion,
        userContent: userContent,
        user_id: userId,
        chat_id: chatId,
      }, (eventData) => {
        setWorkflowSteps((prevSteps) => {
          if (eventData.type === 'node_start') {
            const updated = prevSteps.map(step => step.status === 'active' ? { ...step, status: 'complete' } : step);
            let label = eventData.node;
            let desc = '';
            if (eventData.node === 'researcher') {
              label = 'Researcher Agent';
              desc = 'Analyzing query to plan database metrics & transcript search tool lookup...';
            } else if (eventData.node === 'copywriter') {
              label = 'Copywriter Agent';
              desc = 'Synthesizing raw findings into strategic report response...';
            } else if (eventData.node === 'tools') {
              label = 'Tools Node';
              desc = 'Executing operations...';
            }
            return [
              ...updated,
              {
                id: `node-${eventData.node}-${Date.now()}`,
                type: 'node',
                name: eventData.node,
                label,
                status: 'active',
                desc
              }
            ];
          } else if (eventData.type === 'tool_start') {
            const updated = prevSteps.map(step => step.status === 'active' ? { ...step, status: 'complete' } : step);
            let label = `Tool: ${eventData.tool}`;
            let desc = `Invoking with args: ${JSON.stringify(eventData.input)}`;
            if (eventData.tool === 'get_video_metadata') {
              label = 'Tool: get_video_metadata';
              desc = `Fetching views, likes, and comments for Video: ${eventData.input.video_id || ''}...`;
            } else if (eventData.tool === 'search_transcript') {
              label = 'Tool: search_transcript';
              desc = `Searching transcript excerpts for query: "${eventData.input.query || ''}"...`;
            }
            return [
              ...updated,
              {
                id: `tool-${eventData.tool}-${Date.now()}`,
                type: 'tool',
                name: eventData.tool,
                label,
                status: 'active',
                desc
              }
            ];
          } else if (eventData.type === 'tool_end') {
            return prevSteps.map(step => {
              if (step.type === 'tool' && step.name === eventData.tool && step.status === 'active') {
                let customDesc = step.desc;
                if (eventData.tool === 'get_video_metadata') {
                  customDesc = 'Metadata retrieved successfully.';
                } else if (eventData.tool === 'search_transcript') {
                  customDesc = 'Transcript segments retrieved successfully.';
                }
                return {
                  ...step,
                  status: 'complete',
                  desc: `${customDesc} Output: ${eventData.output}`
                };
              }
              return step;
            });
          } else if (eventData.type === 'node_end') {
            return prevSteps.map(step => 
              step.type === 'node' && step.name === eventData.node && step.status === 'active'
                ? { ...step, status: 'complete' }
                : step
            );
          }
          return prevSteps;
        });
      });

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: 'assistant',
          text: response.answer || 'No answer returned.',
        },
      ]);
    } catch (submissionError) {
      setError(formatError(submissionError));
    } finally {
      setSendingChat(false);
      setWorkflowSteps((prevSteps) => prevSteps.map(step => step.status === 'active' ? { ...step, status: 'complete' } : step));
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
    setVideoUrls({ first: '', second: '' });
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChat();
    }
  }

  return (
    <div className="app-container">
      {/* Alert Banner for Errors */}
      {error ? (
        <div className="alert-error">
          <span>⚠️ {error}</span>
          <button className="alert-close" onClick={() => setError('')}>×</button>
        </div>
      ) : null}

      {/* Sidebar Section */}
      <aside className="sidebar">
        <header className="sidebar-header">
          <div className="logo-icon">vM</div>
          <h1>videoMetric</h1>
        </header>

        <div className="sidebar-scroll-area">
          {/* Section 1: Video Ingestion Setup */}
          <section>
            <h2 className="sidebar-section-title">Video Ingest Workspace</h2>
            <form className="sidebar-form" onSubmit={startSession}>
              <div className="input-group">
                <span>Video URL 1</span>
                <input
                  value={videoUrls.first}
                  onChange={(event) => setVideoUrls((current) => ({ ...current, first: event.target.value }))}
                  placeholder="https://www.youtube.com/watch?v=..."
                  disabled={loadingSession}
                  required
                />
              </div>
              <div className="input-group">
                <span>Video URL 2</span>
                <input
                  value={videoUrls.second}
                  onChange={(event) => setVideoUrls((current) => ({ ...current, second: event.target.value }))}
                  placeholder="https://www.instagram.com/reel/..."
                  disabled={loadingSession}
                  required
                />
              </div>
              <button className="btn-primary" type="submit" disabled={loadingSession}>
                {loadingSession ? 'Ingesting data...' : 'Start Session & Ingest'}
              </button>
            </form>
          </section>

          {/* Section 2: System Execution Flow */}
          <section>
            <h2 className="sidebar-section-title">Agent Workflow</h2>
            <div className="sidebar-status-card" style={{ padding: '1rem 0.75rem' }}>
              {workflowSteps.length === 0 ? (
                <div className="empty-flow-placeholder" style={{ padding: '0.5rem 0.25rem' }}>
                  <span className="status-badge idle" style={{ display: 'inline-block', marginBottom: '0.5rem' }}>System Idle</span>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>Submit a prompt to inspect agent execution steps and tools in real-time.</p>
                </div>
              ) : (
                <div className="workflow-timeline">
                  {workflowSteps.map((step, idx) => (
                    <div key={step.id} className={`workflow-step ${step.status}`}>
                      <div className="workflow-step-marker">
                        <span className="workflow-dot" />
                        {idx < workflowSteps.length - 1 && <span className="workflow-line" />}
                      </div>
                      <div className="workflow-step-content">
                        <div className="workflow-step-header">
                          <span className="workflow-step-icon">
                            {step.name === 'researcher' ? '🔍' : step.name === 'copywriter' ? '✍️' : '🛠️'}
                          </span>
                          <span className="workflow-step-label">{step.label}</span>
                        </div>
                        <p className="workflow-step-desc">{step.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* Section 3: Loaded Video Content details */}
          {ingestedVideos.length ? (
            <section>
              <h2 className="sidebar-section-title">Session Sources</h2>
              <div className="video-cards-container">
                {ingestedVideos.map((entry, index) => (
                  <article className="video-card" key={`${entry.url}-${index}`}>
                    <div className="video-card-title-row">
                      <div className="video-index-badge">{index + 1}</div>
                      <h3>{entry.result?.title || 'Ingested Video'}</h3>
                    </div>
                    <div className="video-card-url" title={entry.url}>
                      {entry.url}
                    </div>
                    <button
                      className="video-card-details-btn"
                      onClick={() => setExpandedVideo((curr) => ({ ...curr, [index]: !curr[index] }))}
                    >
                      {expandedVideo[index] ? 'Hide metadata' : 'View raw metadata'}
                    </button>
                    {expandedVideo[index] ? (
                      <pre className="video-card-meta-view">
                        {JSON.stringify(entry.result, null, 2)}
                      </pre>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        {/* Footer actions inside Sidebar */}
        <footer className="sidebar-footer">
          <button
            className="btn-secondary"
            onClick={endSession}
            disabled={!sessionReady || endingSession}
          >
            {endingSession ? 'Clearing session...' : 'End Session & Clear DB'}
          </button>
        </footer>
      </aside>

      {/* Main Chat Area */}
      <section className="chat-area">
        {/* Chat Area Header */}
        <header className="chat-header">
          <div className="chat-header-title">
            <h2>Chat Assistant</h2>
            <div className={`chat-header-status-indicator ${sessionReady ? 'ready' : ''}`} />
          </div>
        </header>

        {/* Chat Messages Scrolling Area */}
        <div className="chat-thread-container" ref={chatThreadContainerRef}>
          {messages.length <= 1 && !sendingChat ? (
            <div className="empty-chat-state">
              <div className="empty-chat-icon">💬</div>
              <h2>videoMetric Agent Workspace</h2>
              <p>
                Configure two video URLs in the sidebar to populate the vector database and unlock strategic insights. 
                Ask queries abouthooks, comparison metrics, storytelling strategies, or transcript details.
              </p>
            </div>
          ) : (
            <div className="chat-thread-wrapper">
              {messages.map((message, index) => (
                <ChatMessage key={`${message.role}-${index}`} message={message} />
              ))}
              {sendingChat ? (
                <div className="chat-message-row assistant">
                  <div className="avatar assistant">A</div>
                  <div className="bubble" style={{ opacity: 0.65 }}>
                    <p>Agent is thinking and executing tools in the background...</p>
                  </div>
                </div>
              ) : null}
              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Chat Input Bar */}
        <footer className="chat-input-container">
          <div className="chat-input-wrapper">
            <form className="chat-input-bar" onSubmit={(e) => { e.preventDefault(); sendChat(); }}>
              <textarea
                rows={1}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={sessionReady ? "Compare the hook engagement or strategy across both videos..." : "Connect a session via sidebar first to unlock chat"}
                disabled={!sessionReady || sendingChat}
              />
              <button
                className="send-btn"
                type="submit"
                disabled={!sessionReady || !question.trim() || sendingChat}
                title="Send message"
              >
                <svg viewBox="0 0 24 24">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </form>
            <p className="input-info-text">
              Press Enter to send. Shift + Enter for newlines. Questions are grounded in ingested YouTube and Instagram transcripts.
            </p>
          </div>
        </footer>
      </section>
    </div>
  );
}

export default App;
