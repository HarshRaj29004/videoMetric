import { useEffect, useState } from 'react';
import { askQuestion, createDocument, listDocuments } from './api';

const initialDocument = {
  title: '',
  content: '',
};

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [docForm, setDocForm] = useState(initialDocument);
  const [question, setQuestion] = useState('What does the knowledge base contain?');
  const [answer, setAnswer] = useState(null);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingAnswer, setLoadingAnswer] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    listDocuments()
      .then((items) => {
        if (active) {
          setDocuments(items);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load documents');
        }
      })
      .finally(() => {
        if (active) {
          setLoadingDocs(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleAddDocument(event) {
    event.preventDefault();
    setError('');
    setStatus('');

    if (!docForm.title.trim() || !docForm.content.trim()) {
      setError('Document title and content are required.');
      return;
    }

    try {
      const created = await createDocument({
        title: docForm.title.trim(),
        content: docForm.content.trim(),
      });
      setDocuments((current) => [created, ...current]);
      setDocForm(initialDocument);
      setStatus('Document added to the knowledge base.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add document');
    }
  }

  async function handleAsk(event) {
    event.preventDefault();
    setError('');
    setLoadingAnswer(true);

    try {
      const response = await askQuestion({ question: question.trim(), top_k: 3 });
      setAnswer(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ask question');
    } finally {
      setLoadingAnswer(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">videoMetric starter</p>
          <h1>Basic RAG stack with a polished local workflow.</h1>
          <p className="hero-copy">
            Add documents, query them from the React UI, and route retrieval through the FastAPI backend.
            The backend falls back gracefully if no LLM key is configured.
          </p>
        </div>
        <div className="hero-panel">
          <div>
            <span>Frontend</span>
            <strong>React + Vite</strong>
          </div>
          <div>
            <span>Backend</span>
            <strong>FastAPI + RAG</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{loadingDocs ? 'Loading knowledge base...' : `${documents.length} docs ready`}</strong>
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <div className="card-header">
            <h2>Add document</h2>
            <p>Seed the in-memory knowledge base with content for retrieval.</p>
          </div>
          <form onSubmit={handleAddDocument} className="form">
            <label>
              Title
              <input
                value={docForm.title}
                onChange={(event) => setDocForm((current) => ({ ...current, title: event.target.value }))}
                placeholder="Example: Product FAQ"
              />
            </label>
            <label>
              Content
              <textarea
                value={docForm.content}
                onChange={(event) => setDocForm((current) => ({ ...current, content: event.target.value }))}
                placeholder="Paste a short note, policy, or knowledge article here."
                rows={6}
              />
            </label>
            <button type="submit">Add to knowledge base</button>
          </form>
        </article>

        <article className="card">
          <div className="card-header">
            <h2>Ask a question</h2>
            <p>The backend will retrieve the most relevant documents and generate a grounded answer.</p>
          </div>
          <form onSubmit={handleAsk} className="form">
            <label>
              Question
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={5}
              />
            </label>
            <button type="submit" disabled={loadingAnswer}>
              {loadingAnswer ? 'Thinking...' : 'Ask'}
            </button>
          </form>
        </article>
      </section>

      <section className="card results">
        <div className="card-header">
          <h2>Response</h2>
          <p>{status || 'Answers and retrieval context appear here.'}</p>
        </div>
        {error ? <div className="alert error">{error}</div> : null}
        {answer ? (
          <div className="response">
            <p className="answer">{answer.answer}</p>
            <div className="context-block">
              <h3>Retrieved context</h3>
              <pre>{answer.context}</pre>
            </div>
            <div className="sources-block">
              <h3>Sources</h3>
              <ul>
                {answer.sources.map((source) => (
                  <li key={source.id}>
                    <strong>{source.title}</strong>
                    <span>score {source.score}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <p className="placeholder">Submit a question to see the retrieval output.</p>
        )}
      </section>

      <section className="card documents">
        <div className="card-header">
          <h2>Loaded documents</h2>
          <p>These are currently available to the retrieval layer.</p>
        </div>
        <div className="document-list">
          {documents.length === 0 ? (
            <p className="placeholder">No documents loaded yet.</p>
          ) : (
            documents.map((document) => (
              <article key={document.id} className="document-item">
                <h3>{document.title}</h3>
                <p>{document.content}</p>
              </article>
            ))
          )}
        </div>
      </section>
    </main>
  );
}