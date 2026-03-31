import { useState, useCallback, useEffect, useRef } from 'react'
import type { CommentAnchor, ReviewContentBlock } from '../../types/review'

interface SelectionInfo {
  anchor: CommentAnchor
  rect: DOMRect
}

/**
 * 文本选择 hook - 监听用户在内容区域的文本选择
 * 返回选中的锚点信息和浮动工具条位置
 */
export function useTextSelection(blocks: ReviewContentBlock[]) {
  const [selection, setSelection] = useState<SelectionInfo | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMouseUp = useCallback(() => {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed || !sel.rangeCount) {
      return
    }

    const range = sel.getRangeAt(0)
    const text = sel.toString().trim()
    if (!text) return

    // 找到所属的 block 元素
    let node: Node | null = range.startContainer
    let blockEl: HTMLElement | null = null
    while (node && node !== containerRef.current) {
      if (node instanceof HTMLElement && node.dataset.blockId) {
        blockEl = node
        break
      }
      node = node.parentNode
    }

    if (!blockEl) return

    const blockId = blockEl.dataset.blockId!
    const block = blocks.find((b) => b.id === blockId)
    if (!block) return

    // 计算 block 内的 offset
    const blockText = block.content
    const startIdx = blockText.indexOf(text)
    const start = startIdx >= 0 ? startIdx : 0
    const end = start + text.length

    const rect = range.getBoundingClientRect()

    setSelection({
      anchor: { block_id: blockId, start, end, quote: text },
      rect,
    })
  }, [blocks])

  const clearSelection = useCallback(() => {
    setSelection(null)
    window.getSelection()?.removeAllRanges()
  }, [])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.addEventListener('mouseup', handleMouseUp)
    return () => el.removeEventListener('mouseup', handleMouseUp)
  }, [handleMouseUp])

  // 点击空白处清除选择
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('[data-review-toolbar]') && !window.getSelection()?.toString().trim()) {
        setSelection(null)
      }
    }
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [])

  return { selection, clearSelection, containerRef }
}
