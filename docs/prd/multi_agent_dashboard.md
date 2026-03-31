# Multi-Agent Dashboard System PRD

> 版本: 1.0 | 日期: 2026-03-26 | 作者: Claude Code

---

## 1. 项目概述

### 1.1 背景

Crew Media Ops 是一个基于 CrewAI 的自媒体运营 Multi-Agent 系统。当前需要一套通用的前端监控面板，用于：

1. 实时监控每个 Agent 的工作状态
2. 可视化 Agent 的输入/输出数据
3. 追踪任务执行流程
4. 提供系统级别的数据分析

### 1.2 目标

- **通用性**: 适用于任何 CrewAI-based Multi-Agent 系统
- **可扩展**: 支持动态添加新的 Agent 类型
- **实时性**: 实时展示 Agent 执行状态
- **易用性**: 直观的数据可视化

### 1.3 技术选型

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | React | 19.x |
| 样式框架 | Tailwind CSS | v4.x |
| UI 模板 | TailAdmin | 最新版 |
| 图表库 | ApexCharts | 4.x |
| 状态管理 | Zustand | 5.x |
| 后端框架 | FastAPI | 0.115+ |
| 实时通信 | WebSocket | - |
| 数据验证 | Pydantic | v2 |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + TailAdmin)             │
├─────────────────────────────────────────────────────────────┤
│  Dashboard Layout  │  Agent Panels  │  Analytics Charts     │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebSocket + REST API
┌───────────────────────┴─────────────────────────────────────┐
│                     Backend (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│  API Routes  │  WebSocket Hub  │  Event Stream Handler      │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────┴─────────────────────────────────────┐
│                     Agent Runtime Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Agent Registry  │  Task Queue  │  Event Emitter            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 当前系统 Agent 定义

Crew Media Ops 包含 **5 个核心 Agent**，组成完整的内容生产流水线：

| Agent | 角色 | 职责 | 输入 | 输出 |
|-------|------|------|------|------|
| **ContentCreator** | 内容研究创作者 | 追踪热点、研究爆款、学习风格、创作内容 | topic, platform, style | ContentDraft |
| **ContentReviewer** | 内容审核员 | 审核内容质量、把关品牌调性、提出修改建议 | ContentDraft | ReviewResult |
| **PlatformAdapter** | 平台适配师 | 根据平台特性调整内容格式、生成配图 | ContentDraft, Platform | AdaptedContent |
| **PlatformPublisher** | 平台发布员 | 执行发布操作、处理发布结果 | AdaptedContent | PublishResult |
| **DataAnalyst** | 数据分析师 | 采集平台数据、生成分析报告 | PublishResult, time_range | AnalyticsReport |

#### 2.2.1 Agent 详细定义

```python
# ContentCreator - 内容研究创作者
{
    "name": "ContentCreator",
    "role": "内容研究创作者",
    "goal": "追踪热点、研究爆款、学习风格、创作内容",
    "backstory": """
    你是一位全能型内容创作者，擅长追踪热点、研究爆款、学习风格并创作高质量内容。
    你能根据不同平台的调性调整写作风格，同时保证内容的原创性和吸引力。
    """,
    "tools": ["hot_search", "trend_analysis", "style_reference"],
    "input_schema": {
        "topic": "str - 内容主题",
        "platform": "str - 目标平台 (xiaohongshu/weibo/zhihu/wechat/douyin/bilibili)",
        "style": "str - 写作风格 (professional/casual/storytelling)",
        "reference_urls": "list[str] - 参考链接（可选）"
    },
    "output_schema": {
        "title": "str - 标题",
        "content": "str - 正文内容",
        "hashtags": "list[str] - 话题标签",
        "images_prompt": "list[str] - 配图提示词"
    }
}

# ContentReviewer - 内容审核员
{
    "name": "ContentReviewer",
    "role": "内容审核员",
    "goal": "审核内容质量、把关品牌调性、提出修改建议",
    "backstory": """
    你是一位资深内容审核专家，对内容质量、品牌调性、平台规范有敏锐的判断力。
    你能快速识别内容中的问题并提出具体的改进建议。
    """,
    "tools": ["content_checker", "sensitivity_filter"],
    "input_schema": {
        "draft": "ContentDraft - 待审核内容",
        "brand_guidelines": "str - 品牌调性要求",
        "platform_rules": "str - 平台规范"
    },
    "output_schema": {
        "approved": "bool - 是否通过",
        "score": "int - 质量评分 (0-100)",
        "issues": "list[str] - 问题列表",
        "suggestions": "list[str] - 修改建议",
        "revised_draft": "ContentDraft - 修改后的内容（可选）"
    }
}

# PlatformAdapter - 平台适配师
{
    "name": "PlatformAdapter",
    "role": "平台适配师",
    "goal": "根据平台特性调整内容格式、生成配图",
    "backstory": """
    你是一位平台运营专家，深谙各平台的内容规范和最佳实践。
    你能将通用内容适配到不同平台，并生成符合平台调性的配图。
    """,
    "tools": ["image_generator", "format_adapter"],
    "input_schema": {
        "draft": "ContentDraft - 已审核内容",
        "platform": "str - 目标平台",
        "image_style": "str - 配图风格"
    },
    "output_schema": {
        "title": "str - 适配后的标题",
        "content": "str - 适配后的正文",
        "images": "list[str] - 生成的图片路径",
        "metadata": "dict - 平台特定元数据"
    }
}

# PlatformPublisher - 平台发布员
{
    "name": "PlatformPublisher",
    "role": "平台发布员",
    "goal": "执行发布操作、处理发布结果",
    "backstory": """
    你是一位平台发布专家，熟悉各平台的发布流程和规范。
    你能安全、高效地完成内容发布，并妥善处理发布过程中的各种情况。
    """,
    "tools": ["platform_publisher", "status_checker"],
    "input_schema": {
        "adapted_content": "AdaptedContent - 已适配内容",
        "platform": "str - 目标平台",
        "scheduled_at": "datetime - 定时发布时间（可选）"
    },
    "output_schema": {
        "success": "bool - 是否成功",
        "url": "str - 发布后的内容链接",
        "content_id": "str - 平台内容ID",
        "published_at": "datetime - 发布时间",
        "error": "str - 错误信息（失败时）"
    }
}

# DataAnalyst - 数据分析师
{
    "name": "DataAnalyst",
    "role": "数据分析师",
    "goal": "采集平台数据、生成分析报告",
    "backstory": """
    你是一位数据分析专家，擅长从平台数据中提取有价值的洞察。
    你能生成清晰、 actionable 的分析报告，指导后续内容优化。
    """,
    "tools": ["metrics_collector", "report_generator"],
    "input_schema": {
        "content_ids": "list[str] - 待分析的内容ID列表",
        "time_range": "dict - 时间范围 (start, end)",
        "metrics": "list[str] - 需要采集的指标"
    },
    "output_schema": {
        "summary": "dict - 数据摘要",
        "metrics": "dict - 详细指标数据",
        "trends": "dict - 趋势分析",
        "insights": "list[str] - 洞察建议",
        "recommendations": "list[str] - 优化建议"
    }
}
```

#### 2.2.2 Crew 编排流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ContentCrew (内容生产线)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐               │
│  │ ContentCreator │ ─> │ ContentReviewer │ ─> │ PlatformAdapter │         │
│  │   研究创作      │     │    审核把关      │     │    平台适配      │         │
│  └─────────────┘     └─────────────┘     └─────────────┘               │
│         │                   │                   │                        │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ContentDraft         ReviewResult        AdaptedContent                │
│                                                  │                        │
│                                                  ▼                        │
│                                          ┌─────────────┐               │
│                                          │ PlatformPublisher │         │
│                                          │    平台发布        │          │
│                                          └─────────────┘               │
│                                                  │                        │
│                                                  ▼                        │
│                                          PublishResult                  │
│                                                  │                        │
│                                                  ▼                        │
│                                          ┌─────────────┐               │
│                                          │ DataAnalyst  │               │
│                                          │   数据分析    │               │
│                                          └─────────────┘               │
│                                                  │                        │
│                                                  ▼                        │
│                                          AnalyticsReport               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 2.2.3 平台支持矩阵

| 平台 | 内容类型 | ContentCreator | PlatformAdapter | PlatformPublisher | DataAnalyst |
|------|----------|:-------------:|:---------------:|:-----------------:|:-----------:|
| 小红书 | 图文/视频 | ✅ | ✅ | ✅ | ✅ |
| 微信公众号 | 图文 | ✅ | ✅ | ✅ | ✅ |
| 微博 | 图文/头条文章 | ✅ | ✅ | ✅ | ✅ |
| 知乎 | 文章/回答/想法 | ✅ | ✅ | ✅ | ✅ |
| 抖音 | 视频 | ✅ | ✅ | ✅ | ✅ |
| B站 | 视频/专栏 | ✅ | ✅ | ✅ | ✅ |

### 2.3 通用性设计

核心抽象：
- **AgentRegistry**: 动态注册 Agent 类型
- **EventSchema**: 标准化事件格式
- **DataAdapter**: 适配不同 Agent 的数据结构

---

## 3. 功能需求

### 3.1 全局概览 (Overview Dashboard)

#### 3.1.1 系统状态卡片
- 运行中的 Crew 数量
- 活跃 Agent 数量
- 待处理任务数
- 今日完成数

#### 3.1.2 实时活动流
- Agent 执行日志滚动展示
- 任务状态变更通知
- 错误告警高亮

#### 3.1.3 系统资源监控
- LLM API 调用统计
- Token 消耗趋势
- 响应时间分布

### 3.2 Agent 专属面板

每个 Agent 拥有独立的监控面板，包含：

#### 3.2.1 基本信息
- Agent 名称、角色、目标
- 当前状态 (idle/running/waiting/error)
- 最后活动时间
- 累计执行次数

#### 3.2.2 工作过程可视化
```
┌─────────────────────────────────────────────────────────────┐
│  Agent: ContentCreator                                       │
│  Status: Running ████████░░ 80%                              │
├─────────────────────────────────────────────────────────────┤
│  Current Task: 生成小红书爆款内容                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│  │ Research │ -> │ Write   │ -> │ Review  │                 │
│  │   ✓      │    │  ⏳     │    │         │                 │
│  └─────────┘    └─────────┘    └─────────┘                 │
├─────────────────────────────────────────────────────────────┤
│  Input:                                                      │
│  {                                                           │
│    "topic": "AI产品经理认知",                                 │
│    "platform": "xiaohongshu",                                │
│    "style": "professional"                                   │
│  }                                                           │
├─────────────────────────────────────────────────────────────┤
│  Output: (实时流式显示)                                       │
│  标题: 入局 AI 产品经理一年...                                │
│  正文: 在这个 AI 井喷的时代...                                │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.3 输入数据展示
- 结构化参数 (JSON Viewer)
- 原始输入文本
- 上下文数据

#### 3.2.4 输出数据展示
- 流式输出 (实时更新)
- 结构化结果
- 历史输出记录

#### 3.2.5 执行历史
- 时间线视图
- 成功/失败统计
- 平均执行时长

### 3.3 Crew 编排视图

#### 3.3.1 Crew 结构图
- Agent 关系图 (DAG)
- 任务依赖关系
- 数据流向

#### 3.3.2 执行流程追踪
```
Crew: ContentCrew (ID: crew_001)

┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ContentCreator│ ───> │ContentReviewer│ ───> │PlatformAdapter│ ───> │PlatformPublisher│ ───> │ DataAnalyst  │
│   ⏳ 45s     │      │   ✓ 12s      │      │   ⏳ 25s      │      │   Pending    │      │   Pending    │
│             │      │              │      │              │      │              │      │              │
│ Input:      │      │ Input:       │      │ Input:       │      │              │      │              │
│ topic, style│      │ draft.json   │      │ reviewed.json│      │              │      │              │
│             │      │              │      │              │      │              │      │              │
│ Output:     │      │ Output:      │      │ Output:      │      │              │      │              │
│ draft.json  │      │ reviewed.json│      │ adapted.json │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
```

### 3.4 任务队列管理

#### 3.4.1 任务列表
- 优先级排序
- 状态筛选 (pending/running/completed/failed)
- 批量操作

#### 3.4.2 任务详情
- 输入参数
- 执行日志
- 重试机制

### 3.5 数据分析

#### 3.5.1 Agent 性能分析
- 执行成功率
- 平均响应时间
- Token 消耗分布

#### 3.5.2 任务趋势
- 每日任务量
- 完成率趋势
- 错误类型分布

---

## 4. 后端 API 设计

### 4.1 RESTful API

#### 4.1.1 Agent 相关

```yaml
# 获取所有 Agent 列表
GET /api/v1/agents
Response:
  {
    "agents": [
      {
        "id": "agent_001",
        "name": "ContentCreator",
        "role": "内容研究创作者",
        "status": "idle",
        "last_activity": "2026-03-26T10:30:00Z",
        "metrics": {
          "total_executions": 156,
          "success_rate": 0.95,
          "avg_duration_ms": 45000
        }
      },
      {
        "id": "agent_002",
        "name": "ContentReviewer",
        "role": "内容审核员",
        "status": "idle",
        "last_activity": "2026-03-26T10:35:00Z",
        "metrics": {
          "total_executions": 156,
          "success_rate": 0.98,
          "avg_duration_ms": 12000
        }
      },
      {
        "id": "agent_003",
        "name": "PlatformAdapter",
        "role": "平台适配师",
        "status": "running",
        "last_activity": "2026-03-26T11:00:00Z",
        "metrics": {
          "total_executions": 89,
          "success_rate": 0.97,
          "avg_duration_ms": 25000
        }
      },
      {
        "id": "agent_004",
        "name": "PlatformPublisher",
        "role": "平台发布员",
        "status": "idle",
        "last_activity": "2026-03-26T09:45:00Z",
        "metrics": {
          "total_executions": 78,
          "success_rate": 0.92,
          "avg_duration_ms": 18000
        }
      },
      {
        "id": "agent_005",
        "name": "DataAnalyst",
        "role": "数据分析师",
        "status": "idle",
        "last_activity": "2026-03-25T18:00:00Z",
        "metrics": {
          "total_executions": 23,
          "success_rate": 1.0,
          "avg_duration_ms": 35000
        }
      }
    ]
  }

# 获取单个 Agent 详情
GET /api/v1/agents/{agent_id}
Response:
  {
    "id": "agent_001",
    "name": "ContentCreator",
    "role": "内容研究创作者",
    "goal": "追踪热点、研究爆款、学习风格、创作内容",
    "backstory": "...",
    "status": "running",
    "current_task": {
      "id": "task_001",
      "name": "生成小红书爆款内容",
      "progress": 0.8,
      "started_at": "2026-03-26T10:30:00Z"
    },
    "metrics": {...}
  }

# 获取 Agent 执行历史
GET /api/v1/agents/{agent_id}/executions
Query: limit, offset, status
Response:
  {
    "executions": [
      {
        "id": "exec_001",
        "task_id": "task_001",
        "status": "completed",
        "started_at": "2026-03-26T10:00:00Z",
        "completed_at": "2026-03-26T10:01:30Z",
        "duration_ms": 90000,
        "input": {...},
        "output": {...}
      }
    ],
    "total": 156
  }

# 获取 Agent 当前输入
GET /api/v1/agents/{agent_id}/input
Response:
  {
    "task_id": "task_001",
    "input": {
      "topic": "AI产品经理认知",
      "platform": "xiaohongshu"
    },
    "received_at": "2026-03-26T10:30:00Z"
  }

# 获取 Agent 当前输出
GET /api/v1/agents/{agent_id}/output
Response:
  {
    "task_id": "task_001",
    "output": {
      "title": "...",
      "content": "...",
      "status": "streaming"
    },
    "updated_at": "2026-03-26T10:30:45Z"
  }
```

#### 4.1.2 Crew 相关

```yaml
# 获取所有 Crew 列表
GET /api/v1/crews
Response:
  {
    "crews": [
      {
        "id": "crew_001",
        "name": "ContentCrew",
        "status": "running",
        "agents": ["agent_001", "agent_002"],
        "process": "sequential",
        "created_at": "2026-03-26T10:00:00Z"
      }
    ]
  }

# 获取 Crew 详情
GET /api/v1/crews/{crew_id}
Response:
  {
    "id": "crew_001",
    "name": "ContentCrew",
    "description": "内容生产线 Crew",
    "status": "running",
    "process": "sequential",
    "agents": [
      {"id": "agent_001", "name": "ContentCreator", "role": "内容研究创作者", "order": 1},
      {"id": "agent_002", "name": "ContentReviewer", "role": "内容审核员", "order": 2},
      {"id": "agent_003", "name": "PlatformAdapter", "role": "平台适配师", "order": 3},
      {"id": "agent_004", "name": "PlatformPublisher", "role": "平台发布员", "order": 4},
      {"id": "agent_005", "name": "DataAnalyst", "role": "数据分析师", "order": 5}
    ],
    "tasks": [...],
    "current_task_index": 1,
    "progress": 0.6
  }

# 获取 Crew 执行流程
GET /api/v1/crews/{crew_id}/flow
Response:
  {
    "nodes": [
      {"id": "agent_001", "name": "ContentCreator", "type": "agent", "position": {"x": 0, "y": 0}},
      {"id": "agent_002", "name": "ContentReviewer", "type": "agent", "position": {"x": 200, "y": 0}},
      {"id": "agent_003", "name": "PlatformAdapter", "type": "agent", "position": {"x": 400, "y": 0}},
      {"id": "agent_004", "name": "PlatformPublisher", "type": "agent", "position": {"x": 600, "y": 0}},
      {"id": "agent_005", "name": "DataAnalyst", "type": "agent", "position": {"x": 800, "y": 0}}
    ],
    "edges": [
      {"from": "agent_001", "to": "agent_002", "label": "draft"},
      {"from": "agent_002", "to": "agent_003", "label": "reviewed"},
      {"from": "agent_003", "to": "agent_004", "label": "adapted"},
      {"from": "agent_004", "to": "agent_005", "label": "published"}
    ]
  }
```

#### 4.1.3 Task 相关

```yaml
# 获取任务列表
GET /api/v1/tasks
Query: status, crew_id, agent_id, limit, offset
Response:
  {
    "tasks": [
      {
        "id": "task_001",
        "crew_id": "crew_001",
        "agent_id": "agent_001",
        "name": "生成小红书爆款内容",
        "status": "running",
        "priority": 1,
        "created_at": "2026-03-26T10:00:00Z",
        "started_at": "2026-03-26T10:30:00Z"
      }
    ],
    "total": 50
  }

# 创建任务
POST /api/v1/tasks
Body:
  {
    "crew_type": "ContentCrew",
    "inputs": {
      "topic": "AI产品经理认知",
      "platform": "xiaohongshu"
    },
    "priority": 1,
    "scheduled_at": null
  }
Response:
  {
    "task_id": "task_002",
    "status": "pending",
    "created_at": "2026-03-26T11:00:00Z"
  }

# 获取任务详情
GET /api/v1/tasks/{task_id}
Response:
  {
    "id": "task_001",
    "crew_id": "crew_001",
    "agent_id": "agent_001",
    "name": "生成小红书爆款内容",
    "description": "...",
    "status": "completed",
    "priority": 1,
    "input": {...},
    "output": {...},
    "logs": [...],
    "created_at": "2026-03-26T10:00:00Z",
    "started_at": "2026-03-26T10:30:00Z",
    "completed_at": "2026-03-26T10:31:30Z",
    "duration_ms": 90000
  }

# 取消任务
DELETE /api/v1/tasks/{task_id}
Response:
  {
    "task_id": "task_001",
    "status": "cancelled"
  }

# 重试任务
POST /api/v1/tasks/{task_id}/retry
Response:
  {
    "task_id": "task_001",
    "new_task_id": "task_003",
    "status": "pending"
  }
```

#### 4.1.4 Analytics 相关

```yaml
# 获取系统概览统计
GET /api/v1/analytics/overview
Query: period (day/week/month)
Response:
  {
    "period": "day",
    "crews": {
      "total": 15,
      "running": 2,
      "completed": 12,
      "failed": 1
    },
    "agents": {
      "total": 6,
      "active": 4
    },
    "tasks": {
      "total": 150,
      "completed": 142,
      "failed": 3,
      "pending": 5
    },
    "llm": {
      "total_calls": 450,
      "total_tokens": 1250000,
      "avg_latency_ms": 2500
    }
  }

# 获取 Agent 性能指标
GET /api/v1/analytics/agents/{agent_id}/performance
Query: period
Response:
  {
    "agent_id": "agent_001",
    "period": "week",
    "metrics": {
      "executions": 45,
      "success_rate": 0.95,
      "avg_duration_ms": 42000,
      "min_duration_ms": 15000,
      "max_duration_ms": 120000,
      "total_tokens": 350000,
      "error_types": {
        "timeout": 2,
        "rate_limit": 1
      }
    },
    "trend": [
      {"date": "2026-03-20", "executions": 8, "success_rate": 0.88},
      {"date": "2026-03-21", "executions": 7, "success_rate": 1.0}
    ]
  }

# 获取趋势数据
GET /api/v1/analytics/trends
Query: metric, period, granularity
Response:
  {
    "metric": "task_completions",
    "period": "week",
    "granularity": "day",
    "data": [
      {"timestamp": "2026-03-20", "value": 25},
      {"timestamp": "2026-03-21", "value": 30}
    ]
  }
```

### 4.2 WebSocket API

#### 4.2.1 连接

```javascript
// 前端连接
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');

// 订阅频道
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['agent:agent_001', 'crew:crew_001', 'system']
}));
```

#### 4.2.2 事件类型

```typescript
// Agent 状态变更
interface AgentStatusEvent {
  type: 'agent:status';
  agent_id: string;
  status: 'idle' | 'running' | 'waiting' | 'error';
  timestamp: string;
}

