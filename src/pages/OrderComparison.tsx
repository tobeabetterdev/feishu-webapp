import { useState } from 'react'
import FileUpload from '../components/FileUpload'
import ProgressBar from '../components/ProgressBar'
import ResultsTable from '../components/ResultsTable'
import { ComparisonResult } from '../types'

export default function OrderComparison() {
  const [factoryType, setFactoryType] = useState<'hengyi' | 'xinfengming'>('hengyi')
  const [factoryFile, setFactoryFile] = useState<File | null>(null)
  const [jiudingFile, setJiudingFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [results, setResults] = useState<ComparisonResult[]>([])
  const [showProgress, setShowProgress] = useState(false)

  const handleCompare = () => {
    if (!factoryFile || !jiudingFile) {
      alert('请上传两个文件')
      return
    }

    // 临时模拟进度
    setShowProgress(true)
    setProgress(0)
    setProgressMessage('准备中...')
    setResults([])

    // 这里将在Task 8中集成真实API
    console.log('开始对比', { factoryType, factoryFile, jiudingFile })
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* 标题和集团切换 */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">工厂订单数据核对</h1>

          <div className="flex gap-2">
            <button
              onClick={() => setFactoryType('hengyi')}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                factoryType === 'hengyi'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              恒逸
            </button>
            <button
              onClick={() => setFactoryType('xinfengming')}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
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
        <div className="mb-6">
          <button
            onClick={handleCompare}
            disabled={!factoryFile || !jiudingFile}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            开始核对
          </button>
        </div>

        {/* 进度条 */}
        {showProgress && (
          <div className="mb-6 bg-white p-6 rounded-lg shadow">
            <ProgressBar progress={progress} message={progressMessage} />
          </div>
        )}

        {/* 结果表格 */}
        {results.length > 0 && (
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-800">对比结果</h2>
              <button className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
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
