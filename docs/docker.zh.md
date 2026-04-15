# Docker 部署指南

## 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd entrofeed

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API keys（至少需要 DASHSCOPE_API_KEY）

# 3. 启动
docker-compose up -d
```

访问 http://localhost:8000

## 数据持久化

| 容器内路径 | 主机路径 | 内容 | 持久化方式 |
|-----------|---------|------|-----------|
| `/data/db.json` | (volume) | SQLite 数据库 | Docker volume `entrofeed_data` |
| `/data/chroma/` | (volume) | ChromaDB 向量数据库 | Docker volume `entrofeed_data` |
| `/data/ontology.db` | (volume) | 本体知识库 | Docker volume `entrofeed_data` |
| `/data/chat_sessions/` | (volume) | AI 对话历史 | Docker volume `entrofeed_data` |
| `/data/*.json` | (volume) | 备份文件 | Docker volume `entrofeed_data` |
| `/config/feeds.yml` | `./configs/` | 订阅源配置 | 主机目录挂载 |
| `/config/settings.yml` | `./configs/` | 应用设置 | 主机目录挂载 |
| `/config/handlers.yml` | `./configs/` | 处理器配置 | 主机目录挂载 |

**重要**: 所有业务数据（文章、阅读历史、对话记录、向量索引）都存储在 `data` 卷中。请定期备份。

## LLM 提供商配置

### DashScope (阿里云通义千问) - 推荐

1. 获取 API Key: https://dashscope.console.aliyun.com/
2. 在 `.env` 中配置：

```bash
DEFAULT_LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_MODEL=qwen-plus
```

### Ollama (本地模型)

适用于已有 Ollama 服务的用户：

```bash
DEFAULT_LLM_PROVIDER=ollama
# Docker 中使用 host.docker.internal 访问主机
OLLAMA_BASE_URL=http://host.docker.internal:11434/v1
OLLAMA_MODEL=llama3
```

**注意**: 确保宿主机的 Ollama 服务已启动并监听 `0.0.0.0:11434`。

### OpenAI (可选)

```bash
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

## 目录结构

```
entrofeed/
├── configs/              # 配置文件（需持久化到主机）
│   ├── feeds.yml
│   ├── settings.yml
│   └── handlers.yml
├── data/                 # 数据目录（Docker volume）
│   ├── db.json          # SQLite 数据库
│   ├── chroma/          # 向量数据库
│   ├── ontology.db      # 本体库
│   └── chat_sessions/   # AI 对话历史
├── docs/                 # 文档
├── app/                  # 应用代码
├── docker-compose.yml
├── Dockerfile
└── .env                  # 环境变量（不提交到 git）
```

## 常用操作

### 查看日志

```bash
docker-compose logs -f rss
```

### 进入容器

```bash
docker-compose exec rss bash
```

### 重新构建

```bash
docker-compose down
git pull
docker-compose build --no-cache
docker-compose up -d
```

### 备份数据

```bash
# 导出所有数据
docker run --rm -v entrofeed_data:/data -v $(pwd)/backup:/backup alpine \
  tar czf /backup/entrofeed-data-$(date +%Y%m%d).tar.gz /data

# 备份到主机目录
docker-compose down
tar czf entrofeed-backup.tar.gz data/ configs/
```

### 恢复数据

```bash
# 停止服务
docker-compose down

# 恢复数据
tarxzf entrofeed-backup.tar.gz

# 重启
docker-compose up -d
```

### 清理数据（重置）

```bash
docker-compose down
docker volume rm entrofeed_data
docker-compose up -d
```

## 环境变量参考

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENTROFEED_STORAGE_HANDLER` | `sqlite` | 存储处理器 |
| `DEFAULT_LLM_PROVIDER` | `dashscope` | 默认 LLM 提供商 |
| `DASHSCOPE_API_KEY` | - | DashScope API Key |
| `DASHSCOPE_MODEL` | `qwen-plus` | DashScope 模型 |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `llama3` | Ollama 模型 |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 模型 |
| `REFRESH_INTERVAL` | `5` | RSS 刷新间隔（分钟） |
| `RECENT_HOURS` | `36` | 最近文章时间范围（小时） |
| `RSS_BASE_URL` | `http://localhost:8000` | RSS 链接的基础 URL |

## 故障排除

### 健康检查失败

```bash
# 检查容器是否正常运行
docker-compose ps

# 检查日志
docker-compose logs rss

# 检查端口是否被占用
lsof -i :8000
```

### LLM 无法连接

1. 确认 API Key 正确配置在 `.env` 中
2. 对于 Ollama，确认宿主机服务可用：`curl http://localhost:11434/v1/models`
3. 重启服务：`docker-compose restart rss`

### 数据丢失

所有数据存储在 Docker volume 中。删除容器不会丢失数据，但删除 volume 会。
定期备份 `data/` 目录和 `configs/` 目录。

## 生产环境部署

### 使用 Nginx 反向代理

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

### 使用 Let's Encrypt SSL

```bash
# 使用 docker-compose with nginx and certbot
# 参考 https://github.com/nginx-proxy/acme-companion
```

### 系统服务

创建 `/etc/systemd/system/entrofeed.service`：

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

启用服务：

```bash
sudo systemctl enable entrofeed
sudo systemctl start entrofeed
```
