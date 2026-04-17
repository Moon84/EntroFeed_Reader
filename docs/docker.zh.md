# Docker 部署指南

## 快速启动

```bash
# 1. 克隆项目
git clone https://github.com/Moon84/EntroFeed_Reader.git
cd EntroFeed_Reader

# 2. 配置处理器
cp configs/handlers.yml.example configs/handlers.yml
# 编辑 configs/handlers.yml 填入你的 API keys

# 3. 启动
docker compose up -d
```

访问 http://localhost:8000

## 数据持久化

| 容器内路径 | 主机路径 | 内容 | 持久化方式 |
|-----------|---------|------|-----------|
| `/data/entrofeed.db` | (volume) | SQLite 数据库 | Docker volume |
| `/data/chroma/` | (volume) | ChromaDB 向量数据库 | Docker volume |
| `/config/` | `./configs/` | 配置文件 | 主机目录挂载 |

**重要**: 所有业务数据（文章、阅读历史、对话记录、向量索引）都存储在 `data` 卷中。请定期备份。

## 配置文件说明

配置文件从主机的 `./configs/` 目录挂载：

```
configs/
├── feeds.yml           # RSS 订阅源配置
├── handlers.yml        # 处理器配置（LLM、通知等）
├── settings.yml        # 应用设置
└── user.md            # 用户兴趣配置
```

### 处理器配置示例

编辑 `configs/handlers.yml`：

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

## LLM 提供商配置

### DashScope (阿里云通义千问) - 推荐

1. 获取 API Key: https://dashscope.console.aliyun.com/
2. 在 `configs/handlers.yml` 中配置：

```yaml
dashscope:
  api_key: your_api_key_here
  model: qwen-plus
```

然后在 **设置 > 处理器** 界面选择，或通过环境变量设置：
```bash
DEFAULT_LLM_PROVIDER=dashscope
```

### Ollama (本地模型)

适用于已有 Ollama 服务的用户：

```yaml
ollama:
  base_url: http://host.docker.internal:11434/v1
  model: llama3
```

```bash
DEFAULT_LLM_PROVIDER=ollama
```

**注意**: 确保宿主机的 Ollama 服务已启动并监听 `0.0.0.0:11434`。

### OpenAI (可选)

```yaml
openai:
  api_key: your_api_key_here
  model: gpt-4o-mini
```

```bash
DEFAULT_LLM_PROVIDER=openai
```

## 常用操作

### 查看日志

```bash
docker compose logs -f
```

### 进入容器

```bash
docker compose exec rss bash
```

### 重新构建

```bash
docker compose down
git pull
docker compose build --no-cache
docker compose up -d
```

### 备份数据

```bash
# 先停止服务
docker compose down

# 备份数据和配置
tar czf entrofeed-backup.tar.gz data/ configs/

# 或只备份数据库
cp data/entrofeed.db ./entrofeed-backup.db
```

### 恢复数据

```bash
# 停止服务
docker compose down

# 恢复数据
tar xzf entrofeed-backup.tar.gz

# 重启
docker compose up -d
```

### 清理数据（重置）

```bash
docker compose down
docker volume rm entrofeed_data
docker compose up -d
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
| `REFRESH_INTERVAL` | `5` | RSS 刷新间隔（分钟） |
| `RECENT_HOURS` | `36` | 最近文章时间范围（小时） |
| `RSS_BASE_URL` | `http://localhost:8000` | RSS 链接的基础 URL |

## 故障排除

### 健康检查失败

```bash
# 检查容器是否正常运行
docker compose ps

# 检查日志
docker compose logs

# 检查端口是否被占用
lsof -i :8000
```

### LLM 无法连接

1. 确认处理器已在 `configs/handlers.yml` 中正确配置
2. 对于 Ollama，确认宿主机服务可用：`curl http://localhost:11434/v1/models`
3. 重启服务：`docker compose restart`

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
