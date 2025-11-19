# render_app.py (已修复召回逻辑)
# [新增] 导入语言检测库和字符串模糊匹配库

import os
import re
from contextlib import asynccontextmanager
from typing import List
import copy

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# [新增] 导入语言检测库和字符串模糊匹配库
from langdetect import detect
from thefuzz import process,fuzz

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.output_parsers import PydanticOutputParser

# 导入云服务组件
from langchain_pinecone import PineconeVectorStore
from langchain_cohere import CohereRerank
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# --- 全局变量 ---
RAG_COMPONENTS = {}
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# --- 为不同语言创建独立的提示词模板 ---
PROMPT_ZH = ChatPromptTemplate.from_template(
    "你是一名专业的叉车技术助理。你的任务是基于提供的上下文，综合出一个全面且准确的答案。\n"
    "请仔细分析用户的问题和检索到的上下文，上下文中可能包含表格、列表和段落。\n"
    "将来自上下文不同部分的信息连接起来，形成一个完整的画面。\n"
    "如果上下文中提供了模型范围（例如 'CPDS13~20'），你必须能够推断出问题中提到的具体型号（例如 'CPDS16'）的规格。\n"
    "用清晰易读的格式组织你的答案。\n"
    "严格按照上下文进行回答，如果在彻底分析后，答案确实无法在上下文中找到，或者上下文没有任何信息，那么，且仅当此时，你才应该说明“根据提供的材料无法回答”。坚决不能随意编造任何不存在的内容。\n\n"
    "上下文:\n{context}\n\n"
    "问题: {input}\n\n"
    "答案:"
)

PROMPT_EN = ChatPromptTemplate.from_template(
    "You are a professional forklift technical assistant. Your task is to synthesize a comprehensive and accurate answer based on the provided context.\n"
    "Analyze the user's question and the retrieved context carefully. The context may contain tables, lists, and paragraphs.\n"
    "Connect information from different parts of the context to form a complete picture.\n"
    "If a model range is provided in the context (e.g., 'CPDS13~20'), you must be able to infer the specifications for the specific model mentioned in the question (e.g., 'CPDS16').\n"
    "Organize your answer in a clear and readable format.\n"
    "Strictly answer based on the context. If, after thorough analysis, the answer cannot be found in the context, or if there is no information in the context, then and only then should you state, 'I cannot answer based on the provided materials.' Do not invent any content.\n\n"
    "Context:\n{context}\n\n"
    "Question: {input}\n\n"
    "Answer:"
)


# --- Pydantic 模型定义 ---
class SubQuery(BaseModel):
    query: str = Field(description="一个独立的、语义完整的子查询。")
    synonyms: List[str] = Field(description="与子查询核心概念相关的同义词、近义词或技术术语列表。")

class OptimizedQueries(BaseModel):
    queries: List[SubQuery] = Field(description="一个包含所有优化后的子查询对象的列表。")

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    source_documents: List[dict]

# --- 核心逻辑封装 ---
# --- 核心逻辑封装 ---

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

