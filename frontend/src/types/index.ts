export type ComparisonResult = Record<string, string | number | null>

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'parsing' | 'comparing' | 'completed' | 'failed'
  progress: number
  message: string
}

export interface TaskResult {
  data: ComparisonResult[]
  filename: string
  total_count: number
  download_token?: string
}
