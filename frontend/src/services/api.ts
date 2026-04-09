const API_BASE_URL = 'http://localhost:8000/api'

export interface CompareResponse {
  task_id: string
  status: string
}

export interface TaskStatus {
  task_id: string
  status: string
  progress: number
  message: string
}

export interface TaskResult {
  data: any[]
  file_path: string
  filename: string
  total_count: number
}

export async function createComparison(
  factoryFile: File,
  jiudingFile: File,
  factoryType: string,
): Promise<CompareResponse> {
  const formData = new FormData()
  formData.append('factory_file', factoryFile)
  formData.append('jiuding_file', jiudingFile)
  formData.append('factory_type', factoryType)

  const response = await fetch(`${API_BASE_URL}/compare`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`创建核对任务失败: ${errorText}`)
  }

  return response.json()
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE_URL}/compare/${taskId}/status`)
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`获取任务状态失败: ${errorText}`)
  }
  return response.json()
}

export async function getTaskResult(taskId: string): Promise<TaskResult> {
  const response = await fetch(`${API_BASE_URL}/compare/${taskId}/result`)
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`获取任务结果失败: ${errorText}`)
  }
  return response.json()
}

export function getDownloadUrl(taskId: string): string {
  return `${API_BASE_URL}/compare/${taskId}/download`
}
