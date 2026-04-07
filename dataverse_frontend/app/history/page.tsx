'use client'

import { useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { Calendar, MessageSquare, BarChart3, Trash2, Download, Share2, ChevronRight } from 'lucide-react'

interface SessionHistoryItem {
  id: string
  name: string
  dataset: string
  date: string
  timestamp: number
  messages: number
  status: 'active' | 'completed' | 'archived'
  size: string
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([
    {
      id: '1',
      name: 'Q4 Sales Analysis',
      dataset: 'sales_data_q4_2024.csv',
      date: 'Today at 2:30 PM',
      timestamp: Date.now(),
      messages: 15,
      status: 'active',
      size: '2.5 MB',
    },
    {
      id: '2',
      name: 'Customer Segmentation',
      dataset: 'customers_2024.csv',
      date: 'Yesterday',
      timestamp: Date.now() - 86400000,
      messages: 22,
      status: 'completed',
      size: '5.1 MB',
    },
    {
      id: '3',
      name: 'Inventory Trends',
      dataset: 'inventory.csv',
      date: '3 days ago',
      timestamp: Date.now() - 3 * 86400000,
      messages: 18,
      status: 'completed',
      size: '3.2 MB',
    },
    {
      id: '4',
      name: 'Marketing Campaign ROI',
      dataset: 'campaigns_2024.csv',
      date: 'Week ago',
      timestamp: Date.now() - 7 * 86400000,
      messages: 25,
      status: 'archived',
      size: '4.8 MB',
    },
  ])

  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'archived'>('all')
  const [sortBy, setSortBy] = useState<'recent' | 'name' | 'size'>('recent')

  const filteredSessions = filter === 'all'
    ? sessions
    : sessions.filter(s => s.status === filter)

  const sortedSessions = [...filteredSessions].sort((a, b) => {
    switch (sortBy) {
      case 'recent':
        return b.timestamp - a.timestamp
      case 'name':
        return a.name.localeCompare(b.name)
      case 'size':
        return parseInt(b.size) - parseInt(a.size)
      default:
        return 0
    }
  })

  const getStatusBadge = (status: string) => {
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      active: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300', label: 'Active' },
      completed: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', label: 'Completed' },
      archived: { bg: 'bg-gray-100 dark:bg-gray-900/30', text: 'text-gray-700 dark:text-gray-300', label: 'Archived' },
    }
    const badge = badges[status] || badges.completed
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    )
  }

  return (
    <AppShell>
      <div className="p-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-dv-text mb-2">Session History</h1>
            <p className="text-dv-text-secondary">View and manage your analysis sessions</p>
          </div>

          {/* Controls */}
          <div className="flex flex-col md:flex-row gap-4 mb-8">
            <div className="flex gap-2">
              {['all', 'active', 'completed', 'archived'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f as any)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors text-sm ${
                    filter === f
                      ? 'bg-dv-accent text-white'
                      : 'bg-dv-bg border border-dv-border text-dv-text hover:border-dv-accent'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>

            <div className="md:ml-auto">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-4 py-2 rounded-lg border border-dv-border bg-dv-bg text-dv-text font-medium focus:border-dv-accent focus:outline-none"
              >
                <option value="recent">Most Recent</option>
                <option value="name">Name</option>
                <option value="size">Size</option>
              </select>
            </div>
          </div>

          {/* Sessions Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sortedSessions.length > 0 ? (
              sortedSessions.map(session => (
                <div
                  key={session.id}
                  className="group p-6 rounded-lg border border-dv-border bg-dv-bg hover:border-dv-accent hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-dv-text group-hover:text-dv-accent transition-colors">
                        {session.name}
                      </h3>
                      <p className="text-sm text-dv-text-secondary">{session.dataset}</p>
                    </div>
                    {getStatusBadge(session.status)}
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4 p-3 rounded-lg bg-dv-bg-secondary">
                    <div className="flex items-center gap-2 text-sm text-dv-text-secondary">
                      <Calendar size={16} />
                      {session.date}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-dv-text-secondary">
                      <MessageSquare size={16} />
                      {session.messages} messages
                    </div>
                    <div className="text-sm text-dv-text-secondary">
                      {session.size}
                    </div>
                  </div>

                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-dv-text hover:border-dv-accent transition-colors text-sm font-medium">
                      <BarChart3 size={16} />
                      Open
                    </button>
                    <button className="p-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-dv-text hover:border-dv-accent transition-colors">
                      <Download size={16} />
                    </button>
                    <button className="p-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-dv-text hover:border-dv-accent transition-colors">
                      <Share2 size={16} />
                    </button>
                    <button className="p-2 rounded-lg border border-dv-border text-dv-text-secondary hover:text-red-500 hover:border-red-300 transition-colors">
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full text-center py-12">
                <Calendar size={48} className="mx-auto mb-4 text-dv-text-secondary opacity-50" />
                <p className="text-dv-text-secondary mb-2">No sessions found</p>
                <p className="text-sm text-dv-text-secondary">Upload a dataset to start a new analysis session</p>
              </div>
            )}
          </div>

          {/* Storage Info */}
          <div className="mt-12 p-6 rounded-lg border border-dv-border bg-dv-bg-secondary">
            <h3 className="font-semibold text-dv-text mb-4">Storage Usage</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="w-full bg-dv-border rounded-full h-2 overflow-hidden">
                  <div className="bg-gradient-to-r from-dv-accent to-purple-600 h-full" style={{ width: '35%' }}></div>
                </div>
              </div>
              <div className="text-sm text-dv-text-secondary whitespace-nowrap">
                <strong className="text-dv-text">17.6 GB</strong> of 50 GB used
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
