export type JobStatus =
  | 'pending'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'enqueue_failed'
  | 'failed'

export interface DocumentMetadata {
  id: string
  original_filename: string
  media_type: string
  size_bytes: number
  checksum_sha256: string
  created_at: string
}

export interface ProcessingJob {
  id: string
  document_id: string
  status: JobStatus
  attempt_count: number
  error_message: string | null
  created_at: string
  updated_at: string
  started_at: string | null
  completed_at: string | null
}

export interface ProcessingJobListResponse {
  items: ProcessingJob[]
  total: number
  limit: number
  offset: number
}

export type AnalysisStatus = 'processing' | 'completed' | 'failed'

export interface AnalysisOutput {
  summary: string
  document_type: string
  key_points: string[]
}

export interface DocumentAnalysis {
  id: string
  document_id: string
  job_id: string
  status: AnalysisStatus
  provider: string
  model_name: string
  summary: string | null
  structured_output: AnalysisOutput | null
  status_metadata: Record<string, unknown>
  error_code: string | null
  created_at: string
  completed_at: string | null
}

export interface DocumentUploadResponse {
  document: DocumentMetadata
  job: ProcessingJob
}
