import type { RevisionResult } from '../../types/review'
import { Check, X, ArrowRight } from 'lucide-react'

interface Props {
  revision: RevisionResult
  onApply: () => void
  onDiscard: () => void
}

export function RevisionPreview({ revision, onApply, onDiscard }: Props) {
  return (
    <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-purple-900">AI 改写预览</h3>
        <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700">
          {revision.changes.length} 处修改
        </span>
      </div>

      <div className="space-y-3">
        {revision.changes.map((change, i) => (
          <div key={i} className="rounded-lg border border-purple-100 bg-white p-3">
            <div className="mb-1 text-[10px] font-medium text-gray-400">
              Block: {change.block_id}
            </div>

            {/* Diff view */}
            <div className="space-y-2">
              <div className="rounded bg-red-50 px-3 py-2">
                <div className="mb-0.5 text-[10px] font-medium text-red-400">原文</div>
                <p className="text-xs text-red-800 line-through">{change.old_content.slice(0, 200)}{change.old_content.length > 200 ? '...' : ''}</p>
              </div>
              <div className="flex justify-center">
                <ArrowRight className="h-3 w-3 text-gray-300" />
              </div>
              <div className="rounded bg-green-50 px-3 py-2">
                <div className="mb-0.5 text-[10px] font-medium text-green-400">改写</div>
                <p className="text-xs text-green-800">{change.new_content.slice(0, 200)}{change.new_content.length > 200 ? '...' : ''}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Rationale */}
      {revision.rationale.length > 0 && (
        <div className="mt-3 rounded bg-white/60 p-2">
          <div className="mb-1 text-[10px] font-medium text-gray-400">修改说明</div>
          {revision.rationale.map((r, i) => (
            <p key={i} className="text-xs text-gray-600">- {r.resolution}</p>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-3 flex gap-2">
        <button
          onClick={onApply}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-purple-600 py-2 text-xs font-medium text-white hover:bg-purple-700"
        >
          <Check className="h-3.5 w-3.5" />
          应用修改
        </button>
        <button
          onClick={onDiscard}
          className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50"
        >
          <X className="h-3.5 w-3.5" />
          放弃
        </button>
      </div>
    </div>
  )
}
