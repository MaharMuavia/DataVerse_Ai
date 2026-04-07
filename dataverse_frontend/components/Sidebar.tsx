import { useState } from 'react'
import { ChevronLeft, ChevronRight, Plus, History, Settings, LogOut, Database, BarChart3, Brain, Zap, MessageSquare } from 'lucide-react'
import Link from 'next/link'

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [activeItem, setActiveItem] = useState('chat')

  const mainMenuItems = [
    { id: 'chat', icon: MessageSquare, label: 'New Chat', href: '/' },
    { id: 'datasets', icon: Database, label: 'My Datasets', href: '/datasets' },
    { id: 'analytics', icon: BarChart3, label: 'Analytics', href: '/analytics' },
    { id: 'models', icon: Brain, label: 'ML Models', href: '/models' },
    { id: 'insights', icon: Zap, label: 'Insights', href: '/insights' },
  ]

  const bottomItems = [
    { id: 'history', icon: History, label: 'History', href: '/history' },
    { id: 'settings', icon: Settings, label: 'Settings', href: '/settings' },
  ]

  return (
    <aside className={`bg-dv-bg-secondary border-r border-dv-border transition-all duration-300 flex flex-col h-screen ${
      isCollapsed ? 'w-16' : 'w-64'
    }`}>
      {/* Header */}
      <div className="p-4 border-b border-dv-border">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <h1 className="text-sm font-semibold text-dv-text bg-gradient-to-r from-dv-accent to-purple-600 bg-clip-text text-transparent">
              DataVerse AI
            </h1>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 rounded-lg hover:bg-dv-bg transition-colors text-dv-text-secondary hover:text-dv-text"
            title={isCollapsed ? 'Expand' : 'Collapse'}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-4 border-b border-dv-border">
        <button className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-dv-accent text-white hover:bg-dv-accent-hover transition-colors font-medium text-sm ${
          isCollapsed ? 'justify-center' : ''
        }`}>
          <Plus size={18} />
          {!isCollapsed && 'New Chat'}
        </button>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {mainMenuItems.map((item) => (
          <Link
            key={item.id}
            href={item.href}
          >
            <button
              onClick={() => setActiveItem(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-medium ${
                activeItem === item.id
                  ? 'bg-dv-accent text-white shadow-md'
                  : 'text-dv-text-secondary hover:text-dv-text hover:bg-dv-bg'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <item.icon size={18} />
              {!isCollapsed && <span>{item.label}</span>}
            </button>
          </Link>
        ))}
      </nav>

      {/* Divider */}
      <div className="border-t border-dv-border"></div>

      {/* Bottom Navigation */}
      <nav className="p-3 space-y-1 border-b border-dv-border">
        {bottomItems.map((item) => (
          <Link
            key={item.id}
            href={item.href}
          >
            <button
              onClick={() => setActiveItem(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-medium ${
                activeItem === item.id
                  ? 'bg-dv-bg text-dv-accent'
                  : 'text-dv-text-secondary hover:text-dv-text hover:bg-dv-bg'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <item.icon size={18} />
              {!isCollapsed && <span>{item.label}</span>}
            </button>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3">
        <button className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-dv-text-secondary hover:text-dv-text hover:bg-dv-bg transition-colors text-sm font-medium ${
          isCollapsed ? 'justify-center' : ''
        }`}>
          <LogOut size={18} />
          {!isCollapsed && 'Sign Out'}
        </button>
      </div>
    </aside>
  )
}