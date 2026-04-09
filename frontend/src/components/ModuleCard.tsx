import { ReactNode } from 'react'
import { ArrowUpRight } from 'lucide-react'

interface ModuleCardProps {
  title: string
  description: string
  icon: ReactNode
  eyebrow?: string
  meta?: string
  onClick: () => void
}

export default function ModuleCard({
  title,
  description,
  icon,
  eyebrow,
  meta,
  onClick,
}: ModuleCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group relative overflow-hidden rounded-[30px] border border-white/70 bg-white/86 p-6 text-left shadow-[0_24px_60px_-30px_rgba(15,23,42,0.32)] backdrop-blur transition duration-300 hover:-translate-y-1.5 hover:shadow-[0_30px_70px_-28px_rgba(15,23,42,0.38)] focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
    >
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-[#ffb85c] via-[#f08a5d] to-[#0f8b8d]" />
      <div className="absolute right-0 top-0 h-36 w-36 translate-x-8 -translate-y-8 rounded-full bg-gradient-to-br from-[#0f8b8d]/12 to-transparent blur-2xl" />

      <div className="relative flex h-full flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-3">
            {eyebrow ? (
              <span className="inline-flex rounded-full border border-[#0f8b8d]/15 bg-[#0f8b8d]/8 px-3 py-1 text-xs font-semibold tracking-[0.24em] text-[#0f6f72]">
                {eyebrow}
              </span>
            ) : null}
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[linear-gradient(145deg,#fff4dd,#e3fbfb)] text-[#0f6f72] shadow-inner shadow-white/80">
              {icon}
            </div>
          </div>

          <div className="flex flex-col items-end gap-3">
            {meta ? <span className="text-xs font-semibold tracking-[0.24em] text-slate-400">{meta}</span> : null}
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition group-hover:border-[#0f8b8d]/30 group-hover:text-[#0f6f72]">
              <ArrowUpRight size={18} />
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>
    </button>
  )
}
