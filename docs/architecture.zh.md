# EntroFeed 架构文档

## 概述

EntroFeed 是一个智能 RSS 阅读器，将传统订阅聚合与 LLM 驱动的推荐相结合。架构采用模块化设计，关注点分离清晰。

## 系统组件

### 后端层 (FastAPI)

#### 核心组件

**app.py** - FastAPI 应用
- Web 服务器主入口
- 所有 API 端点的路由定义
- 启动/关闭的生命周期管理
- 前端资源的静态文件挂载

**backend.py** - EntroFeedBackend
- 核心业务逻辑处理
- 订阅源和条目管理
- 设置和处理器配置
- 健康检查和版本信息

**rss.py** - EntroFeedRSS
- 通过 feedparser 解析 RSS/Atom 订阅源
- 订阅源轮询和更新检查
- OPML 导入/导出
- 备份和恢复功能

#### 存储层

**storage/** - 存储处理器
- `sqlite_storage.py` - SQLite + ChromaDB 实现
- 添加新存储后端的接口

**存储接口要求:**
- `get_feeds()`, `upsert_feed()`, `delete_feed()`
- `get_entries()`, `get_feed_entry()`, `upsert_feed_entry()`
- `get_settings()`, `upsert_settings()`
- `get_handlers()`, `upsert_handler()`
- `get_poll_state()`, `set_poll_state()`, `update_poll_state()`

#### 推荐引擎

**recommender/** - 推荐系统
- `similar.py` - 基于内容的相似推荐
- `interest_based.py` - 基于用户兴趣的推荐
- `trending.py` - 热门内容推荐

**本体系统**
- `registry.py` - 本体注册中心
- `priority_scorer.py` - 文章优先级评分
- 追踪用户兴趣的记忆系统

#### Agent 系统

**agents/** - AI Agent 实现
- `entrofeed_agent.py` - 主 Agent 类（继承 ReActAgent）
- `tools.py` - Agent 操作的内置工具
- `skills_manager.py` - 技能加载和执行

**Agent 工具:**
- `list_feeds` - 列出所有订阅源
- `get_feed_entries` - 获取订阅源的条目
- `get_entry_content` - 获取条目的完整内容
- `search_entries` - 按查询搜索条目
- `get_user_interests` - 获取用户兴趣
- `add_user_interest` - 添加用户兴趣
- `get_daily_digest` - 生成每日摘要
- `translate_text` - 翻译内容

#### 处理器系统

**llm/** - LLM 处理器
- 统一接口，支持多种 LLM 提供商
- 支持 DashScope、Ollama、OpenAI
- `create_llm_handler()` 工厂函数

**notification/** - 通知处理器
- `ntfy.py` - ntfy.sh 通知
- `jira.py` - Jira 工单
- 通过 simplematrixbotlib 和 slack_sdk 支持 Matrix、Slack

**impls/** - 处理器注册
- `load_storage_config()` - 加载配置的存储处理器
- 内容检索、LLM、通知的处理器注册表

### 前端层 (React)

#### 页面

- `Dashboard.tsx` - 带统计信息的主仪表板
- `FeedList.tsx` - 订阅源管理
- `FeedEntries.tsx` - 订阅源的条目列表
- `ArticleReader.tsx` - 完整文章阅读视图
- `Recommendations.tsx` - 推荐标签页
- `Agent.tsx` - AI 助手聊天界面
- `Settings.tsx` - 全局设置
- `Onboarding.tsx` - 首次设置向导

#### 组件

- `Layout.tsx` - 带侧边栏导航的应用布局
- `EntryCard.tsx` - 订阅源条目卡片组件
- `FeedCard.tsx` - 订阅源卡片组件

#### 状态管理

- React Query 管理服务端状态
- React Router 管理导航
- i18n 用于国际化

### API 端点

#### 订阅源管理
- `GET /feeds/` - 列出所有订阅源
- `GET /feeds/{id}` - 获取订阅源配置
- `POST /api/update_feed/` - 创建/更新订阅源
- `GET /api/refresh_feed/{feed_id}` - 刷新单个订阅源
- `GET /api/delete_feed/{feed_id}` - 删除订阅源

#### 条目管理
- `GET /recent/` - 所有订阅源的最新条目
- `GET /list-entries/{feed_id}` - 特定订阅源的条目
- `GET /read/{feed_entry_id}` - 条目完整内容

#### 推荐
- `GET /api/recommendations/interest` - 基于兴趣的推荐
- `GET /api/recommendations/trending` - 热门推荐
- `GET /api/recommendations/similar/{entry_id}` - 相似条目

#### 用户兴趣
- `GET /api/interests` - 列出用户兴趣
- `POST /api/interests` - 添加新兴趣
- `DELETE /api/interests/{interest_id}` - 移除兴趣
- `PATCH /api/interests/{interest_id}` - 更新兴趣优先级

#### 设置
- `GET /settings/` - 设置页面
- `POST /api/update_settings/` - 更新设置

#### 备份/恢复
- `GET /api/export_opml/` - 导出订阅源为 OPML
- `GET /api/backup/` - 完整 JSON 备份
- `POST /api/restore/` - 从备份恢复
- `POST /api/import_opml/` - 导入 OPML

#### Agent 聊天
- `POST /api/agent/chat` - 向 Agent 发送消息（带会话上下文）
- `GET /api/agent/sessions` - 列出所有聊天会话
- `POST /api/agent/sessions` - 创建新聊天会话
- `GET /api/agent/sessions/{id}` - 获取会话及消息历史
- `DELETE /api/agent/sessions/{id}` - 删除聊天会话
- `POST /api/agent/sessions/{id}/clear` - 清除会话消息

#### 翻译
- `POST /api/translate` - 使用 LLM 翻译文本

#### LLM 状态
- `GET /api/llm/status` - 检查 LLM 提供商连接和模型信息
- `GET /api/llm/usage` - 获取今日 token 使用统计

#### 条目状态同步
- `PATCH /api/entries/{entry_id}` - 更新条目已读/点赞/收藏状态

## 数据模型

### Feed
```python
class Feed(BaseModel):
    id: str
    name: str
    url: str
    category: str
    preview_only: bool = False
    notify: bool = False
    refresh_enabled: bool = False
    use_script: bool = False
    retrieve_content: bool = False
```

### FeedEntry
```python
class FeedEntry(BaseModel):
    id: str
    feed_id: str
    title: str
    url: str
    published_at: int
    updated_at: int
    preview: Optional[str]
    content: Optional[str]
    authors: Optional[List[str]]
    total_score: Optional[float]
    recency_score: Optional[float]
    authority_score: Optional[float]
    relevance_score: Optional[float]
    impact_score: Optional[float]
    tags: Optional[List[Tag]]
    matched_interests: Optional[List[str]]
    has_ontology_match: Optional[bool]
    # 状态字段（后续添加）
    is_read: bool = False
    liked: int = 0  # -1, 0, 1
    is_favorite: bool = False
    read_at: Optional[int] = None
```

### GlobalSettings
```python
class GlobalSettings(BaseModel):
    send_notification: bool
    theme: str
    refresh_interval: int
    reading_speed: int
    notification_handler_key: Optional[str]
    llm_handler_key: Optional[str]
    content_retrieval_handler_key: Optional[str]
    recent_hours: int
    finished_onboarding: bool
```

### ChatSession
```python
class ChatSession(BaseModel):
    id: str
    title: str
    messages: List[ChatMessage]
    created_at: int
    updated_at: int

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: int
```

### LLMUsage
```python
class LLMUsage(BaseModel):
    date: str  # YYYY-MM-DD
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    request_count: int
```

## 存储架构

### SQLite 表

**feeds**
- id (TEXT PRIMARY KEY)
- name, url, category, type
- preview_only, notify, refresh_enabled, use_script, retrieve_content
- notify_destination
- poll_state (JSON)

**entries**
- id (TEXT PRIMARY KEY)
- feed_id (TEXT FOREIGN KEY)
- title, url, preview, content, authors (JSON)
- published_at, updated_at
- total_score, recency_score, authority_score, relevance_score, impact_score
- tags (JSON), matched_interests (JSON), has_ontology_match
- is_read, liked, is_favorite, read_at (状态字段)

**entry_content**
- id (TEXT PRIMARY KEY)
- feed_id (TEXT FOREIGN KEY)
- content, summary, byline
- word_count, reading_time, reading_level
- unretrievable, banned

**handlers**
- id (TEXT PRIMARY KEY)
- type (handler_type enum)
- config (JSON)

**settings**
- 单行存储所有设置为 JSON

### ChromaDB 集合

**content_embeddings**
- id: entry_id
- embedding: 文章内容向量
- document: 标题 + 内容文本

## 推荐算法

### 相似内容（向量搜索）
1. 获取当前条目的内容
2. 生成查询向量
3. 在 ChromaDB 中搜索相似条目
4. 按最小相似度阈值过滤
5. 按相似度排序

### 基于兴趣的推荐
1. 获取用户显式和推断的兴趣
2. 对所有最新条目按兴趣评分
3. 按兴趣优先级和匹配置信度加权
4. 返回按综合评分排序的前 N 个条目

### 热门推荐
1. 聚合过去 24-48 小时的条目
2. 统计跨订阅源的提及次数
3. 应用时间衰减权重
4. 考虑权威度评分
5. 返回热门条目

## 扩展点

### 添加新的 LLM 处理器
1. 在 `app/llm/` 创建新文件
2. 实现带 `get_content()` 和 `summarize()` 方法的处理器类
3. 在 `app/impls.py` 注册
4. 添加配置 schema

### 添加新的存储后端
1. 实现存储接口的所有方法
2. 在 `load_storage_config()` 注册
3. 确保与 ChromaDB 向量兼容

### 添加新的通知处理器
1. 在 `app/notification/` 创建新文件
2. 实现 `send_notification(feed, entry)` 方法
3. 在处理器注册表注册

## 安全注意事项

- API 密钥存储在配置中，不在代码中
- 备份包含敏感信息，需妥善保管
- User Agent 用于识别应用身份
- 禁用域名列表防止抓取被封禁的网站
