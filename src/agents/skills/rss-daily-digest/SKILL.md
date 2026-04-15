---
name: rss-daily-digest
description: RSS 每日新闻摘要 - 获取当日新闻，按优先级排序，分门别类汇总，提取重点信息
tags:
  - rss
  - digest
  - daily
  - summary
  - news
  - newsletter
roles:
  - rss_agent
  - assistant_agent
---

# RSS Daily Digest - 每日新闻摘要

## 何时使用

当用户需要**获取和总结当日新闻**时使用本技能：

| 用户意图 | 典型表达 |
|---------|---------|
| 今日新闻 | "今天有什么新闻"、"今日新闻" |
| 新闻摘要 | "给我一个新闻摘要"、"新闻汇总" |
| 领域新闻 | "AI今天发生了什么"、"医学新闻" |
| 定时简报 | "每天早间简报"、"新闻推送" |

**触发词**: 新闻、摘要、日报、汇总、今日、最近

## 工作流程

### 步骤 1：获取当日新闻

使用 `fetch_articles` 工具获取订阅的文章：

```python
# 获取最近文章
result = fetch_articles(
    limit=100,        # 最多返回100条
    fetch_new=True     # 是否先抓取新文章
)
```

### 步骤 2：优先级排序

文章已根据 `total_score` 排序，评分依据：

| 因素 | 权重 | 说明 |
|------|------|------|
| 时效性 | 40% | 最近发布的文章得分更高 |
| 权威性 | 30% | 学术期刊 > 行业媒体 > 个人博客 |
| 相关性 | 30% | 与用户领域/关键词的匹配度 |

### 步骤 3：分门别类

按来源/主题对文章分组：

```python
# 按 category 分组
grouped = {
    "学术前沿": [articles from arXiv, Nature, Science],
    "行业动态": [articles from TechCrunch, Wired],
    "社交讨论": [articles from Twitter, Reddit],
    "官方公告": [articles from FDA, WHO]
}
```

### 步骤 4：重点信息提取

从每篇文章提取：

```python
# 提取关键信息
key_info = {
    "title": "GPT-5 发布重大更新",
    "summary": "OpenAI 宣布 GPT-5 在推理能力上提升 40%...",
    "key_points": [
        "推理能力提升 40%",
        "支持多模态理解",
        "上下文窗口扩展至 10M tokens"
    ],
    "impact_level": "high",
    "source": "OpenAI Blog",
    "link": article["link"],
    "published": article["published"],
    "tags": article["tags"]
}
```

### 步骤 5：生成摘要报告

**输出格式**：

```markdown
# 📰 每日新闻简报

**日期**: 2026-04-07
**来源**: 15 个订阅源
**文章**: 50 篇

---

## 🔥 今日重点

### 1. GPT-5 发布重大更新
**来源**: OpenAI Blog | **评分**: 0.95
> OpenAI 宣布 GPT-5 在推理能力上提升 40%，支持多模态理解...

### 2. Nature 发表新型疫苗研究
**来源**: Nature | **评分**: 0.92
> 科学家开发出广谱新冠疫苗，有效性提升 3 倍...

---

## 📚 分类汇总

### 学术前沿 (15 篇)
| 来源 | 标题 | 评分 |
|------|------|------|
| arXiv | 新一代 Transformer 架构 | 0.89 |
| Nature | CRISPR 基因编辑新突破 | 0.87 |

### 行业动态 (20 篇)
| 来源 | 标题 | 评分 |
|------|------|------|
| TechCrunch | AI 创业投资回暖 | 0.85 |
| Wired | 量子计算新进展 | 0.83 |
```

## 优先级评分说明

### 评分公式

```
total_score = (
    recency_score * 0.4 +
    authority_score * 0.3 +
    relevance_score * 0.3
)
```

### 时效性评分

| 发布时间 | 评分 |
|----------|------|
| < 1 小时 | 1.0 |
| 1-6 小时 | 0.9 |
| 6-12 小时 | 0.8 |
| 12-24 小时 | 0.7 |
| > 24 小时 | 0.5 |

### 权威性评分

| 来源类型 | 评分 |
|----------|------|
| 顶级期刊 (Nature, Science) | 1.0 |
| 顶会 (NeurIPS, ICML) | 0.95 |
| 预印本 (arXiv) | 0.9 |
| 权威媒体 (WSJ, FT) | 0.85 |
| 行业媒体 (TechCrunch) | 0.8 |
| 社交媒体 (Twitter) | 0.6 |

### 相关性评分

基于用户领域和关键词匹配。

## 与其他 SKILL 的关系

| SKILL | 关系 | 说明 |
|-------|------|------|
| `professional-recommender` | 互补 | 负责推荐，digest 负责汇总 |
| `rss-hunter` | 依赖 | 发现和订阅新源 |

## 避免事项

- ❌ 不要返回过多文章（建议不超过 50 条）
- ❌ 不要忽略低分文章的补充价值
- ❌ 不要跳过 fetch 直接读取缓存
- ❌ 不要遗漏文章来源信息
