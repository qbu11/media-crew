import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clientApi, accountApi } from '../services/api'
import { Modal } from '../components/ui/Modal'
import { PlatformBadge, PLATFORMS } from '../components/ui/PlatformBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { ArrowLeft, Plus, Trash2, Loader2, User, Edit2 } from 'lucide-react'
import { formatDate } from '../lib/utils'
import type { PlatformId, Account } from '../types'

export function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showAddAccount, setShowAddAccount] = useState(false)
  const [accPlatform, setAccPlatform] = useState<PlatformId>('xiaohongshu')
  const [accUsername, setAccUsername] = useState('')
  const [editingClient, setEditingClient] = useState(false)
  const [editName, setEditName] = useState('')
  const [editIndustry, setEditIndustry] = useState('')
  const [editDesc, setEditDesc] = useState('')

  const clientQuery = useQuery({
    queryKey: ['clients', id],
    queryFn: () => clientApi.get(id!),
    enabled: !!id,
  })

  const accountsQuery = useQuery({
    queryKey: ['accounts', { client_id: id }],
    queryFn: () => accountApi.list({ client_id: id }),
    enabled: !!id,
  })

  const updateClientMutation = useMutation({
    mutationFn: () =>
      clientApi.update(id!, {
        name: editName,
        industry: editIndustry || undefined,
        description: editDesc || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients', id] })
      setEditingClient(false)
    },
  })

  const createAccountMutation = useMutation({
    mutationFn: () =>
      accountApi.create({ client_id: id!, platform: accPlatform, username: accUsername }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      setShowAddAccount(false)
      setAccUsername('')
    },
  })

  const deleteAccountMutation = useMutation({
    mutationFn: (accId: string) => accountApi.delete(accId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['accounts'] }),
  })

  const client = clientQuery.data?.data
  const accounts = accountsQuery.data?.data?.items || []

  const startEdit = () => {
    if (!client) return
    setEditName(client.name)
    setEditIndustry(client.industry || '')
    setEditDesc(client.description || '')
    setEditingClient(true)
  }

  if (clientQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
      </div>
    )
  }

  if (!client) {
    return (
      <EmptyState
        icon={<User className="h-10 w-10" />}
        title="客户不存在"
        action={
          <button
            onClick={() => navigate('/clients')}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white"
          >
            返回列表
          </button>
        }
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/clients')}
          className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{client.name}</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            {client.industry || '未设置行业'} · 创建于 {formatDate(client.created_at)}
          </p>
        </div>
        <button
          onClick={startEdit}
          className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Edit2 className="h-4 w-4" />
          编辑
        </button>
      </div>

      {/* Client info */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">客户信息</h3>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <p className="text-xs text-gray-400">名称</p>
            <p className="mt-1 text-sm text-gray-900">{client.name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">行业</p>
            <p className="mt-1 text-sm text-gray-900">{client.industry || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400">描述</p>
            <p className="mt-1 text-sm text-gray-900">{client.description || '-'}</p>
          </div>
        </div>
      </div>

      {/* Accounts */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">
            关联账号 ({accounts.length})
          </h3>
          <button
            onClick={() => setShowAddAccount(true)}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-3.5 w-3.5" />
            添加账号
          </button>
        </div>

        <div className="mt-4 space-y-2">
          {accounts.length === 0 && (
            <p className="py-6 text-center text-sm text-gray-400">暂无关联账号</p>
          )}
          {accounts.map((acc: Account) => (
            <div
              key={acc.id}
              className="flex items-center justify-between rounded-lg border border-gray-100 p-3"
            >
              <div className="flex items-center gap-3">
                <PlatformBadge platform={acc.platform} />
                <div>
                  <p className="text-sm font-medium text-gray-900">{acc.username}</p>
                  <p className="text-xs text-gray-400">
                    {acc.is_logged_in ? '已登录' : '未登录'} ·{' '}
                    <span
                      className={
                        acc.status === 'active'
                          ? 'text-green-500'
                          : acc.status === 'suspended'
                            ? 'text-red-500'
                            : 'text-gray-400'
                      }
                    >
                      {acc.status === 'active' ? '活跃' : acc.status === 'suspended' ? '已停用' : '未激活'}
                    </span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => deleteAccountMutation.mutate(acc.id)}
                className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Add Account Modal */}
      <Modal open={showAddAccount} onClose={() => setShowAddAccount(false)} title="添加账号">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (!accUsername.trim()) return
            createAccountMutation.mutate()
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700">平台</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {PLATFORMS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setAccPlatform(p.id)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    accPlatform === p.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">用户名 *</label>
            <input
              type="text"
              value={accUsername}
              onChange={(e) => setAccUsername(e.target.value)}
              placeholder="平台账号用户名"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              required
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowAddAccount(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={createAccountMutation.isPending || !accUsername.trim()}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createAccountMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              添加
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Client Modal */}
      <Modal open={editingClient} onClose={() => setEditingClient(false)} title="编辑客户">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            updateClientMutation.mutate()
          }}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700">名称 *</label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">行业</label>
            <input
              type="text"
              value={editIndustry}
              onChange={(e) => setEditIndustry(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">描述</label>
            <textarea
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setEditingClient(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={updateClientMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {updateClientMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              保存
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
