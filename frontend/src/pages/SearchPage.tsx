import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { searchApi } from '../services/api'
import { PLATFORMS } from '../components/ui/PlatformBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { Search, TrendingUp, ExternalLink, ThumbsUp, MessageCircle, Eye, Loader2 } from 'lucide-react'
import { cn } from '../lib/utils'
import type { SearchPost, TrendingItem } from '../types'

type Tab = 'search' | 'trending'

export function SearchPage() {
  const [tab, setTab] = useState<Tab>('search')
  const [platform, setPlatform] = useState('xiaohongshu')
  const [keyword, setKeyword] = useState('')
  const [sort, setSort] = useState('hot')

  const searchMutation = useMutation({
    mutationFn: () => searchApi.search(platform, keyword, 20, sort),
  })

  const trendingQuery = useQuery({
    queryKey: ['trending', platform],
    queryFn: () => searchApi.trending(platform),
    enabled: tab === 'trending',
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!keyword.trim()) return
    searchMutation.mutate()
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">热点搜索</h1>
        <p className="mt-1 text-sm text-gray-500">搜索各平台内容，发现热点趋势</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {([['search', '内容搜索', Search], ['trending', '热榜趋势', TrendingUp]] as const).map(
          ([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors',
                tab === id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          )
        )}
      </div>

      {/* Platform selector */}
      <div className="flex flex-wrap gap-2">
        {PLATFORMS.map((p) => (
          <button
            key={p.id}
            onClick={() => setPlatform(p.id)}
            className={cn(
              'rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
              platform === p.id
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            {p.name}
          </button>
        ))}
      </div>

      {tab === 'search' && (
        <>
          {/* Search form */}
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="输入搜索关键词..."
                className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="hot">最热</option>
              <option value="latest">最新</option>
              <option value="relevant">最相关</option>
            </select>
            <button
              type="submit"
              disabled={searchMutation.isPending || !keyword.trim()}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {searchMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              搜索
            </button>
          </form>

          {/* Search results */}
          {searchMutation.data && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">
                找到 {searchMutation.data.total} 条结果
                <span className="ml-2 text-xs text-gray-400">
                  搜索于 {new Date(searchMutation.data.searched_at).toLocaleTimeString('zh-CN')}
                </span>
              </p>
              {searchMutation.data.posts.map((post: SearchPost) => (
                <PostCard key={post.post_id} post={post} />
              ))}
            </div>
          )}

          {searchMutation.isError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
              搜索失败: {(searchMutation.error as Error).message}
            </div>
          )}

          {!searchMutation.data && !searchMutation.isPending && (
            <EmptyState
              icon={<Search className="h-10 w-10" />}
              title="输入关键词开始搜索"
              description="支持搜索各平台的热门内容"
            />
          )}
        </>
      )}

      {tab === 'trending' && (
        <div className="space-y-3">
          {trendingQuery.isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          )}
          {trendingQuery.data?.trending?.map((item: TrendingItem, i: number) => (
            <div
              key={i}
              className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-blue-200"
            >
              <span
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold',
                  i < 3 ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
                )}
              >
                {item.rank || i + 1}
              </span>
              <div className="flex-1">
                <p className="font-medium text-gray-900">{item.topic}</p>
                <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                  <span>热度 {item.heat}</span>
                  <span
                    className={
                      item.trend === 'up'
                        ? 'text-red-500'
                        : item.trend === 'down'
                          ? 'text-green-500'
                          : 'text-gray-400'
                    }
                  >
                    {item.trend === 'up' ? '↑ 上升' : item.trend === 'down' ? '↓ 下降' : '— 持平'}
                  </span>
                </div>
              </div>
            </div>
          ))}
          {trendingQuery.isError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
              获取热榜失败: {(trendingQuery.error as Error).message}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PostCard({ post }: { post: SearchPost }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 transition-colors hover:border-blue-200">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-gray-900">{post.title || '无标题'}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-gray-500">{post.content}</p>
          <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
            <span>{post.author}</span>
            {post.publish_time && <span>{post.publish_time}</span>}
          </div>
        </div>
        {post.url && (
          <a
            href={post.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-blue-500"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>
      <div className="mt-3 flex items-center gap-5 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <ThumbsUp className="h-3 w-3" /> {post.likes}
        </span>
        <span className="flex items-center gap-1">
          <MessageCircle className="h-3 w-3" /> {post.comments}
        </span>
        <span className="flex items-center gap-1">
          <Eye className="h-3 w-3" /> {post.views}
        </span>
      </div>
    </div>
  )
}
