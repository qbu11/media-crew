import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { crewExecutionApi } from '../../services/api'
import { cn } from '../../lib/utils'
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'

interface Props {
  executionId: string
  onComplete?: (result: Record<string, unknown>) => void
  onError?: (error: string) => void
}

const STEP_ICONS = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
}

export function CrewProgressTracker({ executionId, onComplete, onError }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['crew-execution', executionId],
    queryFn: () => crewExecutionApi.get(executionId),
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status
      return status === 'running' || status === 'pending' ? 2000 : false
    },
    enabled: !!executionId,
  })

  const execution = data?.data

  useEffect(() => {
    if (!execution) return
    if (execution.status === 'completed' && execution.result && onComplete) {
      onComplete(execution.result)
    }
    if (execution.status === 'failed' && execution.error && onError) {
      onError(execution.error)
    }
  }, [execution?.status])

  if (isLoading || !execution) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        加载执行状态...
      </div>
    )
  }

  const StatusIcon = STEP_ICONS[execution.status] || Clock
  const isRunning = execution.status === 'running'
  const isDone = execution.status === 'completed'
  const isFailed = execution.status === 'failed'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon
            className={cn(
              'h-5 w-5',
              isRunning && 'animate-spin text-blue-500',
              isDone && 'text-green-500',
              isFailed && 'text-red-500',
              !isRunning && !isDone && !isFailed && 'text-gray-400'
            )}
          />
          <span className="text-sm font-medium text-gray-700">
            {execution.current_step}
          </span>
        </div>
        <span className="text-xs text-gray-400">
          {execution.progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            isDone && 'bg-green-500',
            isFailed && 'bg-red-500',
            isRunning && 'bg-blue-500',
            !isRunning && !isDone && !isFailed && 'bg-gray-300'
          )}
          style={{ width: `${execution.progress}%` }}
        />
      </div>

      {/* Error message */}
      {isFailed && execution.error && (
        <p className="mt-2 text-xs text-red-500">{execution.error}</p>
      )}

      {/* Timing */}
      <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
        <span>开始: {new Date(execution.started_at).toLocaleTimeString()}</span>
        {execution.completed_at && (
          <span>完成: {new Date(execution.completed_at).toLocaleTimeString()}</span>
        )}
      </div>
    </div>
  )
}
