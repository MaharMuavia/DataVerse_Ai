import { Settings, User, Bell, Search } from 'lucide-react'

export function TopBar() {
  return (
    <header className="bg-dv-bg border-b border-dv-border px-6 py-3">
      <div className="flex items-center justify-between max-w-full">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-dv-accent to-purple-600 flex items-center justify-center text-white font-bold text-sm">
              D
            </div>
            <span className="font-semibold text-dv-text">DataVerse AI</span>
          </div>
          <div className="hidden md:flex items-center text-xs text-dv-text-secondary bg-dv-bg-secondary px-3 py-1.5 rounded-lg border border-dv-border">
            <span>✨ AI-Powered Analytics</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Status indicator */}
          <div className="flex items-center gap-2 text-xs text-dv-text-secondary">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>Connected</span>
          </div>

          {/* Notification */}
          <button className="p-2 rounded-lg hover:bg-dv-bg-secondary transition-colors text-dv-text-secondary hover:text-dv-text relative">
            <Bell size={18} />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-red-500" />
          </button>

          {/* Settings */}
          <button className="p-2 rounded-lg hover:bg-dv-bg-secondary transition-colors text-dv-text-secondary hover:text-dv-text" title="Settings">
            <Settings size={18} />
          </button>

          {/* User Profile */}
          <button className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-dv-bg-secondary transition-colors border border-dv-border">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-dv-accent to-purple-600 flex items-center justify-center text-white text-xs font-semibold">
              U
            </div>
            <span className="text-xs font-medium text-dv-text hidden md:block">User</span>
          </button>
        </div>
      </div>
    </header>
  )
}