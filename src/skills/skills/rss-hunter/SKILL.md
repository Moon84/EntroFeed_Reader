---
name: rss-hunter
description: RSS 追踪猎人 - 追踪用户指定的具体内容（网站、UP主、期刊、博主等），发现并订阅 RSS 源
tags:
  - rss
  - hunt
  - discover
  - track
  - subscription
roles:
  - rss_agent
  - assistant_agent
---

# RSS Hunter - RSS 追踪猎人

## 何时使用

当用户需要**追踪特定内容源**时使用本技能：

| 用户意图 | 典型表达 |
|---------|---------|
| 追踪网站 | "订阅某网站"、"追踪某博客" |
| 追踪UP主 | "订阅B站UP主"、"关注某YouTube频道" |
| 追踪期刊 | "订阅某期刊"、"追踪某杂志" |
| 追踪博主 | "订阅某博主"、"关注某专家" |
| 发现RSS | "有没有某网站的RSS"、"能订阅吗" |
| 验证源 | "验证这个RSS是否可用" |

**触发词**: 订阅、追踪、关注、发现、查找、验证、RSS

## 追踪流程

### 步骤 1：理解用户目标

解析用户输入，提取：
- **目标实体**：网站名、UP主名、期刊名、博主名
- **平台类型**：B站、YouTube、Twitter、公众号、博客
- **用户意图**：发现、订阅、验证

```
用户: "订阅B站老高与小茉"
  → 目标实体: "老高与小茉"
  → 平台类型: "bilibili"
  → 用户意图: "订阅"
```

### 步骤 2：Capability 查询

使用 `query_capabilities` 搜索匹配的网站能力：

```
query_capabilities("bilibili")
query_capabilities("youtube")
query_capabilities("twitter")
```

### 步骤 3：根据类型处理

#### 3.1 网站/博客（direct/rsshub）

```python
# 1. 查询 capability
cap = get_capability("example.com")

# 2. 根据 subscription_method 处理
if method == "direct":
    # 直接使用 direct_url
    rss_url = cap["rss_config"]["direct_url"]

elif method == "rsshub":
    # 生成 RSSHub URL
    rss_url = f"http://localhost:1200{rsshub_route}"
```

#### 3.2 社交媒体（B站/YouTube/Twitter）

使用 `rss_subscribe_with_platform`：

```python
# B站 UP主
result = rss_subscribe_with_platform("B站 老高与小茉")

# YouTube 频道
result = rss_subscribe_with_platform("YouTube Two Minute Papers")

# Twitter 用户
result = rss_subscribe_with_platform("Twitter elonmusk")
```

#### 3.3 学术期刊/数据库

使用 `discover_feeds` 或 `manual_rss_generator`：

```python
# 发现 RSS
feeds = discover_feeds("https://www.nature.com")
```

### 步骤 4：Discovery（无可用 capability 时）

当 capability 中没有匹配时：

```python
# 1. 尝试常见 RSS 路径
feeds = discover_feeds("https://example.com")

# 2. 尝试 sitemap
feeds = discover_feeds("https://example.com", try_sitemap=True)

# 3. 搜索权威替代源
result = web_search("example.com 官方 RSS 订阅")
```

### 步骤 5：验证与输出

```python
# 验证 RSS URL
async def verify_rss(rss_url: str) -> bool:
    try:
        response = await httpx.get(rss_url, timeout=10)
        return response.status_code == 200
    except:
        return False
```

## Capability 类型处理

| 类型 | 处理方式 | 工具 |
|------|----------|------|
| `direct` | 直接使用 direct_url | 无需额外工具 |
| `rsshub` | 生成 RSSHub URL | PlatformRouter |
| `direct-w-skill` | 按需 ReAct | manual_rss_generator |
| `manual-crawl` | 配置爬取 | crawler |
| `manual` | ReAct 构建 | manual_rss_generator |

## 平台支持

### 社交媒体

| 平台 | 示例 | 路由 |
|------|------|------|
| B站 | 老高与小茉 | `/bilibili/user/video/{id}` |
| YouTube | Two Minute Papers | `/youtube/channel/{id}` |
| Twitter | elonmusk | `/twitter/user/{id}` |
| 微博 | 人民日报 | `/weibo/user/{id}` |
| 知乎 | 李永乐 | `/zhihu/people/{id}` |

### 学术期刊

| 期刊 | 订阅方式 | URL 格式 |
|------|----------|----------|
| medRxiv | direct-w-skill | `subject={学科}` |
| CNKI | manual-crawl | crawler 爬取 |
| PubMed | direct | 官方 RSS |

## 与其他 SKILL 的关系

| SKILL | 关系 | 说明 |
|-------|------|------|
| `professional-recommender` | 互补 | professional-recommender 按领域推荐，rss-hunter 按实体追踪 |
| `rss-daily-digest` | 依赖 | digest 汇总已订阅的内容 |

## 避免事项

- ❌ 不要订阅未验证的 RSS URL
- ❌ 不要假设所有网站都有 RSS
- ❌ 不要忽略 social media 平台的 RSSHub 配置
- ❌ 不要跳过 capability 查询直接 discover
