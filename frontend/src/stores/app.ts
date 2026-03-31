import { create } from 'zustand'
import type { Agent, Task, Crew, SystemStats, ActivityLog, WSEvent, CrewExecutionStatus, CrewWorkflow, SubAgentStep, ToolCall } from '../types'
import { agentApi, taskApi, crewApi, systemApi } from '../services/api'

interface AppStore {
  // Agents
  agents: Agent[]
  setAgents: (agents: Agent[]) => void
  updateAgent: (id: string, data: Partial<Agent>) => void

  // Tasks
  tasks: Task[]
  setTasks: (tasks: Task[]) => void
  updateTask: (id: string, data: Partial<Task>) => void

  // Crews
  crews: Crew[]
  setCrews: (crews: Crew[]) => void
  updateCrew: (id: string, data: Partial<Crew>) => void

  // System
  stats: SystemStats | null
  setStats: (stats: SystemStats) => void

  // Activity logs
  logs: ActivityLog[]
  addLog: (log: ActivityLog) => void
  clearLogs: () => void

  // WebSocket
  wsConnected: boolean
  setWsConnected: (connected: boolean) => void

  // Crew executions (real-time from WebSocket)
  crewExecutions: Map<string, Partial<CrewExecutionStatus>>
  updateCrewExecution: (id: string, data: Partial<CrewExecutionStatus>) => void

  // ── 工作流状态（新增）──
  workflows: Map<string, CrewWorkflow>
  updateWorkflow: (id: string, data: Partial<CrewWorkflow>) => void
  updateAgentStep: (executionId: string, agentId: string, data: Partial<SubAgentStep>) => void
  addToolCall: (executionId: string, agentId: string, toolCall: ToolCall) => void

  // UI
  sidebarOpen: boolean
  toggleSidebar: () => void

  // Data loading
  loading: boolean
  fetchAll: () => Promise<void>

  // Handle WS events
  handleWSEvent: (event: WSEvent) => void
}

const MAX_LOGS = 200

// Agent 显示名称映射
const AGENT_NAMES: Record<string, string> = {
  researcher: '热点研究员',
  marketer: '营销策划师',
  copywriter: '文案创作者',
  designer: '视觉设计师',
}

