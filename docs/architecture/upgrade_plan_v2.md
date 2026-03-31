# Crew Media Ops 升级计划 V2

> 从"内容发布工具"升级为"全自动化 AI 运营系统"

---

## 🎯 升级愿景

**目标用户**：小白用户、创业者、企业老板

**核心价值**：输入模糊需求 → AI 澄清确认 → 自动化全平台运营 → 数据驱动迭代

```
用户: "帮我做 AI 创业相关的运营"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  AI: "好的，让我了解一下您的需求..."                         │
│  1. 目标平台？  2. 内容风格？  3. 发布频率？  4. 目标受众？    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  AI 自动执行：                                               │
│  🔍 热点探测 → 📊 爆款分析 → 📝 内容创作 → 📤 多平台发布      │
│  📈 数据采集 → 🔄 策略迭代                                   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
    周报: "本周发布 12 篇，总曝光 50w+，建议下周增加..."
```

---

## 📋 优先级总览

| 优先级 | 模块 | 核心价值 | 工作量 | 依赖 |
|--------|------|----------|--------|------|
| **P0** | 上下文管理 | Agent 间数据可追溯 | 3 天 | 无 |
| **P0** | ContentCreator 用户引导 | 小白用户可用 | 5 天 | P0-1 |
| **P0** | 任务持久化 | 服务重启不丢任务 | 2 天 | 无 |
| **P1** | 知识库系统 | 爆款经验积累 | 5 天 | P0 |
| **P1** | 数据采集 | 发布后追踪效果 | 3 天 | P0 |
| **P1** | 策略迭代 | 自动优化内容 | 3 天 | P1 |
| **P2** | 工作流引擎 | 长时间运行任务 | 5 天 | P0 |
| **P2** | 知识图谱 | 话题关联分析 | 4 天 | P1 |
| **P3** | 可观测性 | 问题排查 | 3 天 | P2 |

---

## 🔴 P0 - 必须做（MVP 核心）

> 没有 P0，系统无法满足"小白用户自动化运营"的核心需求

### P0-1: 上下文管理系统

**问题**：Agent 间上下文传递不可追溯，无法调试

**价值**：
- 每个 Agent 的输出有完整记录
- 可追溯：知道某个数据来自哪个 Agent
- 可调试：失败时可复现

**工作量**：3 天

**实现**：
```python
# src/core/context_manager.py

@dataclass
class ContextSnapshot:
    key: str
    value: Any
    source_agent: str
    timestamp: datetime
    metadata: dict

class ContextManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context: dict[str, Any] = {}
        self.history: list[ContextSnapshot] = []

    def set(self, key: str, value: Any, source: str, **metadata) -> None:
        """设置上下文，记录来源"""
        self.context[key] = value
        self.history.append(ContextSnapshot(key, value, source, datetime.now(), metadata))

    def get(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)

    def get_trace(self, key: str) -> list[ContextSnapshot]:
        """获取某个 key 的完整变更历史"""
        return [s for s in self.history if s.key == key]

    def export(self) -> dict:
        """导出完整上下文（用于持久化）"""
        return {"session_id": self.session_id, "context": self.context, "history": [...]}

    @classmethod
    def restore(cls, data: dict) -> "ContextManager":
        """从持久化数据恢复"""
        ...
```

**集成点**：
- `ContentOrchestrator.orchestrate()` - 传入 ContextManager
- 所有 Agent 的 `execute()` 方法 - 读取/写入上下文

---

### P0-2: ContentCreator 用户引导

**问题**：当前只有 API，用户需要懂技术才能用

**方案**：将用户引导功能集成到 ContentCreator Agent 内部，作为创作流程的第一阶段

**价值**：
- 小白用户通过对话完成全流程
- 不新增独立模块，复用现有 Agent 架构
- 引导 → 研究 → 创作 一体化

**工作量**：5 天

**ContentCreator 新增阶段**：
```
ContentCreator Agent
├── Phase 0: 需求引导（新增）     ← 小白用户交互
│   ├── 槽位收集（topic, platforms, style, frequency）
│   ├── 模糊需求澄清（LLM 理解用户意图）
│   └── 确认需求摘要
│
├── Phase 1: 爆款研究（现有）
│   ├── 热点探测
│   ├── 爆款分析（5 维度）
│   └── 模式提取
│
└── Phase 2: 内容创作（现有）
    ├── 标题生成
    ├── 正文撰写
    └── 标签提取
```

