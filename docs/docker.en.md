# Docker Deployment Guide

## Quick Start

```bash
# 1. Clone the project
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd EntroFeed_Reader

# 2. Configure environment variables
cp configs/handlers.yml.example configs/handlers.yml
# Edit configs/handlers.yml with your API keys

# 3. Start
docker compose up -d
```

Access http://localhost:8000

## Data Persistence

| Container Path | Host Path | Content | Persistence |
|---------------|-----------|---------|-------------|
| `/data/entrofeed.db` | (volume) | SQLite database | Docker volume |
| `/data/chroma/` | (volume) | ChromaDB vector database | Docker volume |
| `/config/` | `./configs/` | Configuration files | Host directory mount |

**Important**: All business data (articles, reading history, chat records, vector index) is stored in the `data` volume. Please backup regularly.

## Configuration Files

Configuration files are mounted from `./configs/` on the host:

```
configs/
├── feeds.yml           # RSS feed sources
├── handlers.yml        # Handler configurations (LLM, notifications, etc.)
├── settings.yml        # Application settings
└── user.md            # User interests profile
```

### Handler Configuration Example

Edit `configs/handlers.yml`:

```yaml
openai:
  api_key: your_openai_api_key
  model: gpt-4o-mini
ollama:
  base_url: http://host.docker.internal:11434/v1
  model: llama3
dashscope:
  api_key: your_dashscope_api_key
  model: qwen-plus
```

## LLM Provider Configuration

### DashScope (Alibaba Cloud Qwen) - Recommended

1. Get API Key: https://dashscope.console.aliyun.com/
2. Configure in `configs/handlers.yml`:

```yaml
dashscope:
  api_key: your_api_key_here
  model: qwen-plus
```

Then set via UI at **Settings > Handler** or environment variable:
```bash
DEFAULT_LLM_PROVIDER=dashscope
```

### Ollama (Local Models)

For users who already have Ollama service:

```yaml
ollama:
  base_url: http://host.docker.internal:11434/v1
  model: llama3
```

```bash
DEFAULT_LLM_PROVIDER=ollama
```

**Note**: Ensure Ollama service on the host machine is running and listening on `0.0.0.0:11434`.

### OpenAI (Optional)

```yaml
openai:
  api_key: your_api_key_here
  model: gpt-4o-mini
```

```bash
DEFAULT_LLM_PROVIDER=openai
```

## Common Operations

### View Logs

```bash
docker compose logs -f
```

### Enter Container

```bash
docker compose exec rss bash
```

### Rebuild

```bash
docker compose down
git pull
docker compose build --no-cache
docker compose up -d
```

### Backup Data

```bash
# Stop services first
docker compose down

# Backup data and configs
tar czf entrofeed-backup.tar.gz data/ configs/

# Or backup just the database
cp data/entrofeed.db ./entrofeed-backup.db
```

### Restore Data

```bash
# Stop services
docker compose down

# Restore data
tar xzf entrofeed-backup.tar.gz

# Restart
docker compose up -d
```

### Clean Data (Reset)

```bash
docker compose down
docker volume rm entrofeed_data
docker compose up -d
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
| `REFRESH_INTERVAL` | `5` | RSS refresh interval (minutes) |
| `RECENT_HOURS` | `36` | Recent articles time range (hours) |
| `RSS_BASE_URL` | `http://localhost:8000` | Base URL for RSS links |

## Troubleshooting

### Health Check Failure

```bash
# Check if containers are running
docker compose ps

# Check logs
docker compose logs

# Check if port is occupied
lsof -i :8000
```

### LLM Connection Issues

1. Confirm handler is correctly configured in `configs/handlers.yml`
2. For Ollama, confirm host service is accessible: `curl http://localhost:11434/v1/models`
3. Restart service: `docker compose restart`

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