// Agent 输出流
interface AgentOutputStreamEvent {
  type: 'agent:output_stream';
  agent_id: string;
  task_id: string;
  chunk: string;
  timestamp: string;
}

// Agent 执行完成
interface AgentExecutionCompleteEvent {
  type: 'agent:complete';
  agent_id: string;
  task_id: string;
  output: object;
  duration_ms: number;
  timestamp: string;
}

// Crew 状态变更
interface CrewStatusEvent {
  type: 'crew:status';
  crew_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  current_agent: string;
  timestamp: string;
}

// 任务状态变更
interface TaskStatusEvent {
  type: 'task:status';
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  error?: string;
  timestamp: string;
}

// 系统告警
interface SystemAlertEvent {
  type: 'system:alert';
  level: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  source: string;
  timestamp: string;
}
```

---

## 5. 数据模型

### 5.1 Agent 模型

```python
# src/models/agent.py
from enum import Enum
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"

class AgentMetrics(BaseModel):
    total_executions: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration_ms: int = 0
    avg_duration_ms: float = 0.0
    total_tokens: int = 0

class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    goal: str
    backstory: str
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: str | None = None
    last_activity: datetime | None = None
    created_at: datetime
    metrics: AgentMetrics = AgentMetrics()

class AgentExecution(BaseModel):
    id: str
    agent_id: str
    task_id: str
    crew_id: str | None = None
    status: AgentStatus
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    tokens_used: int = 0
```

### 5.2 Crew 模型

```python
# src/models/crew.py
from enum import Enum
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class CrewStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CrewAgentRef(BaseModel):
    id: str
    name: str
    role: str
    order: int

