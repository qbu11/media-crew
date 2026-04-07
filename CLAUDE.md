# CLAUDE.md — Crew Media Ops 开发指南

> 这是给 Claude Code 的项目开发指南，包含架构决策、编码规范和开发工作流。

---

## 项目概述

Crew Media Ops 是基于 CrewAI 的自媒体运营 Multi-Agent 系统，实现从选题、创作、发布到数据分析的全链路自动化。

**目标用户**: 自己/小团队使用
**支持平台**: 小红书、微信公众号、微博、知乎、抖音、B站（6 个）
**核心场景**: 内容批量生产 + 全流程自动化

---

## 文档规范

**所有新文档必须放在 `docs/` 目录下，按以下分类存放：**

```
docs/
├── architecture/     # 系统架构、技术选型、升级计划
├── prd/              # 产品需求文档
├── platforms/        # 各平台运营指南（小红书、知乎、微信、微博、抖音、B站）
├── research/         # 爆款研究、竞品分析、E2E 测试报告
├── features/         # 功能指南
└── content-samples/  # 内容样例
```

**开发进度：** `docs/PROGRESS.md` — 里程碑和当前状态追踪，每次完成功能后更新

**禁止：** 在根目录创建 `.md` 文档（除 README.md、CLAUDE.md 外）

**临时产物：** `screenshots/`、`generated_images/`、`reports/` 已加入 `.gitignore`，不要提交

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Agent 框架 | CrewAI | 多 agent 编排 |
| LLM | Claude (Anthropic) | 主力模型，OpenAI 备选 |
| 后端框架 | FastAPI | API 服务（可选） |
| 数据验证 | Pydantic v2 | 类型安全 |
| 任务调度 | APScheduler | 定时发布 |
| 持久化 | SQLite → PostgreSQL | 数据存储 |
| 浏览器自动化 | Playwright | 平台发布 |
| CLI 框架 | Typer + Rich | 命令行工具 |

---

## 项目结构

```
C:\11projects\Crew\
├── src/
│   ├── agents/              # Agent 定义
│   │   ├── base_agent.py        # Agent 基类
│   │   ├── topic_researcher.py  # 选题研究员
│   │   ├── content_writer.py    # 内容创作者
│   │   ├── content_reviewer.py  # 内容审核员
│   │   ├── platform_adapter.py  # 平台适配师
│   │   ├── platform_publisher.py # 平台发布员
│   │   └── data_analyst.py      # 数据分析师
│   ├── tools/               # 工具定义
│   │   ├── base_tool.py         # Tool 基类
│   │   ├── search_tools.py      # 热点搜索、竞品分析
│   │   ├── content_tools.py     # 配图、话题、SEO
│   │   ├── analytics_tools.py   # 数据采集、报告
│   │   └── platform/            # 平台发布工具
│   │       ├── base.py          # 平台工具基类
│   │       ├── xiaohongshu.py
│   │       ├── wechat.py
│   │       ├── weibo.py
│   │       ├── zhihu.py
│   │       ├── douyin.py
│   │       └── bilibili.py
│   ├── crew/crews/         # Crew 编排
│   │   ├── base_crew.py         # Crew 基类
│   │   ├── content_crew.py      # 内容生产线
│   │   ├── publish_crew.py      # 发布线
│   │   └── analytics_crew.py    # 分析线
│   ├── schemas/             # Pydantic 数据模型
│   │   ├── content_brief.py
│   │   ├── content_draft.py
│   │   ├── publish_result.py
│   │   └── analytics_report.py
│   ├── models/              # SQLAlchemy 数据库模型
│   │   ├── base.py
│   │   ├── content.py
│   │   ├── publish_log.py
│   │   └── analytics.py
│   ├── core/                # 核心配置
│   │   ├── config.py            # Settings 配置
│   │   └── logging.py           # 日志配置
│   └── api/                 # FastAPI（可选）
│       ├── main.py
│       └── routes/
├── scripts/                 # CLI 入口
│   ├── run_content_crew.py
│   ├── run_publish_crew.py
│   └── run_analytics_crew.py
├── tests/                   # 测试
│   ├── conftest.py              # pytest fixtures
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
├── data/                    # 数据存储
└── pyproject.toml          # 项目配置
```

---

## 编码规范

### Python 风格

- 遵循 PEP 8 和项目 ruff 配置
- 行宽 100 字符
- 使用 type hints
- 使用 Pydantic 进行数据验证
- 不使用 `any` 类型

### 文件组织

