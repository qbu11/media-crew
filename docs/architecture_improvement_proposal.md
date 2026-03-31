# Crew Media Ops 架构改进方案

> 基于 multi-agent-social-media-automation 项目的学习，为 Crew Media Ops 提出架构升级建议。

---

## 1. 两个项目对比分析

### 1.1 架构对比

| 维度 | Crew Media Ops (当前) | multi-agent-social-media-automation (参考) |
|------|----------------------|-------------------------------------------|
| **Agent 框架** | CrewAI | LangGraph |
| **工作流编排** | 纯代码 | n8n (可视化) |
| **数据持久化** | SQLite (基础) | PostgreSQL (完整) |
| **Agent 数量** | 5 个 | 7 个 |
| **通信方式** | 直接调用 | Webhook + REST API |
| **可观测性** | 基础日志 | 完整监控 + 告警 |
| **开发周期** | 已完成 | 3-4 周 |
| **月成本** | ~$50-150 | ~$80-375 |

### 1.2 Agent 职责对比

| Crew Media Ops Agent | 职责 | 对应参考项目 Agent |
|---------------------|------|-------------------|
| ContentCreator | 研究 + 创作 | Researcher + Marketer + Copywriter |
| ContentReviewer | 审核 | Moderator |
| PlatformAdapter | 平台适配 | (内置在 Scheduler) |
| PlatformPublisher | 发布 | Scheduler |
| DataAnalyst | 数据分析 | Analytical |
| - | - | Designer (图片生成) |

**关键差距**：
1. **缺少专门的 Designer Agent** - 图片生成目前在平台工具中处理
2. **ContentCreator 职责过重** - 混合了研究、营销策略、文案创作
3. **缺少调度层** - 没有 n8n 这样的可视化编排

---

## 2. 改进方案

### 2.1 方案 A：轻量级改进（推荐优先）

保持 CrewAI 框架，引入关键改进。

