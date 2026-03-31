import { useAppStore } from '../stores/app'
import { mockCrews, mockAgents } from '../services/mockData'
import { StatusBadge } from '../components/ui/StatusBadge'
import { cn } from '../lib/utils'
import { GitBranch, ArrowRight, Bot } from 'lucide-react'

// Crew pipeline flow visualization
function CrewPipeline({ crew }: { crew: typeof mockCrews[0] }) {
  const { agents } = useAppStore()
  const displayAgents = agents.length > 0 ? agents : mockAgents

  // Define the pipeline steps for ContentCrew
  const pipelineSteps = [
    { name: 'ContentOrchestrator', role: '编排', agentId: 'agent_001' },
    { name: 'Researcher', role: '研究', agentId: 'agent_002' },
    { name: 'Marketer', role: '策划', agentId: 'agent_003' },
    { name: 'Copywriter', role: '文案', agentId: 'agent_004' },
    { name: 'Designer', role: '设计', agentId: 'agent_005' },
    { name: 'ContentReviewer', role: '审核', agentId: 'agent_006' },
    { name: 'PlatformAdapter', role: '适配', agentId: 'agent_007' },
  ]

  const steps = crew.name === 'ContentCrew'
    ? pipelineSteps
    : crew.agents.map((id) => {
        const agent = displayAgents.find((a) => a.id === id)
        return { name: agent?.name || id, role: agent?.role || '', agentId: id }
      })

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-lg',
              crew.status === 'running' ? 'bg-blue-100' : 'bg-gray-100'
            )}
          >
            <GitBranch
              className={cn('h-5 w-5', crew.status === 'running' ? 'text-blue-600' : 'text-gray-500')}
            />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{crew.name}</h3>
            <p className="text-xs text-gray-500">
              步骤 {crew.current_step}/{crew.total_steps}
            </p>
          </div>
        </div>
        <StatusBadge status={crew.status} />
      </div>

      {/* Pipeline visualization */}
      <div className="mt-6 overflow-x-auto">
        <div className="flex items-center gap-2 pb-2">
          {steps.map((step, i) => {
            const agent = displayAgents.find((a) => a.id === step.agentId)
            const stepStatus =
              i < crew.current_step
                ? 'completed'
                : i === crew.current_step
                  ? crew.status === 'running'
                    ? 'running'
                    : 'pending'
                  : 'pending'

            return (
              <div key={step.agentId} className="flex items-center gap-2">
                <div
                  className={cn(
                    'flex min-w-[100px] flex-col items-center rounded-lg border p-3 transition-all',
                    stepStatus === 'running'
                      ? 'border-blue-300 bg-blue-50'
                      : stepStatus === 'completed'
                        ? 'border-green-200 bg-green-50'
                        : 'border-gray-200 bg-gray-50'
                  )}
                >
                  <Bot
                    className={cn(
                      'h-5 w-5',
                      stepStatus === 'running'
                        ? 'text-blue-600'
                        : stepStatus === 'completed'
                          ? 'text-green-600'
                          : 'text-gray-400'
                    )}
                  />
                  <p className="mt-1 text-xs font-medium text-gray-900">{step.name}</p>
                  <p className="text-[10px] text-gray-500">{step.role}</p>
                  <StatusBadge status={agent?.status || stepStatus} className="mt-1" />
                </div>
                {i < steps.length - 1 && (
                  <ArrowRight
                    className={cn(
                      'h-4 w-4 flex-shrink-0',
                      stepStatus === 'completed' ? 'text-green-400' : 'text-gray-300'
                    )}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Progress bar */}
      {crew.total_steps > 0 && (
        <div className="mt-4">
          <div className="h-2 rounded-full bg-gray-100">
            <div
              className={cn(
                'h-2 rounded-full transition-all',
                crew.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
              )}
              style={{ width: `${(crew.current_step / crew.total_steps) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export function CrewsPage() {
  const { crews } = useAppStore()

  const displayCrews = crews.length > 0 ? crews : mockCrews

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Crew 编排</h1>
        <p className="mt-1 text-sm text-gray-500">查看 Crew 执行流程和 Agent 协作关系</p>
      </div>

      <div className="space-y-4">
        {displayCrews.map((crew) => (
          <CrewPipeline key={crew.id} crew={crew} />
        ))}
      </div>
    </div>
  )
}
