"""
Content Reviewer Agent

内容审核员：审核内容质量、合规性，提供优化建议。
集成各平台运营规范，确保内容符合最新平台要求。
"""

from enum import Enum
import re
from typing import Any

from .base_agent import BaseAgent


class ReviewResult(Enum):
    """审核结果枚举。"""

    APPROVED = "approved"  # 通过
    NEEDS_REVISION = "needs_revision"  # 需要修改
    REJECTED = "rejected"  # 拒绝


class ContentReviewer(BaseAgent):
    """
    内容审核员 Agent。

    职责：
    - 审核内容质量和专业性
    - 检查内容合规性（法律、平台规则）
    - 评估传播潜力
    - 提供具体的优化建议
    - 支持人工审核环节
    """

    # 工具占位符（具体工具由工具模块注入）
    _tools: list[Any] = []

    def __init__(
        self,
        llm: str | None = None,
        tools: list[Any] | None = None,
        verbose: bool = True,
        allow_delegation: bool = False,
        human_input: bool = True,  # 默认启用人工输入
    ):
        """
        初始化内容审核员。

        Args:
            llm: 使用的 LLM 模型名称
            tools: Agent 可用的工具列表
            verbose: 是否输出详细日志
            allow_delegation: 是否允许任务委托（审核员默认不允许）
            human_input: 是否需要人工输入（审核员默认需要）
        """
        super().__init__(
            llm=llm,
            tools=tools,
            verbose=verbose,
            allow_delegation=allow_delegation,
            human_input=human_input,
        )

    def get_role(self) -> str:
        """返回 Agent 的角色定义。"""
        return "内容审核员"

    def get_goal(self) -> str:
        """返回 Agent 的目标定义。"""
        return (
            "严格审核内容的质量、准确性和合规性，确保内容符合平台规则 "
            "和法律法规，同时提供具体的优化建议以提升内容价值"
        )

    def get_backstory(self, platform: str = "") -> str:
        """返回 Agent 的背景故事。按需注入目标平台审核规范。"""
        core = self._get_core_backstory()
        if platform:
            platform_rules = self._get_platform_review_rules(platform)
            if platform_rules:
                core += f"\n\n## {platform} 平台审核要点\n\n{platform_rules}"
        return core

    def _get_core_backstory(self) -> str:
        """核心 backstory：审核哲学 + 评分标准 + 决策规则。"""
        return """你是一位资深内容审核专家。

## 审核哲学

严格但公正。指出问题的同时肯定亮点，提供可操作的修改建议。
你的目标不是挑刺，而是帮助创作者把 80 分的内容提升到 95 分。

## 审核流程（按顺序执行）

### 1. 爆款对标验证（一票否决）

检查创作者是否满足对标规则：
- ≥5 个真实爆款对标？
- 每个对标 ≥2 个维度匹配？
- 链接和数据可验证？

**不满足 → 直接 needs_revision，要求补充对标。**

### 2. 内容质量评分（6 维度，与创作者自检对齐）

逐项评分 1-10，对照创作者的 quality_self_check：

| 维度 | 审核标准 |
|------|---------|
| 钩子力 | 标题和开头是否在 3 秒内制造好奇/共鸣/冲突？ |
| 信息密度 | 每段是否都有新信息？能否删掉 20%+ 不影响理解？ |
| 情绪节奏 | 全文情绪是否有起伏？关键位置有情绪高点？ |
| 可操作性 | 读者看完能否立刻行动？有具体方法/步骤/案例？ |
| 原创视角 | 是否有独特切入点？还是搜索引擎第一页的内容？ |
| 互动设计 | 是否自然引导读者参与？（非诱导） |

**如果创作者自评与你的评分差距 >2 分，在 issues 中标注"自评偏差"。**

### 3. 合规检查

检测违禁词（广告法极限词、诱导互动、站外引流、医疗声称、金融承诺）。
任何严重违规 → needs_revision。

### 4. 平台适配检查

检查内容是否符合目标平台的格式规范（字数、结构、标题长度等）。

## 评分权重

综合评分 = 质量(35%) + 合规(30%) + 传播力(20%) + 口味匹配(15%)

## 决策规则

| 综合评分 | 决策 |
|---------|------|
| ≥85 | approved |
| 60-84 | needs_revision（列出具体修改项） |
| <60 | rejected（说明根本性问题） |

## 输出格式

```json
{
  "result": "approved/needs_revision/rejected",
  "overall_score": 85,
  "scores": {
    "hook": 8, "density": 7, "emotion": 8,
    "actionable": 7, "originality": 8, "interaction": 7,
    "compliance": 95, "spread": 80, "taste_fit": 75
  },
  "creator_self_check_delta": {"hook": -1, "density": 0},
  "viral_check": true,
  "viral_count": 5,
  "issues": [
    {"type": "质量", "severity": "high", "description": "第3段信息密度低，可删除50%不影响理解", "suggestion": "精简为..."}
  ],
  "suggestions": ["建议1", "建议2"],
  "highlights": ["亮点1", "亮点2"],
  "final_content": "修正后的内容（如有小修改可直接给出）"
}
```"""

    @staticmethod
    def _get_platform_review_rules(platform: str) -> str:
        """返回指定平台的审核要点。"""
        rules = {
            "xiaohongshu": """- 标题 ≤20 字，前 18 字含 2 个核心关键词
- 正文 500-1000 字，五段式结构
- emoji 1-3 个，不过度
- 禁止：站外引流（微信/手机号）、诱导互动（点赞收藏）、极限词
- 封面图建议：是否提及配图策略""",

            "wechat": """- 标题 20-30 字，激发好奇心
- 正文 2000-4000 字，每 500-800 字设小标题
- 禁止：诱导分享、营销敏感词（加微信/扫码）
- 排版建议：段落长度、小标题密度""",

            "douyin": """- 黄金 3 秒开场是否有效
- 时长 15-60 秒脚本，完播率优先
- 禁止：极限词、医疗/金融声称
- 口语化程度是否足够""",

            "zhihu": """- 开头是否直接给结论
- 专业性与通俗性平衡
- 禁止：答非所问、营销推广过重
- 数据和案例引用是否充分""",

            "weibo": """- 正文 100-120 字，精炼
- 话题标签 1-3 个
- 禁止：刷粉刷赞、标题党
- 热点响应时效性""",

            "bilibili": """- 视频结构是否完整（钩子→正文→互动）
- 信息密度和情绪起伏
- 禁止：赌博/彩票、烟草/走私
- 弹幕互动点设计""",
        }
        return rules.get(platform, "")

    def get_default_model(self) -> str:
        """返回默认的 LLM 模型。"""
        return self.DEFAULT_MODEL  # claude-sonnet-4-20250514

    def get_tools(self) -> list[Any]:
        """返回 Agent 可用的工具列表。"""
        # 工具列表（待工具模块实现后注入）
        # 预期工具：
        # - sensitive_content_checker: 敏感内容检测工具
        # - plagiarism_checker: 抄袭检测工具
        # - grammar_checker: 语法检查工具
        return self._tools if self._tools else self.tools

    @classmethod
    def set_tools(cls, tools: list[Any]) -> None:
        """
        设置类级别的工具列表。

        Args:
            tools: 工具列表
        """
        cls._tools = tools


