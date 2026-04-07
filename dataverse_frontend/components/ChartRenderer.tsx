'use client'

import { useEffect, useRef } from 'react'
import Plotly, { PlotlyHTMLElement } from 'plotly.js'

interface ChartRendererProps {
  chartSpec: any
  className?: string
}

export function ChartRenderer({ chartSpec, className = '' }: ChartRendererProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const plotRef = useRef<PlotlyHTMLElement | null>(null)

  useEffect(() => {
    if (!chartRef.current || !chartSpec) return

    try {
      const spec = typeof chartSpec === 'string' ? JSON.parse(chartSpec) : chartSpec

      Plotly.newPlot(chartRef.current, spec.data || [], spec.layout || {}, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
      }).then((plot: PlotlyHTMLElement) => {
        plotRef.current = plot
      })
    } catch (error) {
      console.error('Failed to render chart:', error)
    }

    return () => {
      if (plotRef.current) {
        Plotly.purge(plotRef.current)
      }
    }
  }, [chartSpec])

  return (
    <div
      ref={chartRef}
      className={`w-full h-96 ${className}`}
    />
  )
}
