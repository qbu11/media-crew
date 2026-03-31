# Crew Media Ops - Multi-Agent 架构设计方案

> **版本**: v1.1 (简化版)
> **日期**: 2026-03-21
> **状态**: 设计阶段

---

## 一、项目概述

### 1.1 目标

打造一个 **全链路自动化自媒体运营系统**，支持海内外主流平台，实现：

- **热点探测** → 自动发现有价值的话题
- **内容生成** → AI 自动创作图文/视频内容
- **自动发布** → 多平台定时发布
- **数据采集** → 获取流量数据
- **智能优化** → 自动学习与进化

### 1.2 支持平台

| 海外 | 中国大陆 |
|------|----------|
| Twitter/X, Instagram, Facebook, LinkedIn, TikTok, YouTube, Pinterest | 小红书, 微信公众号, 微博, 知乎, 抖音, B站, 快手 |

### 1.3 产品形态

- **Web 应用**：用户可通过浏览器管理整个系统
- **低代码配置**：非技术用户可配置 Agent 行为
- **可视化监控**：实时查看 Agent 工作状态和数据

---

## 二、Agent 架构设计（简化版）

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Web UI 层                                        │
│                         (FastAPI + React/Vue)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CrewAI 编排层                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Hotspot  │  │ Content  │  │ Publish  │  │ Analytics│  │ Learning │      │
│  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
         │                 │                 │                 │                 │
┌────────▼─────┐  ┌────────▼─────┐  ┌────────▼─────┐  ┌────────▼─────┐  ┌──▼──────────┐
│ 热点探测工具  │  │ 内容生成工具  │  │ 平台发布工具  │  │ 数据采集工具  │  │  学习引擎   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘
         │                 │                 │                 │                 │
┌────────▼─────────────────────────────────────────────────────────────────────┐
│                              数据层                                           │
│  SQLite (开发) / PostgreSQL (生产) + Redis (缓存) + MinIO (文件)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent 详细设计

#### Agent 1: HotspotAgent（热点探测专家）

**单一 Agent，集成所有热点探测能力**

| 属性 | 值 |
|------|-----|
| **角色** | 热点探测专家 |
| **目标** | 从各平台采集热点，评估价值，预测趋势，输出高质量选题 |
| **背景** | 你是一位资深的热点猎手，擅长从海量信息中发现即将爆发的有价值话题 |

**核心工具**：
- `weibo_hot_search_tool` - 微博热搜采集
- `zhihu_hot_list_tool` - 知乎热榜采集
- `google_trends_tool` - Google Trends 查询
- `youtube_trending_tool` - YouTube 热门视频
- `douyin_hot_tool` - 抖音热点
- `hotspot_evaluator_tool` - 热点评分（0-100）
- `trend_predictor_tool` - 趋势预测

**工作流**：
```
多源采集 → 去重聚合 → 评分过滤 → 趋势预测 → 输出选题列表
```

**输出**：
```python
class HotspotResult(BaseModel):
    title: str                    # 热点标题
    sources: List[str]            # 来源平台
    score: float                  # 评分 0-100
    trend_direction: str          # rising/stable/falling
    suggested_topics: List[str]   # 建议的选题角度
```

---

#### Agent 2: ContentAgent（内容创作专家）

**单一 Agent，集成所有内容创作能力**

| 属性 | 值 |
|------|-----|
| **角色** | 全栈内容创作者 |
| **目标** | 根据选题自动生成高质量图文/视频内容，包括研究、撰写、配图、审核 |
| **背景** | 你是一位全能型内容创作者，擅长研究、写作、设计、视频制作和内容审核 |

**核心工具**：
- `search_tool` - 搜索素材
- `rag_knowledge_tool` - 知识库检索
- `copy_writer_tool` - 文案生成
- `title_optimizer_tool` - 标题优化
- `image_gen_tool` - 图片生成 (Stable Diffusion/Midjourney)
- `video_gen_tool` - 视频生成 (Pika/Luma)
- `compliance_check_tool` - 合规检查

