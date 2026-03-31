# 知乎文章

## 标题
Agent 工程化的拐点到了：从 .claude/ 文件夹说起

## 正文

上周 Hacker News 上有一篇帖子拿了 382 分：「Anatomy of the .claude/ folder」。

一个配置文件夹，为什么能引发这么大的讨论？因为它代表了 AI 编程工具的一个重要转变——Agent 的竞争焦点正在从「模型能力」转向「Harness 工程」。

### 什么是 Agent Harness？

简单说，Harness 就是 Agent 与外部环境之间的连接层。模型本身只是大脑，Harness 决定了它能看到什么、能操作什么、按什么流程工作。

.claude/ 文件夹就是一个典型的 Harness 实现。它包含：
- CLAUDE.md：项目级指令，告诉 Agent 这个项目的规范和约束
- skills/：可复用的技能模块，Agent 可以按需调用
- settings.json：权限和行为配置

这套机制让 Claude Code 从一个通用聊天机器人变成了一个「了解你项目」的专属开发者。

### 三条线索指向同一个结论

巧合的是，同一天 arXiv 上出现了一篇论文「Natural-Language Agent Harnesses」，提出用自然语言而非代码来定义 Agent 的控制逻辑，使其可迁移、可比较、可研究。

同一天 LangChain 发布了 Agent 评估就绪清单（Agent Evaluation Readiness Checklist），从错误分析、数据集构建到评分器设计，系统化地解决 Agent 评估问题。

还是同一天，Cursor 公开了用实时强化学习优化 Composer 的技术细节。

三条独立的线索指向同一个结论：**Agent 的瓶颈已经从模型能力转向工程质量。**

### 这意味着什么？

对开发者来说，这意味着：

1. **写好 CLAUDE.md 比选模型更重要。** 同一个模型，配上好的 Harness 和差的 Harness，效果天差地别。

2. **Agent 技能将成为新的「包管理」。** 就像 npm 管理 JavaScript 包一样，未来会有专门管理 Agent 技能的生态系统。GitHub 上 superpowers 项目单日涨了近 3000 星，就是这个趋势的信号。

3. **评估体系是护城河。** 谁能更好地衡量 Agent 的表现，谁就能更快地迭代改进。LangChain 在这个方向上投入很重，不是没有原因的。

### 一个值得警惕的趋势

当社区围绕 .claude/ 构建工作流时，切换成本会急剧上升。这是 Anthropic 的护城河策略——不是靠模型锁定你，而是靠生态锁定你。

这和 VS Code 的策略如出一辙：编辑器本身开源免费，但插件生态让你离不开。

对于开发者来说，理解这个趋势比追逐最新模型更重要。**选择一个 Agent 平台，本质上是在选择一个生态系统。**

---

参考来源：
- Anatomy of the .claude/ folder (HN 382分) https://blog.dailydoseofds.com/p/anatomy-of-the-claude-folder
- Natural-Language Agent Harnesses (arXiv) https://arxiv.org/abs/2603.25723
- Agent Evaluation Readiness Checklist (LangChain) https://blog.langchain.com/agent-evaluation-readiness-checklist/
- Improving Composer through real-time RL (Cursor) https://cursor.com/blog/real-time-rl-for-composer
- superpowers (GitHub) https://github.com/obra/superpowers

## 标签
AI Agent, Claude Code, LLM, 软件工程, 开发工具
