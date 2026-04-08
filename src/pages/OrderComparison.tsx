import { useState } from 'react'
import FileUpload from '../components/FileUpload'
import ProgressBar from '../components/ProgressBar'
import ResultsTable from '../components/ResultsTable'
import { ComparisonResult } from '../types'
import {
  createComparison,
  getTaskStatus,
  getTaskResult,
  getDownloadUrl
} from '../services/api'

export default function OrderComparison() {
  const [factoryType, setFactoryType] = useState<'hengyi' | 'xinfengming'>('hengyi')
  const [factoryFile, setFactoryFile] = useState<File | null>(null)
  const [jiudingFile, setJiudingFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [results, setResults] = useState<ComparisonResult[]>([])
  const [showProgress, setShowProgress] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)

  const handleCompare = async () => {
    if (!factoryFile || !jiudingFile) {
      alert('请上传两个文件')
      return
    }

    setShowProgress(true)
    setProgress(0)
    setProgressMessage('正在上传文件...')
    setResults([])
    setTaskId(null)

    try {
      const { task_id } = await createComparison(factoryFile, jiudingFile, factoryType)
      setTaskId(task_id)

      // 轮询任务状态
      const pollStatus = async () => {
        try {
          const status = await getTaskStatus(task_id)
          setProgress(status.progress)
          setProgressMessage(status.message)

          if (status.status === 'completed') {
            const result = await getTaskResult(task_id)
            setResults(result.data)
            setShowProgress(false)
          } else if (status.status === 'failed') {
            setProgressMessage('处理失败')
            setShowProgress(false)
          } else {
            setTimeout(pollStatus, 1000)
          }
        } catch (error) {
          console.error('状态查询失败:', error)
          setProgressMessage('状态查询失败')
          setShowProgress(false)
        }
      }

      pollStatus()
    } catch (error) {
      console.error('对比失败:', error)
      setProgressMessage('处理失败')
      setShowProgress(false)
    }
  }

  // 下载功能
  const handleDownload = () => {
    if (!taskId) return
    window.open(getDownloadUrl(taskId), '_blank')
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* 标题和集团切换 */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 md:mb-8 gap-4">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-800">工厂订单数据核对</h1>

          <div className="flex gap-2 w-full md:w-auto">
            <button
              onClick={() => setFactoryType('hengyi')}
              className={`flex-1 md:flex-none px-4 md:px-6 py-2 md:py-2 rounded-lg font-medium transition-colors text-sm md:text-base ${
                factoryType === 'hengyi'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              恒逸
            </button>
            <button
              onClick={() => setFactoryType('xinfengming')}
              className={`flex-1 md:flex-none px-4 md:px-6 py-2 md:py-2 rounded-lg font-medium transition-colors text-sm md:text-base ${
                factoryType === 'xinfengming'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              新凤鸣
            </button>
          </div>
        </div>

        {/* 文件上传区域 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mb-4 md:mb-6">
          <FileUpload
            label={`上传${factoryType === 'hengyi' ? '恒逸' : '新凤鸣'}数据`}
            onFileSelect={setFactoryFile}
            selectedFile={factoryFile}
          />
          <FileUpload
            label="上传久鼎数据"
            onFileSelect={setJiudingFile}
            selectedFile={jiudingFile}
          />
        </div>

        {/* 开始核对按钮 */}
        <div className="mb-4 md:mb-6">
          <button
            onClick={handleCompare}
            disabled={!factoryFile || !jiudingFile}
            className="w-full bg-blue-600 text-white py-3 md:py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm md:text-base"
          >
            开始核对
          </button>
        </div>

        {/* 进度条 */}
        {showProgress && (
          <div className="mb-4 md:mb-6 bg-white p-4 md:p-6 rounded-lg shadow">
            <ProgressBar progress={progress} message={progressMessage} />
          </div>
        )}

        {/* 结果表格 */}
        {results.length > 0 && (
          <div className="bg-white p-4 md:p-6 rounded-lg shadow">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-2">
              <h2 className="text-lg md:text-xl font-semibold text-gray-800">对比结果</h2>
              <button
                onClick={handleDownload}
                className="w-full sm:w-auto bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm md:text-base"
              >
                下载Excel
              </button>
            </div>
            <ResultsTable data={results} />
          </div>
        )}
      </div>
    </div>
  )
}