**工作流**：
```
选题研究 → 内容撰写 → 标题优化 → 配图生成 → 视频生成(可选) → 合规审核 → 内容草稿
```

**输出**：
```python
class ContentDraft(BaseModel):
    topic: str
    title: str
    body: str
    images: List[str]
    video_url: Optional[str]
    hashtags: List[str]
    compliance_score: float        # 合规分数 0-100
    platform_variants: Dict[str, Any]  # 各平台适配版本
```

---

#### Agent 3: PublishAgent（发布执行专家）

**单一 Agent，集成所有发布执行能力**

| 属性 | 值 |
|------|-----|
| **角色** | 多平台发布专家 |
| **目标** | 将内容适配到各平台格式，计算最佳发布时间，执行发布，监控结果 |
| **背景** | 你是一位社交媒体运营专家，熟悉各平台的发布规则和最佳实践 |

**核心工具**：
- `content_adapter_tool` - 内容格式适配
- `schedule_optimizer_tool` - 发布时间优化
- `xiaohongshu_publisher_tool` - 小红书发布
- `wechat_mp_publisher_tool` - 微信公众号发布
- `weibo_publisher_tool` - 微博发布
- `zhihu_publisher_tool` - 知乎发布
- `twitter_publisher_tool` - Twitter 发布
- `youtube_publisher_tool` - YouTube 发布
- `publish_monitor_tool` - 发布监控

**工作流**：
```
内容适配 → 发布时间计算 → 多平台发布 → 结果监控 → 记录日志
```

**输出**：
```python
class PublishResult(BaseModel):
    content_id: str
    platform_results: Dict[str, PlatformResult]
    overall_status: str            # success/partial/failed
    published_at: datetime
```

---

#### Agent 4: AnalyticsAgent（数据分析专家）

**单一 Agent，集成所有数据分析能力**

| 属性 | 值 |
|------|-----|
| **角色** | 数据分析专家 |
| **目标** | 采集各平台数据，计算关键指标，生成分析报告，提供优化建议 |
| **背景** | 你是一位数据分析师，擅长从数据中发现洞察并转化为可执行的建议 |

**核心工具**：
- `data_collector_tool` - 数据采集（各平台 API/爬虫）
- `metrics_calculator_tool` - 指标计算
- `trend_analyzer_tool` - 趋势分析
- `report_generator_tool` - 报告生成

**工作流**：
```
定时触发 → 数据采集 → 指标计算 → 趋势分析 → 报告生成 → 存储到数据库
```

**输出**：
```python
class AnalyticsReport(BaseModel):
    period: str                   # 统计周期
    total_views: int
    total_engagement: int
    top_performing: List[ContentStats]
    insights: List[str]           # 关键洞察
    recommendations: List[str]    # 优化建议
```

---

#### Agent 5: LearningAgent（学习进化专家）

**单一 Agent，集成所有学习进化能力**

| 属性 | 值 |
|------|-----|
| **角色** | 智能优化专家 |
| **目标** | 从历史数据中学习成功模式，优化内容策略，更新知识库 |
| **背景** | 你是一位 AI 研究员，擅长机器学习和数据挖掘，能从复杂模式中提取规律 |

**核心工具**：
- `pattern_mining_tool` - 模式挖掘
- `ab_test_tool` - A/B 测试
- `strategy_optimizer_tool` - 策略优化
- `knowledge_update_tool` - 知识库更新

**工作流**：
```
定期触发 → 挖掘成功模式 → 生成优化策略 → 更新知识库 → 调整 Agent 行为
```

**输出**：
```python
class LearningUpdate(BaseModel):
    patterns_found: List[str]
    strategy_updates: List[str]
    knowledge_updated: bool
    effectiveness_prediction: float
```

---

### 2.3 Agent 交互流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ HotspotAgent │────▶│ ContentAgent │────▶│ PublishAgent │
│  发现选题    │     │  生成内容    │     │  发布内容    │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                        │
       ▼                                        ▼
