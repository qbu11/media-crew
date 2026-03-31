"""
爆款对标系统

核心逻辑：每次内容产出必须有真实爆款对标，防止"凭空创作"。
架构设计：使用 subagent 搜索爆款，结果结构化存储，主上下文只保留关键信息。
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Any


@dataclass
class ViralReference:
    """单个爆款对标内容"""

    platform: str  # 平台
    title: str  # 标题
    url: str  # 原文链接
    author: str  # 作者
    metrics: dict[str, int]  # 数据指标（点赞/评论/转发等）

    # 结构化分析（5个维度）
    structure_analysis: dict[str, Any] = field(default_factory=dict)  # 结构分析
    emotion_analysis: dict[str, Any] = field(default_factory=dict)  # 情绪分析
    image_analysis: dict[str, Any] = field(default_factory=dict)  # 配图分析
    title_analysis: dict[str, Any] = field(default_factory=dict)  # 标题分析
    depth_analysis: dict[str, Any] = field(default_factory=dict)  # 内容深度分析

    # 原文摘要（用于验证）
    content_summary: str = ""
    key_phrases: list[str] = field(default_factory=list)  # 关键句式

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "metrics": self.metrics,
            "structure_analysis": self.structure_analysis,
            "emotion_analysis": self.emotion_analysis,
            "image_analysis": self.image_analysis,
            "title_analysis": self.title_analysis,
            "depth_analysis": self.depth_analysis,
            "content_summary": self.content_summary,
            "key_phrases": self.key_phrases,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ViralReference":
        """从字典创建 ViralReference 实例"""
        return cls(
            platform=data.get("platform", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            author=data.get("author", ""),
            metrics=data.get("metrics", {}),
            structure_analysis=data.get("structure_analysis", {}),
            emotion_analysis=data.get("emotion_analysis", {}),
            image_analysis=data.get("image_analysis", {}),
            title_analysis=data.get("title_analysis", {}),
            depth_analysis=data.get("depth_analysis", {}),
            content_summary=data.get("content_summary", ""),
            key_phrases=data.get("key_phrases", []),
        )


@dataclass
class MatchResult:
    """匹配验证结果"""

    viral_ref: ViralReference  # 对标的爆款
    matched_dimensions: list[str]  # 匹配的维度
    match_details: dict[str, str]  # 每个维度的匹配说明
    match_score: float  # 匹配度评分 (0-1)

    def to_dict(self) -> dict:
        return {
            "viral_ref": self.viral_ref.to_dict(),
            "matched_dimensions": self.matched_dimensions,
            "match_details": self.match_details,
            "match_score": self.match_score,
        }

    @property
    def is_valid(self) -> bool:
        """检查是否是有效对标（至少2个维度匹配）"""
        return len(self.matched_dimensions) >= 2


@dataclass
class ViralReferenceReport:
    """爆款对标报告（主上下文只保留这个结构化摘要）"""

    platform: str
    created_content_title: str  # 本次产出的标题
    viral_references: list[ViralReference]  # 找到的爆款列表
    match_results: list[MatchResult]  # 匹配验证结果
    passed: bool  # 是否通过（至少5个爆款，至少2个维度匹配）
    validation_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "created_content_title": self.created_content_title,
            "viral_references": [v.to_dict() for v in self.viral_references],
            "match_results": [m.to_dict() for m in self.match_results],
            "passed": self.passed,
            "validation_time": self.validation_time,
            "summary": self.get_summary(),
        }

    def get_summary(self) -> str:
        """生成简短摘要（用于主上下文）"""
        lines = [
            "## 爆款对标验证报告",
            "",
            f"**平台**: {self.platform}",
            f"**产出标题**: {self.created_content_title}",
            f"**验证结果**: {'✅ 通过' if self.passed else '❌ 未通过'}",
            "",
            f"### 爆款对标列表 ({len(self.viral_references)} 个)",
        ]

        for i, ref in enumerate(self.viral_references[:5], 1):
            match = self.match_results[i - 1] if i <= len(self.match_results) else None
            match_info = ""
            if match:
                match_info = f" | 匹配维度: {', '.join(match.matched_dimensions)}"
            lines.append(
                f"{i}. **{ref.title}** (作者: {ref.author})"
                f"\n   - 数据: {ref.metrics}"
                f"\n   - 链接: {ref.url}"
                f"{match_info}"
            )

        return "\n".join(lines)

    @classmethod
    def from_content_draft(
        cls,
        platform: str,
        content_title: str,
        viral_references_data: list[dict[str, Any]],
    ) -> "ViralReferenceReport":
        """
        从内容草稿中的爆款对标数据创建报告

        Args:
            platform: 平台
            content_title: 内容标题
            viral_references_data: 爆款对标数据列表

        Returns:
            ViralReferenceReport 实例
        """
        viral_refs = []
        match_results = []

        for ref_data in viral_references_data:
            # 创建 ViralReference
            viral_ref = ViralReference.from_dict(ref_data)
            viral_refs.append(viral_ref)

            # 创建 MatchResult
            matched_dimensions = ref_data.get("matched_dimensions", [])
            match_details = ref_data.get("match_details", {})
            match_score = ref_data.get("match_score", 0.0)

            match_result = MatchResult(
                viral_ref=viral_ref,
                matched_dimensions=matched_dimensions,
                match_details=match_details,
                match_score=match_score,
            )
            match_results.append(match_result)

        # 验证是否通过（至少5个爆款，每个至少2个维度匹配）
        valid_count = sum(1 for m in match_results if m.is_valid)
        passed = len(viral_refs) >= 5 and valid_count >= 5

        return cls(
            platform=platform,
            created_content_title=content_title,
            viral_references=viral_refs,
            match_results=match_results,
            passed=passed,
        )


class ViralReferenceValidator:
    """爆款对标验证器"""

    MIN_REFERENCES = 5  # 最少爆款对标数量
    MIN_MATCHED_DIMENSIONS = 2  # 每个爆款最少匹配维度

    @classmethod
    def validate_content_draft(
        cls, content_draft: dict[str, Any]
    ) -> dict[str, Any]:
        """
        验证内容草稿是否满足爆款对标要求

        Args:
            content_draft: 内容草稿（包含 viral_references 字段）

        Returns:
            验证结果字典
        """
        viral_refs = content_draft.get("viral_references", [])

        # 基本验证
        has_min_refs = len(viral_refs) >= cls.MIN_REFERENCES
        has_urls = all(ref.get("url") for ref in viral_refs)
        has_metrics = all(ref.get("metrics") for ref in viral_refs)

        # 维度匹配验证
        valid_refs_count = 0
        dimension_matches: dict[str, int] = {
            "structure": 0,
            "emotion": 0,
            "image": 0,
            "title": 0,
            "depth": 0,
        }

        for ref in viral_refs:
            matched = ref.get("matched_dimensions", [])
            if len(matched) >= cls.MIN_MATCHED_DIMENSIONS:
                valid_refs_count += 1
            for dim in matched:
                if dim in dimension_matches:
                    dimension_matches[dim] += 1

        # 总体通过条件
        passed = has_min_refs and has_urls and has_metrics and valid_refs_count >= cls.MIN_REFERENCES

        return {
            "passed": passed,
            "total_references": len(viral_refs),
            "valid_references": valid_refs_count,
            "has_urls": has_urls,
            "has_metrics": has_metrics,
            "dimension_matches": dimension_matches,
            "issues": cls._get_validation_issues(
                has_min_refs, has_urls, has_metrics, valid_refs_count, viral_refs
            ),
        }

    @classmethod
    def _get_validation_issues(
        cls,
        has_min_refs: bool,
        has_urls: bool,
        has_metrics: bool,
        valid_refs_count: int,
        viral_refs: list[dict],
    ) -> list[str]:
        """获取验证问题列表"""
        issues = []

        if not has_min_refs:
            issues.append(f"爆款对标数量不足，需要至少 {cls.MIN_REFERENCES} 个，当前只有 {len(viral_refs)} 个")

        if not has_urls:
            issues.append("部分爆款缺少可验证的链接")

        if not has_metrics:
            issues.append("部分爆款缺少数据指标")

        if valid_refs_count < cls.MIN_REFERENCES:
            issues.append(
                f"有效对标数量不足，需要至少 {cls.MIN_REFERENCES} 个（每个至少2个维度匹配），"
                f"当前只有 {valid_refs_count} 个"
            )

        # 检查每个爆款的匹配维度
        for i, ref in enumerate(viral_refs):
            matched = ref.get("matched_dimensions", [])
            if len(matched) < cls.MIN_MATCHED_DIMENSIONS:
                issues.append(
                    f"爆款 {i+1} ({ref.get('title', '未知')}) 只有 {len(matched)} 个维度匹配，"
                    f"需要至少 {cls.MIN_MATCHED_DIMENSIONS} 个"
                )

        return issues


# 五个维度的分析框架
DIMENSION_ANALYSIS_PROMPTS = {
    "structure": {
        "name": "结构",
        "analysis_points": [
            "开头方式（痛点引入/悬念设置/直接陈述）",
            "段落划分（数量和长度）",
            "信息密度（密集/稀疏）",
            "过渡方式（连接词/小标题/空行）",
            "结尾设计（总结/互动/悬念）",
        ],
        "match_criteria": [
            "开头方式相同或相似",
            "段落结构相似",
            "信息密度相近",
            "过渡方式有共同点",
            "结尾设计有参考",
        ],
    },
    "emotion": {
        "name": "情绪",
        "analysis_points": [
            "主要情绪（焦虑/期待/共鸣/好奇）",
            "情绪强度（强烈/温和）",
            "情绪节奏（起伏/平稳）",
            "情绪触发点（痛点/痒点/爽点）",
            "情绪收尾（治愈/焦虑/期待）",
        ],
        "match_criteria": [
            "主要情绪类型相同",
            "情绪强度相近",
            "情绪节奏有参考",
            "触发点有相似",
            "收尾情绪相同",
        ],
    },
    "image": {
        "name": "配图",
        "analysis_points": [
            "图片数量",
            "图片类型（实拍/插画/截图/混合）",
            "图片风格（专业/生活化/创意）",
            "图片与文字关系（说明/装饰/独立）",
            "封面设计（标题图/内容图/人物图）",
        ],
        "match_criteria": [
            "图片数量相近",
            "图片类型相同",
            "风格相似",
            "图文关系相似",
            "封面设计有参考",
        ],
    },
    "title": {
        "name": "标题",
        "analysis_points": [
            "标题长度",
            "核心钩子（数字/疑问/对比/情绪词）",
            "关键词位置",
            "emoji使用",
            "标点符号使用",
        ],
        "match_criteria": [
            "标题长度相近",
            "核心钩子类型相同",
            "关键词使用有参考",
            "emoji使用方式相似",
            "标点风格相似",
        ],
    },
    "depth": {
        "name": "内容深度",
        "analysis_points": [
            "内容长度",
            "信息层次（浅层/中层/深层）",
            "专业程度（小白/进阶/专业）",
            "案例/数据使用",
            "实操性（理论/实践/混合）",
        ],
        "match_criteria": [
            "内容长度相近",
            "信息层次相同",
            "专业程度匹配",
            "案例使用方式相似",
            "实操性相同",
        ],
    },
}


def get_viral_search_prompt(
    platform: str,
    topic: str,
    content_category: str | None = None,
) -> str:
    """
    生成爆款搜索 prompt（给 subagent 用）

    这个 prompt 会发给 subagent，让它广泛搜索，
    返回结构化的爆款分析结果。
    """
    category_hint = f"\n**垂类方向**: {content_category}" if content_category else ""

    return f"""
