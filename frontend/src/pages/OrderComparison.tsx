import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  FileDown,
  LoaderCircle,
  ScanSearch,
  Shapes,
  Sparkles,
  Warehouse,
} from 'lucide-react'
import FileUpload from '../components/FileUpload'
import ProgressBar from '../components/ProgressBar'
import ResultsTable from '../components/ResultsTable'
import { ComparisonResult } from '../types'
import {
  createComparison,
  downloadTaskResult,
  getTaskStatus,
  getTaskResult,
} from '../services/api'

type FactoryType = 'hengyi' | 'xinfengming'
type StageKey = 'upload' | 'identify' | 'normalize' | 'compare' | 'export' | 'done'

const STAGE_META: Record<StageKey, { label: string; min: number; max: number }> = {
  upload: { label: '上传', min: 0, max: 12 },
  identify: { label: '识别', min: 12, max: 40 },
  normalize: { label: '整理', min: 40, max: 68 },
  compare: { label: '核对', min: 68, max: 88 },
  export: { label: '输出', min: 88, max: 98 },
  done: { label: '完成', min: 100, max: 100 },
}

const ROLE_META: Record<
  FactoryType,
  {
    label: string
    icon: typeof Shapes
    tone: string
    glow: string
  }
> = {
  hengyi: {
    label: '恒逸',
    icon: Shapes,
    tone: 'from-[#f6c27a] via-[#f3a74f] to-[#ef8b33]',
    glow: 'shadow-[0_18px_40px_-24px_rgba(243,167,79,0.72)]',
  },
  xinfengming: {
    label: '新凤鸣',
    icon: Warehouse,
    tone: 'from-[#61c7c8] via-[#1fa7a8] to-[#0f7f82]',
    glow: 'shadow-[0_18px_40px_-24px_rgba(15,139,141,0.72)]',
  },
}

function resolveStage(status: string, message: string): StageKey {
  if (status === 'completed') return 'done'
  if (message.includes('生成结果') || message.includes('结果文件')) return 'export'
  if (message.includes('汇总') || message.includes('核对') || status === 'comparing') return 'compare'
  if (message.includes('标准化')) return 'normalize'
  if (message.includes('识别字段') || message.includes('AI')) return 'identify'
  return 'upload'
}

