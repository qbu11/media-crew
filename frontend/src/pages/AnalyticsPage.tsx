import { useQuery } from '@tanstack/react-query'
import { analyticsApi } from '../services/api'
import { formatNumber } from '../lib/utils'
import { Activity, Eye, Heart, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react'
import { Chart } from '../components/ui/Chart'

type OpsData = { total_executions: number; completed: number; failed: number; running: number; success_rate: number; by_type: Record<string, number> }
type TimelineItem = { date: string; total: number; completed: number; failed: number }
type OverviewData = { total_posts: number; total_views: number; total_engagement: number; followers_gained: number }
type PlatformItem = { platform: string; name: string; posts: number; views: number; likes: number; comments: number; shares: number }

export function AnalyticsPage() {
  const opsQuery = useQuery({
    queryKey: ['analytics-operations'],
    queryFn: () => analyticsApi.operations(),
    retry: false,
  })

  const timelineQuery = useQuery({
    queryKey: ['analytics-timeline'],
    queryFn: () => analyticsApi.timeline(),
    retry: false,
  })

  const overviewQuery = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: () => analyticsApi.overview(),
    retry: false,
  })

  const platformsQuery = useQuery({
    queryKey: ['analytics-platforms'],
    queryFn: () => analyticsApi.platforms(),
    retry: false,
  })

  const ops = opsQuery.data as OpsData | undefined
  const timeline = (timelineQuery.data as { timeline: TimelineItem[] } | undefined)?.timeline ?? []
  const overview = overviewQuery.data as OverviewData | undefined
  const platforms = (platformsQuery.data as { platforms: PlatformItem[] } | undefined)?.platforms ?? []

  // 检查是否所有 API 都失败了（后端未连接）
  const isBackendDisconnected =
    opsQuery.isError && timelineQuery.isError && overviewQuery.isError && platformsQuery.isError

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">数据分析</h1>
        <p className="mt-1 text-sm text-gray-500">运维指标和内容平台数据</p>
      </div>

      {/* Backend Disconnected Notice */}
      {isBackendDisconnected && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-amber-900">后端服务未连接</h3>
              <p className="mt-1 text-sm text-amber-700">
                无法连接到后端 API 服务。请确保后端服务正在运行，或检查网络连接。
              </p>
              <button
                onClick={() => {
                  opsQuery.refetch()
                  timelineQuery.refetch()
                  overviewQuery.refetch()
                  platformsQuery.refetch()
                }}
                className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
              >
                <RefreshCw className="h-3 w-3" />
                重试连接
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Operations Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={<Activity className="h-4 w-4 text-blue-500" />}
          label="总执行次数"
          value={ops?.total_executions ?? 0}
        />
        <StatCard
          icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}
          label="成功率"
          value={ops ? `${(ops.success_rate * 100).toFixed(0)}%` : '0%'}
        />
        <StatCard
          icon={<Eye className="h-4 w-4 text-purple-500" />}
          label="总浏览量"
          value={formatNumber(overview?.total_views ?? 0)}
        />
        <StatCard
          icon={<Heart className="h-4 w-4 text-red-500" />}
          label="总互动量"
          value={formatNumber(overview?.total_engagement ?? 0)}
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Execution Timeline */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">执行趋势（7天）</h3>
          {timelineQuery.isLoading ? (
            <div className="flex h-60 items-center justify-center text-sm text-gray-400">
              加载中...
            </div>
          ) : timeline.length > 0 ? (
            <Chart
              type="area"
              height={240}
              options={{
                chart: { toolbar: { show: false }, fontFamily: 'inherit' },
                xaxis: {
                  categories: timeline.map((t) => t.date.slice(5)),
                  labels: { style: { fontSize: '11px', colors: '#9ca3af' } },
                },
                yaxis: { labels: { style: { fontSize: '11px', colors: '#9ca3af' } } },
                stroke: { curve: 'smooth', width: 2 },
                colors: ['#3b82f6', '#22c55e', '#ef4444'],
                fill: { type: 'gradient', gradient: { opacityFrom: 0.3, opacityTo: 0.05 } },
                legend: { position: 'top', fontSize: '12px' },
                grid: { borderColor: '#f3f4f6' },
                tooltip: { theme: 'light' },
              }}
              series={[
                { name: '总计', data: timeline.map((t) => t.total) },
                { name: '成功', data: timeline.map((t) => t.completed) },
                { name: '失败', data: timeline.map((t) => t.failed) },
              ]}
            />
          ) : (
            <div className="flex h-60 flex-col items-center justify-center gap-3 text-sm text-gray-400">
              <Activity className="h-10 w-10 text-gray-300" />
              <span>暂无执行数据</span>
              {timelineQuery.isError && (
                <span className="text-xs text-amber-600">数据加载失败</span>
              )}
            </div>
          )}
        </div>

        {/* Platform Stats */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">平台数据对比</h3>
          {platforms.length > 0 ? (
            <Chart
              type="bar"
              height={240}
              options={{
                chart: { toolbar: { show: false }, fontFamily: 'inherit' },
                xaxis: {
                  categories: platforms.map((p) => p.name),
                  labels: { style: { fontSize: '11px', colors: '#9ca3af' } },
                },
                yaxis: { labels: { style: { fontSize: '11px', colors: '#9ca3af' } } },
                colors: ['#3b82f6', '#f59e0b', '#8b5cf6'],
                plotOptions: { bar: { borderRadius: 4, columnWidth: '60%' } },
                legend: { position: 'top', fontSize: '12px' },
                grid: { borderColor: '#f3f4f6' },
                tooltip: { theme: 'light' },
              }}
              series={[
                { name: '浏览', data: platforms.map((p) => p.views) },
                { name: '点赞', data: platforms.map((p) => p.likes) },
                { name: '评论', data: platforms.map((p) => p.comments) },
              ]}
            />
          ) : (
            <div className="flex h-60 items-center justify-center text-sm text-gray-400">
              暂无平台数据
            </div>
          )}
        </div>
      </div>

      {/* Platform Detail Table */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">平台详细数据</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs font-medium text-gray-500">
                <th className="pb-3 pr-4">平台</th>
                <th className="pb-3 pr-4 text-right">发布数</th>
                <th className="pb-3 pr-4 text-right">浏览量</th>
                <th className="pb-3 pr-4 text-right">点赞</th>
                <th className="pb-3 pr-4 text-right">评论</th>
                <th className="pb-3 text-right">分享</th>
              </tr>
            </thead>
            <tbody>
              {platforms.map((p) => (
                <tr key={p.platform} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-3 pr-4 font-medium text-gray-900">{p.name}</td>
                  <td className="py-3 pr-4 text-right text-gray-700">{p.posts}</td>
                  <td className="py-3 pr-4 text-right text-gray-700">{formatNumber(p.views)}</td>
                  <td className="py-3 pr-4 text-right text-gray-700">{formatNumber(p.likes)}</td>
                  <td className="py-3 pr-4 text-right text-gray-700">{p.comments}</td>
                  <td className="py-3 text-right text-gray-700">{p.shares}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Execution Type Breakdown */}
      {ops && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">执行状态分布</h3>
          <div className="mt-4 flex gap-6">
            {[
              { label: '已完成', count: ops.completed, color: 'bg-green-500' },
              { label: '运行中', count: ops.running, color: 'bg-blue-500' },
              { label: '失败', count: ops.failed, color: 'bg-red-500' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <span className={`h-3 w-3 rounded-full ${item.color}`} />
                <span className="text-sm text-gray-600">{item.label}</span>
                <span className="text-sm font-semibold text-gray-900">{item.count}</span>
              </div>
            ))}
          </div>
          {ops.total_executions > 0 && (
            <div className="mt-3 flex h-5 overflow-hidden rounded-full bg-gray-100">
              <div className="bg-green-500" style={{ width: `${(ops.completed / ops.total_executions) * 100}%` }} />
              <div className="bg-blue-500" style={{ width: `${(ops.running / ops.total_executions) * 100}%` }} />
              <div className="bg-red-500" style={{ width: `${(ops.failed / ops.total_executions) * 100}%` }} />
            </div>
          )}
          <div className="mt-3 flex gap-4 text-xs text-gray-500">
            <span>内容创作: {ops.by_type.content ?? 0} 次</span>
            <span>内容发布: {ops.by_type.publish ?? 0} 次</span>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-2 text-sm text-gray-500">
        {icon}
        {label}
      </div>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
    </div>
  )
}
