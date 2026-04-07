import { Settings, User } from 'lucide-react'

export function TopBar() {
  return (
    <header className="bg-dv-surface border-b border-dv-border px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-dv-text">DataVerse AI</h1>
          <div className="text-sm text-dv-text-secondary">
            Conversational Data Analysis
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="p-2 rounded-lg hover:bg-dv-hover transition-colors">
            <Settings size={20} />
          </button>
          <button className="p-2 rounded-lg hover:bg-dv-hover transition-colors">
            <User size={20} />
          </button>
        </div>
      </div>
    </header>
  )
}