class CrewTaskRef(BaseModel):
    id: str
    name: str
    agent_id: str
    status: str
    order: int

class CrewInfo(BaseModel):
    id: str
    name: str
    description: str
    status: CrewStatus = CrewStatus.PENDING
    process: str = "sequential"
    agents: list[CrewAgentRef] = []
    tasks: list[CrewTaskRef] = []
    current_task_index: int = 0
    progress: float = 0.0
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

### 5.3 Task 模型

```python
# src/models/task.py
from enum import Enum
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(int, Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0

class TaskLog(BaseModel):
    timestamp: datetime
    level: str
    message: str

class TaskInfo(BaseModel):
    id: str
    crew_id: str | None = None
    crew_type: str
    agent_id: str | None = None
    name: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    input: dict[str, Any] = {}
    output: dict[str, Any] | None = None
    error: str | None = None
    logs: list[TaskLog] = []
    created_at: datetime
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
```

### 5.4 事件模型

```python
# src/models/events.py
from enum import Enum
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class EventType(str, Enum):
    AGENT_STATUS = "agent:status"
    AGENT_OUTPUT_STREAM = "agent:output_stream"
    AGENT_COMPLETE = "agent:complete"
    CREW_STATUS = "crew:status"
    TASK_STATUS = "task:status"
    SYSTEM_ALERT = "system:alert"

class BaseEvent(BaseModel):
    type: EventType
    timestamp: datetime

class AgentStatusEvent(BaseEvent):
    type: EventType = EventType.AGENT_STATUS
    agent_id: str
    status: str
    task_id: str | None = None

class AgentOutputStreamEvent(BaseEvent):
    type: EventType = EventType.AGENT_OUTPUT_STREAM
    agent_id: str
    task_id: str
    chunk: str

class SystemAlertEvent(BaseEvent):
    type: EventType = EventType.SYSTEM_ALERT
    level: str  # info, warning, error, critical
    message: str
    source: str
```