export const useAppStore = create<AppStore>((set, get) => ({
  // Agents
  agents: [],
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, data) =>
    set((state) => ({
      agents: state.agents.map((a) => (a.id === id ? { ...a, ...data } : a)),
    })),

  // Tasks
  tasks: [],
  setTasks: (tasks) => set({ tasks }),
  updateTask: (id, data) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...data } : t)),
    })),

  // Crews
  crews: [],
  setCrews: (crews) => set({ crews }),
  updateCrew: (id, data) =>
    set((state) => ({
      crews: state.crews.map((c) => (c.id === id ? { ...c, ...data } : c)),
    })),

  // System
  stats: null,
  setStats: (stats) => set({ stats }),

  // Activity logs
  logs: [],
  addLog: (log) =>
    set((state) => ({
      logs: [log, ...state.logs].slice(0, MAX_LOGS),
    })),
  clearLogs: () => set({ logs: [] }),

  // WebSocket
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),

  // Crew executions (real-time)
  crewExecutions: new Map(),
  updateCrewExecution: (id, data) =>
    set((state) => {
      const next = new Map(state.crewExecutions)
      const existing = next.get(id) ?? {}
      next.set(id, { ...existing, ...data })
      return { crewExecutions: next }
    }),

  // ── 工作流状态（新增）──
  workflows: new Map(),
  updateWorkflow: (id, data) =>
    set((state) => {
      const next = new Map(state.workflows)
      const existing = next.get(id)
      if (existing) {
        next.set(id, { ...existing, ...data })
      } else {
        next.set(id, data as CrewWorkflow)
      }
      return { workflows: next }
    }),

  updateAgentStep: (executionId, agentId, data) =>
    set((state) => {
      const workflow = state.workflows.get(executionId)
      if (!workflow) return state

      const steps = workflow.steps.map((s) =>
        s.agent_id === agentId ? { ...s, ...data } : s
      )
      return {
        workflows: new Map(state.workflows).set(executionId, {
          ...workflow,
          steps,
        }),
      }
    }),

  addToolCall: (executionId, agentId, toolCall) =>
    set((state) => {
      const workflow = state.workflows.get(executionId)
      if (!workflow) return state

      const steps = workflow.steps.map((s) => {
        if (s.agent_id === agentId) {
          return {
            ...s,
            tool_calls: [...(s.tool_calls || []), toolCall],
          }
        }
        return s
      })
      return {
        workflows: new Map(state.workflows).set(executionId, {
          ...workflow,
          steps,
        }),
      }
    }),

  // UI
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  // Data loading
  loading: false,
  fetchAll: async () => {
    set({ loading: true })
    try {
      const [agentsRes, tasksRes, crewsRes, statsRes] = await Promise.allSettled([
        agentApi.list(),
        taskApi.list(),
        crewApi.list(),
        systemApi.stats(),
      ])
      if (agentsRes.status === 'fulfilled' && agentsRes.value.data) {
        set({ agents: agentsRes.value.data })
      }
      if (tasksRes.status === 'fulfilled' && tasksRes.value.data) {
        set({ tasks: tasksRes.value.data })
      }
      if (crewsRes.status === 'fulfilled' && crewsRes.value.data) {
        set({ crews: crewsRes.value.data })
      }
      if (statsRes.status === 'fulfilled' && statsRes.value.data) {
        set({ stats: statsRes.value.data })
      }
    } catch {
      // API unavailable, pages will use mock data fallback
    } finally {
      set({ loading: false })
    }
  },

  // Handle WS events
  handleWSEvent: (event) => {
    const { type, data, timestamp } = event
    const store = get()

    switch (type) {
      case 'agent_status':
        store.updateAgent(data.agent_id as string, data as Partial<Agent>)
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'info',
          agent_name: data.agent_name as string,
          message: `状态变更: ${data.status}`,
        })
        break

      case 'task_update':
        store.updateTask(data.task_id as string, data as Partial<Task>)
        break

      case 'crew_update':
        store.updateCrew(data.crew_id as string, data as Partial<Crew>)
        break

      case 'log':
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: (data.level as ActivityLog['level']) || 'info',
          agent_name: data.agent_name as string,
          message: data.message as string,
        })
        break

      case 'error':
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'error',
          agent_name: data.agent_name as string,
          message: data.message as string,
        })
        break

      case 'metrics':
        if (data.stats) store.setStats(data.stats as SystemStats)
        break

      case 'crew_progress':
        store.updateCrewExecution(data.execution_id as string, {
          status: data.status as CrewExecutionStatus['status'],
          current_step: data.current_step as string,
          progress: data.progress as number,
        })
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'info',
          message: `Crew ${data.crew_type}: ${data.current_step} (${data.progress}%)`,
        })
        break

      // ── 新增：工作流事件处理 ────────────────────────────────────
      case 'workflow_started':
        store.updateWorkflow(data.execution_id as string, {
          execution_id: data.execution_id as string,
          crew_type: 'content',
          status: 'running',
          current_agent: '',
          steps: (data.agents as string[]).map((agentId) => ({
            agent_id: agentId as 'researcher' | 'marketer' | 'copywriter' | 'designer',
            agent_name: AGENT_NAMES[agentId] || agentId,
            status: 'pending' as const,
            tool_calls: [],
          })),
          progress: 0,
          started_at: timestamp,
        })
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'info',
          message: `工作流启动: ${(data.agents as string[])?.join(' → ')}`,
        })
        break

      case 'agent_started':
        store.updateAgentStep(data.execution_id as string, data.agent_id as string, {
          status: 'running',
          started_at: timestamp,
          input: data.input as Record<string, unknown>,
        })
        store.updateWorkflow(data.execution_id as string, {
          current_agent: data.agent_name as string,
        })
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'info',
          agent_name: data.agent_name as string,
          message: `${data.agent_name} 开始执行`,
        })
        break

      case 'agent_completed':
        store.updateAgentStep(data.execution_id as string, data.agent_id as string, {
          status: 'completed',
          completed_at: timestamp,
          duration_ms: data.duration_ms as number,
          output: data.output as Record<string, unknown>,
        })
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'success',
          agent_name: data.agent_name as string,
          message: `${data.agent_name} 完成 (${(data.duration_ms as number) / 1000}秒)`,
        })
        break

      case 'agent_failed':
        store.updateAgentStep(data.execution_id as string, data.agent_id as string, {
          status: 'failed',
          completed_at: timestamp,
          duration_ms: data.duration_ms as number,
        })
        store.addLog({
          id: crypto.randomUUID(),
          timestamp,
          level: 'error',
          agent_name: data.agent_name as string,
          message: `${data.agent_name} 失败: ${data.error}`,
        })
        break

      case 'tool_call_start':
        store.addToolCall(data.execution_id as string, data.agent_id as string, {
          tool_name: data.tool_name as string,
          started_at: timestamp,
          status: 'running',
          input: data.input as Record<string, unknown>,
        })
        break

      case 'tool_call_end':
        // 更新最后一个工具调用状态
        const workflow = store.workflows.get(data.execution_id as string)
        if (workflow) {
          const step = workflow.steps.find((s) => s.agent_id === data.agent_id)
          if (step && step.tool_calls.length > 0) {
            const lastToolCall = step.tool_calls[step.tool_calls.length - 1]
            if (lastToolCall.tool_name === data.tool_name && lastToolCall.status === 'running') {
              store.addToolCall(data.execution_id as string, data.agent_id as string, {
                tool_name: data.tool_name as string,
                started_at: lastToolCall.started_at,
                completed_at: timestamp,
                duration_ms: data.duration_ms as number,
                status: data.status as 'success' | 'failed',
                output: data.output as Record<string, unknown>,
                error: data.error as string | undefined,
              })
            }
          }
        }
        break
    }
  },
}))