┌──────────────┐                         ┌──────────────┐
│LearningAgent │                         │AnalyticsAgent│
│ 学习优化     │◀────────────────────────│ 采集数据     │
└──────────────┘                         └──────────────┘
```

---

## 三、平台集成方案

### 3.1 海外平台

| 平台 | API 方案 | 风险 | 成本 |
|------|----------|------|------|
| Twitter/X | 官方 API v2 | 高（自动化检测） | $100-5000/月 |
| Instagram | Instagram Graph API | 中 | 需 Business 账号 |
| Facebook | Graph API | 中 | 需 Page Access |
| LinkedIn | Member API | 低 | 商业友好 |
| TikTok | 非官方（Playwright） | 极高 | 风险自负 |
| YouTube | Data API v3 | 低 | 配额限制 |
| Pinterest | API v5 | 低 | 最友好 |

### 3.2 中国大陆平台

| 平台 | 方案 | 风险 | 开源参考 |
|------|------|------|----------|
| 小红书 | 逆向API + Cookie池 | 中 | [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader) |
| 微信公众号 | 官方API | 低 | [wechatpy](https://github.com/wechatpy/wechatpy) |
| 微博 | 官方API | 低 | [weibo](https://open.weibo.com/) |
| 知乎 | 逆向API | 中 | [zhihu-api](https://github.com/lzjun567/zhihu-api) |
| 抖音 | 逆向API + Playwright | 高 | [Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) |
| B站 | bilibili-api | 中 | [bilibili-api](https://github.com/Nemo2011/bilibili-api) |
| 快手 | 逆向API | 高 | [KS-Downloader](https://github.com/JoeanAmier/KS-Downloader) |

### 3.3 统一平台接口

```python
# src/tools/platform/base.py
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel

class PublishContent(BaseModel):
    """发布内容统一格式"""
    title: str
    body: str
    images: list[str] = []
    video: Optional[str] = None
    hashtags: list[str] = []
    publish_time: Optional[str] = None

class PublishResult(BaseModel):
    """发布结果统一格式"""
    success: bool
    platform: str
    content_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    published_at: Optional[str] = None

class BasePlatformTool(ABC):
    """平台工具基类"""

    @abstractmethod
    def authenticate(self) -> bool:
        """认证"""
        pass

    @abstractmethod
    def publish(self, content: PublishContent) -> PublishResult:
        """发布内容"""
        pass

    @abstractmethod
    def get_analytics(self, content_id: str) -> dict:
        """获取数据分析"""
        pass

    @property
    @abstractmethod
    def constraints(self) -> dict:
        """平台约束"""
        return {
            "max_title_length": 100,
            "max_body_length": 10000,
            "max_images": 9,
            "min_publish_interval": 30,  # 秒
        }