---

## 6. 前端设计

### 6.1 页面结构

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar  │                    Main Content                  │
│           │                                                   │
│  ┌─────┐  │  ┌─────────────────────────────────────────────┐│
│  │Logo │  │  │                 Header                       ││
│  └─────┘  │  ├─────────────────────────────────────────────┤│
│           │  │                                             ││
│  Overview │  │                                             ││
│  Agents   │  │              Page Content                    ││
│  Crews    │  │                                             ││
│  Tasks    │  │                                             ││
│  Analytics│  │                                             ││
│  Settings │  │                                             ││
│           │  └─────────────────────────────────────────────┘│
│  ─────────│                                                   │
│  Mode: 🌙│                                                   │
└───────────┴───────────────────────────────────────────────────┘
```

### 6.2 路由设计

```typescript
// src/routes/index.tsx
const routes = [
  { path: '/', element: <Overview /> },
  { path: '/agents', element: <AgentList /> },
  { path: '/agents/:id', element: <AgentDetail /> },
  { path: '/crews', element: <CrewList /> },
  { path: '/crews/:id', element: <CrewDetail /> },
  { path: '/tasks', element: <TaskList /> },
  { path: '/tasks/:id', element: <TaskDetail /> },
  { path: '/analytics', element: <Analytics /> },
  { path: '/settings', element: <Settings /> },
];
```

### 6.3 组件设计

#### 6.3.1 核心组件

```typescript
// Agent 监控卡片
interface AgentCardProps {
  agent: AgentInfo;
  onClick: (id: string) => void;
}