def initialize_components():
    """初始化所有用于查询的 LangChain 组件并返回"""
    APP_MODE = os.getenv("APP_MODE")
    print(f"--- (1/3) 开始以 {APP_MODE} 模式 初始化 LangChain 组件 ---")

    # [ 关键修复 1 ]：在函数顶部初始化变量为 None
    base_embeddings = None
    final_reranker = None
    vector_store = None
    base_retriever: None = None # <--- 确保它总是有个初始值

    if APP_MODE == "cloud":
        # --- 云端模式 ---
        print("连接到 OpenAI 和 Pinecone...")
        base_embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        print("    - OpenAI Embeddings 初始化完成。")

        final_reranker = CohereRerank(model="rerank-multilingual-v3.0", top_n=10)
        print("    - Cohere Rerank 初始化完成。")

        vector_store = PineconeVectorStore.from_existing_index(
            index_name=os.getenv("PINECONE_INDEX_NAME","rag-part"),
            embedding=base_embeddings,
            namespace=os.getenv("NAME_SPACE","__default__")
        )
        print("    - Pinecone VectorStore 连接成功。")
        base_retriever = vector_store.as_retriever(search_kwargs={"k": 20})

    elif APP_MODE == "local":
        # --- 本地模式 ---
        print("加载 本地HuggingFace模型 和 本地Chroma数据库...")

        # 1. 本地模型
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        base_embeddings = HuggingFaceEmbeddings(model_name=model_name)
        print("    - 本地 Embeddings 初始化完成。")

        final_reranker = CohereRerank(model="rerank-multilingual-v3.0", top_n=10)
        print("    - Cohere Rerank 初始化完成。")

        # 2. 本地 Chroma
        persist_directory = "./chroma_db"
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=base_embeddings
        )
        print("    - 本地 Chroma 数据库加载成功。")

        base_retriever = vector_store.as_retriever(search_kwargs={"k": 20})

    # [ 关键修复 2 ]：添加 else 分支处理无效 APP_MODE
    else:
        # 如果 APP_MODE 既不是 'cloud' 也不是 'local'，则抛出错误
        raise ValueError(f"APP_MODE 环境变量未设置或设置无效 (当前值: {APP_MODE})。请设置为 'local' 或 'cloud'。")


    # [ 修复 3 ]：删除这一行多余且可能错误的 print
    # print("    - Pinecone VectorStore 连接成功。")


    parser = PydanticOutputParser(pydantic_object=OptimizedQueries)
    rewrite_prompt_template = """你是一个用于RAG系统的查询分析专家。你的任务是分析用户的原始查询，并根据下面提供的格式指令，生成一个包含优化后查询的JSON对象。

        遵循以下原则：
        1. **分解**: 如果查询包含多个意图（例如，同时询问外观和部件），分解成独立的子查询对象。
        2. **扩展**: 对每个子查询对象，在`synonyms`字段中丰富相关的同义词、近义词或技术术语。

        {format_instructions}

        **用户的原始查询是：**
        {original_query}
        """
    rewrite_prompt = ChatPromptTemplate.from_template(rewrite_prompt_template, partial_variables={"format_instructions": parser.get_format_instructions()})
    rewrite_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    rewrite_chain = rewrite_prompt | rewrite_llm | parser
    print("    - 查询重写链 (Rewrite Chain) 初始化完成。")

    # 现在 base_retriever 在任何有效路径下都会被赋值
    return {
        "rewrite_chain": rewrite_chain,
        "base_retriever": base_retriever, # <--- 现在肯定有值了
        "final_reranker": final_reranker,
        "answer_llm": ChatOpenAI(model="gpt-5", temperature=0),
        "vector_store": vector_store
    }
# --- FastAPI 生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n--- 服务器启动流程开始 ---")
    load_dotenv()
    required_keys = ["OPENAI_API_KEY", "PINECONE_API_KEY", "COHERE_API_KEY", "PINECONE_INDEX_NAME", "PINECONE_ENVIRONMENT"]
    for key in required_keys:
        if not os.getenv(key):
            raise ValueError(f"{key} 未设置！")
    
    components = initialize_components()
    RAG_COMPONENTS.update(components)
    print("--- (2/3) LangChain 组件全部初始化完成 ---")
    print("--- (3/3) 服务器已准备就绪，可以接受请求 ---")
    
    yield
    print("\n--- 服务器关闭流程开始 ---")
    RAG_COMPONENTS.clear()

# --- 创建 FastAPI 应用 ---
app = FastAPI(lifespan=lifespan, title="RAG Engine API - Final Version")

