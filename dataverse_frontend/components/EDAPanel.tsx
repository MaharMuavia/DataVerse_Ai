import { BarChart3, TrendingUp, AlertTriangle, Database } from 'lucide-react'
import { EDAResults } from '../lib/types'

interface EDAPanelProps {
  results: EDAResults
}

export function EDAPanel({ results }: EDAPanelProps) {
  return (
    <div className="bg-dv-surface border border-dv-border rounded-lg p-6 space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 size={24} className="text-dv-accent" />
        <h3 className="text-lg font-medium text-dv-text">Exploratory Data Analysis</h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-dv-bg rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Database size={16} className="text-dv-text-secondary" />
            <span className="text-sm font-medium text-dv-text">Rows</span>
          </div>
          <p className="text-2xl font-bold text-dv-text">{results.rowCount.toLocaleString()}</p>
        </div>

        <div className="bg-dv-bg rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-dv-text-secondary" />
            <span className="text-sm font-medium text-dv-text">Columns</span>
          </div>
          <p className="text-2xl font-bold text-dv-text">{results.columnCount}</p>
        </div>

        <div className="bg-dv-bg rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-dv-text-secondary" />
            <span className="text-sm font-medium text-dv-text">Missing Values</span>
          </div>
          <p className="text-2xl font-bold text-dv-text">{results.missingValuesCount}</p>
        </div>

        <div className="bg-dv-bg rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={16} className="text-dv-text-secondary" />
            <span className="text-sm font-medium text-dv-text">Numeric Columns</span>
          </div>
          <p className="text-2xl font-bold text-dv-text">{results.numericColumnsCount}</p>
        </div>
      </div>

      {results.correlations && results.correlations.length > 0 && (
        <div>
          <h4 className="text-md font-medium text-dv-text mb-3">Top Correlations</h4>
          <div className="space-y-2">
            {results.correlations.slice(0, 5).map((corr, index) => (
              <div key={index} className="flex items-center justify-between bg-dv-bg rounded-lg p-3">
                <span className="text-sm text-dv-text">
                  {corr.feature1} ↔ {corr.feature2}
                </span>
                <span className="text-sm font-medium text-dv-accent">
                  {corr.correlation.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.outliers && (
        <div>
          <h4 className="text-md font-medium text-dv-text mb-3">Outlier Detection</h4>
          <div className="bg-dv-bg rounded-lg p-4">
            <p className="text-sm text-dv-text-secondary">
              {results.outliers.totalOutliers} potential outliers detected across {results.outliers.columnsWithOutliers} columns
            </p>
          </div>
        </div>
      )}
    </div>
  )
}