import { ComparisonResult } from '../types'

interface ResultsTableProps {
  data: ComparisonResult[]
}

export default function ResultsTable({ data }: ResultsTableProps) {
  if (data.length === 0) {
    return <div className="text-center text-gray-500 py-8">暂无数据</div>
  }

  return (
    <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
      <table className="min-w-full bg-white border border-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">日期</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">单号</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">工厂</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">型号</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">公司</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">客户出库数</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">久鼎出库数</th>
            <th className="px-2 md:px-4 py-2 md:py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">待处理数量</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.map((row, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.日期}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.单号}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.工厂 || '-'}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.型号}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.公司}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.客户出库数 ?? '-'}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.久鼎出库数 ?? '-'}</td>
              <td className="px-2 md:px-4 py-2 md:py-3 text-xs md:text-sm text-gray-900 whitespace-nowrap">{row.待处理数量 ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
