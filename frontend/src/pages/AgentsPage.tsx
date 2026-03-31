import { useState } from 'react'
import { useAppStore } from '../stores/app'
import { mockAgents } from '../services/mockData'
import { StatusBadge } from '../components/ui/StatusBadge'
import { formatDuration, formatNumber, cn } from '../lib/utils'
import { Bot, Clock, Zap, CheckCircle, XCircle, ChevronRight } from 'lucide-react'
import type { Agent } from '../types'

function AgentCard({ agent, selected, onClick }: { agent: Agent; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full rounded-xl border p-4 text-left transition-all',
        selected
          ? 'border-blue-300 bg-blue-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-lg',
              agent.status === 'running' ? 'bg-blue-100' : 'bg-gray-100'
            )}
          >
            <Bot className={cn('h-5 w-5', agent.status === 'running' ? 'text-blue-600' : 'text-gray-500')} />
          </div>
          <div>
            <p className="font-medium text-gray-900">{agent.name}</p>
            <p className="text-xs text-gray-500">{agent.role}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={agent.status} />
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </div>
      </div>

      {/* Progress bar for running agents */}
      {agent.status === 'running' && agent.progress !== undefined && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{agent.current_task}</span>
            <span>{agent.progress}%</span>
          </div>
          <div className="mt-1 h-1.5 rounded-full bg-gray-200">
            <div
              className="h-1.5 rounded-full bg-blue-500 transition-all"
              style={{ width: `${agent.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <CheckCircle className="h-3 w-3" />
          {(agent.metrics.success_rate * 100).toFixed(0)}%
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {formatDuration(agent.metrics.avg_duration_ms)}
        </span>
        <span className="flex items-center gap-1">
          <Zap className="h-3 w-3" />
          {agent.metrics.total_executions} 次
        </span>
      </div>
    </button>
  )
}

function AgentDetail({ agent }: { agent: Agent }) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              'flex h-14 w-14 items-center justify-center rounded-xl',
              agent.status === 'running' ? 'bg-blue-100' : 'bg-gray-100'
            )}
          >
            <Bot className={cn('h-7 w-7', agent.status === 'running' ? 'text-blue-600' : 'text-gray-500')} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">{agent.name}</h2>
            <p className="text-sm text-gray-500">{agent.role}</p>
          </div>
          <div className="ml-auto">
            <StatusBadge status={agent.status} />
          </div>
        </div>

        {/* Current task */}
        {agent.current_task && (
          <div className="mt-4 rounded-lg bg-blue-50 p-3">
            <p className="text-xs font-medium text-blue-600">当前任务</p>
            <p className="mt-1 text-sm text-blue-900">{agent.current_task}</p>
            {agent.progress !== undefined && (
              <div className="mt-2">
                <div className="h-2 rounded-full bg-blue-200">
                  <div
                    className="h-2 rounded-full bg-blue-600 transition-all"
                    style={{ width: `${agent.progress}%` }}
                  />
                </div>
                <p className="mt-1 text-right text-xs text-blue-500">{agent.progress}%</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <CheckCircle className="h-4 w-4 text-green-500" />
            成功率
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {(agent.metrics.success_rate * 100).toFixed(1)}%
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock className="h-4 w-4 text-blue-500" />
            平均耗时
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {formatDuration(agent.metrics.avg_duration_ms)}
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Zap className="h-4 w-4 text-yellow-500" />
            执行次数
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">{agent.metrics.total_executions}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <XCircle className="h-4 w-4 text-red-400" />
            失败次数
          </div>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {Math.round(agent.metrics.total_executions * (1 - agent.metrics.success_rate))}
          </p>
        </div>
      </div>

      {/* Token usage */}
      {agent.metrics.tokens_used && (
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Token 消耗</h3>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            {formatNumber(agent.metrics.tokens_used)}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            平均每次: {formatNumber(Math.round(agent.metrics.tokens_used / agent.metrics.total_executions))}
          </p>
        </div>
      )}
    </div>
  )
}

export function AgentsPage() {
  const { agents } = useAppStore()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const displayAgents = agents.length > 0 ? agents : mockAgents
  const selectedAgent = displayAgents.find((a) => a.id === selectedId)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agent 监控</h1>
        <p className="mt-1 text-sm text-gray-500">查看每个 Agent 的运行状态和性能指标</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Agent List */}
        <div className="space-y-3 lg:col-span-2">
          {displayAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              selected={agent.id === selectedId}
              onClick={() => setSelectedId(agent.id === selectedId ? null : agent.id)}
            />
          ))}
        </div>

        {/* Agent Detail */}
        <div className="lg:col-span-3">
          {selectedAgent ? (
            <AgentDetail agent={selectedAgent} />
          ) : (
            <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white">
              <div className="text-center">
                <Bot className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-2 text-sm text-gray-400">选择一个 Agent 查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
