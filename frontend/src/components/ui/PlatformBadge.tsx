import type { PlatformId } from '../../types'

const PLATFORM_MAP: Record<string, { name: string; color: string }> = {
  xiaohongshu: { name: '小红书', color: 'bg-red-100 text-red-700' },
  wechat: { name: '微信公众号', color: 'bg-green-100 text-green-700' },
  weibo: { name: '微博', color: 'bg-orange-100 text-orange-700' },
  zhihu: { name: '知乎', color: 'bg-blue-100 text-blue-700' },
  douyin: { name: '抖音', color: 'bg-pink-100 text-pink-700' },
  bilibili: { name: 'B站', color: 'bg-cyan-100 text-cyan-700' },
}

export function PlatformBadge({ platform, size }: { platform: PlatformId | string; size?: 'sm' | 'md' | 'lg' }) {
  const info = PLATFORM_MAP[platform] || { name: platform, color: 'bg-gray-100 text-gray-700' }
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-0.5 text-xs'
  return (
    <span className={`inline-flex items-center rounded-full font-medium ${info.color} ${sizeClass}`}>
      {info.name}
    </span>
  )
}

export function getPlatformName(platform: string): string {
  return PLATFORM_MAP[platform]?.name || platform
}

export const PLATFORMS: { id: PlatformId; name: string }[] = [
  { id: 'xiaohongshu', name: '小红书' },
  { id: 'wechat', name: '微信公众号' },
  { id: 'weibo', name: '微博' },
  { id: 'zhihu', name: '知乎' },
  { id: 'douyin', name: '抖音' },
  { id: 'bilibili', name: 'B站' },
]