请搜索 {platform} 平台上与以下主题相关的爆款内容：

**主题**: {topic}
**目标平台**: {platform}{category_hint}

## 搜索任务

1. **搜索来源**（至少覆盖 3 个）：
   - 平台热榜/热搜
   - 同垂类头部账号最近 30 天的高赞内容
   - 相关话题下的爆款笔记/文章
   - 竞品账号的爆款内容

2. **筛选标准**：
   - 点赞/互动数 > 行业平均
   - 发布时间 < 30 天（越新越好）
   - 内容与主题相关度高

3. **找到至少 10 个候选**，然后分析其中最火爆的 5 个

## 分析要求

对每个爆款，分析以下 5 个维度：

### 1. 结构分析
- 开头方式（痛点引入/悬念设置/直接陈述/故事开场）
- 段落划分（数量和长度）
- 信息密度（密集/稀疏）
- 过渡方式（连接词/小标题/空行）
- 结尾设计（总结/互动/悬念/金句）

### 2. 情绪分析
- 主要情绪（焦虑/期待/共鸣/好奇/治愈）
- 情绪强度（强烈/温和）
- 情绪节奏（起伏/平稳）
- 情绪触发点（痛点/痒点/爽点）
- 情绪收尾（治愈/焦虑/期待）

### 3. 配图分析
- 图片数量
- 图片类型（实拍/插画/截图/混合）
- 图片风格（专业/生活化/创意）
- 图片与文字关系（说明/装饰/独立）
- 封面设计（标题图/内容图/人物图）

