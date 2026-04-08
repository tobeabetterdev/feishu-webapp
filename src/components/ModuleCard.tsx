import { ReactNode } from 'react'

interface ModuleCardProps {
  title: string
  description: string
  icon: ReactNode
  onClick: () => void
}

export default function ModuleCard({ title, description, icon, onClick }: ModuleCardProps) {
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-lg shadow-md p-6 cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105"
    >
      <div className="flex items-center mb-4">
        <div className="text-blue-600 mr-3">{icon}</div>
        <h3 className="text-xl font-semibold text-gray-800">{title}</h3>
      </div>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}