# AI 运营系统知识库架构设计

> 基于 RAG（检索增强生成）技术的高质量知识库系统设计文档
>
> 日期：2026-03-28

---

## 目录

1. [概述](#概述)
2. [技术选型](#技术选型)
3. [系统架构设计](#系统架构设计)
4. [数据 Schema 设计](#数据-schema-设计)
5. [与 Agent 系统的集成方案](#与-agent-系统的集成方案)
6. [实施路线图](#实施路线图)

---

## 概述

### 核心问题

为 Crew Media Ops AI 运营系统构建高质量知识库，支持以下知识类型：

| 知识类型 | 描述 | 数据特点 |
|---------|------|---------|
| 爆款内容库 | 历史爆款及其特征 | 结构化分析 + 向量嵌入 |
| 运营策略库 | 成功的运营案例 | 案例叙事 + 关键决策点 |
| 行业知识库 | 不同垂类的运营特点 | 领域知识 + 规则 |
| 用户画像库 | 目标受众特征 | 人群标签 + 行为模式 |
| 平台规则库 | 各平台算法和规则 | 规则文本 + 更新历史 |

### 设计原则

1. **混合检索**：向量搜索 + 关键词搜索 + 知识图谱
2. **增量更新**：支持实时数据更新和版本管理
3. **可扩展**：支持新增知识类型和平台
4. **高性能**：毫秒级检索响应

---

## 技术选型

### 1. 向量数据库对比

| 数据库 | 优势 | 劣势 | 适用场景 | 成本（10M 向量/月） |
|-------|------|------|---------|-------------------|
| **Qdrant** | 开源、Rust 高性能、云便宜 | 社区较小 | 生产环境首选 | $120-250 |
| **Weaviate** | 混合搜索强、开源 | 部署复杂 | 需要混合搜索 | $150-300 |
| **Pinecone** | 托管服务、企业级 | 闭源、贵 | 快速上线 | $200-400 |
| **Milvus** | 大规模、开源 | 运维复杂 | 超大规模 | 按需 |
| **Chroma** | 轻量、易用 | 不适合生产 | 开发测试 | 免费/低 |

**推荐选择**：

- **开发阶段**：Chroma（轻量，快速迭代）
- **生产环境**：Qdrant（开源、高性能、成本优）
- **Windows 兼容**：由于 Chroma 依赖 lancedb（不支持 Windows），推荐使用 **Qdrant** 或 **DuckDB + sqlite-vec**

### 2. RAG 框架对比

| 框架 | 优势 | 劣势 | 适用场景 |
|-----|------|------|---------|
| **LlamaIndex** | RAG 专用、数据连接器丰富 | 通用性较低 | 纯 RAG 系统 |
| **LangChain** | 生态大、灵活 | 抽象复杂 | Agent + RAG 组合 |
| **Haystack** | 生产就绪、Pipeline 设计 | 社区较小 | 企业级 NLP |

**推荐选择**：

- **主力框架**：LlamaIndex（专注 RAG，索引策略丰富）
- **Agent 编排**：LangChain（与 CrewAI 已集成）
- **组合方案**：LlamaIndex 负责数据索引和检索，LangChain 负责 Agent 编排

### 3. 知识图谱

| 方案 | 优势 | 劣势 | 适用场景 |
|-----|------|------|---------|
| **Neo4j** | 成熟、Cypher 查询 | 商业许可 | 复杂关系 |
| **GraphRAG (Microsoft)** | LLM 自动构建图谱 | 资源消耗大 | 非结构化文本 |
| **自定义图存储** | 灵活、轻量 | 需要自己实现 | 简单关系 |

**推荐选择**：

- **初期**：SQLite + 邻接表（轻量实现）
- **进阶**：Neo4j（复杂关系查询）
- **可选**：Microsoft GraphRAG（自动从文本抽取知识图谱）

### 4. Embedding 模型

| 模型 | MTEB 分数 | 特点 | 成本 |
|-----|----------|------|------|
| **OpenAI text-embedding-3-large** | 64.6 | 通用强 | $0.13/1M tokens |
| **Cohere embed-v4** | 65.2 | 多语言好 | $0.10/1M tokens |
| **BGE-M3** | 63.0 | 开源、免费 | 免费 |
| **text-embedding-005 (Google)** | - | Vertex AI 集成 | 按用量 |

**推荐选择**：

- **中文场景**：BGE-M3（开源，中文效果好）
- **通用场景**：OpenAI text-embedding-3-large
- **成本敏感**：本地部署 BGE-M3

---

## 系统架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent Layer (CrewAI)                          │
├─────────────────────────────────────────────────────────────────────┤
│  TopicResearcher │ ContentCreator │ ContentReviewer │ DataAnalyst   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Knowledge Service Layer                          │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  Viral KB   │  │ Strategy KB │  │ Platform KB │  │ Audience KB│ │
│  │  Service    │  │  Service    │  │  Service    │  │  Service   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘ │
└─────────┼────────────────┼────────────────┼───────────────┼─────────┘
          │                │                │               │
          ▼                ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RAG Engine                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Hybrid Search Engine                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐  │ │
│  │  │ Vector Store│  │ BM25 Index  │  │ Knowledge Graph Store │  │ │
│  │  │  (Qdrant)   │  │ (Whoosh)    │  │     (Neo4j/SQLite)    │  │ │
│  │  └─────────────┘  └─────────────┘  └───────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Reranker & Fusion                            │ │
│  │  • Reciprocal Rank Fusion (RRF)                                 │ │
│  │  • Cross-encoder Reranking                                      │ │
│  │  • Metadata Filtering                                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Data Storage Layer                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ PostgreSQL  │  │   Qdrant    │  │   Neo4j     │  │   Redis    │ │
│  │ (关系数据)  │  │ (向量存储)  │  │  (知识图谱) │  │  (缓存)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 数据流

```
1. 数据摄入流程
   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ 数据源   │ -> │ ETL 管道 │ -> │ Embedding│ -> │  索引    │
   │ (爬取等) │    │ (清洗)   │    │ (向量化) │    │ (存储)   │
   └──────────┘    └──────────┘    └──────────┘    └──────────┘

2. 检索流程
   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ 查询     │ -> │ 混合检索 │ -> │ 融合重排 │ -> │ 返回结果 │
   │ (Agent)  │    │ (多路)   │    │ (RRF)    │    │ (Top-K)  │
   └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

---

## 数据 Schema 设计

### 1. 爆款内容库 (Viral Content KB)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class Platform(str, Enum):
    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    WECHAT = "wechat"

class ContentType(str, Enum):
    ARTICLE = "article"
    VIDEO = "video"
    IMAGE = "image"
    THREAD = "thread"

class ViralContentDocument(BaseModel):
    """爆款内容文档 - 存入向量数据库"""

    # 主键
    id: str = Field(description="唯一标识，格式: viral-{platform}-{hash}")

    # 基础信息
    platform: Platform
    content_type: ContentType
    title: str = Field(max_length=200)
    url: str = Field(description="原文链接")
    author: str = Field(description="作者名称")
    author_id: Optional[str] = Field(description="作者ID")

    # 时间
    published_at: datetime
    indexed_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 内容
    content_text: str = Field(description="正文内容")
    content_summary: str = Field(max_length=500, description="内容摘要")

    # 数据指标
    metrics: dict = Field(description="互动数据", default_factory=dict)
    # {
    #     "likes": int,
    #     "comments": int,
    #     "shares": int,
    #     "views": int,
    #     "saves": int,
    #     "engagement_rate": float
    # }

    # 五维度分析（来自 viral_reference.py）
    structure_analysis: dict = Field(default_factory=dict)
    emotion_analysis: dict = Field(default_factory=dict)
    image_analysis: dict = Field(default_factory=dict)
    title_analysis: dict = Field(default_factory=dict)
    depth_analysis: dict = Field(default_factory=dict)

    # 关键句式
    key_phrases: list[str] = Field(default_factory=list)

    # 话题标签
    hashtags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)

    # 向量元数据（用于过滤）
    category: Optional[str] = Field(description="内容垂类")
    emotion_type: Optional[str] = Field(description="主要情绪类型")
    content_length_range: Optional[str] = Field(description="内容长度范围")

    # 版本控制
    version: int = Field(default=1)
    is_active: bool = Field(default=True)


class ViralContentVector(BaseModel):
    """爆款内容向量 - 存入向量数据库的索引结构"""

    id: str  # 对应 ViralContentDocument.id
    vector: list[float] = Field(description="嵌入向量，维度取决于模型")

    # Payload（元数据，用于过滤）
    payload: dict = Field(default_factory=dict)
    # {
    #     "platform": "xiaohongshu",
    #     "category": "美妆",
    #     "emotion_type": "焦虑",
    #     "has_video": false,
    #     "likes_bucket": "10k-50k",
    #     "publish_date": "2026-03-01"
    # }
```

### 2. 运营策略库 (Strategy KB)

```python
class StrategyType(str, Enum):
    CONTENT_STRATEGY = "content_strategy"      # 内容策略
    GROWTH_STRATEGY = "growth_strategy"        # 增长策略
    ENGAGEMENT_STRATEGY = "engagement_strategy" # 互动策略
    CRISIS_STRATEGY = "crisis_strategy"        # 危机公关

class StrategyDocument(BaseModel):
    """运营策略文档"""

    id: str = Field(description="唯一标识，格式: strategy-{type}-{hash}")

    # 基础信息
    strategy_type: StrategyType
    title: str = Field(max_length=200)
    summary: str = Field(max_length=1000)

    # 适用范围
    platforms: list[Platform] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)  # 垂类
    audience_types: list[str] = Field(default_factory=list)  # 受众类型

    # 策略内容
    context: str = Field(description="背景/问题")
    approach: str = Field(description="方法/方案")
    execution: str = Field(description="执行步骤")
    results: str = Field(description="结果/效果")

    # 关键决策点
    key_decisions: list[dict] = Field(default_factory=list)
    # [
    #     {
    #         "decision": "选择A方案而非B方案",
    #         "reason": "基于数据分析...",
    #         "outcome": "效果提升30%"
    #     }
    # ]

    # 案例关联
    related_viral_ids: list[str] = Field(default_factory=list, description="关联的爆款ID")
    related_content_ids: list[str] = Field(default_factory=list, description="关联的已发布内容ID")

    # 元数据
    tags: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0.8)
    source: str = Field(description="来源：内部实践/外部案例/行业研究")

    # 时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    effective_period: Optional[str] = Field(description="有效期间")
```

### 3. 行业知识库 (Industry KB)

```python
class IndustryCategory(str, Enum):
    BEAUTY = "beauty"           # 美妆
    TECH = "tech"               # 科技
    FINANCE = "finance"         # 财经
    LIFESTYLE = "lifestyle"     # 生活方式
    EDUCATION = "education"     # 教育
    HEALTH = "health"           # 健康
    ENTERTAINMENT = "entertainment"  # 娱乐

class IndustryKnowledgeDocument(BaseModel):
    """行业知识文档"""

    id: str = Field(description="唯一标识，格式: industry-{category}-{hash}")

    # 基础信息
    category: IndustryCategory
    knowledge_type: str = Field(description="知识类型：trend/rule/best_practice/case_study")
    title: str = Field(max_length=200)
    content: str = Field(description="知识内容")

    # 适用平台
    platforms: list[Platform] = Field(default_factory=list)

    # 关键洞察
    key_insights: list[str] = Field(default_factory=list)
    dos: list[str] = Field(default_factory=list, description="推荐做法")
    donts: list[str] = Field(default_factory=list, description="避免做法")

    # 数据支撑
    data_references: list[dict] = Field(default_factory=list)
    # [
    #     {
    #         "source": "小红书官方报告",
    #         "date": "2026-03",
    #         "stat": "美妆类内容互动率平均3.2%"
    #     }
    # ]

    # 有效期
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # 元数据
    tags: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0.7)
    source: str
```

### 4. 用户画像库 (Audience KB)

```python
class AudiencePersona(BaseModel):
    """用户画像"""

    id: str = Field(description="唯一标识，格式: persona-{category}-{hash}")

    # 基础信息
    persona_name: str = Field(max_length=100, description="画像名称，如'都市白领女性'")
    category: IndustryCategory

    # 人口统计
    age_range: str = Field(description="年龄段，如'25-35'")
    gender: Optional[str] = None
    location: list[str] = Field(default_factory=list, description="地域分布")
    occupation: list[str] = Field(default_factory=list, description="职业类型")

    # 行为特征
    platform_preference: dict[str, float] = Field(default_factory=dict)
    # {"xiaohongshu": 0.8, "weibo": 0.3, ...}

    active_hours: list[str] = Field(default_factory=list, description="活跃时段")
    content_preference: list[str] = Field(default_factory=list, description="内容偏好")

    # 心理特征
    pain_points: list[str] = Field(default_factory=list, description="痛点")
    desires: list[str] = Field(default_factory=list, description="渴望")
    values: list[str] = Field(default_factory=list, description="价值观")

    # 互动模式
    engagement_triggers: list[str] = Field(default_factory=list, description="互动触发点")
    conversion_drivers: list[str] = Field(default_factory=list, description="转化驱动因素")

    # 标签
    tags: list[str] = Field(default_factory=list)

    # 数据来源
    data_sources: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, default=0.7)


class AudienceSegment(BaseModel):
    """受众细分"""

    id: str
    segment_name: str
    description: str
    persona_ids: list[str] = Field(default_factory=list)

    # 平台特定数据
    platform_segments: dict[str, dict] = Field(default_factory=dict)
    # {
    #     "xiaohongshu": {
    #         "user_count": 100000,
    #         "growth_rate": 0.15,
    #         "avg_engagement": 0.05
    #     }
    # }
```

### 5. 平台规则库 (Platform Rules KB)

```python
class RuleType(str, Enum):
    ALGORITHM = "algorithm"     # 算法规则
    CONTENT_POLICY = "content_policy"  # 内容政策
    BEST_PRACTICE = "best_practice"  # 最佳实践
    ANTI_FRAUD = "anti_fraud"   # 防刷规则

class PlatformRuleDocument(BaseModel):
    """平台规则文档"""

    id: str = Field(description="唯一标识，格式: rule-{platform}-{type}-{hash}")

    # 基础信息
    platform: Platform
    rule_type: RuleType
    title: str = Field(max_length=200)
    description: str

    # 规则内容
    rules: list[dict] = Field(default_factory=list)
    # [
    #     {
    #         "rule": "标题不超过20字",
    #         "importance": "high",
    #         "impact": "影响推荐权重"
    #     }
    # ]

    # 算法因素（针对 algorithm 类型）
    ranking_factors: list[dict] = Field(default_factory=list)
    # [
    #     {
    #         "factor": "完播率",
    #         "weight": 0.25,
    #         "optimization_tips": "前3秒抓住注意力"
    #     }
    # ]

    # 限制和约束
    limitations: dict = Field(default_factory=dict)
    # {
    #     "max_title_length": 20,
    #     "max_images": 9,
    #     "min_publish_interval": 30  # 分钟
    # }

    # 违规处理
    violations: list[dict] = Field(default_factory=list)
    # [
    #     {
    #         "violation": "标题党",
    #         "penalty": "降权",
    #         "severity": "medium"
    #     }
    # ]

    # 版本和有效期
    version: str = Field(description="规则版本")
    effective_from: datetime
    effective_until: Optional[datetime] = None

    # 来源
    source: str = Field(description="官方文档/实测/社区")
    confidence_score: float = Field(ge=0, le=1, default=0.8)
```

### 知识图谱 Schema（Neo4j）

```cypher
// 节点类型

// 爆款内容节点
CREATE CONSTRAINT viral_id IF NOT EXISTS FOR (v:ViralContent) REQUIRE v.id IS UNIQUE;

// 策略节点
CREATE CONSTRAINT strategy_id IF NOT EXISTS FOR (s:Strategy) REQUIRE s.id IS UNIQUE;

// 话题节点
CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;

// 情绪节点
CREATE CONSTRAINT emotion_name IF NOT EXISTS FOR (e:Emotion) REQUIRE e.name IS UNIQUE;

// 结构模式节点
CREATE CONSTRAINT pattern_name IF NOT EXISTS FOR (p:Pattern) REQUIRE p.name IS UNIQUE;

// 平台节点
CREATE CONSTRAINT platform_name IF NOT EXISTS FOR (p:Platform) REQUIRE p.name IS UNIQUE;

// 关系类型
// (ViralContent)-[:HAS_TOPIC]->(Topic)
// (ViralContent)-[:HAS_EMOTION]->(Emotion)
// (ViralContent)-[:USES_PATTERN]->(Pattern)
// (ViralContent)-[:PUBLISHED_ON]->(Platform)
// (Strategy)-[:APPLIES_TO]->(Platform)
// (Strategy)-[:DERIVED_FROM]->(ViralContent)
// (Topic)-[:RELATED_TO]->(Topic)
// (Pattern)-[:COMBINES_WITH]->(Pattern)
```

---

## 与 Agent 系统的集成方案

### 1. 知识服务接口设计

```python
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class SearchResult(BaseModel):
    """统一搜索结果"""
    id: str
    content: str
    metadata: dict[str, Any]
    score: float
    source: str  # viral/strategy/industry/audience/platform

class KnowledgeService(ABC):
    """知识服务基类"""

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """混合搜索"""
        pass

    @abstractmethod
    async def add_document(self, document: BaseModel) -> str:
        """添加文档"""
        pass

    @abstractmethod
    async def update_document(self, id: str, document: BaseModel) -> bool:
        """更新文档"""
        pass

    @abstractmethod
    async def delete_document(self, id: str) -> bool:
        """删除文档"""
        pass


class ViralKBService(KnowledgeService):
    """爆款内容知识库服务"""

    def __init__(
        self,
        vector_store: "VectorStore",
        bm25_index: "BM25Index",
        knowledge_graph: "KnowledgeGraph",
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.knowledge_graph = knowledge_graph

    async def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        混合搜索实现

        1. 向量搜索（语义相似）
        2. BM25 搜索（关键词匹配）
        3. 知识图谱遍历（关联发现）
        4. RRF 融合排序
        """
        # 1. 向量搜索
        vector_results = await self.vector_store.search(
            query=query,
            filters=filters,
            top_k=top_k * 2,
        )

        # 2. BM25 搜索
        bm25_results = await self.bm25_index.search(
            query=query,
            filters=filters,
            top_k=top_k * 2,
        )

        # 3. 知识图谱扩展（可选）
        graph_expansions = []
        if filters and "topic" in filters:
            graph_expansions = await self.knowledge_graph.get_related(
                topic=filters["topic"],
                depth=2,
            )

        # 4. RRF 融合
        fused_results = self._rrf_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            graph_results=graph_expansions,
            k=60,  # RRF 参数
        )

        return fused_results[:top_k]

    def _rrf_fusion(
        self,
        vector_results: list[SearchResult],
        bm25_results: list[SearchResult],
        graph_results: list[SearchResult],
        k: int = 60,
    ) -> list[SearchResult]:
        """Reciprocal Rank Fusion 算法"""
        scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        # 向量搜索得分
        for rank, result in enumerate(vector_results, 1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank)
            result_map[result.id] = result

        # BM25 搜索得分
        for rank, result in enumerate(bm25_results, 1):
            scores[result.id] = scores.get(result.id, 0) + 1 / (k + rank)
            if result.id not in result_map:
                result_map[result.id] = result

        # 知识图谱扩展得分（权重较低）
        for rank, result in enumerate(graph_results, 1):
            scores[result.id] = scores.get(result.id, 0) + 0.5 / (k + rank)
            if result.id not in result_map:
                result_map[result.id] = result

        # 排序并返回
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [result_map[id] for id in sorted_ids]
```

### 2. CrewAI Agent 集成

```python
from crewai import Agent, Task
from langchain.tools import tool

class KnowledgeTools:
    """知识库工具集，供 Agent 使用"""

    def __init__(self, kb_service: KnowledgeService):
        self.kb = kb_service

    @tool("搜索爆款案例")
    async def search_viral_examples(
        self,
        topic: str,
        platform: str,
        emotion_type: str | None = None,
        top_k: int = 5,
    ) -> str:
        """
        搜索相关爆款案例

        Args:
            topic: 主题关键词
            platform: 目标平台
            emotion_type: 情绪类型（可选）
            top_k: 返回数量

        Returns:
            爆款案例摘要（JSON格式）
        """
        filters = {"platform": platform}
        if emotion_type:
            filters["emotion_type"] = emotion_type

        results = await self.kb.search(
            query=topic,
            filters=filters,
            top_k=top_k,
        )

        # 格式化为 Agent 可理解的文本
        summaries = []
        for r in results:
            summaries.append(f"""
## {r.metadata.get('title', '未知标题')}
- 平台: {r.metadata.get('platform')}
- 数据: {r.metadata.get('metrics')}
- 结构: {r.metadata.get('structure_analysis')}
- 情绪: {r.metadata.get('emotion_analysis')}
- 链接: {r.metadata.get('url')}
""")

        return "\n---\n".join(summaries)

    @tool("获取平台规则")
    async def get_platform_rules(
        self,
        platform: str,
        rule_type: str = "algorithm",
    ) -> str:
        """
        获取平台规则和最佳实践

        Args:
            platform: 平台名称
            rule_type: 规则类型 (algorithm/content_policy/best_practice)

        Returns:
            规则摘要
        """
        results = await self.kb.search(
            query=f"{platform} {rule_type} 规则",
            filters={"platform": platform, "rule_type": rule_type},
            top_k=3,
        )
        return "\n".join([r.content for r in results])

    @tool("查询用户画像")
    async def get_audience_persona(
        self,
        category: str,
        platform: str,
    ) -> str:
        """
        查询目标用户画像

        Args:
            category: 内容垂类
            platform: 目标平台

        Returns:
            用户画像描述
        """
        results = await self.kb.search(
            query=f"{category} {platform} 用户画像",
            filters={"category": category},
            top_k=3,
        )
        return "\n".join([r.content for r in results])


# Agent 工厂函数
def create_content_creator_agent(kb_service: KnowledgeService) -> Agent:
    """创建内容创作者 Agent，注入知识库工具"""
    tools = KnowledgeTools(kb_service)

    return Agent(
        role="内容创作者",
        goal="根据选题和平台特性创作高质量、高传播力的内容",
        backstory="""
        你是一位全能型内容创作者，擅长撰写各类风格的文案。
        你能根据不同平台的调性调整写作风格，同时保证内容的原创性和吸引力。
        在创作前，你会先搜索爆款案例作为参考，确保内容有传播潜力。
        """,
        tools=[
            tools.search_viral_examples,
            tools.get_platform_rules,
            tools.get_audience_persona,
        ],
        verbose=True,
    )
```

### 3. 数据摄入 Pipeline

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import asyncio

@dataclass
class IngestionTask:
    """数据摄入任务"""
    source: str  # 数据来源
    data: dict[str, Any]
    priority: int = 0  # 优先级，0 最高
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class DataIngestionPipeline:
    """数据摄入管道"""

    def __init__(
        self,
        viral_kb: ViralKBService,
        strategy_kb: "StrategyKBService",
        embedding_service: "EmbeddingService",
    ):
        self.viral_kb = viral_kb
        self.strategy_kb = strategy_kb
        self.embedding_service = embedding_service
        self._queue: asyncio.Queue[IngestionTask] = asyncio.Queue()

    async def ingest_viral_content(
        self,
        content_data: dict[str, Any],
        incremental: bool = True,
    ) -> str:
        """
        摄入爆款内容

        Args:
            content_data: 爆款内容数据
            incremental: 是否增量更新

        Returns:
            文档ID
        """
        # 1. 数据清洗和验证
        document = ViralContentDocument(**content_data)

        # 2. 生成嵌入向量
        text_to_embed = f"{document.title}\n{document.content_summary}\n{document.content_text}"
        embedding = await self.embedding_service.embed(text_to_embed)

        # 3. 提取元数据
        payload = {
            "platform": document.platform.value,
            "category": document.category,
            "emotion_type": document.emotion_type,
            "has_video": document.content_type == ContentType.VIDEO,
            "likes_bucket": self._bucket_likes(document.metrics.get("likes", 0)),
            "publish_date": document.published_at.strftime("%Y-%m-%d"),
        }

        # 4. 存入向量数据库
        if incremental:
            # 检查是否已存在
            existing = await self.viral_kb.get_by_url(document.url)
            if existing:
                # 更新
                await self.viral_kb.vector_store.update(
                    id=existing.id,
                    vector=embedding,
                    payload=payload,
                )
                return existing.id

        # 新增
        doc_id = await self.viral_kb.vector_store.add(
            id=document.id,
            vector=embedding,
            payload=payload,
        )

        # 5. 更新 BM25 索引
        await self.viral_kb.bm25_index.add(
            id=document.id,
            text=f"{document.title} {document.content_summary} {' '.join(document.hashtags)}",
            metadata=payload,
        )

        # 6. 更新知识图谱
        await self._update_knowledge_graph(document)

        return doc_id

    async def _update_knowledge_graph(self, document: ViralContentDocument):
        """更新知识图谱"""
        # 创建内容节点
        await self.viral_kb.knowledge_graph.merge_node(
            label="ViralContent",
            id=document.id,
            properties={
                "title": document.title,
                "platform": document.platform.value,
                "likes": document.metrics.get("likes", 0),
            },
        )

        # 创建/关联话题节点
        for topic in document.topics:
            await self.viral_kb.knowledge_graph.merge_node(
                label="Topic",
                id=topic,
                properties={"name": topic},
            )
            await self.viral_kb.knowledge_graph.merge_relation(
                from_id=document.id,
                relation="HAS_TOPIC",
                to_id=topic,
            )

        # 创建/关联情绪节点
        if document.emotion_type:
            await self.viral_kb.knowledge_graph.merge_node(
                label="Emotion",
                id=document.emotion_type,
                properties={"name": document.emotion_type},
            )
            await self.viral_kb.knowledge_graph.merge_relation(
                from_id=document.id,
                relation="HAS_EMOTION",
                to_id=document.emotion_type,
            )

    def _bucket_likes(self, likes: int) -> str:
        """将点赞数分桶"""
        if likes < 1000:
            return "0-1k"
        elif likes < 5000:
            return "1k-5k"
        elif likes < 10000:
            return "5k-10k"
        elif likes < 50000:
            return "10k-50k"
        elif likes < 100000:
            return "50k-100k"
        else:
            return "100k+"

    async def start_worker(self):
        """启动后台摄入工作进程"""
        while True:
            task = await self._queue.get()
            try:
                if task.source == "viral":
                    await self.ingest_viral_content(task.data)
                elif task.source == "strategy":
                    await self.strategy_kb.add_document(task.data)
                # ... 其他类型
            except Exception as e:
                # 错误处理
                print(f"Ingestion error: {e}")
            finally:
                self._queue.task_done()
```

### 4. 增量更新和版本管理

```python
from datetime import datetime
from typing import Optional
import hashlib

class VersionedKnowledgeBase:
    """版本化知识库"""

    def __init__(self, kb_service: KnowledgeService):
        self.kb = kb_service
        self._version_cache: dict[str, str] = {}  # id -> content_hash

    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def upsert_document(
        self,
        document: BaseModel,
        force_update: bool = False,
    ) -> tuple[str, bool]:
        """
        增量更新文档

        Returns:
            (文档ID, 是否更新)
        """
        doc_id = document.id
        content_hash = self._compute_hash(document.model_dump_json())

        # 检查是否需要更新
        if not force_update and doc_id in self._version_cache:
            if self._version_cache[doc_id] == content_hash:
                return doc_id, False  # 无变化

        # 执行更新
        if doc_id in self._version_cache:
            await self.kb.update_document(doc_id, document)
        else:
            await self.kb.add_document(document)

        # 更新缓存
        self._version_cache[doc_id] = content_hash
        return doc_id, True

    async def sync_from_external(
        self,
        external_source: "ExternalDataSource",
        last_sync: Optional[datetime] = None,
    ) -> dict[str, int]:
        """
        从外部源同步数据

        Args:
            external_source: 外部数据源
            last_sync: 上次同步时间

        Returns:
            同步统计
        """
        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

        async for item in external_source.fetch(since=last_sync):
            try:
                doc_id, updated = await self.upsert_document(item)
                if updated:
                    if doc_id in self._version_cache:
                        stats["updated"] += 1
                    else:
                        stats["added"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                stats["errors"] += 1

        return stats


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self):
        self.viral_kb: Optional[ViralKBService] = None
        self.strategy_kb: Optional["StrategyKBService"] = None
        self.industry_kb: Optional["IndustryKBService"] = None
        self.audience_kb: Optional["AudienceKBService"] = None
        self.platform_kb: Optional["PlatformKBService"] = None

    async def initialize(self):
        """初始化所有知识库"""
        # 初始化向量存储
        vector_store = await self._init_vector_store()

        # 初始化 BM25 索引
        bm25_index = await self._init_bm25_index()

        # 初始化知识图谱
        knowledge_graph = await self._init_knowledge_graph()

        # 创建各知识库服务
        self.viral_kb = ViralKBService(vector_store, bm25_index, knowledge_graph)
        # ... 其他知识库

    async def full_sync(self):
        """全量同步"""
        tasks = [
            self._sync_viral_content(),
            self._sync_strategies(),
            self._sync_industry_knowledge(),
            self._sync_audience_data(),
            self._sync_platform_rules(),
        ]
        await asyncio.gather(*tasks)

    async def incremental_sync(self, since: datetime):
        """增量同步"""
        # 只同步有变化的数据
        pass
```

---

## 实施路线图

### Phase 1: 基础设施（2周）

**目标**：搭建核心存储和检索基础设施

**任务**：
1. 部署 Qdrant 向量数据库
2. 实现 BM25 索引（Whoosh 或自定义）
3. 设计并实现基础 Schema
4. 实现 Embedding 服务

**交付物**：
- 向量数据库运行
- 基础 CRUD API
- Embedding 服务

### Phase 2: 知识库核心（3周）

**目标**：实现 5 大知识库的基础功能

**任务**：
1. 实现爆款内容库
   - 数据摄入 Pipeline
   - 混合搜索
   - 与现有 viral_reference.py 集成

2. 实现运营策略库
   - 策略文档结构
   - 案例关联

3. 实现行业知识库
   - 垂类知识结构
   - 规则和洞察

4. 实现用户画像库
   - 画像数据结构
   - 平台细分

5. 实现平台规则库
   - 规则文档结构
   - 版本管理

**交付物**：
- 5 大知识库服务
- 统一搜索 API
- 数据摄入 Pipeline

### Phase 3: Agent 集成（2周）

**目标**：将知识库集成到 CrewAI Agent 系统

**任务**：
1. 实现 KnowledgeTools 工具集
2. 更新现有 Agent 注入知识库工具
3. 实现上下文增强（检索增强生成）
4. 优化检索性能

**交付物**：
- Agent 工具集成
- RAG Pipeline
- 性能基准

### Phase 4: 知识图谱（2周）

**目标**：实现知识图谱增强

**任务**：
1. 部署 Neo4j 或实现轻量图存储
2. 实现实体抽取
3. 实现关系推理
4. 集成到混合搜索

**交付物**：
- 知识图谱存储
- 图谱增强搜索
- 可视化界面（可选）

### Phase 5: 运维和优化（持续）

**目标**：持续优化和运维

**任务**：
1. 实现增量更新机制
2. 实现数据质量监控
3. 优化检索效果
4. 扩展知识类型

---

## 参考资源

### 向量数据库
- [Qdrant 官方文档](https://qdrant.tech/documentation/)
- [Weaviate 文档](https://weaviate.io/developers/weaviate)
- [Pinecone 对比指南](https://www.buildmvpfast.com/blog/pinecone-vs-weaviate-vs-qdrant-vector-database-comparison-2026)
- [向量数据库对比 2026](https://encore.dev/articles/best-vector-databases)

### RAG 框架
- [LlamaIndex GraphRAG 实现](https://developers.llamaindex.ai/python/examples/cookbooks/graphrag_v2/)
- [LlamaIndex Neo4j 集成](https://developers.llamaindex.ai/python/examples/index_structs/knowledge_graph/neo4jkgindexdemo/)
- [LangChain RAG 最佳实践](https://python.langchain.com/docs/use_cases/question_answering/)
- [Hybrid Search RAG](https://medium.com/@abheshith7/hybrid-search-rag-combining-keyword-and-semantic-search-for-enhanced-retrieval-e594b49647e5)

### 知识图谱
- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [Neo4j GraphRAG Python](https://neo4j.com/blog/developer/knowledge-graphs-neo4j-graphrag-for-python/)
- [Neo4j + LlamaIndex](https://neo4j.com/developer/genai-ecosystem/llamaindex/)

### Embedding 模型
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Embedding 模型对比 2025](https://ingestiq.ai/resources/curation/best-embedding-models-2025)

### 增量更新
- [增量索引策略](https://medium.com/@vasanthancomrads/incremental-indexing-strategies-for-large-rag-systems-e3e5a9e2ced7)
- [实时 RAG 更新](https://articles.chatnexus.io/knowledge-base/real-time-learning-rag-systems-that-update-knowledge-intantly/)
- [Milvus 增量索引](https://milvus.io/ai-quick-reference/how-does-incremental-indexing-or-periodic-batch-indexing-help-in-handling-continuously-growing-large-datasets-and-what-are-the-limitations-of-these-approaches)

### Agent 知识库集成
- [Agent 知识库模式](https://thenewstack.io/agentic-knowledge-base-patterns/)
- [向量数据库 Agent 记忆](https://medium.com/towardsdev/how-vector-databases-enable-ai-agents-to-remember-and-retrieve-knowledge-4d51ebde252e)
- [AWS Bedrock Knowledge Bases](https://aws.amazon.com/blogs/machine-learning/dive-deep-into-vector-data-stores-using-amazon-bedrock-knowledge-bases/)

---

## 附录：技术选型决策记录

### ADR-001: 选择 Qdrant 作为向量数据库

**背景**：需要在 Windows 环境下部署向量数据库，支持生产级负载。

**考虑的选项**：
1. Chroma - 轻量，但依赖 lancedb（不支持 Windows）
2. Pinecone - 托管服务，但闭源且成本高
3. Qdrant - 开源，Rust 实现，支持 Windows
4. Milvus - 功能强大，但运维复杂

**决策**：选择 Qdrant

**理由**：
- 开源，可自托管
- Rust 实现，高性能
- 支持 Windows（通过 WSL 或 Docker）
- 云服务价格合理（$120-250/月）
- API 设计清晰，Python SDK 成熟

### ADR-002: 选择 LlamaIndex 作为 RAG 框架

**背景**：需要实现复杂的文档索引和检索逻辑。

**考虑的选项**：
1. LangChain - 通用框架，但 RAG 抽象不够深入
2. LlamaIndex - RAG 专用，索引策略丰富
3. Haystack - 生产就绪，但社区较小

**决策**：选择 LlamaIndex，配合 LangChain

**理由**：
- LlamaIndex 专注 RAG，数据连接器丰富
- 支持多种索引策略（tree, vector, keyword）
- 与 LangChain 可无缝集成
- GraphRAG 支持完善

### ADR-003: 选择 BGE-M3 作为中文 Embedding 模型

**背景**：需要为中文内容生成高质量的嵌入向量。

**考虑的选项**：
1. OpenAI text-embedding-3-large - 通用强，但成本高
2. Cohere embed-v4 - 多语言好，但需要 API
3. BGE-M3 - 开源，中文效果优

**决策**：选择 BGE-M3

**理由**：
- 开源免费
- 中文效果在 MTEB 排名靠前
- 支持多语言
- 可本地部署，保护隐私

---

*文档版本：1.0*
*最后更新：2026-03-28*
