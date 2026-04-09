import { AlertTriangle, Factory, Hash, Layers3 } from 'lucide-react'
import { ComparisonResult } from '../types'

interface ResultsTableProps {
  data: ComparisonResult[]
}

type RawRow = ComparisonResult & Record<string, unknown>

interface DisplayRow {
  date: string
  orderNo: string
  factory: string
  model: string
  company: string
  customerQty: string
  jiudingQty: string
  pendingQty: number | null
}

const FIELD_ALIASES = {
  date: ['日期', 'date'],
  orderNo: ['订单号', 'order_no', 'orderNo'],
  factory: ['工厂', 'factory'],
  model: ['型号', 'model'],
  company: ['公司', 'company'],
  customerQty: ['工厂出库数量', 'customer_qty', 'customerQty'],
  jiudingQty: ['久鼎出库数量', 'jiuding_qty', 'jiudingQty'],
  pendingQty: ['待处理数量', 'pending_qty', 'pendingQty'],
} as const

function readField(row: RawRow, keys: readonly string[]): unknown {
  for (const key of keys) {
    if (key in row) {
      return row[key]
    }
  }

  return undefined
}

function toText(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return String(value)
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }

  return null
}

function normalizeRows(data: ComparisonResult[]): DisplayRow[] {
  return data
    .filter((item): item is RawRow => typeof item === 'object' && item !== null && !Array.isArray(item))
    .map((row) => ({
      date: toText(readField(row, FIELD_ALIASES.date)),
      orderNo: toText(readField(row, FIELD_ALIASES.orderNo)),
      factory: toText(readField(row, FIELD_ALIASES.factory)),
      model: toText(readField(row, FIELD_ALIASES.model)),
      company: toText(readField(row, FIELD_ALIASES.company)),
      customerQty: toText(readField(row, FIELD_ALIASES.customerQty)),
      jiudingQty: toText(readField(row, FIELD_ALIASES.jiudingQty)),
      pendingQty: toNumber(readField(row, FIELD_ALIASES.pendingQty)),
    }))
}

function renderPendingBadge(value: number | null) {
  if (value === null) {
    return (
      <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
        -
      </span>
    )
  }

  const isPositive = value > 0
  const toneClassName = isPositive
    ? 'bg-amber-100 text-amber-700'
    : 'bg-emerald-100 text-emerald-700'

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${toneClassName}`}>
      {value > 0 ? `+${value}` : value}
    </span>
  )
}

export default function ResultsTable({ data }: ResultsTableProps) {
  const rows = normalizeRows(data)

  if (rows.length === 0) {
    return <div className="py-10 text-center text-slate-500">暂无异常</div>
  }

  const factoryCount = new Set(rows.map((row) => row.factory).filter((value) => value !== '-')).size
  const totalPending = rows.reduce((sum, row) => sum + Math.abs(row.pendingQty ?? 0), 0)

  const stats = [
    { icon: AlertTriangle, label: '异常', value: rows.length },
    { icon: Factory, label: '工厂', value: factoryCount },
    { icon: Layers3, label: '差量', value: totalPending },
  ]

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        {stats.map((stat) => {
          const Icon = stat.icon

          return (
            <div
              key={stat.label}
              className="rounded-[24px] border border-slate-200 bg-[linear-gradient(135deg,rgba(255,255,255,0.95),rgba(248,250,252,0.92))] px-4 py-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold tracking-[0.22em] text-slate-400">{stat.label}</span>
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                  <Icon size={18} />
                </span>
              </div>
              <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">{stat.value}</p>
            </div>
          )
        })}
      </div>

      <div className="overflow-hidden rounded-[30px] border border-slate-200 bg-white/92 shadow-[0_24px_50px_-34px_rgba(15,23,42,0.28)]">
        <div className="flex items-center justify-between border-b border-slate-200 bg-[linear-gradient(135deg,rgba(255,248,235,0.95),rgba(240,252,252,0.92))] px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/80 text-slate-600">
              <Hash size={18} />
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-900">结果明细</p>
              <p className="text-xs text-slate-400">{rows.length} 条</p>
            </div>
          </div>
          <p className="text-xs text-slate-400">可横向查看</p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left">
            <thead className="bg-slate-50/90">
              <tr>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap">日期</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap">订单</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap">工厂</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap">型号</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap">公司</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap text-right">工厂量</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap text-right">久鼎量</th>
                <th className="px-4 py-4 text-xs font-semibold tracking-[0.16em] text-slate-500 whitespace-nowrap text-right">差量</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/80">
              {rows.map((row, index) => (
                <tr key={`${row.orderNo}-${index}`} className="transition hover:bg-slate-50/70">
                  <td className="px-4 py-4 text-sm text-slate-600 whitespace-nowrap">{row.date}</td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-semibold tracking-tight text-slate-900 [font-family:ui-monospace,SFMono-Regular,Consolas,monospace]">
                      {row.orderNo}
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap">
                    <span className="inline-flex rounded-full bg-cyan-50 px-3 py-1.5 text-sm font-medium text-cyan-700">
                      {row.factory}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-700 whitespace-nowrap">{row.model}</td>
                  <td className="px-4 py-4 text-sm text-slate-700 whitespace-nowrap">{row.company}</td>
                  <td className="px-4 py-4 text-sm font-medium text-slate-700 whitespace-nowrap text-right">{row.customerQty}</td>
                  <td className="px-4 py-4 text-sm font-medium text-slate-700 whitespace-nowrap text-right">{row.jiudingQty}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-right">{renderPendingBadge(row.pendingQty)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
