import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { contentApi, crewExecutionApi } from '../services/api'
import { CrewProgressTracker } from '../components/crew/CrewProgressTracker'
import { PLATFORMS } from '../components/ui/PlatformBadge'
import { Send, CheckCircle2, XCircle, ExternalLink } from 'lucide-react'

export function PublishPage() {
  const [searchParams] = useSearchParams()
  const preselectedDraft = searchParams.get('draft') || ''

  const [selectedDraft, setSelectedDraft] = useState(preselectedDraft)
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['xiaohongshu'])
  const [scheduleMode, setScheduleMode] = useState<'now' | 'scheduled'>('now')
  const [scheduleTime, setScheduleTime] = useState('')
  const [executionId, setExecutionId] = useState<string | null>(null)
  const [publishResult, setPublishResult] = useState<Record<string, unknown> | null>(null)

  const draftsQuery = useQuery({
    queryKey: ['content-drafts'],
    queryFn: () => contentApi.listDrafts(),
  })

  const drafts = draftsQuery.data?.drafts ?? []

  const togglePlatform = (id: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    )
  }

  const publishMutation = useMutation({
    mutationFn: () =>
      crewExecutionApi.startPublish({
        content_id: selectedDraft,
        target_platforms: selectedPlatforms,
        schedule_time: scheduleMode === 'scheduled' ? scheduleTime : undefined,
      }),
    onSuccess: (data) => {
      setExecutionId(data.execution_id)
      setPublishResult(null)
    },
  })

  const canPublish =
    selectedDraft && selectedPlatforms.length > 0 && !publishMutation.isPending && !executionId

  const records = (publishResult?.publish_records as Array<Record<string, unknown>>) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">内容发布</h1>
        <p className="mt-1 text-sm text-gray-500">选择草稿和目标平台，一键发布到多个平台</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Config */}
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
            {/* Draft selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">选择草稿</label>
              <select
                value={selectedDraft}
                onChange={(e) => setSelectedDraft(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">-- 选择草稿 --</option>
                {drafts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} ({d.platform_name || d.platform})
                  </option>
                ))}
              </select>
            </div>

            {/* Platform selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                目标平台（可多选）
              </label>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => togglePlatform(p.id)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      selectedPlatforms.includes(p.id)
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Schedule */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">发布时间</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setScheduleMode('now')}
                  className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium ${
                    scheduleMode === 'now'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600'
                  }`}
                >
                  立即发布
                </button>
                <button
                  onClick={() => setScheduleMode('scheduled')}
                  className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium ${
                    scheduleMode === 'scheduled'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600'
                  }`}
                >
                  定时发布
                </button>
              </div>
              {scheduleMode === 'scheduled' && (
                <input
                  type="datetime-local"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              )}
            </div>

            {/* Publish button */}
            <button
              onClick={() => publishMutation.mutate()}
              disabled={!canPublish}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              <Send className="h-4 w-4" />
              {publishMutation.isPending ? '启动中...' : '开始发布'}
            </button>

            {publishMutation.isError && (
              <p className="text-xs text-red-500">
                发布失败: {String(publishMutation.error)}
              </p>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="space-y-4">
          {executionId && (
            <CrewProgressTracker
              executionId={executionId}
              onComplete={(r) => {
                setPublishResult(r)
                setExecutionId(null)
              }}
              onError={() => setExecutionId(null)}
            />
          )}

          {publishResult && records.length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
              <h2 className="text-sm font-semibold text-gray-900">发布结果</h2>
              <div className="space-y-2">
                {records.map((rec, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      {rec.status === 'published' ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="text-sm text-gray-700">
                        {String(rec.platform)}
                      </span>
                    </div>
                    {!!rec.published_url && (
                      <a
                        href={String(rec.published_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                      >
                        查看 <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>

              {/* Summary */}
              {!!publishResult.summary && (
                <div className="border-t border-gray-100 pt-2 text-xs text-gray-500">
                  总计 {String((publishResult.summary as Record<string, number>).total ?? 0)} 个平台，
                  成功 {String((publishResult.summary as Record<string, number>).successful ?? 0)}，
                  失败 {String((publishResult.summary as Record<string, number>).failed ?? 0)}
                </div>
              )}
            </div>
          )}

          {!executionId && !publishResult && (
            <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 py-16 text-center">
              <Send className="mb-3 h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-500">选择草稿和平台后点击"开始发布"</p>
              <p className="mt-1 text-xs text-gray-400">支持同时发布到多个平台</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