// Agent 详情面板
interface AgentPanelProps {
  agentId: string;
  showInput: boolean;
  showOutput: boolean;
  showHistory: boolean;
}

// 实时输出流组件
interface OutputStreamProps {
  agentId: string;
  maxHeight?: number;
}

// Crew 流程图组件
interface CrewFlowChartProps {
  crewId: string;
  orientation: 'horizontal' | 'vertical';
}

// 任务时间线组件
interface TaskTimelineProps {
  crewId: string;
  showDetails: boolean;
}

// 统计卡片组件
interface StatCardProps {
  title: string;
  value: number | string;
  trend?: number;
  icon: React.ReactNode;
  color: string;
}
```

#### 6.3.2 布局组件

```typescript
// 基于 TailAdmin 的布局
import { Sidebar, Header } from '@tailadmin';

<DefaultLayout>
  <Sidebar menuItems={menuItems} />
  <div className="flex-1">
    <Header title={pageTitle} />
    <main className="p-4">
      {children}
    </main>
  </div>
</DefaultLayout>
```

### 6.4 主题配置

```typescript
// src/styles/theme.ts
const theme = {
  dark: {
    background: '#0f172a',      // slate-900
    card: '#1e293b',           // slate-800
    border: '#334155',         // slate-700
    text: {
      primary: '#f1f5f9',      // slate-100
      secondary: '#94a3b8',    // slate-400
    },
    accent: {
      primary: '#6366f1',      // indigo-500
      success: '#22c55e',      // green-500
      warning: '#f59e0b',      // amber-500
      error: '#ef4444',        // red-500
    }
  },
  light: {
    background: '#f8fafc',     // slate-50
    card: '#ffffff',
    border: '#e2e8f0',         // slate-200
    text: {
      primary: '#0f172a',      // slate-900
      secondary: '#64748b',    // slate-500
    },
    accent: { /* 同 dark */ }
  }
};
```

### 6.5 状态管理

```typescript
// src/store/agentStore.ts
import { create } from 'zustand';

