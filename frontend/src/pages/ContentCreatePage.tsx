import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { crewExecutionApi } from '../services/api'
import { CrewProgressTracker } from '../components/crew/CrewProgressTracker'
import { SubagentWorkflow } from '../components/crew/SubagentWorkflow'
import { PlatformBadge, PLATFORMS } from '../components/ui/PlatformBadge'
import { Sparkles, FileText, Send, Check, ClipboardCheck } from 'lucide-react'

const CONTENT_TYPES = [
  { value: 'article', label: '图文文章' },
  { value: 'short_post', label: '短文/动态' },
  { value: 'video_script', label: '视频脚本' },
]

const RESEARCH_DEPTHS = [
  { value: 'basic', label: '快速' },
  { value: 'standard', label: '标准' },
  { value: 'deep', label: '深度' },
]

export function ContentCreatePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [topic, setTopic] = useState('')
  const [platform, setPlatform] = useState('xiaohongshu')
  const [contentType, setContentType] = useState('article')
  const [researchDepth, setResearchDepth] = useState('standard')
  const [viralCategory, setViralCategory] = useState('')
  const [brandVoice, setBrandVoice] = useState('专业但不失亲和')
  const [executionId, setExecutionId] = useState<string | null>(null)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [saved, setSaved] = useState(false)

  const startMutation = useMutation({
    mutationFn: () =>
      crewExecutionApi.startContent({
        topic,
        target_platform: platform,
        content_type: contentType,
        research_depth: researchDepth,
        viral_category: viralCategory || undefined,
        brand_voice: brandVoice,
      }),
    onSuccess: (data) => {
      setExecutionId(data.execution_id)
      setResult(null)
    },
  })

  const canStart = topic.trim().length > 0 && !startMutation.isPending && !executionId

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">内容创作</h1>
        <p className="mt-1 text-sm text-gray-500">AI 驱动的内容研究与创作流水线</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Form */}
        <div className="space-y-4 lg:col-span-2">
          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
            {/* Topic */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">主题</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="输入创作主题，如：AI 创业的 5 个关键建议"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Platform */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">目标平台</label>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.filter(p => p.id !== 'bilibili').map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPlatform(p.id)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      platform === p.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Content Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">内容类型</label>
              <select
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                {CONTENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Research Depth */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">研究深度</label>
              <div className="flex gap-2">
                {RESEARCH_DEPTHS.map((d) => (
                  <button
                    key={d.value}
                    onClick={() => setResearchDepth(d.value)}
                    className={`flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      researchDepth === d.value
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Viral Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">爆款垂类（可选）</label>
              <input
                type="text"
                value={viralCategory}
                onChange={(e) => setViralCategory(e.target.value)}
                placeholder="如：职场、美妆、科技"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Brand Voice */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">品牌调性</label>
              <input
                type="text"
                value={brandVoice}
                onChange={(e) => setBrandVoice(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            {/* Start button */}
            <button
              onClick={() => startMutation.mutate()}
              disabled={!canStart}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              <Sparkles className="h-4 w-4" />
              {startMutation.isPending ? '启动中...' : '开始创作'}
            </button>

            {startMutation.isError && (
              <p className="text-xs text-red-500">启动失败: {String(startMutation.error)}</p>
            )}
          </div>
        </div>

        {/* Result area */}
        <div className="space-y-4 lg:col-span-3">
          {/* Progress — SubAgent 工作流 + 传统进度 */}
          {executionId && (
            <div className="space-y-4">
              <SubagentWorkflow executionId={executionId} />
              <CrewProgressTracker
                executionId={executionId}
                onComplete={(r) => {
                  setResult(r)
                  setExecutionId(null)
                }}
                onError={() => setExecutionId(null)}
              />
            </div>
          )}

          {/* Result preview */}
          {result && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">
                  {(result.title as string) || '创作结果'}
                </h2>
                <PlatformBadge platform={platform} />
              </div>

              {/* Review scores */}
              {result.review ? (
                <div className="flex gap-3">
                  {(['overall_score', 'quality_score', 'compliance_score', 'spread_score'] as const).map((key) => {
                    const review = result.review as Record<string, number>
                    const labels: Record<string, string> = {
                      overall_score: '综合',
                      quality_score: '质量',
                      compliance_score: '合规',
                      spread_score: '传播',
                    }
                    return (
                      <div key={key} className="rounded-lg bg-gray-50 px-3 py-1.5 text-center">
                        <div className="text-xs text-gray-500">{labels[key]}</div>
                        <div className="text-sm font-bold text-gray-900">{String(review[key] ?? '-')}</div>
                      </div>
                    )
                  })}
                </div>
              ) : null}

              {/* Content */}
              <div className="prose prose-sm max-h-96 overflow-y-auto rounded-lg bg-gray-50 p-4">
                <pre className="whitespace-pre-wrap text-sm text-gray-700">
                  {String(result.content || '')}
                </pre>
              </div>

              {/* Tags */}
              {result.tags ? (
                <div className="flex flex-wrap gap-1">
                  {(result.tags as string[]).map((tag) => (
                    <span key={tag} className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
                      #{tag}
                    </span>
                  ))}
                </div>
              ) : null}

              {/* Actions */}
              <div className="flex gap-2 border-t border-gray-100 pt-3">
                <button
                  onClick={() => {
                    queryClient.invalidateQueries({ queryKey: ['content-drafts'] })
                    setSaved(true)
                  }}
                  disabled={saved}
                  className="flex items-center gap-1.5 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
                >
                  {saved ? <Check className="h-3.5 w-3.5 text-green-600" /> : <FileText className="h-3.5 w-3.5" />}
                  {saved ? '已保存' : '保存草稿'}
                </button>
                {(result.review_draft_id as string) && (
                  <button
                    onClick={() => navigate(`/content/${result.review_draft_id as string}/review`)}
                    className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700"
                  >
                    <ClipboardCheck className="h-3.5 w-3.5" />
                    进入审核
                  </button>
                )}
                <button
                  onClick={() => {
                    const draftId = result.draft_id as string
                    if (draftId) navigate(`/publish?draft=${draftId}`)
                    else navigate('/publish')
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                >
                  <Send className="h-3.5 w-3.5" />
                  发布到平台
                </button>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!executionId && !result && (
            <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 py-16 text-center">
              <Sparkles className="mb-3 h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-500">填写左侧表单，点击"开始创作"</p>
              <p className="mt-1 text-xs text-gray-400">AI 将自动研究热点、分析爆款、创作内容</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
