---
name: professional-recommender
description: 专业领域 RSS 推荐，根据用户的专业领域需求推荐权威、第一手的 RSS 订阅源（学术期刊/会议/机构/专家/KOL）
tags:
  - rss feed
  - recommendation
  - professional
  - academic tracing
roles:
  - rss_agent
---

# 专业 RSS 推荐助手 (Professional RSS Recommender)

## 何时使用

当用户需要**专业领域 RSS 推荐**时使用本技能：

| 用户意图 | 典型表达 |
|---------|---------|
| 专业推荐 | "推荐 RSS"、"推荐订阅源"、"有什么 RSS" |
| 权威订阅 | "专业订阅"、"权威信息源"、"前沿资讯" |
| 领域订阅 | "AI 领域订阅"、"医学 RSS"、"金融信息源" |
| 订阅方案 | "怎么订阅 XX"、"XX 领域有哪些源" |

**触发词**: 推荐、专业、权威、前沿、第一手、领域、订阅方案

## 推荐流程

### 步骤 1：分析用户需求

1. **理解领域**：从用户输入提取专业领域关键词
   - "AI" → "人工智能"、"机器学习"、"大模型"
   - "医学" → "医学研究"、"生物医学"、"临床试验"
   - "金融" → "金融经济"、"投资"、"市场"

2. **确定推荐级别**：
   - `tier1`：顶级学术源（预印本、期刊、顶会）
   - `industry`：行业权威源（官方机构、权威媒体）
   - `social`：专家/KOL 社交媒体
   - `all`：全部

### 步骤 2：Capability 搜索

使用 `query_capabilities` 工具搜索已知匹配的网站能力：

```
query_capabilities("AI")  # 搜索 AI 领域
query_capabilities("医学")  # 搜索医学领域
```

**Capability 类型分类**：

| 类型 | 说明 | 处理方式 |
|------|------|----------|
| `direct` | 有直接可用的 RSS URL | ✅ 直接推荐 |
| `direct-w-skill` | 有 RSS URL，需 skills 精细化订阅 | ✅ 生成 RSS URL + skill 辅助 |
| `rsshub` | 有 RSSHub 路由 | ✅ 生成 RSSHub URL 推荐 |
| `manual-crawl` | 无 RSS，需用 crawler 爬取 | ⚠️ 配置 crawler 定时任务 |
| `discovery` | 需要自动发现 RSS 源 | ⚠️ 使用 discover_feeds 发现 |
| `manual` | 需要通过 skills + ReAct 构建 | ⚠️ LLM 补充或手动配置 |

### 步骤 3：RSS 源发现

对于 `manual` 类型或 Capability 不足的情况：

1. **使用 discover_feeds**：
   ```
   discover_feeds("https://example.com")  # 发现网站的 RSS
   ```

2. **使用 web_search**（当 discover_feeds 不足时）：
   ```
   web_search("AI 领域权威 RSS 订阅源 arxiv google deepmind")
   ```

### 步骤 4：融合预配置数据

内置推荐数据（按领域）：

```json
{
  "artificial_intelligence": {
    "name": "人工智能",
    "tier1_sources": [
      {"name": "arXiv AI", "rss_url": "https://rss.arxiv.org/rss/cs.AI"},
      {"name": "arXiv CL (NLP)", "rss_url": "https://rss.arxiv.org/rss/cs.CL"}
    ],
    "industry_sources": [
      {"name": "OpenAI Blog", "rsshub": "/openai/blog"}
    ]
  }
}
```

### 步骤 5：验证与输出

**验证**：
- direct 类型：验证 RSS URL 可访问
- rsshub 类型：确保 RSSHub 服务可用
- discovered 类型：调用 `discover_feeds` 验证

**输出格式选项**：

#### 格式 A：OPML 格式（推荐用于 RSS 阅读器导入）

#### 格式 B：Markdown 格式（推荐用于阅读和分享）

```markdown
## AI 领域 RSS 订阅推荐

### Tier-1 顶级学术源

| 名称 | RSS URL | 说明 |
|------|---------|------|
| arXiv AI | https://rss.arxiv.org/rss/cs.AI | 人工智能预印本 |
| arXiv CL | https://rss.arxiv.org/rss/cs.CL | 自然语言处理 |

### 行业权威源

| 名称 | RSS URL | 说明 |
|------|---------|------|
| OpenAI Blog | http://localhost:1200/openai/blog | OpenAI 官方博客 |
```

## 推荐原则

### 1. 分级推荐策略

| 等级 | 来源类型 | 说明 |
|-----|---------|------|
| **Tier1** | 预印本/期刊/会议 | 顶级学术来源，必须订阅 |
| **Priority** | 官方机构/监管 | 高优先级官方信息 |
| **Optional** | 行业媒体/专家 | 按需补充订阅 |

### 2. 第一手信息优先

推荐顺序：`预印本 > 顶级期刊/会议 > 官方机构 > 权威媒体 > 专家博客`

### 3. 领域匹配策略

- 支持领域别名映射（如 "AI" → "人工智能"）
- 支持关键词匹配（如 "机器学习" → "人工智能"）
- 支持子串匹配

## 与其他 SKILL 的关系

| SKILL | 关系 | 说明 |
|-------|------|------|
| `rss-daily-digest` | 依赖 | digest 汇总已订阅的内容 |
| `rss-hunter` | 互补 | rss-hunter 按实体追踪，recommender 按领域推荐 |

## 避免事项

- ❌ 不要推荐未验证的 RSS URL
- ❌ 不要忽略 `manual` 类型网站的 discover_feeds 处理
- ❌ 不要跳过预配置数据的融合
