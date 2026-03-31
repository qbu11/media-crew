"""实跑 ContentCrew 测试脚本 - 验证 prompt 优化后的输出质量."""

import io
import json
import os
import sys
import time

# UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 确保项目根目录在 path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.crew.crews.content_crew import ContentCrew, ContentCrewInput


def main():
    print("=" * 60)
    print("ContentCrew 实跑测试")
    print("=" * 60)

    # 创建输入
    inputs = ContentCrewInput(
        topic="AI Agent 创业：从 0 到 1 的实战经验",
        target_platform="xiaohongshu",
        content_type="article",
        research_depth="standard",
        viral_category="科技创业",
    )

    # 创建 ContentCrew（禁用人工审核和 memory）
    crew = ContentCrew(
        verbose=True,
        enable_human_review=False,
        memory=False,
    )

    print(f"\n主题: {inputs.inputs['topic']}")
    print(f"平台: {inputs.inputs['target_platform']}")
    print(f"人工审核: {crew.enable_human_review}")
    print("-" * 60)

    # 执行
    start = time.time()
    result = crew.execute(inputs)
    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"执行完成 ({elapsed:.1f}s)")
    print(f"状态: {result.status}")
    print("=" * 60)

    # 输出结果
    if hasattr(result, "content_draft") and result.content_draft:
        print("\n--- 内容草稿 ---")
        draft = result.content_draft
        if isinstance(draft, str):
            print(draft[:3000])
        elif isinstance(draft, dict):
            print(json.dumps(draft, ensure_ascii=False, indent=2)[:3000])
        else:
            print(str(draft)[:3000])

    if hasattr(result, "review_report") and result.review_report:
        print("\n--- 审核报告 ---")
        report = result.review_report
        if isinstance(report, str):
            print(report[:2000])
        elif isinstance(report, dict):
            print(json.dumps(report, ensure_ascii=False, indent=2)[:2000])
        else:
            print(str(report)[:2000])

    # result.data 结构
    if result.data:
        print("\n--- result.data keys ---")
        print(list(result.data.keys()) if isinstance(result.data, dict) else type(result.data))
        print("\n--- result.data (前 5000 字符) ---")
        raw = json.dumps(result.data, ensure_ascii=False, default=str, indent=2)
        print(raw[:5000])

    # raw_outputs
    if hasattr(result, "raw_outputs") and result.raw_outputs:
        print("\n--- raw_outputs (前 5000 字符) ---")
        raw = json.dumps(result.raw_outputs, ensure_ascii=False, default=str, indent=2)
        print(raw[:5000])

    if hasattr(result, "metadata") and result.metadata:
        print("\n--- 元数据 ---")
        print(json.dumps(result.metadata, ensure_ascii=False, default=str, indent=2))

    if result.error:
        print(f"\n--- 错误 ---\n{result.error}")

    print("\n" + "=" * 60)
    print("测试结束")


if __name__ == "__main__":
    main()
