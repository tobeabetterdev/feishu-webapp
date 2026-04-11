import { AlertTriangle, ChevronDown, ChevronUp, Factory, Hash, Layers3 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { ComparisonResult } from '../types'

interface ResultsTableProps {
  data: ComparisonResult[]
}

type RawRow = Record<string, unknown>
type HengyiCategory = '工厂侧待补录' | '久鼎侧待补录' | '数量差异待核实'

interface HengyiGroup {
  key: string
  type: HengyiCategory
  jiudingOrderNo: string
  factoryOrderNo: string
  factory: string
  company: string
  jiudingQty: string
  diff: number | null
  jiuding: RawRow | null
  rows: RawRow[]
}

const DIFF_KEYS = ['差量', '待处理数量', 'pendingQty', 'pending_qty'] as const
const FACTORY_KEYS = ['工厂(工厂)', '工厂', 'factory'] as const
const HENGYI_TYPES: HengyiCategory[] = ['工厂侧待补录', '久鼎侧待补录', '数量差异待核实']

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

function readField(row: RawRow, keys: readonly string[]): unknown {
  for (const key of keys) {
    if (key in row) {
      return row[key]
    }
  }

  return undefined
}

function buildColumns(data: RawRow[]): string[] {
  const firstRow = data[0]
  return firstRow ? Object.keys(firstRow) : []
}

function isHengyiRow(row: RawRow | undefined): row is RawRow {
  return !!row && '异常类型' in row
}

function renderDiffBadge(value: unknown) {
  const diff = toNumber(value)
  if (diff === null) {
    return <span className="text-base text-slate-400">-</span>
  }

  const toneClassName =
    diff > 0 ? 'bg-amber-100 text-amber-800' : diff < 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'

  return (
    <span className={`inline-flex rounded-full px-3 py-1.5 text-sm font-semibold ${toneClassName}`}>
      {diff > 0 ? `+${diff}` : diff}
    </span>
  )
}

function renderCompactCell(label: string, value: unknown) {
  if (label === '差量') {
    return renderDiffBadge(value)
  }

  const text = toText(value)
  if (text === '-') {
    return <span className="text-base text-slate-400">-</span>
  }

  const isCodeLike = label.includes('单') || label.includes('订单')
  if (isCodeLike) {
    return (
      <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-semibold text-slate-800 [font-family:ui-monospace,SFMono-Regular,Consolas,monospace]">
        {text}
      </span>
    )
  }

  return <span className="text-base text-slate-700">{text}</span>
}

function buildHengyiGroups(rows: RawRow[]): HengyiGroup[] {
  const groupMap = new Map<string, HengyiGroup>()

  rows.forEach((row) => {
    const type = toText(row['异常类型']) as HengyiCategory
    const jiudingOrderNo = toText(row['出库单号(久鼎)'])
    const factoryOrderNo = toText(row['交货单(工厂)'])
    const key = jiudingOrderNo !== '-' ? `J-${jiudingOrderNo}` : `F-${factoryOrderNo}`

    const existing = groupMap.get(key)
    if (existing) {
      existing.rows.push(row)
      if (!existing.jiuding && jiudingOrderNo !== '-') {
        existing.jiuding = row
        existing.jiudingOrderNo = jiudingOrderNo
      }
      return
    }

    groupMap.set(key, {
      key,
      type,
      jiudingOrderNo,
      factoryOrderNo,
      factory: toText(row['工厂(工厂)']),
      company: toText(row['会员名称(久鼎)']) !== '-' ? toText(row['会员名称(久鼎)']) : toText(row['送达方(工厂)']),
      jiudingQty: toText(row['实际出库数量(久鼎)']),
      diff: toNumber(row['差量']),
      jiuding: jiudingOrderNo !== '-' ? row : null,
      rows: [row],
    })
  })

  return Array.from(groupMap.values()).sort((left, right) => {
    const leftOrder = left.jiudingOrderNo !== '-' ? left.jiudingOrderNo : left.factoryOrderNo
    const rightOrder = right.jiudingOrderNo !== '-' ? right.jiudingOrderNo : right.factoryOrderNo
    return leftOrder.localeCompare(rightOrder, 'zh-CN')
  })
}

function GenericResultsTable({ rows }: { rows: RawRow[] }) {
  const columns = buildColumns(rows)
  const factoryCount = new Set(
    rows
      .map((row) => readField(row, FACTORY_KEYS))
      .map((value) => toText(value))
      .filter((value) => value !== '-'),
  ).size
  const totalPending = rows.reduce((sum, row) => {
    const diff = toNumber(readField(row, DIFF_KEYS))
    return sum + Math.abs(diff ?? 0)
  }, 0)
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
                <span className="text-sm font-semibold tracking-[0.18em] text-slate-400">{stat.label}</span>
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
              <p className="text-base font-semibold text-slate-900">结果明细</p>
              <p className="text-sm text-slate-400">{rows.length} 条</p>
            </div>
          </div>
          <p className="text-sm text-slate-400">支持横向查看</p>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left">
            <thead className="bg-slate-50/90">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    className={`px-4 py-4 text-sm font-semibold tracking-[0.06em] text-slate-500 whitespace-nowrap ${
                      DIFF_KEYS.includes(column as (typeof DIFF_KEYS)[number]) ? 'text-right' : ''
                    }`}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/80">
              {rows.map((row, index) => (
                <tr key={index} className="transition hover:bg-slate-50/70">
                  {columns.map((column) => (
                    <td
                      key={`${index}-${column}`}
                      className={`px-4 py-4 whitespace-nowrap ${
                        DIFF_KEYS.includes(column as (typeof DIFF_KEYS)[number]) ? 'text-right' : ''
                      }`}
                    >
                      {renderCompactCell(column, row[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function HengyiResultsView({ rows }: { rows: RawRow[] }) {
  const groups = useMemo(() => buildHengyiGroups(rows), [rows])
  const [activeType, setActiveType] = useState<HengyiCategory>('数量差异待核实')
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({})

  const groupedByType = useMemo(() => {
    return HENGYI_TYPES.reduce<Record<HengyiCategory, HengyiGroup[]>>(
      (acc, type) => {
        acc[type] = groups.filter((group) => group.type === type)
        return acc
      },
      {
        工厂侧待补录: [],
        久鼎侧待补录: [],
        数量差异待核实: [],
      },
    )
  }, [groups])
  const stats = [
    {
      type: '工厂侧待补录' as HengyiCategory,
      label: '工厂待补录',
      value: groupedByType['工厂侧待补录'].length,
      activeClassName: 'border-amber-300 bg-amber-500 text-white shadow-[0_18px_38px_-24px_rgba(217,119,6,0.55)]',
    },
    {
      type: '久鼎侧待补录' as HengyiCategory,
      label: '久鼎待补录',
      value: groupedByType['久鼎侧待补录'].length,
      activeClassName: 'border-cyan-300 bg-cyan-600 text-white shadow-[0_18px_38px_-24px_rgba(8,145,178,0.55)]',
    },
    {
      type: '数量差异待核实' as HengyiCategory,
      label: '数量待核实',
      value: groupedByType['数量差异待核实'].length,
      activeClassName: 'border-rose-300 bg-rose-600 text-white shadow-[0_18px_38px_-24px_rgba(225,29,72,0.52)]',
    },
  ]

  const visibleGroups = groupedByType[activeType]

  const toggleGroup = (key: string) => {
    setExpandedKeys((current) => ({ ...current, [key]: !current[key] }))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-nowrap items-stretch gap-3 overflow-x-auto pb-1">
        {stats.map((stat) => (
          <button
            key={stat.type}
            type="button"
            onClick={() => setActiveType(stat.type)}
            className={`min-w-[188px] flex-1 rounded-[22px] border px-4 py-4 text-left transition ${
              activeType === stat.type
                ? stat.activeClassName
                : 'border-slate-200 bg-slate-100 text-slate-900 hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            <p className={`text-sm font-semibold tracking-[0.12em] ${activeType === stat.type ? 'text-white/80' : 'text-slate-500'}`}>
              {stat.label}
            </p>
            <p className="mt-3 text-3xl font-semibold tracking-tight">{stat.value}</p>
          </button>
        ))}
      </div>

      <div className="rounded-[30px] border border-slate-200 bg-white/92 shadow-[0_24px_50px_-34px_rgba(15,23,42,0.28)]">
        <div className="flex flex-col gap-3 border-b border-slate-200 bg-[linear-gradient(135deg,rgba(255,248,235,0.95),rgba(240,252,252,0.92))] px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/80 text-slate-600">
              <Hash size={18} />
            </span>
            <div>
              <p className="text-base font-semibold text-slate-900">{activeType}</p>
              <p className="text-sm text-slate-400">{visibleGroups.length} 组</p>
            </div>
          </div>
          <p className="text-sm text-slate-400">按订单分组查看</p>
        </div>

        <div className="space-y-3 p-4">
          {visibleGroups.length === 0 ? (
            <div className="rounded-[22px] border border-dashed border-slate-200 px-4 py-10 text-center text-base text-slate-400">
              当前分类暂无异常
            </div>
          ) : (
            visibleGroups.map((group) => {
              const expanded = expandedKeys[group.key] ?? true
              const summaryOrder = group.jiudingOrderNo !== '-' ? group.jiudingOrderNo : group.factoryOrderNo

              return (
                <div key={group.key} className="overflow-hidden rounded-[24px] border border-slate-200 bg-white">
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.key)}
                    className="flex w-full items-center justify-between gap-4 bg-slate-50/80 px-4 py-4 text-left transition hover:bg-slate-100/80"
                  >
                    <div className="grid flex-1 gap-4 md:grid-cols-[1.2fr_1fr_1.2fr_auto]">
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">订单</p>
                        <div className="mt-2">{renderCompactCell('订单', summaryOrder)}</div>
                      </div>
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">工厂</p>
                        <p className="mt-2 text-base font-medium text-slate-800">{group.factory}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">公司</p>
                        <p className="mt-2 text-base font-medium text-slate-800">{group.company}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">差量</p>
                        <div className="mt-2">{renderDiffBadge(group.diff)}</div>
                      </div>
                    </div>
                    <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-slate-500">
                      {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </span>
                  </button>

                  {expanded ? (
                    <div className="space-y-4 px-4 py-4">
                      <div className="hidden rounded-[20px] border border-slate-200 bg-[linear-gradient(135deg,rgba(240,252,252,0.88),rgba(255,248,235,0.72))] p-4">
                        <p className="text-sm font-semibold tracking-[0.12em] text-slate-400">久鼎摘要</p>
                        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-3 text-base text-slate-700">
                          <div className="flex items-center gap-2 whitespace-nowrap">
                            <span className="text-slate-400">出库单号</span>
                            {renderCompactCell('出库单号', group.jiuding?.['出库单号(久鼎)'])}
                          </div>
                          <div className="flex items-center gap-2 whitespace-nowrap">
                            <span className="text-slate-400">客户名称</span>
                            <span>{toText(group.jiuding?.['客户名称(久鼎)'])}</span>
                          </div>
                          <div className="flex items-center gap-2 whitespace-nowrap">
                            <span className="text-slate-400">会员名称</span>
                            <span>{toText(group.jiuding?.['会员名称(久鼎)'])}</span>
                          </div>
                          <div className="flex items-center gap-2 whitespace-nowrap">
                            <span className="text-slate-400">久鼎数量</span>
                            <span className="font-semibold text-slate-900">{group.jiudingQty}</span>
                          </div>
                          <div className="flex items-center gap-2 whitespace-nowrap">
                            <span className="text-slate-400">订单日期</span>
                            <span>{toText(group.jiuding?.['订单日期(久鼎)'])}</span>
                          </div>
                        </div>
                      </div>

                      <div className="overflow-hidden rounded-[20px] border border-slate-200 bg-[linear-gradient(135deg,rgba(240,252,252,0.88),rgba(255,248,235,0.72))]">
                        <div className="border-b border-slate-200/80 px-4 py-3">
                          <p className="text-sm font-semibold tracking-[0.12em] text-slate-400">久鼎摘要</p>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-left">
                            <thead>
                              <tr className="border-b border-slate-200/80">
                                {['出库单号', '客户名称', '会员名称', '久鼎数量', '订单日期'].map((column) => (
                                  <th
                                    key={column}
                                    className={`px-4 py-3 text-sm font-semibold tracking-[0.06em] text-slate-400 whitespace-nowrap ${
                                      column === '久鼎数量' ? 'text-right' : ''
                                    }`}
                                  >
                                    {column}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="bg-white/55">
                                <td className="px-4 py-4 whitespace-nowrap">
                                  {renderCompactCell('出库单号', group.jiuding?.['出库单号(久鼎)'])}
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">
                                  {toText(group.jiuding?.['客户名称(久鼎)'])}
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">
                                  {toText(group.jiuding?.['会员名称(久鼎)'])}
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-right text-base font-semibold text-slate-900">
                                  {group.jiudingQty}
                                </td>
                                <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">
                                  {toText(group.jiuding?.['订单日期(久鼎)'])}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="rounded-[20px] border border-slate-200 bg-white">
                        <div className="border-b border-slate-200 px-4 py-3">
                          <p className="text-sm font-semibold tracking-[0.12em] text-slate-400">工厂明细</p>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-left">
                            <thead>
                              <tr className="border-b border-slate-200">
                                {['交货单', '工厂', '送达方', '车牌号', '型号', '托盘数'].map((column) => (
                                  <th
                                    key={column}
                                    className={`px-4 py-3 text-sm font-semibold tracking-[0.06em] text-slate-400 whitespace-nowrap ${
                                      column === '托盘数' ? 'text-right' : ''
                                    }`}
                                  >
                                    {column}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {group.rows.map((row, index) => (
                                <tr key={`${group.key}-${index}`} className="hover:bg-slate-50/70">
                                  <td className="px-4 py-4 whitespace-nowrap">{renderCompactCell('交货单', row['交货单(工厂)'])}</td>
                                  <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">{toText(row['工厂(工厂)'])}</td>
                                  <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">{toText(row['送达方(工厂)'])}</td>
                                  <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">{toText(row['车牌号(工厂)'])}</td>
                                  <td className="px-4 py-4 whitespace-nowrap text-base text-slate-700">{toText(row['型号(工厂)'])}</td>
                                  <td className="px-4 py-4 whitespace-nowrap text-right text-base font-semibold text-slate-900">{toText(row['托盘数(工厂)'])}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

export default function ResultsTable({ data }: ResultsTableProps) {
  const rows: RawRow[] = data.filter(
    (item) => typeof item === 'object' && item !== null && !Array.isArray(item),
  ) as RawRow[]

  if (rows.length === 0) {
    return <div className="py-10 text-center text-slate-500">暂无异常</div>
  }

  if (isHengyiRow(rows[0])) {
    return <HengyiResultsView rows={rows} />
  }

  return <GenericResultsTable rows={rows} />
}