interface AgentStore {
  agents: AgentInfo[];
  selectedAgent: string | null;
  eventStream: Event[];

  fetchAgents: () => Promise<void>;
  selectAgent: (id: string) => void;
  subscribeToEvents: (agentId: string) => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  selectedAgent: null,
  eventStream: [],

  fetchAgents: async () => {
    const res = await fetch('/api/v1/agents');
    const data = await res.json();
    set({ agents: data.agents });
  },

  selectAgent: (id) => set({ selectedAgent: id }),

  subscribeToEvents: (agentId) => {
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.agent_id === agentId) {
        set((state) => ({
          eventStream: [...state.eventStream, data]
        }));
      }
    };
  }
}));
```

---

## 7. 后端实现

### 7.1 目录结构

```
src/api/
├── main.py                    # FastAPI 入口
├── routes/
│   ├── __init__.py
│   ├── agents.py              # Agent API
│   ├── crews.py               # Crew API
│   ├── tasks.py               # Task API
│   ├── analytics.py           # Analytics API
│   └── websocket.py           # WebSocket 处理
├── services/
│   ├── __init__.py
│   ├── agent_service.py       # Agent 业务逻辑
│   ├── crew_service.py        # Crew 业务逻辑
│   ├── task_service.py        # Task 业务逻辑
│   ├── event_emitter.py       # 事件发射器
│   └── analytics_service.py   # 统计分析逻辑
├── models/
│   ├── __init__.py
│   ├── agent.py
│   ├── crew.py
│   ├── task.py
│   └── events.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── database.py
└── static/                    # 前端静态文件
    ├── index.html
    ├── assets/
    └── ...
