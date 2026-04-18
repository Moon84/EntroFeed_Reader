# -*- coding: utf-8 -*-
"""
Priority Scorer - 基于 DIKW 的文章重要性评估工具

功能：
- 基于用户的 Ontology（关注点）评估文章相关性
- 多维度评分：相关性、创新性、影响性、权威性
- extraction_count 评分：基于用户兴趣的 extraction_count
- BM25 + 同义词扩展：关键词匹配优化
- 图传播评分：基于知识图谱的偏好传播（借鉴 RippleNet）

这是从 Publication_research 适配过来的版本，针对 EntroFeed 项目定制。
"""

import os
import re
import math
from collections import defaultdict
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from urllib.parse import urlparse

from .types import (
    InterestCategory,
)
from .tagging import TagMatcher


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

# ==================== Authority 评分常量 ====================
# Authority 是二维评分：
# 1. Evidence Level（内容类型/证据级别）- 反映内容本身的质量/影响力
# 2. Institution Authority（机构权威性）- 反映发布来源的可靠性
# 最终 Authority = Evidence Level × Institution Authority（相乘）

# Evidence Level（证据级别）- 反映内容类型的学术/新闻价值
EVIDENCE_LEVELS = {
    # 高证据级别
    "rct": 1.0,                # 随机对照试验 (Randomized Controlled Trial)
    "meta_analysis": 1.0,       # 元分析/系统综述
    "systematic_review": 1.0,    # 系统综述
    "guideline": 0.95,          # 临床指南
    "cohort": 0.75,             # 队列研究
    "case_control": 0.55,       # 病例对照研究
    "cross_sectional": 0.45,    # 横断面研究
    "case_report": 0.35,        # 病例报告
    "expert_opinion": 0.25,     # 专家意见
    "news": 0.20,              # 新闻报道
    "blog": 0.15,              # 博客
    "social_media": 0.10,       # 社交媒体
    "press_release": 0.12,     # 新闻稿
    "advertorial": 0.08,        # 软文/广告
}

# Institution Authority（机构权威性）- 反映来源的可信度
INSTITUTION_AUTHORITY = {
    # 顶级医学期刊
    "nejm.org": 1.0,            # New England Journal of Medicine
    "lancet.com": 1.0,          # The Lancet
    "nature.com": 0.98,         # Nature
    "science.org": 0.98,        # Science
    "cell.com": 0.95,           # Cell
    "jama.com": 0.95,          # JAMA
    "bmj.com": 0.90,           # BMJ

    # 预印本
    "arxiv.org": 0.70,          # arXiv (开放获取预印本)
    "biorxiv.org": 0.65,        # bioRxiv
    "medrxiv.org": 0.65,       # medRxiv

    # 政府/监管机构
    "fda.gov": 0.90,            # FDA
    "ema.europa.eu": 0.88,     # EMA
    "who.int": 0.88,            # WHO
    "nih.gov": 0.85,            # NIH
    "cdc.gov": 0.85,            # CDC

    # AI/ML 顶会
    "neurips.cc": 0.92,         # NeurIPS
    "icml.cc": 0.92,           # ICML
    "iclr.cc": 0.90,           # ICLR
    "aaai.org": 0.85,           # AAAI
    "acm.org": 0.80,           # ACM

    # 主流媒体
    "reuters.com": 0.55,        # Reuters
    "bloomberg.com": 0.52,      # Bloomberg
    "wsj.com": 0.50,           # Wall Street Journal
    "ft.com": 0.50,            # Financial Times
    "nytimes.com": 0.48,       # NY Times
    "theguardian.com": 0.45,    # The Guardian

    # 科技媒体
    "techcrunch.com": 0.40,    # TechCrunch
    "theverge.com": 0.38,      # The Verge
    "arstechnica.com": 0.40,   # Ars Technica
    "wired.com": 0.38,         # Wired

    # 社交媒体（低权威性）
    "twitter.com": 0.15,        # Twitter/X
    "x.com": 0.15,
    "reddit.com": 0.12,
    "linkedin.com": 0.18,
    "youtube.com": 0.15,
    "github.com": 0.30,         # GitHub (代码/项目)
}

