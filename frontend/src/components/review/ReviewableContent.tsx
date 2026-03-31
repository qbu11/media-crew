import { useMemo, Fragment } from 'react'
import type { ReviewContentBlock, ReviewComment } from '../../types/review'

interface Props {
  blocks: ReviewContentBlock[]
  comments: ReviewComment[]
  activeCommentId: string | null
  onCommentClick: (id: string) => void
}

/**
 * 可审核的内容区 - 渲染 blocks 并高亮有评论的文本
 */
export function ReviewableContent({ blocks, comments, activeCommentId, onCommentClick }: Props) {
  // 按 block_id 分组评论
  const commentsByBlock = useMemo(() => {
    const map: Record<string, ReviewComment[]> = {}
    for (const c of comments) {
      const bid = c.anchor.block_id
      if (!map[bid]) map[bid] = []
      map[bid].push(c)
    }
    return map
  }, [comments])

  return (
    <div className="space-y-1">
      {blocks.map((block) => {
        const blockComments = commentsByBlock[block.id] || []
        return (
          <div key={block.id} data-block-id={block.id} className="group relative">
            {/* 左侧评论指示器 */}
            {blockComments.length > 0 && (
              <div className="absolute -left-6 top-1 flex flex-col gap-0.5">
                {blockComments.map((c) => (
                  <button
                    key={c.id}
                    onClick={(e) => { e.stopPropagation(); onCommentClick(c.id) }}
                    className={`h-2 w-2 rounded-full transition-all ${
                      c.status === 'resolved' ? 'bg-green-400'
                        : c.status === 'accepted' ? 'bg-blue-400'
                        : c.status === 'rejected' ? 'bg-gray-300'
                        : c.severity === 'critical' || c.severity === 'high' ? 'bg-red-400'
                        : 'bg-amber-400'
                    } ${activeCommentId === c.id ? 'ring-2 ring-blue-400 ring-offset-1' : ''}`}
                    title={c.message.slice(0, 40)}
                  />
                ))}
              </div>
            )}

            {/* 内容渲染 */}
            {block.type === 'heading' ? (
              <h2 className="text-lg font-bold text-gray-900 leading-relaxed py-1">
                <HighlightedText text={block.content} comments={blockComments} activeId={activeCommentId} onCommentClick={onCommentClick} />
              </h2>
            ) : block.type === 'quote' ? (
              <blockquote className="border-l-3 border-gray-300 pl-4 text-sm italic text-gray-600 leading-relaxed py-1">
                <HighlightedText text={block.content} comments={blockComments} activeId={activeCommentId} onCommentClick={onCommentClick} />
              </blockquote>
            ) : (
              <p className="text-sm text-gray-800 leading-relaxed py-1">
                <HighlightedText text={block.content} comments={blockComments} activeId={activeCommentId} onCommentClick={onCommentClick} />
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}

/**
 * 高亮文本组件 - 在文本中标记有评论的区域
 */
function HighlightedText({
  text,
  comments,
  activeId,
  onCommentClick,
}: {
  text: string
  comments: ReviewComment[]
  activeId: string | null
  onCommentClick: (id: string) => void
}) {
  if (comments.length === 0) return <>{text}</>

  // 构建高亮区间
  const highlights: Array<{ start: number; end: number; comment: ReviewComment }> = []
  for (const c of comments) {
    if (c.status === 'rejected') continue
    // 用 quote 做 fuzzy match
    const idx = text.indexOf(c.anchor.quote)
    if (idx >= 0) {
      highlights.push({ start: idx, end: idx + c.anchor.quote.length, comment: c })
    } else if (c.anchor.start < text.length) {
      highlights.push({ start: c.anchor.start, end: Math.min(c.anchor.end, text.length), comment: c })
    }
  }

  if (highlights.length === 0) return <>{text}</>

  // 按 start 排序，处理重叠
  highlights.sort((a, b) => a.start - b.start)

  const segments: Array<{ text: string; comment?: ReviewComment }> = []
  let cursor = 0

  for (const h of highlights) {
    if (h.start > cursor) {
      segments.push({ text: text.slice(cursor, h.start) })
    }
    if (h.start >= cursor) {
      segments.push({ text: text.slice(h.start, h.end), comment: h.comment })
      cursor = h.end
    }
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) })
  }

  return (
    <>
      {segments.map((seg, i) =>
        seg.comment ? (
          <mark
            key={i}
            onClick={(e) => { e.stopPropagation(); onCommentClick(seg.comment!.id) }}
            className={`cursor-pointer rounded-sm px-0.5 transition-all ${getHighlightColor(seg.comment!, activeId)}`}
            title={seg.comment.message.slice(0, 60)}
          >
            {seg.text}
          </mark>
        ) : (
          <Fragment key={i}>{seg.text}</Fragment>
        )
      )}
    </>
  )
}

function getHighlightColor(comment: ReviewComment, activeId: string | null): string {
  const isActive = comment.id === activeId
  if (comment.status === 'resolved') {
    return isActive ? 'bg-green-200/80' : 'bg-green-100/60'
  }
  if (comment.status === 'accepted') {
    return isActive ? 'bg-blue-200/80' : 'bg-blue-100/60'
  }
  // open
  if (comment.severity === 'critical' || comment.severity === 'high') {
    return isActive ? 'bg-red-200/80' : 'bg-red-100/60'
  }
  return isActive ? 'bg-amber-200/80' : 'bg-amber-100/60'
}
