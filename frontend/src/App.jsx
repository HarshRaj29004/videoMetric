import { useEffect, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { getHealth, getMediaMetadata, getTranscript } from './api';

const DEFAULT_YOUTUBE_URL = 'https://www.youtube.com/watch?v=XuIswf2NauQ';

function Layout({ children, subtitle }) {
  const location = useLocation();

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">videoMetric router demo</p>
          <h1>Route-first UI for media metadata and transcripts.</h1>
          <p className="hero-copy">
            Use the navigation to switch between scraping media details and extracting transcripts.
            The interface talks directly to the FastAPI routers.
          </p>
        </div>
        <div className="hero-panel">
          <div>
            <span>Backend</span>
            <strong>FastAPI routers</strong>
          </div>
          <div>
            <span>Current route</span>
            <strong>{location.pathname}</strong>
          </div>
          <div>
            <span>Focus</span>
            <strong>{subtitle}</strong>
          </div>
        </div>
      </header>

      <nav className="top-nav">
        <NavLink to="/" end>
          Home
        </NavLink>
        <NavLink to="/metadata">Metadata</NavLink>
        <NavLink to="/transcript">Transcript</NavLink>
      </nav>

      {children}
    </main>
  );
}

function HomePage({ health }) {
  const cards = [
    {
      title: 'Metadata',
      copy: 'Inspect media info from the /scraper router.',
      to: '/metadata',
    },
    {
      title: 'Transcript',
      copy: 'Pull YouTube captions or Instagram Whisper output from /scraper/transcript.',
      to: '/transcript',
    },
  ];

  return (
    <section className="grid single-grid">
      <article className="card">
        <div className="card-header">
          <h2>Backend status</h2>
          <p>{health ? `Connected: ${health.status}` : 'Checking backend...'}</p>
        </div>
        <div className="stack">
          {cards.map((card) => (
            <NavLink key={card.title} to={card.to} className="route-card">
              <strong>{card.title}</strong>
              <span>{card.copy}</span>
            </NavLink>
          ))}
        </div>
      </article>
    </section>
  );
}

function MediaForm({
  title,
  description,
  buttonLabel,
  onSubmit,
  defaultUrl,
  resultRenderer,
}) {
  const [url, setUrl] = useState(defaultUrl);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await onSubmit({ url: url.trim() });
      setResult(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid">
      <article className="card">
        <div className="card-header">
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <form onSubmit={handleSubmit} className="form">
          <label>
            Media URL
            <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder={defaultUrl} />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? 'Working...' : buttonLabel}
          </button>
        </form>
        {error ? <div className="alert error">{error}</div> : null}
      </article>

      <article className="card results">
        <div className="card-header">
          <h2>Result</h2>
          <p>Response from the backend route appears below.</p>
        </div>
        {result ? resultRenderer(result) : <p className="placeholder">Submit a URL to see the response.</p>}
      </article>
    </section>
  );
}

function MetadataPage() {
  return (
    <Layout subtitle="Media metadata">
      <MediaForm
        title="Scrape metadata"
        description="Calls POST /scraper and returns title, duration, uploader, and related media details."
        buttonLabel="Fetch metadata"
        defaultUrl={DEFAULT_YOUTUBE_URL}
        onSubmit={getMediaMetadata}
        resultRenderer={(result) => (
          <div className="response">
            <p className="answer">{result.title || 'No title returned.'}</p>
            <div className="context-block">
              <h3>Key fields</h3>
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </div>
          </div>
        )}
      />
    </Layout>
  );
}

function TranscriptPage() {
  return (
    <Layout subtitle="Transcript extraction">
      <MediaForm
        title="Extract transcript"
        description="Calls POST /scraper/transcript. YouTube uses captions; Instagram downloads audio and runs Whisper."
        buttonLabel="Get transcript"
        defaultUrl={DEFAULT_YOUTUBE_URL}
        onSubmit={({ url }) => getTranscript({ url })}
        resultRenderer={(result) => (
          <div className="response">
            <p className="answer">
              {result.method} · {result.source}
            </p>

            <div className="context-block">
              <h3>Summary</h3>
              <pre>{result.transcript || 'No transcript returned.'}</pre>
            </div>

            {Array.isArray(result.segments) && result.segments.length ? (
              <div className="sources-block">
                <h3>Video Segments</h3>
                <div className="stack">
                  {result.segments.map((segment, index) => (
                    <article className="route-card" key={`${segment.start}-${index}`}>
                      <strong>Segment {index + 1}</strong>
                      <span>
                        {segment.start.toFixed(2)}s - {(segment.start + segment.duration).toFixed(2)}s
                      </span>
                      <pre>{segment.text}</pre>
                    </article>
                  ))}
                </div>
              </div>
            ) : null}

            {result.metadata ? (
              <div className="sources-block">
                <h3>Metadata</h3>
                <pre>{JSON.stringify(result.metadata, null, 2)}</pre>
              </div>
            ) : null}
          </div>
        )}
      />
    </Layout>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);

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

  return (
    <Routes>
      <Route
        path="/"
        element={
          <Layout subtitle="Quick links">
            <HomePage health={health} />
          </Layout>
        }
      />
      <Route path="/metadata" element={<MetadataPage />} />
      <Route path="/transcript" element={<TranscriptPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}