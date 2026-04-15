---
name: xiaohongshu-generator
description: 生成小红书风格图片系列 - 11种视觉风格和8种布局，将内容分解为1-10张卡通风格图片
version: 1.56.1
metadata:
  openclaw:
    homepage: https://github.com/JimLiu/baoyu-skills#baoyu-xhs-images
---

# Xiaohongshu Infographic Series Generator - 小红书图片生成器

将复杂内容分解为小红书风格的多张信息图，支持多种视觉风格和布局选择。

## 何时使用

当用户提到以下内容时使用本技能：
- "小红书图片"、"XHS图片"
- "RedNote信息图"
- "小红书种草"
- 需要为中国平台创建社交媒体图片

## 视觉风格

| 风格 | 描述 |
|------|------|
| `cute` (默认) | 甜美可爱，经典小红书风格 |
| `fresh` | 清新干净，自然风格 |
| `warm` | 温馨友好，平易近人 |
| `bold` | 高冲击力，引人注目 |
| `minimal` | 极简干净，高级感 |
| `retro` | 复古怀旧，潮流感 |
| `pop` | 活泼生动，视觉冲击 |
| `notion` | 极简手绘线条，知识分子风格 |
| `chalkboard` | 黑板粉笔， 教育风格 |
| `study-notes` | 真实手写笔记风格 |
| `screen-print` | 潮流海报风格 |

## 布局选项

| 布局 | 描述 |
|------|------|
| `sparse` (默认) | 少量信息，最大冲击 |
| `balanced` | 标准内容布局 |
| `dense` | 高信息密度，知识卡片风格 |
| `list` | 枚举和排名格式 |
| `comparison` | 并排对比布局 |
| `flow` | 流程和时间线布局 |
| `mindmap` | 中心放射思维导图 |
| `quadrant` | 四象限/圆形分区 |

## 预设组合

快速使用预设置的风格+布局组合：

| 预设 | 风格 | 布局 | 最佳用途 |
|------|------|------|---------|
| `knowledge-card` | notion | dense | 干货知识卡、概念科普 |
| `checklist` | notion | list | 清单、排行榜 |
| `concept-map` | notion | mindmap | 概念图、知识脉络 |
| `swot` | notion | quadrant | SWOT分析 |
| `tutorial` | chalkboard | flow | 教程步骤 |
| `study-guide` | study-notes | dense | 学习笔记 |

## 自动选择逻辑

| 内容信号 | 风格 | 布局 |
|---------|------|------|
| 知识、概念、效率、SaaS | `notion` | dense/list |
| 教育、教程、学习 | `chalkboard` | balanced/dense |
| 笔记、手写、学习指南 | `study-notes` | dense/list/mindmap |
| 美妆、时尚、可爱 | `cute` | sparse/balanced |
| 产品、对比、测评 | `fresh` | comparison |

## 工作流程

### Step 1: 内容分析

1. 保存源内容（如用户粘贴）
2. 深度分析内容类型（种草/干货/测评/教程/避坑）
3. 分析Hook（爆款标题潜力）
4. 确定目标受众
5. 评估互动潜力（收藏/分享/评论）

### Step 2: 智能确认

呈现自动推荐方案供用户确认：
- 策略风格
- 视觉风格
- 布局方式
- 图片数量

### Step 3: 生成图片

1. 首先生成封面图片（无参考）
2. 使用封面作为后续图片的参考（保持风格一致）
3. 逐张生成内容图片

### Step 4: 完成报告

```
小红书图片系列完成！

主题: [topic]
策略: [A/B/C]
风格: [style name]
布局: [layout name]
图片数量: N 张
```

## 文件结构

```
xhs-images/{topic-slug}/
├── source-{slug}.{ext}             # 源文件
├── analysis.md                     # 分析结果
├── outline.md                      # 最终大纲
├── prompts/
│   ├── 01-cover-[slug].md
│   └── ...
├── 01-cover-[slug].png
├── 02-content-[slug].png
└── ...
```

## 输出质量标准

- 封面：Hook + 视觉冲击 → sparse布局
- 内容：核心价值 per 图片 → balanced/dense/list/comparison/flow
- 结尾：CTA/总结 → sparse 或 balanced

## 避免事项

- ❌ 不要生成超过10张图片
- ❌ 不要跳过内容分析直接生成
- ❌ 不要忽略风格一致性（使用封面作为参考图）
