# 德国议会RAG智能问答系统 - Streamlit部署指南

## 目录
- [部署方式对比](#部署方式对比)
- [方式一：Streamlit Cloud（推荐）](#方式一streamlit-cloud推荐)
- [方式二：Docker部署](#方式二docker部署)
- [方式三：自建服务器](#方式三自建服务器)
- [方式四：云平台部署](#方式四云平台部署)
- [常见问题](#常见问题)

---

## 部署方式对比

| 方式 | 难度 | 成本 | 适用场景 |
|------|------|------|----------|
| **Streamlit Cloud** | ⭐ 简单 | 免费/付费 | 演示、个人项目 |
| **Docker** | ⭐⭐ 中等 | 按需 | 企业内网、自主可控 |
| **自建服务器** | ⭐⭐ 中等 | 固定 | 长期稳定运行 |
| **Render/Railway** | ⭐⭐ 中等 | 按需 | 快速上线 |

---

## 方式一：Streamlit Cloud（推荐）

Streamlit官方云平台，最简单的部署方式。

### 步骤

1. **准备代码仓库**
   ```bash
   # 确保代码已推送到GitHub
   git add .
   git commit -m "准备Streamlit Cloud部署"
   git push origin main
   ```

2. **访问Streamlit Cloud**
   - 打开 https://share.streamlit.io
   - 使用GitHub账号登录

3. **创建新应用**
   - 点击 "New app"
   - 选择你的GitHub仓库
   - 分支选择 `main`
   - 主文件路径填写 `streamlit_app.py`

4. **配置Secrets（关键！）**
   在 "Advanced settings" > "Secrets" 中添加：

   ```toml
   # LLM API
   OPENAI_API_KEY = "sk-your-key"
   GEMINI_API_KEY = "sk-your-key"
   THIRD_PARTY_BASE_URL = "https://api.evolink.ai/v1"
   THIRD_PARTY_MODEL_NAME = "gemini-2.5-pro"

   # Embedding API
   EMBEDDING_MODE = "deepinfra"
   DEEPINFRA_EMBEDDING_API_KEY = "your-key"

   # Pinecone
   PINECONE_VECTOR_DATABASE_API_KEY = "your-key"
   PINECONE_HOST = "https://your-index.svc.pinecone.io"

   # Cohere
   COHERE_API_KEY = "your-key"

   # 系统
   PRODUCTION_MODE = "true"
   ```

5. **部署**
   - 点击 "Deploy!"
   - 等待几分钟完成部署
   - 获得公网URL: `https://your-app.streamlit.app`

### 注意事项

- **免费版限制**: 1GB内存，可能不够复杂查询
- **付费版**: 推荐升级到 Starter Plan ($25/月) 获得更多资源
- **超时问题**: Streamlit Cloud默认超时较短，复杂查询可能超时

---

## 方式二：Docker部署

### 本地Docker运行

```bash
# 1. 构建镜像
docker build -f Dockerfile.streamlit -t german-rag-streamlit .

# 2. 运行容器
docker run -d \
  --name rag-streamlit \
  -p 8501:8501 \
  --env-file .env \
  german-rag-streamlit

# 3. 访问应用
# http://localhost:8501
```

### Docker Compose方式

```bash
# 使用专用的compose文件
docker-compose -f docker-compose.streamlit.yml up -d

# 查看日志
docker-compose -f docker-compose.streamlit.yml logs -f

# 停止
docker-compose -f docker-compose.streamlit.yml down
```

---

## 方式三：自建服务器

### 在云服务器上部署（阿里云/腾讯云/AWS）

1. **购买服务器**
   - 推荐配置: 2核4G
   - 操作系统: Ubuntu 22.04

2. **安装依赖**
   ```bash
   # 更新系统
   sudo apt update && sudo apt upgrade -y

   # 安装Python
   sudo apt install python3.10 python3.10-venv python3-pip -y

   # 安装Git
   sudo apt install git -y
   ```

3. **部署应用**
   ```bash
   # 克隆代码
   git clone https://github.com/your-repo/rag_germant.git
   cd rag_germant

   # 创建虚拟环境
   python3.10 -m venv venv
   source venv/bin/activate

   # 安装依赖
   pip install -r requirements-streamlit.txt

   # 配置环境变量
   cp .env.example .env
   nano .env  # 编辑填写API密钥
   ```

4. **使用systemd管理服务**
   ```bash
   # 创建服务文件
   sudo nano /etc/systemd/system/streamlit-rag.service
   ```

   内容：
   ```ini
   [Unit]
   Description=German Parliament RAG Streamlit App
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/rag_germant
   Environment="PATH=/home/ubuntu/rag_germant/venv/bin"
   ExecStart=/home/ubuntu/rag_germant/venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

5. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable streamlit-rag
   sudo systemctl start streamlit-rag

   # 查看状态
   sudo systemctl status streamlit-rag
   ```

6. **配置Nginx反向代理（可选）**
   ```bash
   sudo apt install nginx -y
   sudo nano /etc/nginx/sites-available/streamlit
   ```

   内容：
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_read_timeout 86400;
       }
   }
   ```

   ```bash
   sudo ln -s /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

---

## 方式四：云平台部署

### Render.com

1. **创建Web Service**
   - 选择 "Docker" 环境
   - Dockerfile Path: `Dockerfile.streamlit`

2. **配置环境变量**
   在Environment页面添加所有API密钥

3. **设置启动命令**（如果不使用Dockerfile）
   ```
   streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
   ```

### Railway

```bash
# 安装CLI
npm install -g @railway/cli

# 登录并部署
railway login
railway init
railway up
```

在Railway控制台设置启动命令：
```
streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
```

### Hugging Face Spaces

1. 创建新Space，选择 "Streamlit" SDK
2. 上传代码文件
3. 在Settings中配置Secrets

---

## 快速启动脚本

```bash
#!/bin/bash
# start_streamlit.sh

# 激活虚拟环境
source venv/bin/activate

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "❌ 请先配置 .env 文件"
    exit 1
fi

# 加载环境变量
export $(cat .env | grep -v '^#' | xargs)

# 启动Streamlit
echo "🚀 启动Streamlit应用..."
echo "📍 访问地址: http://localhost:8501"
streamlit run streamlit_app.py --server.port 8501
```

---

## 常见问题

### Q1: Streamlit Cloud部署后显示"Error"

**原因**: 通常是缺少环境变量或API密钥无效

**解决**:
1. 检查Secrets配置是否完整
2. 查看应用日志排查具体错误

### Q2: 应用加载很慢

**原因**: 首次加载需要初始化workflow（连接Pinecone等）

**解决**:
1. 这是正常现象，首次需要30-60秒
2. 后续请求会快很多

### Q3: 查询超时（Streamlit Cloud）

**原因**: 复杂查询可能需要10-20分钟，超过平台限制

**解决**:
1. 升级到Streamlit Cloud付费版
2. 或使用自建服务器/Docker部署

### Q4: WebSocket连接断开

**原因**: 长时间无操作或网络不稳定

**解决**:
1. 已在 `.streamlit/config.toml` 中优化配置
2. 使用稳定的网络环境

### Q5: 内存不足

**原因**: 免费版资源限制

**解决**:
1. 升级到更高配置
2. 使用Docker部署并分配更多内存

---

## 监控和维护

### 查看日志

```bash
# Docker
docker logs -f rag-streamlit

# systemd
sudo journalctl -u streamlit-rag -f

# Streamlit Cloud
# 在应用页面点击 "Manage app" > "Logs"
```

### 重启服务

```bash
# Docker
docker restart rag-streamlit

# systemd
sudo systemctl restart streamlit-rag

# Streamlit Cloud
# 在应用页面点击 "Reboot app"
```

---

## 相关文件

| 文件 | 用途 |
|------|------|
| `streamlit_app.py` | 主应用程序 |
| `.streamlit/config.toml` | Streamlit配置 |
| `.streamlit/secrets.toml.example` | Secrets示例 |
| `Dockerfile.streamlit` | Docker镜像 |
| `docker-compose.streamlit.yml` | Docker Compose |
| `requirements-streamlit.txt` | 依赖文件 |
