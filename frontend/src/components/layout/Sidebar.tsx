import { NavLink } from 'react-router-dom'
import { useAppStore } from '../../stores/app'
import { cn } from '../../lib/utils'
import {
  LayoutDashboard,
  Bot,
  GitBranch,
  ListTodo,
  BarChart3,
  Search,
  Image,
  Users,
  Menu,
  X,
  Wifi,
  WifiOff,
  PenTool,
  Send,
  FileText,
  ClipboardCheck,
} from 'lucide-react'

const monitorItems = [
  { to: '/', icon: LayoutDashboard, label: '概览' },
  { to: '/agents', icon: Bot, label: 'Agent 监控' },
  { to: '/crews', icon: GitBranch, label: 'Crew 编排' },
  { to: '/tasks', icon: ListTodo, label: '任务队列' },
  { to: '/analytics', icon: BarChart3, label: '数据分析' },
]

const contentItems = [
  { to: '/content', icon: FileText, label: '内容中心' },
  { to: '/content/create', icon: PenTool, label: '内容创作' },
  { to: '/content/drafts', icon: ClipboardCheck, label: '内容审核' },
  { to: '/publish', icon: Send, label: '内容发布' },
]

const operationItems = [
  { to: '/search', icon: Search, label: '热点搜索' },
  { to: '/images', icon: Image, label: '图片生成' },
  { to: '/clients', icon: Users, label: '客户管理' },
]

function NavSection({ title, items }: { title: string; items: typeof monitorItems }) {
  return (
    <div>
      <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
        {title}
      </p>
      <div className="space-y-1">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )
            }
          >
            <item.icon className="h-5 w-5" />
            {item.label}
          </NavLink>
        ))}
      </div>
    </div>
  )
}

export function Sidebar() {
  const { sidebarOpen, toggleSidebar, wsConnected } = useAppStore()

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 z-30 flex h-screen w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-200 lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-blue-600" />
            <span className="text-lg font-semibold text-gray-900">Crew Ops</span>
          </div>
          <button onClick={toggleSidebar} className="lg:hidden">
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
          <NavSection title="系统监控" items={monitorItems} />
          <NavSection title="内容运营" items={contentItems} />
          <NavSection title="运营工具" items={operationItems} />
        </nav>

        {/* Footer */}
        <div className="border-t border-gray-200 px-4 py-3">
          <div className="flex items-center gap-2 text-xs">
            {wsConnected ? (
              <>
                <Wifi className="h-3.5 w-3.5 text-green-500" />
                <span className="text-green-600">WebSocket 已连接</span>
              </>
            ) : (
              <>
                <WifiOff className="h-3.5 w-3.5 text-red-400" />
                <span className="text-red-500">WebSocket 未连接</span>
              </>
            )}
          </div>
          <div className="mt-1 text-xs text-gray-400">v0.1.0</div>
        </div>
      </aside>

      {/* Mobile toggle */}
      <button
        onClick={toggleSidebar}
        className="fixed left-4 top-4 z-10 rounded-lg bg-white p-2 shadow-md lg:hidden"
      >
        <Menu className="h-5 w-5 text-gray-600" />
      </button>
    </>
  )
}