```

---

## 三、技术栈

### 3.1 核心框架

| 层级 | 技术 | 说明 |
|------|------|------|
| Agent 框架 | CrewAI | 5 个 Agent 编排 |
| LLM | Claude (主力) + DeepSeek (降本) | 内容生成 |
| 后端框架 | FastAPI | Web API |
| 前端框架 | React + TypeScript | Web UI |
| 数据验证 | Pydantic v2 | 类型安全 |
| 任务调度 | APScheduler | 定时任务 |
| 浏览器自动化 | Playwright | 平台发布 |
| 数据库 | SQLite → PostgreSQL | 数据存储 |
| 缓存 | Redis | 会话/队列 |
| 文件存储 | MinIO / OSS | 图片/视频 |

### 3.2 AI 工具链

| 功能 | 工具 | 成本 |
|------|------|------|
| 文本生成 | Claude 3.5 Sonnet + DeepSeek V3 | $3-15/1M tokens |
| 图片生成 | Stable Diffusion (自部署) + Midjourney | $0.002-0.05/图 |
| 视频生成 | Pika Labs + Luma Dream Machine | $8-58/月 |
| 热点探测 | Google Trends + pytrends | 免费 |
| 合规检查 | OpenAI Moderation API | 按需付费 |

### 3.3 项目结构（简化版）

```
C:\11projects\Crew\
├── src/
│   ├── agents/              # 5 个 Agent 定义
│   │   ├── hotspot_agent.py      # 热点探测 Agent
│   │   ├── content_agent.py      # 内容创作 Agent
│   │   ├── publish_agent.py      # 发布执行 Agent
│   │   ├── analytics_agent.py    # 数据分析 Agent
│   │   └── learning_agent.py     # 学习进化 Agent
│   ├── tools/               # 工具定义
│   │   ├── hotspot/              # 热点探测工具
│   │   │   ├── weibo_tool.py
│   │   │   ├── zhihu_tool.py
│   │   │   ├── google_trends.py
│   │   │   └── evaluator.py
│   │   ├── content/              # 内容生成工具
│   │   │   ├── writer_tool.py
│   │   │   ├── image_tool.py
│   │   │   ├── video_tool.py
│   │   │   └── compliance_tool.py
│   │   └── platform/             # 平台发布工具
│   │       ├── base.py
│   │       ├── xiaohongshu.py
│   │       ├── wechat_mp.py
│   │       ├── weibo.py
│   │       ├── zhihu.py
│   │       ├── twitter.py
│   │       └── youtube.py
│   ├── schemas/             # Pydantic 模型
│   │   ├── hotspot.py
│   │   ├── content.py
│   │   ├── publish.py
│   │   └── analytics.py
│   ├── models/              # 数据库模型
│   │   ├── hotspot.py
│   │   ├── content.py
│   │   ├── publish_log.py
│   │   └── analytics.py
│   ├── core/                # 核心配置
│   │   ├── config.py
│   │   ├── llm.py
│   │   └── logging.py
│   └── api/                 # FastAPI
│       ├── main.py
│       └── routes/
├── frontend/               # React 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
├── data/                   # 数据存储
├── tests/                  # 测试
├── scripts/                # CLI 脚本
└── pyproject.toml
```

---

## 四、核心代码示例

### 4.1 HotspotAgent 实现

```python
# src/agents/hotspot_agent.py
from crewai import Agent
from langchain_anthropic import ChatAnthropic
from src.tools.hotspot import (
    weibo_hot_search_tool,
    zhihu_hot_list_tool,
    google_trends_tool,
    hotspot_evaluator_tool,
    trend_predictor_tool,
)

def create_hotspot_agent(brand_voice: str = "专业但不失亲和") -> Agent:
    """创建热点探测 Agent"""
    return Agent(
        role="热点探测专家",
        goal="从各平台采集热点，评估价值，预测趋势，输出高质量选题",
        backstory="""你是一位资深的热点猎手，擅长从海量信息中发现即将爆发的有价值话题。
        你熟悉微博、知乎、抖音、YouTube等平台的热点机制，能够准确判断话题的传播潜力。
        你的输出将为内容创作提供方向指引。""",
        llm=ChatAnthropic(model="claude-sonnet-4-20250514"),
        tools=[
            weibo_hot_search_tool,
            zhihu_hot_list_tool,
            google_trends_tool,
            hotspot_evaluator_tool,
            trend_predictor_tool,
        ],
        verbose=True,
        allow_delegation=False,
    )
```

### 4.2 ContentAgent 实现

```python
# src/agents/content_agent.py
from crewai import Agent
from langchain_anthropic import ChatAnthropic
from src.tools.content import (
    search_tool,
    rag_knowledge_tool,
    writer_tool,
    title_optimizer_tool,
    image_gen_tool,
    video_gen_tool,
    compliance_check_tool,
)

def create_content_agent(brand_voice: str = "专业但不失亲和") -> Agent:
    """创建内容创作 Agent"""
    return Agent(
        role="全栈内容创作者",
        goal=f"根据选题自动生成符合{brand_voice}调性的高质量图文/视频内容",
        backstory="""你是一位全能型内容创作者，具备以下能力：
        1. 深度研究：能从海量信息中提取有价值的观点和数据
        2. 文案创作：擅长撰写各类风格的文案，能把握品牌调性
        3. 视觉设计：懂得如何用图片增强内容的吸引力
        4. 视频制作：能将内容转化为吸引人的短视频
        5. 内容审核：熟悉各平台的发布规则，确保内容合规""",
        llm=ChatAnthropic(model="claude-sonnet-4-20250514"),
        tools=[
            search_tool,
            rag_knowledge_tool,
            writer_tool,
            title_optimizer_tool,
            image_gen_tool,
            video_gen_tool,
            compliance_check_tool,
        ],
        verbose=True,
        allow_delegation=False,
    )
