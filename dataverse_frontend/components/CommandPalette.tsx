'use client'

import { useState, useEffect, useRef } from 'react'
import { Search, Settings, BarChart3, Database, Upload, Share2, Download, Trash2, ChevronRight, type LucideIcon } from 'lucide-react'

interface Command {
  id: string
  label: string
  description: string
  icon: LucideIcon
  action: () => void
  category: string
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [search, setSearch] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const searchRef = useRef<HTMLInputElement>(null)

  const commands: Command[] = [
    {
      id: 'upload',
      label: 'Upload Dataset',
      description: 'Upload a new CSV file for analysis',
      icon: Upload,
      action: () => {
        onClose()
        // Trigger upload
      },
      category: 'Dataset',
    },
    {
      id: 'analyze',
      label: 'Analyze Data',
      description: 'Start a new analysis session',
      icon: BarChart3,
      action: () => {
        onClose()
      },
      category: 'Analysis',
    },
    {
      id: 'export',
      label: 'Export Results',
      description: 'Export analysis as PDF, Excel, or JSON',
      icon: Download,
      action: () => {
        onClose()
      },
      category: 'Export',
    },
    {
      id: 'share',
      label: 'Share Session',
      description: 'Share your analysis with others',
      icon: Share2,
      action: () => {
        onClose()
      },
      category: 'Collaboration',
    },
    {
      id: 'settings',
      label: 'Settings',
      description: 'Configure preferences and options',
      icon: Settings,
      action: () => {
        onClose()
      },
      category: 'System',
    },
  ]

  const filteredCommands = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(search.toLowerCase()) ||
    cmd.description.toLowerCase().includes(search.toLowerCase())
  )

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => searchRef.current?.focus(), 100)
      setSelectedIndex(0)
    }
  }, [isOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      switch (e.key) {
        case 'Escape':
          onClose()
          break
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(prev => (prev + 1) % filteredCommands.length)
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(prev => (prev - 1 + filteredCommands.length) % filteredCommands.length)
          break
        case 'Enter':
          e.preventDefault()
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action()
          }
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, filteredCommands])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Command Palette */}
      <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-xl">
        <div className="bg-dv-bg rounded-lg shadow-2xl border border-dv-border overflow-hidden">
          {/* Search Input */}
          <div className="border-b border-dv-border p-4">
            <div className="flex items-center gap-3">
              <Search size={20} className="text-dv-text-secondary" />
              <input
                ref={searchRef}
                type="text"
                placeholder="Search commands..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setSelectedIndex(0)
                }}
                className="flex-1 bg-transparent text-dv-text placeholder-dv-text-secondary focus:outline-none text-lg"
              />
            </div>
          </div>

          {/* Commands List */}
          <div className="max-h-96 overflow-y-auto">
            {filteredCommands.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-dv-text-secondary">No commands found</p>
              </div>
            ) : (
              <div className="divide-y divide-dv-border">
                {filteredCommands.map((cmd, idx) => {
                  const Icon = cmd.icon
                  return (
                    <button
                      key={cmd.id}
                      onClick={() => {
                        cmd.action()
                      }}
                      className={`w-full px-4 py-3 flex items-center gap-3 transition-colors ${
                        idx === selectedIndex
                          ? 'bg-dv-accent/10 border-l-2 border-dv-accent'
                          : 'hover:bg-dv-bg-secondary'
                      }`}
                    >
                      <Icon size={18} className="text-dv-text-secondary flex-shrink-0" />
                      <div className="flex-1 text-left">
                        <p className="text-sm font-medium text-dv-text">{cmd.label}</p>
                        <p className="text-xs text-dv-text-secondary">{cmd.description}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-1 bg-dv-bg-secondary rounded text-dv-text-secondary">
                          {cmd.category}
                        </span>
                        <ChevronRight size={16} className="text-dv-text-secondary" />
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-dv-border p-3 bg-dv-bg-secondary flex items-center justify-between text-xs text-dv-text-secondary">
            <div className="flex gap-2">
              <kbd className="px-2 py-1 bg-dv-bg rounded border border-dv-border">↑↓</kbd>
              <span>to navigate</span>
              <kbd className="px-2 py-1 bg-dv-bg rounded border border-dv-border">Enter</kbd>
              <span>to select</span>
              <kbd className="px-2 py-1 bg-dv-bg rounded border border-dv-border">Esc</kbd>
              <span>to close</span>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
