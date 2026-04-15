# Docker Deployment Guide

## Quick Start

```bash
# 1. Clone the project
git clone https://github.com/entrofeed/entrofeed.git
cd entrofeed

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your API keys (at minimum DASHSCOPE_API_KEY is required)

# 3. Start
docker-compose up -d
```

Access http://localhost:8000

## Data Persistence

| Container Path | Host Path | Content | Persistence |
|---------------|-----------|---------|-------------|
| `/data/db.json` | (volume) | SQLite database | Docker volume `entrofeed_data` |
| `/data/chroma/` | (volume) | ChromaDB vector database | Docker volume `entrofeed_data` |
| `/data/ontology.db` | (volume) | Ontology knowledge base | Docker volume `entrofeed_data` |
| `/data/chat_sessions/` | (volume) | AI chat history | Docker volume `entrofeed_data` |
| `/data/*.json` | (volume) | Backup files | Docker volume `entrofeed_data` |
| `/config/feeds.yml` | `./configs/` | Feed configuration | Host directory mount |
| `/config/settings.yml` | `./configs/` | Application settings | Host directory mount |
| `/config/handlers.yml` | `./configs/` | Handler configuration | Host directory mount |

**Important**: All business data (articles, reading history, chat records, vector index) is stored in the `data` volume. Please backup regularly.

## LLM Provider Configuration

### DashScope (Alibaba Cloud Qwen) - Recommended

1. Get API Key: https://dashscope.console.aliyun.com/
2. Configure in `.env`:

```bash
DEFAULT_LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_MODEL=qwen-plus
```

### Ollama (Local Models)

For users who already have Ollama service:

```bash
DEFAULT_LLM_PROVIDER=ollama
# In Docker, use host.docker.internal to access host
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=llama3
```

**Note**: Ensure Ollama service on the host machine is running and listening on `0.0.0.0:11434`.

### OpenAI (Optional)

```bash
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Directory Structure

```
entrofeed/
├── configs/              # Configuration files (need to persist to host)
│   ├── feeds.yml
│   ├── settings.yml
│   └── handlers.yml
├── data/                 # Data directory (Docker volume)
│   ├── db.json          # SQLite database
│   ├── chroma/          # Vector database
│   ├── ontology.db      # Ontology library
│   └── chat_sessions/   # AI chat history
├── docs/                 # Documentation
├── app/                  # Application code
├── docker-compose.yml
├── Dockerfile
└── .env                  # Environment variables (do not commit to git)
```

## Common Operations

### View Logs

```bash
docker-compose logs -f rss
```

### Enter Container

```bash
docker-compose exec rss bash
```

### Rebuild

```bash
docker-compose down
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Backup Data

```bash
# Export all data
docker run --rm -v entrofeed_data:/data -v $(pwd)/backup:/backup alpine \
  tar czf /backup/entrofeed-data-$(date +%Y%m%d).tar.gz /data

# Backup to host directory
docker-compose down
tar czf entrofeed-backup.tar.gz data/ configs/
```

### Restore Data

```bash
# Stop services
docker-compose down

# Restore data
tarxzf entrofeed-backup.tar.gz

# Restart
docker-compose up -d
```

### Clean Data (Reset)

```bash
docker-compose down
docker volume rm entrofeed_data
docker-compose up -d
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENTROFEED_STORAGE_HANDLER` | `sqlite` | Storage handler |
| `DEFAULT_LLM_PROVIDER` | `dashscope` | Default LLM provider |
| `DASHSCOPE_API_KEY` | - | DashScope API Key |
| `DASHSCOPE_MODEL` | `qwen-plus` | DashScope model |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama service address |
| `OLLAMA_MODEL` | `llama3` | Ollama model |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `REFRESH_INTERVAL` | `5` | RSS refresh interval (minutes) |
| `RECENT_HOURS` | `36` | Recent articles time range (hours) |
| `RSS_BASE_URL` | `http://localhost:8000` | Base URL for RSS links |

## Troubleshooting

### Health Check Failure

```bash
# Check if containers are running
docker-compose ps

# Check logs
docker-compose logs rss

# Check if port is occupied
lsof -i :8000
```

### LLM Connection Issues

1. Confirm API Key is correctly configured in `.env`
2. For Ollama, confirm host service is accessible: `curl http://localhost:11434/v1/models`
3. Restart service: `docker-compose restart rss`

### Data Loss

All data is stored in Docker volume. Deleting containers will not lose data, but deleting the volume will.
Regularly backup `data/` and `configs/` directories.

## Production Deployment

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Using Let's Encrypt SSL

```bash
# Use docker-compose with nginx and certbot
# Reference https://github.com/nginx-proxy/acme-companion
```

### System Service

Create `/etc/systemd/system/entrofeed.service`:

```ini
[Unit]
Description=EntroFeed RSS Service
Requires=docker-compose@entrofeed.service
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/docker-compose -f /path/to/entrofeed/docker-compose.yml up -d
ExecStop=/usr/local/bin/docker-compose -f /path/to/entrofeed/docker-compose.yml down
WorkingDirectory=/path/to/entrofeed

[Install]
WantedBy=multi-user.target
```

Enable service:

```bash
sudo systemctl enable entrofeed
sudo systemctl start entrofeed
```
