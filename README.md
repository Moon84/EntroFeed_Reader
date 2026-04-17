<div align="center">

# EntroFeed

### Intelligent Feed Reader powered by AI

[![GitHub Stars](https://img.shields.io/github/stars/Moon84/EntroFeed_Reader?style=social)](https://github.com/Moon84/EntroFeed_Reader/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/Moon84/EntroFeed_Reader?style=social)](https://github.com/Moon84/EntroFeed_Reader/network/members)
[![License](https://img.shields.io/github/license/Moon84/EntroFeed_Reader?color=green)](https://github.com/Moon84/EntroFeed_Reader/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18.x-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ed.svg)](https://www.docker.com/)

![Logo](src/assets/EntroFeed_logo_w_name.png)

> **English** | [中文](README_zh.md)

</div>

---

## 📖 Overview

**EntroFeed (熵流)** is an open-source, AI-powered RSS reader that leverages **Entropy** (information theory) and **Ontology** (knowledge structures) with Large Language Models to understand your professional domains and reading preferences. It helps you build an effective information moat through decentralized RSS feeds.

## ✨ Features

### Core Functionality

| Feature | Description |
|---------|-------------|
| 🔗 **Personalized Subscription** | RSS/Feed aggregation with automatic content fetching; supports RSS and RSShub feeds |
| 📊 **Multi-dimensional Scoring** | Ontology-based article evaluation (recency, authority, relevance, impact) |
| 🔄 **Continuous Evolution** | Refine evaluation criteria based on your reading habits and event correlations |
| 🌍 **Multi-language Support** | Full i18n support for Chinese and English |

### AI Assistant

- Built-in AI chat powered by **AntDesign X**
- Summarize, translate, and discuss articles with context
- Attach articles to conversations for deep analysis
- Multi-provider support: OpenAI, Ollama, DashScope

### Extensible Plugin Architecture

| Plugin Type | Options |
|-------------|---------|
| **LLM Providers** | OpenAI, Ollama, DashScope |
| **Content Retrieval** | requests, Playwright, RSShub |
| **Storage** | SQLite + ChromaDB vector store |
| **Notifications** | Slack, Ntfy |

### User Interface

- Clean, modern UI built with **React** and **AntDesign**
- Responsive design with fixed-height layouts
- Dark/Light theme support

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Node.js | 18+ |
| Python | 3.11+ |
| uv | Latest |
| Docker | 20.10+ (optional) |

### Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd EntroFeed_Reader

# Start with default configuration
docker compose up

# Or configure environment variables first
export DEFAULT_LLM_PROVIDER=dashscope
export DASHSCOPE_API_KEY=your_api_key
docker compose up
```

> **Access**: Open [http://localhost:8000](http://localhost:8000) in your browser.

### Development Mode

```bash
# Install dependencies
make install

# Terminal 1: Start backend (FastAPI on port 8001)
make dev-backend

# Terminal 2: Start frontend (Vite on port 5173)
make dev-frontend
```

> **Access**: Open [http://localhost:5173](http://localhost:5173) in your browser.

## ⚙️ Configuration

### Environment Variables

#### LLM Providers

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_LLM_PROVIDER` | Provider: `openai`, `ollama`, `dashscope` | `dashscope` |
| `DASHSCOPE_API_KEY` | DashScope API key | - |
| `DASHSCOPE_MODEL` | DashScope model | `qwen-plus` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | Ollama model | `llama3` |

#### Notifications

| Variable | Description |
|----------|-------------|
| `SLACK_API_TOKEN` | Slack bot token |
| `NTFY_BASE_URL` | Ntfy server URL |
| `NTFY_TOPIC` | Ntfy topic name |

#### Storage & Feeds

| Variable | Description | Default |
|----------|-------------|---------|
| `ENTROFEED_STORAGE_HANDLER` | Storage handler type | `sqlite` |
| `DATA_DIR` | Data directory path | `./data` |
| `CONFIG_DIR` | Config directory path | `./configs` |
| `REFRESH_INTERVAL` | Feed refresh interval (minutes) | `5` |
| `RECENT_HOURS` | Hours for "recent" entries | `36` |

### UI Configuration

Handlers can also be configured through the web UI at **Settings → Handlers**.

| Handler | Required Fields |
|---------|----------------|
| **OpenAI** | `api_key` |
| **Ollama** | `base_url`, `model` |
| **DashScope** | `api_key`, `model` |
| **Slack** | `token` |
| **Ntfy** | `topic` |

## 🏗️ Project Structure

```
entrofeed/
├── src/                          # Python backend (FastAPI)
│   ├── app.py                    # Main application & routes
│   ├── backend.py                # Business logic layer
│   ├── handlers.py               # Handler base classes
│   ├── mcp.py                    # MCP server implementation
│   ├── scheduler.py              # Feed refresh scheduler
│   ├── metrics.py                # Prometheus metrics
│   ├── plugins/                  # Plugin implementations
│   │   ├── llm/                  # LLM provider plugins
│   │   ├── storage/              # Storage handler plugins
│   │   ├── notification/         # Notification plugins
│   │   └── content/              # Content retrieval plugins
│   ├── services/                 # Business services
│   │   ├── feed/                 # Feed aggregation
│   │   ├── ontology/             # Knowledge base & tagging
│   │   └── recommendation/       # Recommendation engine
│   └── storage/                  # Storage implementations
├── frontend/                     # React frontend (Vite)
│   └── src/
│       ├── components/           # React components
│       ├── pages/                # Page components
│       ├── hooks/                # Custom React hooks
│       ├── client-api/           # API client functions
│       └── context/              # React context providers
├── configs/                      # Configuration files
│   ├── feeds.yml                 # Default RSS feeds
│   ├── handlers.yml              # Handler configurations
│   └── user.md                   # User profile/interests
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   └── e2e/                      # End-to-end tests
├── docker-compose.yml             # Docker composition
├── Dockerfile                     # Multi-stage Docker build
└── Makefile                      # Development commands
```

## 🛠️ Development

### Available Commands

```bash
make install          # Install all dependencies
make run              # Run backend with uvicorn
make dev-frontend     # Start Vite dev server
make dev-backend      # Start backend with auto-reload
make build            # Build Docker images
make docker-up        # Start Docker containers
make docker-down      # Stop Docker containers
make unit-test        # Run pytest
make clean            # Clean data directory
```

### Running Tests

```bash
# Unit tests
make unit-test

# Or manually
pytest -vvv -cov

# E2E tests (requires running backend)
cd frontend && npx playwright test
```

## 📡 API Reference

### Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/util/list-feeds` | GET | List all configured feeds |
| `/util/feed-stats` | GET | Get statistics per feed |
| `/util/list-feed-entries` | GET | List entries (supports filtering) |
| `/util/list-handlers` | GET | List configured handlers |

### Feed Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/refresh_feed/{id}` | POST | Refresh a specific feed |
| `/api/delete_feed/{id}` | POST | Delete a feed |
| `/api/update_feed/` | POST | Create/update feed |
| `/api/import_opml/` | POST | Import OPML file |
| `/api/export_opml/` | GET | Export feeds as OPML |

### Settings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/about` | GET | Get settings & app info |
| `/api/update_settings/` | POST | Update settings |
| `/api/backup/` | GET | Download database backup |
| `/api/restore/` | POST | Restore from backup |

### AI & Agent

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agent/chat` | POST | Send message to AI assistant |
| `/api/agent/sessions` | GET/POST | List/create chat sessions |
| `/api/agent/tools` | GET | List available agent tools |
| `/api/translate` | POST | Translate text |
| `/api/llm/status` | GET | Get LLM provider status |
| `/api/llm/usage` | GET | Get token usage stats |

### Search & Recommendations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET | Search entries |
| `/api/recommendations/interest` | GET | Interest-based recommendations |
| `/api/recommendations/trending` | GET | Trending entries |
| `/api/recommendations/similar/{id}` | GET | Similar entries |

## 🔌 MCP Server

EntroFeed provides a **Model Context Protocol (MCP)** server for external AI integration.

```bash
# Start MCP server
entrofeed mcp --port 8765

# Or in stdio mode
entrofeed mcp --stdio
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the **AGPL-3.0 License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - UI library
- [AntDesign](https://ant.design/) - Design system
- [ChromaDB](https://www.trychroma.com/) - Vector database
- All our contributors and users

## 📬 Contact

- **Author**: Yinlei Zhang
- **Email**: wuyuezhang1984@gmail.com
- **Issues**: [GitHub Issues](https://github.com/Moon84/EntroFeed_Reader/issues)

---

<div align="center">

*If you find EntroFeed helpful, please give us a ⭐ on GitHub!*

</div>
