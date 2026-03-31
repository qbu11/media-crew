import type {
  Agent, AgentDetail, Task, Crew, SystemStats, ExecutionRecord, ApiResponse,
  Client, ClientCreate, Account, AccountCreate,
  SearchResult, TrendingItem, SearchPost,
  GeneratedImage, ImageGenerateRequest,
  ContentBrief, ContentDraft, PlatformInfo,
  CrewExecutionStatus, ContentStartRequest, PublishStartRequest,
} from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

// Agents
export const agentApi = {
  list: () => request<ApiResponse<Agent[]>>('/agents'),
  get: (id: string) => request<ApiResponse<AgentDetail>>(`/agents/${id}`),
  getHistory: (id: string) => request<ApiResponse<ExecutionRecord[]>>(`/agents/${id}/history`),
}

// Tasks
export const taskApi = {
  list: (params?: { status?: string; page?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.page) query.set('page', String(params.page))
    if (params?.limit) query.set('limit', String(params.limit))
    return request<ApiResponse<Task[]>>(`/tasks?${query}`)
  },
  get: (id: string) => request<ApiResponse<Task>>(`/tasks/${id}`),
  cancel: (id: string) => request<ApiResponse<void>>(`/tasks/${id}/cancel`, { method: 'POST' }),
  retry: (id: string) => request<ApiResponse<void>>(`/tasks/${id}/retry`, { method: 'POST' }),
}

// Crews
export const crewApi = {
  list: () => request<ApiResponse<Crew[]>>('/crews'),
  get: (id: string) => request<ApiResponse<Crew>>(`/crews/${id}`),
  start: (data: { topic: string; platforms: string[]; style?: string }) =>
    request<ApiResponse<Crew>>('/crews', { method: 'POST', body: JSON.stringify(data) }),
}

// System
export const systemApi = {
  stats: () => request<ApiResponse<SystemStats>>('/system/stats'),
  health: () => request<ApiResponse<{ status: string }>>('/system/health'),
}

