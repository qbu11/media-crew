// Agent 状态
export type AgentStatus = 'idle' | 'running' | 'waiting' | 'error'

// Agent 指标
export interface AgentMetrics {
  total_executions: number
  success_rate: number
  avg_duration_ms: number
  tokens_used?: number
}

// Agent 定义
export interface Agent {
  id: string
  name: string
  role: string
  status: AgentStatus
  last_activity: string
  metrics: AgentMetrics
  current_task?: string
  progress?: number
}

// Agent 详情
export interface AgentDetail extends Agent {
  goal: string
  backstory: string
  tools: string[]
  execution_history: ExecutionRecord[]
}

// 执行记录
export interface ExecutionRecord {
  id: string
  agent_id: string
  task_id: string
  status: 'success' | 'failed' | 'running'
  started_at: string
  completed_at?: string
  duration_ms?: number
  input: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
  tokens_used?: number
}

// 任务
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Task {
  id: string
  crew_id: string
  agent_id?: string
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  created_at: string
  started_at?: string
  completed_at?: string
  input: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
  retry_count: number
}

// Crew
export type CrewStatus = 'idle' | 'running' | 'completed' | 'failed'

export interface Crew {
  id: string
  name: string
  status: CrewStatus
  agents: string[] // agent IDs
  current_step: number
  total_steps: number
  started_at?: string
  completed_at?: string
}

// Crew 执行步骤
export interface CrewStep {
  agent_id: string
  agent_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  duration_ms?: number
  input?: Record<string, unknown>
  output?: Record<string, unknown>
}

// ── SubAgent 工作流 ──
export type SubAgentStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface ToolCall {
  tool_name: string
  started_at: string
  completed_at?: string
  duration_ms?: number
  status: 'running' | 'success' | 'failed'
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
}

export interface SubAgentStep {
  agent_id: 'researcher' | 'marketer' | 'copywriter' | 'designer'
  agent_name: string
  status: SubAgentStatus
  started_at?: string
  completed_at?: string
  duration_ms?: number
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  tool_calls: ToolCall[]
}

export interface CrewWorkflow {
  execution_id: string
  crew_type: 'content'
  status: SubAgentStatus
  current_agent: string
  steps: SubAgentStep[]
  progress: number
  started_at: string
  completed_at?: string
}

// WebSocket 事件
export interface WSEvent {
  type:
    | 'agent_status'
    | 'task_update'
    | 'crew_update'
    | 'log'
    | 'error'
    | 'metrics'
    | 'crew_progress'
    | 'workflow_started'
    | 'agent_started'
    | 'agent_completed'
    | 'agent_failed'
    | 'tool_call_start'
    | 'tool_call_end'
  timestamp: string
  data: Record<string, unknown>
}

// 活动日志
export interface ActivityLog {
  id: string
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success'
  agent_name?: string
  message: string
}

// 系统统计
export interface SystemStats {
  active_crews: number
  active_agents: number
  pending_tasks: number
  completed_today: number
  total_tokens_today: number
  api_calls_today: number
}

// API 响应
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total: number
    page: number
    limit: number
  }
}

// ── 平台 ──
export type PlatformId = 'xiaohongshu' | 'wechat' | 'weibo' | 'zhihu' | 'douyin' | 'bilibili'

export interface PlatformInfo {
  id: PlatformId
  name: string
  status: 'available' | 'unavailable'
}

// ── 客户 ──
export interface Client {
  id: string
  name: string
  industry: string | null
  description: string | null
  created_at: string
  updated_at: string
}

export interface ClientCreate {
  name: string
  industry?: string
  description?: string
}

// ── 账号 ──
export type AccountStatus = 'active' | 'inactive' | 'suspended'

export interface Account {
  id: string
  client_id: string
  platform: PlatformId
  username: string
  status: AccountStatus
  is_logged_in: boolean
  last_login: string | null
  created_at: string
  updated_at: string
}

export interface AccountCreate {
  client_id: string
  platform: PlatformId
  username: string
  status?: AccountStatus
}

// ── 搜索 ──
export interface SearchPost {
  post_id: string
  title: string
  content: string
  author: string
  author_id: string
  publish_time: string
  url: string
  likes: number
  comments: number
  shares: number
  views: number
}

export interface SearchResult {
  success: boolean
  platform: string
  keyword: string
  total: number
  posts: SearchPost[]
  searched_at: string
}

export interface TrendingItem {
  rank?: number
  topic: string
  heat: number
  trend: 'up' | 'down' | 'stable'
}

// ── 图片 ──
export type ImagePlatform = 'xiaohongshu' | 'weibo' | 'zhihu' | 'bilibili' | 'douyin'
export type ColorScheme = 'tech' | 'business' | 'vibrant' | 'minimal'
export type ImageType = 'cover' | 'comparison' | 'highlights' | 'summary'

export interface ImageGenerateRequest {
  platform: ImagePlatform
  color_scheme: ColorScheme
  image_type: ImageType
  data: Record<string, unknown>
}

export interface GeneratedImage {
  filepath: string
  filename: string
  platform: string
  size: number
  created_at: number
}

// ── 内容 ──
export interface ContentBrief {
  topic: string
  keywords: string[]
  target_platforms: PlatformId[]
  tone: string
  language: string
}

export interface ContentDraft {
  id: string
  title: string
  body: string
  platform: string
  platform_name?: string
  status: 'draft' | 'published' | 'archived'
  created_at: string
  word_count: number
}

// ── Crew 执行 ──
export type CrewType = 'content' | 'publish' | 'analytics'

export interface CrewExecutionStatus {
  id: string
  crew_type: CrewType
  status: 'pending' | 'running' | 'completed' | 'failed'
  current_step: string
  progress: number
  started_at: string
  completed_at?: string
  result?: Record<string, unknown>
  error?: string
  inputs?: Record<string, unknown>
}

export interface ContentStartRequest {
  topic: string
  target_platform: string
  content_type: string
  research_depth: string
  viral_category?: string
  brand_voice?: string
}

export interface PublishStartRequest {
  content_id: string
  content?: Record<string, unknown>
  target_platforms: string[]
  schedule_time?: string
}
