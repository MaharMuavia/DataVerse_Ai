import { Brain, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import { MLResults } from '../lib/types'

interface MLStatusCardProps {
  results: MLResults
}

export function MLStatusCard({ results }: MLStatusCardProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={20} className="text-green-500" />
      case 'running':
        return <Clock size={20} className="text-blue-500 animate-spin" />
      case 'failed':
        return <AlertCircle size={20} className="text-red-500" />
      default:
        return <Clock size={20} className="text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'border-green-200 bg-green-50'
      case 'running':
        return 'border-blue-200 bg-blue-50'
      case 'failed':
        return 'border-red-200 bg-red-50'
      default:
        return 'border-dv-border bg-dv-bg'
    }
  }

  return (
    <div className={`border rounded-lg p-4 ${getStatusColor(results.status)}`}>
      <div className="flex items-center gap-3 mb-3">
        <Brain size={24} className="text-dv-accent" />
        <div>
          <h3 className="text-lg font-medium text-dv-text">Machine Learning Training</h3>
          <p className="text-sm text-dv-text-secondary capitalize">{results.status}</p>
        </div>
        {getStatusIcon(results.status)}
      </div>

      {results.bestModel && (
        <div className="space-y-3">
          <div className="bg-dv-surface rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-dv-text">Best Model</span>
              <span className="text-sm text-dv-accent font-medium">
                {results.bestModel.name}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-dv-text-secondary">Accuracy</span>
              <span className="text-sm font-medium text-dv-text">
                {(results.bestModel.accuracy * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {results.models && results.models.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-dv-text mb-2">Model Comparison</h4>
              <div className="space-y-2">
                {results.models.slice(0, 3).map((model, index) => (
                  <div key={index} className="flex items-center justify-between bg-dv-surface rounded-lg p-2">
                    <span className="text-sm text-dv-text">{model.name}</span>
                    <span className="text-sm font-medium text-dv-text">
                      {(model.accuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {results.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3">
          <p className="text-sm text-red-700">{results.error}</p>
        </div>
      )}
    </div>
  )
}