// Clients
export const clientApi = {
  list: (skip = 0, limit = 100) =>
    request<{ success: boolean; data: { items: Client[]; total: number } }>(
      `/clients/?skip=${skip}&limit=${limit}`
    ),
  get: (id: string) => request<{ success: boolean; data: Client }>(`/clients/${id}`),
  create: (data: ClientCreate) =>
    request<{ success: boolean; data: Client }>('/clients/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<ClientCreate>) =>
    request<{ success: boolean; data: Client }>(`/clients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) => request<void>(`/clients/${id}`, { method: 'DELETE' }),
}

// Accounts
export const accountApi = {
  list: (params?: { client_id?: string; platform?: string }) => {
    const query = new URLSearchParams()
    if (params?.client_id) query.set('client_id', params.client_id)
    if (params?.platform) query.set('platform', params.platform)
    return request<{ success: boolean; data: { items: Account[]; total: number } }>(
      `/accounts/?${query}`
    )
  },
  get: (id: string) => request<{ success: boolean; data: Account }>(`/accounts/${id}`),
  create: (data: AccountCreate) =>
    request<{ success: boolean; data: Account }>('/accounts/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<AccountCreate>) =>
    request<{ success: boolean; data: Account }>(`/accounts/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) => request<void>(`/accounts/${id}`, { method: 'DELETE' }),
}

// Search
export const searchApi = {
  status: () =>
    request<{ platforms: Record<string, { available: boolean }> }>('/search/status'),
  search: (platform: string, keyword: string, limit = 20, sort = 'hot') =>
    request<SearchResult>(`/search/${platform}`, {
      method: 'POST',
      body: JSON.stringify({ keyword, limit, sort }),
    }),
  multiSearch: (keyword: string, platforms: string[] = [], limit = 20) =>
    request<{ success: boolean; keyword: string; results: Record<string, { total: number; top_posts: SearchPost[] }> }>(
      '/search/multi',
      { method: 'POST', body: JSON.stringify({ keyword, platforms, limit }) },
    ),
  trending: (platform: string, category = '', limit = 20) =>
    request<{ success: boolean; platform: string; trending: TrendingItem[] }>(
      `/search/${platform}/trending?category=${category}&limit=${limit}`
    ),
  userPosts: (platform: string, userId: string, limit = 20) =>
    request<{ success: boolean; posts: SearchPost[] }>(
      `/search/${platform}/user/${userId}?limit=${limit}`
    ),
}

// Images
export const imageApi = {
  platforms: () =>
    request<{ success: boolean; data: Record<string, unknown> }>('/images/platforms'),
  colorSchemes: () =>
    request<{ success: boolean; data: Record<string, unknown> }>('/images/color-schemes'),
  generateSingle: (data: ImageGenerateRequest) =>
    request<{ success: boolean; data: { platform: string; image_type: string; filepath: string } }>(
      '/images/generate-single',
      { method: 'POST', body: JSON.stringify(data) },
    ),
  history: (platform?: string, limit = 20) => {
    const query = new URLSearchParams()
    if (platform) query.set('platform', platform)
    query.set('limit', String(limit))
    return request<{ success: boolean; data: GeneratedImage[]; total: number }>(
      `/images/history?${query}`
    )
  },
}

// Content
export const contentApi = {
  platforms: () =>
    request<{ domestic: PlatformInfo[]; overseas: PlatformInfo[] }>('/content/platforms'),
  generate: (brief: ContentBrief) =>
    request<{ success: boolean; drafts: ContentDraft[] }>('/content/generate', {
      method: 'POST',
      body: JSON.stringify(brief),
    }),
  listDrafts: () => request<{ drafts: ContentDraft[] }>('/content/drafts'),
  deleteDraft: (id: string) =>
    request<{ success: boolean }>(`/content/drafts/${id}`, { method: 'DELETE' }),
  publish: (contentId: string, platforms: string[], scheduleTime?: string) =>
    request<{ success: boolean; results: Record<string, unknown>[] }>('/content/publish', {
      method: 'POST',
      body: JSON.stringify({ content_id: contentId, platforms, schedule_time: scheduleTime }),
    }),
}

// Analytics
export const analyticsApi = {
  operations: () =>
    request<{ total_executions: number; completed: number; failed: number; running: number; success_rate: number; by_type: Record<string, number> }>('/analytics/operations'),
  timeline: () =>
    request<{ timeline: Array<{ date: string; total: number; completed: number; failed: number }> }>('/analytics/operations/timeline'),
  overview: () =>
    request<{ total_posts: number; total_views: number; total_engagement: number; followers_gained: number }>('/analytics/overview'),
  platforms: () =>
    request<{ platforms: Array<{ platform: string; name: string; posts: number; views: number; likes: number; comments: number; shares: number }> }>('/analytics/platforms'),
}

// Crew Executions
export const crewExecutionApi = {
  startContent: (data: ContentStartRequest) =>
    request<{ success: boolean; execution_id: string }>('/crew-executions/content/start', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  startPublish: (data: PublishStartRequest) =>
    request<{ success: boolean; execution_id: string }>('/crew-executions/publish/start', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  get: (id: string) =>
    request<{ success: boolean; data: CrewExecutionStatus }>(`/crew-executions/${id}`),
  list: (crewType?: string, limit = 20) => {
    const query = new URLSearchParams()
    if (crewType) query.set('crew_type', crewType)
    query.set('limit', String(limit))
    return request<{ success: boolean; data: CrewExecutionStatus[]; total: number }>(
      `/crew-executions/?${query}`
    )
  },
}

// Reviews
import type {
  ReviewComment, ReviewableDraft, RevisionResult, UserPreferences,
} from '../types/review'

export const reviewApi = {
  listDrafts: () =>
    request<{ success: boolean; drafts: ReviewableDraft[] }>('/reviews/drafts'),
  getDraft: (id: string) =>
    request<{ success: boolean; data: ReviewableDraft }>(`/reviews/drafts/${id}`),
  updateDraftStatus: (id: string, status: string) =>
    request<{ success: boolean; data: ReviewableDraft }>(`/reviews/drafts/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  listComments: (draftId: string) =>
    request<{ success: boolean; comments: ReviewComment[] }>(`/reviews/drafts/${draftId}/comments`),
  createComment: (draftId: string, data: {
    anchor: { block_id: string; start: number; end: number; quote: string }
    category?: string
    severity?: string
    message: string
    suggested_rewrite?: string
  }) =>
    request<{ success: boolean; comment: ReviewComment }>(`/reviews/drafts/${draftId}/comments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateComment: (commentId: string, data: { status?: string; message?: string }) =>
    request<{ success: boolean; comment: ReviewComment }>(`/reviews/comments/${commentId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteComment: (commentId: string) =>
    request<{ success: boolean }>(`/reviews/comments/${commentId}`, { method: 'DELETE' }),
  requestRevision: (draftId: string, data: { accepted_comment_ids: string[]; mode?: string }) =>
    request<{ success: boolean; revision: RevisionResult }>(`/reviews/drafts/${draftId}/request-revision`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  applyRevision: (draftId: string, revisionId: string) =>
    request<{ success: boolean; data: ReviewableDraft }>(`/reviews/drafts/${draftId}/apply-revision?revision_id=${revisionId}`, {
      method: 'POST',
    }),
  getPreferences: () =>
    request<{ success: boolean; preferences: UserPreferences }>('/reviews/preferences'),
  updatePreferences: (data: Record<string, unknown>) =>
    request<{ success: boolean; preferences: UserPreferences }>('/reviews/preferences', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}
