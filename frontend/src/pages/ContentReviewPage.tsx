import { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { reviewApi } from '../services/api'
import { ReviewableContent } from '../components/review/ReviewableContent'
import { CommentEditor } from '../components/review/CommentEditor'
import { CommentCard } from '../components/review/CommentCard'
import { RevisionPreview } from '../components/review/RevisionPreview'
import { useTextSelection } from '../components/review/useTextSelection'
import type { RevisionResult, CommentAnchor } from '../types/review'
import {
  ArrowLeft, CheckCircle2, XCircle, MessageSquare, Sparkles,
  FileText, Filter, ChevronDown, Send, Brain,
} from 'lucide-react'
import { PlatformBadge } from '../components/ui/PlatformBadge'

type CommentFilter = 'all' | 'open' | 'accepted' | 'resolved' | 'rejected'

export function ContentReviewPage() {
  const { id: draftId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [activeCommentId, setActiveCommentId] = useState<string | null>(null)
  const [editingAnchor, setEditingAnchor] = useState<CommentAnchor | null>(null)
  const [pendingRevision, setPendingRevision] = useState<RevisionResult | null>(null)
  const [commentFilter, setCommentFilter] = useState<CommentFilter>('all')
  const [showFilterMenu, setShowFilterMenu] = useState(false)

  // --- Queries ---
  const draftQuery = useQuery({
    queryKey: ['review-draft', draftId],
    queryFn: () => reviewApi.getDraft(draftId!),
    enabled: !!draftId,
  })

  const commentsQuery = useQuery({
    queryKey: ['review-comments', draftId],
    queryFn: () => reviewApi.listComments(draftId!),
    enabled: !!draftId,
  })

  const prefsQuery = useQuery({
    queryKey: ['review-preferences'],
    queryFn: () => reviewApi.getPreferences(),
  })

  const draft = draftQuery.data?.data
  const comments = commentsQuery.data?.comments ?? []

  // --- Text selection ---
  const { selection, clearSelection, containerRef } = useTextSelection(draft?.blocks ?? [])

  // --- Mutations ---
  const createComment = useMutation({
    mutationFn: (data: Parameters<typeof reviewApi.createComment>[1]) =>
      reviewApi.createComment(draftId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-comments', draftId] })
      setEditingAnchor(null)
      clearSelection()
    },
  })

  const updateComment = useMutation({
    mutationFn: ({ commentId, data }: { commentId: string; data: { status?: string; message?: string } }) =>
      reviewApi.updateComment(commentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-comments', draftId] })
    },
  })

  const deleteComment = useMutation({
    mutationFn: (commentId: string) => reviewApi.deleteComment(commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-comments', draftId] })
      setActiveCommentId(null)
    },
  })

  const updateStatus = useMutation({
    mutationFn: (status: string) => reviewApi.updateDraftStatus(draftId!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review-draft', draftId] })
    },
  })

  const requestRevision = useMutation({
    mutationFn: () => {
      const acceptedIds = comments.filter((c) => c.status === 'accepted').map((c) => c.id)
      return reviewApi.requestRevision(draftId!, { accepted_comment_ids: acceptedIds })
    },
    onSuccess: (data) => {
      setPendingRevision(data.revision)
    },
  })

  const applyRevision = useMutation({
    mutationFn: () => reviewApi.applyRevision(draftId!, pendingRevision!.revision_id),
    onSuccess: () => {
      setPendingRevision(null)
      queryClient.invalidateQueries({ queryKey: ['review-draft', draftId] })
      queryClient.invalidateQueries({ queryKey: ['review-comments', draftId] })
    },
  })

  // --- Derived state ---
  const filteredComments = useMemo(() => {
    if (commentFilter === 'all') return comments
    return comments.filter((c) => c.status === commentFilter)
  }, [comments, commentFilter])

  const stats = useMemo(() => ({
    total: comments.length,
    open: comments.filter((c) => c.status === 'open').length,
    accepted: comments.filter((c) => c.status === 'accepted').length,
    resolved: comments.filter((c) => c.status === 'resolved').length,
  }), [comments])

  const canRequestRevision = stats.accepted > 0

  // --- Loading / Error ---
  if (!draftId) return <div className="p-8 text-center text-gray-400">未指定草稿 ID</div>
  if (draftQuery.isLoading) return <div className="p-8 text-center text-gray-400">加载中...</div>
  if (!draft) return <div className="p-8 text-center text-gray-400">草稿不存在</div>

  const statusLabel: Record<string, string> = {
    draft: '草稿',
    in_review: '审核中',
    changes_requested: '需修改',
    revising: 'AI 改写中',
    approved: '已通过',
    rejected: '已拒绝',
  }

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <h1 className="text-sm font-semibold text-gray-900">{draft.title}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <PlatformBadge platform={draft.platform} size="sm" />
              <span className="text-[10px] text-gray-400">v{draft.version}</span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                draft.status === 'approved' ? 'bg-green-100 text-green-700'
                  : draft.status === 'rejected' ? 'bg-red-100 text-red-700'
                  : draft.status === 'revising' ? 'bg-purple-100 text-purple-700'
                  : draft.status === 'changes_requested' ? 'bg-amber-100 text-amber-700'
                  : 'bg-blue-100 text-blue-700'
              }`}>
                {statusLabel[draft.status] || draft.status}
              </span>
            </div>
          </div>
        </div>

        {/* Review actions */}
        <div className="flex items-center gap-2">
          {draft.review_score && (
            <div className="flex gap-1.5 mr-2">
              {(['overall', 'quality', 'compliance', 'spread'] as const).map((key) => {
                const labels = { overall: '综合', quality: '质量', compliance: '合规', spread: '传播' }
                const val = draft.review_score![key]
                return (
                  <div key={key} className="rounded bg-gray-50 px-2 py-1 text-center">
                    <div className="text-[9px] text-gray-400">{labels[key]}</div>
                    <div className={`text-xs font-bold ${val >= 80 ? 'text-green-600' : val >= 60 ? 'text-amber-600' : 'text-red-600'}`}>{val}</div>
                  </div>
                )
              })}
            </div>
          )}

          {canRequestRevision && draft.status !== 'revising' && (
            <button
              onClick={() => requestRevision.mutate()}
              disabled={requestRevision.isPending}
              className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700 disabled:bg-gray-300"
            >
              <Sparkles className="h-3.5 w-3.5" />
              {requestRevision.isPending ? 'AI 改写中...' : `AI 改写 (${stats.accepted})`}
            </button>
          )}

          {draft.status !== 'approved' && draft.status !== 'rejected' && (
            <>
              <button
                onClick={() => updateStatus.mutate('approved')}
                className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> 通过
              </button>
              <button
                onClick={() => {
                  if (stats.open > 0) {
                    updateStatus.mutate('changes_requested')
                  } else {
                    updateStatus.mutate('rejected')
                  }
                }}
                className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                <XCircle className="h-3.5 w-3.5" />
                {stats.open > 0 ? '请求修改' : '拒绝'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Center: Content */}
        <div className="flex-1 overflow-y-auto px-12 py-6" ref={containerRef}>
          {/* Floating toolbar on text selection */}
          {selection && !editingAnchor && (
            <div
              data-review-toolbar
              className="fixed z-50 flex gap-1 rounded-lg border border-gray-200 bg-white p-1 shadow-lg"
              style={{
                top: selection.rect.bottom + 8,
                left: selection.rect.left + selection.rect.width / 2 - 60,
              }}
            >
              <button
                onClick={() => { setEditingAnchor(selection.anchor); clearSelection() }}
                className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
              >
                <MessageSquare className="h-3 w-3" /> 添加评论
              </button>
            </div>
          )}

          {/* Comment editor (inline) */}
          {editingAnchor && (
            <div className="mb-4">
              <CommentEditor
                anchor={editingAnchor}
                onSubmit={(data) => createComment.mutate(data)}
                onCancel={() => setEditingAnchor(null)}
              />
            </div>
          )}

          {/* Revision preview */}
          {pendingRevision && (
            <div className="mb-4">
              <RevisionPreview
                revision={pendingRevision}
                onApply={() => applyRevision.mutate()}
                onDiscard={() => setPendingRevision(null)}
              />
            </div>
          )}

          {/* Content blocks */}
          <div className="pl-8">
            <ReviewableContent
              blocks={draft.blocks}
              comments={comments}
              activeCommentId={activeCommentId}
              onCommentClick={setActiveCommentId}
            />
          </div>

          {/* Tags */}
          {draft.tags.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-1 pl-8">
              {draft.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">#{tag}</span>
              ))}
            </div>
          )}
        </div>

        {/* Right sidebar: Comments */}
        <div className="w-80 flex-shrink-0 border-l border-gray-200 bg-gray-50 flex flex-col">
          {/* Comment header */}
          <div className="border-b border-gray-200 bg-white px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-semibold text-gray-900">评审意见</span>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">
                  {stats.total}
                </span>
              </div>
              <div className="relative">
                <button
                  onClick={() => setShowFilterMenu(!showFilterMenu)}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-gray-500 hover:bg-gray-100"
                >
                  <Filter className="h-3 w-3" />
                  {commentFilter === 'all' ? '全部' : commentFilter === 'open' ? '待处理' : commentFilter === 'accepted' ? '已接受' : commentFilter === 'resolved' ? '已解决' : '已拒绝'}
                  <ChevronDown className="h-3 w-3" />
                </button>
                {showFilterMenu && (
                  <div className="absolute right-0 top-full z-10 mt-1 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                    {([['all', '全部', stats.total], ['open', '待处理', stats.open], ['accepted', '已接受', stats.accepted], ['resolved', '已解决', stats.resolved], ['rejected', '已拒绝', 0]] as const).map(([val, label, count]) => (
                      <button
                        key={val}
                        onClick={() => { setCommentFilter(val as CommentFilter); setShowFilterMenu(false) }}
                        className={`flex w-full items-center justify-between px-3 py-1.5 text-xs hover:bg-gray-50 ${commentFilter === val ? 'font-medium text-blue-600' : 'text-gray-600'}`}
                      >
                        {label}
                        <span className="ml-4 text-gray-400">{count}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Stats bar */}
            {stats.total > 0 && (
              <div className="mt-2 flex h-1.5 overflow-hidden rounded-full bg-gray-100">
                {stats.resolved > 0 && <div className="bg-green-400" style={{ width: `${(stats.resolved / stats.total) * 100}%` }} />}
                {stats.accepted > 0 && <div className="bg-blue-400" style={{ width: `${(stats.accepted / stats.total) * 100}%` }} />}
                {stats.open > 0 && <div className="bg-amber-400" style={{ width: `${(stats.open / stats.total) * 100}%` }} />}
              </div>
            )}
          </div>

          {/* Comment list */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {filteredComments.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquare className="mb-2 h-8 w-8 text-gray-300" />
                <p className="text-xs text-gray-400">
                  {stats.total === 0 ? '选中文本添加评审意见' : '没有匹配的评论'}
                </p>
              </div>
            ) : (
              filteredComments.map((c) => (
                <CommentCard
                  key={c.id}
                  comment={c}
                  isActive={activeCommentId === c.id}
                  onClick={() => setActiveCommentId(activeCommentId === c.id ? null : c.id)}
                  onUpdateStatus={(status) => updateComment.mutate({ commentId: c.id, data: { status } })}
                  onDelete={() => deleteComment.mutate(c.id)}
                />
              ))
            )}
          </div>

          {/* Preference learning indicator */}
          {prefsQuery.data?.preferences?.learned && (
            <div className="border-t border-gray-200 bg-white px-4 py-3">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Brain className="h-3 w-3 text-purple-500" />
                <span className="text-[10px] font-medium text-gray-500">偏好学习</span>
              </div>
              <div className="flex gap-3 text-[10px] text-gray-400">
                <span>接受 {Object.values(prefsQuery.data.preferences.learned.accepted_categories as Record<string, number>).reduce((a: number, b: number) => a + b, 0)}</span>
                <span>拒绝 {Object.values(prefsQuery.data.preferences.learned.rejected_categories as Record<string, number>).reduce((a: number, b: number) => a + b, 0)}</span>
              </div>
              {prefsQuery.data.preferences.tone?.prefer && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {(prefsQuery.data.preferences.tone.prefer as string[]).slice(0, 3).map((t: string) => (
                    <span key={t} className="rounded bg-purple-50 px-1.5 py-0.5 text-[9px] text-purple-600">{t}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Approved: publish button */}
          {draft.status === 'approved' && (
            <div className="border-t border-gray-200 bg-white px-4 py-3">
              <button
                onClick={() => navigate(`/publish?draft=${draftId}`)}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700"
              >
                <Send className="h-3.5 w-3.5" />
                发布到平台
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
