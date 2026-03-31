"""
端到端内容生产管线：选题→创作→审核→平台适配→保存输出文件

用法:
    uv run python scripts/run_e2e_pipeline.py --topic "AI编程工具" --platforms wechat,xiaohongshu
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 修复 Windows GBK 编码问题
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool as crewai_tool


# ============================================================
# 1. 搜索工具（包装为 CrewAI tool）
# ============================================================

@crewai_tool("hot_search")
def hot_search_tool(platform: str, keywords: str) -> str:
    """Search trending topics on a platform. Args: platform (weibo/xiaohongshu/douyin/zhihu/bilibili), keywords (search terms)."""
    # 这些工具返回模拟数据——Agent 会用自己的知识来补充
    return json.dumps({
        "platform": platform,
        "note": "Tool returned simulated data. Use your own knowledge to research real trends.",
        "keywords": keywords,
        "suggestion": f"Research current trends about '{keywords}' based on your knowledge."
    }, ensure_ascii=False)


@crewai_tool("competitor_analysis")
def competitor_analysis_tool(platform: str, topic: str) -> str:
    """Analyze competitor content on a platform for a given topic. Args: platform, topic."""
    return json.dumps({
        "platform": platform,
        "topic": topic,
        "note": "Use your knowledge to analyze what kind of content performs well for this topic."
    }, ensure_ascii=False)


@crewai_tool("trend_analysis")
def trend_analysis_tool(keyword: str) -> str:
    """Analyze trends for a keyword across platforms. Args: keyword."""
    return json.dumps({
        "keyword": keyword,
        "note": "Use your knowledge to assess the trend direction and potential of this keyword."
    }, ensure_ascii=False)


# ============================================================
# 2. Agent 定义
# ============================================================

def create_topic_researcher(llm: str) -> Agent:
    return Agent(
        role="选题研究员",
        goal="分析热点趋势，挖掘高潜力选题，为内容创作提供数据支持和方向建议",
        backstory="""你是一位资深的自媒体选题研究员，对各大内容平台的热点机制了如指掌。
你能够快速捕捉趋势，找到差异化的选题方向。你的选题报告数据翔实、洞察深刻。
注意：你不需要使用任何工具，直接基于你的知识和经验来分析选题。""",
        tools=[],  # 不给工具——proxy 不支持 tool_use 的 assistant prefill
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_content_writer(llm: str) -> Agent:
    return Agent(
        role="内容创作者",
        goal="根据选题报告创作高质量、有深度、有传播力的原创内容",
        backstory="""你是一位才华横溢的内容创作者，精通各种风格的文案写作。
你的文字既有深度又有趣味性，总能抓住读者的注意力。
你擅长将复杂概念用通俗方式表达，同时保持专业性。""",
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_content_reviewer(llm: str) -> Agent:
    return Agent(
        role="内容审核员",
        goal="严格审核内容质量、准确性和合规性，提供具体优化建议",
        backstory="""你是一位资深的内容审核专家。
你对各平台的内容规范了如指掌，能够快速识别问题和潜在风险。
你的审核标准严格但公正，总是能提供可操作的优化建议。""",
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        human_input=False,
    )


def create_platform_adapter(llm: str) -> Agent:
    return Agent(
        role="平台适配师",
        goal="将通用内容精准适配到各平台的格式和风格要求，确保每个平台都能获得最佳表现",
        backstory="""你是一位全能的平台适配专家，对各大内容平台的特性如数家珍。
你深谙微信公众号的深度阅读氛围、小红书的种草文化。
你能将同一内容在不同平台上转化为完全不同的呈现形式，同时保持核心信息一致。
你了解每个平台的推荐算法偏好，能针对性优化内容以获得更好的流量。""",
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


# ============================================================
# 3. Task 定义
# ============================================================

def create_tasks(
    topic: str,
    platforms: list[str],
    researcher: Agent,
    writer: Agent,
    reviewer: Agent,
    adapter: Agent,
) -> list[Task]:
    platform_names = {"wechat": "微信公众号", "xiaohongshu": "小红书"}
    platform_display = "、".join(platform_names.get(p, p) for p in platforms)

    # Task 1: 选题研究
    research_task = Task(
        description=f"""
对以下主题进行选题研究：

**主题**: {topic}
**目标平台**: {platform_display}

请基于你的知识和经验执行以下分析：
1. 分析该主题在国内自媒体领域的热度和趋势
2. 分析该主题在目标平台上什么样的内容表现好
3. 找到 2-3 个最有潜力的选题角度

输出要求（JSON 格式）：
{{
    "selected_topic": {{
        "title": "推荐的选题标题",
        "angle": "选题切入角度",
        "target_audience": "目标受众描述",
        "reasoning": "为什么选这个角度"
    }},
    "keywords": ["关键词1", "关键词2", "..."],
    "content_direction": "内容方向建议"
}}
""",
        expected_output="JSON 格式的选题报告，包含推荐选题、关键词和内容方向",
        agent=researcher,
    )

    # Task 2: 内容创作
    write_task = Task(
        description=f"""
