// ============================================================
// 内容审核反馈系统 - 类型定义
// ============================================================

// --- 评论锚点 ---
export interface CommentAnchor {
  block_id: string
  start: number
  end: number
  quote: string // 原文引用，用于 fuzzy re-attach
}

// --- 枚举 ---
export type CommentCategory = 'issue' | 'suggestion' | 'approval' | 'question'
export type CommentSeverity = 'low' | 'medium' | 'high' | 'critical'
export type CommentStatus = 'open' | 'accepted' | 'rejected' | 'resolved'

export type ReviewDraftStatus =
  | 'draft'
  | 'in_review'
  | 'changes_requested'
  | 'revising'
  | 'approved'
  | 'rejected'
  | 'scheduled'
  | 'published'

// --- 评审评论 ---
export interface ReviewComment {
  id: string
  draft_id: string
  anchor: CommentAnchor
  category: CommentCategory
  severity: CommentSeverity
  status: CommentStatus
  message: string
  suggested_rewrite?: string
  author: { id: string; name: string; type: 'human' | 'ai' }
  created_at: string
  resolved_at?: string
}

// --- 内容块 ---
export interface ReviewContentBlock {
  id: string
  type: 'text' | 'heading' | 'list' | 'quote' | 'image'
  content: string
}

// --- 可审核的草稿 ---
export interface ReviewableDraft {
  id: string
  title: string
  platform: string
  status: ReviewDraftStatus
  version: number
  blocks: ReviewContentBlock[]
  tags: string[]
  created_at: string
  updated_at: string
  review_score?: {
    overall: number
    quality: number
    compliance: number
    spread: number
  }
}

// --- AI 修改请求 ---
export interface RevisionRequest {
  draft_id: string
  draft_version: number
  accepted_comment_ids: string[]
  mode: 'targeted' | 'full'
}

// --- AI 修改结果 ---
export interface RevisionChange {
  block_id: string
  old_content: string
  new_content: string
}

export interface RevisionResult {
  revision_id: string
  changes: RevisionChange[]
  rationale: Array<{ comment_id: string; resolution: string }>
}

// --- 用户偏好 ---
export interface UserPreferences {
  tone: { prefer: string[]; avoid: string[] }
  structure: { prefer_opening: string[]; prefer_length: 'short' | 'medium' | 'long' }
  style: { emoji: 'none' | 'light' | 'heavy'; cta: 'none' | 'soft' | 'strong' }
  learned: {
    accepted_categories: Record<CommentCategory, number>
    rejected_categories: Record<CommentCategory, number>
    last_updated: string
  }
}
