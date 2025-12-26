# 德国议会RAG智能问答系统 - API部署指南

## 目录
- [快速开始](#快速开始)
- [本地运行](#本地运行)
- [Docker部署](#docker部署)
- [云平台部署](#云平台部署)
- [API使用说明](#api使用说明)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 环境要求
- Python 3.10+
- 网络访问（调用外部API）
- 必需的API密钥（见下方）

### 2. 必需的API密钥

| API服务 | 用途 | 获取地址 |
|---------|------|----------|
| **Evolink/OpenAI** | LLM推理 | https://evolink.ai |
| **DeepInfra** | Embedding API | https://deepinfra.com |
| **Pinecone** | 向量数据库 | https://pinecone.io |
| **Cohere** (可选) | ReRank | https://cohere.com |

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写API密钥
```

---

## 本地运行

### 方式一：直接运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装API依赖
pip install -r requirements-api.txt

# 启动API服务
python api_server.py
```

### 方式二：开发模式（热重载）

```bash
python api_server.py --reload
```

### 访问服务

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health
- **示例问题**: http://localhost:8000/api/v1/examples

---

## Docker部署

### 构建并运行

```bash
# 构建镜像
docker build -t german-parliament-rag-api .

# 运行容器
docker run -d \
  --name rag-api \
  -p 8000:8000 \
  --env-file .env \
  german-parliament-rag-api
```

### 使用Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 云平台部署

### 方案一：Render.com（推荐）

1. **Fork仓库到GitHub**

2. **在Render创建Web Service**
   - 连接GitHub仓库
   - Render会自动检测 `render.yaml` 配置

3. **设置环境变量**
   在Render控制台的 Environment 页面添加：
   ```
   OPENAI_API_KEY=xxx
   DEEPINFRA_EMBEDDING_API_KEY=xxx
   PINECONE_VECTOR_DATABASE_API_KEY=xxx
   PINECONE_HOST=xxx
   COHERE_API_KEY=xxx
   ```

4. **部署**
   - 点击 "Manual Deploy" 或等待自动部署
   - 部署完成后获得公网URL

### 方案二：Railway

```bash
# 安装Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 部署
railway up
```

### 方案三：阿里云/腾讯云

1. 购买云服务器（推荐2核4G）
2. 安装Docker
3. 使用Docker Compose部署

```bash
# SSH到服务器
ssh root@your-server-ip

# 克隆代码
git clone your-repo-url
cd rag_germant

# 配置环境变量
cp .env.example .env
vim .env

# 启动服务
docker-compose up -d
```

### 方案四：Google Cloud Run

```bash
# 构建并推送镜像
gcloud builds submit --tag gcr.io/PROJECT_ID/german-parliament-rag

# 部署到Cloud Run
gcloud run deploy german-parliament-rag \
  --image gcr.io/PROJECT_ID/german-parliament-rag \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=xxx,..."
```

---

## API使用说明

### 基础问答

```bash
curl -X POST "https://your-api-url/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "2019年CDU/CSU对难民政策的立场是什么？",
    "deep_thinking": false
  }'
```

### 深度分析

```bash
curl -X POST "https://your-api-url/api/v1/ask/deep" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "请对比2015-2018年各党派在难民问题上的立场变化"
  }'
```

### Python调用示例

```python
import requests

API_URL = "https://your-api-url/api/v1/ask"

response = requests.post(API_URL, json={
    "question": "2019年德国联邦议院讨论了哪些主要议题？",
    "deep_thinking": False
})

result = response.json()
print(result["answer"])
```

### JavaScript调用示例

```javascript
const response = await fetch('https://your-api-url/api/v1/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: '2019年CDU/CSU对难民政策的立场是什么？',
    deep_thinking: false
  })
});

const result = await response.json();
console.log(result.answer);
```

---

## API响应格式

```json
{
  "success": true,
  "question": "用户问题",
  "answer": "系统回答",
  "intent": "simple/complex",
  "question_type": "事实查询/变化分析/对比分析",
  "parameters": {
    "time_range": {"start_year": "2015", "end_year": "2018"},
    "parties": ["CDU/CSU", "SPD"],
    "topics": ["难民政策"]
  },
  "sub_questions": ["子问题1", "子问题2"],
  "sources_count": 15,
  "sources": [
    {
      "text": "文档片段...",
      "year": "2017",
      "speaker": "Merkel",
      "party": "CDU/CSU"
    }
  ],
  "processing_time_ms": 5230,
  "deep_thinking_mode": false
}
```

---

## 常见问题

### Q1: 服务启动时报错"缺少环境变量"
**A**: 确保已正确配置所有必需的API密钥，检查 `.env` 文件。

### Q2: API响应很慢（>30秒）
**A**:
- 检查网络连接（需要访问Pinecone、LLM API）
- 复杂问题需要更长时间处理
- 深度分析模式预计需要3-5分钟

### Q3: Docker容器启动后立即退出
**A**: 查看日志 `docker logs rag-api`，通常是环境变量配置问题。

### Q4: 如何更新已部署的服务？
**A**:
```bash
# Docker方式
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Render方式
# 推送代码到GitHub，Render会自动重新部署
```

### Q5: 如何监控API服务？
**A**:
- 健康检查端点: `/api/v1/health`
- 日志: `docker-compose logs -f`
- 推荐使用Render/Railway内置监控

---

---

## 前后端分离部署（推荐）

本项目采用前后端分离架构：
- **后端服务 (API Server)**: FastAPI，处理问答逻辑
- **前端服务 (Web UI)**: Streamlit，提供用户界面

### 部署架构

```
┌──────────────────┐     ┌──────────────────┐
│   Streamlit UI   │────▶│   FastAPI API    │
│   (前端展示)      │     │   (后端服务)      │
│   Port: 8501     │     │   Port: 8000     │
└──────────────────┘     └──────────────────┘
         │                        │
         │                        ▼
         │              ┌──────────────────┐
         │              │   Pinecone +     │
         │              │   LLM APIs       │
         └──────────────│   (外部服务)      │
                        └──────────────────┘
```

### 步骤一：部署API服务（后端）

#### Railway部署

1. **创建新项目**
   ```bash
   # 登录Railway
   railway login

   # 创建项目
   railway init
   ```

2. **配置环境变量**
   在Railway控制台设置：
   ```
   OPENAI_API_KEY=xxx
   DEEPINFRA_EMBEDDING_API_KEY=xxx
   PINECONE_VECTOR_DATABASE_API_KEY=xxx
   PINECONE_HOST=xxx
   COHERE_API_KEY=xxx
   PRODUCTION_MODE=true
   ```

3. **配置启动命令**
   - Build Command: `pip install -r requirements-api.txt`
   - Start Command: `python api_server.py`

4. **部署并获取URL**
   部署成功后，记录API服务的公网URL，例如：
   `https://your-api-service.railway.app`

### 步骤二：部署Streamlit UI（前端）

#### Railway部署

1. **创建新的Railway服务**（同一项目中新建服务）

2. **配置环境变量**
   ```
   # 最关键：指向API服务地址
   API_URL=https://your-api-service.railway.app
   API_TIMEOUT=300
   ```

3. **配置启动命令**
   - Build Command: `pip install -r requirements-streamlit.txt`
   - Start Command: `streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0`

4. **配置端口**
   Railway会自动检测端口，或手动设置 `PORT=8501`

### 本地开发（前后端同时运行）

```bash
# 终端1：启动API服务
source venv/bin/activate
python api_server.py

# 终端2：启动Streamlit UI
source venv/bin/activate
streamlit run streamlit_app.py
```

默认情况下：
- API服务运行在 `http://localhost:8000`
- Streamlit UI运行在 `http://localhost:8501`
- Streamlit会自动连接本地API

### 环境变量配置

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `API_URL` | API服务地址 | `http://localhost:8000` | 云端必需 |
| `API_TIMEOUT` | API请求超时(秒) | `300` | 否 |

### 故障排查

#### Streamlit无法连接API
1. 检查 `API_URL` 环境变量是否正确设置
2. 确保API服务已正常运行
3. 检查网络连通性

#### 跨域问题 (CORS)
API服务已配置允许所有来源，如遇问题检查 `api_server.py` 中的CORS设置。

---

## 技术支持

- 项目文档: [README.md](README.md)
- API文档: 访问 `/docs` 端点
- 问题反馈: 提交GitHub Issue
