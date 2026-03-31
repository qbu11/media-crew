import type { ReviewComment } from '../../types/review'
import { Check, X, RotateCcw, Trash2, AlertTriangle, Lightbulb, HelpCircle, ThumbsUp } from 'lucide-react'

const CATEGORY_CONFIG: Record<string, { icon: typeof AlertTriangle; color: string; label: string }> = {
  issue: { icon: AlertTriangle, color: 'text-red-500', label: '问题' },
  suggestion: { icon: Lightbulb, color: 'text-amber-500', label: '建议' },
  question: { icon: HelpCircle, color: 'text-blue-500', label: '疑问' },
  approval: { icon: ThumbsUp, color: 'text-green-500', label: '认可' },
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-amber-50 border-amber-200',
  accepted: 'bg-blue-50 border-blue-200',
  rejected: 'bg-gray-50 border-gray-200',
  resolved: 'bg-green-50 border-green-200',
}

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-gray-100 text-gray-600',
}

interface Props {
  comment: ReviewComment
  isActive: boolean
  onClick: () => void
  onUpdateStatus: (status: string) => void
  onDelete: () => void
}

export function CommentCard({ comment, isActive, onClick, onUpdateStatus, onDelete }: Props) {
  const cat = CATEGORY_CONFIG[comment.category] || CATEGORY_CONFIG.suggestion
  const Icon = cat.icon

  return (
    <div
      onClick={onClick}
      className={`cursor-pointer rounded-lg border p-3 transition-all ${
        isActive ? 'ring-2 ring-blue-400 ' : ''
      }${STATUS_COLORS[comment.status] || STATUS_COLORS.open}`}
    >
      {/* Header */}
      <div className="mb-1.5 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon className={`h-3.5 w-3.5 ${cat.color}`} />
          <span className="text-xs font-medium text-gray-700">{cat.label}</span>
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${SEVERITY_BADGE[comment.severity] || ''}`}>
            {comment.severity === 'critical' ? '严重' : comment.severity === 'high' ? '高' : comment.severity === 'medium' ? '中' : '低'}
          </span>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
          comment.status === 'open' ? 'bg-amber-100 text-amber-700'
            : comment.status === 'accepted' ? 'bg-blue-100 text-blue-700'
            : comment.status === 'resolved' ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
        }`}>
          {comment.status === 'open' ? '待处理' : comment.status === 'accepted' ? '已接受' : comment.status === 'resolved' ? '已解决' : '已拒绝'}
        </span>
      </div>

      {/* Quote */}
      <div className="mb-2 rounded bg-white/60 px-2 py-1 text-[11px] italic text-gray-500">
        "{comment.anchor.quote.slice(0, 50)}{comment.anchor.quote.length > 50 ? '...' : ''}"
      </div>

      {/* Message */}
      <p className="mb-2 text-sm text-gray-800">{comment.message}</p>

      {/* Suggested rewrite */}
      {comment.suggested_rewrite && (
        <div className="mb-2 rounded border border-green-200 bg-green-50 px-2 py-1.5 text-xs text-green-800">
          <span className="font-medium">建议改写：</span>{comment.suggested_rewrite}
        </div>
      )}

      {/* Actions */}
      {comment.status === 'open' && (
        <div className="flex gap-1 border-t border-gray-100 pt-2">
          <button
            onClick={(e) => { e.stopPropagation(); onUpdateStatus('accepted') }}
            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-blue-600 hover:bg-blue-100"
          >
            <Check className="h-3 w-3" /> 接受
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onUpdateStatus('rejected') }}
            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-gray-500 hover:bg-gray-100"
          >
            <X className="h-3 w-3" /> 拒绝
          </button>
          <div className="flex-1" />
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      )}

      {comment.status === 'resolved' && (
        <div className="flex gap-1 border-t border-gray-100 pt-2">
          <button
            onClick={(e) => { e.stopPropagation(); onUpdateStatus('open') }}
            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-gray-500 hover:bg-gray-100"
          >
            <RotateCcw className="h-3 w-3" /> 重新打开
          </button>
        </div>
      )}
    </div>
  )
}