**实现**：
```python
# src/agents/content_creator.py

class ContentCreator(BaseAgent):
    """内容创作者 Agent - 包含用户引导功能"""

    role = "内容创作顾问"
    goal = "通过友好对话帮助用户明确运营需求，然后研究热点并创作高质量内容"
    backstory = """你是一位全能型内容创作顾问，擅长：
    1. 引导不懂运营的小白用户明确需求
    2. 追踪热点趋势、分析爆款内容结构
    3. 创作高质量内容
    """

    # 槽位定义
    REQUIRED_SLOTS = {
        "topic": "内容主题",
        "platforms": "目标平台",
    }
    OPTIONAL_SLOTS = {
        "content_style": {"default": "专业但不失亲和", "desc": "内容风格"},
        "publish_frequency": {"default": "daily", "desc": "发布频率"},
        "target_audience": {"default": None, "desc": "目标受众"},
    }

    def __init__(self):
        super().__init__()
        self.slots: dict = {}
        self.guidance_complete: bool = False

    def guide_user(self, user_input: str, context: ContextManager) -> dict:
        """
        引导用户完成需求收集。

        Returns:
            {
                "status": "collecting" | "confirming" | "ready",
                "message": "AI 回复",
                "slots": 当前已收集的槽位,
            }
        """
        # 1. 从用户输入提取槽位
        extracted = self._extract_slots(user_input)
        self.slots.update(extracted)

        # 2. 检查缺失的必填槽位
        missing = [s for s in self.REQUIRED_SLOTS if s not in self.slots]

        if missing:
            return {
                "status": "collecting",
                "message": self._ask_for_slot(missing[0]),
                "slots": self.slots,
            }

        # 3. 确认
        if not self.guidance_complete:
            return {
                "status": "confirming",
                "message": self._build_confirmation(),
                "slots": self.slots,
            }

        # 4. 写入上下文，准备执行
        for k, v in self.slots.items():
            context.set(k, v, source="ContentCreator.guide_user")

        return {"status": "ready", "message": "开始执行...", "slots": self.slots}

    def confirm(self, approved: bool) -> None:
        self.guidance_complete = approved
```

**用户体验**：
```
用户: 帮我做 AI 运营
ContentCreator: 好的！请选择目标平台：
               [小红书] [微博] [知乎] [抖音] [B站]

用户: 小红书和知乎
ContentCreator: 收到。内容风格偏好？
               [专业科普] [轻松幽默] [故事化] [自动推荐]

用户: 自动推荐
ContentCreator: 确认您的需求：
               📝 主题：AI 运营
               📱 平台：小红书、知乎
               🎨 风格：自动推荐（专业科普+案例）
               确认开始？[确认] [修改]

用户: 确认
ContentCreator: 🚀 开始执行！
               🔍 正在探测热点...
               📊 发现"AI Agent"热度上升 230%
               📝 正在创作第 1/3 篇内容...
```

**依赖**：P0-1（上下文管理）

---

### P0-3: 任务持久化

**问题**：APScheduler 内存调度，服务重启丢失任务

**价值**：
- 定时任务不会丢失
- 崩溃后可恢复

**工作量**：2 天

**快速方案**（APScheduler + PostgreSQL）：
```python
# src/services/scheduler.py

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url='postgresql://localhost/crew')
}

scheduler = BackgroundScheduler(jobstores=jobstores)
```

**完整方案**（Temporal，见 P2-1）：
- 长时间运行的工作流
- 复杂的状态管理
- 人工审批节点

---

## 🟡 P1 - 应该做（核心增强）

> P1 让系统具备"学习能力"和"数据驱动"能力

### P1-1: RAG 知识库系统

**问题**：无知识积累，每次创作从零开始

**价值**：
- 爆款案例积累（越用越聪明）
- 运营策略沉淀
- 平台规则知识

**工作量**：5 天

**技术选型**：
| 组件 | 选择 | 理由 |
|------|------|------|
| 向量数据库 | Qdrant | 开源、Rust 高性能、支持 Windows |
| Embedding | BGE-M3 | 开源免费、中文效果好 |
| RAG 框架 | LlamaIndex | 专注 RAG 索引 |

