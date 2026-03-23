"""
Crew 使用示例

演示如何使用 3 个核心 Crew。
"""


# 导入 Crew
from src.crew.crews import (
    AnalyticsCrew,
    AnalyticsCrewInput,
    ContentCrew,
    ContentCrewInput,
    PublishCrew,
    PublishCrewInput,
)


def example_content_crew():
    """
    ContentCrew 使用示例。

    流程：选题研究 → 内容创作 → 内容审核
    """
    print("\n=== ContentCrew Example ===\n")

    # 创建 Crew
    crew = ContentCrew.create(
        enable_human_review=True,  # 启用人工审核
        verbose=True,
    )

    # 准备输入
    inputs = ContentCrewInput(
        industry="科技",
        keywords=["AI", "大模型", "ChatGPT"],
        target_platform="xiaohongshu",
        content_type="article",
        research_depth="standard",
        enable_human_review=True,
    )

    # 执行 Crew
    result = crew.execute(inputs)

    # 处理结果
    if result.is_success():
        print(f"选题报告: {result.topic_report}")
        print(f"内容草稿: {result.content_draft}")
        print(f"审核报告: {result.review_report}")

        if result.is_approved:
            print("内容已通过审核，可以发布！")
        else:
            print("内容需要修改。")
    else:
        print(f"执行失败: {result.error}")

    print(f"执行时间: {result.execution_time:.2f}秒")


def example_publish_crew():
    """
    PublishCrew 使用示例。

    流程：平台适配 → 并行发布
    """
    print("\n=== PublishCrew Example ===\n")

    # 创建 Crew
    crew = PublishCrew.create(
        enable_retry=True,
        max_retries=3,
        verbose=True,
    )

    # 模拟已审核通过的内容草稿
    content_draft = {
        "title": "AI 大模型的未来发展趋势",
        "content": "随着 ChatGPT 的爆火，大模型技术正在快速发展...",
        "summary": "探讨 AI 大模型的技术发展和应用前景",
        "tags": ["AI", "大模型", "科技"],
    }

    # 准备输入
    inputs = PublishCrewInput(
        content_id="content_001",
        content_draft=content_draft,
        target_platforms=["xiaohongshu", "weibo", "zhihu"],
        schedule_time=None,  # 立即发布
    )

    # 执行 Crew
    result = crew.execute(inputs)

    # 处理结果
    if result.is_success():
        print(f"适配内容: {result.adapted_contents}")
        print(f"发布记录: {result.publish_records}")

        if result.all_success:
            print("所有平台发布成功！")
        else:
            print(f"成功平台: {result.successful_platforms}")
            print(f"失败平台: {result.failed_platforms}")

        print(f"成功率: {result.data['summary']['success_rate']}")
    else:
        print(f"执行失败: {result.error}")


def example_analytics_crew():
    """
    AnalyticsCrew 使用示例。

    流程：数据采集 → 数据分析 → 优化建议
    """
    print("\n=== AnalyticsCrew Example ===\n")

    # 创建 Crew
    crew = AnalyticsCrew.create(
        verbose=True,
    )

    # 准备输入
    inputs = AnalyticsCrewInput(
        content_ids=["content_001", "content_002", "content_003"],
        time_range="7d",
        platforms=["xiaohongshu", "weibo"],
        metrics=["views", "likes", "comments", "shares"],
        report_format="json",
    )

    # 执行 Crew
    result = crew.execute(inputs)

    # 处理结果
    if result.is_success():
        print(f"采集数据: {len(result.collected_data)} 条")

        # 打印关键发现
        for finding in result.key_findings:
            print(f"- {finding}")

        # 打印优化建议
        print("\n优化建议:")
        for rec in result.recommendations[:5]:
            print(f"- {rec}")

        # 生成 Markdown 报告
        print("\n" + result.to_markdown_report())
    else:
        print(f"执行失败: {result.error}")


def example_quick_kickoff():
    """
    快速 kickoff 示例。
    """
    print("\n=== Quick Kickoff Example ===\n")

    # ContentCrew 快速 kickoff
    ContentCrew.create().kickoff(
        industry="科技",
        keywords=["AI"],
        target_platform="xiaohongshu",
    )

    # PublishCrew 快速 kickoff
    PublishCrew.create().kickoff(
        content_id="content_001",
        content_draft={
            "title": "测试标题",
            "content": "测试内容",
        },
        target_platforms=["xiaohongshu"],
    )

    # AnalyticsCrew 快速 kickoff
    AnalyticsCrew.create().kickoff(
        content_ids=["content_001"],
        time_range="7d",
    )


def example_end_to_end():
    """
    端到端流程示例。

    演示完整的内容生产 → 发布 → 分析流程。
    """
    print("\n=== End-to-End Workflow Example ===\n")

    # 步骤 1：内容生产
    print("步骤 1: 内容生产")
    content_crew = ContentCrew.create(enable_human_review=False)
    content_result = content_crew.kickoff(
        industry="科技",
        keywords=["AI", "大模型"],
        target_platform="xiaohongshu",
    )

    if not content_result.is_success():
        print(f"内容生产失败: {content_result.error}")
        return

    content_draft = content_result.content_draft
    print(f"内容已创作: {content_draft.get('title')}")

    # 步骤 2：发布
    print("\n步骤 2: 内容发布")
    publish_crew = PublishCrew.create()
    publish_result = publish_crew.kickoff(
        content_id="content_001",
        content_draft=content_draft,
        target_platforms=["xiaohongshu", "weibo"],
    )

    if not publish_result.is_success():
        print(f"发布失败: {publish_result.error}")
        return

    print(f"发布成功: {publish_result.successful_platforms}")

    # 步骤 3：数据分析
    print("\n步骤 3: 数据分析")
    analytics_crew = AnalyticsCrew.create()
    analytics_result = analytics_crew.kickoff(
        content_ids=["content_001"],
        time_range="24h",
    )

    if not analytics_result.is_success():
        print(f"分析失败: {analytics_result.error}")
        return

    print(f"分析完成，发现 {len(analytics_result.key_findings)} 条关键洞察")


if __name__ == "__main__":
    # 运行示例
    example_content_crew()
    example_publish_crew()
    example_analytics_crew()
    example_end_to_end()
