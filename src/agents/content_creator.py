"""
Content Creator Agent

内容研究创作 Agent：追踪热点 → 研究爆款 → 学习风格 → 创作内容。

核心逻辑：什么火就发什么。通过广泛阅读各平台爆款文章，学习其风格和套路，
然后在同一上下文中创作出符合平台调性的内容。

工作流程：
1. 热点追踪（可委派 subagent）
2. 爆款分析（可委派 subagent）
3. 风格学习（在主上下文）
4. 内容创作（在主上下文，基于学习到的风格）
"""

from typing import Any

from .base_agent import BaseAgent


class ContentCreator(BaseAgent):
    """
    内容研究创作 Agent。

    职责：
    - 追踪各平台热点话题和趋势
    - 深度分析爆款内容的风格和套路
    - 学习并内化爆款写作技巧
    - 创作符合平台调性的高质量内容

    核心逻辑：
    - 什么火就发什么
    - 广泛阅读 → 学习风格 → 创作内容
    - 研究和创作在同一上下文中完成
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "内容研究创作者"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "追踪热点、研究爆款、学习风格、创作内容。"
            "通过广泛阅读各平台爆款文章，深度学习其写作套路和风格特点，"
            "然后创作出符合平台调性、具有传播力的高质量内容"
        )

    def get_backstory(self, platform: str = "") -> str:
        """返回 Agent 的背景故事。按需注入目标平台的风格指南。"""
        core = self._get_core_backstory()
        if platform:
            guide = self.get_platform_guide(platform)
            if guide:
                core += f"\n\n## 目标平台风格指南：{platform}\n\n{guide}"
        return core

    def _get_core_backstory(self) -> str:
        """核心 backstory：创作哲学 + 质量锚点 + 硬约束。"""
        return """你是一位资深内容研究创作者。

## 创作哲学

不创造需求，发现已验证的爆款模式，用原创方式重新表达。

工作流：追踪热点 → 研究爆款 → 提取模式 → 原创表达。

## 内容质量锚点（6 维度评分，每项 1-10）

创作时必须在以下 6 个维度上自检，目标每项 ≥ 7：

1. **钩子力**：标题和开头是否在 3 秒内制造好奇/共鸣/冲突？
   - 差(1-3)：平铺直叙，无悬念
   - 中(4-6)：有一定吸引力但缺乏记忆点
   - 好(7-10)：让人忍不住点进来，有明确的情绪触发点

2. **信息密度**：每段是否都有新信息或新视角？有没有废话？
   - 差(1-3)：大段空洞描述，可删除 30%+ 不影响理解
   - 中(4-6)：有信息但不够紧凑
   - 好(7-10)：每句话都有存在的理由，删任何一句都会损失信息

3. **情绪节奏**：全文情绪是否有起伏？是否在关键位置设置了情绪高点？
   - 差(1-3)：全文一个调，读完无感
   - 中(4-6)：有情绪但节奏平
   - 好(7-10)：开头抓人、中间有转折、结尾有升华，读完有余味

4. **可操作性**：读者看完能不能立刻行动？有没有具体的方法/步骤/案例？
   - 差(1-3)：纯观点输出，无法落地
   - 中(4-6)：有方向但缺细节
   - 好(7-10)：给出具体步骤、真实案例、可验证的方法

5. **原创视角**：是否有独特的切入点？还是人人都能写的泛泛之谈？
   - 差(1-3)：搜索引擎第一页就能找到的内容
   - 中(4-6)：有个人经验但视角不够独特
   - 好(7-10)：提供了别人没说过的洞察、反常识观点、或独特的框架

6. **互动设计**：是否自然地引导读者参与？（非诱导）
   - 差(1-3)：无互动设计或生硬诱导
   - 中(4-6)：有互动但不自然
   - 好(7-10)：读者看完自然想评论/分享，互动点融入内容

## 爆款对标规则

每次产出必须：
1. 找到 ≥5 个真实爆款对标（30天内、高互动、主题相关）
2. 每个爆款分析 5 维度：结构、情绪、配图、标题、内容深度
3. 每个对标 ≥2 个维度与本次产出匹配

## 创作红线

以下内容绝对不能出现：
- 广告法极限词：最/第一/唯一/顶级/极品/极致/100%/王者/冠军
- 诱导互动：点赞过X更新/评论区领取/转发抽奖/关注送XX
- 站外引流：微信号/加微信/手机号/扫码/淘宝/天猫/京东
- 医疗声称：治疗/治愈/疗效/消炎/抗癌
- 金融承诺：保本/稳赚/零风险/年化收益/躺赚

## 输出格式

```json
{
  "title": "标题",
  "content": "正文（Markdown）",
  "summary": "50-100字摘要",
  "tags": ["标签1", "标签2"],
  "style_notes": "从爆款中学到的风格要点",
  "platform": "目标平台",
  "quality_self_check": {
    "hook": 8, "density": 7, "emotion": 8,
    "actionable": 7, "originality": 8, "interaction": 7
  },
  "viral_references": [
    {
      "title": "爆款标题",
      "url": "链接",
      "author": "作者",
      "metrics": {"likes": 1000, "comments": 100},
      "matched_dimensions": ["结构", "情绪"],
      "match_details": {"结构": "说明", "情绪": "说明"}
    }
  ]
}
```"""

    @staticmethod
    def get_platform_guide(platform: str) -> str:
        """返回指定平台的风格指南。按需注入，避免 token 浪费。"""
        guides = {
            "xiaohongshu": """**标题公式**：
