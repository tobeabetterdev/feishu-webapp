interface ProgressStep {
  key: string
  label: string
  hint: string
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
  const activeStep = steps.find((step) => step.active) ?? steps[0]

  return (
    <div className="w-full space-y-6">
      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <div className="rounded-[28px] border border-[#dcefed] bg-[linear-gradient(135deg,rgba(246,251,250,0.96),rgba(236,248,247,0.92))] p-5 shadow-[0_20px_50px_-35px_rgba(15,23,42,0.35)] md:p-6">
          <div className="flex items-start gap-4">
            <div className="relative mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#0f8b8d]/10">
              <div
                className={`h-3.5 w-3.5 rounded-full ${
                  isBusy ? 'animate-pulse bg-[#0f8b8d]' : 'bg-emerald-500'
                }`}
              />
              <div className="absolute inset-0 rounded-2xl border border-[#0f8b8d]/15" />
            </div>

            <div className="min-w-0">
              <p className="text-[11px] font-semibold tracking-[0.24em] text-slate-400">当前阶段</p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <h3 className="text-2xl font-semibold tracking-tight text-slate-950">{activeStep.label}</h3>
                <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-slate-500 shadow-sm">
                  {progress}%
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-500 md:text-[15px]">{activeStep.hint}</p>
              <p className="mt-4 text-base font-medium text-slate-900 md:text-lg">{message}</p>
            </div>
          </div>
        </div>

        <div className="rounded-[28px] border border-white/80 bg-white/88 p-5 shadow-[0_20px_50px_-35px_rgba(15,23,42,0.28)] md:p-6">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold tracking-[0.24em] text-slate-400">进度</p>
            <p className="text-3xl font-semibold tracking-tight text-slate-950">{progress}%</p>
          </div>

          <div className="mt-5 overflow-hidden rounded-full bg-slate-200/80">
            <div
              className="relative h-3 rounded-full bg-gradient-to-r from-[#f3a74f] via-[#0f8b8d] to-[#1dbb83] transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            >
              <div className="absolute inset-y-0 right-0 w-16 animate-pulse bg-white/25 blur-sm" />
            </div>
          </div>

          <p className="mt-4 text-sm text-slate-500">
            {isBusy ? '系统会按实际处理环节逐步推进。' : '结果已就绪，可以继续查看或下载。'}
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-5">
        {steps.map((step, index) => (
          <div
            key={step.key}
            className={`relative overflow-hidden rounded-[24px] border px-4 py-4 transition ${
              step.done
                ? 'border-emerald-200 bg-emerald-50/90'
                : step.active
                  ? 'border-cyan-200 bg-cyan-50/90 shadow-[0_16px_30px_-24px_rgba(15,139,141,0.45)]'
                  : 'border-slate-200 bg-slate-50/90'
            }`}
          >
            <div className="flex items-start gap-3">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                  step.done
                    ? 'bg-emerald-500 text-white'
                    : step.active
                      ? 'bg-[#0f8b8d] text-white'
                      : 'bg-white text-slate-400'
                }`}
              >
                {index + 1}
              </span>

              <div className="min-w-0">
                <p
                  className={`text-sm font-semibold ${
                    step.done || step.active ? 'text-slate-900' : 'text-slate-500'
                  }`}
                >
                  {step.label}
                </p>
                <p className="mt-1 line-clamp-2 text-xs text-slate-400">{step.hint}</p>
              </div>
            </div>

            {step.active ? <div className="mt-4 h-1.5 rounded-full bg-[#0f8b8d]/15" /> : null}
          </div>
        ))}
      </div>
    </div>
  )
}
