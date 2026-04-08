import { Upload } from 'lucide-react'

interface FileUploadProps {
  label: string
  onFileSelect: (file: File) => void
  selectedFile: File | null
}

export default function FileUpload({ label, onFileSelect, selectedFile }: FileUploadProps) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onFileSelect(file)
    }
  }

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-colors">
      <input
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileChange}
        className="hidden"
        id={`file-upload-${label}`}
      />
      <label htmlFor={`file-upload-${label}`} className="cursor-pointer">
        <Upload className="mx-auto mb-2 text-gray-400" size={32} />
        <p className="text-sm font-medium text-gray-700 mb-1">{label}</p>
        {selectedFile ? (
          <p className="text-xs text-green-600">📁 {selectedFile.name}</p>
        ) : (
          <p className="text-xs text-gray-500">点击或拖拽上传 Excel 文件</p>
        )}
      </label>
    </div>
  )
}
