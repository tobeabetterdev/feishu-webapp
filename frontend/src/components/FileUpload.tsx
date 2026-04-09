import { ChangeEvent, DragEvent, useCallback, useId, useState } from 'react'
import { CheckCircle2, FileSpreadsheet, Upload, X } from 'lucide-react'

interface FileUploadProps {
  label: string
  description: string
  onFileSelect: (file: File) => void
  onFileRemove: () => void
  selectedFile: File | null
}

export default function FileUpload({
  label,
  description,
  onFileSelect,
  onFileRemove,
  selectedFile,
}: FileUploadProps) {
  const inputId = useId()
  const [isDragging, setIsDragging] = useState(false)

  const validateAndSelect = (file?: File) => {
    if (!file) return

    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      alert('请上传 Excel 文件（.xlsx 或 .xls）')
      return
    }

    onFileSelect(file)
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    validateAndSelect(event.target.files?.[0])
  }

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
    validateAndSelect(event.dataTransfer.files?.[0])
  }, [])

  const handleDragState = useCallback((event: DragEvent<HTMLDivElement>, dragging: boolean) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(dragging)
  }, [])

  const containerClassName = selectedFile
    ? 'border-emerald-200 bg-[linear-gradient(180deg,rgba(240,253,244,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_-30px_rgba(16,185,129,0.45)]'
    : isDragging
      ? 'border-cyan-400 bg-[linear-gradient(180deg,rgba(236,254,255,0.98),rgba(255,255,255,0.98))] shadow-[0_18px_45px_-30px_rgba(8,145,178,0.38)]'
      : 'border-slate-200 bg-white/88 hover:border-[#0f8b8d]/35 hover:bg-white'

  return (
    <div
      className={`rounded-[30px] border p-5 transition duration-300 md:p-6 ${containerClassName}`}
      onDrop={handleDrop}
      onDragOver={(event) => handleDragState(event, true)}
      onDragEnter={(event) => handleDragState(event, true)}
      onDragLeave={(event) => handleDragState(event, false)}
    >
      <input
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileChange}
        className="hidden"
        id={inputId}
      />

      <div className="flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">文件上传</p>
            <div className="mt-3 flex items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                <FileSpreadsheet size={20} strokeWidth={1.8} />
              </div>
              <div className="min-w-0">
                <h3 className="text-lg font-semibold tracking-tight text-slate-950">{label}</h3>
                <p className="mt-1 text-sm text-slate-500">{description}</p>
              </div>
            </div>
          </div>

          <span
            className={`inline-flex shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
              selectedFile
                ? 'bg-emerald-100 text-emerald-700'
                : isDragging
                  ? 'bg-cyan-100 text-cyan-700'
                  : 'bg-slate-100 text-slate-500'
            }`}
          >
            {selectedFile ? '已就绪' : isDragging ? '释放上传' : '等待文件'}
          </span>
        </div>

        {selectedFile ? (
          <div className="rounded-[24px] border border-emerald-200/80 bg-white/82 p-4 md:p-5">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <CheckCircle2 size={24} strokeWidth={1.8} />
              </div>

              <div className="min-w-0 flex-1">
                <p className="break-all text-sm font-semibold leading-6 text-slate-900">{selectedFile.name}</p>
                <p className="mt-2 text-xs text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
              </div>

              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault()
                  onFileRemove()
                }}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-transparent text-slate-400 transition hover:border-rose-100 hover:bg-rose-50 hover:text-rose-600"
              >
                <X size={18} />
              </button>
            </div>
          </div>
        ) : (
          <label
            htmlFor={inputId}
            className="flex min-h-[240px] w-full cursor-pointer flex-col items-center justify-center rounded-[26px] border border-dashed border-slate-200 bg-[linear-gradient(180deg,rgba(248,250,252,0.9),rgba(255,255,255,0.94))] px-6 py-8 text-center transition hover:border-[#0f8b8d]/35 hover:bg-white md:px-8 md:py-10"
          >
            <div className="flex h-16 w-16 items-center justify-center rounded-[20px] bg-slate-100 text-slate-500">
              {isDragging ? (
                <Upload size={26} className="text-cyan-600" />
              ) : (
                <FileSpreadsheet size={26} strokeWidth={1.8} />
              )}
            </div>
            <p className="mt-5 text-sm font-semibold text-slate-800">
              {isDragging ? '释放文件' : '点击或拖入表格'}
            </p>
            <p className="mt-2 text-xs text-slate-500">支持 Excel 文件</p>
          </label>
        )}

        <div className="flex items-center justify-between gap-3 border-t border-slate-200/80 pt-4 text-xs text-slate-500">
          <span>Excel 文件</span>
          <span className="font-medium text-slate-400">拖入或选择</span>
        </div>
      </div>
    </div>
  )
}