#### 2.1.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  REST API Routes                                         ││
│  │  /api/v1/agents/*  /api/v1/crews/*  /api/v1/content/*   ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  WebSocket Hub (实时状态推送)                            ││
│  └─────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────────────┐
│                   CrewAI Runtime Layer                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ContentCrew │ │PublishCrew │ │AnalyticsCrew│              │
│  │            │ │            │ │            │              │
│  │ Creator    │ │ Adapter    │ │ Collector  │              │
│  │ Reviewer   │ │ Publisher  │ │ Analyzer   │              │
│  └────────────┘ └────────────┘ └────────────┘              │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────────────┐
│                   PostgreSQL Database                        │
│  content_drafts | publish_logs | analytics | recommendations │
└─────────────────────────────────────────────────────────────┘
```

#### 2.1.2 关键改进点

1. **Agent 职责拆分（可选）**
   ```python
   # 将 ContentCreator 拆分为更细粒度的 Agent
   class ResearcherAgent(BaseAgent):
       """热点研究员 - 专注趋势分析、竞品分析"""
       role = "热点研究员"
       tools = ["hot_search", "trend_analysis", "competitor_analysis"]

   class MarketerAgent(BaseAgent):
       """营销策划师 - 专注内容策略、平台适配策略"""
       role = "营销策划师"
       tools = ["strategy_planner", "audience_analyzer"]

   class CopywriterAgent(BaseAgent):
       """文案创作者 - 专注文案生成、A/B 测试变体"""
       role = "文案创作者"
       tools = ["content_generator", "style_adapter"]

   class DesignerAgent(BaseAgent):
       """视觉设计师 - 专注图片生成、封面设计"""
       role = "视觉设计师"
       tools = ["dalle_generator", "image_optimizer"]
   ```

2. **引入 PostgreSQL 持久化**
   ```sql
   -- 核心表结构
   CREATE TABLE content_drafts (
       id SERIAL PRIMARY KEY,
       topic VARCHAR(255) NOT NULL,
       platform VARCHAR(50) NOT NULL,
       content_type VARCHAR(50),
       title VARCHAR(255),
       body TEXT,
       tags JSONB,
       viral_references JSONB,
       status VARCHAR(20) DEFAULT 'draft',
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE publish_logs (
       id SERIAL PRIMARY KEY,
       content_id INTEGER REFERENCES content_drafts(id),
       platform VARCHAR(50) NOT NULL,
       status VARCHAR(20),
       published_url VARCHAR(500),
       published_at TIMESTAMP,
       error_message TEXT,
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE analytics (
       id SERIAL PRIMARY KEY,
       publish_log_id INTEGER REFERENCES publish_logs(id),
       views INTEGER DEFAULT 0,
       likes INTEGER DEFAULT 0,
       comments INTEGER DEFAULT 0,
       shares INTEGER DEFAULT 0,
       engagement_rate FLOAT,
       collected_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE recommendations (
       id SERIAL PRIMARY KEY,
       content_id INTEGER REFERENCES content_drafts(id),
       recommendation_type VARCHAR(50),
       content TEXT,
       priority INTEGER,
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```

3. **Webhook 支持**
   ```python
   # api/webhooks.py
   from fastapi import APIRouter, BackgroundTasks

   router = APIRouter(prefix="/webhook", tags=["webhooks"])

   @router.post("/content-approved")
   async def content_approved(
       content_id: int,
       background_tasks: BackgroundTasks
   ):
       """内容审核通过后触发发布"""
       background_tasks.add_task(
           trigger_publish_crew,
           content_id=content_id
       )
       return {"status": "queued"}

   @router.post("/content-rejected")
   async def content_rejected(content_id: int, reason: str):
       """内容审核拒绝后触发重新创作"""
       # 可以触发重新创作流程
       return {"status": "queued_for_revision"}

   @router.post("/post-published")
   async def post_published(
       content_id: int,
       platform: str,
       published_url: str
   ):
       """发布成功后记录"""
       # 更新数据库状态
       return {"status": "recorded"}

   @router.post("/analytics-ready")
   async def analytics_ready(content_id: int):
       """24小时后触发数据采集"""
       # 启动数据采集任务
       return {"status": "queued"}
   ```

4. **Agent 状态端点**
   ```python
   # api/routes/agents.py
   @router.get("/agents/status")
   async def get_agents_status():
       """获取所有 Agent 状态"""
       return {
           "agents": [
               {
                   "name": "ContentCreator",
                   "status": "idle",
                   "last_execution": "2026-03-26T10:00:00Z",
                   "success_rate": 0.95
               },
               # ...
           ]
       }

   @router.post("/agents/{agent_name}/trigger")
   async def trigger_agent(agent_name: str, input_data: dict):
       """手动触发单个 Agent"""
       # 触发 Agent 执行
       return {"task_id": "xxx", "status": "running"}
   ```

### 2.2 方案 B：引入 n8n 可视化编排

如果需要更灵活的工作流管理，可以引入 n8n。

#### 2.2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      n8n Workflows                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Content Pipeline Workflow                               ││
│  │  [Schedule] → [Researcher] → [Marketer] → [Copywriter]  ││
│  │       → [Designer] → [Moderator] → [Scheduler]          ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Analytics Workflow                                      ││
│  │  [Schedule 24h] → [Collector] → [Analyzer] → [Notify]   ││
│  └─────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP Webhooks
┌───────────────────────▼─────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  CrewAI Agent Endpoints                                  ││
│  │  POST /api/v1/agents/researcher                          ││
│  │  POST /api/v1/agents/copywriter                          ││
│  │  POST /api/v1/agents/moderator                           ││
│  │  ...                                                     ││
│  └─────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              PostgreSQL Database                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.2 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: crew_media_ops
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    ports:
      - "5432:5432"

  n8n:
    image: n8nio/n8n
    environment:
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin
      - N8N_ENCRYPTION_KEY=your-encryption-key
      - WEBHOOK_URL=http://localhost:5678/
    volumes:
      - n8n_data:/home/node/.n8n
      - ./n8n_workflows:/home/node/.n8n/workflows
    ports:
      - "5678:5678"
    depends_on:
      - postgres

  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/crew_media_ops
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres

volumes:
  postgres_data:
  n8n_data:
```

#### 2.2.3 n8n 工作流示例

```json
// n8n_workflows/content_pipeline.json
{
  "name": "Content Pipeline",
  "nodes": [
    {
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [250, 300],
      "parameters": {
        "rule": {
          "interval": [{"field": "hours", "hoursInterval": 4}]
        }
      }
    },
    {
      "name": "AI Researcher",
      "type": "n8n-nodes-base.httpRequest",
      "position": [450, 300],
      "parameters": {
        "url": "http://api:8000/api/v1/agents/researcher",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={ \"topic\": \"{{ $json.topic }}\" }"
      }
    },
    {
      "name": "AI Copywriter",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 300],
      "parameters": {
        "url": "http://api:8000/api/v1/agents/copywriter",
        "method": "POST"
      }
    },
    {
      "name": "AI Moderator",
      "type": "n8n-nodes-base.httpRequest",
      "position": [850, 300],
      "parameters": {
        "url": "http://api:8000/api/v1/agents/moderator",
        "method": "POST"
      }
    },
    {
      "name": "IF Approved",
      "type": "n8n-nodes-base.if",
      "position": [1050, 300],
      "parameters": {
        "conditions": {
          "boolean": [{"value1": "={{ $json.result }}", "value2": true}]
        }
      }
    },
    {
      "name": "AI Scheduler",
      "type": "n8n-nodes-base.httpRequest",
      "position": [1250, 200],
      "parameters": {
        "url": "http://api:8000/api/v1/agents/scheduler",
        "method": "POST"
      }
    }
  ]
}
```

### 2.3 方案 C：迁移到 LangGraph（可选）

如果需要更细粒度的状态管理，可以考虑迁移到 LangGraph。

**优点**：
- 更好的状态管理
- 支持循环和条件分支
- 更容易实现 A/B 测试

**缺点**：
- 需要重写现有代码
- 学习曲线较陡

---

## 3. 推荐实施路径

### Phase 1：基础改进（1-2 周）

1. **引入 PostgreSQL**
   - 创建数据库 schema
   - 添加 SQLAlchemy 模型
   - 实现 CRUD 操作

2. **增强 API 层**
   - 添加 Agent 状态端点
   - 添加 Webhook 支持
   - 添加 WebSocket 实时推送

3. **改进日志和监控**
   - 结构化日志
   - Agent 执行时间追踪
   - 错误告警

### Phase 2：Agent 职责优化（可选，1 周）

1. **拆分 ContentCreator**
   - 创建 Researcher Agent
   - 创建 Marketer Agent
   - 创建 Copywriter Agent
   - 创建 Designer Agent

2. **更新 ContentCrew**
   - 支持灵活的 Agent 组合
   - 支持条件分支

### Phase 3：可视化编排（可选，1-2 周）

1. **部署 n8n**
   - Docker Compose 配置
   - 导入工作流模板

2. **创建工作流**
   - 内容生产流程
   - 发布调度流程
   - 数据采集流程

---

## 4. 成本估算

### 方案 A（轻量级改进）

| 项目 | 月成本 |
|------|--------|
| Anthropic API | $50-150 |
| PostgreSQL (本地/云) | $0-25 |
| 服务器 | $10-50 |
| **总计** | **$60-225** |

### 方案 B（引入 n8n）

| 项目 | 月成本 |
|------|--------|
| Anthropic API | $50-150 |
| DALL-E (图片生成) | $20-100 |
| PostgreSQL | $0-25 |
| n8n (自托管) | $0 |
| 服务器 | $10-50 |
| **总计** | **$80-325** |

---

## 5. 结论

**推荐方案 A（轻量级改进）** 作为第一步：

1. **保持 CrewAI 框架** - 现有代码可复用
2. **引入 PostgreSQL** - 提升数据持久化能力
3. **增强 API 层** - 支持 Webhook 和实时状态
4. **改进监控** - 提升可观测性

**后续可按需引入 n8n**，如果需要：
- 可视化工作流编辑
- 非技术人员参与流程调整
- 更复杂的调度逻辑

---

## 6. 参考资源

- [multi-agent-social-media-automation](https://github.com/frankomondo/multi-agent-social-media-automation)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [n8n 文档](https://docs.n8n.io/)
- [CrewAI 文档](https://docs.crewai.com/)
