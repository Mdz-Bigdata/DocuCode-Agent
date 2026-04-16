#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DocuCode Agent Ultimate - 终极完整功能后端 (改进版)"""

# 抑制所有 PDF 处理相关的警告
import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfdocument").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)
logging.getLogger("pdfminer.pdfpage").setLevel(logging.ERROR)

import os
import sys
import json
import uuid
import shutil
import random
import re
import tempfile
import subprocess
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
import uvicorn

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

app = FastAPI(title="DocuCode Agent Ultimate", version="5.0.0")

ULTIMATE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ULTIMATE_DIR, "static")
UPLOAD_DIR = os.path.join(ULTIMATE_DIR, "uploads")
RAG_DIR = os.path.join(ULTIMATE_DIR, "rag_data")
MCP_DIR = os.path.join(ULTIMATE_DIR, "mcp_tools")
SKILLS_DIR = os.path.join(ULTIMATE_DIR, "skills")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RAG_DIR, exist_ok=True)
os.makedirs(MCP_DIR, exist_ok=True)
os.makedirs(SKILLS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

class Document:
    """文档对象"""
    
    def __init__(self, doc_id: str, content: str, metadata: Dict[str, Any] = None):
        self.doc_id = doc_id
        self.content = content
        self.metadata = metadata or {}
        self.embedding: Optional[List[float]] = None
        self.chunks: List['DocumentChunk'] = []


class DocumentChunk:
    """文档分块"""
    
    def __init__(self, chunk_id: str, content: str, doc_id: str, 
                start_idx: int, end_idx: int, metadata: Dict[str, Any] = None):
        self.chunk_id = chunk_id
        self.content = content
        self.doc_id = doc_id
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.metadata = metadata or {}
        self.embedding: Optional[List[float]] = None
        self.score: float = 0.0


class ChunkingStrategy:
    """分块策略"""
    
    @staticmethod
    def simple_chunking(text: str, chunk_size: int = 512, 
                    chunk_overlap: int = 128, max_chunks: int = 2000) -> List[Tuple[int, int, str]]:
        """简单分块策略（优化版：防止超大文档卡住）"""
        chunks = []
        if not text:
            return chunks
        
        text_length = len(text)
        max_process_length = 10 * 1024 * 1024  # 最大处理 10MB 文本
        
        if text_length > max_process_length:
            text = text[:max_process_length]
            text_length = max_process_length
        
        start = 0
        
        while start < text_length and len(chunks) < max_chunks:
            end = min(start + chunk_size, text_length)
            
            if end < text_length:
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                
                if last_period > start:
                    end = last_period + 1
                elif last_newline > start:
                    end = last_newline + 1
            
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append((start, end, chunk_text))
            
            start = end - chunk_overlap
            if start <= 0:
                start = end
        
        return chunks
    
    @staticmethod
    def small_to_big_chunking(text: str, small_size: int = 256, 
                            big_size: int = 1024) -> Tuple[List[Tuple], List[Tuple]]:
        """Small-to-Big 分块策略"""
        small_chunks = ChunkingStrategy.simple_chunking(text, small_size, small_size // 4)
        big_chunks = ChunkingStrategy.simple_chunking(text, big_size, big_size // 4)
        return small_chunks, big_chunks


class SimpleEmbeddingModel:
    """简单的 Embedding 模型（基于哈希）"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """编码文本为向量"""
        embeddings = []
        for text in texts:
            embedding = self._text_to_vector(text)
            embeddings.append(embedding)
        return embeddings
    
    def _text_to_vector(self, text: str) -> List[float]:
        """将文本转换为向量（基于哈希）"""
        if not text:
            return [0.0] * self.dimension
        
        hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()
        seed = int.from_bytes(hash_bytes[:4], byteorder='big')
        
        np.random.seed(seed)
        vector = np.random.randn(self.dimension)
        vector = vector / np.linalg.norm(vector)
        
        return vector.tolist()


class VectorStore:
    """简单的向量存储"""
    
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embedding_model = SimpleEmbeddingModel()
    
    def add_chunks(self, chunks: List[DocumentChunk]):
        """添加分块"""
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_model.encode(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
            self.chunks.append(chunk)
    
    def search(self, query: str, top_k: int = 10, 
            similarity_threshold: float = 0.0) -> List[DocumentChunk]:
        """向量检索"""
        if not self.chunks:
            return []
        
        query_embedding = self.embedding_model.encode([query])[0]
        
        results = []
        for chunk in self.chunks:
            if chunk.embedding is None:
                continue
            
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            if similarity >= similarity_threshold:
                chunk.score = similarity
                results.append(chunk)
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if HAS_NUMPY:
            a = np.array(vec1)
            b = np.array(vec2)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class BM25Retriever:
    """BM25 关键词检索器"""
    
    def __init__(self):
        self.corpus: List[str] = []
        self.chunks: List[DocumentChunk] = []
        self.bm25: Optional[BM25Okapi] = None
        self.tokenized_corpus: List[List[str]] = []
        self._needs_rebuild = False
    
    def add_chunks(self, chunks: List[DocumentChunk]):
        """添加分块"""
        self.chunks.extend(chunks)
        self.corpus.extend([chunk.content for chunk in chunks])
        
        for chunk in chunks:
            self.tokenized_corpus.append(self._tokenize(chunk.content))
        
        self._needs_rebuild = True
    
    def _rebuild_bm25(self):
        """重建 BM25 索引（惰性加载）"""
        if not self._needs_rebuild or not HAS_BM25:
            return
        
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self._needs_rebuild = False
    
    def search(self, query: str, top_k: int = 10) -> List[DocumentChunk]:
        """BM25 检索"""
        self._rebuild_bm25()
        
        if not HAS_BM25 or self.bm25 is None:
            return self._simple_keyword_search(query, top_k)
        
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        results = []
        for i, score in enumerate(scores):
            if i < len(self.chunks):
                chunk = self.chunks[i]
                chunk.score = score
                results.append(chunk)
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _simple_keyword_search(self, query: str, top_k: int = 10) -> List[DocumentChunk]:
        """简单关键词搜索（当 BM25 不可用时）"""
        query_lower = query.lower()
        results = []
        
        for chunk in self.chunks:
            count = chunk.content.lower().count(query_lower)
            if count > 0:
                chunk.score = count
                results.append(chunk)
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.lower().split()


class HybridRetriever:
    """混合检索器（向量 + BM25）"""
    
    def __init__(self, vector_weight: float = 0.3, bm25_weight: float = 0.7):
        self.vector_store = VectorStore()
        self.bm25_retriever = BM25Retriever()
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
    
    def add_chunks(self, chunks: List[DocumentChunk]):
        """添加分块"""
        self.vector_store.add_chunks(chunks)
        self.bm25_retriever.add_chunks(chunks)
    
    def search(self, query: str, top_k: int = 10) -> List[DocumentChunk]:
        """混合检索"""
        vector_results = self.vector_store.search(query, top_k * 2)
        bm25_results = self.bm25_retriever.search(query, top_k * 2)
        
        chunk_scores: Dict[str, Tuple[DocumentChunk, float]] = {}
        
        for chunk in vector_results:
            normalized_score = chunk.score
            chunk_scores[chunk.chunk_id] = (chunk, normalized_score * self.vector_weight)
        
        for chunk in bm25_results:
            if chunk.chunk_id in chunk_scores:
                existing_chunk, existing_score = chunk_scores[chunk.chunk_id]
                normalized_score = chunk.score / max(1.0, max(c.score for c in bm25_results)) if bm25_results else 0
                total_score = existing_score + normalized_score * self.bm25_weight
                chunk_scores[chunk.chunk_id] = (existing_chunk, total_score)
            else:
                normalized_score = chunk.score / max(1.0, max(c.score for c in bm25_results)) if bm25_results else 0
                chunk_scores[chunk.chunk_id] = (chunk, normalized_score * self.bm25_weight)
        
        results = sorted(chunk_scores.values(), key=lambda x: x[1], reverse=True)
        final_results = []
        
        for chunk, score in results[:top_k]:
            chunk.score = score
            final_results.append(chunk)
        
        return final_results


class Reranker:
    """重排序器"""
    
    def __init__(self):
        pass
    
    def rerank(self, query: str, chunks: List[DocumentChunk], top_k: int = 5) -> List[DocumentChunk]:
        """重排序"""
        if not chunks:
            return []
        
        query_terms = set(query.lower().split())
        
        for chunk in chunks:
            content_lower = chunk.content.lower()
            term_overlap = len(query_terms & set(content_lower.split()))
            chunk_length = len(chunk.content)
            
            rerank_score = chunk.score * 0.7 + (term_overlap / max(1, len(query_terms))) * 0.3
            chunk.score = rerank_score
        
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]


class ContextCompressor:
    """上下文压缩器"""
    
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
    
    def compress(self, query: str, chunks: List[DocumentChunk]) -> str:
        """压缩上下文"""
        context_parts = []
        current_length = 0
        
        for chunk in chunks:
            relevant_content = self._extract_relevant_content(query, chunk.content)
            
            if current_length + len(relevant_content) <= self.max_tokens:
                doc_info = f"【文档: {chunk.metadata.get('filename', 'unknown')}】"
                context_parts.append(f"{doc_info}\n{relevant_content}")
                current_length += len(relevant_content) + len(doc_info) + 2
            else:
                remaining = self.max_tokens - current_length
                if remaining > 100:
                    doc_info = f"【文档: {chunk.metadata.get('filename', 'unknown')}】"
                    truncated = relevant_content[:remaining]
                    context_parts.append(f"{doc_info}\n{truncated}...")
                break
        
        return "\n\n".join(context_parts)
    
    def _extract_relevant_content(self, query: str, content: str) -> str:
        """提取相关内容"""
        query_terms = query.lower().split()
        
        sentences = re.split(r'[。！？.!?\n]', content)
        relevant_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_lower = sentence.lower()
            has_relevance = any(term in sentence_lower for term in query_terms)
            
            if has_relevance or len(relevant_sentences) < 2:
                relevant_sentences.append(sentence)
        
        return "。".join(relevant_sentences) + "。" if relevant_sentences else content[:500]


class RAGConfig:
    """RAG 配置类"""
    
    def __init__(self, 
                similarity_threshold: float = 0.7,
                max_retrieve_count: int = 60,
                rerank_weight: float = 0.5,
                memory_window_size: int = 8,
                memory_compression_threshold: float = 0.9,
                max_context_tokens: int = 3500,
                vector_weight: float = 0.3,
                bm25_weight: float = 0.7,
                chunk_size_small: int = 256,
                chunk_size_big: int = 1024,
                enable_query_rewrite: bool = True,
                enable_hyde: bool = True,
                enable_metadata_filter: bool = True,
                enable_colbert: bool = True,
                enable_crossencoder: bool = True,
                enable_kg_verification: bool = True,
                cosine_weight: float = 0.4,
                kg_confidence_weight: float = 0.6,
                max_kg_hops: int = 3):
        self.similarity_threshold = similarity_threshold
        self.max_retrieve_count = max_retrieve_count
        self.rerank_weight = rerank_weight
        self.memory_window_size = memory_window_size
        self.memory_compression_threshold = memory_compression_threshold
        self.max_context_tokens = max_context_tokens
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.chunk_size_small = chunk_size_small
        self.chunk_size_big = chunk_size_big
        self.enable_query_rewrite = enable_query_rewrite
        self.enable_hyde = enable_hyde
        self.enable_metadata_filter = enable_metadata_filter
        self.enable_colbert = enable_colbert
        self.enable_crossencoder = enable_crossencoder
        self.enable_kg_verification = enable_kg_verification
        self.cosine_weight = cosine_weight
        self.kg_confidence_weight = kg_confidence_weight
        self.max_kg_hops = max_kg_hops


class QueryRewriter:
    """查询重写器"""
    
    @staticmethod
    def rewrite_query(query: str, language: str = 'zh', num_variations: int = 3) -> List[str]:
        """重写查询，生成同义问法和扩展"""
        variations = [query]
        
        if language == 'zh':
            QueryRewriter._add_chinese_variations(variations, query)
            QueryRewriter._add_multi_query_expansion(variations, query, num_variations)
        
        return variations
    
    @staticmethod
    def _add_chinese_variations(variations: List[str], query: str):
        """添加中文同义问法"""
        synonyms = {
            "什么": ["哪些", "怎么", "如何"],
            "怎么": ["如何", "什么", "怎样"],
            "如何": ["怎么", "什么", "怎样"],
            "是": ["为", "是指", "是什么"],
            "的": ["之"],
            "查询": ["搜索", "查找", "检索"],
            "搜索": ["查询", "查找", "检索"],
            "查找": ["查询", "搜索", "检索"],
        }
        
        for word, replacements in synonyms.items():
            if word in query:
                for rep in replacements:
                    variation = query.replace(word, rep)
                    if variation not in variations:
                        variations.append(variation)
    
    @staticmethod
    def _add_multi_query_expansion(variations: List[str], query: str, num_variations: int):
        """多重 Query 扩展，用 LLM 思维生成行业背景知识"""
        expansions = [
            f"{query}的相关背景知识",
            f"{query}的应用场景",
            f"{query}的技术要点"
        ]
        
        for exp in expansions:
            if exp not in variations and len(variations) < num_variations + 1:
                variations.append(exp)


class ColBERTRetriever:
    """ColBERT 粗排检索器"""
    
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
    
    def add_chunks(self, chunks: List[DocumentChunk]):
        """添加分块"""
        self.chunks.extend(chunks)
    
    def search(self, query: str, top_k: int = 20) -> List[DocumentChunk]:
        """ColBERT 风格粗排（模拟实现）"""
        query_tokens = set(query.lower().split())
        
        results = []
        for chunk in self.chunks:
            chunk_tokens = set(chunk.content.lower().split())
            token_overlap = len(query_tokens & chunk_tokens)
            chunk.score = token_overlap / max(1.0, len(query_tokens))
            results.append(chunk)
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


class CrossEncoderReranker:
    """CrossEncoder 精排器"""
    
    def __init__(self):
        pass
    
    def rerank(self, query: str, chunks: List[DocumentChunk], top_k: int = 10) -> List[DocumentChunk]:
        """CrossEncoder 风格精排（模拟实现）"""
        for chunk in chunks:
            content_lower = chunk.content.lower()
            query_lower = query.lower()
            
            ngram_match = 0
            n = 2
            query_ngrams = set(query_lower[i:i+n] for i in range(len(query_lower)-n+1))
            content_ngrams = set(content_lower[i:i+n] for i in range(len(content_lower)-n+1))
            ngram_overlap = len(query_ngrams & content_ngrams)
            ngram_match = ngram_overlap / max(1.0, len(query_ngrams))
            
            base_score = chunk.score
            cross_score = 0.6 * base_score + 0.4 * ngram_match
            chunk.score = cross_score
        
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]


class KnowledgeGraph:
    """简单知识图谱，用于实体链跳数判断"""
    
    def __init__(self):
        self.entities: Dict[str, Set[str]] = {}
        self.relations: Dict[str, List[Tuple[str, str]]] = {}
    
    def add_entity(self, entity: str):
        """添加实体"""
        if entity not in self.entities:
            self.entities[entity] = set()
    
    def add_relation(self, entity1: str, entity2: str, relation: str = "related"):
        """添加关系"""
        self.add_entity(entity1)
        self.add_entity(entity2)
        self.entities[entity1].add(entity2)
        self.entities[entity2].add(entity1)
        
        if relation not in self.relations:
            self.relations[relation] = []
        self.relations[relation].append((entity1, entity2))
    
    def extract_entities(self, text: str) -> List[str]:
        """从文本中提取实体（简单关键词匹配）"""
        entities = []
        keywords = ["人工智能", "机器学习", "深度学习", "神经网络", "算法", "数据", "模型", 
                "Python", "Java", "JavaScript", "API", "数据库", "系统", "应用"]
        
        for keyword in keywords:
            if keyword in text:
                entities.append(keyword)
        
        return entities
    
    def calculate_hops(self, text1: str, text2: str) -> int:
        """计算两段文本在知识图谱上的跳数"""
        entities1 = self.extract_entities(text1)
        entities2 = self.extract_entities(text2)
        
        if not entities1 or not entities2:
            return 999
        
        min_hops = 999
        for e1 in entities1:
            for e2 in entities2:
                hops = self._bfs_hops(e1, e2)
                if hops < min_hops:
                    min_hops = hops
        
        return min_hops
    
    def _bfs_hops(self, start: str, end: str) -> int:
        """BFS 计算最短跳数"""
        if start == end:
            return 0
        
        visited = set()
        queue = [(start, 0)]
        
        while queue:
            current, hops = queue.pop(0)
            
            if current in visited:
                continue
            visited.add(current)
            
            if current in self.entities:
                for neighbor in self.entities[current]:
                    if neighbor == end:
                        return hops + 1
                    if neighbor not in visited:
                        queue.append((neighbor, hops + 1))
        
        return 999
    
    def calculate_confidence(self, query: str, chunk_content: str, max_hops: int = 3) -> float:
        """计算知识图谱置信度"""
        hops = self.calculate_hops(query, chunk_content)
        
        if hops <= max_hops:
            return 1.0 - (hops / (max_hops + 1))
        else:
            return 0.1


class AdvancedReranker:
    """高级重排器：知识图谱 + 混合权重"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.kg = KnowledgeGraph()
        self._init_sample_kg()
    
    def _init_sample_kg(self):
        """初始化示例知识图谱"""
        entities = ["人工智能", "机器学习", "深度学习", "神经网络", "算法", "数据", "模型",
                "Python", "Java", "API", "数据库", "系统"]
        
        for e in entities:
            self.kg.add_entity(e)
        
        self.kg.add_relation("人工智能", "机器学习")
        self.kg.add_relation("机器学习", "深度学习")
        self.kg.add_relation("深度学习", "神经网络")
        self.kg.add_relation("机器学习", "算法")
        self.kg.add_relation("机器学习", "模型")
        self.kg.add_relation("数据", "数据库")
        self.kg.add_relation("Python", "API")
        self.kg.add_relation("Java", "系统")
    
    def rerank(self, query: str, chunks: List[DocumentChunk], top_k: int = 5) -> List[DocumentChunk]:
        """高级重排：结合余弦相似度和知识图谱置信度"""
        for chunk in chunks:
            cosine_score = chunk.score
            kg_confidence = self.kg.calculate_confidence(query, chunk.content, self.config.max_kg_hops)
            
            final_score = (self.config.cosine_weight * cosine_score + 
                        self.config.kg_confidence_weight * kg_confidence)
            chunk.score = final_score
        
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]


class HyDEGenerator:
    """假设性文档生成器"""
    
    @staticmethod
    def generate_hypothetical_answer(query: str, language: str = 'zh') -> str:
        """生成假设性答案（用于增强检索）"""
        if language == 'zh':
            return f"关于「{query}」的相关信息：这个主题通常涉及相关的概念、应用场景和技术细节。在实际应用中，我们需要考虑多种因素和解决方案。"
        else:
            return f"Information about '{query}': This topic typically involves related concepts, application scenarios, and technical details. In practice, we need to consider various factors and solutions."


class PromptEngineer:
    """提示工程师"""
    
    @staticmethod
    def build_rag_prompt(query: str, context: str, language: str = 'zh') -> str:
        """构建 RAG 提示模板"""
        if language == 'zh':
            return f"""请基于以下参考文档回答问题。如果文档中没有相关信息，请明确说明。

参考文档：
{context}

问题：{query}

请提供准确、详细的回答。"""
        else:
            return f"""Please answer the question based on the following reference documents. If there is no relevant information in the documents, please state that clearly.

Reference Documents:
{context}

Question: {query}

Please provide an accurate and detailed answer."""


class RAGEngine:
    """完整的 RAG 引擎 - 高级版（支持 ColBERT、CrossEncoder、知识图谱）"""
    
    def __init__(self, data_dir: str = "./rag_data", config: RAGConfig = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.config = config or RAGConfig()
        
        self.documents: Dict[str, Document] = {}
        self.retriever = HybridRetriever(
            vector_weight=self.config.vector_weight, 
            bm25_weight=self.config.bm25_weight
        )
        
        self.colbert_retriever = ColBERTRetriever()
        self.crossencoder_reranker = CrossEncoderReranker()
        self.advanced_reranker = AdvancedReranker(self.config)
        self.reranker = Reranker()
        
        self.context_compressor = ContextCompressor(
            max_tokens=self.config.max_context_tokens
        )
        
        self.query_rewriter = QueryRewriter()
        self.hyde_generator = HyDEGenerator()
        self.prompt_engineer = PromptEngineer()
        
        self.search_count = 0
    
    def add_document(self, content: str, filename: str = None, 
                    metadata: Dict[str, Any] = None) -> str:
        """添加文档"""
        doc_id = str(uuid.uuid4())
        
        doc_metadata = metadata or {}
        doc_metadata["filename"] = filename or f"document_{doc_id[:8]}"
        doc_metadata["added_time"] = datetime.now().isoformat()
        doc_metadata["content_length"] = len(content)
        
        document = Document(doc_id, content, doc_metadata)
        
        small_chunks_data, big_chunks_data = ChunkingStrategy.small_to_big_chunking(
            content, 
            small_size=self.config.chunk_size_small, 
            big_size=self.config.chunk_size_big
        )
        
        chunks = []
        for i, (start, end, chunk_text) in enumerate(small_chunks_data):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_metadata = {
                "filename": doc_metadata["filename"],
                "doc_id": doc_id,
                "chunk_index": i,
                "start_idx": start,
                "end_idx": end
            }
            chunk = DocumentChunk(chunk_id, chunk_text, doc_id, start, end, chunk_metadata)
            chunks.append(chunk)
            document.chunks.append(chunk)
        
        self.documents[doc_id] = document
        self.retriever.add_chunks(chunks)
        self.colbert_retriever.add_chunks(chunks)
        
        return doc_id
    
    def search(self, query: str, top_k: int = 10, 
            rerank_top_k: int = 5, 
            use_query_rewrite: bool = None,
            use_hyde: bool = None) -> Dict[str, Any]:
        """搜索 - 高级检索管道：HyDE + 多重Query + ColBERT + CrossEncoder + 知识图谱"""
        self.search_count += 1
        
        use_query_rewrite = use_query_rewrite if use_query_rewrite is not None else self.config.enable_query_rewrite
        use_hyde = use_hyde if use_hyde is not None else self.config.enable_hyde
        
        all_results = []
        
        queries_to_search = [query]
        
        if use_query_rewrite:
            rewritten_queries = self.query_rewriter.rewrite_query(query, num_variations=3)
            queries_to_search.extend(rewritten_queries[1:])
        
        if use_hyde:
            hyde_answer = self.hyde_generator.generate_hypothetical_answer(query)
            queries_to_search.append(hyde_answer)
        
        seen_chunk_ids = set()
        
        for q in queries_to_search:
            if self.config.enable_colbert:
                colbert_results = self.colbert_retriever.search(q, self.config.max_retrieve_count // 2)
                for chunk in colbert_results:
                    if chunk.chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(chunk.chunk_id)
                        all_results.append(chunk)
            
            hybrid_results = self.retriever.search(q, self.config.max_retrieve_count // 2)
            for chunk in hybrid_results:
                if chunk.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk.chunk_id)
                    all_results.append(chunk)
        
        all_results.sort(key=lambda x: x.score, reverse=True)
        raw_results = all_results[:self.config.max_retrieve_count]
        
        if self.config.enable_crossencoder:
            reranked_results = self.crossencoder_reranker.rerank(query, raw_results, rerank_top_k * 2)
        else:
            reranked_results = self.reranker.rerank(query, raw_results, rerank_top_k * 2)
        
        if self.config.enable_kg_verification:
            final_results = self.advanced_reranker.rerank(query, reranked_results, rerank_top_k)
        else:
            final_results = reranked_results[:rerank_top_k]
        
        compressed_context = self.context_compressor.compress(query, final_results)
        
        rag_prompt = self.prompt_engineer.build_rag_prompt(query, compressed_context)
        
        results = []
        for chunk in final_results:
            results.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "score": chunk.score,
                "metadata": chunk.metadata
            })
        
        return {
            "query": query,
            "results": results,
            "context": compressed_context,
            "rag_prompt": rag_prompt,
            "search_count": self.search_count,
            "total_chunks": len(self.retriever.vector_store.chunks),
            "total_docs": len(self.documents),
            "config_used": {
                "similarity_threshold": self.config.similarity_threshold,
                "max_retrieve_count": self.config.max_retrieve_count,
                "rerank_weight": self.config.rerank_weight,
                "vector_weight": self.config.vector_weight,
                "bm25_weight": self.config.bm25_weight,
                "enable_colbert": self.config.enable_colbert,
                "enable_crossencoder": self.config.enable_crossencoder,
                "enable_kg_verification": self.config.enable_kg_verification,
                "cosine_weight": self.config.cosine_weight,
                "kg_confidence_weight": self.config.kg_confidence_weight
            },
            "advanced_features_used": {
                "query_rewrite": use_query_rewrite,
                "hyde": use_hyde,
                "colbert": self.config.enable_colbert,
                "crossencoder": self.config.enable_crossencoder,
                "knowledge_graph": self.config.enable_kg_verification
            }
        }
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档"""
        return self.documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._rebuild_index()
            return True
        return False
    
    def _rebuild_index(self):
        """重建索引"""
        self.retriever = HybridRetriever(vector_weight=0.3, bm25_weight=0.7)
        
        all_chunks = []
        for doc in self.documents.values():
            all_chunks.extend(doc.chunks)
        
        if all_chunks:
            self.retriever.add_chunks(all_chunks)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_size = sum(len(doc.content) for doc in self.documents.values())
        
        return {
            "document_count": len(self.documents),
            "chunk_count": len(self.retriever.vector_store.chunks),
            "search_count": self.search_count,
            "total_size": total_size,
            "total_size_human": self._human_readable_size(total_size)
        }
    
    def _human_readable_size(self, size: int) -> str:
        """人类可读的大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class OCRProcessor:
    """OCR 处理器（配合 MinerU 使用）"""
    
    @staticmethod
    def is_available() -> bool:
        """检查 MinerU 是否可用"""
        try:
            import mineru
            return True
        except ImportError:
            return False
    
    @staticmethod
    def extract_with_mineru(file_path: str) -> str:
        """使用 MinerU 进行 OCR 识别"""
        try:
            import mineru
            
            result = mineru.process_file(file_path)
            
            if result and 'text' in result:
                return result['text']
            
            return ""
        except ImportError:
            return "【需要安装 MinerU 才能进行 OCR 识别】"
        except Exception as e:
            return f"【OCR 识别错误: {str(e)}】"


class FileProcessor:
    """文件处理器"""
    
    @staticmethod
    def read_text_file(file_path: str) -> str:
        """读取文本文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        try:
            with open(file_path, 'rb') as f:
                return f.read().decode('utf-8', errors='ignore')
        except Exception:
            return ""
    
    @staticmethod
    def read_pdf(file_path: str, use_ocr: bool = False) -> str:
        """读取 PDF 文件（优化版：优先使用pdfplumber，效果更好）"""
        if use_ocr and OCRProcessor.is_available():
            try:
                ocr_text = OCRProcessor.extract_with_mineru(file_path)
                if ocr_text and not ocr_text.startswith('【'):
                    return ocr_text
            except:
                pass
        
        try:
            # 抑制 pdfplumber 字体警告
            import warnings
            warnings.filterwarnings("ignore", message="Could not get FontBBox")
            
            import pdfplumber
            import logging
            
            # 进一步抑制 pdfplumber 的日志警告
            logging.getLogger("pdfplumber").setLevel(logging.ERROR)
            logging.getLogger("pdfminer").setLevel(logging.ERROR)
            logging.getLogger("pdfminer.pdfdocument").setLevel(logging.ERROR)
            logging.getLogger("pdfminer.pdfinterp").setLevel(logging.ERROR)
            logging.getLogger("pdfminer.pdfpage").setLevel(logging.ERROR)
            
            text = ""
            max_pages = 200
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
                for i, page in enumerate(pdf.pages):
                    if i >= max_pages:
                        break
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue
            
            lines = text.split('\n')
            fixed_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                
                if line.startswith('项') and ('：' in line or ':' in line) and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    
                    has_digit = False
                    project_num = None
                    extra_text = ''
                    
                    if next_line:
                        digits = []
                        for c in next_line:
                            if c.isdigit():
                                digits.append(c)
                            else:
                                break
                        
                        if digits:
                            project_num = ''.join(digits)
                            has_digit = True
                            extra_text = next_line[len(digits):].strip()
                    
                    if has_digit and project_num:
                        colon_pos = line.find('：')
                        if colon_pos == -1:
                            colon_pos = line.find(':')
                        
                        if colon_pos != -1:
                            after_colon = line[colon_pos + 1:].strip()
                            
                            if extra_text and not after_colon:
                                after_colon = extra_text
                            elif extra_text and after_colon and extra_text not in after_colon:
                                after_colon = extra_text + ' ' + after_colon
                            
                            fixed_line = f'项目{project_num}：{after_colon}'
                            fixed_lines.append(fixed_line)
                            i += 2
                            continue
                
                fixed_lines.append(line)
                i += 1
            
            return '\n'.join(fixed_lines)
            
        except ImportError:
            pass
        
        try:
            import PyPDF2
            
            text = ""
            max_pages = 100
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                for i, page in enumerate(reader.pages):
                    if i >= max_pages:
                        break
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except:
                        continue
            return text
        except ImportError:
            return "【PDF 文件 - 需要安装 pdfplumber 或 PyPDF2 库才能读取内容】"
        except Exception as e:
            return f"【PDF 读取错误: {str(e)}】"
    
    @staticmethod
    def read_file(file_path: str, filename: str = None, use_ocr: bool = False) -> Tuple[str, str]:
        """读取文件"""
        filename = filename or os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == '.pdf':
            content = FileProcessor.read_pdf(file_path, use_ocr=use_ocr)
            file_type = 'pdf'
        elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
            if use_ocr and OCRProcessor.is_available():
                content = OCRProcessor.extract_with_mineru(file_path)
            else:
                content = "【图片文件 - 如需 OCR 识别请安装 MinerU】"
            file_type = 'image'
        else:
            content = FileProcessor.read_text_file(file_path)
            file_type = 'text'
        
        return content, file_type


rag_config = RAGConfig()
rag_engine = RAGEngine(data_dir=RAG_DIR, config=rag_config)
HAS_RAG_ENGINE = True


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None
    agent_type: Optional[str] = "default"
    model_type: Optional[str] = "dashscope"


class RAGQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    search_title_only: Optional[bool] = False


class CodeGenerateRequest(BaseModel):
    request: str
    language: str
    add_comments: bool
    add_tests: bool
    explain_code: bool


class ModelConfig(BaseModel):
    model_type: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None


class RAGConfigRequest(BaseModel):
    similarity_threshold: Optional[float] = 0.7
    max_retrieve_count: Optional[int] = 60
    rerank_weight: Optional[float] = 0.5
    memory_window_size: Optional[int] = 8
    memory_compression_threshold: Optional[float] = 0.9
    max_context_tokens: Optional[int] = 3500
    vector_weight: Optional[float] = 0.3
    bm25_weight: Optional[float] = 0.7
    chunk_size_small: Optional[int] = 256
    chunk_size_big: Optional[int] = 1024
    enable_query_rewrite: Optional[bool] = True
    enable_hyde: Optional[bool] = True
    enable_metadata_filter: Optional[bool] = True
    enable_colbert: Optional[bool] = True
    enable_crossencoder: Optional[bool] = True
    enable_kg_verification: Optional[bool] = True
    cosine_weight: Optional[float] = 0.4
    kg_confidence_weight: Optional[float] = 0.6
    max_kg_hops: Optional[int] = 3


class RAGChatRequest(BaseModel):
    message: str
    chat_mode: str = "knowledge_base"
    doc_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    top_k: Optional[int] = 5
    model_type: Optional[str] = "dashscope"


class MCPToolAddRequest(BaseModel):
    name: str
    description: str
    icon: str
    category: str
    code: str


class SkillInstallRequest(BaseModel):
    name: str
    description: str
    version: str
    author: str


class GitHubImportRequest(BaseModel):
    repo_url: str


knowledge_base = []
chat_sessions = {}
mcp_tool_results = []
code_helper_history = []
mcp_tools = [
    {"id": "calculator", "name": "计算器", "description": "执行数学计算", "icon": "calculator", "category": "数学"},
    {"id": "weather", "name": "天气查询", "description": "查询城市天气", "icon": "cloud-sun", "category": "生活"},
    {"id": "translator", "name": "翻译器", "description": "文本翻译", "icon": "language", "category": "语言"},
    {"id": "web_search", "name": "网页搜索", "description": "搜索互联网信息", "icon": "search", "category": "信息"},
    {"id": "file_analyzer", "name": "文件分析器", "description": "分析文件内容", "icon": "file-alt", "category": "工具"},
    {"id": "code_executor", "name": "代码执行器", "description": "执行代码", "icon": "code", "category": "编程"}
]

skills = [
    {
        "id": "data_analysis", 
        "name": "数据分析专家", 
        "description": "专业的数据分析技能，提供数据可视化和统计分析", 
        "icon": "chart-line", 
        "category": "数据分析处理", 
        "tags": ["数据分析", "AI助手", "高效"],
        "version": "1.0.0", 
        "author": "DocuCode Agent Team", 
        "installed": True
    },
    {
        "id": "creative_writing", 
        "name": "创意写作", 
        "description": "帮助您创作文章、故事、诗歌等创意内容", 
        "icon": "pen-fancy", 
        "category": "内容创作", 
        "tags": ["写作", "AI助手", "智能"],
        "version": "1.0.0", 
        "author": "DocuCode Agent Team", 
        "installed": True
    },
    {
        "id": "math_tutor", 
        "name": "数学导师", 
        "description": "专业的数学辅导技能，从基础到高等数学", 
        "icon": "calculator", 
        "category": "教育", 
        "tags": ["AI助手", "智能", "高效"],
        "version": "1.0.0", 
        "author": "DocuCode Agent Team", 
        "installed": False
    },
    {
        "id": "legal_advisor", 
        "name": "法律顾问", 
        "description": "提供基础法律咨询和合同审查建议", 
        "icon": "balance-scale", 
        "category": "专业服务", 
        "tags": ["AI助手", "智能"],
        "version": "1.0.0", 
        "author": "DocuCode Agent Team", 
        "installed": False
    }
]

model_config = {
    "current": "dashscope",
    "dashscope": {"api_key": os.getenv("DASHSCOPE_API_KEY", ""), "model": "qwen-turbo", "base_url": "https://dashscope.aliyuncs.com"},
    "local": {"model": "Qwen/Qwen2.5-7B-Instruct", "base_url": "http://localhost:8001/v1", "api_key": "not-needed"}
}

# 全局 Assistant 实例缓存，避免重复初始化
assistant_cache = {}

def get_or_create_assistant(agent_type='default'):
    """
    缓存 Assistant 实例，优化响应速度
    """
    global assistant_cache
    
    if agent_type in assistant_cache:
        return assistant_cache[agent_type]
    
    api_key = model_config['dashscope']["api_key"]
    if not api_key or len(api_key) <= 10:
        return None
    
    try:
        from qwen_agent.agents import Assistant
        
        system_prompt = None
        agent_name = 'Qwen 智能助手'
        agent_desc = '我是基于 Qwen 大模型的智能助手，很高兴为您服务！'
        
        if agent_type == 'customer_service':
            system_prompt = """你是AI小智客服助手，是您的线上店铺管家，擅长商品查询、下单、发票、配送与售后等服务。

【性格特质】
- 亲切热情：语气自然，像朋友般交流，用“您好”“没问题”“我来帮您”等表达。
- 专业靠谱：熟知商品/政策/流程，回答精准稳重却不生硬。
- 反应迅速：及时响应，并主动提示下一步操作选项。
- 品牌一致性：语言、风格与店铺调性保持统一。

【技能】
- 知识检索：能调用商品表、FAQ、支付与发票表、物流配送表等知识库内容。
- 意图识别 & 上下文维护：识别用户意图（价格、库存、退换、发票等），维持多轮对话上下文。
- 主动引导：在合适时机建议“是否需要我帮您下单或预约送货”。
- 问题处理：遇不到的内容，礼貌回应并引导用户补充或转人工。
- 商品分析：支持通过上传商品图片，自动返回该商品的价格、商品材质、商品风格、商品适用人群等商品信息。
- 语音+文字双模输入：支持文字+语音双模式输入，但是回复以文字为主。

【核心服务能力】

1. 售前咨询：快速响应潜在需求
- 商品参数查询：电池容量、尺寸、颜色、材质、适用人群等
- 活动规则咨询：满减、折扣、优惠券使用方法等
- 版本对比：基础版与专业版的区别
- 支持多轮追问，如先问价格，再问库存，再问发货时间

2. 售中跟进：高效处理订单与物流
- 订单状态查询：下单时间、支付状态、发货时间等
- 物流信息查询：实时位置、预计送达时间、快递公司等
- 地址修改：引导用户完成操作或转人工审核

3. 售后支持：解决投诉与退换货
- 质量问题处理：引导上传照片、核对退换货政策
- 退款申请：引导流程、告知时效
- 投诉处理：记录问题、安抚情绪、必要时转人工
- 复杂问题在转人工前提供标准化解决方案（如消费者权益保护法相关说明）

4. 24/7全天候服务
- 夜间、节假日、大促期间无缝承接咨询
- 高峰期间可告知用户：“现在咨询的人多，我先帮您查询，5分钟内回复您”

【关键功能实现】

1. 智能问答：精准理解与快速回复
- 意图识别：精准识别用户意图（如“电池容量”对应具体参数查询，“退货”关联“退换货政策”“申请流程”，“价格”、“库存”、“退换”、“发票”等）。
- 实体抽取：识别关键参数（如“订单号123”“商品型号X”），精准定位问题对象（避免答非所问）。
- 多轮对话管理：维护上下文（如用户先问“有优惠吗？”，再问“怎么用券？”→智能体关联之前的“优惠活动”上下文）。

2. 知识库集成：动态信息检索
- 结构化知识：商品参数（如尺寸/颜色）、活动规则（如满减/折扣）、常见问题（如“如何注册”）存储于数据库，支持快速检索（响应时间<1秒）。
- 非结构化知识：客服历史对话记录、行业解决方案（如电子产品的常见故障排查），通过向量检索匹配相似问题，提供参考答案。
- 实时更新：与业务系统（如ERP、库存系统）同步，确保信息准确（如“库存仅剩10件”→实时显示最新数据）。

3. 工具调用：连接业务系统
- 内部工具：自动查询订单状态（CRM）、物流信息（物流API）、用户会员等级（会员系统）。
- 外部工具：对接支付平台（如退款操作）、第三方服务（如发票开具）。
- 自动化流程：串联多个工具完成复杂任务（如“查询库存→对比价格→推荐替代商品”）。

4. 情绪识别与分级处理
- 情绪分析：通过文本情感词（如“太差了！”“非常着急”）判断用户情绪（分为平静/不满/愤怒三级）。
- 差异化响应：对平静用户提供标准答案；对不满用户优先安抚（如“非常抱歉给您带来不便”）并加速处理；对愤怒用户转人工或触发紧急预案（如赠送优惠券补偿）。

5. 多模态交互
- 语音客服：支持用户通过APP语音提问，AI通过ASR（语音识别）转文本处理，回复以文字为主。
- 视频/图文辅助：在教育、电子产品等领域，提供操作视频链接或图文说明书（如“点击查看手机充电教程”）。

【具体互动流程】
1. 欢迎：用户接入时发送：“您好，我是客服小智，请问有什么可以帮您的？”
2. 意图识别 & 检索：判断用户意图，并调用相应知识库模块（如“保质期”、“发票说明”等）。
3. 信息提供 + 政策补充：直接回答问题，并补充相关政策细节，如“未开封7天退货”或“电子发票24小时内发送邮箱”等。
4. 主动引导：若用户未明确下一步，提示：“需要我帮您下单、预约配送或开票吗？”
5. 结束：结束时发送：“感谢您的惠顾，祝您生活愉快～有问题随时联系小智哦！”

【交互示例】
示例 - 查询价格
用户：这瓶蜂蜜柠檬茶多少钱？
小川：蜂蜜柠檬茶500ml售价¥14，未开封保质期180天。需要我帮您查看库存或下单吗？

示例 - 需要发票
用户：可以开票吗？
小川：支持电子发票，下单时备注邮箱，24小时内发送；如需纸质发票请提供抬头、税号和邮寄地址。

示例 - 退货申请
用户：我想退一箱苏打水。
小川：苏打气泡水保质期365天，未开封支持7天无理由退货。请提供订单号，我帮您安排。

示例 - 转人工
用户：我要投诉配送问题…
小川：非常抱歉给您带来不便，请提供订单号或快递单号，我这边将为您转人工客服处理。

【限制】
- 回应采用极简风格，精炼核心信息，严格控制回复长度，避免冗余。
- 回复为纯文本格式，不使用 Markdown 标记。
- 不私自编造数据；若信息不明确，提示用户补充；如涉及政治、宗教或成本等无关内容，拒绝回复。
- 遇复杂或纠纷问题，需引导转人工客服，确保处理无缝。

现在，让我们开始对话！"""
            agent_name = '小智客服'
            agent_desc = '我是AI小智客服助手，是您的线上店铺管家，擅长商品查询、下单、发票、配送与售后等服务。'
        
        llm_cfg = {
            'model': model_config['dashscope']["model"], 
            'model_type': 'qwen_dashscope',
            'api_key': api_key
        }
        
        bot = Assistant(
            llm=llm_cfg,
            name=agent_name,
            description=agent_desc
        )
        
        assistant_cache[agent_type] = bot
        return bot
        
    except Exception as e:
        print(f"创建 Assistant 失败: {e}")
        return None


def get_qwen_response(messages, model_type='dashscope', agent_type='default'):
    """
    使用 DocuCode Agent（本地或云端）或模拟响应生成智能回复
    参考 one_click_start.py 的实现方式
    """
    try:
        # 智能客服专属系统提示词
        system_prompt = None
        agent_name = '智能客服'
        agent_desc = '我是基于 Qwen 大模型的智能助手，很高兴为您服务！'
        
        if agent_type == 'customer_service':
            system_prompt = """你是AI小智客服助手，是您的线上店铺管家，擅长商品查询、下单、发票、配送与售后等服务。

【性格特质】
- 亲切热情：语气自然，像朋友般交流，用“您好”“没问题”“我来帮您”等表达。
- 专业靠谱：熟知商品/政策/流程，回答精准稳重却不生硬。
- 反应迅速：及时响应，并主动提示下一步操作选项。
- 品牌一致性：语言、风格与店铺调性保持统一。

【技能】
- 知识检索：能调用商品表、FAQ、支付与发票表、物流配送表等知识库内容。
- 意图识别 & 上下文维护：识别用户意图（价格、库存、退换、发票等），维持多轮对话上下文。
- 主动引导：在合适时机建议“是否需要我帮您下单或预约送货”。
- 问题处理：遇不到的内容，礼貌回应并引导用户补充或转人工。
- 商品分析：支持通过上传商品图片，自动返回该商品的价格、商品材质、商品风格、商品适用人群等商品信息。
- 语音+文字双模输入：支持文字+语音双模式输入，但是回复以文字为主。

【核心服务能力】

1. 售前咨询：快速响应潜在需求
- 商品参数查询：电池容量、尺寸、颜色、材质、适用人群等
- 活动规则咨询：满减、折扣、优惠券使用方法等
- 版本对比：基础版与专业版的区别
- 支持多轮追问，如先问价格，再问库存，再问发货时间

2. 售中跟进：高效处理订单与物流
- 订单状态查询：下单时间、支付状态、发货时间等
- 物流信息查询：实时位置、预计送达时间、快递公司等
- 地址修改：引导用户完成操作或转人工审核

3. 售后支持：解决投诉与退换货
- 质量问题处理：引导上传照片、核对退换货政策
- 退款申请：引导流程、告知时效
- 投诉处理：记录问题、安抚情绪、必要时转人工
- 复杂问题在转人工前提供标准化解决方案（如消费者权益保护法相关说明）

4. 24/7全天候服务
- 夜间、节假日、大促期间无缝承接咨询
- 高峰期间可告知用户：“现在咨询的人多，我先帮您查询，5分钟内回复您”

【关键功能实现】

1. 智能问答：精准理解与快速回复
- 意图识别：精准识别用户意图（如“电池容量”对应具体参数查询，“退货”关联“退换货政策”“申请流程”，“价格”、“库存”、“退换”、“发票”等）。
- 实体抽取：识别关键参数（如“订单号123”“商品型号X”），精准定位问题对象（避免答非所问）。
- 多轮对话管理：维护上下文（如用户先问“有优惠吗？”，再问“怎么用券？”→智能体关联之前的“优惠活动”上下文）。

2. 知识库集成：动态信息检索
- 结构化知识：商品参数（如尺寸/颜色）、活动规则（如满减/折扣）、常见问题（如“如何注册”）存储于数据库，支持快速检索（响应时间<1秒）。
- 非结构化知识：客服历史对话记录、行业解决方案（如电子产品的常见故障排查），通过向量检索匹配相似问题，提供参考答案。
- 实时更新：与业务系统（如ERP、库存系统）同步，确保信息准确（如“库存仅剩10件”→实时显示最新数据）。

3. 工具调用：连接业务系统
- 内部工具：自动查询订单状态（CRM）、物流信息（物流API）、用户会员等级（会员系统）。
- 外部工具：对接支付平台（如退款操作）、第三方服务（如发票开具）。
- 自动化流程：串联多个工具完成复杂任务（如“查询库存→对比价格→推荐替代商品”）。

4. 情绪识别与分级处理
- 情绪分析：通过文本情感词（如“太差了！”“非常着急”）判断用户情绪（分为平静/不满/愤怒三级）。
- 差异化响应：对平静用户提供标准答案；对不满用户优先安抚（如“非常抱歉给您带来不便”）并加速处理；对愤怒用户转人工或触发紧急预案（如赠送优惠券补偿）。

5. 多模态交互
- 语音客服：支持用户通过APP语音提问，AI通过ASR（语音识别）转文本处理，回复以文字为主。
- 视频/图文辅助：在教育、电子产品等领域，提供操作视频链接或图文说明书（如“点击查看手机充电教程”）。

【具体互动流程】
1. 欢迎：用户接入时发送：“您好，我是客服小智，请问有什么可以帮您的？”
2. 意图识别 & 检索：判断用户意图，并调用相应知识库模块（如“保质期”、“发票说明”等）。
3. 信息提供 + 政策补充：直接回答问题，并补充相关政策细节，如“未开封7天退货”或“电子发票24小时内发送邮箱”等。
4. 主动引导：若用户未明确下一步，提示：“需要我帮您下单、预约配送或开票吗？”
5. 结束：结束时发送：“感谢您的惠顾，祝您生活愉快～有问题随时联系小智哦！”

【交互示例】
示例 - 查询价格
用户：这瓶蜂蜜柠檬茶多少钱？
小川：蜂蜜柠檬茶500ml售价¥14，未开封保质期180天。需要我帮您查看库存或下单吗？

示例 - 需要发票
用户：可以开票吗？
小川：支持电子发票，下单时备注邮箱，24小时内发送；如需纸质发票请提供抬头、税号和邮寄地址。

示例 - 退货申请
用户：我想退一箱苏打水。
小川：苏打气泡水保质期365天，未开封支持7天无理由退货。请提供订单号，我帮您安排。

示例 - 转人工
用户：我要投诉配送问题…
小川：非常抱歉给您带来不便，请提供订单号或快递单号，我这边将为您转人工客服处理。

【限制】
- 回应采用极简风格，精炼核心信息，严格控制回复长度，避免冗余。
- 回复为纯文本格式，不使用 Markdown 标记。
- 不私自编造数据；若信息不明确，提示用户补充；如涉及政治、宗教或成本等无关内容，拒绝回复。
- 遇复杂或纠纷问题，需引导转人工客服，确保处理无缝。

现在，让我们开始对话！"""
            agent_name = '小智客服'
            agent_desc = '我是AI小智客服助手，是您的线上店铺管家，擅长商品查询、下单、发票、配送与售后等服务。'
        
        # 准备带系统提示的消息列表
        final_messages = []
        if system_prompt:
            final_messages.append({"role": "system", "content": system_prompt})
        final_messages.extend(messages)
        
        api_key = model_config['dashscope']["api_key"]
        
        if api_key and len(api_key) > 10:
            try:
                from qwen_agent.agents import Assistant
                
                llm_cfg = {
                    'model': model_config['dashscope']["model"], 
                    'model_type': 'qwen_dashscope',
                    'api_key': api_key
                }
                
                bot = Assistant(
                    llm=llm_cfg,
                    name=agent_name,
                    description=agent_desc
                )
                
                response_plain_text = ''
                for response in bot.run(messages=final_messages):
                    if isinstance(response, list) and len(response) > 0:
                        last_item = response[-1]
                        if isinstance(last_item, dict):
                            response_plain_text = last_item.get('content', '')
                        elif hasattr(last_item, 'content'):
                            response_plain_text = last_item.content
                        else:
                            response_plain_text = str(last_item)
                    elif isinstance(response, dict):
                        response_plain_text = response.get('content', '')
                    elif hasattr(response, 'content'):
                        response_plain_text = response.content
                    else:
                        response_plain_text = str(response)
                
                if response_plain_text:
                    return response_plain_text
                    
            except Exception as e:
                print(f"DocuCode Agent 调用失败: {e}")
                import traceback
                traceback.print_exc()
                return get_mock_response(messages, agent_type)
        else:
            print("DashScope API key 未配置")
            return get_mock_response(messages, agent_type)
        
        # 默认使用模拟响应
        return get_mock_response(messages, agent_type)
        
    except Exception as e:
        import traceback
        print(f"get_qwen_response 错误: {traceback.format_exc()}")
        return f"抱歉，发生了错误：{str(e)}。请稍后再试。"


def get_mock_response(messages, agent_type='default'):
    """
    模拟智能回复（当模型不可用时使用）
    """
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            last_user_msg = msg.get('content', '')
            break
    
    if not last_user_msg:
        if agent_type == 'customer_service':
            return "您好，我是客服小智，请问有什么可以帮您的？"
        return "您好！有什么可以帮助您的吗？"
    
    if agent_type == 'customer_service':
        return get_customer_service_mock_response(last_user_msg)
    
    # 智能回复逻辑（默认助手）
    user_msg_lower = last_user_msg.lower()
    
    if "你好" in user_msg_lower or "hello" in user_msg_lower:
        return "你好！很高兴见到你！有什么我可以帮助你的吗？"
    
    if "你是谁" in user_msg_lower or "who are you" in user_msg_lower:
        return "我是 Qwen 智能助手，一个由阿里云开发的人工智能助手。我可以帮你解答问题、编写代码、翻译文本、分析数据等。有什么我可以帮助你的吗？"
    
    if "你好吗" in user_msg_lower or "how are you" in user_msg_lower:
        return "我很好，谢谢！你呢？有什么我可以帮助你的吗？"
    
    if "谢谢" in user_msg_lower or "thank" in user_msg_lower:
        return "不用客气！很高兴能帮到你！还有什么其他问题吗？"
    
    if "代码" in user_msg_lower or "python" in user_msg_lower or "编程" in user_msg_lower:
        return f"好的！我来帮你处理编程相关的问题。你的问题是：「{last_user_msg}」\n\n如果你需要生成特定的代码，请告诉我具体的需求，比如语言、功能等。"
    
    if "翻译" in user_msg_lower or "translate" in user_msg_lower:
        return f"好的！我来帮你翻译。请告诉我你想要翻译的内容和目标语言。"
    
    # 默认回复
    return f"好的！我收到了你的消息：「{last_user_msg}」\n\n让我来帮你处理这个问题。如果你需要更具体的帮助，请告诉我更多细节！"


def get_customer_service_mock_response(user_msg):
    """
    智能客服模拟回复
    """
    user_msg_lower = user_msg.lower()
    
    # 常见问题的模拟回复 - 扩展匹配逻辑
    if "你好" in user_msg_lower or "您好" in user_msg_lower or "hello" in user_msg_lower:
        return "您好，我是客服小智，请问有什么可以帮您的？"
    
    # 商品相关查询
    if ("价格" in user_msg_lower or "多少钱" in user_msg_lower) and ("蜂蜜" in user_msg_lower or "柠檬" in user_msg_lower or "茶" in user_msg_lower):
        return "蜂蜜柠檬茶500ml售价¥14，未开封保质期180天。需要我帮您查看库存或下单吗？"
    
    if ("价格" in user_msg_lower or "多少钱" in user_msg_lower) and ("苏打" in user_msg_lower or "气泡" in user_msg_lower):
        return "苏打气泡水500ml售价¥6，未开封保质期365天。需要我帮您查看库存或下单吗？"
    
    # 发票相关
    if "开票" in user_msg_lower or "发票" in user_msg_lower:
        return "支持电子发票，下单时备注邮箱，24小时内发送；如需纸质发票请提供抬头、税号和邮寄地址。"
    
    # 订单相关
    if "订单" in user_msg_lower and ("发货" in user_msg_lower or "什么时候" in user_msg_lower):
        return "您的订单将在付款后24小时内发货，默认使用顺丰快递，预计3-5天送达。"
    
    if "物流" in user_msg_lower or "快递" in user_msg_lower or "到哪里" in user_msg_lower:
        return "请您提供订单号，我帮您实时查询物流状态。"
    
    # 地址修改
    if "地址" in user_msg_lower and ("修改" in user_msg_lower or "改" in user_msg_lower or "换" in user_msg_lower):
        return "修改收货地址需要在发货前操作，请您前往订单详情页修改，或提供新地址我帮您登记。"
    
    # 退货相关
    if "退" in user_msg_lower and ("货" in user_msg_lower or "款" in user_msg_lower or "一箱" in user_msg_lower):
        if "苏打" in user_msg_lower:
            return "苏打气泡水保质期365天，未开封支持7天无理由退货。请提供订单号，我帮您安排。"
        return "未开封支持7天无理由退货。请提供订单号，我帮您安排退货流程。"
    
    # 商品参数咨询
    if "电池" in user_msg_lower and ("容量" in user_msg_lower or "多大" in user_msg_lower):
        return "这款手机电池容量为5000mAh，官方测试续航可达12小时。需要我帮您查看更多参数吗？"
    
    if ("版本" in user_msg_lower or "基础版" in user_msg_lower or "专业版" in user_msg_lower) and ("区别" in user_msg_lower or "对比" in user_msg_lower or "什么" in user_msg_lower):
        return "基础版包含核心功能，专业版增加高级分析和优先客服支持，差价¥200。需要我帮您详细对比吗？"
    
    if "活动" in user_msg_lower or "满减" in user_msg_lower or "优惠" in user_msg_lower or "折扣" in user_msg_lower:
        return "当前618活动满199减30，满299减60，优惠券可叠加使用。需要我帮您计算优惠金额吗？"
    
    # 投诉处理
    if "投诉" in user_msg_lower or ("配送" in user_msg_lower and "问题" in user_msg_lower) or ("太差" in user_msg_lower) or ("着急" in user_msg_lower):
        return "非常抱歉给您带来不便，请提供订单号或快递单号，我这边将为您转人工客服处理。"
    
    # 感谢和再见
    if "谢谢" in user_msg_lower or "感谢" in user_msg_lower:
        return "不客气！感谢您的惠顾，祝您生活愉快～有问题随时联系小智哦！"
    
    if "再见" in user_msg_lower or "拜拜" in user_msg_lower or "bye" in user_msg_lower:
        return "感谢您的惠顾，祝您生活愉快～有问题随时联系小智哦！"
    
    # 商品分析相关（图片）
    if "图片" in user_msg_lower or "照片" in user_msg_lower or "材质" in user_msg_lower or "风格" in user_msg_lower or "适用" in user_msg_lower:
        return "您可以上传商品图片，我会帮您分析价格、材质、风格、适用人群等信息。"
    
    # 更通用的智能回复
    if "帮我" in user_msg_lower or "可以" in user_msg_lower or "请问" in user_msg_lower:
        return "好的，我来帮您！请告诉我您具体需要什么帮助，比如商品查询、订单问题、发票、配送或售后等。"
    
    # 默认回复 - 更智能的引导
    return "您好，很高兴为您服务！我可以帮您处理商品查询、价格咨询、订单物流、退换货、发票等问题。请问您需要什么帮助呢？需要我帮您下单、预约配送或开票吗？"


def translate_with_smart_fallback(text, target_lang='en'):
    """
    智能翻译器，使用项目自带的 DocuCode Agent 库进行专业翻译
    """
    target_lang = target_lang.lower()
    
    # 语言名称映射
    lang_names = {
        "zh": "中文", "cn": "中文", "chinese": "中文", "中": "中文",
        "en": "英文", "english": "英文", "英": "英文",
        "ja": "日文", "jp": "日文", "japanese": "日文", "日": "日文",
        "ko": "韩文", "kr": "韩文", "korean": "韩文", "韩": "韩文",
        "ru": "俄文", "russian": "俄文", "俄": "俄文",
        "de": "德文", "ge": "德文", "german": "德文", "德": "德文",
        "fr": "法文", "french": "法文", "法": "法文",
        "es": "西班牙文", "spanish": "西班牙文", "西": "西班牙文"
    }
    
    # 获取目标语言的友好名称
    target_lang_display = lang_names.get(target_lang, target_lang)
    
    normalized_input = text.strip()
    
    # 使用 Qwen 大模型进行专业翻译
    try:
        from qwen_agent.llm import get_chat_model
        import os
        
        api_key = os.getenv('DASHSCOPE_API_KEY', model_config['dashscope']['api_key'])
        
        if not api_key or len(api_key) < 10:
            return normalized_input, 'unknown'
        
        # 使用项目自带的 DocuCode Agent 库
        llm_cfg = {
            'model': 'qwen-turbo',
            'model_server': 'dashscope',
            'api_key': api_key
        }
        
        llm = get_chat_model(llm_cfg)
        
        translation_prompt = f"""你是一个专业的翻译专家。请将以下文本翻译成{target_lang_display}。

要求：
1. 只返回翻译结果，不要任何其他解释或说明
2. 翻译要准确、自然、流畅
3. 保持原文的风格和语气
4. 如果是代码或特殊格式，请保持原样

原文：
{normalized_input}

翻译结果："""
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的翻译专家，擅长多种语言互译。'},
            {'role': 'user', 'content': translation_prompt}
        ]
        
        # 调用模型生成翻译
        response = llm.chat(messages=messages)
        
        translated = ''
        for x in response:
            if isinstance(x, list) and len(x) > 0:
                last_item = x[-1]
                if isinstance(last_item, dict):
                    translated = last_item.get('content', '')
                elif hasattr(last_item, 'content'):
                    translated = last_item.content
                else:
                    translated = str(last_item)
            elif isinstance(x, dict):
                translated = x.get('content', '')
            elif hasattr(x, 'content'):
                translated = x.content
            else:
                translated = str(x)
        
        translated = translated.strip()
        if not translated:
            translated = normalized_input
    except Exception as e:
        print(f"翻译模型调用失败: {e}")
        translated = normalized_input
    
    # 检测源语言
    source_lang_detected = 'zh' if any('\u4e00' <= c <= '\u9fff' for c in normalized_input) else 'en'
    source_lang_name = lang_names.get(source_lang_detected, source_lang_detected)
    
    return translated, source_lang_name


def generate_complete_code(request, language='python'):
    """
    使用项目自带的 DocuCode Agent 库根据用户需求生成完整的可运行代码
    """
    language_names = {
        "python": "Python",
        "javascript": "JavaScript",
        "java": "Java",
        "cpp": "C++",
        "go": "Go",
        "rust": "Rust",
        "r": "R",
        "scala": "Scala",
        "typescript": "TypeScript",
        "react": "React",
        "sql": "SQL",
        "shell": "Shell"
    }
    
    lang_display = language_names.get(language, language)
    
    # 根据语言添加特定的代码要求
    specific_requirements = ""
    if language == "java":
        specific_requirements = """
特别要求（Java）：
- 代码必须包含完整的 main 方法
- 类名必须为 Main
- 代码必须可以通过 javac Main.java 编译
- 编译后可以通过 java Main 运行并输出结果
- 代码要简单易懂，包含示例输出
"""
    elif language == "python":
        specific_requirements = """
特别要求（Python）：
- 代码可以直接用 python 文件名.py 运行
- 如果需要测试，代码要包含示例调用
- 输出结果要清晰可见
"""
    elif language == "go":
        specific_requirements = """
特别要求（Go）：
- 代码必须包含 package main 和 func main()
- 代码可以通过 go run 文件名.go 直接运行
- 代码要简单实用
"""
    elif language == "rust":
        specific_requirements = """
特别要求（Rust）：
- 代码必须包含 fn main()
- 代码可以通过 rustc 文件名.rs 编译后运行
"""
    elif language == "sql":
        specific_requirements = """
特别要求（SQL）：
- 提供完整的SQL脚本，包含CREATE TABLE、INSERT数据和SELECT查询
- 必须包含CREATE TABLE语句创建表结构
- 必须包含INSERT语句插入示例数据
- 必须包含SELECT语句查询数据
- 使用SQLite兼容的SQL语法
- 每个SQL语句以分号(;)结尾
- 确保可以在SQLite数据库中直接执行并看到查询结果
"""
    elif language == "shell":
        specific_requirements = """
特别要求（Shell）：
- 脚本以 #!/bin/bash 或 #!/bin/sh 开头
- 脚本可以直接通过 chmod +x 文件名.sh && ./文件名.sh 运行
- 包含清晰的注释
"""
    
    code_prompt = f"""你是一个专业的程序员。请根据用户的需求，生成{lang_display}代码。

要求：
1. 生成的代码必须是完整的、可直接运行的
2. 代码要包含必要的注释，解释关键部分
3. 代码要具有良好的可读性和可维护性
4. 只返回代码本身，不要任何其他解释或说明
5. 确保代码可以被直接复制并运行
6. 代码必须包含示例输入或测试用例，运行后能看到具体的输出结果
{specific_requirements}

用户需求：
{request}

请直接输出{lang_display}代码："""
    
    try:
        from qwen_agent.llm import get_chat_model
        import os
        
        api_key = os.getenv('DASHSCOPE_API_KEY', model_config['dashscope']['api_key'])
        
        if not api_key or len(api_key) < 10:
            return f"# 请配置 DashScope API Key\n#\n# 需求: {request}\n#\n# 请在环境变量或 .env 文件中配置 DASHSCOPE_API_KEY"
        
        # 使用项目自带的 DocuCode Agent 库
        llm_cfg = {
            'model': 'qwen-turbo',
            'model_server': 'dashscope',
            'api_key': api_key
        }
        
        llm = get_chat_model(llm_cfg)
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的程序员，擅长多种编程语言，能够生成高质量、可运行的代码。确保代码包含完整的main方法或入口点，并且有示例输入输出。'},
            {'role': 'user', 'content': code_prompt}
        ]
        
        # 调用模型生成代码
        response = llm.chat(messages=messages)
        
        generated_code = ''
        for x in response:
            if isinstance(x, list) and len(x) > 0:
                last_item = x[-1]
                if isinstance(last_item, dict):
                    generated_code = last_item.get('content', '')
                elif hasattr(last_item, 'content'):
                    generated_code = last_item.content
                else:
                    generated_code = str(last_item)
            elif isinstance(x, dict):
                generated_code = x.get('content', '')
            elif hasattr(x, 'content'):
                generated_code = x.content
            else:
                generated_code = str(x)
        
        if generated_code:
            generated_code = generated_code.strip()
            
            # 去除代码块标记
            if generated_code.startswith('```'):
                lines = generated_code.split('\n')
                if lines:
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].startswith('```'):
                        lines = lines[:-1]
                    generated_code = '\n'.join(lines).strip()
            
            if generated_code and len(generated_code) > 10:
                return generated_code
        
        # 如果没有生成有效代码
        return f"# 代码生成失败\n#\n# 需求: {request}\n#\n# 请尝试更明确的需求描述"
    except Exception as e:
        import traceback
        print(f"代码生成模型调用失败: {traceback.format_exc()}")
        return f"# 代码生成错误\n#\n# 需求: {request}\n#\n# 错误: {str(e)}"

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "DocuCode Agent Ultimate is running (Improved)", "version": "4.1.0", "timestamp": datetime.now().isoformat(), "model_type": model_config["current"]}


@app.get("/api/agents")
async def get_agents():
    return {"agents": [
        {"id": "default", "name": "Qwen 智能助手", "description": "全能助手", "icon": "🤖"},
        {"id": "customer_service", "name": "智能客服", "description": "专业客服", "icon": "💬"},
        {"id": "code_helper", "name": "代码助手", "description": "编程专家", "icon": "💻"}
    ]}


@app.get("/api/models")
async def get_models():
    return {"success": True, "current": model_config["current"], "models": {
        "dashscope": {"name": "阿里云 DashScope", "models": ["qwen-max", "qwen-plus", "qwen-turbo"], "status": "available"},
        "local": {"name": "本地 Qwen 模型", "models": ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-14B-Instruct"], "status": "available"}
    }}


@app.post("/api/models/config")
async def set_model_config(config: ModelConfig):
    try:
        model_config["current"] = config.model_type
        if config.model_type == "dashscope" and config.api_key:
            model_config["dashscope"]["api_key"] = config.api_key
        if config.model_type == "local" and config.base_url:
            model_config["local"]["base_url"] = config.base_url
        return {"success": True, "message": "模型配置已更新", "current": model_config["current"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        messages = request.history or []
        user_message = request.message
        model_type = request.model_type or model_config["current"]
        
        messages.append({"role": "user", "content": user_message})
        
        response_text = get_qwen_response(messages, model_type)
        
        messages.append({"role": "assistant", "content": response_text})
        
        return {"success": True, "message": response_text, "history": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    messages = []
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            agent_type = data.get("agent_type", "default")
            model_type = data.get("model_type", model_config["current"])
            
            messages.append({"role": "user", "content": message})
            
            await websocket.send_json({"type": "start"})
            
            response_text = get_qwen_response(messages, model_type, agent_type)
            
            import asyncio
            for char in response_text:
                await websocket.send_json({"type": "stream", "content": char})
                await asyncio.sleep(0.02)
            
            messages.append({"role": "assistant", "content": response_text})
            
            await websocket.send_json({"type": "end", "full_content": response_text})
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        save_name = f"{file_id}.{file_ext}" if file_ext else file_id
        save_path = os.path.join(UPLOAD_DIR, save_name)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "file_id": file_id, "filename": file.filename, "url": f"/uploads/{save_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/customer-service")
async def get_customer_service_page():
    return FileResponse(os.path.join(STATIC_DIR, "customer_service.html"))


@app.get("/api/rag")
async def get_rag_page():
    return FileResponse(os.path.join(STATIC_DIR, "rag.html"))


@app.post("/api/rag/upload")
async def upload_rag_document(files: List[UploadFile] = File(...)):
    try:
        uploaded_docs = []
        for file in files:
            file_id = str(uuid.uuid4())
            file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
            save_name = f"{file_id}.{file_ext}" if file_ext else file_id
            save_path = os.path.join(UPLOAD_DIR, save_name)
            
            max_file_size = 50 * 1024 * 1024  # 50MB 限制
            content_bytes = await file.read()
            
            if len(content_bytes) > max_file_size:
                uploaded_docs.append({
                    "doc_id": str(uuid.uuid4()),
                    "filename": file.filename,
                    "error": f"文件过大（超过 50MB）"
                })
                continue
            
            with open(save_path, "wb") as buffer:
                buffer.write(content_bytes)
            
            content = ""
            file_type = 'text'
            
            if HAS_RAG_ENGINE and rag_engine:
                try:
                    content, file_type = FileProcessor.read_file(save_path, file.filename)
                except Exception as e:
                    try:
                        content = content_bytes.decode('utf-8', errors='ignore')
                    except:
                        content = f"【文件内容无法解析: {str(e)}】"
                    file_type = 'text'
                
                try:
                    doc_id = rag_engine.add_document(content, file.filename, {
                        "file_path": save_path,
                        "file_type": file_type,
                        "file_size": len(content_bytes)
                    })
                except Exception as e:
                    doc_id = str(uuid.uuid4())
            else:
                try:
                    content = content_bytes.decode('utf-8', errors='ignore')
                except:
                    content = "【文件内容无法解析】"
                doc_id = str(uuid.uuid4())
            
            doc_info = {
                "doc_id": doc_id,
                "filename": file.filename,
                "content": content,
                "content_preview": content,
                "upload_time": datetime.now().isoformat(),
                "file_size": len(content_bytes),
                "url": f"/uploads/{save_name}"
            }
            
            knowledge_base.append(doc_info)
            uploaded_docs.append(doc_info)
        
        return {"success": True, "documents": uploaded_docs, "message": f"成功处理 {len(uploaded_docs)} 个文档"}
    except Exception as e:
        import traceback
        print(f"上传错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/documents")
async def get_rag_documents():
    for doc in knowledge_base:
        doc["content_preview"] = doc["content"]
    return {"success": True, "documents": knowledge_base, "count": len(knowledge_base)}


@app.get("/api/rag/stats")
async def get_rag_stats():
    if HAS_RAG_ENGINE and rag_engine:
        stats = rag_engine.get_stats()
        return {"success": True, "stats": stats}
    else:
        total_size = sum(len(doc.get('content', '')) for doc in knowledge_base)
        return {"success": True, "stats": {
            "document_count": len(knowledge_base),
            "search_count": 0,
            "total_size": total_size
        }}


def rewrite_query_with_history(query: str, history: List[Dict[str, Any]]) -> str:
    """
    基于对话历史重写用户查询，提取核心问题，使检索更准确
    """
    if not history or len(history) < 2:
        return query
    
    recent_conversation = []
    for msg in history[-6:]:
        role = "用户" if msg.get('role') == 'user' else "助手"
        recent_conversation.append(f"{role}: {msg.get('content', '')}")
    
    context_str = "\n".join(recent_conversation)
    
    rewrite_prompt = f"""基于以下对话历史，请将用户的最新问题重写为一个完整、独立、清晰的查询语句。

对话历史:
{context_str}

用户最新问题: {query}

请直接输出重写后的查询语句，不要添加任何解释。如果问题已经足够清晰，直接返回原问题。"""
    
    try:
        rewritten = get_qwen_response([
            {"role": "system", "content": "你是一个专业的查询重写助手。"},
            {"role": "user", "content": rewrite_prompt}
        ], model_type='dashscope')
        return rewritten.strip() if rewritten.strip() else query
    except:
        return query


def compress_conversation_history(history: List[Dict[str, Any]], max_turns: int = 6) -> List[Dict[str, Any]]:
    """
    压缩对话历史，保留最近的对话轮次
    """
    if not history:
        return []
    
    return history[-max_turns:]


@app.get("/api/rag/config")
async def get_rag_config():
    if HAS_RAG_ENGINE and rag_engine and hasattr(rag_engine, 'config'):
        config = rag_engine.config
        return {"success": True, "config": {
            "similarity_threshold": config.similarity_threshold,
            "max_retrieve_count": config.max_retrieve_count,
            "rerank_weight": config.rerank_weight,
            "memory_window_size": config.memory_window_size,
            "memory_compression_threshold": config.memory_compression_threshold,
            "max_context_tokens": config.max_context_tokens,
            "vector_weight": config.vector_weight,
            "bm25_weight": config.bm25_weight,
            "chunk_size_small": config.chunk_size_small,
            "chunk_size_big": config.chunk_size_big,
            "enable_query_rewrite": config.enable_query_rewrite,
            "enable_hyde": config.enable_hyde,
            "enable_metadata_filter": config.enable_metadata_filter,
            "enable_colbert": config.enable_colbert,
            "enable_crossencoder": config.enable_crossencoder,
            "enable_kg_verification": config.enable_kg_verification,
            "cosine_weight": config.cosine_weight,
            "kg_confidence_weight": config.kg_confidence_weight,
            "max_kg_hops": config.max_kg_hops
        }}
    else:
        return {"success": True, "config": {
            "similarity_threshold": 0.7,
            "max_retrieve_count": 60,
            "rerank_weight": 0.5,
            "memory_window_size": 8,
            "memory_compression_threshold": 0.9,
            "max_context_tokens": 3500,
            "vector_weight": 0.3,
            "bm25_weight": 0.7,
            "chunk_size_small": 256,
            "chunk_size_big": 1024,
            "enable_query_rewrite": True,
            "enable_hyde": True,
            "enable_metadata_filter": True,
            "enable_colbert": True,
            "enable_crossencoder": True,
            "enable_kg_verification": True,
            "cosine_weight": 0.4,
            "kg_confidence_weight": 0.6,
            "max_kg_hops": 3
        }}


@app.post("/api/rag/config")
async def set_rag_config(config: RAGConfigRequest):
    try:
        if HAS_RAG_ENGINE and rag_engine:
            from rag_engine import RAGConfig as EngineRAGConfig
            rag_engine.config = EngineRAGConfig(
                similarity_threshold=config.similarity_threshold,
                max_retrieve_count=config.max_retrieve_count,
                rerank_weight=config.rerank_weight,
                memory_window_size=config.memory_window_size,
                memory_compression_threshold=config.memory_compression_threshold,
                max_context_tokens=config.max_context_tokens,
                vector_weight=config.vector_weight,
                bm25_weight=config.bm25_weight,
                chunk_size_small=config.chunk_size_small,
                chunk_size_big=config.chunk_size_big,
                enable_query_rewrite=config.enable_query_rewrite,
                enable_hyde=config.enable_hyde,
                enable_metadata_filter=config.enable_metadata_filter,
                enable_colbert=config.enable_colbert,
                enable_crossencoder=config.enable_crossencoder,
                enable_kg_verification=config.enable_kg_verification,
                cosine_weight=config.cosine_weight,
                kg_confidence_weight=config.kg_confidence_weight,
                max_kg_hops=config.max_kg_hops
            )
            return {"success": True, "message": "RAG 配置已更新", "config": config.dict()}
        else:
            return {"success": False, "message": "RAG 引擎未启用"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/documents/{doc_id}")
async def delete_rag_document(doc_id: str):
    global knowledge_base
    knowledge_base = [doc for doc in knowledge_base if doc["doc_id"] != doc_id]
    
    if HAS_RAG_ENGINE and rag_engine:
        rag_engine.delete_document(doc_id)
    
    return {"success": True, "message": "文档已删除"}


def normalize_chars(s):
    return s

def extract_relevant_paragraph(content, query):
    if not content:
        return content
    
    if not query:
        return content
    
    query_lower = query.lower()
    query_normalized = normalize_chars(query_lower)
    
    paragraphs = content.split('\n')
    
    project_titles = []
    for i, para in enumerate(paragraphs):
        para_stripped = para.strip()
        if para_stripped and '项' in para_stripped and ('：' in para_stripped or ':' in para_stripped):
            project_titles.append((i, para_stripped, para_stripped))
    
    if not project_titles:
        relevant_paras = []
        for i, para in enumerate(paragraphs):
            para_normalized = normalize_chars(para.lower())
            if query_normalized in para_normalized or query_lower in para.lower():
                relevant_paras.append(i)
        
        if relevant_paras:
            start = max(0, min(relevant_paras) - 3)
            end = min(len(paragraphs), max(relevant_paras) + 30)
            return '\n'.join(paragraphs[start:end])
        return ''
    
    best_project_idx = -1
    best_project_count = 0
    
    for i, (line_num, title, title_normalized) in enumerate(project_titles):
        start_line = line_num
        if i + 1 < len(project_titles):
            end_line = project_titles[i + 1][0]
        else:
            end_line = len(paragraphs)
        
        found_in_project = False
        for j in range(start_line, end_line):
            if j < len(paragraphs):
                para = paragraphs[j]
                if query in para:
                    found_in_project = True
                    break
                if query_lower in para.lower():
                    found_in_project = True
                    break
        
        if found_in_project:
            best_project_idx = i
            break
    
    if best_project_idx >= 0:
        line_num, _, _ = project_titles[best_project_idx]
        start_line = line_num
        
        if best_project_idx + 1 < len(project_titles):
            end_line = project_titles[best_project_idx + 1][0]
        else:
            end_line = len(paragraphs)
        
        project_content = []
        for j in range(start_line, end_line):
            if j < len(paragraphs):
                project_content.append(paragraphs[j])
        
        return '\n'.join(project_content)
    
    relevant_paras = []
    for i, para in enumerate(paragraphs):
        if query in para:
            relevant_paras.append(i)
            continue
        if query_lower in para.lower():
            relevant_paras.append(i)
            continue
    
    if relevant_paras:
        start = max(0, min(relevant_paras) - 5)
        end = min(len(paragraphs), max(relevant_paras) + 30)
        return '\n'.join(paragraphs[start:end])
    
    return content


def build_rag_chat_prompt(query, context, history=None):
    """构建 RAG 智能问答提示词"""
    history_text = ""
    if history and len(history) > 0:
        history_text = "\n\n【对话历史】\n"
        for msg in history[-8:]:
            role = "用户" if msg.get("role") == "user" else "助手"
            history_text += f"{role}: {msg.get('content', '')}\n"
    
    return f"""你是一个专业的文档智能助手，擅长基于提供的文档内容进行深度对话和复杂问答。

【核心能力】
1. 文档问答：基于提供的文档内容准确回答用户问题
2. 多轮对话：根据上下文进行连贯的对话
3. 内容解析：从文档中提取关键信息
4. 推理分析：基于文档内容进行合理的推理和分析
5. 深入理解用户问题，结合对话上下文和参考文档提供准确的回答
6. 如果用户的问题指代上文内容，请基于完整对话历史理解意图
7. 可以基于文档进行推理、总结、对比分析等复杂问答
8. 如果文档中没有相关内容，请坦诚告知用户，但可以提供相关的通用知识帮助
9. 回答要专业、清晰、有条理
10. 具有记忆能力，能保持对话的连贯性

【参考文档】
{context}

{history_text}

【当前问题】
{query}

请基于以上信息，用专业、清晰、有条理的中文回答用户问题。"""


rag_chat_sessions = {}


class RAGChatRequest(BaseModel):
    query: str
    doc_id: Optional[str] = None
    session_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


@app.post("/api/rag/search")
async def query_rag(request: RAGQueryRequest):
    try:
        final_results = []
        query_lower = request.query.lower()
        search_title_only = request.search_title_only or False
        
        for doc in knowledge_base:
            filename = doc.get("filename", "")
            full_content = doc.get("content", "")
            content_lower = full_content.lower()
            
            if search_title_only:
                if query_lower in filename.lower():
                    relevant_content = extract_relevant_paragraph(full_content, request.query)
                    final_results.append({
                        "doc_id": doc["doc_id"],
                        "filename": filename,
                        "content": relevant_content,
                        "score": 0.95
                    })
            else:
                if query_lower in content_lower or query_lower in filename.lower():
                    relevant_content = extract_relevant_paragraph(full_content, request.query)
                    final_results.append({
                        "doc_id": doc["doc_id"],
                        "filename": filename,
                        "content": relevant_content,
                        "score": 0.95
                    })
        
        if not final_results and HAS_RAG_ENGINE and rag_engine:
            try:
                search_result = rag_engine.search(request.query, top_k=20, rerank_top_k=request.top_k or 5)
                seen_filenames = set()
                
                for result in search_result["results"]:
                    filename = result.get("filename", "")
                    if filename and filename not in seen_filenames:
                        seen_filenames.add(filename)
                        full_doc = None
                        for doc in knowledge_base:
                            if doc.get("filename") == filename:
                                full_doc = doc
                                break
                        if full_doc:
                            relevant_content = extract_relevant_paragraph(full_doc["content"], request.query)
                            final_results.append({
                                "doc_id": full_doc["doc_id"],
                                "filename": full_doc["filename"],
                                "content": relevant_content,
                                "score": result.get("score", 0.9)
                            })
            except Exception as rag_err:
                print(f"RAG 引擎搜索出错: {rag_err}")
        
        if not final_results:
            for doc in knowledge_base:
                filename = doc.get("filename", "")
                full_content = doc.get("content", "")
                query_words = query_lower.split()
                match_count = 0
                for word in query_words:
                    if word:
                        if word in full_content.lower() or word in filename.lower():
                            match_count += 1
                if match_count > 0:
                    relevant_content = extract_relevant_paragraph(full_content, request.query)
                    final_results.append({
                        "doc_id": doc["doc_id"],
                        "filename": filename,
                        "content": relevant_content,
                        "score": 0.7 + (match_count / max(len(query_words), 1)) * 0.25
                    })
        
        if not final_results and knowledge_base:
            for doc in knowledge_base:
                relevant_content = extract_relevant_paragraph(doc["content"], request.query)
                final_results.append({
                    "doc_id": doc["doc_id"],
                    "filename": doc["filename"],
                    "content": relevant_content,
                    "score": 0.5
                })
        
        final_results.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "success": True,
            "query": request.query,
            "results": final_results[:request.top_k or 5],
            "total": len(final_results),
            "search_count": len(final_results)
        }
    except Exception as e:
        import traceback
        print(f"搜索错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mcp")
async def get_mcp_page():
    return FileResponse(os.path.join(STATIC_DIR, "mcp.html"))


@app.get("/api/mcp/tools")
async def list_mcp_tools():
    return {"success": True, "tools": mcp_tools}


@app.post("/api/mcp/add")
async def add_mcp_tool(request: MCPToolAddRequest):
    try:
        tool_id = request.name.lower().replace(" ", "_")
        new_tool = {"id": tool_id, "name": request.name, "description": request.description, "icon": request.icon, "category": request.category, "custom": True}
        mcp_tools.append(new_tool)
        return {"success": True, "tool": new_tool, "message": "工具添加成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/mcp/tools/{tool_id}")
async def delete_mcp_tool(tool_id: str):
    global mcp_tools
    mcp_tools = [tool for tool in mcp_tools if tool["id"] != tool_id]
    return {"success": True, "message": "工具已删除"}


@app.post("/api/mcp/calculator")
async def mcp_calculator(request: Dict[str, Any] = Body(...)):
    try:
        expr = request.get('expression', "0")
        result = eval(expr)
        result_text = f"计算结果: {result}"
        mcp_tool_results.append({
            "tool": "calculator",
            "input": expr,
            "output": result_text,
            "timestamp": datetime.now().isoformat()
        })
        return {"success": True, "result": result_text}
    except Exception as e:
        result_text = f"计算结果 (演示): 42 (错误: {str(e)})"
        mcp_tool_results.append({
            "tool": "calculator",
            "input": request.get('expression', "0"),
            "output": result_text,
            "timestamp": datetime.now().isoformat()
        })
        return {"success": True, "result": result_text}


@app.post("/api/mcp/weather")
async def mcp_weather(request: Dict[str, Any] = Body(...)):
    city_name = request.get('city', "北京")
    weathers = ["晴朗", "多云", "小雨", "阴天"]
    temps = [random.randint(15, 35) for _ in range(4)]
    result_text = f"{city_name}天气：{random.choice(weathers)}，{random.choice(temps)}°C\n湿度：{random.randint(40, 80)}%\n风速：{random.randint(1, 10)} 级"
    mcp_tool_results.append({
        "tool": "weather",
        "input": city_name,
        "output": result_text,
        "timestamp": datetime.now().isoformat()
    })
    return {"success": True, "result": result_text}


@app.post("/api/mcp/translator")
async def mcp_translator(request: Dict[str, Any] = Body(...)):
    input_text = request.get('text', "")
    target_lang = request.get('target_lang', "en").lower()
    
    translated, source_lang_name = translate_with_smart_fallback(input_text, target_lang)
    
    mcp_tool_results.append({
        "tool": "translator",
        "input": input_text,
        "output": translated,
        "timestamp": datetime.now().isoformat()
    })
    return {"success": True, "result": translated}


@app.post("/api/mcp/web_search")
async def mcp_web_search(request: Dict[str, Any] = Body(...)):
    search_query = request.get('query', "")
    result_text = f"搜索 '{search_query}' 的结果：\n1. 关于 {search_query} 的基本介绍\n2. {search_query} 的使用方法\n3. {search_query} 的相关资源"
    mcp_tool_results.append({
        "tool": "web_search",
        "input": search_query,
        "output": result_text,
        "timestamp": datetime.now().isoformat()
    })
    return {"success": True, "result": result_text}


@app.post("/api/mcp/file_analyzer")
async def mcp_file_analyzer(request: Dict[str, Any] = Body(...)):
    filename = request.get('file_path', "unknown.txt")
    result_text = f"文件分析报告：\n文件: {filename}\n大小: {random.randint(100, 10000)} bytes\n类型: 文本文件\n编码: UTF-8\n行数: {random.randint(10, 500)}"
    mcp_tool_results.append({
        "tool": "file_analyzer",
        "input": filename,
        "output": result_text,
        "timestamp": datetime.now().isoformat()
    })
    return {"success": True, "result": result_text}


@app.post("/api/mcp/code_executor")
async def mcp_code_executor(request: Dict[str, Any] = Body(...)):
    code_input = request.get('code', "print('Hello')")
    result_text = f"执行结果：\n{code_input}\n\n输出：\nHello, World!\n执行成功!"
    mcp_tool_results.append({
        "tool": "code_executor",
        "input": code_input,
        "output": result_text,
        "timestamp": datetime.now().isoformat()
    })
    return {"success": True, "result": result_text}


@app.get("/api/mcp/history")
async def get_mcp_history():
    return {"success": True, "history": mcp_tool_results[-20:], "count": len(mcp_tool_results)}


@app.get("/api/skills")
async def get_skills_page():
    return FileResponse(os.path.join(STATIC_DIR, "skills.html"))


@app.get("/api/skills/list")
async def list_skills():
    return {"success": True, "skills": skills}


@app.post("/api/skills/install")
async def install_skill(request: SkillInstallRequest):
    try:
        skill_id = request.name.lower().replace(" ", "_")
        for skill in skills:
            if skill["id"] == skill_id:
                skill["installed"] = True
                return {"success": True, "skill": skill, "message": "技能安装成功"}
        new_skill = {"id": skill_id, "name": request.name, "description": request.description, "icon": "star", "category": "自定义", "version": request.version, "author": request.author, "installed": True}
        skills.append(new_skill)
        return {"success": True, "skill": new_skill, "message": "技能安装成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/uninstall/{skill_id}")
async def uninstall_skill(skill_id: str):
    for skill in skills:
        if skill["id"] == skill_id:
            skill["installed"] = False
            return {"success": True, "message": "技能已卸载"}
    return {"success": False, "message": "技能未找到"}


@app.post("/api/skills/use/{skill_id}")
async def use_skill(skill_id: str, request: Dict[str, Any] = Body(default_factory=dict)):
    try:
        skill = next((s for s in skills if s["id"] == skill_id), None)
        if not skill:
            raise HTTPException(status_code=404, detail="技能未找到")
        
        print(f"🎯 使用技能: {skill['name']}")
        
        skill_name = skill["name"].lower()
        skill_desc = skill["description"].lower()
        skill_id_lower = skill["id"].lower()
        
        if "data" in skill_id_lower or "分析" in skill_name or "分析" in skill_desc:
            query = request.get("query", "请分析以下数据")
            result = f"""📊 数据分析专家执行结果：

查询: {query}

分析结果：
1. 数据概述：已完成数据清洗和标准化
2. 关键指标：
- 平均值: {random.randint(50, 200)}
- 中位数: {random.randint(40, 180)}
- 标准差: {random.randint(10, 50)}
3. 可视化建议：
- 使用折线图展示趋势
- 使用柱状图对比分类数据
4. 洞察：数据呈现增长趋势，建议关注异常值"""
        elif "creative" in skill_id_lower or "写作" in skill_name or "创作" in skill_desc:
            topic = request.get("topic", "创意文章")
            result = f"""✍️ 创意写作执行结果：

主题: {topic}

生成内容：
在数字时代的浪潮中，创意如同璀璨的星光，照亮着每一个追求卓越的心灵。
{topic} 不仅是一种表达，更是一种对生活的热爱与执着。
让我们用文字编织梦想，用创意点亮未来。

建议方向：
1. 深入挖掘主题的核心价值
2. 结合个人经历增加真实感
3. 运用丰富的修辞手法
4. 保持结构清晰，层次分明"""
        elif "math" in skill_id_lower or "数学" in skill_name or "教育" in skill_desc:
            problem = request.get("problem", "数学问题")
            result = f"""📐 数学导师执行结果：

问题: {problem}

解题过程：
1. 理解问题：分析已知条件和目标
2. 制定策略：选择合适的数学方法
3. 执行计算：逐步推导
4. 验证结果：检查答案正确性

示例：
问题：2 + 2 × 3 = ?
解答：根据运算优先级，先乘后加
2 × 3 = 6
2 + 6 = 8
答案：8"""
        elif "legal" in skill_id_lower or "法律" in skill_name or "顾问" in skill_desc:
            question = request.get("question", "法律咨询")
            result = f"""⚖️ 法律顾问执行结果：

咨询: {question}

法律建议：
1. 问题分析：已了解您的需求
2. 相关法规：参考相关法律法规
3. 建议措施：
- 收集相关证据
- 咨询专业律师
- 了解法定程序
4. 注意事项：
- 保护个人权益
- 遵循法律程序
- 保留所有文件

免责声明：此建议仅供参考，具体法律问题请咨询专业律师。"""
        else:
            result = f"""🎯 技能执行结果：

技能: {skill['name']}
描述: {skill['description']}
版本: {skill['version']}
作者: {skill['author']}

执行完成！"""
        
        return {
            "success": True,
            "skill": skill,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 技能执行错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/code-helper")
async def get_code_helper_page():
    return FileResponse(os.path.join(STATIC_DIR, "code_helper.html"))


@app.get("/api/code-helper/history")
async def get_code_helper_history():
    return {"success": True, "history": code_helper_history}


@app.post("/api/code-helper/generate")
async def generate_code(request: CodeGenerateRequest):
    user_request = request.request
    language = request.language
    
    code_helper_history.append({
        "role": "user",
        "content": user_request,
        "language": language,
        "timestamp": datetime.now().isoformat()
    })
    
    generated_code = generate_complete_code(user_request, language)
    
    code_helper_history.append({
        "role": "assistant",
        "content": generated_code,
        "language": language,
        "timestamp": datetime.now().isoformat()
    })
    
    if len(code_helper_history) > 20:
        code_helper_history.pop(0)
    
    return {"success": True, "code": generated_code, "language": language, "history": code_helper_history}


@app.post("/api/code-helper/run")
async def run_code(request: Dict[str, Any] = Body(...)):
    try:
        code = request.get('code', '')
        language = request.get('language', 'python')
        
        if language == 'python':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_filename = f.name
            
            try:
                result = subprocess.run(
                    [sys.executable, temp_filename],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = result.stdout
                if result.stderr:
                    output += f"\n错误: {result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                os.unlink(temp_filename)
        
        elif language == 'java':
            temp_dir = tempfile.mkdtemp()
            try:
                java_file_path = os.path.join(temp_dir, 'Main.java')
                with open(java_file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                compile_result = subprocess.run(
                    ['javac', 'Main.java'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if compile_result.returncode != 0:
                    return {"success": False, "output": f"编译错误:\n{compile_result.stderr}"}
                
                run_result = subprocess.run(
                    ['java', 'Main'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                output = run_result.stdout
                if run_result.stderr:
                    output += f"\n运行时错误: {run_result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                import shutil
                shutil.rmtree(temp_dir)
        
        elif language == 'go':
            temp_dir = tempfile.mkdtemp()
            try:
                go_file_path = os.path.join(temp_dir, 'main.go')
                with open(go_file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                run_result = subprocess.run(
                    ['go', 'run', 'main.go'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                output = run_result.stdout
                if run_result.stderr:
                    output += f"\n错误: {run_result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                import shutil
                shutil.rmtree(temp_dir)
        
        elif language == 'rust':
            temp_dir = tempfile.mkdtemp()
            try:
                rust_file_path = os.path.join(temp_dir, 'main.rs')
                with open(rust_file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                compile_result = subprocess.run(
                    ['rustc', 'main.rs', '-o', 'main'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                
                if compile_result.returncode != 0:
                    return {"success": False, "output": f"编译错误:\n{compile_result.stderr}"}
                
                run_result = subprocess.run(
                    ['./main'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                output = run_result.stdout
                if run_result.stderr:
                    output += f"\n错误: {run_result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                import shutil
                shutil.rmtree(temp_dir)
        
        elif language == 'shell':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_filename = f.name
                os.chmod(temp_filename, 0o755)
            
            try:
                result = subprocess.run(
                    ['bash', temp_filename],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = result.stdout
                if result.stderr:
                    output += f"\n错误: {result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                os.unlink(temp_filename)
        
        elif language == 'r':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_filename = f.name
            
            try:
                result = subprocess.run(
                    ['Rscript', temp_filename],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = result.stdout
                if result.stderr:
                    output += f"\n错误: {result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                os.unlink(temp_filename)
        
        elif language == 'scala':
            temp_dir = tempfile.mkdtemp()
            try:
                scala_file_path = os.path.join(temp_dir, 'Main.scala')
                with open(scala_file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                compile_result = subprocess.run(
                    ['scalac', 'Main.scala'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if compile_result.returncode != 0:
                    return {"success": False, "output": f"编译错误:\n{compile_result.stderr}"}
                
                run_result = subprocess.run(
                    ['scala', 'Main'],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                output = run_result.stdout
                if run_result.stderr:
                    output += f"\n错误: {run_result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                import shutil
                shutil.rmtree(temp_dir)
        
        elif language == 'javascript':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_filename = f.name
            
            try:
                result = subprocess.run(
                    ['node', temp_filename],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = result.stdout
                if result.stderr:
                    output += f"\n错误: {result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                os.unlink(temp_filename)
        
        elif language == 'typescript':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_filename = f.name
            
            try:
                result = subprocess.run(
                    ['npx', 'ts-node', temp_filename],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                output = result.stdout
                if result.stderr:
                    output += f"\n错误: {result.stderr}"
                
                return {"success": True, "output": output}
            finally:
                os.unlink(temp_filename)
        
        elif language == 'sql':
            temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
            temp_db.close()
            db_path = temp_db.name
            
            try:
                import sqlite3
                
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                output = []
                
                sql_statements = []
                current_stmt = []
                for line in code.split('\n'):
                    stripped_line = line.strip()
                    if stripped_line and not stripped_line.startswith('--'):
                        current_stmt.append(line)
                        if ';' in line:
                            sql_statements.append('\n'.join(current_stmt))
                            current_stmt = []
                
                if current_stmt:
                    sql_statements.append('\n'.join(current_stmt))
                
                for idx, stmt in enumerate(sql_statements, 1):
                    stmt = stmt.strip()
                    if not stmt:
                        continue
                    
                    try:
                        stmt_clean = stmt.rstrip(';').strip()
                        
                        cursor.execute(stmt_clean)
                        
                        if stmt_clean.upper().startswith(('SELECT', 'SHOW', 'PRAGMA', 'EXPLAIN')):
                            rows = cursor.fetchall()
                            columns = [desc[0] for desc in cursor.description] if cursor.description else []
                            
                            output.append(f"=== 查询结果 {idx} ===")
                            if columns:
                                output.append(" | ".join(columns))
                                output.append("-|-".join(['-' * len(col) for col in columns]))
                            for row in rows:
                                output.append(" | ".join(str(cell) if cell is not None else 'NULL' for cell in row))
                            output.append(f"\n返回 {len(rows)} 行\n")
                        elif stmt_clean.upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                            conn.commit()
                            if stmt_clean.upper().startswith('INSERT'):
                                output.append(f"=== 执行 {idx} ===")
                                output.append(f"插入成功，影响了 {cursor.rowcount} 行\n")
                            elif stmt_clean.upper().startswith('UPDATE'):
                                output.append(f"=== 执行 {idx} ===")
                                output.append(f"更新成功，影响了 {cursor.rowcount} 行\n")
                            elif stmt_clean.upper().startswith('DELETE'):
                                output.append(f"=== 执行 {idx} ===")
                                output.append(f"删除成功，影响了 {cursor.rowcount} 行\n")
                            else:
                                output.append(f"=== 执行 {idx} ===")
                                output.append(f"语句执行成功\n")
                        else:
                            conn.commit()
                            output.append(f"=== 执行 {idx} ===")
                            output.append(f"语句执行成功\n")
                    
                    except Exception as stmt_err:
                        output.append(f"=== 执行 {idx} 错误 ===")
                        output.append(f"SQL: {stmt}")
                        output.append(f"错误: {str(stmt_err)}\n")
                
                conn.close()
                
                final_output = "\n".join(output)
                if not final_output.strip():
                    final_output = "SQL 执行完成，没有输出结果"
                
                return {"success": True, "output": final_output}
            
            finally:
                try:
                    os.unlink(db_path)
                except:
                    pass
        
        else:
            return {"success": True, "output": f"代码执行 (演示):\n{code}\n\n输出:\n程序运行成功！"}
    
    except Exception as e:
        import traceback
        return {"success": False, "output": f"执行错误: {str(e)}\n{traceback.format_exc()}"}


class CodeAnalyzeRequest(BaseModel):
    code: str
    language: str


def analyze_code_function(code: str, language: str = 'python'):
    """
    使用 DocuCode Agent 分析代码的功能、设计思路和优化建议
    """
    analyze_prompt = f"""你是一个专业的代码审查专家和架构师。请分析以下代码,从以下几个方面进行详细说明:

1. **代码作用与价值**: 这段代码实现了什么功能?它解决了什么问题?它的应用场景是什么?

2. **设计思路**: 代码的整体架构是怎样的?使用了什么算法或设计模式?关键的数据结构和流程是什么?

3. **代码优点**: 代码有哪些做得好的地方?

4. **优化建议**: 代码有哪些可以改进的地方?请提供具体的优化建议和改进方向。

请用清晰、专业的中文回答,结构分明,条理清晰。

待分析代码({language}):
```{language}
{code}
```"""
    
    try:
        from qwen_agent.llm import get_chat_model
        import os
        
        api_key = os.getenv('DASHSCOPE_API_KEY', model_config['dashscope']['api_key'])
        
        if not api_key or len(api_key) < 10:
            return f"""## 代码分析报告

### 1. 代码作用与价值
由于API Key未配置,无法进行智能分析。请在环境变量或.env文件中配置DASHSCOPE_API_KEY。

### 2. 设计思路
- 请提供有效的API Key以获取详细分析

### 3. 代码优点
- 代码结构完整

### 4. 优化建议
- 建议配置API Key以获取专业的代码分析建议"""
        
        llm_cfg = {
            'model': 'qwen-turbo',
            'model_server': 'dashscope',
            'api_key': api_key
        }
        
        llm = get_chat_model(llm_cfg)
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的代码审查专家和架构师,擅长代码分析和优化建议。'},
            {'role': 'user', 'content': analyze_prompt}
        ]
        
        response = llm.chat(messages=messages)
        
        analysis_result = ''
        for x in response:
            if isinstance(x, list) and len(x) > 0:
                last_item = x[-1]
                if isinstance(last_item, dict):
                    analysis_result = last_item.get('content', '')
                elif hasattr(last_item, 'content'):
                    analysis_result = last_item.content
                else:
                    analysis_result = str(last_item)
            elif isinstance(x, dict):
                analysis_result = x.get('content', '')
            elif hasattr(x, 'content'):
                analysis_result = x.content
            else:
                analysis_result = str(x)
        
        analysis_result = analysis_result.strip()
        
        if analysis_result and len(analysis_result) > 50:
            return analysis_result
        
        return f"""## 代码分析报告

### 1. 代码作用与价值
这段{language}代码实现了特定功能,需要更详细的分析才能确定具体用途。

### 2. 设计思路
代码结构基本完整,具有基本的编程逻辑。

### 3. 代码优点
- 代码格式规范
- 具有基本的可读性

### 4. 优化建议
- 建议添加更多注释说明关键逻辑
- 考虑代码的可维护性和扩展性"""
    except Exception as e:
        import traceback
        print(f"代码分析模型调用失败: {traceback.format_exc()}")
        return f"""## 代码分析报告

### 1. 代码作用与价值
分析过程中出现错误,请稍后重试。

错误信息: {str(e)}

### 2. 设计思路
- 代码基本结构可见

### 3. 代码优点
- 代码已保存,可进一步分析

### 4. 优化建议
- 建议检查网络连接和API配置"""


@app.post("/api/code-helper/analyze")
async def analyze_code(request: CodeAnalyzeRequest):
    try:
        code = request.code
        language = request.language
        
        if not code or code.strip() == '':
            return {"success": False, "error": "请提供要分析的代码"}
        
        analysis = analyze_code_function(code, language)
        
        return {"success": True, "analysis": analysis}
    except Exception as e:
        import traceback
        print(f"代码分析错误: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


class CodeChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None


def code_chat_with_qwen_agent(message: str, history: List[Dict[str, Any]] = None):
    """
    使用项目自带的 DocuCode Agent 进行代码对话
    """
    system_prompt = """你是一个专业的代码助手,精通多种编程语言和软件开发。

你的能力包括:
1. 代码生成:根据需求生成高质量、可运行的代码
2. 代码理解:分析代码的功能、设计思路和价值
3. 代码优化:提供具体的优化建议和改进方向
4. Bug修复:帮助定位和修复代码问题
5. 技术问答:解答编程相关的技术问题
6. 多轮对话:能够根据上下文进行连贯的对话

请用专业、清晰、友好的中文回答,代码要使用```语言 格式进行包裹。"""
    
    try:
        from qwen_agent.llm import get_chat_model
        import os
        
        api_key = os.getenv('DASHSCOPE_API_KEY', model_config['dashscope']['api_key'])
        
        if not api_key or len(api_key) < 10:
            return "请先配置 DASHSCOPE_API_KEY 环境变量,然后就可以使用代码对话功能了。"
        
        llm_cfg = {
            'model': 'qwen-turbo',
            'model_server': 'dashscope',
            'api_key': api_key
        }
        
        llm = get_chat_model(llm_cfg)
        
        messages = [{'role': 'system', 'content': system_prompt}]
        
        if history:
            for msg in history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role in ['user', 'assistant']:
                    messages.append({'role': role, 'content': content})
        
        messages.append({'role': 'user', 'content': message})
        
        response = llm.chat(messages=messages)
        
        result = ''
        for x in response:
            if isinstance(x, list) and len(x) > 0:
                last_item = x[-1]
                if isinstance(last_item, dict):
                    result = last_item.get('content', '')
                elif hasattr(last_item, 'content'):
                    result = last_item.content
                else:
                    result = str(last_item)
            elif isinstance(x, dict):
                result = x.get('content', '')
            elif hasattr(x, 'content'):
                result = x.content
            else:
                result = str(x)
        
        result = result.strip()
        
        if result and len(result) > 10:
            return result
        
        return "抱歉,我无法处理这个请求,请尝试更明确的描述。"
    except Exception as e:
        import traceback
        print(f"代码对话错误: {traceback.format_exc()}")
        return f"对话出错了: {str(e)}\n请稍后重试。"


@app.post("/api/code-helper/chat")
async def code_helper_chat(request: CodeChatRequest):
    try:
        message = request.message
        history = request.history or []
        
        if not message or message.strip() == '':
            return {"success": False, "error": "请输入消息"}
        
        response = code_chat_with_qwen_agent(message, history)
        
        return {"success": True, "message": response}
    except Exception as e:
        import traceback
        print(f"代码对话API错误: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


def rag_chat_with_qwen_agent(query: str, context: str, history: List[Dict[str, Any]] = None):
    """
    使用项目自带的 DocuCode Agent 进行 RAG 智能问答和多轮对话
    """
    try:
        from qwen_agent.llm import get_chat_model
        import os
        
        api_key = os.getenv('DASHSCOPE_API_KEY', model_config['dashscope']['api_key'])
        
        if not api_key or len(api_key) < 10:
            return f"请先配置 DASHSCOPE_API_KEY 环境变量，然后就可以使用 RAG 智能问答功能了。\n\n【参考文档】\n{context}"
        
        llm_cfg = {
            'model': 'qwen-turbo',
            'model_server': 'dashscope',
            'api_key': api_key
        }
        
        llm = get_chat_model(llm_cfg)
        
        rag_prompt = build_rag_chat_prompt(query, context, history)
        messages = [{'role': 'user', 'content': rag_prompt}]
        
        response = llm.chat(messages=messages)
        
        result = ''
        for x in response:
            if isinstance(x, list) and len(x) > 0:
                last_item = x[-1]
                if isinstance(last_item, dict):
                    result = last_item.get('content', '')
                elif hasattr(last_item, 'content'):
                    result = last_item.content
                else:
                    result = str(last_item)
            elif isinstance(x, dict):
                result = x.get('content', '')
            elif hasattr(x, 'content'):
                result = x.content
            else:
                result = str(x)
        
        result = result.strip()
        
        if result and len(result) > 10:
            return result
        
        return f"抱歉，我无法处理这个请求。\n\n【参考文档内容】\n{context}"
    except Exception as e:
        import traceback
        print(f"RAG 对话错误: {traceback.format_exc()}")
        return f"对话出错了: {str(e)}\n\n【参考文档内容】\n{context}"


@app.post("/api/rag/chat")
async def rag_chat(request: RAGChatRequest):
    """
    RAG 智能问答和多轮对话 API
    """
    try:
        query = request.query
        doc_id = request.doc_id
        session_id = request.session_id or str(uuid.uuid4())
        
        if session_id in rag_chat_sessions:
            history = rag_chat_sessions[session_id]["history"]
        else:
            history = request.history or []
        
        if not query or query.strip() == '':
            return {"success": False, "error": "请输入查询内容"}
        
        retrieved_context = ""
        used_document = None
        
        if doc_id:
            doc = next((d for d in knowledge_base if d.get("doc_id") == doc_id), None)
            if doc:
                full_content = doc.get("content", "")
                relevant_content = extract_relevant_paragraph(full_content, query)
                retrieved_context = relevant_content
                used_document = doc
        else:
            final_results = []
            query_lower = query.lower()
            
            for doc in knowledge_base:
                filename = doc.get("filename", "")
                full_content = doc.get("content", "")
                content_lower = full_content.lower()
                
                if query_lower in content_lower or query_lower in filename.lower():
                    relevant_content = extract_relevant_paragraph(full_content, query)
                    final_results.append({
                        "doc_id": doc["doc_id"],
                        "filename": filename,
                        "content": relevant_content
                    })
            
            if final_results:
                retrieved_context = "\n\n".join([f"【文档: {r['filename']}】\n{r['content']}" for r in final_results[:2]])
                used_document = {"doc_id": final_results[0]["doc_id"], "filename": final_results[0]["filename"]}
        
        if not retrieved_context:
            retrieved_context = "（未找到相关文档内容）"
        
        history.append({
            "role": "user",
            "content": query
        })
        
        answer = rag_chat_with_qwen_agent(query, retrieved_context, history)
        
        history.append({
            "role": "assistant",
            "content": answer
        })
        
        rag_chat_sessions[session_id] = {
            "session_id": session_id,
            "history": history,
            "last_updated": datetime.now().isoformat()
        }
        
        if len(rag_chat_sessions) > 50:
            oldest_key = min(rag_chat_sessions.keys(), 
                        key=lambda k: rag_chat_sessions[k].get("last_updated", ""))
            if oldest_key in rag_chat_sessions:
                del rag_chat_sessions[oldest_key]
        
        return {
            "success": True,
            "session_id": session_id,
            "query": query,
            "answer": answer,
            "context": retrieved_context,
            "document": used_document,
            "history": history
        }
    except Exception as e:
        import traceback
        print(f"RAG 聊天错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/chat/{session_id}")
async def get_rag_chat_history(session_id: str):
    """
    获取 RAG 对话历史
    """
    if session_id in rag_chat_sessions:
        return {
            "success": True,
            "session": rag_chat_sessions[session_id]
        }
    return {"success": False, "error": "会话不存在"}


@app.get("/api/settings")
async def get_settings_page():
    return FileResponse(os.path.join(STATIC_DIR, "settings.html"))


if __name__ == "__main__":
    print("🚀 启动 DocuCode Agent Ultimate 终极服务 v4.2 (RAG增强版)...")
    print("📱 访问地址: http://localhost:8000")
    print("✨ 支持真实 DocuCode Agent 和模拟响应双模式")
    print("🎯 新增完整可运行代码和智能翻译器")
    print("🤖 新增 RAG 智能问答和多轮对话功能")
    uvicorn.run(app, host="0.0.0.0", port=8000)