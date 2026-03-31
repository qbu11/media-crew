import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { contentApi, crewExecutionApi } from '../services/api'
import { PlatformBadge } from '../components/ui/PlatformBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { FileText, Plus, Send, Clock, CheckCircle2, Sparkles } from 'lucide-react'

export function ContentPage() {
  const draftsQuery = useQuery({
    queryKey: ['content-drafts'],
    queryFn: () => contentApi.listDrafts(),
  })

  const executionsQuery = useQuery({
    queryKey: ['crew-executions', 'content'],
    queryFn: () => crewExecutionApi.list('content', 5),
  })

  const drafts = draftsQuery.data?.drafts ?? []
  const executions = executionsQuery.data?.data ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">内容中心</h1>
          <p className="mt-1 text-sm text-gray-500">管理内容创作、草稿和发布</p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/content/create"
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            新建创作
          </Link>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <FileText className="h-4 w-4" />
            草稿数
          </div>
          <div className="mt-1 text-2xl font-bold text-gray-900">{drafts.length}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            进行中
          </div>
          <div className="mt-1 text-2xl font-bold text-blue-600">
            {executions.filter((e) => e.status === 'running').length}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <CheckCircle2 className="h-4 w-4" />
            已完成
          </div>
          <div className="mt-1 text-2xl font-bold text-green-600">
            {executions.filter((e) => e.status === 'completed').length}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Send className="h-4 w-4" />
            已发布
          </div>
          <div className="mt-1 text-2xl font-bold text-purple-600">
            {drafts.filter((d) => d.status === 'published').length}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent drafts */}
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-gray-900">最近草稿</h2>
            <Link to="/content/drafts" className="text-xs text-blue-600 hover:underline">
              查看全部
            </Link>
          </div>
          {drafts.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={<FileText className="h-10 w-10" />} title="暂无草稿" description="创作内容后将显示在这里" />
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {drafts.slice(0, 5).map((draft) => (
                <div key={draft.id} className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">{draft.title}</p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400">
                      <PlatformBadge platform={draft.platform} size="sm" />
                      <span>{draft.word_count} 字</span>
                      <span>{new Date(draft.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      draft.status === 'published'
                        ? 'bg-green-50 text-green-700'
                        : draft.status === 'draft'
                          ? 'bg-gray-50 text-gray-600'
                          : 'bg-yellow-50 text-yellow-700'
                    }`}
                  >
                    {draft.status === 'published' ? '已发布' : draft.status === 'draft' ? '草稿' : draft.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent executions */}
        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-gray-900">最近执行</h2>
          </div>
          {executions.length === 0 ? (
            <div className="p-6">
              <EmptyState icon={<Sparkles className="h-10 w-10" />} title="暂无执行记录" description="开始创作后将显示进度" />
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {executions.map((exec) => (
                <div key={exec.id} className="flex items-center justify-between px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">
                      {(exec.inputs?.topic as string) || exec.id}
                    </p>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400">
                      <span>{exec.current_step}</span>
                      <span>{exec.progress}%</span>
                    </div>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      exec.status === 'completed'
                        ? 'bg-green-50 text-green-700'
                        : exec.status === 'running'
                          ? 'bg-blue-50 text-blue-700'
                          : exec.status === 'failed'
                            ? 'bg-red-50 text-red-700'
                            : 'bg-gray-50 text-gray-600'
                    }`}
                  >
                    {exec.status === 'completed' ? '完成' : exec.status === 'running' ? '运行中' : exec.status === 'failed' ? '失败' : '等待'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
