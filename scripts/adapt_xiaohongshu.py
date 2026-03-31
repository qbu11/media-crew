"""
轻量脚本：将微信版文章适配为小红书版笔记。
单次 LLM 调用，不走 CrewAI。
"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from anthropic import Anthropic

WECHAT_ARTICLE = Path("data/outputs/20260324_185208/wechat/article.md")
XHS_DIR = Path("data/outputs/20260324_185208/xiaohongshu")

client = Anthropic()

wechat_content = WECHAT_ARTICLE.read_text(encoding="utf-8")

prompt = f"""请将以下微信公众号文章改写为小红书笔记风格。

要求：
- 标题：≤20字，吸引眼球，可以用emoji
- 正文：500-1000字，轻松口语化，用emoji增加可读性
- 像和朋友聊天一样的语气
- 保持核心信息（3款工具对比 + 3个坑），但大幅精简
- 摘要：≤100字
- 标签：5-10个，带#号

输出严格按以下 JSON 格式（不要加 ```json 代码块标记）：
{{
    "title": "小红书版标题",
    "content": "小红书版正文（用\\n表示换行）",
    "summary": "小红书版摘要",
    "tags": ["#标签1", "#标签2", "#标签3"]
}}

原文：
{wechat_content[:4000]}
"""

print("调用 LLM 生成小红书版...")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}],
)

result_text = response.content[0].text.strip()
print(f"LLM 返回 {len(result_text)} 字符")

# Parse JSON
try:
    # Remove code fences if present
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1]
    if result_text.endswith("```"):
        result_text = result_text.rsplit("```", 1)[0]
    result_text = result_text.strip()

    data = json.loads(result_text)
except json.JSONDecodeError as e:
    print(f"JSON 解析失败: {e}")
    print(f"原始输出:\n{result_text[:500]}")
    sys.exit(1)

# Save
XHS_DIR.mkdir(parents=True, exist_ok=True)

content = data["content"]
(XHS_DIR / "note.md").write_text(content, encoding="utf-8")

meta = {k: v for k, v in data.items() if k != "content"}
(XHS_DIR / "metadata.json").write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
)

print(f"\n[OK] 小红书版已保存到 {XHS_DIR}/")
print(f"  标题: {data['title']}")
print(f"  正文: {len(content)} 字符")
print(f"  标签: {data['tags']}")