根据选题报告创作一篇高质量的原创文章：

**目标平台**: {platform_display}
**内容类型**: 深度文章

创作要求：
1. 从选题报告中获取主题方向和关键词
2. 撰写一篇 1000-2000 字的深度文章
3. 标题要有吸引力，正文有逻辑有深度
4. 内容要有实用价值，读者能获得启发或知识

输出要求（JSON 格式）：
{{
    "title": "文章标题",
    "content": "完整的文章正文（Markdown 格式）",
    "summary": "100字以内的文章摘要",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}}
""",
        expected_output="JSON 格式的内容草稿，包含标题、正文、摘要、标签",
        agent=writer,
        context=[research_task],
    )

    # Task 3: 内容审核
    review_task = Task(
        description="""
审核内容草稿的质量和合规性：

请检查以下方面：
1. 质量：内容结构、逻辑性、专业性、可读性
2. 合规：无敏感内容、无虚假信息、符合平台规则
3. 传播：标题吸引力、内容传播潜力
4. 如有问题，提供具体修改建议

输出要求（JSON 格式）：
{
    "result": "approved 或 needs_revision",
    "overall_score": 85,
    "quality_score": 88,
    "compliance_score": 90,
    "spread_score": 80,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "highlights": ["亮点1", "亮点2"],
    "final_content": {
        "title": "审核后的标题（如有修改）",
        "content": "审核后的正文（如有修改，否则保持原文）",
        "summary": "审核后的摘要",
        "tags": ["标签列表"]
    }
}
""",
        expected_output="JSON 格式的审核报告，包含评分、问题、建议和最终内容",
        agent=reviewer,
        context=[write_task],
    )

    # Task 4: 平台适配
    platform_specs = []
    if "wechat" in platforms:
        platform_specs.append("""
**微信公众号版本**:
- 标题: ≤64字，专业深度风格
- 正文: 1500-3000字，Markdown 格式，深度长文
- 摘要: ≤200字
- 标签: 3-5个
- 风格: 专业、有深度、适合深度阅读""")

    if "xiaohongshu" in platforms:
        platform_specs.append("""
**小红书版本**:
- 标题: ≤20字，吸引眼球，可以用emoji
- 正文: 500-1000字，轻松口语化，用emoji增加可读性
- 摘要: ≤100字
- 标签: 5-10个，带#号
- 风格: 轻松、实用、种草感，像和朋友聊天""")

    adapt_task = Task(
        description=f"""
将审核通过的内容适配到不同平台版本。

请根据以下平台规格生成对应版本：
{"".join(platform_specs)}

重要要求：
- 每个平台版本是独立的完整内容，不是简单的复制粘贴
- 保持核心信息一致，但风格和表达要完全适应平台调性
- 微信版偏专业深度，小红书版偏轻松种草

输出要求（JSON 格式）：
{{
    "platforms": {{
        "wechat": {{
            "title": "微信版标题",
            "content": "微信版正文（Markdown）",
            "summary": "微信版摘要",
            "tags": ["标签1", "标签2"]
        }},
        "xiaohongshu": {{
            "title": "小红书版标题",
            "content": "小红书版正文",
            "summary": "小红书版摘要",
            "tags": ["#标签1", "#标签2"]
        }}
    }}
}}

注意：只输出目标平台（{platform_display}）的版本。
""",
        expected_output="JSON 格式，包含各平台适配后的完整内容",
        agent=adapter,
        context=[review_task],
    )

    return [research_task, write_task, review_task, adapt_task]


# ============================================================
# 4. 输出处理
# ============================================================

def extract_json(text: str) -> dict | None:
    """从 LLM 输出中提取 JSON。"""
    # 尝试直接解析
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试从 markdown code block 中提取
    import re
    patterns = [
        r'```json\s*\n([\s\S]*?)\n```',
        r'```\s*\n([\s\S]*?)\n```',
        r'\{[\s\S]*\}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                candidate = match.group(1) if match.lastindex else match.group(0)
                return json.loads(candidate)
            except (json.JSONDecodeError, TypeError, IndexError):
                continue
    return None


def save_outputs(result_text: str, platforms: list[str], output_dir: Path) -> dict[str, Path]:
    """解析结果并保存为各平台的 Markdown 文件。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files = {}

    data = extract_json(result_text)
    if not data:
        # 如果无法解析 JSON，保存原始输出
        raw_path = output_dir / "raw_output.md"
        raw_path.write_text(result_text, encoding="utf-8")
        print(f"  [!] 无法解析 JSON，原始输出已保存到: {raw_path}")
        saved_files["raw"] = raw_path
        return saved_files

    platforms_data = data.get("platforms", data)

    for platform in platforms:
        p_data = platforms_data.get(platform, {})
        if not p_data:
            print(f"  [!] 未找到 {platform} 的适配内容")
            continue

        title = p_data.get("title", "无标题")
        content = p_data.get("content", "")
        summary = p_data.get("summary", "")
        tags = p_data.get("tags", [])

        # 构建 Markdown 文件
        lines = [f"# {title}", ""]
        if summary:
            lines.extend([f"> {summary}", ""])
        lines.extend([content, ""])
        if tags:
            tag_line = " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
            lines.extend(["---", "", tag_line])

        md_content = "\n".join(lines)
        filename = f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = output_dir / filename
        filepath.write_text(md_content, encoding="utf-8")
        saved_files[platform] = filepath
        print(f"  [OK] {platform} 内容已保存: {filepath}")

    # 保存完整 JSON
    json_path = output_dir / "full_output.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    saved_files["json"] = json_path

    return saved_files