```

### 4.3 主工作流编排

```python
# src/crews/media_ops_crew.py
from crewai import Crew, Process
from src.agents.hotspot_agent import create_hotspot_agent
from src.agents.content_agent import create_content_agent
from src.agents.publish_agent import create_publish_agent
from src.agents.analytics_agent import create_analytics_agent
from src.agents.learning_agent import create_learning_agent

class MediaOpsCrew:
    """自媒体运营 Crew - 5 Agent 协作"""

    def __init__(self, brand_voice: str = "专业但不失亲和"):
        self.hotspot_agent = create_hotspot_agent(brand_voice)
        self.content_agent = create_content_agent(brand_voice)
        self.publish_agent = create_publish_agent()
        self.analytics_agent = create_analytics_agent()
        self.learning_agent = create_learning_agent()

    def run_content_pipeline(self, platforms: list[str]):
        """运行内容生产流水线"""
        crew = Crew(
            agents=[
                self.hotspot_agent,
                self.content_agent,
                self.publish_agent,
            ],
            process=Process.sequential,
            verbose=True,
            memory=True,
        )
        return crew.kickoff()

    def run_analytics_cycle(self):
        """运行数据分析循环"""
        crew = Crew(
            agents=[self.analytics_agent, self.learning_agent],
            process=Process.sequential,
            verbose=True,
        )
        return crew.kickoff()
```

---

## 五、数据模型

### 6.1 核心数据表

```sql
-- 热点表
CREATE TABLE hotspots (
    id INTEGER PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source VARCHAR(50) NOT NULL,     -- weibo, zhihu, google_trends, etc.
    score FLOAT DEFAULT 0,            -- 评分 0-100
    trend_growth_rate FLOAT,          -- 趋势增长率
    social_engagement FLOAT,          -- 社交互动分数
    platform_coverage INT,            -- 跨平台覆盖数
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,             -- 热点过期时间
    metadata JSON                     -- 其他元数据
);

