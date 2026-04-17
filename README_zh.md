<div align="center">

# EntroFeed

### AI 驱动的智能 RSS 阅读器

[![GitHub Stars](https://img.shields.io/github/stars/Moon84/EntroFeed_Reader?style=social)](https://github.com/Moon84/EntroFeed_Reader/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Moon84/EntroFeed_Reader?style=social)](https://github.com/Moon84/EntroFeed_Reader/network/members)
[![License](https://img.shields.io/github/license/Moon84/EntroFeed_Reader?color=green)](https://github.com/Moon84/EntroFeed_Reader/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.x-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ed.svg)](https://www.docker.com/)

![Logo](src/assets/EntroFeed_logo_w_name.png)

> **中文** | [English](README.md)

</div>

---

## 📖 简介

**EntroFeed（熵流）** 是一款开源免费的 AI RSS 阅读器，基于 **Entropy**（信息熵）以及 **Ontology**（本体论），利用大语言模型理解您的专业领域以及阅读偏好，利用 RSS 这种去中心化的阅读方式，构建信息获取的护城河。

## ✨ 功能特性

### 核心功能

| 功能 | 描述 |
|-----|------|
| 🔗 **个性化订阅** | RSS/Feed 订阅聚合，内容自动抓取，支持 RSS 和 RSShub 订阅 |
| 📊 **多维度评分** | 基于 Ontology 的文章评估（时效性、权威性、相关性、影响力） |
| 🔄 **持续进化** | 根据阅读习惯和事件相关性评估，持续优化评估标准 |
| 🌍 **多语言支持** | 完整的 i18n 支持，支持中文和英文 |

### AI 助手

- 内置 AI 对话功能，基于 **AntDesign X**
- 可对文章进行摘要、翻译、讨论
- 支持将文章作为附件发送给 AI 分析
- 多提供商支持：OpenAI、Ollama、DashScope

### 可扩展插件架构

| 插件类型 | 可选方案 |
|---------|---------|
| **大语言模型** | OpenAI, Ollama, DashScope |
| **内容获取** | requests, Playwright, RSShub |
| **存储方案** | SQLite + ChromaDB 向量库 |
| **通知提醒** | Slack, Ntfy |

### 用户界面

- 基于 **React** 和 **AntDesign** 的简洁现代 UI
- 响应式设计，固定高度布局优化滚动体验
- 支持深色/浅色主题

## 🚀 快速开始

### 前置要求

| 依赖 | 版本要求 |
|-----|---------|
| Node.js | 18+ |
| Python | 3.11+ |
| uv | 最新版 |
| Docker | 20.10+（可选）|

### Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd EntroFeed_Reader

# 使用默认配置启动
docker compose up

# 或先配置环境变量
export DEFAULT_LLM_PROVIDER=dashscope
export DASHSCOPE_API_KEY=your_api_key
docker compose up
```

> **访问地址**：在浏览器中打开 [http://localhost:8000](http://localhost:8000)

### 开发模式

```bash
# 安装所有依赖
make install

# 终端 1：启动后端 (FastAPI，端口 8001)
make dev-backend

# 终端 2：启动前端 (Vite，端口 5173)
make dev-frontend
```

> **访问地址**：在浏览器中打开 [http://localhost:5173](http://localhost:5173)

## ⚙️ 配置说明

### 环境变量

#### 大语言模型

| 变量名 | 说明 | 默认值 |
|-------|------|-------|
| `DEFAULT_LLM_PROVIDER` | 提供商：`openai`、`ollama`、`dashscope` | `dashscope` |
| `DASHSCOPE_API_KEY` | DashScope API 密钥 | - |
| `DASHSCOPE_MODEL` | DashScope 模型 | `qwen-plus` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | - |
| `OLLAMA_BASE_URL` | Ollama 服务器地址 | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | Ollama 模型 | `llama3` |

#### 通知

| 变量名 | 说明 |
|-------|------|
| `SLACK_API_TOKEN` | Slack Bot Token |
| `NTFY_BASE_URL` | Ntfy 服务器地址 |
| `NTFY_TOPIC` | Ntfy Topic 名称 |

#### 存储与订阅

| 变量名 | 说明 | 默认值 |
|-------|------|-------|
| `ENTROFEED_STORAGE_HANDLER` | 存储处理器类型 | `sqlite` |
| `DATA_DIR` | 数据目录路径 | `./data` |
| `CONFIG_DIR` | 配置目录路径 | `./configs` |
| `REFRESH_INTERVAL` | 订阅刷新间隔（分钟）| `5` |
| `RECENT_HOURS` | 视为"近期"条目的小时数 | `36` |

### 界面配置

处理器也可以通过网页界面在 **设置 → 处理器** 中配置。

| 处理器 | 必填字段 |
|-------|--------|
| **OpenAI** | `api_key` |
| **Ollama** | `base_url`, `model` |
| **DashScope** | `api_key`, `model` |
| **Slack** | `token` |
| **Ntfy** | `topic` |

## 🏗️ 项目结构

```
entrofeed/
├── src/                          # Python 后端 (FastAPI)
│   ├── app.py                    # 主应用和路由
│   ├── backend.py                # 业务逻辑层
│   ├── handlers.py               # 处理器基类
│   ├── mcp.py                    # MCP 服务器实现
│   ├── scheduler.py              # 订阅刷新调度器
│   ├── metrics.py                # Prometheus 指标
│   ├── plugins/                  # 插件实现
│   │   ├── llm/                  # LLM 提供商插件
│   │   ├── storage/              # 存储处理器插件
│   │   ├── notification/         # 通知插件
│   │   └── content/              # 内容获取插件
│   ├── services/                 # 业务服务
│   │   ├── feed/                 # 订阅聚合
│   │   ├── ontology/             # 知识库和标签
│   │   └── recommendation/       # 推荐引擎
│   └── storage/                  # 存储实现
├── frontend/                     # React 前端 (Vite)
│   └── src/
│       ├── components/           # React 组件
│       ├── pages/                # 页面组件
│       ├── hooks/                # 自定义 Hooks
│       ├── client-api/           # API 客户端
│       └── context/              # React Context
├── configs/                      # 配置文件
│   ├── feeds.yml                 # 默认 RSS 订阅源
│   ├── handlers.yml              # 处理器配置
│   └── user.md                   # 用户兴趣配置
├── tests/                        # 测试套件
│   ├── unit/                     # 单元测试
│   └── e2e/                      # 端到端测试
├── docker-compose.yml             # Docker 编排
├── Dockerfile                     # 多阶段 Docker 构建
└── Makefile                      # 开发命令
```

## 🛠️ 开发指南

### 可用命令

```bash
make install          # 安装所有依赖
make run              # 使用 uvicorn 运行后端
make dev-frontend     # 启动 Vite 开发服务器
make dev-backend      # 启动后端（热重载）
make build            # 构建 Docker 镜像
make docker-up        # 启动 Docker 容器
make docker-down       # 停止 Docker 容器
make unit-test        # 运行单元测试
make clean            # 清理数据目录
```

### 运行测试

```bash
# 单元测试
make unit-test

# 或手动运行
pytest -vvv -cov

# E2E 测试（需要先运行后端）
cd frontend && npx playwright test
```

## 📡 API 参考

### 工具接口

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/util/list-feeds` | GET | 获取所有订阅源列表 |
| `/util/feed-stats` | GET | 获取各订阅源统计信息 |
| `/util/list-feed-entries` | GET | 获取条目列表（支持过滤）|
| `/util/list-handlers` | GET | 获取已配置处理器列表 |

### 订阅管理

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/refresh_feed/{id}` | POST | 刷新指定订阅源 |
| `/api/delete_feed/{id}` | POST | 删除订阅源 |
| `/api/update_feed/` | POST | 创建/更新订阅源 |
| `/api/import_opml/` | POST | 导入 OPML 文件 |
| `/api/export_opml/` | GET | 导出 OPML |

### 设置

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/about` | GET | 获取设置和应用信息 |
| `/api/update_settings/` | POST | 更新设置 |
| `/api/backup/` | GET | 下载数据库备份 |
| `/api/restore/` | POST | 从备份恢复 |

### AI 与助手

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/agent/chat` | POST | 发送消息给 AI 助手 |
| `/api/agent/sessions` | GET/POST | 获取/创建对话会话 |
| `/api/agent/tools` | GET | 获取可用工具列表 |
| `/api/translate` | POST | 翻译文本 |
| `/api/llm/status` | GET | 获取 LLM 提供商状态 |
| `/api/llm/usage` | GET | 获取 Token 使用统计 |

### 搜索与推荐

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/search` | GET | 搜索条目 |
| `/api/recommendations/interest` | GET | 基于兴趣的推荐 |
| `/api/recommendations/trending` | GET | 热门条目 |
| `/api/recommendations/similar/{id}` | GET | 相似条目 |

## 🔌 MCP 服务器

EntroFeed 提供 **MCP (Model Context Protocol)** 服务器，用于外部 AI 系统集成。

```bash
# 启动 MCP 服务器
entrofeed mcp --port 8765

# 或使用 stdio 模式
entrofeed mcp --stdio
```

## 🤝 贡献

欢迎提交贡献！请随时提交 Pull Request。

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 **AGPL-3.0 许可证** - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [React](https://react.dev/) - UI 库
- [AntDesign](https://ant.design/) - 设计系统
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- 所有贡献者和用户

## 📬 联系方式

- **作者**：张寅磊 (Yinlei Zhang)
- **邮箱**：wuyuezhang1984@gmail.com
- **问题反馈**：[GitHub Issues](https://github.com/Moon84/EntroFeed_Reader/issues)

---

<div align="center">

*如果 EntroFeed 对您有帮助，请在 GitHub 上给我们一个 ⭐！*

</div>
