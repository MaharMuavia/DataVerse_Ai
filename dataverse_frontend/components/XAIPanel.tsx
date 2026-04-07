import { Zap, TrendingUp, AlertTriangle, Lightbulb } from 'lucide-react'
import { XAIResults } from '../lib/types'

interface XAIPanelProps {
  results: XAIResults
}

export function XAIPanel({ results }: XAIPanelProps) {
  return (
    <div className="bg-dv-surface border border-dv-border rounded-lg p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Zap size={24} className="text-dv-accent" />
        <h3 className="text-lg font-medium text-dv-text">XAI Insights</h3>
      </div>

      {results.featureImportance && results.featureImportance.length > 0 && (
        <div>
          <h4 className="text-md font-medium text-dv-text mb-3 flex items-center gap-2">
            <TrendingUp size={16} />
            Feature Importance
          </h4>
          <div className="space-y-2">
            {results.featureImportance.slice(0, 5).map((feature, index) => (
              <div key={index} className="bg-dv-bg rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-dv-text">{feature.name}</span>
                  <span className="text-sm text-dv-accent font-medium">
                    {(feature.importance * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-dv-surface rounded-full h-2">
                  <div
                    className="bg-dv-accent h-2 rounded-full transition-all duration-300"
                    style={{ width: `${feature.importance * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.shapValues && results.shapValues.length > 0 && (
        <div>
          <h4 className="text-md font-medium text-dv-text mb-3 flex items-center gap-2">
            <Lightbulb size={16} />
            SHAP Analysis
          </h4>
          <div className="bg-dv-bg rounded-lg p-4">
            <p className="text-sm text-dv-text-secondary mb-3">
              SHAP (SHapley Additive exPlanations) values show how each feature contributes to individual predictions
            </p>
            <div className="text-sm text-dv-text">
              Analysis completed for {results.shapValues.length} features
            </div>
          </div>
        </div>
      )}

      {results.limeExplanations && results.limeExplanations.length > 0 && (
        <div>
          <h4 className="text-md font-medium text-dv-text mb-3 flex items-center gap-2">
            <AlertTriangle size={16} />
            LIME Explanations
          </h4>
          <div className="space-y-2">
            {results.limeExplanations.slice(0, 3).map((explanation, index) => (
              <div key={index} className="bg-dv-bg rounded-lg p-3">
                <p className="text-sm text-dv-text">{explanation.explanation}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-dv-text-secondary">Confidence</span>
                  <span className="text-xs font-medium text-dv-accent">
                    {(explanation.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.recommendations && results.recommendations.length > 0 && (
        <div>
          <h4 className="text-md font-medium text-dv-text mb-3">Recommendations</h4>
          <div className="space-y-2">
            {results.recommendations.map((rec, index) => (
              <div key={index} className="flex items-start gap-3 bg-dv-bg rounded-lg p-3">
                <Lightbulb size={16} className="text-dv-accent mt-0.5 flex-shrink-0" />
                <p className="text-sm text-dv-text">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}