# -*- coding: utf-8 -*-
"""
Priority Scorer - 基于 DIKW 的文章重要性评估工具

功能：
- 基于用户的 Ontology（关注点）评估文章相关性
- 多维度评分：相关性、创新性、影响性、权威性
- extraction_count 评分：基于用户兴趣的 extraction_count
- BM25 + 同义词扩展：关键词匹配优化

这是从 Publication_research 适配过来的版本，针对 EntroFeed 项目定制。
"""

import os
import json
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urlparse

from src.ontology.types import (
    InterestTag,
    UserInterest,
    ContentProfile,
    InterestCategory,
)
from src.ontology.tagging import TagMatcher


# ==================== 公共常量 ====================

# 常见缩写映射
ABBREVIATIONS = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "llm": "large language model",
    "genai": "generative artificial intelligence",
    "rag": "retrieval augmented generation",
}

# 时效性评分表
RECENCY_SCORES = {
    (0, 1): 1.0,      # < 1 hour
    (1, 6): 0.9,     # 1-6 hours
    (6, 12): 0.8,    # 6-12 hours
    (12, 24): 0.7,   # 12-24 hours
    (24, float('inf')): 0.5  # > 24 hours
}

# 权威性评分表
AUTHORITY_SCORES = {
    "nature": 1.0,
    "science": 1.0,
    "neurips": 0.95,
    "icml": 0.95,
    "arxiv": 0.9,
    "wsj": 0.85,
    "ft": 0.85,
    "techcrunch": 0.8,
    "twitter": 0.6,
    "reddit": 0.6,
}

# 关系谓词权重
PREDICATE_WEIGHTS = {
    "is_a": 1.0,
    "part_of": 0.9,
    "related_to": 0.5,
    "similar_to": 0.4,
    "causes": 0.7,
    "treats": 0.8,
}


def get_recency_score(hours_old: float) -> float:
    """根据文章发布小时数获取时效性评分"""
    for (min_h, max_h), score in RECENCY_SCORES.items():
        if min_h <= hours_old < max_h:
            return score
    return 0.5


def get_authority_score(source: str) -> float:
    """根据来源URL获取权威性评分"""
    # Extract host/domain from URL for matching
    try:
        parsed = urlparse(source.lower())
        domain = parsed.netloc
        # Remove port, www prefix
        domain = domain.replace(":443", "").replace(":80", "").replace("www.", "")
    except Exception:
        domain = source.lower()

    # Authority hosts mapping with domains
    AUTHORITY_HOSTS = {
        "nature.com": 1.0,
        "science.org": 1.0,
        "cell.com": 1.0,
        "nejm.org": 1.0,
        "lancet.com": 1.0,
        "arxiv.org": 0.9,
        "biorxiv.org": 0.85,
        "medrxiv.org": 0.85,
        "fda.gov": 0.95,
        "ema.europa.eu": 0.95,
        "nih.gov": 0.9,
        "who.int": 0.9,
        "techcrunch.com": 0.8,
        "wsj.com": 0.85,
        "ft.com": 0.85,
        "statnews.com": 0.8,
        "reuters.com": 0.75,
        "bloomberg.com": 0.75,
        "twitter.com": 0.6,
        "x.com": 0.6,
    }
    for host, score in AUTHORITY_HOSTS.items():
        if host in domain:
            return score
    return 0.5  # 默认中等权威


# ==================== BM25 算法 ====================