# Evidence Level 关键词（从标题/摘要中检测）
EVIDENCE_KEYWORDS = {
    "rct": ["randomized controlled trial", "randomised controlled trial", "rct",
             "随机对照试验", "随机临床试验"],
    "meta_analysis": ["meta-analysis", "meta analysis", "systematic review",
                       "荟萃分析", "系统综述", "meta-analys", "systematic review"],
    "cohort": ["cohort study", "prospective study", "retrospective cohort",
               "队列研究", "前瞻性研究", "随访研究"],
    "case_control": ["case-control", "case control study", "病例对照"],
    "case_report": ["case report", "case series", "病例报告", "个案报告"],
    "guideline": ["guideline", "consensus", "指南", "专家共识", "clinical practice guideline"],
    "expert_opinion": ["expert opinion", "expert review", "专家观点", "专家述评"],
    "news": ["news", "reports", "报道", "新闻"],
    "blog": ["blog post", "blog", "博客"],
    "press_release": ["press release", "新闻稿", "媒体通稿"],
}


# ==================== Impact 评分常量 ====================
# Impact 只与领域相关，通过图距离评估
# 高影响力关键词只在领域内有意义，超出领域范围则不考虑

# 领域特定的高影响力关键词（按领域分层）
DOMAIN_IMPACT_KEYWORDS = {
    # 医疗领域
    "medical": {
        "high": ["fda approved", "phase 3", "phase ii", "phase iii", "clinical trial",
                 "随机对照", "临床试验", "fda批准", "突破性疗法", "优先审批",
                 "rct", "randomized", "随机", "双盲", "安慰剂对照"],
        "medium": ["cohort", "observational", "队列", "观察性", "随访",
                   "registry", "登记研究"],
        "low": ["case report", "case series", "病例报告", "专家观点"],
    },
    # AI/技术领域
    "technology": {
        "high": ["benchmark", "state-of-the-art", "sota", "breakthrough",
                 "open source", "github", "released", "announced",
                 "基准测试", "最优", "开源", "发布"],
        "medium": ["preprint", "arxiv", "technical report", "预印本"],
        "low": ["opinion", "perspective", "观点", "展望"],
    },
    # 商业/金融领域
    "business": {
        "high": ["acquisition", "merger", "ipo", "funding round", "series a", "series b",
                 "收购", "并购", "上市", "融资", "a轮", "b轮"],
        "medium": ["partnership", "launch", "expansion", "合作", "发布", "扩张"],
        "low": [" layoffs", "rumor", "裁员", "传闻"],
    },
    # 通用高影响力（跨领域）
    "general": {
        "high": ["regulation", "policy", "government", "监管", "政策", "政府",
                 "banned", "prohibited", "禁止", "批准", "regulation approved"],
        "medium": ["announcement", "unveils", "公告", "发布", "推出"],
    },
}


# ==================== 图传播系数常量 ====================
# 图传播用系数方式，而非比例方式
# 避免分数累积导致的不可控范围

GRAPH_COEFFICIENTS = {
    "exact_match": 1.0,           # 精确匹配（种子节点直接命中）
    "hop_1": 0.5,                 # 1跳（父子关系）
    "hop_2": 0.25,                # 2跳（叔侄关系）
    "cross_domain_boost": 1.2,   # 跨领域加成（医学AI = AI + Medical）
    # 注意：hop_1 和 hop_2 是通过 HOP_DECAY 隐含计算的
}

# Hop 衰减因子
HOP_DECAY = 0.5


# ==================== 关系谓词权重 ====================
PREDICATE_WEIGHTS = {
    "is_a": 1.0,
    "part_of": 0.9,
    "related_to": 0.5,
    "similar_to": 0.4,
    "causes": 0.7,
    "treats": 0.8,
}


# ==================== 时效性评分 ====================
# 时间衰减评分（小时数 -> 分数）
RECENCY_SCORES = {
    (0, 6): 1.0,           # 6小时内：最新
    (6, 24): 0.9,          # 1天内：很新
    (24, 72): 0.7,         # 3天内：较新
    (72, 168): 0.5,        # 1周内：中等
    (168, 720): 0.3,       # 1个月内：较旧
    (720, float('inf')): 0.1,  # 1个月以上：旧
}


def get_recency_score(hours_old: float) -> float:
    """根据文章发布小时数获取时效性评分"""
    for (min_h, max_h), score in RECENCY_SCORES.items():
        if min_h <= hours_old < max_h:
            return score
    return 0.5