- 文件 < 400 行，函数 < 50 行
- 按功能/领域组织，不按类型
- `__init__.py` 用于导出公共 API

### 命名约定

```python
# Agent 类：PascalCase，以 Agent 结尾
class TopicResearcherAgent: ...

# Tool 类：PascalCase，以 Tool 结尾
class HotSearchTool: ...

# Crew 类：PascalCase，以 Crew 结尾
class ContentCrew: ...

# 函数/变量：snake_case
def collect_metrics(): ...
content_draft = ...

# 常量：UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
```

### 错误处理

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def publish_content(content: dict) -> PublishResult:
    """发布内容到平台，带重试"""
    try:
        result = await platform.publish(content)
        return PublishResult(success=True, url=result.url)
    except PlatformError as e:
        logger.error(f"发布失败: {e}")
        return PublishResult(success=False, error=str(e))
```

---

## Agent 开发指南

### Agent 定义模式

```python
from crewai import Agent
from langchain_anthropic import ChatAnthropic

from src.agents.base_agent import BaseAgent

class ContentWriterAgent(BaseAgent):
    """内容创作者 Agent"""

    role = "内容创作者"
    goal = "根据选题和平台特性创作高质量、高传播力的内容"
    backstory = """
    你是一位全能型内容创作者，擅长撰写各类风格的文案。
    你能根据不同平台的调性调整写作风格，同时保证内容的原创性和吸引力。
    """
    llm_model = "claude-opus-4-20250514"

    def __init__(self):
        super().__init__(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            llm=ChatAnthropic(model=self.llm_model),
            tools=[...],  # 注入工具
            verbose=True,
        )
```

### Tool 定义模式

```python
from crewai import tool
from src.tools.base_tool import BaseTool, ToolResult

class HotSearchTool(BaseTool):
    """热点搜索工具"""

    @tool("热点搜索")
    def execute(self, keywords: str, platform: str) -> ToolResult:
        """
        搜索指定平台的热点话题。

        Args:
            keywords: 搜索关键词
            platform: 目标平台 (xiaohongshu, weibo, etc.)

        Returns:
            ToolResult 包含热点话题列表
        """
        # 实现逻辑
        return ToolResult(
            success=True,
            data={"topics": [...]},
            message="搜索完成"
        )
```

### Crew 编排模式

```python
from crewai import Crew, Process

from src.agents.topic_researcher import TopicResearcherAgent
from src.agents.content_writer import ContentWriterAgent
from src.agents.content_reviewer import ContentReviewerAgent

class ContentCrew:
    """内容生产线 Crew"""

    def __init__(self):
        self.researcher = TopicResearcherAgent()
        self.writer = ContentWriterAgent()
        self.reviewer = ContentReviewerAgent()

    def create_crew(self, tasks: list) -> Crew:
        return Crew(
            agents=[self.researcher, self.writer, self.reviewer],
            tasks=tasks,
            process=Process.sequential,  # 顺序执行
            memory=True,                 # 启用共享记忆
            verbose=True,
        )

    def run(self, topic: str, platforms: list[str]) -> ContentDraft:
        """运行内容生产线"""
        tasks = self._create_tasks(topic, platforms)
        crew = self.create_crew(tasks)
        result = crew.kickoff()
        return ContentDraft.model_validate(result)
```

---

## 平台集成指南

### 平台工具基类

```python
from abc import abstractmethod
from src.tools.base_tool import BaseTool

class BasePlatformTool(BaseTool):
    """平台工具抽象基类"""

    # 平台约束
    max_title_length: int = 100
    max_body_length: int = 10000
    max_images: int = 9
    min_publish_interval: int = 30  # 秒

    @abstractmethod
    def authenticate(self) -> bool:
        """认证"""
        pass

    @abstractmethod
    def publish(self, content: PublishContent) -> PublishResult:
        """发布内容"""
        pass

    @abstractmethod
    def get_analytics(self, content_id: str) -> AnalyticsReport:
        """获取数据分析"""
        pass

    @abstractmethod
    def schedule(self, content: PublishContent, publish_time: datetime) -> bool:
        """定时发布"""
        pass
```

### 复用 MetaBot Skills

各平台发布工具可复用 MetaBot 现有 skills：

| 平台 | Skill | 路径 |
|------|-------|------|
| 小红书 | `media-publish-xiaohongshu` | `~/.claude/skills/media-publish/` |
| 微信公众号 | `baoyu-post-to-wechat` | `~/.claude/skills/` |
| 微博 | `media-publish-weibo` | `~/.claude/skills/media-publish/` |
| 知乎 | `media-publish-zhihu` | `~/.claude/skills/media-publish/` |

---

## 测试规范

### 测试结构

```python
# tests/unit/test_tools.py
import pytest
from unittest.mock import Mock, patch

