#!/usr/bin/env python3
"""
德国议会RAG智能问答系统 - FastAPI服务
支持云端部署，对外提供API服务

API端点:
- POST /api/v1/ask - 标准问答
- POST /api/v1/ask/deep - 深度分析模式
- GET /api/v1/health - 健康检查
- GET /api/v1/info - 系统信息
- GET / - API文档入口
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载环境变量
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env", override=True)

# 导入项目模块
from src.utils.logger import setup_logger
from src.graph.workflow import QuestionAnswerWorkflow
from src.graph.state import create_initial_state, GraphState
from src.config import settings

# 初始化logger
logger = setup_logger()

# ========== Pydantic 模型定义 ==========

class QuestionRequest(BaseModel):
    """问题请求模型"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题（支持中文和德文）")
    deep_thinking: bool = Field(default=False, description="是否启用深度分析模式（耗时更长，分析更详细）")

class SourceDocument(BaseModel):
    """来源文档模型"""
    text: str = Field(description="文档内容片段")
    year: Optional[str] = Field(default=None, description="年份")
    speaker: Optional[str] = Field(default=None, description="发言人")
    party: Optional[str] = Field(default=None, description="党派")
    score: Optional[float] = Field(default=None, description="相关性分数")

class SubAnswer(BaseModel):
    """子问题答案模型"""
    question: str = Field(description="子问题")
    answer: str = Field(description="子问题答案")
    sources_count: int = Field(default=0, description="参考来源数量")

class AnswerResponse(BaseModel):
    """问答响应模型"""
    success: bool = Field(description="请求是否成功")
    question: str = Field(description="原始问题")
    answer: str = Field(description="最终答案")

    # 处理信息
    intent: Optional[str] = Field(default=None, description="问题意图: simple/complex")
    question_type: Optional[str] = Field(default=None, description="问题类型")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="提取的参数")

    # 子问题和答案（复杂问题时有值）
    sub_questions: Optional[List[Any]] = Field(default=None, description="拆解后的子问题（字符串或结构化对象）")
    sub_answers: Optional[List[SubAnswer]] = Field(default=None, description="子问题答案")

    # 来源文档
    sources_count: int = Field(default=0, description="参考来源总数")
    sources: Optional[List[SourceDocument]] = Field(default=None, description="部分参考来源")

    # 深度分析信息
    deep_thinking_mode: bool = Field(default=False, description="是否为深度分析模式")
    reasoning_steps: Optional[List[str]] = Field(default=None, description="推理步骤（深度模式）")
    kg_expansion_info: Optional[Dict[str, Any]] = Field(default=None, description="知识图谱扩展信息")

    # 性能信息
    processing_time_ms: int = Field(description="处理耗时（毫秒）")

    # 错误信息
    error: Optional[str] = Field(default=None, description="错误信息")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(description="服务状态")
    workflow_ready: bool = Field(description="工作流是否就绪")
    timestamp: str = Field(description="检查时间")

class SystemInfoResponse(BaseModel):
    """系统信息响应"""
    service_name: str = Field(default="德国议会RAG智能问答系统")
    version: str = Field(default="1.0.0")
    embedding_mode: str = Field(description="Embedding模式")
    llm_model: str = Field(description="LLM模型")
    vector_db: str = Field(default="Pinecone")
    production_mode: bool = Field(description="是否为生产模式")
    supported_languages: List[str] = Field(default=["中文", "德文"])

# ========== 全局变量 ==========
workflow: Optional[QuestionAnswerWorkflow] = None
executor = ThreadPoolExecutor(max_workers=4)

# ========== 辅助函数 ==========

def extract_sources_from_state(state: GraphState, max_sources: int = 5) -> List[SourceDocument]:
    """从状态中提取来源文档"""
    sources = []

    # 优先从reranked_results获取
    results = state.get("reranked_results") or state.get("retrieval_results") or []

    for result in results:
        chunks = result.get("chunks", [])
        for chunk in chunks[:max_sources]:
            metadata = chunk.get("metadata", {})
            sources.append(SourceDocument(
                text=chunk.get("text", "")[:500],  # 截断长文本
                year=metadata.get("year"),
                speaker=metadata.get("speaker"),
                party=metadata.get("group") or metadata.get("party"),
                score=chunk.get("score") or chunk.get("rerank_score")
            ))
            if len(sources) >= max_sources:
                return sources

    return sources