export default function OrderComparison() {
  const navigate = useNavigate()
  const [factoryType, setFactoryType] = useState<FactoryType>('hengyi')
  const [factoryFiles, setFactoryFiles] = useState<File[]>([])
  const [jiudingFiles, setJiudingFiles] = useState<File[]>([])
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState('')
  const [results, setResults] = useState<ComparisonResult[]>([])
  const [showProgress, setShowProgress] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeStage, setActiveStage] = useState<StageKey>('upload')
  const progressTimerRef = useRef<number | null>(null)

  const clearProgressTimer = () => {
    if (progressTimerRef.current !== null) {
      window.clearInterval(progressTimerRef.current)
      progressTimerRef.current = null
    }
  }

  useEffect(() => {
    return () => clearProgressTimer()
  }, [])

  const beginSmoothProgress = (stage: StageKey) => {
    clearProgressTimer()
    const target = STAGE_META[stage].max
    progressTimerRef.current = window.setInterval(() => {
      setProgress((current) => {
        if (current >= target) return current
        const step = stage === 'upload' ? 2 : 1
        return Math.min(current + step, target)
      })
    }, 500)
  }

  const updateStage = (status: string, message: string, exactProgress?: number) => {
    const nextStage = resolveStage(status, message)
    setActiveStage(nextStage)
    setProgressMessage(message)
    beginSmoothProgress(nextStage)

    if (typeof exactProgress === 'number') {
      setProgress((current) => Math.max(current, Math.min(exactProgress, STAGE_META[nextStage].max)))
    } else {
      setProgress((current) => Math.max(current, STAGE_META[nextStage].min))
    }
  }

  const resetPageState = (nextFactoryType: FactoryType) => {
    setFactoryType(nextFactoryType)
    setFactoryFiles([])
    setJiudingFiles([])
    setResults([])
    setShowProgress(false)
    setTaskId(null)
    setProgress(0)
    setProgressMessage('')
    setActiveStage('upload')
  }

  const handleFactoryTypeChange = (type: FactoryType) => {
    if (isSubmitting || factoryType === type) return
    resetPageState(type)
  }

  const appendFiles = (current: File[], incoming: File[]) => {
    const keySet = new Set(current.map((file) => `${file.name}-${file.size}-${file.lastModified}`))
    const merged = [...current]
    incoming.forEach((file) => {
      const key = `${file.name}-${file.size}-${file.lastModified}`
      if (!keySet.has(key)) {
        merged.push(file)
        keySet.add(key)
      }
    })
    return merged
  }

  const handleCompare = async () => {
    if (factoryFiles.length === 0 || jiudingFiles.length === 0 || isSubmitting) return

    setIsSubmitting(true)
    setShowProgress(true)
    setProgress(4)
    setProgressMessage('正在上传文件...')
    setActiveStage('upload')
    beginSmoothProgress('upload')
    setResults([])
    setTaskId(null)

    try {
      const { task_id } = await createComparison(factoryFiles, jiudingFiles, factoryType)
      setTaskId(task_id)
      updateStage('pending', '任务已创建，等待系统处理...', 5)

      const pollStatus = async () => {
        try {
          const status = await getTaskStatus(task_id)
          updateStage(status.status, status.message, status.progress)

          if (status.status === 'completed') {
            clearProgressTimer()
            setProgressMessage('核对完成，正在加载结果...')
            setProgress((current) => Math.max(current, 99))

            try {
              const result = await getTaskResult(task_id)
              setResults(result.data)
              setProgress(100)
              setActiveStage('done')
              window.setTimeout(() => {
                setShowProgress(false)
                setIsSubmitting(false)
              }, 900)
            } catch (error) {
              setIsSubmitting(false)
              const errorMessage = error instanceof Error ? error.message : '结果加载失败'
              setProgressMessage(errorMessage)
              alert(`结果加载失败: ${errorMessage}`)
            }
          } else if (status.status === 'failed') {
            clearProgressTimer()
            setIsSubmitting(false)
            setProgressMessage(status.message)
            alert(`核对失败: ${status.message}`)
          } else {
            window.setTimeout(pollStatus, 700)
          }
        } catch (error) {
          clearProgressTimer()
          setIsSubmitting(false)
          const errorMessage = error instanceof Error ? error.message : '任务状态查询失败'
          setProgressMessage(errorMessage)
          alert(`状态查询失败: ${errorMessage}`)
        }
      }

      window.setTimeout(pollStatus, 250)
    } catch (error) {
      clearProgressTimer()
      setIsSubmitting(false)
      const errorMessage = error instanceof Error ? error.message : '处理失败'
      setProgressMessage(errorMessage)
      alert(`核对失败: ${errorMessage}`)
    }
  }

  const handleDownload = async () => {
    if (!taskId) return

    try {
      await downloadTaskResult(taskId)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '下载结果失败'
      alert(`下载结果失败: ${errorMessage}`)
    }
  }

  const steps = (Object.keys(STAGE_META) as StageKey[]).map((key) => ({
    key,
    label: STAGE_META[key].label,
    active: activeStage === key,
    done: STAGE_META[key].max < STAGE_META[activeStage].max || activeStage === 'done',
  }))

  const currentRole = ROLE_META[factoryType]

  return (
    <div className="relative min-h-screen overflow-hidden px-4 py-6 md:px-8 md:py-10">
      <div className="absolute left-0 top-0 h-72 w-72 rounded-full bg-[#f6b96f]/20 blur-3xl" />
      <div className="absolute right-0 top-20 h-80 w-80 rounded-full bg-[#52a7a8]/16 blur-3xl" />

      <div className="relative mx-auto max-w-7xl space-y-6">
        <section className="overflow-hidden rounded-[36px] border border-white/70 bg-[linear-gradient(140deg,rgba(255,249,241,0.95),rgba(240,252,252,0.88))] p-6 shadow-[0_30px_80px_-42px_rgba(15,23,42,0.42)] backdrop-blur md:p-8">
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-5">
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="inline-flex items-center gap-2 rounded-full border border-white/80 bg-white/80 px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:border-[#0f8b8d]/20 hover:text-[#0f6f72]"
                >
                  <ArrowLeft size={16} />
                  返回
                </button>

                <div className="space-y-4">
                  <div className="inline-flex items-center gap-2 rounded-full border border-[#0f8b8d]/15 bg-white/70 px-4 py-2 text-xs font-semibold tracking-[0.24em] text-[#0f6f72]">
                    <Sparkles size={14} />
                    智能核对
                  </div>
                  <div>
                    <h1 className="text-3xl font-semibold tracking-tight text-slate-950 md:text-4xl">
                      订单核对
                    </h1>
                    <p className="mt-3 text-sm text-slate-500 md:text-base">多文件识别，合并核对，输出结果。</p>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-[24px] border border-white/75 bg-white/68 p-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#fff2de] text-[#d98620]">
                      <ScanSearch size={20} />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-900">识别</p>
                  </div>
                  <div className="rounded-[24px] border border-white/75 bg-white/68 p-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#def6f4] text-[#0f8b8d]">
                      <Shapes size={20} />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-900">汇总</p>
                  </div>
                  <div className="rounded-[24px] border border-white/75 bg-white/68 p-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#e8f8ef] text-emerald-600">
                      <FileDown size={20} />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-900">输出</p>
                  </div>
                </div>
              </div>

              <div className="w-full xl:max-w-[360px]">
                <div className="rounded-[30px] border border-white/80 bg-white/82 p-4 shadow-[0_18px_50px_-32px_rgba(15,23,42,0.28)] md:p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">工厂角色</p>
                    <div
                      className={`inline-flex items-center rounded-full bg-gradient-to-r px-3 py-1 text-xs font-semibold text-white ${currentRole.tone} ${currentRole.glow}`}
                    >
                      {currentRole.label}
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 rounded-[26px] bg-slate-100/90 p-1.5">
                    {(Object.entries(ROLE_META) as [FactoryType, (typeof ROLE_META)[FactoryType]][]).map(
                      ([value, option]) => {
                        const active = factoryType === value
                        const Icon = option.icon

                        return (
                          <button
                            key={value}
                            type="button"
                            onClick={() => handleFactoryTypeChange(value)}
                            disabled={isSubmitting}
                            className={`relative overflow-hidden rounded-[22px] px-4 py-4 text-left transition ${
                              active
                                ? `bg-gradient-to-br text-white ${option.tone} ${option.glow}`
                                : 'bg-transparent text-slate-500 hover:bg-white/80 hover:text-slate-900'
                            } ${isSubmitting ? 'cursor-not-allowed opacity-60' : ''}`}
                          >
                            <div className="flex items-center justify-between">
                              <span
                                className={`inline-flex h-10 w-10 items-center justify-center rounded-2xl ${
                                  active ? 'bg-white/18 text-white' : 'bg-white text-slate-500'
                                }`}
                              >
                                <Icon size={18} />
                              </span>
                            </div>
                            <p className="mt-5 text-lg font-semibold tracking-[0.02em]">{option.label}</p>
                          </button>
                        )
                      },
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-2 xl:gap-6">
          <FileUpload
            label="工厂数据"
            description={currentRole.label}
            onFilesSelect={(files) => setFactoryFiles((current) => appendFiles(current, files))}
            onFileRemove={(index) => setFactoryFiles((current) => current.filter((_, currentIndex) => currentIndex !== index))}
            selectedFiles={factoryFiles}
          />
          <FileUpload
            label="久鼎数据"
            description="久鼎"
            onFilesSelect={(files) => setJiudingFiles((current) => appendFiles(current, files))}
            onFileRemove={(index) => setJiudingFiles((current) => current.filter((_, currentIndex) => currentIndex !== index))}
            selectedFiles={jiudingFiles}
          />
        </section>

        <section className="rounded-[32px] border border-white/70 bg-white/82 p-5 shadow-[0_24px_60px_-38px_rgba(15,23,42,0.42)] backdrop-blur md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">AI 任务</p>
              <h2 className="text-2xl font-semibold tracking-tight text-slate-950">开始核对</h2>
              <p className="text-sm text-slate-500">两侧文件就绪后即可执行。</p>
            </div>

            <button
              type="button"
              onClick={handleCompare}
              disabled={factoryFiles.length === 0 || jiudingFiles.length === 0 || isSubmitting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-[linear-gradient(135deg,#f3a74f,#0f8b8d)] px-6 py-4 text-base font-semibold text-white shadow-[0_18px_40px_-20px_rgba(15,139,141,0.6)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-white/80 disabled:shadow-none md:w-auto md:min-w-[220px]"
            >
              {isSubmitting ? <LoaderCircle className="h-5 w-5 animate-spin" /> : null}
              <span>{isSubmitting ? '处理中' : '开始核对'}</span>
            </button>
          </div>
        </section>

        {showProgress && (
          <section className="rounded-[32px] border border-white/70 bg-white/82 p-5 shadow-[0_24px_60px_-38px_rgba(15,23,42,0.42)] backdrop-blur md:p-6">
            <ProgressBar
              progress={progress}
              message={progressMessage}
              steps={steps}
              isBusy={isSubmitting}
            />
          </section>
        )}

        {results.length > 0 && (
          <section className="rounded-[32px] border border-white/70 bg-white/86 p-5 shadow-[0_24px_60px_-38px_rgba(15,23,42,0.42)] backdrop-blur md:p-6">
            <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="space-y-2">
                <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">核对结果</p>
                <h2 className="text-2xl font-semibold tracking-tight text-slate-950">异常结果</h2>
                <p className="text-sm text-slate-500">{results.length} 条</p>
              </div>

              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-5 py-3 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 md:w-auto"
              >
                <FileDown size={18} />
                下载结果
              </button>
            </div>

            <ResultsTable data={results} />
          </section>
        )}
      </div>
    </div>
  )
}
