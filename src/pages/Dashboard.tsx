import { useNavigate } from 'react-router-dom'
import ModuleCard from '../components/ModuleCard'
import { FileSpreadsheet } from 'lucide-react'

export default function Dashboard() {
  const navigate = useNavigate()

  const modules = [
    {
      title: '工厂订单数据核对',
      description: '上传工厂侧和久鼎侧Excel文档，进行订单数据对比，生成差异报告',
      icon: <FileSpreadsheet size={32} />,
      path: '/order-comparison'
    }
  ]

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-8">工作台</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((module) => (
            <ModuleCard
              key={module.path}
              title={module.title}
              description={module.description}
              icon={module.icon}
              onClick={() => navigate(module.path)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}