class ReviewReport:
    """
    审核报告数据结构。

    用于规范化内容审核员的输出格式。
    """

    def __init__(
        self,
        result: ReviewResult,
        quality_score: float,
        compliance_score: float,
        spread_score: float,
        issues: list[dict[str, Any]],
        suggestions: list[str],
        highlights: list[str],
        reviewer_notes: str,
    ):
        """
        初始化审核报告。

        Args:
            result: 审核结果
            quality_score: 质量评分（0-100）
            compliance_score: 合规评分（0-100）
            spread_score: 传播评分（0-100）
            issues: 问题列表，每项包含位置、类型、描述
            suggestions: 优化建议列表
            highlights: 内容亮点列表
            reviewer_notes: 审核员备注
        """
        self.result = result
        self.quality_score = quality_score
        self.compliance_score = compliance_score
        self.spread_score = spread_score
        self.issues = issues
        self.suggestions = suggestions
        self.highlights = highlights
        self.reviewer_notes = reviewer_notes

    @property
    def overall_score(self) -> float:
        """计算综合评分。"""
        return (
            self.quality_score * 0.4
            + self.compliance_score * 0.35
            + self.spread_score * 0.25
        )

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "result": self.result.value,
            "overall_score": self.overall_score,
            "quality_score": self.quality_score,
            "compliance_score": self.compliance_score,
            "spread_score": self.spread_score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "highlights": self.highlights,
            "reviewer_notes": self.reviewer_notes,
        }

    def is_approved(self) -> bool:
        """检查是否通过审核。"""
        return self.result == ReviewResult.APPROVED


# ── 违禁词检测库 ────────────────────────────────────────────────────────

