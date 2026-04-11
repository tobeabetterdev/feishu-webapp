const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

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
  filename: string
  total_count: number
  download_token?: string
}

export async function createComparison(
  factoryFiles: File[],
  jiudingFiles: File[],
  factoryType: string,
): Promise<CompareResponse> {
  const formData = new FormData()
  factoryFiles.forEach((file) => formData.append('factory_files', file))
  jiudingFiles.forEach((file) => formData.append('jiuding_files', file))
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

function resolveDownloadFilename(contentDisposition: string | null, fallbackFilename: string): string {
  if (!contentDisposition) {
    return fallbackFilename
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1])
  }

  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  if (filenameMatch?.[1]) {
    return filenameMatch[1]
  }

  return fallbackFilename
}

export async function downloadTaskResult(taskId: string, fallbackFilename = '订单核对结果.xlsx'): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/compare/${taskId}/download`)
  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`下载结果失败: ${errorText}`)
  }

  const blob = await response.blob()
  const downloadUrl = URL.createObjectURL(blob)
  const filename = resolveDownloadFilename(response.headers.get('content-disposition'), fallbackFilename)
  const anchor = document.createElement('a')

  anchor.href = downloadUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(downloadUrl)
}
