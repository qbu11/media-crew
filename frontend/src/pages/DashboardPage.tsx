import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAppStore } from '../stores/app'
import { analyticsApi, crewExecutionApi } from '../services/api'
import { formatNumber, formatTime } from '../lib/utils'
import {
  PenTool, Send, Search, Image, Activity, Eye, Heart,
  CheckCircle2, XCircle, Clock, ArrowRight, Sparkles,
} from 'lucide-react'

const quickActions = [
  { to: '/content/create', icon: PenTool, label: '内容创作', desc: 'AI 驱动创作流水线', color: 'bg-blue-50 text-blue-600' },
  { to: '/publish', icon: Send, label: '内容发布', desc: '一键多平台发布', color: 'bg-green-50 text-green-600' },
  { to: '/search', icon: Search, label: '热点搜索', desc: '全平台热点追踪', color: 'bg-purple-50 text-purple-600' },
  { to: '/images', icon: Image, label: '图片生成', desc: '平台配图生成', color: 'bg-orange-50 text-orange-600' },
]

export function DashboardPage() {
  const { logs, wsConnected } = useAppStore()

  const opsQuery = useQuery({
    queryKey: ['analytics-operations'],
    queryFn: () => analyticsApi.operations(),
  })

  const overviewQuery = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: () => analyticsApi.overview(),
  })

  const recentQuery = useQuery({
    queryKey: ['recent-executions'],
    queryFn: () => crewExecutionApi.list(undefined, 5),
  })

  const ops = opsQuery.data
  const overview = overviewQuery.data
  const recentExecs = recentQuery.data?.data ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">系统概览</h1>
        <p className="mt-1 text-sm text-gray-500">
          Crew Media Ops 运营中心
          {wsConnected && <span className="ml-2 text-green-500">● 实时连接</span>}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashStatCard icon={<Activity className="h-4 w-4 text-blue-500" />} label="总执行次数" value={ops?.total_executions ?? 0} />
        <DashStatCard icon={<CheckCircle2 className="h-4 w-4 text-green-500" />} label="成功率" value={ops ? `${(ops.success_rate * 100).toFixed(0)}%` : '-'} />
        <DashStatCard icon={<Eye className="h-4 w-4 text-purple-500" />} label="总浏览量" value={formatNumber(overview?.total_views ?? 0)} />
        <DashStatCard icon={<Heart className="h-4 w-4 text-red-500" />} label="总互动量" value={formatNumber(overview?.total_engagement ?? 0)} />
      </div>

      {/* Quick Actions + Recent Executions */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Quick Actions */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">快捷操作</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {quickActions.map((action) => (
              <Link
                key={action.to}
                to={action.to}
                className="group flex flex-col rounded-lg border border-gray-100 p-4 transition-all hover:border-blue-200 hover:shadow-sm"
              >
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${action.color}`}>
                  <action.icon className="h-4 w-4" />
                </div>
                <p className="mt-3 text-sm font-medium text-gray-900">{action.label}</p>
                <p className="mt-0.5 text-xs text-gray-500">{action.desc}</p>
                <ArrowRight className="mt-2 h-3.5 w-3.5 text-gray-300 transition-colors group-hover:text-blue-500" />
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Executions */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">最近执行</h3>
            <Link to="/content" className="text-xs text-blue-600 hover:underline">查看全部</Link>
          </div>
          <div className="mt-4 space-y-3">
            {recentExecs.length === 0 ? (
              <div className="flex flex-col items-center py-8 text-center">
                <Sparkles className="h-8 w-8 text-gray-200" />
                <p className="mt-2 text-sm text-gray-400">暂无执行记录</p>
                <Link to="/content/create" className="mt-2 text-xs text-blue-600 hover:underline">开始创作</Link>
              </div>
            ) : (
              recentExecs.map((exec) => (
                <div key={exec.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2.5">
                  <div className="flex items-center gap-3">
                    {exec.status === 'completed' ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : exec.status === 'failed' ? (
                      <XCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Clock className="h-4 w-4 text-blue-500 animate-pulse" />
                    )}
                    <div>
                      <p className="text-sm text-gray-900">
                        {exec.crew_type === 'content' ? '内容创作' : '内容发布'}
                      </p>
                      <p className="text-xs text-gray-400">{exec.current_step}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-medium ${
                      exec.status === 'completed' ? 'text-green-600' :
                      exec.status === 'failed' ? 'text-red-600' : 'text-blue-600'
                    }`}>
                      {exec.status === 'completed' ? '完成' : exec.status === 'failed' ? '失败' : `${exec.progress}%`}
                    </span>
                    <p className="text-xs text-gray-400">{formatTime(exec.started_at)}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Activity Feed */}
      {logs.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">实时活动</h3>
          <div className="mt-4 max-h-48 space-y-1.5 overflow-y-auto">
            {logs.slice(0, 8).map((log) => (
              <div key={log.id} className="flex items-start gap-2 rounded px-2 py-1 text-sm hover:bg-gray-50">
                <span className={`mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                  log.level === 'error' ? 'bg-red-500' :
                  log.level === 'warning' ? 'bg-yellow-500' :
                  log.level === 'success' ? 'bg-green-500' : 'bg-blue-400'
                }`} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-gray-600">
                    {log.agent_name && <span className="font-medium text-gray-800">{log.agent_name}: </span>}
                    {log.message}
                  </p>
                </div>
                <span className="flex-shrink-0 text-xs text-gray-400">{formatTime(log.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function DashStatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-2 text-sm text-gray-500">{icon}{label}</div>
      <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
    </div>
  )
}