class BM25:
    """
    BM25 关键词匹配算法

    BM25 是一种基于概率的文本相关性排序算法，比简单的 TF-IDF 更加精确。
    通过引入文档长度归一化和饱和函数来避免长文档偏差。

    公式: score(D, Q) = Σ IDF(qi) * (tf(qi, D) * (k1 + 1)) / (tf(qi, D) + k1 * (1 - b + b * |D|/avgdl))

    其中:
    - tf(qi, D): 词项 qi 在文档 D 中的频率
    - |D|: 文档 D 的长度
    - avgdl: 语料库平均文档长度
    - k1: 词频饱和参数 (典型值 1.2-2.0)
    - b: 文档长度归一化参数 (典型值 0.75)
    - IDF(qi): 逆文档频率
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """初始化 BM25

        Args:
            k1: 词频饱和参数。较低的值会让高频词饱和得更快，默认 1.5
            b: 文档长度归一化参数。0.0 表示不归一化，1.0 表示完全归一化，默认 0.75
        """
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avgdl = 0.0
        self.doc_len: Dict[str, int] = {}
        self.doc_freqs: Dict[str, int] = {}  # 词项出现在多少个文档中
        self.idf: Dict[str, float] = {}
        self.doc_tokens: Dict[str, List[str]] = {}  # 每个文档的分词
        self.N = 0  # 文档总数

    def _tokenize(self, text: str) -> List[str]:
        """分词：简单按空格和标点分割，转小写"""
        if not text:
            return []
        # 去除 HTML 标签和特殊字符
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.lower().split()
        # 过滤停用词和太短的词
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'this',
                     'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
                     'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how'}
        return [t for t in tokens if len(t) > 2 and t not in stopwords]

    def _get_synonym_tokens(self, token: str) -> List[str]:
        """获取同义词扩展"""
        synonyms = {
            "ai": ["artificial", "intelligence"],
            "ml": ["machine", "learning"],
            "dl": ["deep", "learning"],
            "nlp": ["natural", "language", "processing"],
            "cv": ["computer", "vision"],
            "llm": ["large", "language", "model"],
            "genai": ["generative", "artificial", "intelligence"],
            "rag": ["retrieval", "augmented", "generation"],
        }
        return synonyms.get(token.lower(), [])

    def add_document(self, doc_id: str, text: str) -> None:
        """添加文档到语料库

        Args:
            doc_id: 文档唯一标识
            text: 文档文本
        """
        tokens = self._tokenize(text)
        self.doc_tokens[doc_id] = tokens
        self.doc_len[doc_id] = len(tokens)
        self.corpus_size += 1

        # 统计文档频率
        seen = set()
        for token in tokens:
            if token not in seen:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1
                seen.add(token)

    def build(self) -> None:
        """构建 IDF 表。在所有文档添加完毕后调用"""
        self.N = self.corpus_size
        import math
        for token, df in self.doc_freqs.items():
            # BM25 IDF 公式: log((N - n + 0.5) / (n + 0.5))
            idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
            self.idf[token] = idf

        # 计算平均文档长度
        if self.doc_len:
            self.avgdl = sum(self.doc_len.values()) / len(self.doc_len)

    def score(self, doc_id: str, query: List[str], use_synonyms: bool = True) -> float:
        """计算单个文档与查询的 BM25 得分

        Args:
            doc_id: 文档 ID
            query: 查询词列表（已分词）
            use_synonyms: 是否使用同义词扩展

        Returns:
            BM25 相关性得分
        """
        if doc_id not in self.doc_tokens:
            return 0.0

        doc_tokens = self.doc_tokens[doc_id]
        doc_len = self.doc_len[doc_id]
        score = 0.0

        # 构建文档词频表
        tf = defaultdict(int)
        for token in doc_tokens:
            tf[token] += 1

        # 扩展查询的同义词
        expanded_query = []
        for q in query:
            # 多词短语（如 "machine learning"）先拆分
            words = q.split()
            expanded_query.extend(words)
            if use_synonyms:
                for word in words:
                    syns = self._get_synonym_tokens(word)
                    expanded_query.extend(syns)

        for term in expanded_query:
            if term not in self.idf:
                continue

            term_tf = tf.get(term, 0)
            if term_tf == 0:
                continue

            idf = self.idf[term]
            # BM25 公式
            numerator = term_tf * (self.k1 + 1)
            denominator = term_tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            score += idf * (numerator / denominator)

        return score

    def get_top_k(self, query: List[str], k: int = 10, use_synonyms: bool = True) -> List[tuple]:
        """获取与查询最相关的 K 个文档

        Args:
            query: 查询词列表
            k: 返回数量上限
            use_synonyms: 是否使用同义词扩展

        Returns:
            [(doc_id, score), ...] 按得分降序
        """
        scores = []
        for doc_id in self.doc_tokens:
            s = self.score(doc_id, query, use_synonyms=use_synonyms)
            if s > 0:
                scores.append((doc_id, s))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class PriorityScorer:
    """
    基于 DIKW 的文章重要性评分器

    评估维度：
    - 相关性 (relevance): 与用户关注点（Ontology）的匹配程度
    - 时效性 (recency): 内容的发布时间
    - 权威性 (authority): 来源可信度
    - 影响性 (impact): 潜在影响和重要性
    """

    def __init__(self, tag_matcher: TagMatcher = None):
        """初始化评分器

        Args:
            tag_matcher: 标签匹配器
        """
        self.tag_matcher = tag_matcher or TagMatcher()
        # 缓存用户兴趣
        self._user_interests_cache: Optional[List[Dict]] = None
        self._cache_time = 0

    def _get_user_interests_from_registry(self) -> List[Dict[str, Any]]:
        """从 OntologyRegistry 获取用户兴趣"""
        if self._user_interests_cache is not None:
            return self._user_interests_cache

        try:
            from src.ontology import get_ontology_registry
            registry = get_ontology_registry()
            interests = registry.get_user_interests()

            # 转换为字典格式
            self._user_interests_cache = [
                {
                    "name": i.tag.name,
                    "category": i.tag.category.value,
                    "priority": i.priority,
                    "relevance_score": i.relevance_score,
                    "access_count": i.access_count,
                    "synonyms": i.tag.synonyms,
                }
                for i in interests
            ]
            return self._user_interests_cache
        except Exception as e:
            print(f"[PriorityScorer] Failed to get user interests: {e}")
            return []

    def score_article(
        self,
        article: Dict[str, Any],
        user_interests: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        对单篇文章评分

        Args:
            article: 文章数据，包含 title, summary, source, published_at 等
            user_interests: 用户兴趣列表（可选）

        Returns:
            评分结果，包含 total_score 和各维度分数
        """
        if user_interests is None:
            user_interests = self._get_user_interests_from_registry()

        title = article.get("title", "")
        summary = article.get("summary", "") or article.get("preview", "")
        source = article.get("source", "")
        published_at = article.get("published_at")

        text = f"{title} {summary}".lower()

        # 1. 计算时效性分数
        recency_score = self._calculate_recency_score(published_at)

        # 2. 计算权威性分数
        authority_score = get_authority_score(source)

        # 3. 计算相关性分数
        relevance_score = self._calculate_relevance_score(text, user_interests)

        # 4. 计算影响力分数（基于关键词触发）
        impact_score = self._calculate_impact_score(text)

        # 综合评分
        total_score = (
            recency_score * 0.4 +
            authority_score * 0.3 +
            relevance_score * 0.3
        )

        return {
            "total_score": round(total_score, 3),
            "recency_score": round(recency_score, 3),
            "authority_score": round(authority_score, 3),
            "relevance_score": round(relevance_score, 3),
            "impact_score": round(impact_score, 3),
            "has_match": relevance_score > 0.3,
        }

    def score_articles(
        self,
        articles: List[Dict[str, Any]],
        user_interests: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        批量评分

        Args:
            articles: 文章列表
            user_interests: 用户兴趣列表（可选）

        Returns:
            评分后的文章列表（按分数降序）
        """
        if user_interests is None:
            user_interests = self._get_user_interests_from_registry()

        scored = []
        for article in articles:
            result = self.score_article(article, user_interests)
            scored.append({
                **article,
                "total_score": result["total_score"],
                "recency_score": result["recency_score"],
                "authority_score": result["authority_score"],
                "relevance_score": result["relevance_score"],
                "impact_score": result["impact_score"],
                "has_match": result["has_match"],
            })

        # 按总分排序
        scored.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        return scored

    def _calculate_recency_score(self, published_at: Any) -> float:
        """计算时效性分数"""
        if not published_at:
            return 0.5  # 默认中等

        try:
            # 处理时间戳
            if isinstance(published_at, (int, float)):
                published_time = datetime.fromtimestamp(published_at)
            elif isinstance(published_at, str):
                published_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            else:
                return 0.5

            hours_old = (datetime.now() - published_time).total_seconds() / 3600
            return get_recency_score(hours_old)
        except Exception:
            return 0.5

    def _expand_abbreviations(self, text: str) -> str:
        """Expand known abbreviations in text for better matching.

        e.g. 'ai' → 'ai artificial intelligence', 'llm' → 'llm large language model'
        """
        text_lower = text.lower()
        for abbr, full in ABBREVIATIONS.items():
            # Replace standalone abbreviations with expanded form
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text_lower = re.sub(pattern, f"{abbr} {full}", text_lower)
        return text_lower

    def _calculate_relevance_score(
        self,
        text: str,
        user_interests: List[Dict[str, Any]]
    ) -> float:
        """计算相关性分数（基于用户兴趣匹配 + BM25）

        结合两种方法:
        1. 关键词精确/同义词/模糊匹配（权重 0.4）
        2. BM25 概率排序算法（权重 0.6）
        """
        if not user_interests or not text:
            return 0.0

        # Expand abbreviations so "ai" matches "artificial intelligence"
        text_lower = self._expand_abbreviations(text)
        max_keyword_score = 0.0

        for interest in user_interests:
            name = interest.get("name", "").lower()
            priority = interest.get("priority", 3)
            relevance = interest.get("relevance_score", 0.5)
            synonyms = interest.get("synonyms", [])

            # 优先级权重
            priority_weight = 0.5 + (priority / 10) * 2

            # 精确匹配
            if name in text_lower:
                score = relevance * priority_weight
                max_keyword_score = max(max_keyword_score, score)
                continue

            # 同义词匹配
            for syn in synonyms:
                syn_lower = syn.lower()
                if syn_lower in text_lower:
                    score = relevance * priority_weight * 0.8
                    max_keyword_score = max(max_keyword_score, score)
                    break
            else:
                # 模糊匹配
                words = set(w for w in text_lower.split() if len(w) > 2)
                if name in words or any(w in name for w in words):
                    score = relevance * priority_weight * 0.5
                    max_keyword_score = max(max_keyword_score, score)

        keyword_score = min(max_keyword_score, 1.0) * 0.4

        # ========== BM25 部分 ==========
        # 构建查询词列表（兴趣名 + 同义词）
        query_terms = []
        for interest in user_interests:
            query_terms.append(interest.get("name", "").lower())
            query_terms.extend([s.lower() for s in interest.get("synonyms", [])])

        # 过滤空词和太短的词
        query_terms = [t for t in query_terms if len(t) > 2]
        if not query_terms:
            return keyword_score

        # 创建 BM25 实例并添加文档
        bm25 = BM25(k1=1.5, b=0.75)
        bm25.add_document("doc", text_lower)
        bm25.build()

        # 计算 BM25 得分
        bm25_raw = bm25.score("doc", query_terms, use_synonyms=True)

        # 归一化 BM25 得分（经验值：>10 通常是很高的相关性）
        bm25_score = min(bm25_raw / 15.0, 1.0) * 0.6

        total_score = keyword_score + bm25_score
        return min(total_score, 1.0)

    def _calculate_impact_score(self, text: str) -> float:
        """计算影响力分数（基于关键词触发）"""
        text_lower = text.lower()

        # 高影响力关键词
        HIGH_IMPACT = {
            "breakthrough", "fda approved", "acquisition", "merger",
            "ipo", "patent granted", "regulation", "policy",
            "record high", "record low", "world's first",
        }

        # 中等影响力关键词
        MEDIUM_IMPACT = {
            "announcement", "launches", "unveils", "releases",
            "expands", "partners", "collaboration",
        }

        # 低影响力/噪音关键词
        LOW_IMPACT = {
            "advertisement", "sponsored", "press release",
            "webinar", "newsletter", "career", "job opening",
        }

        score = 0.0

        # 检查高影响力
        for kw in HIGH_IMPACT:
            if kw in text_lower:
                score = max(score, 0.9)
                break

        # 检查中等影响力
        if score == 0:
            for kw in MEDIUM_IMPACT:
                if kw in text_lower:
                    score = max(score, 0.6)
                    break

        # 检查低影响力
        for kw in LOW_IMPACT:
            if kw in text_lower:
                score = max(score, 0.2)
                break

        return score


class ArticleTagger:
    """
    文章打标签器

    基于 ontology 和规则为文章打标签
    """

    # 领域关键词映射
    DOMAIN_KEYWORDS = {
        InterestCategory.TECHNOLOGY: [
            "ai", "machine learning", "python", "software", "tech", "startup",
            "api", "cloud", "data", "algorithm", "javascript", "github",
            "openai", "google", "microsoft", "meta", "amazon",
        ],
        InterestCategory.MEDICAL: [
            "medical", "health", "doctor", "patient", "hospital", "treatment",
            "disease", "drug", "clinical", "patient", "fda", "nmpa",
            "cancer", "oncology", "vaccine", "therapy",
        ],
        InterestCategory.FINANCE: [
            "stock", "market", "investment", "bank", "finance", "economy",
            "revenue", "billion", "ipo", "cryptocurrency", "fintech",
            "trading", "fund", "investor",
        ],
        InterestCategory.SCIENCE: [
            "research", "study", "scientist", "experiment", "discovery",
            "physics", "chemistry", "biology", "space", "nasa",
            "research", "paper", "journal", "publication",
        ],
        InterestCategory.BUSINESS: [
            "company", "ceo", "startup", "funding", "acquisition",
            "partnership", "launch", "product", "strategy", "enterprise",
        ],
    }

    def __init__(self):
        pass

    def extract_tags(self, article: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        为文章提取标签

        Args:
            article: 文章数据

        Returns:
            标签列表 [{"name": "...", "category": "...", "confidence": 0.8}, ...]
        """
        title = article.get("title", "")
        summary = article.get("summary", "") or article.get("preview", "")
        text = f"{title} {summary}".lower()

        detected_tags = []

        # 按领域检测关键词
        for category, keywords in self.DOMAIN_KEYWORDS.items():
            matched = []
            for kw in keywords:
                if kw in text:
                    matched.append(kw)

            if matched:
                confidence = min(0.9, 0.5 + len(matched) * 0.1)
                detected_tags.append({
                    "name": matched[0],  # 主关键词作为标签名
                    "category": category.value,
                    "confidence": confidence,
                    "matched_keywords": matched,
                })

        # 提取命名实体（简单的大写词组检测）
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', f"{title} {summary}")
        entities = [e for e in entities if len(e) > 2][:5]

        for entity in entities:
            detected_tags.append({
                "name": entity.lower(),
                "category": "entity",
                "confidence": 0.6,
                "is_entity": True,
            })

        # 按置信度排序
        detected_tags.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        # Add RSS category tags as high-confidence domain signals
        rss_tags = article.get("rss_tags", [])
        for rt in rss_tags:
            # Skip if already a processed tag dict (from previous backfill)
            if isinstance(rt, dict):
                continue
            if not isinstance(rt, str):
                continue
            rt_lower = rt.lower()
            if len(rt_lower) < 2:
                continue
            # Check if RSS tag maps to a known domain category
            matched = False
            for cat, keywords in self.DOMAIN_KEYWORDS.items():
                if rt_lower in [kw.lower() for kw in keywords]:
                    detected_tags.insert(0, {
                        "name": rt_lower,
                        "category": cat.value,
                        "confidence": 0.95,
                        "is_rss_tag": True,
                    })
                    matched = True
                    break
            if not matched:
                detected_tags.insert(0, {
                    "name": rt_lower,
                    "category": "entity",
                    "confidence": 0.8,
                    "is_rss_tag": True,
                })

        # Re-sort after adding RSS tags
        detected_tags.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        detected_tags = detected_tags[:10]  # 最多10个标签

        return detected_tags

    def _expand_tag_name(self, name: str) -> str:
        """Expand abbreviation in tag name to match user interests.

        e.g. 'ai' → 'artificial intelligence', 'llm' → 'large language model'
        """
        if not isinstance(name, str):
            return name
        name_lower = name.lower()
        for abbr, full in ABBREVIATIONS.items():
            if name_lower == abbr:
                return full
        return name

    def tag_article(
        self,
        article: Dict[str, Any],
        user_interests: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为文章打标签并评分

        Args:
            article: 文章数据
            user_interests: 用户兴趣列表

        Returns:
            带标签和分数的文章
        """
        tags = self.extract_tags(article)

        # 计算与用户兴趣的匹配度
        match_score = 0.0
        matched_interests = []

        if user_interests:
            # Build expanded tag names set for matching
            # e.g. "ai" → "artificial intelligence" so it matches interest
            expanded_names = {self._expand_tag_name(t["name"].lower()) for t in tags}
            original_names = {t["name"].lower() for t in tags}

            for interest in user_interests:
                interest_name = interest.get("name", "").lower()
                # Check if interest name matches either original or expanded tag
                if interest_name in original_names or interest_name in expanded_names:
                    match_score = max(match_score, interest.get("relevance_score", 0.5))
                    matched_interests.append(interest.get("name"))

        return {
            **article,
            "tags": tags,
            "matched_interests": matched_interests,
            "ontology_match_score": match_score,
            "has_ontology_match": len(matched_interests) > 0,
        }


# 全局实例
_scorer: Optional[PriorityScorer] = None
_tagger: Optional[ArticleTagger] = None


def get_priority_scorer() -> PriorityScorer:
    """获取全局 PriorityScorer 实例"""
    global _scorer
    if _scorer is None:
        _scorer = PriorityScorer()
    return _scorer


def get_article_tagger() -> ArticleTagger:
    """获取全局 ArticleTagger 实例"""
    global _tagger
    if _tagger is None:
        _tagger = ArticleTagger()
    return _tagger


def score_and_tag_articles(
    articles: List[Dict[str, Any]],
    user_interests: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：对文章列表评分和打标签

    Args:
        articles: 文章列表
        user_interests: 用户兴趣列表

    Returns:
        带评分和标签的文章列表
    """
    scorer = get_priority_scorer()
    tagger = get_article_tagger()

    if user_interests is None:
        user_interests = scorer._get_user_interests_from_registry()

    results = []
    for article in articles:
        # 评分
        scored = scorer.score_article(article, user_interests)

        # 打标签
        tagged = tagger.tag_article(article, user_interests)

        # 合并结果
        results.append({
            **article,
            "total_score": scored["total_score"],
            "recency_score": scored["recency_score"],
            "authority_score": scored["authority_score"],
            "relevance_score": scored["relevance_score"],
            "impact_score": scored["impact_score"],
            "tags": tagged["tags"],
            "matched_interests": tagged["matched_interests"],
            "has_ontology_match": tagged["has_ontology_match"] or scored["has_match"],
        })

    # 按总分排序
    results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    return results


__all__ = [
    "PriorityScorer",
    "ArticleTagger",
    "get_priority_scorer",
    "get_article_tagger",
    "score_and_tag_articles",
    "get_recency_score",
    "get_authority_score",
]
