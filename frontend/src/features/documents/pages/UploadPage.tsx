import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError, uploadDocument } from '../../../lib/api'

import styles from './UploadPage.module.css'

function formatFileSize(sizeInBytes: number) {
  if (sizeInBytes < 1024) {
    return `${sizeInBytes} bytes`
  }

  const sizeInKilobytes = sizeInBytes / 1024

  if (sizeInKilobytes < 1024) {
    return `${sizeInKilobytes.toFixed(1)} KB`
  }

  return `${(sizeInKilobytes / 1024).toFixed(1)} MB`
}

export function UploadPage() {
  const navigate = useNavigate()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      const result = await uploadDocument(selectedFile)
      navigate(`/jobs/${result.job.id}`)
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : 'Could not reach the backend API. Confirm that it is running.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section aria-labelledby="upload-heading">
      <header className="page-header">
        <h1 id="upload-heading">Upload a document</h1>
        <p className="page-description">
          Select a PDF or CSV file to prepare it for asynchronous analysis.
        </p>
      </header>

      <div className="panel">
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="document">
              Document
            </label>
            <input
              accept=".csv,.pdf,application/pdf,text/csv"
              aria-describedby="document-help"
              className={styles.fileInput}
              disabled={isSubmitting}
              id="document"
              name="document"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null)
                setErrorMessage(null)
              }}
              type="file"
            />
            <p className={styles.helpText} id="document-help">
              Accepted formats: PDF and CSV. Upload limits will be enforced by
              the backend.
            </p>
          </div>

          {selectedFile ? (
            <div aria-live="polite" className={styles.selection}>
              <strong>{selectedFile.name}</strong>
              <span>{formatFileSize(selectedFile.size)}</span>
            </div>
          ) : null}

          {errorMessage ? (
            <p className={styles.error} role="alert">
              {errorMessage}
            </p>
          ) : null}

          <div className={styles.actions}>
            <button
              className="button"
              disabled={!selectedFile || isSubmitting}
              type="submit"
            >
              {isSubmitting ? 'Queueing…' : 'Queue analysis'}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}
