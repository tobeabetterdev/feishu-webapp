import { AlertTriangle, ChevronDown, ChevronUp, Factory, Hash, Layers3 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { ComparisonResult } from '../types'

interface ResultsTableProps {
  data: ComparisonResult[]
}

type RawRow = Record<string, unknown>
type HengyiCategory = '数量差异' | '久鼎缺单' | '工厂缺单'

interface HengyiGroup {
  key: string
  type: HengyiCategory
  orderNo: string
  factory: string
  orderDate: string
  memberName: string
  deliveryName: string
  diff: number | null
  rows: RawRow[]
}

const DIFF_KEYS = ['出库数量差异', '差量', '待处理数量', 'pendingQty', 'pending_qty'] as const
const FACTORY_KEYS = ['工厂', 'factory'] as const
const HENGYI_TYPES: HengyiCategory[] = ['数量差异', '久鼎缺单', '工厂缺单']
const HENGYI_FACTORY_DETAIL_COLUMNS = ['送达方', '工厂交货单', '工厂车牌号', '工厂物料组', '工厂交货数量', '工厂托盘数', '工厂业务员', '工厂过账日期']
const HENGYI_JIUDING_DETAIL_COLUMNS = ['会员名称', '久鼎出库单号', '久鼎产品类型', '久鼎客户名称', '久鼎子公司名称', '久鼎出库数量', '久鼎订单日期']

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
  return !!row && '异常类型' in row && '订单号' in row && '出库数量差异' in row
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
  if (label === '出库数量差异' || label === '差量') {
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
    const orderNo = toText(row['订单号'])
    const existing = groupMap.get(orderNo)
    if (existing) {
      existing.rows.push(row)
      if (existing.memberName === '-' && toText(row['会员名称']) !== '-') {
        existing.memberName = toText(row['会员名称'])
      }
      if (existing.deliveryName === '-' && toText(row['送达方']) !== '-') {
        existing.deliveryName = toText(row['送达方'])
      }
      if (existing.orderDate === '-' && toText(row['订单日期']) !== '-') {
        existing.orderDate = toText(row['订单日期'])
      }
      return
    }

    groupMap.set(orderNo, {
      key: orderNo,
      type: toText(row['异常类型']) as HengyiCategory,
      orderNo,
      factory: toText(row['工厂']),
      orderDate: toText(row['订单日期']),
      memberName: toText(row['会员名称']),
      deliveryName: toText(row['送达方']),
      diff: toNumber(row['出库数量差异']),
      rows: [row],
    })
  })

  return Array.from(groupMap.values()).sort((left, right) => left.orderNo.localeCompare(right.orderNo, 'zh-CN'))
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

function HengyiTableBlock({
  title,
  columns,
  row,
}: {
  title: string
  columns: string[]
  row: RawRow
}) {
  return (
    <div className="overflow-hidden rounded-[20px] border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <p className="text-sm font-semibold tracking-[0.12em] text-slate-400">{title}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left">
          <thead>
            <tr className="border-b border-slate-200">
              {columns.map((column) => (
                <th
                  key={column}
                  className={`px-4 py-3 text-sm font-semibold tracking-[0.06em] text-slate-400 whitespace-nowrap ${
                    column.includes('数量') || column.includes('托盘') ? 'text-right' : ''
                  }`}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="hover:bg-slate-50/70">
              {columns.map((column) => (
                <td
                  key={column}
                  className={`px-4 py-4 whitespace-nowrap ${
                    column.includes('数量') || column.includes('托盘') ? 'text-right' : ''
                  }`}
                >
                  {renderCompactCell(column, row[column])}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

function HengyiResultsView({ rows }: { rows: RawRow[] }) {
  const groups = useMemo(() => buildHengyiGroups(rows), [rows])
  const [activeType, setActiveType] = useState<HengyiCategory>('数量差异')
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({})

  const groupedByType = useMemo(() => {
    return HENGYI_TYPES.reduce<Record<HengyiCategory, HengyiGroup[]>>(
      (acc, type) => {
        acc[type] = groups.filter((group) => group.type === type)
        return acc
      },
      {
        数量差异: [],
        久鼎缺单: [],
        工厂缺单: [],
      },
    )
  }, [groups])

  const stats = [
    {
      type: '数量差异' as HengyiCategory,
      label: '数量待核实',
      value: groupedByType['数量差异'].length,
      activeClassName: 'border-rose-300 bg-rose-600 text-white shadow-[0_18px_38px_-24px_rgba(225,29,72,0.52)]',
    },
    {
      type: '久鼎缺单' as HengyiCategory,
      label: '久鼎待补录',
      value: groupedByType['久鼎缺单'].length,
      activeClassName: 'border-cyan-300 bg-cyan-600 text-white shadow-[0_18px_38px_-24px_rgba(8,145,178,0.55)]',
    },
    {
      type: '工厂缺单' as HengyiCategory,
      label: '工厂待补录',
      value: groupedByType['工厂缺单'].length,
      activeClassName: 'border-amber-300 bg-amber-500 text-white shadow-[0_18px_38px_-24px_rgba(217,119,6,0.55)]',
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
              <p className="text-base font-semibold text-slate-900">{stats.find((item) => item.type === activeType)?.label}</p>
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
              const headerTone =
                group.type === '数量差异'
                  ? 'bg-rose-50/80'
                  : group.type === '久鼎缺单'
                    ? 'bg-cyan-50/80'
                    : 'bg-amber-50/80'

              return (
                <div key={group.key} className="overflow-hidden rounded-[24px] border border-slate-200 bg-white">
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.key)}
                    className={`flex w-full items-center justify-between gap-4 px-4 py-4 text-left transition hover:bg-slate-100/80 ${headerTone}`}
                  >
                    <div className="grid flex-1 gap-4 md:grid-cols-[1.1fr_1fr_1fr_1fr_auto]">
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">订单号</p>
                        <div className="mt-2">{renderCompactCell('订单号', group.orderNo)}</div>
                      </div>
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">异常类型</p>
                        <p className="mt-2 text-base font-medium text-slate-800">{group.type}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">工厂</p>
                        <p className="mt-2 text-base font-medium text-slate-800">{group.factory}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">订单日期</p>
                        <p className="mt-2 text-base font-medium text-slate-800">{group.orderDate}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">差异</p>
                        <div className="mt-2">{renderDiffBadge(group.diff)}</div>
                      </div>
                    </div>
                    <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-slate-500">
                      {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </span>
                  </button>

                  {expanded ? (
                    <div className="space-y-4 px-4 py-4">
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-[20px] border border-slate-200 bg-slate-50/70 px-4 py-3">
                          <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">送达方</p>
                          <p className="mt-2 text-base font-medium text-slate-800">{group.deliveryName}</p>
                        </div>
                        <div className="rounded-[20px] border border-slate-200 bg-slate-50/70 px-4 py-3">
                          <p className="text-sm font-semibold tracking-[0.08em] text-slate-400">会员名称</p>
                          <p className="mt-2 text-base font-medium text-slate-800">{group.memberName}</p>
                        </div>
                      </div>

                      {group.rows.map((row, index) => (
                        <div key={`${group.key}-${index}`} className="grid gap-4 xl:grid-cols-2">
                          <HengyiTableBlock title={index === 0 ? '工厂明细' : `工厂明细 ${index + 1}`} columns={HENGYI_FACTORY_DETAIL_COLUMNS} row={row} />
                          <HengyiTableBlock title={index === 0 ? '久鼎明细' : `久鼎明细 ${index + 1}`} columns={HENGYI_JIUDING_DETAIL_COLUMNS} row={row} />
                        </div>
                      ))}
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
