'use client'

import { BarChart3, Sparkles, Database, TrendingUp } from 'lucide-react'

interface QuickActionProps {
  onAction: (action: string) => void
}

export function QuickActions({ onAction }: QuickActionProps) {
  const actions = [
    {
      id: 'eda',
      label: 'Exploratory Analysis',
      description: 'Auto-generate EDA report',
      icon: BarChart3,
      color: 'from-blue-500 to-cyan-500',
    },
    {
      id: 'insights',
      label: 'AI Insights',
      description: 'Generate smart insights',
      icon: Sparkles,
      color: 'from-purple-500 to-pink-500',
    },
    {
      id: 'predict',
      label: 'Predictions',
      description: 'Build predictive models',
      icon: TrendingUp,
      color: 'from-orange-500 to-red-500',
    },
    {
      id: 'profile',
      label: 'Data Profile',
      description: 'Quick data overview',
      icon: Database,
      color: 'from-green-500 to-emerald-500',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 p-4">
      {actions.map(action => {
        const Icon = action.icon
        return (
          <button
            key={action.id}
            onClick={() => onAction(action.id)}
            className={`group relative overflow-hidden rounded-lg p-4 text-left transition-all duration-300 hover:shadow-lg`}
          >
            {/* Background gradient */}
            <div className={`absolute inset-0 -z-10 bg-gradient-to-br ${action.color} opacity-0 group-hover:opacity-10 transition-opacity`} />
            
            {/* Content */}
            <div className="flex items-start justify-between mb-2">
              <Icon size={20} className={`bg-gradient-to-br ${action.color} bg-clip-text text-transparent`} />
              <span className="text-xs px-2 py-1 bg-dv-bg-secondary rounded-full text-dv-text-secondary group-hover:bg-dv-accent group-hover:text-white transition-colors">
                Quick
              </span>
            </div>
            <h3 className="font-semibold text-sm text-dv-text mb-1">{action.label}</h3>
            <p className="text-xs text-dv-text-secondary">{action.description}</p>
          </button>
        )
      })}
    </div>
  )
}
