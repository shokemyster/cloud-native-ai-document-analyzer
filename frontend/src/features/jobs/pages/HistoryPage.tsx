import { Link } from 'react-router-dom'

export function HistoryPage() {
  return (
    <section aria-labelledby="history-heading">
      <header className="page-header">
        <h1 id="history-heading">Processing history</h1>
        <p className="page-description">
          Review queued, running, completed, and failed analysis jobs.
        </p>
      </header>

      <div className="panel">
        <h2>No analysis jobs yet</h2>
        <p className="page-description">
          Job history will appear here after the frontend is connected to the
          backend API.
        </p>
        <p>
          <Link className="text-link" to="/upload">
            Upload a document
          </Link>
        </p>
      </div>
    </section>
  )
}
