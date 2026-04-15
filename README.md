# EntroFeed - Intelligent Feed Reader

> 中文：[切换到中文](README_zh.md)

![EntroFeed Logo](src/assets/EntroFeed_logo_w_name.png)

EntroFeed (熵流) is an open-source, AI-powered RSS reader that leverages Entropy (information theory) and Ontology (knowledge structures) with Large Language Models to understand your professional domains and reading preferences. It helps you build an effective information moat through decentralized RSS feeds.

## Features

### Core Functionality
- **Personalized Subscription**: RSS/Feed aggregation with automatic content fetching; supports RSS and RSShub feeds
- **Multi-dimensional Scoring**: Ontology-based article evaluation (recency, authority, relevance, impact) to improve effective information acquisition
- **Continuous Evolution**: Continuously refine evaluation criteria based on your reading habits and event correlations
- **Multi-language Support (i18n)**: Currently supports Chinese and English

### Extensible Architecture
EntroFeed supports modular handlers:
1. **Large Language Models** - Ollama, OpenAI, DashScope - for summarization and content analysis
2. **Content Retrieval** - requests or Playwright for fetching article content
3. **Storage** - SQLite + ChromaDB vector store (production), or file-based storage
4. **Notifications (Coming Soon)** - Matrix, Slack, Jira, ntfy - for new article alerts

### User-Friendly Interface
- Clean, modern UI built with React and Tailwind CSS
- Responsive design with AntDesign components

## Quick Start

### Development Mode

**Prerequisites**: Node.js 18+, Python 3.11+, uv (Python package manager)

```bash
# Terminal 1: Start backend (FastAPI on port 8001)
make dev:backend

# Terminal 2: Start frontend (Vite on port 5173)
make dev:frontend

# Or install all dependencies at once
make install
make dev
```

Visit `http://localhost:5173` to access the application.

### Using Docker Compose

```bash
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd entrofeed
docker compose up
```

Visit `http://localhost:8000` to access the application.

## Project Structure

```
entrofeed/
├── src/                    # Python backend (FastAPI)
│   ├── app.py              # Main application & routes
│   ├── backend.py          # Business logic layer
│   ├── static/              # Static assets (icons, CSS)
│   ├── assets/             # Images (logos)
│   ├── agents/             # AI agent & skills
│   ├── content/            # Content retrieval (RSS, Playwright)
│   ├── llm/                # LLM interfaces
│   ├── ontology/           # Knowledge base & tagging
│   ├── recommender/        # Recommendation engine
│   └── storage/            # Data persistence
├── frontend/               # React frontend (Vite)
│   └── src/                # React source code
│       ├── api/            # API client hooks
│       ├── components/    # React components
│       ├── pages/          # Page components
│       └── hooks/          # Custom React hooks
├── templates/              # Jinja2 templates (legacy)
├── configs/                # Configuration files
│   ├── feeds.yml           # Default RSS feeds
│   ├── handlers.yml.example # Handler config template
│   └── digital_medical_feeds.opml
└── data/                   # Runtime data (gitignored)
    ├── db.json             # SQLite database
    ├── chroma/             # Vector database
    └── ontology.db         # Knowledge base
```

## First-Time Setup

### LLM Configuration

Configure LLM, notification, and content retrieval handlers via YAML files in `configs/`.

## CLI Usage

```bash
# Backup and restore
entrofeed backup
entrofeed restore backup_file.json

# OPML import/export
entrofeed export-opml
entrofeed import-opml feeds.opml

# Load configurations
entrofeed load-settings
entrofeed load-handlers
entrofeed load-feeds

# Check for new articles
entrofeed check-feeds

# Start MCP server for external AI integration
entrofeed mcp --port 8765
```

## MCP Server (External AI Integration)

EntroFeed provides a **Model Context Protocol (MCP)** server that exposes its tools to external AI systems. This allows AI assistants to query your feed data, get recommendations, and manage interests.

### Starting the MCP Server

```bash
# TCP mode (default) - AI clients connect via TCP
entrofeed mcp --port 8765 --host 127.0.0.1

# Stdio mode - for subprocess-based AI integration
entrofeed mcp --stdio
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `list_feeds` | List all configured RSS feeds |
| `get_feed_entries` | Get entries from a specific feed or recent entries |
| `get_entry_content` | Get full content of a feed entry |
| `search_entries` | Search entries by query |
| `get_recommendations` | Get content recommendations (interest/trending/similar) |
| `get_user_interests` | Get user interests |
| `add_user_interest` | Add a new user interest |
| `remove_user_interest` | Remove a user interest |

#### MCP Usage Examples: Claude Desktop Integration

Add to your Claude Desktop configuration (`~/.claude/desktop-config.json`):

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

Then you can ask Claude:
- "What are my latest articles about AI?"
- "Show me trending content in my feed"
- "Add machine learning to my interests"
- "Find articles similar to [article title]"

### Security Note

The TCP MCP server binds to `127.0.0.1` by default. For production deployments, consider:
- Using `--stdio` mode with a process manager
- Adding authentication to the connection
- Using a reverse proxy with TLS

## License

AGPL 3.0 License

## Links

- Contact Email: wuyuezhang1984@gmail.com
- Location: Shanghai, Hongkou District
- Documentation: [docs/](docs/)
- Docker Deployment Guide: [docs/docker.zh.md](docs/docker.zh.md)
- Issue Tracker: [GitHub Issues](https://github.com/Moon84/EntroFeed_Reader/issues)