def get_authority_score(source: str) -> float:
    """根据来源URL获取权威性评分（二维评分的 Institution Authority 部分）

    新评分系统：
    - Authority = Evidence Level × Institution Authority
    - 这里只返回 Institution Authority 部分
    - Evidence Level 需要从内容中检测
    """
    # Extract host/domain from URL for matching
    try:
        parsed = urlparse(source.lower())
        domain = parsed.netloc
        # Remove port, www prefix
        domain = domain.replace(":443", "").replace(":80", "").replace("www.", "")
    except Exception:
        domain = source.lower()

    for host, score in INSTITUTION_AUTHORITY.items():
        if host in domain:
            return score
    return 0.30  # 默认低权威性


def detect_evidence_level(text: str) -> float:
    """从文本中检测证据级别

    Args:
        text: 文章标题 + 摘要

    Returns:
        Evidence Level 分数（0-1）
    """
    text_lower = text.lower()

    # 按优先级顺序检测（高优先级先检测）
    detection_order = [
        ("rct", EVIDENCE_KEYWORDS["rct"]),
        ("meta_analysis", EVIDENCE_KEYWORDS["meta_analysis"]),
        ("guideline", EVIDENCE_KEYWORDS["guideline"]),
        ("cohort", EVIDENCE_KEYWORDS["cohort"]),
        ("case_control", EVIDENCE_KEYWORDS["case_control"]),
        ("case_report", EVIDENCE_KEYWORDS["case_report"]),
        ("expert_opinion", EVIDENCE_KEYWORDS["expert_opinion"]),
        ("news", EVIDENCE_KEYWORDS["news"]),
        ("blog", EVIDENCE_KEYWORDS["blog"]),
        ("press_release", EVIDENCE_KEYWORDS["press_release"]),
    ]

    for level_name, keywords in detection_order:
        for kw in keywords:
            if kw.lower() in text_lower:
                return EVIDENCE_LEVELS[level_name]

    return EVIDENCE_LEVELS["news"]  # 默认新闻级别


def calculate_authority_score(source: str, title: str, preview: str = "") -> Dict[str, float]:
    """计算二维 Authority 评分

    新评分系统：
    Authority = Evidence Level × Institution Authority

    Args:
        source: 来源 URL
        title: 文章标题
        preview: 文章摘要/预览

    Returns:
        {
            "authority_total": 0.0-1.0,    # 最终 Authority 分数
            "evidence_level": 0.0-1.0,     # 证据级别分数
            "institution": 0.0-1.0,        # 机构权威性分数
        }
    """
    text = f"{title} {preview}"

    # 1. Institution Authority（从 URL 获取）
    institution_score = get_authority_score(source)

    # 2. Evidence Level（从文本检测）
    evidence_level = detect_evidence_level(text)

    # 3. 最终 Authority = 两者相乘
    authority_total = evidence_level * institution_score

    return {
        "authority_total": round(authority_total, 4),
        "evidence_level": round(evidence_level, 4),
        "institution": round(institution_score, 4),
    }


