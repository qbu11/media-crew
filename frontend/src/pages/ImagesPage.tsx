import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { imageApi } from '../services/api'
import { PLATFORMS } from '../components/ui/PlatformBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { Image, Loader2, Download, Clock } from 'lucide-react'
import { cn } from '../lib/utils'
import type { ImagePlatform, ColorScheme, ImageType } from '../types'

const COLOR_SCHEMES: { id: ColorScheme; name: string; desc: string }[] = [
  { id: 'tech', name: '科技蓝', desc: '专业科技风格' },
  { id: 'business', name: '商务金', desc: '高端商务风格' },
  { id: 'vibrant', name: '活力橙', desc: '年轻活力风格' },
  { id: 'minimal', name: '极简灰', desc: '简约现代风格' },
]

const IMAGE_TYPES: { id: ImageType; name: string; desc: string }[] = [
  { id: 'cover', name: '封面图', desc: '文章/笔记封面' },
  { id: 'comparison', name: '对比图', desc: '数据对比展示' },
  { id: 'highlights', name: '亮点图', desc: '核心亮点展示' },
  { id: 'summary', name: '总结图', desc: '内容总结概览' },
]

export function ImagesPage() {
  const queryClient = useQueryClient()
  const [platform, setPlatform] = useState<ImagePlatform>('xiaohongshu')
  const [colorScheme, setColorScheme] = useState<ColorScheme>('tech')
  const [imageType, setImageType] = useState<ImageType>('cover')
  const [title, setTitle] = useState('')
  const [subtitle, setSubtitle] = useState('')
  const [tags, setTags] = useState('')

  const historyQuery = useQuery({
    queryKey: ['images', 'history', platform],
    queryFn: () => imageApi.history(platform, 20),
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      imageApi.generateSingle({
        platform,
        color_scheme: colorScheme,
        image_type: imageType,
        data: {
          title: title || '示例标题',
          subtitle: subtitle || '示例副标题',
          tags: tags ? tags.split(',').map((t) => t.trim()) : ['标签1', '标签2'],
          items: [
            { label: '要点一', value: '描述内容' },
            { label: '要点二', value: '描述内容' },
            { label: '要点三', value: '描述内容' },
          ],
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['images', 'history'] })
    },
  })

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault()
    generateMutation.mutate()
  }

  const imagePlatforms = PLATFORMS.filter((p) =>
    ['xiaohongshu', 'weibo', 'zhihu', 'bilibili', 'douyin'].includes(p.id)
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">图片生成</h1>
        <p className="mt-1 text-sm text-gray-500">为各平台生成配图、封面和信息图</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Form */}
        <form onSubmit={handleGenerate} className="space-y-5 lg:col-span-2">
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            {/* Platform */}
            <div>
              <label className="block text-sm font-medium text-gray-700">目标平台</label>
              <div className="mt-2 flex flex-wrap gap-2">
                {imagePlatforms.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setPlatform(p.id as ImagePlatform)}
                    className={cn(
                      'rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                      platform === p.id
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Color scheme */}
            <div>
              <label className="block text-sm font-medium text-gray-700">配色方案</label>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {COLOR_SCHEMES.map((cs) => (
                  <button
                    key={cs.id}
                    type="button"
                    onClick={() => setColorScheme(cs.id)}
                    className={cn(
                      'rounded-lg border p-2.5 text-left text-xs transition-colors',
                      colorScheme === cs.id
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    )}
                  >
                    <p className="font-medium text-gray-900">{cs.name}</p>
                    <p className="text-gray-400">{cs.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Image type */}
            <div>
              <label className="block text-sm font-medium text-gray-700">图片类型</label>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {IMAGE_TYPES.map((it) => (
                  <button
                    key={it.id}
                    type="button"
                    onClick={() => setImageType(it.id)}
                    className={cn(
                      'rounded-lg border p-2.5 text-left text-xs transition-colors',
                      imageType === it.id
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    )}
                  >
                    <p className="font-medium text-gray-900">{it.name}</p>
                    <p className="text-gray-400">{it.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Content fields */}
            <div>
              <label className="block text-sm font-medium text-gray-700">标题</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="图片主标题"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">副标题</label>
              <input
                type="text"
                value={subtitle}
                onChange={(e) => setSubtitle(e.target.value)}
                placeholder="图片副标题"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">标签</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="逗号分隔，如: AI, 创业, 效率"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={generateMutation.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {generateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Image className="h-4 w-4" />
              )}
              生成图片
            </button>

            {generateMutation.isSuccess && (
              <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
                图片已生成: {generateMutation.data.data.filepath}
              </div>
            )}
            {generateMutation.isError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
                生成失败: {(generateMutation.error as Error).message}
              </div>
            )}
          </div>
        </form>

        {/* History */}
        <div className="lg:col-span-3">
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="text-base font-semibold text-gray-900">历史生成</h3>
            <div className="mt-4 space-y-3">
              {historyQuery.isLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                </div>
              )}
              {historyQuery.data?.data?.length === 0 && (
                <EmptyState
                  icon={<Image className="h-8 w-8" />}
                  title="暂无生成记录"
                  description="生成图片后会在这里显示"
                />
              )}
              {historyQuery.data?.data?.map((img, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg border border-gray-100 p-3 hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
                      <Image className="h-5 w-5 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{img.filename}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span>{img.platform}</span>
                        <span>{(img.size / 1024).toFixed(0)} KB</span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(img.created_at * 1000).toLocaleDateString('zh-CN')}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Download className="h-4 w-4 text-gray-400" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