def count_total_sources(state: GraphState) -> int:
    """统计总来源数"""
    total = 0
    results = state.get("reranked_results") or state.get("retrieval_results") or []
    for result in results:
        total += len(result.get("chunks", []))
    return total

def extract_sub_answers(state: GraphState) -> Optional[List[SubAnswer]]:
    """提取子问题答案"""
    sub_answers = state.get("sub_answers")
    if not sub_answers:
        return None

    return [
        SubAnswer(
            question=sa.get("question", ""),
            answer=sa.get("answer", ""),
            sources_count=len(sa.get("sources", []))
        )
        for sa in sub_answers
    ]

def run_workflow_sync(question: str, deep_thinking: bool = False) -> GraphState:
    """同步运行工作流"""
    global workflow
    if workflow is None:
        raise RuntimeError("工作流未初始化")

    # 创建初始状态
    initial_state = create_initial_state(question, deep_thinking_mode=deep_thinking)

    # 运行工作流
    return workflow.graph.invoke(initial_state)

# ========== FastAPI 生命周期管理 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global workflow

    logger.info("=" * 60)
    logger.info("德国议会RAG智能问答API服务启动中...")
    logger.info("=" * 60)

    # 验证必要的环境变量
    required_vars = [
        ("OPENAI_API_KEY", "LLM API密钥"),
        ("DEEPINFRA_EMBEDDING_API_KEY", "Embedding API密钥"),
        ("PINECONE_VECTOR_DATABASE_API_KEY", "Pinecone API密钥"),
    ]

    missing_vars = []
    for var_name, description in required_vars:
        if not os.getenv(var_name):
            missing_vars.append(f"{var_name} ({description})")

    if missing_vars:
        logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
        raise ValueError(f"缺少必要的环境变量: {', '.join(missing_vars)}")

    # 初始化工作流
    try:
        logger.info("[启动] 正在初始化问答工作流...")

        # 强制启用生产模式
        settings.production_mode = True
        logger.info("[启动] 已启用生产模式")

        workflow = QuestionAnswerWorkflow()
        logger.info("[启动] 问答工作流初始化成功")

    except Exception as e:
        logger.error(f"[启动] 工作流初始化失败: {str(e)}")
        raise

    logger.info("=" * 60)
    logger.info("API服务已准备就绪，可以接受请求")
    logger.info("=" * 60)

    yield

    # 清理资源
    logger.info("API服务正在关闭...")
    workflow = None
    executor.shutdown(wait=False)
    logger.info("API服务已关闭")

# ========== 创建 FastAPI 应用 ==========