class ForbiddenWordsChecker:
    """
    违禁词检测工具。

    根据各平台运营规范检测内容中的违禁词和敏感内容。
    """

    # 广告法极限词（所有平台通用）
    AD_LIMITED_WORDS = [
        "最", "最佳", "最具", "最爱", "最赚", "最优", "最优秀", "最好",
        "最大", "最大程度", "最高", "最高级", "最高端", "最低", "最低级",
        "第一", "首个", "首家", "唯一", "独一无二", "NO.1", "TOP1",
        "国家级", "世界级", "顶级", "极品", "极佳", "绝对", "极致",
        "史无前例", "万能", "100%", "永久", "王者", "冠军", "领衔",
    ]

    # 诱导互动词汇
    INDUCEMENT_WORDS = [
        "点赞过", "评论有惊喜", "留言领取", "转发抽奖", "转发有好运",
        "关注送", "粉丝专属", "集赞", "分享后查看", "转发领取",
    ]

    # 站外引流词
    EXTERNAL_LINK_WORDS = [
        "微信号", "加微信", "联系微信", "V信", "v信",
        "手机号", "联系电话", "扫码", "二维码",
        "淘宝", "天猫", "京东", "拼多多", "抖音号",
    ]

    # 医疗健康敏感词（需特证）
    MEDICAL_WORDS = [
        "治疗", "治愈", "疗效", "消炎", "抗癌", "抗肿瘤",
        "预防疾病", "药效", "杀菌", "祛斑", "美白针",
    ]

    # 金融投资敏感词
    FINANCIAL_WORDS = [
        "保本", "稳赚", "零风险", "高收益", "年化收益",
        "躺赚", "暴富", "必涨", "无风险",
    ]

    # 平台特定违禁词
    PLATFORM_SPECIFIC = {
        "xiaohongshu": ["姐妹们", "宝子们", "剁手", "回购无数"],
        "wechat": ["分享后", "集赞", "转发朋友圈"],
        "weibo": ["刷粉", "刷量", "互粉互赞"],
        "zhihu": ["软文", "植入", "合作推广"],
        "douyin": ["点击主页", "关注我", "橱窗链接"],
        "bilibili": ["UP主互粉", "投币关注"],
    }

    @classmethod
    def check_all(cls, text: str, platform: str = "general") -> dict[str, list[dict]]:
        """
        检查文本中的所有类型违禁词。

        Args:
            text: 待检查文本
            platform: 目标平台 (xiaohongshu/wechat/weibo/zhihu/douyin/bilibili/general)

        Returns:
            检查结果字典，包含各类违禁词的匹配信息
        """
        result = {
            "ad_limited": cls._check_words(text, cls.AD_LIMITED_WORDS, "广告法极限词"),
            "inducement": cls._check_words(text, cls.INDUCEMENT_WORDS, "诱导互动"),
            "external_link": cls._check_words(text, cls.EXTERNAL_LINK_WORDS, "站外引流"),
            "medical": cls._check_words(text, cls.MEDICAL_WORDS, "医疗健康"),
            "financial": cls._check_words(text, cls.FINANCIAL_WORDS, "金融投资"),
        }

        # 检查平台特定违禁词
        if platform in cls.PLATFORM_SPECIFIC:
            result["platform_specific"] = cls._check_words(
                text,
                cls.PLATFORM_SPECIFIC[platform],
                f"{platform}平台特定"
            )

        return result

    @classmethod
    def _check_words(
        cls, text: str, word_list: list[str], category: str
    ) -> list[dict]:
        """
        检查文本中是否包含指定词汇。

        Returns:
            匹配结果列表，每项包含词汇、位置、上下文
        """
        matches = []
        for word in word_list:
            # 使用正则查找所有匹配位置
            for match in re.finditer(re.escape(word), text):
                # 获取上下文（前后各10个字符）
                start = max(0, match.start() - 10)
                end = min(len(text), match.end() + 10)
                context = text[start:end]

                matches.append({
                    "word": word,
                    "position": match.start(),
                    "context": context,
                    "category": category,
                })

        return matches

    @classmethod
    def get_compliance_score(cls, check_result: dict[str, list[dict]]) -> float:
        """
        根据违禁词检查结果计算合规评分。

        Args:
            check_result: check_all() 返回的检查结果

        Returns:
            合规评分 (0-100)
        """
        # 严重违规：广告法极限词、站外引流、医疗金融
        severe = (
            len(check_result.get("ad_limited", []))
            + len(check_result.get("external_link", []))
            + len(check_result.get("medical", []))
            + len(check_result.get("financial", []))
        )

        # 轻度违规：诱导互动
        light = len(check_result.get("inducement", []))

        # 计算分数：每个严重违规扣20分，每个轻度违规扣10分
        score = 100 - (severe * 20) - (light * 10)
        return max(0, score)

    @classmethod
    def generate_suggestions(cls, check_result: dict[str, list[dict]]) -> list[str]:
        """
        根据违禁词检查结果生成优化建议。

        Args:
            check_result: check_all() 返回的检查结果

        Returns:
            优化建议列表
        """
        suggestions = []

        if check_result.get("ad_limited"):
            suggestions.append(
                f"发现 {len(check_result['ad_limited'])} 处广告法极限词，"
                "建议替换为具体描述（如'非常'、'相当'、'许多'等）"
            )

        if check_result.get("inducement"):
            suggestions.append(
                "发现诱导互动词汇，建议改为开放式提问，如'有问题欢迎评论区讨论'、"
                "'详细内容在置顶'等"
            )

        if check_result.get("external_link"):
            suggestions.append(
                "发现站外引流词，建议删除或使用平台官方功能（如小红书专栏、微信公众号菜单）"
            )

        if check_result.get("medical"):
            suggestions.append(
                "发现医疗健康敏感词，如非相关资质主体，建议删除或改为'保养'、'护理'等"
            )

        if check_result.get("financial"):
            suggestions.append(
                "发现金融投资敏感词，建议删除风险承诺，改为'仅供参考'、'市场有风险'等"
            )

        platform_specific = check_result.get("platform_specific")
        if platform_specific:
            suggestions.append(
                f"发现 {len(platform_specific)} 处平台特定违禁词，建议调整为平台推荐的表达方式"
            )

        return suggestions