```

### 7.2 API 路由示例

```python
# src/api/routes/agents.py
from fastapi import APIRouter, HTTPException
from src.api.services.agent_service import AgentService
from src.api.models.agent import AgentInfo, AgentExecution

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])
service = AgentService()

@router.get("", response_model=dict)
async def list_agents():
    """获取所有 Agent 列表"""
    agents = await service.get_all_agents()
    return {"agents": agents}

@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """获取 Agent 详情"""
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.get("/{agent_id}/executions")
async def get_executions(
    agent_id: str,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None
):
    """获取 Agent 执行历史"""
    executions = await service.get_executions(
        agent_id, limit, offset, status
    )
    return {"executions": executions, "total": len(executions)}

@router.get("/{agent_id}/input")
async def get_current_input(agent_id: str):
    """获取 Agent 当前输入"""
    input_data = await service.get_current_input(agent_id)
    return input_data

@router.get("/{agent_id}/output")
async def get_current_output(agent_id: str):
    """获取 Agent 当前输出"""
    output_data = await service.get_current_output(agent_id)
    return output_data
```

### 7.3 WebSocket 实现

```python
# src/api/routes/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from src.api.services.event_emitter import EventEmitter
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # 清理订阅
        for channel in self.subscriptions:
            if websocket in self.subscriptions[channel]:
                self.subscriptions[channel].remove(websocket)

    async def subscribe(self, websocket: WebSocket, channels: list[str]):
        for channel in channels:
            if channel not in self.subscriptions:
                self.subscriptions[channel] = []
            self.subscriptions[channel].append(websocket)

    async def broadcast(self, channel: str, message: dict):
        if channel in self.subscriptions:
            for connection in self.subscriptions[channel]:
                await connection.send_json(message)

manager = ConnectionManager()
emitter = EventEmitter(manager)

@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "subscribe":
                await manager.subscribe(websocket, message["channels"])

    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### 7.4 事件发射器集成

```python
# src/api/services/event_emitter.py
from src.api.routes.websocket import manager
from src.api.models.events import BaseEvent
import json

class EventEmitter:
    """事件发射器，集成到 Crew 执行流程中"""

    def __init__(self, ws_manager):
        self.manager = ws_manager

    async def emit(self, event: BaseEvent):
        """发射事件到 WebSocket"""
        channel = self._get_channel(event)
        await self.manager.broadcast(channel, event.model_dump())

    def _get_channel(self, event: BaseEvent) -> str:
        """根据事件类型确定频道"""
        if event.type.startswith("agent:"):
            return f"agent:{event.agent_id}"
        elif event.type.startswith("crew:"):
            return f"crew:{event.crew_id}"
        else:
            return "system"

# 在 BaseCrew 中集成
class BaseCrew:
    def __init__(self, ..., event_emitter: EventEmitter = None):
        self.event_emitter = event_emitter

    async def _emit_event(self, event: BaseEvent):
        if self.event_emitter:
            await self.event_emitter.emit(event)
```

---

## 8. 通用性设计

### 8.1 Agent 注册机制

