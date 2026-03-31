import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contentApi, reviewApi } from '../services/api'
import { PlatformBadge } from '../components/ui/PlatformBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { FileText, Trash2, Send, ClipboardCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

export function ContentDraftsPage() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['content-drafts'],
    queryFn: () => contentApi.listDrafts(),
  })

  const { data: reviewData } = useQuery({
    queryKey: ['review-drafts'],
    queryFn: () => reviewApi.listDrafts(),
    retry: false,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => contentApi.deleteDraft(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['content-drafts'] }),
  })

  const drafts = data?.drafts ?? []
  const reviewDrafts = reviewData?.drafts ?? []

  const STATUS_LABEL: Record<string, { text: string; color: string }> = {
    draft: { text: '草稿', color: 'bg-gray-50 text-gray-600' },
    in_review: { text: '审核中', color: 'bg-blue-50 text-blue-700' },
    changes_requested: { text: '需修改', color: 'bg-amber-50 text-amber-700' },
    revising: { text: 'AI 改写中', color: 'bg-purple-50 text-purple-700' },
    approved: { text: '已通过', color: 'bg-green-50 text-green-700' },
    rejected: { text: '已拒绝', color: 'bg-red-50 text-red-700' },
    published: { text: '已发布', color: 'bg-green-50 text-green-700' },
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">内容审核</h1>
          <p className="mt-1 text-sm text-gray-500">审核、评论和管理内容草稿</p>
        </div>
        <Link
          to="/content/create"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          新建创作
        </Link>
      </div>

      {/* Review drafts section */}
      {reviewDrafts.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-gray-700">待审核内容</h2>
          <div className="space-y-3">
            {reviewDrafts.map((draft) => {
              const st = STATUS_LABEL[draft.status] || STATUS_LABEL.draft
              return (
                <div
                  key={draft.id}
                  className="rounded-lg border border-gray-200 bg-white p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-semibold text-gray-900">{draft.title}</h3>
                      <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                        <PlatformBadge platform={draft.platform} size="sm" />
                        <span>v{draft.version}</span>
                        <span className={`rounded-full px-2 py-0.5 font-medium ${st.color}`}>
                          {st.text}
                        </span>
                        {draft.review_score && (
                          <span className={`font-medium ${
                            draft.review_score.overall >= 80 ? 'text-green-600'
                              : draft.review_score.overall >= 60 ? 'text-amber-600'
                              : 'text-red-600'
                          }`}>
                            综合 {draft.review_score.overall}
                          </span>
                        )}
                        {draft.tags.map((tag) => (
                          <span key={tag} className="rounded-full bg-blue-50 px-1.5 py-0.5 text-blue-600">#{tag}</span>
                        ))}
                      </div>
                    </div>
                    <div className="ml-4 flex gap-1">
                      <Link
                        to={`/content/${draft.id}/review`}
                        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                      >
                        <ClipboardCheck className="h-3.5 w-3.5" />
                        审核
                      </Link>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Content drafts section */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">创作草稿</h2>
        {isLoading ? (
          <div className="text-center text-sm text-gray-500 py-12">加载中...</div>
        ) : drafts.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-10 w-10" />}
            title="暂无草稿"
            description="开始创作内容，草稿将显示在这里"
          />
        ) : (
          <div className="space-y-3">
            {drafts.map((draft) => (
              <div
                key={draft.id}
                className="rounded-lg border border-gray-200 bg-white p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-gray-900">{draft.title}</h3>
                    <p className="mt-1 line-clamp-2 text-xs text-gray-500">{draft.body}</p>
                    <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                      <PlatformBadge platform={draft.platform} size="sm" />
                      <span>{draft.word_count} 字</span>
                      <span>{new Date(draft.created_at).toLocaleString()}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 font-medium ${
                          draft.status === 'published'
                            ? 'bg-green-50 text-green-700'
                            : 'bg-gray-50 text-gray-600'
                        }`}
                      >
                        {draft.status === 'published' ? '已发布' : '草稿'}
                      </span>
                    </div>
                  </div>
                  <div className="ml-4 flex gap-1">
                    <Link
                      to={`/publish?draft=${draft.id}`}
                      className="rounded-lg p-2 text-gray-400 hover:bg-blue-50 hover:text-blue-600"
                      title="发布"
                    >
                      <Send className="h-4 w-4" />
                    </Link>
                    <button
                      onClick={() => {
                        if (confirm('确定删除此草稿？')) deleteMutation.mutate(draft.id)
                      }}
                      className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
                      title="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