-- 内容表
CREATE TABLE contents (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER REFERENCES hotspots(id),
    title VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    images JSON,                      -- 图片 URL 列表
    video_url VARCHAR(500),
    hashtags JSON,
    status VARCHAR(20) DEFAULT 'draft', -- draft, approved, published, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- 发布记录表
CREATE TABLE publish_logs (
    id INTEGER PRIMARY KEY,
    content_id INTEGER REFERENCES contents(id),
    platform VARCHAR(50) NOT NULL,
    platform_content_id VARCHAR(200),  -- 平台返回的内容ID
    platform_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending', -- pending, success, failed
    published_at TIMESTAMP,
    scheduled_for TIMESTAMP,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    metadata JSON
);

-- 数据分析表
CREATE TABLE analytics (
    id INTEGER PRIMARY KEY,
    publish_log_id INTEGER REFERENCES publish_logs(id),
    views INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    engagement_rate FLOAT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Agent 学习记录表
CREATE TABLE agent_learning (
    id INTEGER PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    learning_type VARCHAR(50),        -- pattern, strategy, feedback
    content TEXT NOT NULL,
    confidence FLOAT,                 -- 置信度 0-1
    applied_at TIMESTAMP,
    effectiveness_score FLOAT,        -- 应用效果评分
    metadata JSON
);
```

---

## 六、开发优先级

### Phase 1: MVP（最小可行产品）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| HotspotAgent | P0 | 支持微博、知乎、Google Trends |
| ContentAgent | P0 | 图文内容生成，支持1-2个平台 |
| PublishAgent | P0 | 手动确认后发布 |
| AnalyticsAgent | P1 | 基础数据采集 |
| LearningAgent | P2 | 暂不实现 |

### Phase 2: 自动化

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 自动发布 | P0 | 定时发布，支持更多平台 |
| 配图生成 | P1 | Stable Diffusion 集成 |
| 可视化 Dashboard | P1 | Web UI |
| LearningAgent | P2 | 基础学习反馈 |

### Phase 3: 智能化

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 视频生成 | P1 | Pika/Luma 集成 |
| 智能优化 | P1 | A/B测试 |
| 预测模型 | P2 | 热点预测 |
| 低代码配置 | P2 | 用户可配置 Agent |

---

## 七、简化版 vs 多 Agent 版本对比

| 维度 | 简化版（推荐） | 多 Agent 版本 |
|------|----------------|--------------|
| Agent 数量 | **5 个** | 22 个 |
| 架构复杂度 | 低 | 高 |
| 开发周期 | 短 | 长 |
| 维护成本 | 低 | 高 |
| LLM 调用次数 | 少 | 多 |
| 成本 | 低 | 高 |
| 适合场景 | **MVP、小团队** | 大规模、定制化 |

**推荐理由**：
1. 单 Agent 内部通过 tools 实现功能拆分，代码更简洁
2. 减少 Agent 间通信开销，性能更好
3. 便于调试和监控
4. 成本可控（每次 LLM 调用都有成本）

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 平台 API 变更 | 高 | 多源备份，快速响应机制 |
| 反爬虫风控 | 高 | 代理池、频率控制、备用方案 |
| 内容合规性 | 高 | 多层审核、敏感词过滤 |
| AI 内容检测 | 中 | 人工润色、增加原创元素 |
| 成本超支 | 中 | 设置配额告警、多模型组合 |
| 性能问题 | 中 | 并行执行、缓存优化 |

---

## 九、成本估算

### 9.1 月度成本（小团队）

| 项目 | 方案 | 月成本 |
|------|------|--------|
| LLM API | Claude + DeepSeek 组合 | $50-100 |
| 图片生成 | Stable Diffusion 自部署 + Midjourney | $30-60 |
| 视频生成 | Pika 基础版 + Luma 免费版 | $8-20 |
| 热点数据 | 官方API + 自建爬虫 | ¥0-300 |
| 服务器 | VPS + 数据库 | ¥100-300 |
| **总计** | - | **$100-200 + ¥100-600** |

### 9.2 成本优化建议

1. **LLM 降本**：DeepSeek 处理初稿，Claude 做最终润色
2. **图片降本**：自部署 Stable Diffusion（需要 GPU）
3. **热点降本**：优先使用免费 API
4. **视频降本**：优先使用国内免费工具（Kling, Vidu）

---

## 十、参考资源

### 10.1 开源项目

| 项目 | 链接 | 说明 |
|------|------|------|
| multi-agent-social-media-automation | [GitHub](https://github.com/soulcrancerdev/multi-agent-social-media-automation) | n8n + LangGraph |
| writer | [GitHub](https://github.com/rk-vashista/writer) | CrewAI + FastAPI |
| social-media-agent | [GitHub](https://github.com/langchain-ai/social-media-agent) | LangChain 官方 |
| XHS-Downloader | [GitHub](https://github.com/JoeanAmier/XHS-Downloader) | 小红书 |
| bilibili-api | [GitHub](https://github.com/Nemo2011/bilibili-api) | B站 |

### 10.2 文档

- [CrewAI 文档](https://docs.crewai.com/)
- [LangChain 文档](https://python.langchain.com/)
- [Playwright 文档](https://playwright.dev/python/)

---

## 十一、下一步行动

1. **技术验证**：搭建 CrewAI 基础框架，实现 5 个 Agent
2. **平台对接**：选择 2-3 个平台（小红书、微信公众号、微博）进行对接测试
3. **MVP 开发**：实现 HotspotAgent + ContentAgent + PublishAgent
4. **用户测试**：小范围内测，收集反馈
5. **迭代优化**：根据反馈持续改进

---

_文档版本：v1.1 (简化版) | 最后更新：2026-03-21_
