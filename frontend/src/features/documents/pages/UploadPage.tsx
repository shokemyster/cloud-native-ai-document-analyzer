import { useState } from 'react'

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
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  return (
    <section aria-labelledby="upload-heading">
      <header className="page-header">
        <h1 id="upload-heading">Upload a document</h1>
        <p className="page-description">
          Select a PDF or CSV file to prepare it for asynchronous analysis.
        </p>
      </header>

      <div className="panel">
        <form className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="document">
              Document
            </label>
            <input
              accept=".csv,.pdf,application/pdf,text/csv"
              aria-describedby="document-help"
              className={styles.fileInput}
              id="document"
              name="document"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null)
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

          <div className={styles.actions}>
            <button className="button" disabled type="button">
              Queue analysis
            </button>
          </div>

          <p className={styles.helpText}>
            Analysis submission will be enabled when the backend API is
            connected.
          </p>
        </form>
      </div>
    </section>
  )
}
