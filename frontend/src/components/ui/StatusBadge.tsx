import { cn, getStatusBgColor } from '../../lib/utils'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const labels: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    waiting: '等待中',
    error: '错误',
    completed: '已完成',
    failed: '失败',
    pending: '待处理',
    cancelled: '已取消',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
        getStatusBgColor(status),
        className
      )}
    >
      {status === 'running' && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {labels[status] || status}
    </span>
  )
}