@app.get("/")
def read_root():
    return {"status": "RAG Engine API is running."}

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    print("\n" + "="*50)
    print("接收到新的 /query 请求")
    print("="*50)

    cleaned_query = request.question.strip()
    print(f"原始查询: {cleaned_query}")
    
    # 1. 实体提取
    print("\n--- 1. 实体提取 ---")
    
    # [BUG 1 修复] 修复正则表达式，删除末尾的 \b 以支持中文
    # 旧: model_pattern = r'\b([A-Z]+[0-9]+[A-Z0-9]*-[A-Z0-9-()]+)\b'
    model_pattern = r'([A-Z]+[0-9]+[A-Z0-9]*-[A-Z0-9-()]+)' # (已修改)
    
    match = re.search(model_pattern, cleaned_query, re.IGNORECASE)
    extracted_model = match.group(0).upper() if match else None
    
    pinecone_filter = {}

    # [BUG 2 修复] 为召回和查询优化准备“干净”的语义查询
    semantic_query_base = cleaned_query
    
    if extracted_model:
        print(f"识别到实体: {extracted_model}。将启用元数据过滤。")
        pinecone_filter = {"product_models": {"$in": [extracted_model]}}
        
        # [关键修复] 像在重排时一样，从基础查询中删除实体
        # 使用 re.sub 替换，确保只替换匹配到的部分，且不区分大小写
        semantic_query_base = re.sub(model_pattern, "", cleaned_query, flags=re.IGNORECASE).strip()
        
        # [关键修复] 如果查询只包含型号 (例如 "CPQYD20-XRW22")
        # 移除后 semantic_query_base 会变为空。
        # 此时，我们必须使用型号本身作为语义查询，否则会搜索空字符串。
        if not semantic_query_base:
            semantic_query_base = extracted_model
            
        print(f"用于语义搜索和优化的基础查询: '{semantic_query_base}'")
        
    else:
        print("未识别到特定型号，将进行全局搜索。")

    # 2. 查询优化
    print("\n--- 2. 查询优化 ---")
    try:
        # [关键修复] 使用 semantic_query_base 而不是 cleaned_query
        optimized_queries_pydantic = RAG_COMPONENTS["rewrite_chain"].invoke({"original_query": semantic_query_base})
        
        all_queries_list = []
        for item in optimized_queries_pydantic.queries:
            all_queries_list.append(item.query)
            all_queries_list.extend(item.synonyms)
        
        # [关键修复] 如果查询优化失败或列表为空 (例如只搜型号)
        # 确保我们至少用 semantic_query_base 搜索一次
        if not all_queries_list:
             all_queries_list = [semantic_query_base]
             
        # 确保基础查询也在列表中，以防优化器将其遗漏
        if semantic_query_base not in all_queries_list:
            all_queries_list.append(semantic_query_base)

        print(f"优化后的查询列表 (共 {len(all_queries_list)} 个): {all_queries_list}")
    except Exception as e:
        print(f"查询优化失败: {e}")
        all_queries_list = [semantic_query_base] # (已修改)

    # --- 3. 独立检索 (带过滤) ---
    print(f"\n--- 3. 独立检索 (带过滤)，过滤器: {pinecone_filter} ---")
    unique_docs = {}
    
    base_retriever = RAG_COMPONENTS["base_retriever"]
    search_kwargs = copy.deepcopy(base_retriever.search_kwargs)
    # [ 调试步骤 1：暂时注释掉这 2 行 ]
    if pinecone_filter:
        search_kwargs['filter'] = pinecone_filter
    
    vector_store = RAG_COMPONENTS["vector_store"]
    request_specific_retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    for i, q in enumerate(all_queries_list):
        if not q.strip(): # 避免搜索空字符串
            continue
        
        # --- [在这里添加调试代码] ---
        #print(f"\n[DEBUG] 循环 {i+1}：正在查询 '{q}'")
        #print(f"[DEBUG] 循环 {i+1}：使用的过滤器是: {request_specific_retriever.search_kwargs.get('filter')}")
        # --- [调试代码结束] ---
        
        print(f"  正在为第 {i+1}/{len(all_queries_list)} 个查询 '{q}' 进行初步检索...")
        retrieved_docs = request_specific_retriever.invoke(q)
        print(f"    -> 初步召回 {len(retrieved_docs)} 个文档。")

        # 预览代码保持不变...
        
        for doc in retrieved_docs:
            # --- [ 调试步骤 2：在这里添加一行 print ] ---
            #print(f"      [DEBUG-METADATA] 文档源: {doc.metadata.get('source')}, 型号: {doc.metadata.get('product_models')}")
            # --- [ 调试代码结束 ] ---
            if doc.page_content not in unique_docs:
                unique_docs[doc.page_content] = doc
    
    merged_docs = list(unique_docs.values())
    print(f"\n所有查询完成后，去重共得到 {len(merged_docs)} 份候选文档。")

    # --- [重大优化] 检查是否存在“型号不存在”的特定失败场景 ---
    if extracted_model and not merged_docs:
        print(f"检测到实体 '{extracted_model}' 但未找到相关文档。开始执行双重推荐逻辑...")
        
        # 1. 执行宽泛的语义搜索，为两种推荐准备候选池
        suggestion_docs = base_retriever.invoke(cleaned_query)
        
        # 2. 从返回的文档中收集所有相关的产品型号作为候选池
        candidate_models = set()
        if suggestion_docs:
            for doc in suggestion_docs:
                models = doc.metadata.get("product_models")
                if models and isinstance(models, list):
                    candidate_models.update(models)
        
        # 如果候选池为空，则直接返回无法回答
        if not candidate_models:
             return QueryResponse(answer=f"知识库中不存在型号为 {extracted_model} 的产品，也未能找到任何相关主题的文档。", source_documents=[])

        # 3. 执行两种推荐逻辑
        # 3.1 语义推荐 (Semantic Suggestion): 简单地选择第一个语义最相关的文档中的第一个型号
        semantic_suggestion = list(candidate_models)[0]

        # 3.2 字符串相似度推荐 (String Similarity Suggestion)
        # a. 将候选型号列表转为list
        candidate_models_list = list(candidate_models)
        # b. 使用 thefuzz 库找到最相似的字符串
        # b. 使用 thefuzz 库并指定更直观的 fuzz.ratio 算法
        best_match = process.extractOne(extracted_model, candidate_models_list, scorer=fuzz.ratio)

        string_suggestion = best_match[0] # best_match 是一个元组 (型号, 相似度分数)
        
        print(f"语义推荐型号: {semantic_suggestion}")
        print(f"字符串相似度推荐型号: {string_suggestion} (相似度: {best_match[1]})")

        # 4. 根据语言和推荐结果构建友好的提示信息
        try:
            lang = detect(cleaned_query)
        except:
            lang = 'en'
        
        # 根据两种推荐是否相同，生成不同的回答
        if string_suggestion == semantic_suggestion:
            if lang == 'zh-cn' or lang == 'zh-tw':
                answer = f"知识库中不存在型号为 {extracted_model} 的产品。根据您问题的上下文以及最相似的型号名称，我们找到了相关的型号：{string_suggestion}，您是否想了解该型号的信息？"
            else:
                answer = f"The product model {extracted_model} was not found. Based on your question's context and the most similar model name, we found a relevant model: {string_suggestion}. Were you looking for information about it?"
        else:
            if lang == 'zh-cn' or lang == 'zh-tw':
                answer = (f"知识库中不存在型号为 {extracted_model} 的产品。\n"
                          f"- 根据您问题的主题，我们找到了关于 **{semantic_suggestion}** 的信息。\n"
                          f"- 与您输入的名称最相似的型号是 **{string_suggestion}**。\n"
                          f"请问您想了解哪一个型号？")
            else:
                answer = (f"The product model {extracted_model} was not found.\n"
                          f"- Based on the topic of your question, we found information about **{semantic_suggestion}**.\n"
                          f"- The model with the most similar name is **{string_suggestion}**.\n"
                          f"Which model would you like to know about?")

        print(f"最终生成的建议性回答: {answer}")
        return QueryResponse(answer=answer, source_documents=[])

    # --- 4. 最终精排 ---
    # (此部分及之后代码保持不变)
    print("\n--- 4. 最终精排 ---")
    
    # [修改] 使用 semantic_query_base 进行重排，逻辑保持一致
    rerank_query = semantic_query_base
    print(f"用于重排的查询: '{rerank_query}'")

    final_reranker = RAG_COMPONENTS["final_reranker"]
    final_context_docs = final_reranker.compress_documents(
        documents=merged_docs, 
        query=rerank_query
    )
    print(f"最终精排后剩下 {len(final_context_docs)} 份文档用于生成答案。")
    
    if final_context_docs:
        print("\n    --- 最终精排文档详细内容 ---")
        for doc_idx, doc in enumerate(final_context_docs):
            print(f"      --- [文档 {doc_idx+1}] ---")
            print(f"      内容: {doc.page_content}")
            print(f"      元数据: {doc.metadata}")
            print(f"      ------------------------")

    # --- 5. 生成答案 ---
    print("\n--- 5. 生成答案 ---")
    
    if not final_context_docs:
        print("上下文为空，将直接返回无法回答的信息，以防止幻觉。")
        try:
            lang = detect(cleaned_query)
        except:
            lang = 'en'
        
        if lang == 'zh-cn' or lang == 'zh-tw':
            answer = "根据提供的材料无法回答。"
        else:
            answer = "I cannot answer based on the provided materials."
            
        return QueryResponse(answer=answer, source_documents=[])

    try:
        lang = detect(cleaned_query)
        print(f"检测到查询语言为: {lang}")
    except:
        lang = 'en'
        print("语言检测失败，默认使用英文。")

    if lang == 'zh-cn' or lang == 'zh-tw':
        prompt = PROMPT_ZH
    else:
        prompt = PROMPT_EN

    answer_llm = RAG_COMPONENTS["answer_llm"]
    document_chain = create_stuff_documents_chain(answer_llm, prompt)
    
    answer = document_chain.invoke({
        "input": cleaned_query,
        "context": final_context_docs
    })
    print("答案生成完毕。")
    
    return QueryResponse(answer=answer, source_documents=[doc.model_dump() for doc in final_context_docs])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)