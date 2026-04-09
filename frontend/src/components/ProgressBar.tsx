interface ProgressStep {
  key: string
  label: string
  active: boolean
  done: boolean
}

interface ProgressBarProps {
  progress: number
  message: string
  steps: ProgressStep[]
  isBusy: boolean
}

export default function ProgressBar({ progress, message, steps, isBusy }: ProgressBarProps) {
  return (
    <div className="w-full space-y-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex items-start gap-4">
          <div
            className={`mt-1.5 h-3.5 w-3.5 shrink-0 rounded-full ${
              isBusy ? 'animate-pulse bg-[#0f8b8d]' : 'bg-emerald-500'
            }`}
          />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Processing</p>
            <p className="mt-2 text-base font-semibold text-slate-950 md:text-lg">{message}</p>
            <p className="mt-1 text-sm text-slate-500">
              {isBusy ? '系统正在持续处理，请保持页面开启。' : '任务已完成，结果列表与导出文件已准备好。'}
            </p>
          </div>
        </div>

        <div className="rounded-[24px] border border-white/80 bg-white/80 px-5 py-4 shadow-sm">
          <p className="text-right text-3xl font-semibold tracking-tight text-slate-950">{progress}%</p>
          <p className="text-right text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">进度</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-full bg-slate-200">
        <div
          className="relative h-3 rounded-full bg-gradient-to-r from-[#f3a74f] via-[#0f8b8d] to-[#22c55e] transition-all duration-700 ease-out"
          style={{ width: `${progress}%` }}
        >
          <div className="absolute inset-y-0 right-0 w-16 animate-pulse bg-white/25 blur-sm" />
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {steps.map((step) => (
          <div
            key={step.key}
            className={`rounded-[22px] border px-4 py-4 transition ${
              step.done
                ? 'border-emerald-200 bg-emerald-50/80'
                : step.active
                  ? 'border-cyan-200 bg-cyan-50/80 shadow-sm'
                  : 'border-slate-200 bg-slate-50/90'
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  step.done
                    ? 'bg-emerald-500'
                    : step.active
                      ? 'animate-pulse bg-[#0f8b8d]'
                      : 'bg-slate-300'
                }`}
              />
              <span
                className={`text-sm font-medium ${
                  step.done || step.active ? 'text-slate-900' : 'text-slate-500'
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