# ============================================================
# 5. 主流程
# ============================================================

def run_pipeline(
    topic: str,
    platforms: list[str],
    writer_model: str = "claude-sonnet-4-6",
    other_model: str = "claude-sonnet-4-6",
    verbose: bool = True,
) -> dict:
    """运行完整的内容生产管线。"""

    print("=" * 60)
    print(f"  Crew Media Ops — 端到端内容生产管线")
    print(f"  主题: {topic}")
    print(f"  平台: {', '.join(platforms)}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    start_time = time.time()

    # CrewAI 使用 "anthropic/model" 格式字符串，自动读取 ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL
    writer_llm = f"anthropic/{writer_model}"
    other_llm = f"anthropic/{other_model}"

    print("\n[1/5] 创建 Agents...")
    researcher = create_topic_researcher(other_llm)
    writer = create_content_writer(writer_llm)
    reviewer = create_content_reviewer(other_llm)
    adapter = create_platform_adapter(other_llm)
    print("  Agents: 选题研究员, 内容创作者, 内容审核员, 平台适配师")

    print("\n[2/5] 创建 Tasks...")
    tasks = create_tasks(topic, platforms, researcher, writer, reviewer, adapter)
    print(f"  Tasks: {len(tasks)} 个 (研究→创作→审核→适配)")

    print("\n[3/5] 构建 Crew...")
    crew = Crew(
        agents=[researcher, writer, reviewer, adapter],
        tasks=tasks,
        process=Process.sequential,
        memory=False,  # 关闭 memory 减少复杂度
        verbose=verbose,
    )

    print("\n[4/5] 开始执行...")
    print("  (这可能需要 2-5 分钟，取决于 LLM 响应速度)")
    print("-" * 60)

    try:
        result = crew.kickoff()
        elapsed = time.time() - start_time

        print("-" * 60)
        print(f"\n[5/5] 执行完成! 耗时: {elapsed:.1f} 秒")

        # 获取最终输出
        final_output = str(result)

        # 保存输出文件
        output_dir = PROJECT_ROOT / "data" / "outputs" / datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n保存输出文件...")
        saved_files = save_outputs(final_output, platforms, output_dir)

        # 保存各阶段原始输出
        if hasattr(result, "tasks_output"):
            stages_dir = output_dir / "stages"
            stages_dir.mkdir(parents=True, exist_ok=True)
            stage_names = ["1_research", "2_writing", "3_review", "4_adaptation"]
            for i, task_out in enumerate(result.tasks_output):
                stage_name = stage_names[i] if i < len(stage_names) else f"stage_{i}"
                raw = task_out.raw if hasattr(task_out, "raw") else str(task_out)
                stage_file = stages_dir / f"{stage_name}.md"
                stage_file.write_text(raw, encoding="utf-8")
                print(f"  [OK] 阶段 {stage_name} 输出已保存")

        return {
            "success": True,
            "elapsed": elapsed,
            "output_dir": str(output_dir),
            "saved_files": {k: str(v) for k, v in saved_files.items()},
            "final_output": final_output,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[ERROR] 执行失败 ({elapsed:.1f}s): {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "elapsed": elapsed,
            "error": str(e),
        }


# ============================================================
# 6. CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Crew Media Ops 端到端管线")
    parser.add_argument("--topic", "-t", default="AI编程工具如何改变开发者工作流",
                        help="选题主题")
    parser.add_argument("--platforms", "-p", default="wechat,xiaohongshu",
                        help="目标平台（逗号分隔）")
    parser.add_argument("--writer-model", default="claude-sonnet-4-6",
                        help="内容创作者使用的模型")
    parser.add_argument("--other-model", default="claude-sonnet-4-6",
                        help="其他 Agent 使用的模型")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="安静模式（减少输出）")
    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",")]

    result = run_pipeline(
        topic=args.topic,
        platforms=platforms,
        writer_model=args.writer_model,
        other_model=args.other_model,
        verbose=not args.quiet,
    )

    if result["success"]:
        print("\n" + "=" * 60)
        print("  管线执行成功!")
        print(f"  总耗时: {result['elapsed']:.1f} 秒")
        print(f"  输出目录: {result['output_dir']}")
        for platform, filepath in result.get("saved_files", {}).items():
            print(f"  - {platform}: {filepath}")
        print("=" * 60)
    else:
        print(f"\n管线执行失败: {result.get('error', 'unknown')}")
        sys.exit(1)