def calculate_impact_score(
    text: str,
    user_interests: List[Dict[str, Any]],
    graph_scorer: 'GraphPropagationScorer' = None
) -> Dict[str, Any]:
    """计算领域相关的 Impact 评分

    Impact 只在领域相关时有意义：
    1. 检测文本中的高影响力关键词
    2. 检查这些关键词是否在用户关注的领域范围内（图距离）
    3. 如果在领域内，返回高分；否则返回低分

    Args:
        text: 文章标题 + 摘要
        user_interests: 用户兴趣列表
        graph_scorer: 图传播评分器（用于计算领域距离）

    Returns:
        {
            "impact_score": 0.0-1.0,      # 最终 Impact 分数
            "domain_relevance": 0.0-1.0,  # 领域相关性
            "detected_keywords": [...],     # 检测到的高影响力关键词
            "domain_match": {...},          # 领域匹配详情
        }
    """
    text_lower = text.lower()

    # 1. 检测所有领域的高影响力关键词
    detected_impacts = []  # [(keyword, domain, level, level_score)]
    detected_domains = set()

    for domain, keywords_by_level in DOMAIN_IMPACT_KEYWORDS.items():
        for level_name, keywords in keywords_by_level.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    level_score = {
                        "high": 1.0,
                        "medium": 0.5,
                        "low": 0.2,
                    }.get(level_name, 0.3)
                    detected_impacts.append({
                        "keyword": kw,
                        "domain": domain,
                        "level": level_name,
                        "base_score": level_score,
                    })
                    detected_domains.add(domain)

    if not detected_impacts:
        return {
            "impact_score": 0.0,
            "domain_relevance": 0.0,
            "detected_keywords": [],
            "domain_match": {},
        }

    # 2. 计算领域相关性（通过图距离）
    domain_relevance = 0.0
    domain_match_detail = {}

    if graph_scorer and user_interests:
        # 将检测到的领域映射到标准领域节点
        # 对于 "healthcare policy" 这样的短语，应该找到 "Healthcare" 节点
        domain_to_nodes = {
            "medical": "Medical",
            "technology": "Technology",
            "business": "Business",
            "general": None,  # 通用领域需要上下文判断
        }

        for domain in detected_domains:
            target_node = domain_to_nodes.get(domain)

            if target_node is None:
                # 通用领域关键词：尝试从文本中找领域线索
                # 例如："healthcare policy" -> 检测到 "healthcare" 在文本中
                best_relevance = 0.0
                for interest in user_interests:
                    seed_name = interest.get("name", "")
                    # 简单检查：用户兴趣词是否出现在文本中
                    if seed_name.lower() in text_lower:
                        # 用户兴趣在文本中出现，假设相关
                        best_relevance = max(best_relevance, 0.6)

                if best_relevance == 0:
                    # 没有找到领域线索，通用关键词不给高分
                    domain_match_detail[domain] = {"relevance": 0.0, "method": "no_context"}
                    continue

                domain_relevance = max(domain_relevance, best_relevance)
                domain_match_detail[domain] = {"relevance": best_relevance, "method": "context_hint"}
                continue

            # 通过图传播计算与用户兴趣的距离
            best_relevance = 0.0

            for interest in user_interests:
                seed_name = interest.get("name", "")
                seed_priority = interest.get("priority", 3) / 5.0  # 归一化

                hop_score, hops = graph_scorer._get_hopped_score(
                    seed_name, target_node, set()
                )

                if hops == 0:  # 精确匹配
                    relevance = 1.0 * seed_priority
                elif hops == 1:
                    relevance = 0.6 * seed_priority
                elif hops == 2:
                    relevance = 0.3 * seed_priority
                else:
                    relevance = 0.0

                best_relevance = max(best_relevance, relevance)

            domain_relevance = max(domain_relevance, best_relevance)
            domain_match_detail[domain] = {
                "relevance": best_relevance,
                "method": "graph_propagation"
            }

    else:
        # 没有图传播器时，简单假设领域相关
        domain_relevance = 0.5
        for domain in detected_domains:
            domain_match_detail[domain] = {"relevance": 0.5, "method": "default"}

    # 3. 计算最终 Impact 分数
    # = 最高基础分 × 领域相关性
    max_base_score = max(d["base_score"] for d in detected_impacts)
    impact_score = max_base_score * domain_relevance

    return {
        "impact_score": round(impact_score, 4),
        "domain_relevance": round(domain_relevance, 4),
        "detected_keywords": [d["keyword"] for d in detected_impacts],
        "domain_match": domain_match_detail,
    }


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


# ==================== 图传播评分器 ====================
# 借鉴 RippleNet 的偏好传播思路，在领域层次图上做多跳扩散


