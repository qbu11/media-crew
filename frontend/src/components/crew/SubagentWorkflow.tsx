import { useAppStore } from '@/stores/app'
import { cn } from '@/lib/utils'
import type { SubAgentStep, ToolCall } from '@/types'
import { Bot, ChevronRight, CheckCircle2, Clock, Loader2, Wrench } from 'lucide-react'

interface Props {
  executionId: string
}

// Agent 配置
const AGENT_CONFIG = {
  researcher: {
    icon: Bot,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    name: '热点研究',
  },
  marketer: {
    icon: Bot,
    color: 'text-purple-600',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    name: '营销策划',
  },
  copywriter: {
    icon: Bot,
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    name: '文案创作',
  },
  designer: {
    icon: Bot,
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    name: '视觉设计',
  },
} as const

export function SubagentWorkflow({ executionId }: Props) {
  const workflows = useAppStore((s) => s.workflows)
  const workflow = workflows.get(executionId)

  if (!workflow || !workflow.steps || workflow.steps.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        等待工作流启动...
      </div>
    )
  }

  const steps = workflow.steps
  const currentStep = steps.find((s) => s.status === 'running') || steps.find((s) => s.status === 'pending') || steps[steps.length - 1]
  const progress = Math.round((steps.filter((s) => s.status === 'completed').length / steps.length) * 100)

  return (
    <div className="space-y-6">
      {/* 进度条 */}
      <div className="flex items-center gap-3">
        <div className="h-2 flex-1 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-sm text-gray-600">{progress}%</span>
      </div>

      {/* 水平流程图 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-4">
        {steps.map((step, i) => {
          const config = AGENT_CONFIG[step.agent_id]
          const Icon = config.icon
          const isRunning = step.status === 'running'
          const isCompleted = step.status === 'completed'
          const isFailed = step.status === 'failed'

          return (
            <div key={step.agent_id} className="flex items-center gap-2">
              <div
                className={cn(
                  'flex min-w-[140px] flex-col items-center rounded-lg border-2 p-3 transition-all',
                  isRunning ? config.border + ' ' + config.bg + ' animate-pulse' :
                  isCompleted ? 'border-green-300 bg-green-50' :
                  isFailed ? 'border-red-300 bg-red-50' :
                  'border-gray-200 bg-gray-50'
                )}
              >
                <Icon className={cn(
                  'h-6 w-6',
                  isRunning ? config.color + ' animate-spin' :
                  isCompleted ? 'text-green-500' :
                  isFailed ? 'text-red-500' :
                  'text-gray-400'
                )} />
                <p className="mt-2 text-sm font-medium">{config.name}</p>
                <StepStatusBadge status={step.status} />
                {step.duration_ms && (
                  <span className="mt-1 text-xs text-gray-500">{(step.duration_ms / 1000).toFixed(1)}s</span>
                )}
              </div>
              {i < steps.length - 1 && (
                <ChevronRight className={cn(
                  'h-5 w-5 flex-shrink-0',
                  isCompleted ? 'text-green-400' : 'text-gray-300'
                )} />
              )}
            </div>
          )
        })}
      </div>

      {/* 当前 agent 详情 + 工具调用列表 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <AgentDetailCard step={currentStep} />
        <ToolCallsList toolCalls={currentStep?.tool_calls || []} />
      </div>
    </div>
  )
}

function StepStatusBadge({ status }: { status: SubAgentStep['status'] }) {
  if (status === 'running') return <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
  if (status === 'completed') return <CheckCircle2 className="h-3 w-3 text-green-500" />
  if (status === 'failed') return <Clock className="h-3 w-3 text-red-500" />
  return <Clock className="h-3 w-3 text-gray-400" />
}

function AgentDetailCard({ step }: { step: SubAgentStep | null }) {
  if (!step) return null

  const config = AGENT_CONFIG[step.agent_id]

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Bot className={`h-4 w-4 ${config.color}`} />
        {step.agent_name} 详情
      </h3>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">状态</span>
          <span className={cn(
            'font-medium',
            step.status === 'running' ? 'text-blue-600' :
            step.status === 'completed' ? 'text-green-600' :
            step.status === 'failed' ? 'text-red-600' :
            'text-gray-600'
          )}>
            {step.status === 'running' ? '执行中' :
             step.status === 'completed' ? '已完成' :
             step.status === 'failed' ? '失败' : '等待中'}
          </span>
        </div>
        {step.duration_ms && (
          <div className="flex justify-between">
            <span className="text-gray-500">耗时</span>
            <span>{(step.duration_ms / 1000).toFixed(1)}秒</span>
          </div>
        )}
        {step.tool_calls && step.tool_calls.length > 0 && (
          <div className="flex justify-between">
            <span className="text-gray-500">工具调用</span>
            <span>{step.tool_calls.length} 次</span>
          </div>
        )}
        {/* Input 预览 */}
        {step.input && (
          <div className="mt-3">
            <span className="text-gray-500">输入预览</span>
            <pre className="mt-1 max-h-24 overflow-auto rounded bg-gray-50 p-2 text-xs">
              {JSON.stringify(step.input, null, 2)}
            </pre>
          </div>
        )}
        {/* Output 预览 */}
        {step.output && step.status === 'completed' && (
          <div className="mt-3">
            <span className="text-gray-500">输出预览</span>
            <pre className="mt-1 max-h-24 overflow-auto rounded bg-green-50 p-2 text-xs">
              {JSON.stringify(step.output, null, 2).substring(0, 300)}...
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}

function ToolCallsList({ toolCalls }: { toolCalls: ToolCall[] }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Wrench className="h-4 w-4 text-gray-500" />
        工具调用记录
      </h3>
      {toolCalls.length === 0 ? (
        <p className="text-sm text-gray-400">暂无工具调用</p>
      ) : (
        <div className="space-y-2">
          {toolCalls.map((call, i) => (
            <div
              key={i}
              className={cn(
                'flex items-center justify-between rounded-lg px-3 py-2 transition-colors',
                call.status === 'running' ? 'bg-blue-50' :
                call.status === 'success' ? 'bg-green-50' :
                'bg-red-50'
              )}
            >
              <div className="flex items-center gap-2">
                <Wrench className="h-3 w-3 text-gray-400" />
                <span className="text-xs font-medium">{call.tool_name}</span>
              </div>
              <div className="flex items-center gap-2">
                {call.status === 'running' && <Loader2 className="h-3 w-3 animate-spin text-blue-500" />}
                {call.status === 'success' && <CheckCircle2 className="h-3 w-3 text-green-500" />}
                {call.status === 'failed' && <Clock className="h-3 w-3 text-red-500" />}
                {call.duration_ms && (
                  <span className="text-xs text-gray-500">{(call.duration_ms / 1000).toFixed(1)}s</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
