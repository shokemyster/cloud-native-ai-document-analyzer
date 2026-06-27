import { Link, useParams } from 'react-router-dom'

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()

  return (
    <section aria-labelledby="job-detail-heading">
      <header className="page-header">
        <h1 id="job-detail-heading">Job detail</h1>
        <p className="page-description">
          Job ID: <strong>{jobId ?? 'Unavailable'}</strong>
        </p>
      </header>

      <div className="panel">
        <h2>Job data is not available</h2>
        <p className="page-description">
          Status, attempts, errors, and analysis results will appear here when
          the job API is connected.
        </p>
        <p>
          <Link className="text-link" to="/history">
            Return to processing history
          </Link>
        </p>
      </div>
    </section>
  )
}