### 4. 标题分析
- 标题完整内容
- 标题长度（字符数）
- 核心钩子类型（数字/疑问/对比/情绪词/热点词）
- 关键词位置
- emoji使用（有/无，数量）
- 标点符号使用

### 5. 内容深度分析
- 内容总长度（字数）
- 信息层次（浅层科普/中层分析/深层洞察）
- 专业程度（小白友好/进阶内容/专业深度）
- 案例/数据使用（有/无，数量）
- 实操性（纯理论/理论+实践/纯实操）

## 输出格式

请返回 JSON 数组，每个爆款一个对象：

```json
[
  {{
    "platform": "平台名称",
    "title": "完整标题",
    "url": "原文链接",
    "author": "作者名称",
    "metrics": {{
      "likes": 点赞数,
      "comments": 评论数,
      "shares": 转发数,
      "views": 浏览数（如有）
    }},
    "structure_analysis": {{
      "opening_style": "开头方式",
      "paragraph_count": 段落数,
      "info_density": "信息密度",
      "transition_style": "过渡方式",
      "ending_style": "结尾设计"
    }},
    "emotion_analysis": {{
      "primary_emotion": "主要情绪",
      "intensity": "情绪强度",
      "rhythm": "情绪节奏",
      "trigger_point": "情绪触发点",
      "ending_emotion": "情绪收尾"
    }},
    "image_analysis": {{
      "image_count": 图片数量,
      "image_type": "图片类型",
      "style": "图片风格",
      "text_relation": "图文关系",
      "cover_design": "封面设计"
    }},
    "title_analysis": {{
      "full_title": "完整标题",
      "length": 标题长度,
      "hook_type": "核心钩子类型",
      "keyword_position": "关键词位置",
      "emoji_count": emoji数量,
      "punctuation": "标点使用"
    }},
    "depth_analysis": {{
      "content_length": 内容长度,
      "info_level": "信息层次",
      "professional_level": "专业程度",
      "case_count": 案例数量,
      "practicality": "实操性"
    }},
    "content_summary": "内容摘要（100字以内）",
    "key_phrases": ["关键句式1", "关键句式2", "关键句式3"]
  }}
]
```

