export interface ComparisonResult {
  日期: string
  单号: string
  工厂: string | null
  型号: string
  公司: string
  客户出库数: number | null
  久鼎出库数: number | null
  待处理数量: number | null
}

export interface TaskStatus {
  task_id: string
  status: 'pending' | 'parsing' | 'comparing' | 'completed' | 'failed'
  progress: number
  message: string
}

export interface TaskResult {
  data: ComparisonResult[]
  file_path: string
  filename: string
  total_count: number
}