from src.tools.search_tools import HotSearchTool

class TestHotSearchTool:
    """热点搜索工具测试"""

    @pytest.fixture
    def tool(self):
        return HotSearchTool()

    def test_execute_with_valid_keywords(self, tool):
        """测试有效关键词搜索"""
        # Arrange
        keywords = "AI创业"
        platform = "xiaohongshu"

        # Act
        result = tool.execute(keywords, platform)

        # Assert
        assert result.success is True
        assert "topics" in result.data

    def test_execute_with_empty_keywords_raises_error(self, tool):
        """测试空关键词抛出错误"""
        with pytest.raises(ValueError):
            tool.execute("", "xiaohongshu")
```

### Mock LLM 响应

```python
# tests/conftest.py
@pytest.fixture
def mock_llm_response():
    """Mock LLM 响应"""
    return {
        "topic": "AI创业",
        "title": "AI创业的5个关键建议",
        "body": "...",
        "hashtags": ["AI创业", "创业", "科技"]
    }

@pytest.fixture
def mock_agent(mock_llm_response):
    """Mock Agent"""
    agent = Mock()
    agent.execute.return_value = mock_llm_response
    return agent
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/unit/test_tools.py -v

# 查看覆盖率
uv run pytest --cov=src --cov-report=html
```

---

## CLI 开发指南

### 使用 Typer

```python
# scripts/run_content_crew.py
import typer
from rich.console import Console
from rich.progress import Progress

app = typer.Typer()
console = Console()

@app.command()
def run(
    topic: str = typer.Option(..., "--topic", "-t", help="选题主题"),
    platforms: str = typer.Option(..., "--platforms", "-p", help="目标平台，逗号分隔"),
    brand_voice: str = typer.Option("专业但不失亲和", "--brand-voice", "-b", help="品牌调性"),
    output: str = typer.Option(None, "--output", "-o", help="输出文件路径"),
    dry_run: bool = typer.Option(False, "--dry-run", help="模拟运行"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """运行内容生产线"""
    with Progress() as progress:
        task = progress.add_task("[green]生成内容...", total=100)
        # 实现逻辑
        progress.update(task, advance=100)

    console.print("[green]✓[/green] 内容生成完成！")

if __name__ == "__main__":
    app()
```

---

## 配置管理

### 环境变量

```python
# src/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""

    # LLM
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # 平台
    xiaohongshu_cookie: str | None = None
    wechat_app_id: str | None = None
    wechat_app_secret: str | None = None
    weibo_cookie: str | None = None
    zhihu_cookie: str | None = None
    douyin_cookie: str | None = None
    bilibili_cookie: str | None = None

    # 数据库
    database_url: str = "sqlite:///data/crew.db"

    # 日志
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

---

## 开发工作流

每次完成一个模块后，必须执行以下流程：

1. **假定有问题，先测试** — 使用 `/qa` skill 对新完成的模块进行系统性测试
2. **修复发现的问题** — `/qa` 会自动定位并修复 bug，每个 fix 一个原子 commit
3. **全部通过后 commit** — 只有测试全部通过、健康分无下降，才提交功能代码

```
开发 → /qa 测试 → 修复 → 再验证 → commit
```

**禁止：** 跳过测试直接 commit 功能代码

---

## 常见问题

### Q: 如何添加新平台？

1. 在 `src/tools/platform/` 创建新文件，继承 `BasePlatformTool`
2. 实现 `authenticate()`, `publish()`, `get_analytics()`, `schedule()` 方法
3. 在 `src/tools/platform/__init__.py` 注册到工厂函数
4. 添加对应的测试

### Q: 如何调试 Agent 行为？

1. 设置 `verbose=True` 查看 Agent 思考过程
2. 查看日志文件 `logs/crew.log`
3. 使用 `--dry-run` 模式模拟运行

### Q: 如何处理平台风控？

1. 遵守各平台的 `min_publish_interval`
2. 使用 `--schedule` 分散发布时间
3. 首次使用用小号测试
4. 模拟人工操作间隔

---

## 相关资源

- [CrewAI 文档](https://docs.crewai.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [Playwright 文档](https://playwright.dev/python/)
- [Typer 文档](https://typer.tiangolo.com/)

---

_最后更新：2026-03-20_
