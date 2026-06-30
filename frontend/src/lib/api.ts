import type {
  DocumentAnalysis,
  DocumentUploadResponse,
  ProcessingJob,
  ProcessingJobListResponse,
} from '../types/api'

const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function errorMessage(payload: unknown) {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) {
    return 'The request could not be completed.'
  }

  const { detail } = payload
  if (typeof detail === 'string') {
    return detail
  }
  if (
    detail &&
    typeof detail === 'object' &&
    'message' in detail &&
    typeof detail.message === 'string'
  ) {
    return detail.message
  }

  return 'The request could not be completed.'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, init)
  const payload: unknown = await response.json()

  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(payload))
  }

  return payload as T
}

export function uploadDocument(file: File) {
  const body = new FormData()
  body.append('file', file)

  return request<DocumentUploadResponse>('/documents', {
    method: 'POST',
    body,
  })
}

export function getProcessingJob(jobId: string, signal?: AbortSignal) {
  return request<ProcessingJob>(`/jobs/${encodeURIComponent(jobId)}`, {
    signal,
  })
}

export function listProcessingJobs(signal?: AbortSignal) {
  return request<ProcessingJobListResponse>('/jobs', { signal })
}

export function getDocumentAnalysis(
  documentId: string,
  signal?: AbortSignal,
) {
  return request<DocumentAnalysis>(
    `/documents/${encodeURIComponent(documentId)}/analysis`,
    { signal },
  )
}
