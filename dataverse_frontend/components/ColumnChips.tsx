import { X } from 'lucide-react'
import { Dataset } from '../lib/types'

interface ColumnChipsProps {
  dataset: Dataset
  selectedColumns: string[]
  onColumnToggle: (column: string) => void
}

export function ColumnChips({ dataset, selectedColumns, onColumnToggle }: ColumnChipsProps) {
  const getDtypeColor = (dtype: string) => {
    switch (dtype.toLowerCase()) {
      case 'int64':
      case 'float64':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'object':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'bool':
        return 'bg-purple-100 text-purple-800 border-purple-200'
      case 'datetime64[ns]':
        return 'bg-orange-100 text-orange-800 border-orange-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-dv-text">Dataset Columns</h3>
        <span className="text-sm text-dv-text-secondary">
          {selectedColumns.length} of {dataset.columnNames.length} selected
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {dataset.columnNames.map((column, index) => {
          const isSelected = selectedColumns.includes(column)
          const dtype = dataset.columnDtypes[index]

          return (
            <button
              key={column}
              onClick={() => onColumnToggle(column)}
              className={`flex items-center gap-2 px-3 py-1 rounded-full border text-sm transition-colors ${
                isSelected
                  ? 'bg-dv-accent text-dv-accent-foreground border-dv-accent'
                  : `border-dv-border hover:border-dv-accent/50 ${getDtypeColor(dtype)}`
              }`}
            >
              <span>{column}</span>
              <span className="text-xs opacity-75">({dtype})</span>
              {isSelected && <X size={14} />}
            </button>
          )
        })}
      </div>

      <div className="text-sm text-dv-text-secondary">
        <p>Click columns to include/exclude from analysis</p>
      </div>
    </div>
  )
}