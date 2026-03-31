import { useState } from 'react'
import type { CommentCategory, CommentSeverity, CommentAnchor } from '../../types/review'
import { MessageSquarePlus, AlertTriangle, Lightbulb, HelpCircle, X } from 'lucide-react'

const CATEGORIES: { value: CommentCategory; label: string; icon: typeof AlertTriangle; color: string }[] = [
  { value: 'issue', label: '问题', icon: AlertTriangle, color: 'text-red-500' },
  { value: 'suggestion', label: '建议', icon: Lightbulb, color: 'text-amber-500' },
  { value: 'question', label: '疑问', icon: HelpCircle, color: 'text-blue-500' },
]

const SEVERITIES: { value: CommentSeverity; label: string; color: string }[] = [
  { value: 'critical', label: '严重', color: 'bg-red-100 text-red-700' },
  { value: 'high', label: '高', color: 'bg-orange-100 text-orange-700' },
  { value: 'medium', label: '中', color: 'bg-amber-100 text-amber-700' },
  { value: 'low', label: '低', color: 'bg-gray-100 text-gray-600' },
]

interface Props {
  anchor: CommentAnchor
  onSubmit: (data: {
    anchor: CommentAnchor
    category: CommentCategory
    severity: CommentSeverity
    message: string
    suggested_rewrite?: string
  }) => void
  onCancel: () => void
}

export function CommentEditor({ anchor, onSubmit, onCancel }: Props) {
  const [category, setCategory] = useState<CommentCategory>('suggestion')
  const [severity, setSeverity] = useState<CommentSeverity>('medium')
  const [message, setMessage] = useState('')
  const [rewrite, setRewrite] = useState('')
  const [showRewrite, setShowRewrite] = useState(false)

  const handleSubmit = () => {
    if (!message.trim()) return
    onSubmit({
      anchor,
      category,
      severity,
      message: message.trim(),
      suggested_rewrite: rewrite.trim() || undefined,
    })
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-white p-3 shadow-lg">
      {/* 引用文本 */}
      <div className="mb-3 rounded bg-blue-50 px-3 py-2 text-xs text-blue-800">
        <span className="font-medium">选中文本：</span>
        <span className="italic">"{anchor.quote.slice(0, 60)}{anchor.quote.length > 60 ? '...' : ''}"</span>
      </div>

      {/* 类型选择 */}
      <div className="mb-2 flex gap-1">
        {CATEGORIES.map((c) => {
          const Icon = c.icon
          return (
            <button
              key={c.value}
              onClick={() => setCategory(c.value)}
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
                category === c.value
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              <Icon className="h-3 w-3" />
              {c.label}
            </button>
          )
        })}
      </div>

      {/* 严重程度 */}
      <div className="mb-3 flex gap-1">
        {SEVERITIES.map((s) => (
          <button
            key={s.value}
            onClick={() => setSeverity(s.value)}
            className={`rounded-md px-2 py-0.5 text-[10px] font-medium transition-colors ${
              severity === s.value ? s.color + ' ring-1 ring-gray-400' : 'bg-gray-50 text-gray-400'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* 评论内容 */}
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="输入评审意见..."
        rows={3}
        autoFocus
        className="mb-2 w-full resize-none rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />

      {/* 建议改写 */}
      {showRewrite ? (
        <div className="mb-2">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500">建议改写</span>
            <button onClick={() => { setShowRewrite(false); setRewrite('') }} className="text-gray-400 hover:text-gray-600">
              <X className="h-3 w-3" />
            </button>
          </div>
          <textarea
            value={rewrite}
            onChange={(e) => setRewrite(e.target.value)}
            placeholder="输入建议的改写内容..."
            rows={2}
            className="w-full resize-none rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-green-400 focus:outline-none focus:ring-1 focus:ring-green-400"
          />
        </div>
      ) : (
        <button
          onClick={() => setShowRewrite(true)}
          className="mb-2 text-xs text-blue-500 hover:text-blue-700"
        >
          + 添加建议改写
        </button>
      )}

      {/* 操作按钮 */}
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded-md px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100"
        >
          取消
        </button>
        <button
          onClick={handleSubmit}
          disabled={!message.trim()}
          className="flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:bg-gray-300"
        >
          <MessageSquarePlus className="h-3 w-3" />
          提交评论
        </button>
      </div>
    </div>
  )
}
