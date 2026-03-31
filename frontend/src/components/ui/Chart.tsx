import { useEffect, useRef } from 'react'
import ApexCharts, { type ApexAxisChartSeries, type ApexNonAxisChartSeries } from 'apexcharts'

interface ChartProps {
  type: 'area' | 'bar' | 'line' | 'pie' | 'donut'
  height: number
  options: ApexCharts.ApexOptions
  series: ApexAxisChartSeries | ApexNonAxisChartSeries
}

export function Chart({ type, height, options, series }: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ApexCharts | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const merged: ApexCharts.ApexOptions = {
      ...options,
      chart: { ...options.chart, type, height },
      series,
    }

    if (chartRef.current) {
      chartRef.current.updateOptions(merged, true, true)
    } else {
      const chart = new ApexCharts(containerRef.current, merged)
      chart.render()
      chartRef.current = chart
    }

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, height, JSON.stringify(options), JSON.stringify(series)])

  return <div ref={containerRef} />
}