app = FastAPI(
    title="德国议会RAG智能问答API",
    description="""
## 德国议会（Bundestag）智能问答系统 API

基于RAG技术的德国联邦议院演讲记录智能问答系统，支持1949-2025年的议会演讲数据。

### 功能特点
- 支持中文和德文问题输入
- 支持简单查询和复杂分析
- 支持多年份、多党派、多议员的对比分析
- 支持深度分析模式（知识图谱扩展）

### 问题类型支持
- **事实查询**: 某年某党派的具体立场
- **变化分析**: 跨年份的政策变化追踪
- **对比分析**: 多党派观点对比
- **趋势分析**: 政策演变趋势

### 示例问题
- "2019年CDU/CSU对难民政策的立场是什么？"
- "请对比2015-2018年各党派在移民问题上的立场变化"
- "Merkel在2017年关于欧盟一体化说了什么？"
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== API 端点 ==========

@app.get("/", tags=["Root"])
async def root():
    """API入口 - 重定向到文档"""
    return {
        "service": "德国议会RAG智能问答API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """健康检查"""
    from datetime import datetime
    return HealthResponse(
        status="healthy" if workflow is not None else "initializing",
        workflow_ready=workflow is not None,
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/v1/info", response_model=SystemInfoResponse, tags=["System"])
async def system_info():
    """获取系统信息"""
    return SystemInfoResponse(
        embedding_mode=settings.embedding_mode,
        llm_model=settings.third_party_model_name,
        production_mode=settings.production_mode
    )

@app.post("/api/v1/ask", response_model=AnswerResponse, tags=["QA"])
async def ask_question(request: QuestionRequest):
    """
    标准问答接口

    - **question**: 用户问题（支持中文和德文）
    - **deep_thinking**: 是否启用深度分析模式（默认False）

    深度分析模式会：
    - 强制启用知识图谱扩展
    - 生成更详细的分析报告
    - 显示推理过程
    - 预计耗时: 3-5分钟
    """
    if workflow is None:
        raise HTTPException(status_code=503, detail="服务正在初始化，请稍后重试")

    start_time = time.time()

    try:
        logger.info(f"[API] 收到问题: {request.question[:100]}...")

        # 在线程池中运行同步工作流
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            executor,
            run_workflow_sync,
            request.question,
            request.deep_thinking
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # 构建响应
        response = AnswerResponse(
            success=not state.get("error"),
            question=request.question,
            answer=state.get("final_answer", "抱歉，无法生成答案"),
            intent=state.get("intent"),
            question_type=state.get("question_type"),
            parameters=state.get("parameters"),
            sub_questions=state.get("sub_questions"),
            sub_answers=extract_sub_answers(state),
            sources_count=count_total_sources(state),
            sources=extract_sources_from_state(state),
            deep_thinking_mode=state.get("deep_thinking_mode", False),
            reasoning_steps=state.get("reasoning_steps"),
            kg_expansion_info=state.get("kg_expansion_info"),
            processing_time_ms=processing_time_ms,
            error=state.get("error")
        )

        logger.info(f"[API] 问题处理完成，耗时: {processing_time_ms}ms")
        return response

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[API] 处理问题失败: {str(e)}")

        return AnswerResponse(
            success=False,
            question=request.question,
            answer="处理问题时发生错误",
            processing_time_ms=processing_time_ms,
            error=str(e)
        )

@app.post("/api/v1/ask/deep", response_model=AnswerResponse, tags=["QA"])
async def ask_question_deep(request: QuestionRequest):
    """
    深度分析问答接口（强制启用深度模式）

    此接口会强制启用深度分析模式，适用于：
    - 复杂的多年份变化分析
    - 多党派立场对比
    - 需要详细推理过程的问题

    **注意**: 处理时间较长，通常需要3-5分钟
    """
    # 强制启用深度分析
    request.deep_thinking = True
    return await ask_question(request)

# ========== 示例问题端点 ==========

@app.get("/api/v1/examples", tags=["Help"])
async def get_example_questions():
    """获取示例问题"""
    return {
        "examples": {
            "simple_queries": [
                "2019年CDU/CSU对难民政策的立场是什么？",
                "Merkel在2017年关于欧盟一体化说了什么？",
                "2018年AfD在移民问题上的主要观点是什么？"
            ],
            "complex_queries": [
                "请对比2015-2018年各党派在难民家庭团聚问题上的立场变化",
                "2017年德国联邦议会中各党派对专业人才移民制度改革分别持什么立场？",
                "请概述2015年以来德国基民盟对难民政策的立场发生了哪些主要变化"
            ],
            "german_queries": [
                "Welche Positionen vertraten die verschiedenen Parteien im Deutschen Bundestag 2017 zur Reform des Fachkräfteeinwanderungsgesetzes?",
                "Was waren die Hauptpositionen und Forderungen der Grünen zur Migrationsfrage im Deutschen Bundestag 2015?"
            ]
        },
        "supported_parties": ["CDU/CSU", "SPD", "GRÜNE", "FDP", "DIE LINKE", "AfD"],
        "data_range": "1949-2025"
    }

# ========== 主程序入口 ==========

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="德国议会RAG API服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--reload", action="store_true", help="开发模式（热重载）")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")

    args = parser.parse_args()

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║           德国议会RAG智能问答API服务                            ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  地址: http://{args.host}:{args.port}                              ║
    ║  文档: http://{args.host}:{args.port}/docs                         ║
    ║  健康检查: http://{args.host}:{args.port}/api/v1/health            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1
    )