**实现**：
```python
# src/knowledge/base.py

class KnowledgeBase:
    COLLECTIONS = {
        "viral_content": "爆款内容库",
        "strategies": "运营策略库",
        "platform_rules": "平台规则库",
    }

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=qdrant_url)
        self.embedder = SentenceTransformer("BAAI/bge-m3")

    def add_viral_content(self, content: ViralContentDocument) -> None:
        vector = self.embedder.encode(f"{content.title}\n{content.content}")
        self.client.upsert(collection_name="viral_content", points=[...])

    def search_similar_viral(self, query: str, platform: str | None = None) -> list[dict]:
        vector = self.embedder.encode(query)
        return self.client.search(collection_name="viral_content", query_vector=vector, ...)
```

**依赖**：P0-1（上下文管理）

---

### P1-2: 数据采集系统

**问题**：发布后无数据追踪，无法评估效果

**价值**：
- 自动采集发布后的数据
- 支持策略优化
- 生成周报

**工作量**：3 天

**采集策略**：
```python
COLLECTION_SCHEDULE = {
    "realtime": {  # 发布后 24 小时内
        "interval": "15min",
        "metrics": ["views", "likes", "comments"]
    },
    "frequent": {  # 第 2-7 天
        "interval": "2h",
        "metrics": ["views", "likes", "comments", "shares", "saves"]
    },
    "daily": {  # 第 8-30 天
        "interval": "24h",
        "metrics": ["all"]
    }
}
```

**依赖**：P0-3（任务持久化）

---

### P1-3: 策略迭代系统

**问题**：无法根据数据自动优化内容策略

**价值**：
- 自动发现最佳标题风格
- 自动发现最佳发布时间
- 自动发现最佳内容结构

**工作量**：3 天

**实现**（Thompson Sampling）：
```python
# src/analytics/bandit.py

class ContentStrategyBandit:
    """多臂老虎机 - 策略优化"""

    def __init__(self, arms: list[str]):
        self.arms = arms
        self.alpha = np.ones(len(arms))  # 成功次数
        self.beta = np.ones(len(arms))   # 失败次数

    def select_arm(self) -> str:
        """选择策略（探索 vs 利用）"""
        samples = np.random.beta(self.alpha, self.beta)
        return self.arms[np.argmax(samples)]

    def update(self, arm: str, reward: float) -> None:
        """更新策略效果"""
        idx = self.arms.index(arm)
        self.alpha[idx] += reward
        self.beta[idx] += (1 - reward)

# 使用示例
title_bandit = ContentStrategyBandit(
    arms=["question", "listicle", "how_to", "controversial"]
)

selected_style = title_bandit.select_arm()
# ... 发布内容 ...
engagement_rate = 0.08
title_bandit.update(selected_style, engagement_rate)
```

**依赖**：P1-2（数据采集）

---

## 🟢 P2 - 可以做（进阶特性）

> P2 让系统更健壮、更智能

### P2-1: Temporal 工作流引擎

**问题**：APScheduler 无法处理长时间运行、复杂状态的工作流

**价值**：
- 工作流可运行数天/数周
- 崩溃自动恢复
- 人工审批节点
- 完整执行历史

**工作量**：5 天

**何时需要**：
- 需要人工审核内容后再发布
- 需要等待用户确认（可能等几天）
- 工作流超过 1 小时

**暂时替代**：P0-3 的 APScheduler + PostgreSQL 方案

---

### P2-2: 知识图谱

**问题**：向量搜索只能找相似内容，无法发现关联关系

**价值**：
- 话题关联分析（"AI创业" → "AI Agent" → "大模型"）
- 爆款传播路径分析
- 竞品关系图谱

**工作量**：4 天

**技术选型**：Neo4j

**暂时替代**：Qdrant 的 payload 过滤 + 手动关联

---

## 🔵 P3 - 未来做（锦上添花）

### P3-1: 可观测性系统

**内容**：OpenTelemetry + Grafana + 告警

**工作量**：3 天

### P3-2: 多租户支持

**内容**：支持多个用户/团队独立使用

**工作量**：5 天

### P3-3: 移动端

**内容**：微信小程序 / App

**工作量**：10 天

---

## 📅 实施计划

### 第 1 周：P0 基础

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 1-2 | P0-1 上下文管理 | `src/core/context_manager.py` |
| Day 3-4 | P0-2 ContentCreator 用户引导 | `src/agents/content_creator.py` 新增 guide_user() |
| Day 5 | P0-3 任务持久化 | APScheduler + PostgreSQL |

### 第 2 周：P0 完成 + P1 启动

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 1-2 | P0-2 ContentCreator 引导（完善） | 槽位提取 + LLM 澄清逻辑 |
| Day 3-4 | P1-1 知识库（Qdrant） | `src/knowledge/base.py` |
| Day 5 | P1-1 知识库（Schema） | 5 大知识库 Schema |

