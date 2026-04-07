import { useState } from 'react'
import { ChevronLeft, ChevronRight, Database, BarChart3, Brain, Zap } from 'lucide-react'

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const menuItems = [
    { icon: Database, label: 'Datasets', active: true },
    { icon: BarChart3, label: 'Analytics' },
    { icon: Brain, label: 'ML Models' },
    { icon: Zap, label: 'XAI Insights' },
  ]

  return (
    <aside className={`bg-dv-surface border-r border-dv-border transition-all duration-200 ${
      isCollapsed ? 'w-16' : 'w-64'
    }`}>
      <div className="p-4 border-b border-dv-border">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center p-2 rounded-lg hover:bg-dv-hover transition-colors"
        >
          {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      <nav className="p-4 space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.label}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              item.active
                ? 'bg-dv-accent text-dv-accent-foreground'
                : 'hover:bg-dv-hover'
            }`}
          >
            <item.icon size={20} />
            {!isCollapsed && <span className="text-sm">{item.label}</span>}
          </button>
        ))}
      </nav>
    </aside>
  )
}