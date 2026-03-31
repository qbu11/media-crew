# 爆款对标验证系统使用指南

## 概述

爆款对标验证系统确保每次内容产出都有真实爆款作为参考，防止"凭空创作"。

## 核心规则

1. **至少 5 个爆款对标**
2. **每个爆款至少 2 个维度匹配**
3. **必须提供可验证的链接**

## 5 个分析维度

| 维度 | 分析要点 | 匹配标准 |
|------|----------|----------|
| 结构 | 开头方式、段落划分、信息密度、过渡方式、结尾设计 | 开头方式相同、段落结构相似 |
| 情绪 | 主要情绪、情绪强度、情绪节奏、触发点、收尾 | 情绪类型相同、强度相近 |
| 配图 | 图片数量、类型、风格、图文关系、封面设计 | 数量相近、类型相同 |
| 标题 | 长度、钩子类型、关键词、emoji、标点 | 长度相近、钩子类型相同 |
| 深度 | 长度、信息层次、专业程度、案例使用、实操性 | 层次相同、专业度匹配 |

## 使用示例

### 1. 创建爆款对标数据

```python
from src.tools import ViralReference, ViralReferenceReport, ViralReferenceValidator

# 创建爆款对标
viral_ref = ViralReference(
    platform="xiaohongshu",
    title="混油敏皮闭口反复？这个成分救了我",
    url="https://xiaohongshu.com/explore/123456",
    author="美妆博主小A",
    metrics={"likes": 15000, "comments": 800, "shares": 200},
    structure_analysis={
        "opening_style": "痛点引入",
        "paragraph_count": 5,
        "info_density": "密集",
    },
    emotion_analysis={
        "primary_emotion": "焦虑+期待",
        "intensity": "强烈",
    },
    title_analysis={
        "length": 18,
        "hook_type": "疑问+解决方案",
        "emoji_count": 0,
    },
)
```

### 2. 验证内容草稿

```python
# 内容草稿包含爆款对标
content_draft = {
    "title": "干皮起皮卡粉？这3个方法亲测有效",
    "content": "# 干皮救星\n\n姐妹们！...",
    "viral_references": [
        {
            "title": "混油敏皮闭口反复？这个成分救了我",
            "url": "https://xiaohongshu.com/explore/123456",
            "author": "美妆博主小A",
            "metrics": {"likes": 15000},
            "matched_dimensions": ["结构", "标题"],
            "match_details": {
                "结构": "同样采用痛点引入开头",
                "标题": "都是问题+解决方案的公式"
            }
        },
        # ... 至少 5 个
    ]
}

# 验证
validator = ViralReferenceValidator()
result = validator.validate_content_draft(content_draft)

if result["passed"]:
    print("✅ 爆款对标验证通过")
else:
    print("❌ 验证未通过:")
    for issue in result["issues"]:
        print(f"  - {issue}")
```

### 3. 在 ContentCrew 中使用

```python
from src.crew.crews.content_crew import ContentCrew, ContentCrewInput

# 创建输入
crew_input = ContentCrewInput(
    topic="干皮护肤方法",
    target_platform="xiaohongshu",
    viral_category="美妆护肤",
)

# 运行
crew = ContentCrew()
result = crew.run(crew_input)

# 检查爆款对标验证
if result.viral_check_passed:
    print(f"✅ 爆款对标数量: {result.viral_reference_count}")
else:
    print("❌ 爆款对标验证未通过，需要重新创作")
```

## Agent 任务描述

ContentCreator 会在创作任务中自动包含爆款对标研究：

```
## 第一步：爆款对标研究（必须完成）

**强制规则**：找到至少 5 个 xiaohongshu 平台上与主题相关的真实爆款，
分析 5 个维度：
- 结构分析：开头方式、段落划分、信息密度、过渡方式、结尾设计
- 情绪分析：主要情绪、情绪强度、情绪节奏、触发点、收尾
- 配图分析：图片数量、类型、风格、图文关系、封面设计
- 标题分析：长度、钩子类型、关键词、emoji、标点
- 深度分析：内容长度、信息层次、专业程度、案例使用、实操性

## 第二步：内容创作（基于学习成果）

**必须满足的对标要求**：
- 至少 5 个真实爆款对标
- 每个爆款至少 2 个维度匹配
- 提供可验证的链接和具体匹配说明
```

## 审核员验证

ContentReviewer 会验证爆款对标是否完整：

```json
{
  "viral_check": "passed/failed",
  "viral_count": 5,
  "issues": [
    "爆款对标数量不足，需要至少 5 个",
    "爆款 3 只有 1 个维度匹配，需要至少 2 个"
  ]
}
```

## 上下文保护策略

1. **Subagent 搜索**：爆款搜索委派给 subagent
2. **结构化存储**：爆款数据以 ViralReference 对象存储
3. **摘要输出**：主上下文只保留 ViralReferenceReport.get_summary()

```
主上下文（轻量）:
## 爆款对标验证报告
**平台**: xiaohongshu
**验证结果**: ✅ 通过
### 爆款对标列表 (5 个)
1. 标题1 | 匹配维度: 结构, 情绪
2. 标题2 | 匹配维度: 标题, 深度
...

完整数据（存储）:
- ViralReference 对象包含 5 维度完整分析
- 可用于后续学习和模式提取
```

## 输出格式

完整的内容草稿输出包含：

```json
{
  "title": "内容标题",
  "content": "正文内容",
  "summary": "摘要",
  "tags": ["标签1", "标签2"],
  "style_notes": "风格说明",
  "platform": "xiaohongshu",
  "viral_references": [
    {
      "title": "爆款标题1",
      "url": "原文链接",
      "author": "作者",
      "metrics": {"likes": 1000, "comments": 100},
      "matched_dimensions": ["结构", "情绪"],
      "match_details": {
        "结构": "具体匹配说明",
        "情绪": "具体匹配说明"
      }
    }
  ]
}
```