class GraphPropagationScorer:
    """
    基于知识图谱的偏好传播评分器（借鉴 RippleNet）

    核心思想：
    1. 用户兴趣作为种子节点，在领域层次图上向外传播偏好
    2. 每跳有权重衰减（hop_decay）
    3. 跨领域连接有额外权重（cross_domain_boost）
    4. 文章标签在图中的"到达强度"作为图传播相关性分数

    优势：
    - 能够发现间接相关的文章（如用户关注 AI，文章是 MedicalAI 领域）
    - 跨领域推理能力（如 AI + Medical = MedicalAI）
    - 可解释性强（可以显示匹配路径）
    """

    # 关系类型权重（从 domain_hierarchy.py 的关系类型映射）
    # 注意：sibling 边默认禁用，因为它会过度连接不相关领域
    RELATION_WEIGHTS = {
        "parent_to_child": 0.85,   # 父子关系（强）
        "cross_domain": 0.5,       # 跨领域（中等）
        "sibling": 0.0,            # 兄弟领域（禁用，避免无关领域连通）
        "seed_to_domain": 1.0,     # 种子到领域（最强）
    }

    # Hop 衰减因子（每跳乘以此因子）
    HOP_DECAY = 0.5

    # 最大跳数（限制为2，避免过度传播）
    MAX_HOPS = 2

    def __init__(self):
        """初始化图传播评分器"""
        self._domain_hierarchy: Optional[Dict] = None
        self._node_index: Optional[Dict[str, Dict]] = None
        self._adjacency: Optional[Dict[str, List[Tuple[str, float]]]] = None  # node -> [(neighbor, weight)]

    def _get_domain_hierarchy(self) -> Dict:
        """懒加载领域层次图"""
        if self._domain_hierarchy is None:
            from .domain_hierarchy import DOMAIN_HIERARCHY
            self._domain_hierarchy = DOMAIN_HIERARCHY
            self._build_graph_index()
        return self._domain_hierarchy

    def _build_graph_index(self) -> None:
        """构建图的邻接表和节点索引"""
        if self._domain_hierarchy is None:
            return

        hierarchy = self._domain_hierarchy
        self._adjacency = defaultdict(list)
        self._node_index = {}

        # 遍历所有领域节点（扩展到 Level 3 以包含 MachineLearning, DeepLearning 等）
        for domain, info in hierarchy.items():
            level = info.get("level", 0)
            if level > 3:  # 处理 Level 0-3，包含 MachineLearning, DeepLearning 等
                continue

            aliases = info.get("aliases", [])
            parent = info.get("parent", "")
            cross_domains = info.get("cross_domains", [])
            children = info.get("children", [])

            # 构建节点索引（用于别名匹配）
            for alias in [domain] + aliases:
                self._node_index[alias.lower()] = domain

            # 父子关系边（双向）
            if parent:
                self._adjacency[domain].append((parent, self.RELATION_WEIGHTS["parent_to_child"]))
                self._adjacency[parent].append((domain, self.RELATION_WEIGHTS["parent_to_child"]))

            # 跨领域边（只对 Level 2 节点添加单向 cross_domain 边）
            # Level 2 节点（如 MedicalAI, FinTech）是跨领域概念，表示多个 Level 0/1 的交集
            # 只有 Level 2 节点才添加 cross_domain 边，Level 0/1 节点不添加
            # 这样可以避免"FinTech 是 Finance+Technology 的交集，却被 AI 连接到"的问题
            if level == 2:
                for cross in cross_domains:
                    if cross in hierarchy:
                        self._adjacency[domain].append((cross, self.RELATION_WEIGHTS["cross_domain"]))

            # 注意：不再创建 sibling 边，因为 sibling weight = 0

    def _normalize_name(self, name: str) -> Optional[str]:
        """将标签名标准化为领域节点名"""
        name_lower = name.lower().strip()
        return self._node_index.get(name_lower)

    def _get_hopped_score(
        self,
        seed_domain: str,
        target_domain: str,
        visited: Set[str]
    ) -> Tuple[float, int]:
        """
        计算从种子领域到目标领域的传播强度

        关键约束：
        - cross_domain 边只能作为路径的最后一跳（不允许"跨领域桥接"）
        - 这是因为 cross_domain 节点（如 FinTech）是多个父领域的交叉点，
          不应该被用作到达其他父领域的跳板

        Returns:
            (score, hops) - 传播分数和跳数，如果无法到达返回 (0.0, 0)
        """
        if seed_domain.lower() == target_domain.lower():
            return (1.0, 0)

        # 确保图已构建
        self._get_domain_hierarchy()

        # BFS 查找最短路径
        queue = [(seed_domain, 1.0, 0, False)]  # (current_domain, accumulated_score, hops, used_cross_domain)
        visited_local = {seed_domain.lower()}  # 使用 lowercase 便于比较

        while queue:
            current, score, hops, used_cross = queue.pop(0)

            if hops >= self.MAX_HOPS:
                continue

            for neighbor, edge_weight in self._adjacency.get(current, []):
                neighbor_lower = neighbor.lower()
                if neighbor_lower in visited_local:
                    continue

                is_cross = (edge_weight == self.RELATION_WEIGHTS["cross_domain"])

                # 如果已经使用过 cross_domain 边，则不能再继续扩展路径
                # cross_domain 边只能作为路径的最后一跳
                # 这防止了"跨领域桥接"：如 AI -> Technology -> FinTech -> Finance
                if used_cross:
                    continue

                new_score = score * edge_weight * self.HOP_DECAY
                new_hops = hops + 1

                if neighbor.lower() == target_domain.lower():
                    return (new_score, new_hops)

                visited_local.add(neighbor_lower)
                queue.append((neighbor, new_score, new_hops, used_cross or is_cross))

        # No path found - return (-1) hops to distinguish from exact match (hops=0)
        return (0.0, -1)

    def calculate_graph_score(
        self,
        content_tags: List[str],
        user_interests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        计算文章的图传播相关性分数（系数方式）

        新评分方式：
        - graph_coefficient = 精确匹配系数或跳数系数的最大值
        - exact = 1.0, hop_1 = 0.5, hop_2 = 0.25
        - 跨领域加成 ×1.2

        这种方式更可解释，避免分数累积导致的不可控范围。

        Args:
            content_tags: 文章的标签列表（可以是领域节点、别名、或任意匹配词）
            user_interests: 用户兴趣列表

        Returns:
            包含 graph_coefficient 和匹配详情的字典
        """
        self._get_domain_hierarchy()  # 确保图已构建

        if not content_tags or not user_interests:
            return {"graph_coefficient": 0.0, "matched_seeds": [], "hop_details": []}

        # 标准化文章标签为领域节点
        content_domains = []
        for tag in content_tags:
            domain = self._normalize_name(tag)
            if domain:
                content_domains.append(domain)
            else:
                # 尝试直接匹配（可能是子领域名）
                tag_lower = tag.lower()
                if tag_lower in self._node_index:
                    content_domains.append(self._node_index[tag_lower])

        content_domains = list(set(content_domains))  # 去重

        best_coefficient = 0.0
        best_hop_info = None
        matched_seeds = []
        hop_details = []

        for interest in user_interests:
            seed_name = interest.get("name", "")
            seed_priority = interest.get("priority", 3)
            seed_relevance = interest.get("relevance_score", 0.5)

            # 标准化种子节点
            seed_domain = self._normalize_name(seed_name)
            if not seed_domain:
                # 尝试模糊匹配
                seed_lower = seed_name.lower()
                for alias, domain in self._node_index.items():
                    if seed_lower in alias or alias in seed_lower:
                        seed_domain = domain
                        break

            if not seed_domain:
                continue

            # 种子权重（用于最终系数计算）
            seed_weight = (seed_priority / 5.0) * seed_relevance

            # 对每个内容领域计算传播系数
            for content_domain in content_domains:
                if seed_domain.lower() == content_domain.lower():
                    # 精确匹配：系数 = 1.0
                    coefficient = 1.0 * seed_weight
                    hops = 0
                    match_type = "exact"
                else:
                    # 图传播匹配
                    hop_score, hops = self._get_hopped_score(seed_domain, content_domain, set())

                    if hops == 1:
                        coefficient = GRAPH_COEFFICIENTS["hop_1"] * seed_weight
                        match_type = "hop_1"
                    elif hops == 2:
                        coefficient = GRAPH_COEFFICIENTS["hop_2"] * seed_weight
                        match_type = "hop_2"
                    else:
                        coefficient = 0.0
                        match_type = "no_path"

                if coefficient > best_coefficient:
                    best_coefficient = coefficient
                    best_hop_info = {
                        "seed": seed_name,
                        "content_domain": content_domain,
                        "hops": hops,
                        "match_type": match_type,
                    }

                if coefficient > 0:
                    matched_seeds.append(seed_name)
                    hop_details.append({
                        "seed": seed_name,
                        "content_domain": content_domain,
                        "coefficient": round(coefficient, 4),
                        "hops": hops,
                        "match_type": match_type,
                    })

        # 去重
        matched_seeds = list(set(matched_seeds))

        # 限制系数在 0-1 范围内
        best_coefficient = min(1.0, best_coefficient)

        return {
            "graph_coefficient": round(best_coefficient, 4),
            "best_match": best_hop_info,
            "matched_seeds": matched_seeds,
            "hop_details": hop_details,
        }

    def calculate_batch_graph_scores(
        self,
        articles: List[Dict[str, Any]],
        user_interests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量计算文章的图传播分数

        Args:
            articles: 文章列表，每篇包含 tags 字段
            user_interests: 用户兴趣列表

        Returns:
            带图传播分数的文章列表
        """
        results = []
        for article in articles:
            tags = article.get("tags", [])
            if isinstance(tags, list):
                tag_names = []
                for t in tags:
                    if isinstance(t, dict):
                        tag_names.append(t.get("name", ""))
                    elif isinstance(t, str):
                        tag_names.append(t)

                graph_result = self.calculate_graph_score(tag_names, user_interests)
                results.append({
                    **article,
                    "graph_score": graph_result["graph_score"],
                    "graph_matched_seeds": graph_result["matched_seeds"],
                    "graph_hop_details": graph_result.get("hop_details", []),
                })
            else:
                results.append({
                    **article,
                    "graph_score": 0.0,
                    "graph_matched_seeds": [],
                    "graph_hop_details": [],
                })

        return results


# 全局图传播评分器实例
_graph_scorer: Optional[GraphPropagationScorer] = None


def get_graph_propagation_scorer() -> GraphPropagationScorer:
    """获取全局 GraphPropagationScorer 实例"""
    global _graph_scorer
    if _graph_scorer is None:
        _graph_scorer = GraphPropagationScorer()
    return _graph_scorer


class PriorityScorer:
    """
    基于 DIKW 的文章重要性评分器

    评估维度：
    - 相关性 (relevance): 与用户关注点（Ontology）的匹配程度
    - 时效性 (recency): 内容的发布时间（低权重）
    - 权威性 (authority): 来源可信度
    - 影响性 (impact): 潜在影响和重要性

    新评分公式（权重分配）：
    - ontology_relevance: 0.50 (核心：语义相关性)
    - authority: 0.25 (来源可信度)
    - impact: 0.20 (事件重要性)
    - recency: 0.05 (时效性，低权重)
    """

    # 评分权重配置
    WEIGHTS = {
        "ontology_relevance": 0.50,  # 核心：基于 Ontology 的语义相关性
        "authority": 0.25,           # 来源权威性
        "impact": 0.20,              # 影响力
        "recency": 0.05,             # 时效性（低权重，内容比时效更重要）
    }

    def __init__(self, tag_matcher: TagMatcher = None):
        """初始化评分器

        Args:
            tag_matcher: 标签匹配器
        """
        self.tag_matcher = tag_matcher or TagMatcher()
        self.graph_scorer = GraphPropagationScorer()
        # 缓存用户兴趣
        self._user_interests_cache: Optional[List[Dict]] = None
        self._cache_time = 0

    def _get_user_interests_from_registry(self) -> List[Dict[str, Any]]:
        """从 OntologyRegistry 获取用户兴趣"""
        if self._user_interests_cache is not None:
            return self._user_interests_cache

        try:
            from . import get_ontology_registry
            registry = get_ontology_registry()
            interests = registry.get_user_interests()

            # 转换为字典格式（UnifiedNode 的扁平结构）
            self._user_interests_cache = [
                {
                    "name": i.name,
                    "category": i.category.value if hasattr(i.category, 'value') else str(i.category),
                    "priority": i.interest_priority,
                    "relevance_score": i.interest_level,
                    "access_count": i.access_count,
                    "synonyms": i.synonyms,
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
        对单篇文章评分（新评分体系）

        新评分架构（权重分配）：
        total_score = (
            WEIGHTS["ontology_relevance"] * (relevance * 0.6 + graph_coefficient * 0.4) +
            WEIGHTS["authority"] * authority_total +
            WEIGHTS["impact"] * impact_score +
            WEIGHTS["recency"] * recency_score
        )

        其中：
        - ontology_relevance = relevance * 0.6 + graph_coefficient * 0.4
          （基础相关性 + 图传播加成，图不再是乘法门控）
        - Authority = Evidence Level × Institution Authority（二维评分）
        - Impact = domain_relevance × keyword_impact（领域相关）
        - Recency = 时间衰减（低权重 0.05）

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

        # 1. 计算 Authority（二维评分：Evidence Level × Institution）
        authority_result = calculate_authority_score(source, title, summary)
        authority_total = authority_result["authority_total"]
        evidence_level = authority_result["evidence_level"]
        institution_score = authority_result["institution"]

        # 2. 计算相关性分数（BM25 + 关键词匹配）
        relevance_score = self._calculate_relevance_score(text, user_interests)

        # 3. 计算图传播系数（系数方式：exact=1.0, hop1=0.5, hop2=0.25）
        article_tags = article.get("tags", [])
        tag_names = []
        for t in article_tags:
            if isinstance(t, dict):
                tag_names.append(t.get("name", ""))
            elif isinstance(t, str):
                tag_names.append(t)
        graph_result = self.graph_scorer.calculate_graph_score(tag_names, user_interests)
        graph_coefficient = graph_result.get("graph_coefficient", 0.0)

        # 4. 计算领域相关的 Impact 分数
        impact_result = calculate_impact_score(
            text, user_interests, self.graph_scorer
        )
        impact_score = impact_result["impact_score"]

        # 5. 计算时效性分数（低权重）
        recency_score = self._calculate_recency_score(published_at)

        # 6. 综合评分公式（新权重分配）
        # ontology_relevance = 基础相关性 + 图传播加成（加法，不是乘法门控）
        ontology_relevance = relevance_score * 0.6 + graph_coefficient * 0.4

        total_score = (
            self.WEIGHTS["ontology_relevance"] * ontology_relevance +
            self.WEIGHTS["authority"] * authority_total +
            self.WEIGHTS["impact"] * impact_score +
            self.WEIGHTS["recency"] * recency_score
        )

        # 归一化到 0-1
        total_score = min(1.0, max(0.0, total_score))

        return {
            "total_score": round(total_score, 4),
            # Authority 详情
            "authority_total": authority_total,
            "evidence_level": evidence_level,
            "institution_score": institution_score,
            # Relevance
            "relevance_score": round(relevance_score, 4),
            # Graph
            "graph_coefficient": round(graph_coefficient, 4),
            "graph_matched_seeds": graph_result.get("matched_seeds", []),
            # Impact
            "impact_score": impact_score,
            "impact_keywords": impact_result.get("detected_keywords", []),
            "impact_domain_relevance": impact_result.get("domain_relevance", 0.0),
            # Recency
            "recency_score": round(recency_score, 4),
            # Ontology relevance (combined)
            "ontology_relevance": round(ontology_relevance, 4),
            # 诊断用
            "has_match": relevance_score > 0.2 or graph_coefficient > 0.1,
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
                # Authority
                "authority_total": result["authority_total"],
                "evidence_level": result["evidence_level"],
                "institution_score": result["institution_score"],
                # Relevance
                "relevance_score": result["relevance_score"],
                # Graph
                "graph_coefficient": result["graph_coefficient"],
                "graph_matched_seeds": result.get("graph_matched_seeds", []),
                # Impact
                "impact_score": result["impact_score"],
                "impact_keywords": result.get("impact_keywords", []),
                # Recency
                "recency_score": result["recency_score"],
                # Ontology relevance
                "ontology_relevance": result["ontology_relevance"],
                # Match flag
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

        # 归一化 BM25 得分：用对数函数避免硬阈值，更平滑
        # log(1+x) 增长慢，对高分文章不惩罚太狠
        bm25_score = min(math.log(1 + bm25_raw) / math.log(2 + bm25_raw), 1.0) * 0.6

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

    def __init__(self):
        """Initialize ArticleTagger with DomainGraph for Wikidata resolution."""
        from .domain_graph import DomainGraph
        from .wikidata import WikidataResolver
        from .memory import OntologyMemory

        data_dir = os.getenv("DATA_DIR", "./data")
        memory = OntologyMemory(data_dir=data_dir)
        wikidata = WikidataResolver()
        self.domain_graph = DomainGraph(memory=memory, wikidata=wikidata)

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

        # Resolve tags through Wikidata to get QIDs
        for tag in detected_tags:
            tag_name = tag.get("name", "")
            if not tag_name:
                continue

            # Try to resolve through DomainGraph
            try:
                qid = self.domain_graph.resolve_and_add(tag_name)
                tag["wikidata_qid"] = qid

                # Get node details if available
                node_data = self.domain_graph.get_node_by_qid(qid)
                if node_data:
                    tag["wikidata_label"] = node_data.get("label", tag_name)
                    tag["wikidata_description"] = node_data.get("description", "")
            except Exception:
                # If resolution fails, tag still works without QID
                tag["wikidata_qid"] = None

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


def reset_article_tagger():
    """Reset global ArticleTagger instance (for testing or reinitialization)"""
    global _tagger
    _tagger = None


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
            "authority_total": scored["authority_total"],
            "relevance_score": scored["relevance_score"],
            "impact_score": scored["impact_score"],
            "graph_coefficient": scored["graph_coefficient"],
            "ontology_relevance": scored["ontology_relevance"],
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
    "GraphPropagationScorer",
    "get_priority_scorer",
    "get_article_tagger",
    "get_graph_propagation_scorer",
    "score_and_tag_articles",
    "get_recency_score",
    "get_authority_score",
]
