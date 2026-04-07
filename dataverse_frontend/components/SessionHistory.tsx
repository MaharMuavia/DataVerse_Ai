'use client'

import { useEffect, useState } from 'react'
import { Clock, Trash2, SharedIcon, FileJson } from 'lucide-react'

interface SessionData {
  id: string
  name: string
  dataset: string
  date: string
  messages: number
}

export function SessionHistory() {
  const [sessions, setSessions] = useState<SessionData[]>([])

  useEffect(() => {
    // In a real app, fetch from backend
    setSessions([
      {
        id: '1',
        name: 'Retail Sales Analysis',
        dataset: 'sales_data_2024.csv',
        date: 'Today at 2:30 PM',
        messages: 12,
      },
      {
        id: '2',
        name: 'Customer Segmentation',
        dataset: 'customer_data.csv',
        date: 'Yesterday',
        messages: 8,
      },
      {
        id: '3',
        name: 'Inventory Trends',
        dataset: 'inventory.csv',
        date: '2 days ago',
        messages: 15,
      },
    ])
  }, [])

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-dv-text flex items-center gap-2">
          <Clock size={16} />
          Recent Sessions
        </h2>
      </div>

      <div className="space-y-2">
        {sessions.map(session => (
          <div
            key={session.id}
            className="group p-3 rounded-lg hover:bg-dv-bg-secondary transition-colors cursor-pointer border border-transparent hover:border-dv-border"
          >
            <div className="flex items-start justify-between mb-1">
              <h3 className="text-sm font-medium text-dv-text group-hover:text-dv-accent transition-colors">
                {session.name}
              </h3>
              <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-1 hover:bg-dv-bg rounded text-dv-text-secondary hover:text-dv-text">
                  <SharedIcon size={14} />
                </button>
                <button className="p-1 hover:bg-dv-bg rounded text-dv-text-secondary hover:text-dv-text">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            <p className="text-xs text-dv-text-secondary mb-2">{session.dataset}</p>
            <div className="flex items-center justify-between text-xs text-dv-text-secondary">
              <span>{session.date}</span>
              <span className="px-2 py-0.5 bg-dv-bg rounded text-dv-text-secondary">
                {session.messages} messages
              </span>
            </div>
          </div>
        ))}
      </div>

      <button className="w-full mt-4 py-2 text-sm font-medium text-dv-accent hover:bg-dv-accent/10 rounded-lg transition-colors">
        View All Sessions
      </button>
    </div>
  )
}