```python
# src/core/agent_registry.py
from typing import Type, Callable
from dataclasses import dataclass

@dataclass
class AgentDescriptor:
    """Agent 描述符"""
    name: str
    role: str
    goal: str
    backstory: str
    agent_class: Type
    tools: list

class AgentRegistry:
    """Agent 注册表"""

    _instance = None
    _agents: dict[str, AgentDescriptor] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, descriptor: AgentDescriptor):
        """注册 Agent"""
        cls._agents[descriptor.name] = descriptor

    @classmethod
    def get(cls, name: str) -> AgentDescriptor | None:
        """获取 Agent 描述符"""
        return cls._agents.get(name)

    @classmethod
    def list_all(cls) -> list[AgentDescriptor]:
        """列出所有已注册 Agent"""
        return list(cls._agents.values())

    @classmethod
    def create_agent(cls, name: str, **kwargs):
        """创建 Agent 实例"""
        descriptor = cls.get(name)
        if not descriptor:
            raise ValueError(f"Agent '{name}' not registered")
        return descriptor.agent_class(**kwargs)

# 使用装饰器注册
def register_agent(name: str, role: str, goal: str, backstory: str):
    def decorator(cls):
        AgentRegistry.register(AgentDescriptor(
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            agent_class=cls,
            tools=[]
        ))
        return cls
    return decorator

# 使用示例
@register_agent(
    name="ContentCreator",
    role="内容研究创作者",
    goal="追踪热点、研究爆款、创作内容",
    backstory="..."
)
class ContentCreatorAgent(BaseAgent):
    pass
```

### 8.2 数据适配器

```python
# src/core/data_adapter.py
from abc import ABC, abstractmethod
from typing import Any

class DataAdapter(ABC):
    """数据适配器基类"""

    @abstractmethod
    def adapt_input(self, raw_input: Any) -> dict:
        """将原始输入适配为标准格式"""
        pass

    @abstractmethod
    def adapt_output(self, raw_output: Any) -> dict:
        """将原始输出适配为标准格式"""
        pass

class CrewAIAdapter(DataAdapter):
    """CrewAI 数据适配器"""

    def adapt_input(self, raw_input: Any) -> dict:
        if isinstance(raw_input, dict):
            return raw_input
        return {"raw": str(raw_input)}

    def adapt_output(self, raw_output: Any) -> dict:
        if hasattr(raw_output, 'to_dict'):
            return raw_output.to_dict()
        elif isinstance(raw_output, dict):
            return raw_output
        return {"output": str(raw_output)}

# 适配器工厂
class AdapterFactory:
    _adapters: dict[str, DataAdapter] = {
        "crewai": CrewAIAdapter(),
    }

    @classmethod
    def get(cls, framework: str) -> DataAdapter:
        return cls._adapters.get(framework, cls._adapters["crewai"])

    @classmethod
    def register(cls, name: str, adapter: DataAdapter):
        cls._adapters[name] = adapter
```

### 8.3 插件化配置

```python
# src/core/plugin_config.py
from pydantic import BaseModel
from typing import Any

class AgentPanelConfig(BaseModel):
    """Agent 面板配置"""
    show_input: bool = True
    show_output: bool = True
    show_history: bool = True
    show_metrics: bool = True
    custom_components: list[str] = []

class DashboardConfig(BaseModel):
    """Dashboard 配置"""
    title: str = "Multi-Agent Dashboard"
    logo: str = "/static/logo.svg"
    sidebar_items: list[str] = ["overview", "agents", "crews", "tasks", "analytics"]
    agent_panels: dict[str, AgentPanelConfig] = {}
    theme: str = "dark"
    custom_css: str | None = None

# 配置加载
def load_config(config_path: str) -> DashboardConfig:
    import yaml
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return DashboardConfig(**data)
```

---

## 9. 部署方案

### 9.1 开发环境

```bash
# 后端
uvicorn src.api.main:app --reload --port 8000

# 前端
cd frontend
pnpm dev
```

### 9.2 生产环境

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 10. 开发计划

### Phase 1: 基础框架 (1周)
- [ ] 初始化 React + TailAdmin 项目
- [ ] 实现基础布局和路由
- [ ] 搭建 FastAPI 后端骨架
- [ ] 实现 Agent 注册机制

### Phase 2: 核心功能 (2周)
- [ ] Agent 列表和详情页
- [ ] Crew 编排视图
- [ ] Task 管理功能
- [ ] WebSocket 实时通信

### Phase 3: 数据分析 (1周)
- [ ] 统计卡片组件
- [ ] 图表集成 (ApexCharts)
- [ ] Analytics 页面

### Phase 4: 通用化 (1周)
- [ ] 插件化配置系统
- [ ] 数据适配器
- [ ] 主题切换
- [ ] 文档编写

---

## 11. 附录

### 11.1 API 响应格式标准

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

错误响应：
```json
{
  "success": false,
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent with ID 'xxx' not found"
  }
}
```

### 11.2 TailAdmin 组件映射

| 功能 | TailAdmin 组件 |
|------|---------------|
| 侧边栏 | Sidebar |
| 顶栏 | Header |
| 统计卡片 | Card, EcommerceCard |
| 表格 | Table |
| 图表 | Chart (ApexCharts) |
| 表单 | Form, Input, Select |
| 模态框 | Modal |
| 通知 | Alert |

### 11.3 参考资料

- [TailAdmin 文档](https://tailadmin.com/docs)
- [CrewAI 文档](https://docs.crewai.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Zustand 文档](https://docs.pmnd.rs/zustand/getting-started/introduction)
