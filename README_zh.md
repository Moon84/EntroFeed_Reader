# EntroFeed - 智能 RSS 阅读器

> English: [切换到 English](README.md)

![EntroFeed Logo](src/assets/EntroFeed_logo_w_name.png)

EntroFeed（熵流）是一款开源免费的AI RSS 阅读器，希望基于Entropy（信息熵）以及Ontology（本体论），利用大语言模型理解您的专业领域以及相关知识偏好，利用RSS这种去中心化的阅读方式，构建信息获取的护城河。

## 功能特性

### 核心功能
- 个性化订阅：RSS/Feed 订阅聚合，内容自动抓取，支持RSS以及RSShub订阅；
- 个性化评估：基于Ontology的多维度文章评分（时效性、权威性、相关性、影响力），提高有效信息的获取效率
- 持续进化：根据阅读的习惯以及事件相关性的评估，持续进化评估标准，让阅读更有效。
- 多语言支持（i18n）：目前支持中文和英文；

### 可扩展架构
EntroFeed 支持模块化处理器：
1. **大语言模型** - Ollama、OpenAI、DashScope - 用于摘要和内容分析
2. **内容获取** - requests 或 Playwright 获取文章内容
3. **存储方案** - SQLite + ChromaDB 向量库（生产环境），或文件存储
4. **通知提醒（待实现）** - Matrix、Slack、Jira、ntfy - 新文章推送


### 用户友好界面
- 基于 React 和 Tailwind CSS 的简洁现代 UI
- 响应式设计，AntDesign组件


## 快速开始

### Docker Compose 部署

```bash
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd entrofeed
docker compose up
```

访问 `http://localhost:8000` 即可使用。

## 首次使用

### LLM配置
通过 YAML 文件配置大语言模型、通知和内容获取处理器：


## 命令行工具

```bash
# 备份与恢复
entrofeed backup
entrofeed restore backup_file.json

# OPML 导入导出
entrofeed export-opml
entrofeed import-opml feeds.opml

# 加载配置
entrofeed load-settings
entrofeed load-handlers
entrofeed load-feeds

# 检查新文章
entrofeed check-feeds

# 启动 MCP 服务器，供外部 AI 系统集成
entrofeed mcp --port 8765
```

## MCP 服务器（外部 AI 集成）

EntroFeed 提供了一个 **MCP (Model Context Protocol)** 服务器，将其工具暴露给外部 AI 系统。这允许 AI 助手查询您的订阅数据、获取推荐和管理兴趣。

### 启动 MCP 服务器

```bash
# TCP 模式（默认）- AI 客户端通过 TCP 连接
entrofeed mcp --port 8765 --host 127.0.0.1

# Stdio 模式 - 用于基于子进程的 AI 集成
entrofeed mcp --stdio
```

### 可用的 MCP 工具

| 工具 | 说明 |
|------|------|
| `list_feeds` | 列出所有配置的 RSS 订阅源 |
| `get_feed_entries` | 获取特定订阅源或最新条目 |
| `get_entry_content` | 获取条目的完整内容 |
| `search_entries` | 按关键词搜索条目 |
| `get_recommendations` | 获取内容推荐（兴趣/热门/相似） |
| `get_user_interests` | 获取用户兴趣 |
| `add_user_interest` | 添加新用户兴趣 |
| `remove_user_interest` | 删除用户兴趣 |


#### MCP 使用示例：Claude Desktop 集成

添加到 Claude Desktop 配置文件（`~/.claude/desktop-config.json`）：

```json
{
  "mcpServers": {
    "entrofeed": {
      "command": "entrofeed",
      "args": ["mcp", "--stdio"]
    }
  }
}
```

然后您可以问 Claude：
- "我有哪些关于 AI 的最新文章？"
- "显示我订阅源中的热门内容"
- "把机器学习添加到我的兴趣"
- "找与 [文章标题] 相似的文章"


### 安全说明

TCP MCP 服务器默认绑定到 `127.0.0.1`。对于生产部署，请考虑：
- 使用 `--stdio` 模式配合进程管理器
- 添加连接身份验证
- 使用带 TLS 的反向代理

## 许可证

AGPL3.0 许可证

## 相关链接

- Contact_Email:wuyuezhang1984@gmail.com
- InTheCity: 上海，虹口
- [文档](docs/)
- [Docker 部署指南](docs/docker.md)
- [问题反馈](https://github.com/Moon84/EntroFeed_Reader/issues)
