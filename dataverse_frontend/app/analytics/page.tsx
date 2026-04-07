'use client'

import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { Brain, TrendingUp, Zap, BarChart3, Edit2, Trash2, Download, Eye } from 'lucide-react'

interface Model {
  id: string
  name: string
  type: 'classification' | 'regression' | 'clustering'
  accuracy: number
  createdAt: string
  dataset: string
  targetVariable: string
  features: string[]
  status: 'training' | 'ready' | 'archived'
}

export default function AnalyticsPage() {
  const [models, setModels] = useState<Model[]>([
    {
      id: '1',
      name: 'Sales Prediction Model',
      type: 'regression',
      accuracy: 0.87,
      createdAt: 'Today',
      dataset: 'sales_2024.csv',
      targetVariable: 'Revenue',
      features: ['Product Category', 'Season', 'Marketing Spend', 'Customer Segment'],
      status: 'ready',
    },
    {
      id: '2',
      name: 'Customer Churn Classifier',
      type: 'classification',
      accuracy: 0.92,
      createdAt: '2 days ago',
      dataset: 'customers.csv',
      targetVariable: 'Churn',
      features: ['Usage Frequency', 'Support Tickets', 'Payment History'],
      status: 'ready',
    },
    {
      id: '3',
      name: 'Product Recommendation Engine',
      type: 'clustering',
      accuracy: 0.78,
      createdAt: 'Week ago',
      dataset: 'transactions.csv',
      targetVariable: 'Product Category',
      features: ['Purchase History', 'Demographics', 'Ratings'],
      status: 'archived',
    },
  ])

  const [selectedModel, setSelectedModel] = useState<Model | null>(null)
  const [tab, setTab] = useState<'models' | 'analytics' | 'anomalies'>('models')

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'regression':
        return <TrendingUp className="text-blue-500" size={20} />
      case 'classification':
        return <Brain className="text-purple-500" size={20} />
      case 'clustering':
        return <Zap className="text-orange-500" size={20} />
      default:
        return <BarChart3 size={20} />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
      case 'training':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
      case 'archived':
        return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-300'
      default:
        return ''
    }
  }

  return (
    <AppShell>
      <div className="p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-dv-text mb-2">Analytics & Models</h1>
            <p className="text-dv-text-secondary">Manage trained models and analysis features</p>
          </div>

          {/* Tabs */}
          <div className="flex gap-4 mb-8 border-b border-dv-border">
            {['models', 'analytics', 'anomalies'].map(t => (
              <button
                key={t}
                onClick={() => setTab(t as any)}
                className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                  tab === t
                    ? 'border-dv-accent text-dv-accent'
                    : 'border-transparent text-dv-text-secondary hover:text-dv-text'
                }`}
              >
                {t === 'models' && '🤖 Models'}
                {t === 'analytics' && '📊 Analytics'}
                {t === 'anomalies' && '🚨 Anomalies'}
              </button>
            ))}
          </div>

          {/* Models Tab */}
          {tab === 'models' && (
            <div className="space-y-4">
              {models.length > 0 ? (
                models.map(model => (
                  <div
                    key={model.id}
                    onClick={() => setSelectedModel(model)}
                    className="p-6 rounded-lg border border-dv-border bg-dv-bg hover:border-dv-accent hover:shadow-lg transition-all cursor-pointer group"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-start gap-4 flex-1">
                        <div className="p-3 rounded-lg bg-dv-bg-secondary">
                          {getTypeIcon(model.type)}
                        </div>
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-dv-text group-hover:text-dv-accent transition-colors">
                            {model.name}
                          </h3>
                          <p className="text-sm text-dv-text-secondary mb-2">{model.dataset}</p>
                          <div className="flex flex-wrap gap-2">
                            {model.features.map((feat, idx) => (
                              <span key={idx} className="text-xs px-2 py-1 rounded-full bg-dv-bg-secondary text-dv-text-secondary">
                                {feat}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-3">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(model.status)}`}>
                          {model.status.charAt(0).toUpperCase() + model.status.slice(1)}
                        </span>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-dv-accent">{(model.accuracy * 100).toFixed(0)}%</div>
                          <div className="text-xs text-dv-text-secondary">Accuracy</div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-sm text-dv-text-secondary mb-4">
                      <span>{model.type.charAt(0).toUpperCase() + model.type.slice(1)} • Target: {model.targetVariable}</span>
                      <span>Created {model.createdAt}</span>
                    </div>

                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-dv-text hover:border-dv-accent transition-colors text-sm font-medium">
                        <Eye size={16} />
                        View Details
                      </button>
                      <button className="p-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-dv-text hover:border-dv-accent transition-colors">
                        <Download size={16} />
                      </button>
                      <button className="p-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-red-500 hover:border-red-300 transition-colors">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-12">
                  <Brain size={48} className="mx-auto mb-4 text-dv-text-secondary opacity-50" />
                  <p className="text-dv-text-secondary">No trained models yet</p>
                </div>
              )}
            </div>
          )}

          {/* Analytics Tab */}
          {tab === 'analytics' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { title: 'Time Series Forecasting', description: 'Predict future trends', icon: '📈' },
                { title: 'Customer Segmentation', description: 'Identify customer groups', icon: '👥' },
                { title: 'Correlation Analysis', description: 'Find feature relationships', icon: '🔗' },
                { title: 'Distribution Analysis', description: 'Understand data patterns', icon: '📊' },
              ].map((feature, idx) => (
                <div key={idx} className="p-6 rounded-lg border border-dv-border bg-dv-bg hover:border-dv-accent hover:shadow-lg transition-all cursor-pointer group">
                  <div className="text-3xl mb-3">{feature.icon}</div>
                  <h3 className="font-semibold text-dv-text mb-1 group-hover:text-dv-accent transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-dv-text-secondary mb-4">{feature.description}</p>
                  <button className="text-sm font-medium text-dv-accent hover:text-dv-accent-hover transition-colors">
                    Launch Analysis →
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Anomalies Tab */}
          {tab === 'anomalies' && (
            <div className="space-y-4">
              <div className="p-6 rounded-lg border border-dv-border bg-dv-bg">
                <h3 className="text-lg font-semibold text-dv-text mb-4">Anomaly Detection Results</h3>
                
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-4 rounded-lg bg-dv-bg-secondary">
                    <div className="text-sm text-dv-text-secondary mb-1">Total Anomalies</div>
                    <div className="text-2xl font-bold text-dv-accent">247</div>
                  </div>
                  <div className="p-4 rounded-lg bg-dv-bg-secondary">
                    <div className="text-sm text-dv-text-secondary mb-1">% of Dataset</div>
                    <div className="text-2xl font-bold text-orange-500">2.3%</div>
                  </div>
                  <div className="p-4 rounded-lg bg-dv-bg-secondary">
                    <div className="text-sm text-dv-text-secondary mb-1">Last Scan</div>
                    <div className="text-sm font-semibold text-dv-text">Today 2:30 PM</div>
                  </div>
                </div>

                <button className="w-full px-4 py-2 rounded-lg border border-dv-border bg-dv-bg text-dv-text hover:border-dv-accent transition-colors font-medium">
                  Run Anomaly Detection
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
