import { Fragment, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  ApiError,
  getDocumentAnalysis,
  listProcessingJobs,
} from '../../../lib/api'
import type {
  DocumentAnalysis,
  JobStatus,
  ProcessingJob,
} from '../../../types/api'
import styles from './HistoryPage.module.css'

interface AnalysisRequestState {
  jobId: string
  isLoading: boolean
  analysis: DocumentAnalysis | null
  errorMessage: string | null
}

function formatStatus(status: JobStatus) {
  return status.replaceAll('_', ' ')
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'Not yet'
}

function messageFromError(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

export function HistoryPage() {
  const [jobs, setJobs] = useState<ProcessingJob[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const [analysisState, setAnalysisState] =
    useState<AnalysisRequestState | null>(null)
  const analysisController = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadJobs() {
      setIsLoading(true)
      setErrorMessage(null)

      try {
        const response = await listProcessingJobs(controller.signal)
        setJobs(response.items)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }

        setErrorMessage(
          messageFromError(
            error,
            'Could not load processing history from the backend API.',
          ),
        )
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    void loadJobs()

    return () => controller.abort()
  }, [reloadToken])

  useEffect(
    () => () => {
      analysisController.current?.abort()
    },
    [],
  )

  async function toggleAnalysis(job: ProcessingJob) {
    if (analysisState?.jobId === job.id) {
      analysisController.current?.abort()
      analysisController.current = null
      setAnalysisState(null)
      return
    }

    analysisController.current?.abort()
    const controller = new AbortController()
    analysisController.current = controller
    setAnalysisState({
      jobId: job.id,
      isLoading: true,
      analysis: null,
      errorMessage: null,
    })

    try {
      const analysis = await getDocumentAnalysis(
        job.document_id,
        controller.signal,
      )
      setAnalysisState({
        jobId: job.id,
        isLoading: false,
        analysis,
        errorMessage: null,
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }

      setAnalysisState({
        jobId: job.id,
        isLoading: false,
        analysis: null,
        errorMessage: messageFromError(
          error,
          'Could not load the document analysis.',
        ),
      })
    }
  }

  return (
    <section aria-labelledby="history-heading" aria-live="polite">
      <header className="page-header">
        <h1 id="history-heading">Processing history</h1>
        <p className="page-description">
          Review queued, running, completed, and failed analysis jobs.
        </p>
      </header>

      {isLoading ? (
        <div className="panel">
          <p className={styles.stateMessage}>Loading processing history…</p>
        </div>
      ) : null}

      {!isLoading && errorMessage ? (
        <div className="panel">
          <p className={styles.error} role="alert">
            {errorMessage}
          </p>
          <button
            className="button"
            type="button"
            onClick={() => setReloadToken((value) => value + 1)}
          >
            Try again
          </button>
        </div>
      ) : null}

      {!isLoading && !errorMessage && jobs.length === 0 ? (
        <div className="panel">
          <h2>No analysis jobs yet</h2>
          <p className="page-description">
            Upload a document to create your first background analysis job.
          </p>
          <p className={styles.emptyAction}>
            <Link className="text-link" to="/upload">
              Upload a document
            </Link>
          </p>
        </div>
      ) : null}

      {!isLoading && !errorMessage && jobs.length > 0 ? (
        <div className={`panel ${styles.historyPanel}`}>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <caption className={styles.caption}>
                Document processing jobs, newest first
              </caption>
              <thead>
                <tr>
                  <th scope="col">Status</th>
                  <th scope="col">Job ID</th>
                  <th scope="col">Document ID</th>
                  <th scope="col">Created</th>
                  <th scope="col">Started</th>
                  <th scope="col">Completed</th>
                  <th scope="col">Failure details</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  const isAnalysisOpen = analysisState?.jobId === job.id

                  return (
                    <Fragment key={job.id}>
                      <tr>
                        <td>
                          <span className={styles.status} data-status={job.status}>
                            {formatStatus(job.status)}
                          </span>
                        </td>
                        <td>
                          <Link className="text-link" to={`/jobs/${job.id}`}>
                            <code>{job.id}</code>
                          </Link>
                        </td>
                        <td>
                          <code>{job.document_id}</code>
                        </td>
                        <td>{formatDate(job.created_at)}</td>
                        <td>{formatDate(job.started_at)}</td>
                        <td>{formatDate(job.completed_at)}</td>
                        <td className={job.error_message ? styles.error : undefined}>
                          {job.error_message ?? '—'}
                        </td>
                        <td>
                          {job.status === 'completed' ? (
                            <button
                              className={styles.analysisButton}
                              type="button"
                              aria-expanded={isAnalysisOpen}
                              aria-controls={`analysis-${job.id}`}
                              onClick={() => void toggleAnalysis(job)}
                            >
                              {isAnalysisOpen ? 'Close analysis' : 'View analysis'}
                            </button>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                      {isAnalysisOpen ? (
                        <tr>
                          <td colSpan={8}>
                            <AnalysisResult
                              id={`analysis-${job.id}`}
                              state={analysisState}
                            />
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  )
}

function AnalysisResult({
  id,
  state,
}: {
  id: string
  state: AnalysisRequestState
}) {
  if (state.isLoading) {
    return (
      <div id={id} className={styles.analysis}>
        Loading analysis…
      </div>
    )
  }

  if (state.errorMessage) {
    return (
      <div id={id} className={`${styles.analysis} ${styles.error}`} role="alert">
        {state.errorMessage}
      </div>
    )
  }

  if (!state.analysis) {
    return null
  }

  const { analysis } = state

  return (
    <article id={id} className={styles.analysis}>
      <div className={styles.analysisHeader}>
        <h2>Analysis result</h2>
        <span>
          {analysis.provider} · {analysis.model_name}
        </span>
      </div>
      <p>{analysis.summary ?? 'No summary was returned.'}</p>
      {analysis.structured_output ? (
        <>
          <p>
            <strong>Document type:</strong>{' '}
            {analysis.structured_output.document_type}
          </p>
          <h3>Key points</h3>
          <ul>
            {analysis.structured_output.key_points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </>
      ) : null}
    </article>
  )
}