## 重要提醒

- 必须是真实的爆款，提供可验证的链接
- 分析必须具体，不要泛泛而谈
- 关键句式要能直接用于创作参考
"""


def get_match_validation_prompt(
    created_content: dict[str, Any],
    viral_references: list[dict[str, Any]],
    platform: str,
) -> str:
    """
    生成匹配验证 prompt（在主上下文中执行）

    验证产出内容与爆款的匹配度。
    """
    return f"""
请验证以下内容与爆款的匹配度：

## 本次产出的内容

**平台**: {platform}
**标题**: {created_content.get('title', '')}
**正文摘要**: {created_content.get('content', '')[:500]}...

## 爆款对标列表

{json.dumps([{
    'title': v.get('title'),
    'url': v.get('url'),
    'metrics': v.get('metrics'),
    'structure': v.get('structure_analysis'),
    'emotion': v.get('emotion_analysis'),
    'image': v.get('image_analysis'),
    'title_analysis': v.get('title_analysis'),
    'depth': v.get('depth_analysis'),
} for v in viral_references], ensure_ascii=False, indent=2)}

## 匹配验证要求

对每个爆款，验证以下 5 个维度的匹配情况：

1. **结构** - 开头方式、段落划分、信息密度、过渡方式、结尾设计
2. **情绪** - 主要情绪、情绪强度、情绪节奏、触发点、收尾
3. **配图** - 图片数量、类型、风格、图文关系、封面设计
4. **标题** - 长度、钩子类型、关键词、emoji、标点
5. **内容深度** - 长度、信息层次、专业程度、案例使用、实操性

## 匹配标准

- **匹配**：该维度有明显相似或明确的参考借鉴
- **不匹配**：该维度风格差异明显

## 强制规则

- 至少需要 5 个爆款对标
- 每个爆款至少 2 个维度匹配才算有效对标
- 总体通过条件：至少 5 个有效对标

## 输出格式

```json
{{
  "passed": true/false,
  "match_results": [
    {{
      "viral_index": 0,
      "viral_title": "爆款标题",
      "matched_dimensions": ["结构", "情绪"],
      "match_details": {{
        "结构": "本次产出采用了相同的痛点引入开头...",
        "情绪": "主要情绪都是焦虑+期待，触发点相似..."
      }},
      "match_score": 0.8
    }}
  ],
  "valid_count": 有效对标数量,
  "total_analyzed": 分析的爆款总数,
  "summary": "一句话总结匹配情况"
}}
```
"""


# 平台搜索 URL 模板
PLATFORM_SEARCH_URLS = {
    "xiaohongshu": "https://www.xiaohongshu.com/search_result?keyword={keyword}",
    "weibo": "https://s.weibo.com/weibo?q={keyword}",
    "zhihu": "https://www.zhihu.com/search?type=content&q={keyword}",
    "douyin": "https://www.douyin.com/search/{keyword}",
    "bilibili": "https://search.bilibili.com/all?keyword={keyword}",
    "wechat": "https://weixin.sogou.com/weixin?type=2&query={keyword}",
}
