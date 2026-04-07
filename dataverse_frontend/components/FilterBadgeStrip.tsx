'use client'

import { Filter, X } from 'lucide-react'
import { ActiveFilter } from '@/types'

interface FilterBadgeStripProps {
  filters: ActiveFilter[]
  onClearAll?: () => void
}

export function FilterBadgeStrip({ filters, onClearAll }: FilterBadgeStripProps) {
  if (!filters.length) {
    return null
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="rounded-full bg-slate-100 p-2 text-slate-600">
            <Filter className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-medium text-slate-900">Active filters</div>
            <div className="text-xs text-slate-500">These conditions shape the current analysis context.</div>
          </div>
        </div>

        {onClearAll && (
          <button
            type="button"
            onClick={onClearAll}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
          >
            <X className="h-3.5 w-3.5" />
            Clear all
          </button>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {filters.map((filter, index) => (
          <div
            key={`${filter.column}-${filter.operator}-${String(filter.value)}-${index}`}
            className="rounded-full bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
          >
            {filter.column} {filter.operator} {String(filter.value)}
          </div>
        ))}
      </div>
    </div>
  )
}
