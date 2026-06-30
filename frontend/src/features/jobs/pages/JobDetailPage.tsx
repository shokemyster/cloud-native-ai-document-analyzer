import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, getProcessingJob } from '../../../lib/api'
import type { JobStatus, ProcessingJob } from '../../../types/api'
import styles from './JobDetailPage.module.css'

const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set([
  'completed',
  'enqueue_failed',
  'failed',
])

function formatStatus(status: JobStatus) {
  return status.replace('_', ' ')
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'Not yet'
}

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [job, setJob] = useState<ProcessingJob | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) {
      return
    }

    const resolvedJobId = jobId
    const controller = new AbortController()
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    async function loadJob() {
      try {
        const nextJob = await getProcessingJob(resolvedJobId, controller.signal)
        setJob(nextJob)
        setErrorMessage(null)
        setIsLoading(false)

        if (!TERMINAL_STATUSES.has(nextJob.status)) {
          timeoutId = setTimeout(loadJob, 2000)
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }

        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : 'Could not load processing status from the backend API.',
        )
        setIsLoading(false)
      }
    }

    void loadJob()

    return () => {
      controller.abort()
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }, [jobId])

  if (!jobId) {
    return <p className={styles.error}>A job ID is required.</p>
  }

  return (
    <section aria-labelledby="job-detail-heading" aria-live="polite">
      <header className="page-header">
        <h1 id="job-detail-heading">Job detail</h1>
        <p className="page-description">
          Job ID: <strong>{jobId}</strong>
        </p>
      </header>

      <div className="panel">
        {isLoading ? <p>Loading processing status…</p> : null}

        {errorMessage ? (
          <p className={styles.error} role="alert">
            {errorMessage}
          </p>
        ) : null}

        {job ? (
          <>
            <span className={styles.status}>{formatStatus(job.status)}</span>
            <dl className={styles.details}>
              <dt>Document ID</dt>
              <dd>{job.document_id}</dd>
              <dt>Attempts</dt>
              <dd>{job.attempt_count}</dd>
              <dt>Created</dt>
              <dd>{formatDate(job.created_at)}</dd>
              <dt>Started</dt>
              <dd>{formatDate(job.started_at)}</dd>
              <dt>Completed</dt>
              <dd>{formatDate(job.completed_at)}</dd>
              {job.error_message ? (
                <>
                  <dt>Error</dt>
                  <dd className={styles.error}>{job.error_message}</dd>
                </>
              ) : null}
            </dl>
          </>
        ) : null}

        <p>
          <Link className="text-link" to="/history">
            Return to processing history
          </Link>
        </p>
      </div>
    </section>
  )
}