### 第 3 周：P1 完成

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 1-2 | P1-2 数据采集 | `src/analytics/collector.py` |
| Day 3-4 | P1-3 策略迭代 | `src/analytics/bandit.py` |
| Day 5 | 集成测试 | E2E 测试通过 |

### 第 4 周：P2 / 打磨

| 天数 | 任务 | 交付物 |
|------|------|--------|
| Day 1-3 | P2-1 Temporal（可选） | `src/workflows/` |
| Day 4-5 | 性能优化 + 文档 | README + API 文档 |

---

## 🏗️ 架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CREW MEDIA OPS V2 架构                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  交互层                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                          │
│  │  Web Chat    │    │  REST API    │    │  WebSocket   │                          │
│  │  (前端)      │    │  (现有)      │    │  (进度推送)  │                          │
│  └──────────────┘    └──────────────┘    └──────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  编排层                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  ContextManager (P0-1) - 显式上下文管理                                      │   │
│  │  - 追踪所有 Agent 的输入输出                                                 │   │
│  │  - 支持调试和复现                                                            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  CrewAI Agents                                                               │   │
│  │  ContentCreator (P0-2, 含用户引导) → Reviewer → Publisher                   │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                         │                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  任务调度                                                                    │   │
│  │  - P0-3: APScheduler + PostgreSQL (快速方案)                                 │   │
│  │  - P2-1: Temporal Workflows (完整方案)                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  知识层 (P1-1)                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  爆款内容库  │  │  运营策略库  │  │  平台规则库  │  │  用户画像库  │           │
│  │  (Qdrant)    │  │  (Qdrant)    │  │  (Qdrant)    │  │  (Qdrant)    │           │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  数据层 (P1-2, P1-3)                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                              │
│  │  数据采集    │  │  策略优化    │  │  周报生成    │                              │
│  │  (P1-2)      │  │  (P1-3)      │  │  (P1-3)      │                              │
│  └──────────────┘  └──────────────┘  └──────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  基础设施层                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  PostgreSQL  │  │   Qdrant     │  │   Redis      │  │  Playwright  │           │
│  │  (P0-3)      │  │  (P1-1)      │  │  (缓存)      │  │  (现有)      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 技术栈

### 新增依赖

```toml
# P0
"apscheduler>=3.10.0",
"sqlalchemy>=2.0.0",
"psycopg2-binary>=2.9.0",

# P1
"qdrant-client>=1.10.0",
"sentence-transformers>=3.0.0",
"llama-index>=0.10.0",
"numpy>=2.0.0",

# P2
"temporalio>=1.5.0",
"neo4j>=5.0.0",

# P3
"opentelemetry-api>=1.20.0",
```

### 基础设施

```yaml
# docker-compose.yml (最小化版本)
services:
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: crew
      POSTGRES_PASSWORD: crew
      POSTGRES_DB: crew

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

---

## ✅ 成功指标

| 指标 | 当前 | P0 完成后 | P1 完成后 |
|------|------|-----------|-----------|
| 小白用户可用性 | ❌ 需懂 API | ✅ 对话交互 | ✅ |
| 任务持久化 | ❌ 内存 | ✅ PostgreSQL | ✅ |
| 知识积累 | ❌ 无 | ❌ | ✅ Qdrant |
| 数据驱动 | ❌ 无 | ❌ | ✅ Bandit |
| 策略迭代 | ❌ 手动 | ❌ | ✅ 自动 |

---

## 🚀 立即可做

### 本周任务

1. **P0-1 上下文管理** (Day 1-2)
   ```bash
   # 创建文件
   touch src/core/context_manager.py
   ```

2. **P0-3 任务持久化** (Day 3)
   ```bash
   # 启动 PostgreSQL
   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=crew postgres:16

   # 修改调度器配置
   # src/services/scheduler.py
   ```

3. **P0-2 ContentCreator 用户引导** (Day 4-5)
   ```bash
   # 修改现有文件，新增 guide_user() 方法
   # src/agents/content_creator.py
   ```

### 需要确认

1. **部署环境**：本地 Docker 还是云服务器？
2. **UI 方案**：自建 Web Chat 还是接入飞书/钉钉？
3. **知识库种子数据**：需要我先采集一批爆款案例吗？

---

_文档版本：v2.1 | 更新时间：2026-03-28_