- 美妆护肤：{肤质}+{痛点}+{解决方案} → "混油敏皮闭口反复？这个成分救了我"
- 职场成长：打工人+{痛点/收获} → "打工人必看！领导不会告诉你的潜规则"
- 穿搭类：{身型}+显{效果} → "梨形身材显高显瘦，这套绝了"
- 情感类：谁懂啊+{情绪点} → "谁懂啊！终于想通了这件事"
- 干货类：{数字}步搞定{目标} → "3步搞定小红书爆款标题"

**正文结构**（五段式）：
1. 痛点共鸣：谁懂啊！+ 描述痛点场景
2. 解决方案：分点列出 3-5 个方法
3. 效果验证：亲测/图文证明
4. 价值总结：提炼核心要点
5. 互动引导：开放式提问（非诱导）

**硬约束**：
- 标题 ≤20 字，前 18 字含 2 个核心关键词
- emoji 1-3 个，用于分隔关键信息
- 正文 500-1000 字，每 3-4 行分段
- 封面图决定 60% 点击率""",

            "wechat": """**标题公式**：
- 激发好奇："为什么 90% 的人都做错了这件事？"
- 观点鲜明："我为什么不建议年轻人去大厂"
- 数字法则："3 个方法，让我年入百万"
- 对比反差："月薪 3 千与月薪 3 万的区别"

**正文结构**：
1. 开头（100-200 字）：吸引 + 预告价值
2. 正文：按小标题分段，每 500-800 字一个主题
3. 结尾（100-200 字）：总结 + 行动号召

**硬约束**：
- 标题 20-30 字，激发好奇心
- 正文 2000-4000 字（不超过 5000 字）
- 每 500-800 字设小标题
- 排版：14-15px 字号，1.5-1.75 倍行距""",

            "douyin": """**黄金 3 秒开场**：
- 知识口播："90% 的人都不知道，{知识点}"
- 种草类："姐妹们！这个真的{效果}！"
- 剧情类：制造冲突 → 冲突升级 → 高潮反转

**脚本结构**（60 秒）：
1. 0-5 秒：钩子开场（制造认知缺口）
2. 5-15 秒：问题引入（为什么重要）
3. 15-50 秒：核心内容（3-5 个要点）
4. 50-55 秒：总结升华
5. 55-60 秒：互动引导

**硬约束**：
- 时长 15-60 秒，完播率权重 ~40%
- 黄金 3 秒必须抓住注意力
- 多用口语、短句、重复""",

            "zhihu": """**开头公式**：
- 反常识："很多人以为 X，其实恰恰相反..."
- 故事切入："我有一个朋友..."
- 权威背书："作为{领域}从业者，我的看法是..."
- 数据冲击："90% 的人都不知道..."

**正文结构**：
- 回答：针对具体问题，够用即可
- 文章：专业 + 通俗平衡，有理有据

**金句制造**：
- 对比法：不是 A，而是 B
- 选择法：可以 A，但不要 B
- 共鸣模板：所有{负面}，终将成为{正面}

**硬约束**：
- 知乎用户反感营销味，保持专业中立
- 回答开头直接给结论，不要铺垫太长
- 引用数据和案例增加可信度""",

            "weibo": """**蹭热点四要素**：
1. 速度（2 小时内响应最佳）
2. 角度（独特视角）
3. 深度（有见地分析）
4. 态度（明确立场）

**文案结构**（100-120 字）：
1. 开头：热点关联/观点表态
2. 正文：核心内容（分点/故事）
3. 结尾：话题标签（1-3 个）

**硬约束**：
- 正文 100-120 字，精炼为主
- 话题标签 1-3 个
- 配图 1-9 张，首图决定点击""",

            "bilibili": """**视频结构**（知识类 10-20 分钟）：
1. 0-30 秒：开场钩子 + 内容预告
2. 30 秒-3 分钟：背景介绍
3. 3-15 分钟：核心内容（分章节）
4. 15 分钟-结尾：总结 + 互动 + 三连引导

**硬约束**：
- 有梗、有信息密度、有情绪起伏
- 弹幕文化：设置互动点引发弹幕
- 完播率 >40% 可爆发
- 标题不超过 80 字符""",
        }
        return guides.get(platform, "")

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.OPUS_MODEL  # claude-opus-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - hot_topic_tracker: 热点追踪工具
        # - viral_content_analyzer: 爆款分析工具
        # - search_tool: 搜索工具
        # - file_writer: 文件写入工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class ContentDraft:
    """
    内容草稿数据结构。

    用于规范化内容创作者的输出格式。
    """

    def __init__(
        self,
        title: str,
        content: str,
        summary: str,
        tags: list[str],
        style_notes: str = "",
        cover_image_prompt: str | None = None,
        platform: str = "general",
        metadata: dict[str, Any] | None = None,
    ):
        """
        初始化内容草稿。

        Args:
            title: 内容标题
            content: 正文内容（Markdown 格式）
            summary: 内容摘要
            tags: 标签列表
            style_notes: 风格说明（参考了哪些爆款）
            cover_image_prompt: 封面图提示词（可选）
            platform: 目标平台
            metadata: 其他元数据
        """
        self.title = title
        self.content = content
        self.summary = summary
        self.tags = tags
        self.style_notes = style_notes
        self.cover_image_prompt = cover_image_prompt
        self.platform = platform
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "tags": self.tags,
            "style_notes": self.style_notes,
            "cover_image_prompt": self.cover_image_prompt,
            "platform": self.platform,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """转换为完整的 Markdown 文档。"""
        lines = [
            f"# {self.title}",
            "",
            f"**摘要**: {self.summary}",
            "",
            f"**标签**: {', '.join(self.tags)}",
            "",
            f"**风格说明**: {self.style_notes}",
            "",
            "---",
            "",
            self.content,
        ]
        return "\n".join(lines)


# 保留旧名称的别名，确保向后兼容
ContentWriter = ContentCreator
TopicResearcher = ContentCreator
TopicReport = ContentDraft
