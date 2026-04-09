import { useNavigate } from 'react-router-dom'
import { FileSpreadsheet, Sparkles } from 'lucide-react'
import ModuleCard from '../components/ModuleCard'

export default function Dashboard() {
  const navigate = useNavigate()

  const modules = [
    {
      title: '工厂订单数据核对',
      description: 'Excel / AI / 核对',
      icon: <FileSpreadsheet size={28} strokeWidth={1.8} />,
      eyebrow: '已上线',
      meta: '01',
      path: '/order-comparison',
    },
  ]

  return (
    <div className="relative min-h-screen overflow-hidden px-4 py-6 md:px-8 md:py-10">
      <div className="absolute left-0 top-0 h-72 w-72 rounded-full bg-[#f6b96f]/20 blur-3xl" />
      <div className="absolute right-0 top-24 h-80 w-80 rounded-full bg-[#52a7a8]/16 blur-3xl" />

      <div className="relative mx-auto max-w-7xl space-y-8">
        <section className="overflow-hidden rounded-[36px] border border-white/70 bg-[linear-gradient(135deg,rgba(255,250,244,0.92),rgba(246,255,255,0.88))] px-6 py-7 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.4)] backdrop-blur md:px-10 md:py-10">
          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
            <div className="space-y-5">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#0f8b8d]/15 bg-white/70 px-4 py-2 text-xs font-semibold tracking-[0.24em] text-[#0f6f72]">
                <Sparkles size={14} />
                智能工作台
              </div>
              <div>
                <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-slate-950 md:text-5xl">
                  智能核对
                </h1>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-500 md:text-base">
                  以 AI 辅助业务流程处理与优化，聚焦识别、核对与结果输出。
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-3">
              <div className="rounded-[24px] border border-white/80 bg-white/70 p-5 shadow-sm backdrop-blur">
                <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">模块</p>
                <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">01</p>
              </div>
              <div className="rounded-[24px] border border-white/80 bg-white/70 p-5 shadow-sm backdrop-blur">
                <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">状态</p>
                <p className="mt-3 text-lg font-semibold tracking-tight text-slate-950">可用</p>
              </div>
              <div className="rounded-[24px] border border-white/80 bg-white/70 p-5 shadow-sm backdrop-blur">
                <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">方式</p>
                <p className="mt-3 text-lg font-semibold tracking-tight text-slate-950">AI</p>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div>
            <p className="text-xs font-semibold tracking-[0.24em] text-slate-400">功能模块</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">当前功能</h2>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {modules.map((module) => (
              <ModuleCard
                key={module.path}
                title={module.title}
                description={module.description}
                icon={module.icon}
                eyebrow={module.eyebrow}
                meta={module.meta}
                onClick={() => navigate(module.path)}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
