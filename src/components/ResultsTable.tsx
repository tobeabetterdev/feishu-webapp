import { ComparisonResult } from '../types'

interface ResultsTableProps {
  data: ComparisonResult[]
}

export default function ResultsTable({ data }: ResultsTableProps) {
  if (data.length === 0) {
    return <div className="text-center text-gray-500 py-8">暂无数据</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日期</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">单号</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">工厂</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">型号</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">公司</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">客户出库数</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">久鼎出库数</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">待处理数量</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.map((row, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm text-gray-900">{row.日期}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.单号}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.工厂 || '-'}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.型号}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.公司}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.客户出库数 ?? '-'}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.久鼎出库数 ?? '-'}</td>
              <td className="px-4 py-3 text-sm text-gray-900">{row.待处理数量 ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
