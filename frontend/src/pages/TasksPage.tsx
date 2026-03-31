import { useState } from 'react'
import { useAppStore } from '../stores/app'
import { mockTasks } from '../services/mockData'
import { StatusBadge } from '../components/ui/StatusBadge'
import { formatDate, cn } from '../lib/utils'
import { ListTodo, RotateCcw, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import type { Task, TaskStatus } from '../types'

const statusFilters: { label: string; value: TaskStatus | 'all' }[] = [
  { label: '全部', value: 'all' },
  { label: '待处理', value: 'pending' },
  { label: '运行中', value: 'running' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

const priorityColors: Record<string, string> = {
  urgent: 'text-red-600 bg-red-50',
  high: 'text-orange-600 bg-orange-50',
  medium: 'text-blue-600 bg-blue-50',
  low: 'text-gray-600 bg-gray-50',
}

const priorityLabels: Record<string, string> = {
  urgent: '紧急',
  high: '高',
  medium: '中',
  low: '低',
}

function TaskRow({ task }: { task: Task }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded-lg border border-gray-200 bg-white transition-shadow hover:shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-4 p-4 text-left"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-gray-900">{task.title}</p>
            <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', priorityColors[task.priority])}>
              {priorityLabels[task.priority]}
            </span>
          </div>
          <p className="mt-0.5 truncate text-xs text-gray-500">{task.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={task.status} />
          <span className="text-xs text-gray-400">{formatDate(task.created_at)}</span>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 px-4 pb-4 pt-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs font-medium text-gray-500">输入参数</p>
              <pre className="mt-1 max-h-32 overflow-auto rounded bg-gray-50 p-2 text-xs text-gray-700">
                {JSON.stringify(task.input, null, 2)}
              </pre>
            </div>
            {task.output && (
              <div>
                <p className="text-xs font-medium text-gray-500">输出结果</p>
                <pre className="mt-1 max-h-32 overflow-auto rounded bg-gray-50 p-2 text-xs text-gray-700">
                  {JSON.stringify(task.output, null, 2)}
                </pre>
              </div>
            )}
            {task.error && (
              <div className="col-span-2">
                <p className="text-xs font-medium text-red-500">错误信息</p>
                <p className="mt-1 rounded bg-red-50 p-2 text-xs text-red-700">{task.error}</p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-3 flex gap-2">
            {task.status === 'failed' && (
              <button className="flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100">
                <RotateCcw className="h-3 w-3" />
                重试 ({task.retry_count}/3)
              </button>
            )}
            {(task.status === 'pending' || task.status === 'running') && (
              <button className="flex items-center gap-1 rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100">
                <XCircle className="h-3 w-3" />
                取消
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export function TasksPage() {
  const { tasks } = useAppStore()
  const [filter, setFilter] = useState<TaskStatus | 'all'>('all')

  const displayTasks = tasks.length > 0 ? tasks : mockTasks
  const filtered = filter === 'all' ? displayTasks : displayTasks.filter((t) => t.status === filter)

  const counts = displayTasks.reduce(
    (acc, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">任务队列</h1>
        <p className="mt-1 text-sm text-gray-500">管理和追踪所有任务的执行状态</p>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {statusFilters.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
              filter === f.value
                ? 'bg-blue-100 text-blue-700'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            )}
          >
            {f.label}
            {f.value !== 'all' && counts[f.value] ? (
              <span className="ml-1 text-xs">({counts[f.value]})</span>
            ) : f.value === 'all' ? (
              <span className="ml-1 text-xs">({displayTasks.length})</span>
            ) : null}
          </button>
        ))}
      </div>

      {/* Task List */}
      <div className="space-y-2">
        {filtered.length === 0 ? (
          <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-gray-300 bg-white">
            <div className="text-center">
              <ListTodo className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-2 text-sm text-gray-400">暂无任务</p>
            </div>
          </div>
        ) : (
          filtered.map((task) => <TaskRow key={task.id} task={task} />)
        )}
      </div>
    </div>
  )
}
