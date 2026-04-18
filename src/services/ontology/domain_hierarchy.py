# -*- coding: utf-8 -*-
"""
Domain Hierarchy - Hierarchical domain classification for cross-domain content analysis.

DEPRECATION WARNING:
This module is deprecated in favor of the dynamic DomainGraph system with Wikidata integration.
The hardcoded DOMAIN_HIERARCHY is being phased out. New code should use:
- DomainGraph for dynamic graph-based domain relationships
- WikidataResolver for entity standardization
- Layer 2 (Wikidata-aligned) and Layer 3 (custom entities) instead of Level 0-1 backbone

This module is kept for backward compatibility during the transition period.

This module defines a domain hierarchy inspired by Publication_research's domain system,
supporting multi-level domains and cross-domain concept detection.

Domain Levels:
- Level 0: Root domains (broadest)
- Level 1: Primary domains
- Level 2: Secondary domains (e.g., MedicalAI)
- Level 3: Tertiary domains (e.g., HER2_ADC)
- Level 4+: Specific entities

Cross-Domain Concepts:
- MedicalAI: Intersection of AI and Medical
- DigitalHealth: Intersection of Digital and Healthcare
- FinTech: Intersection of Finance and Technology
"""

import warnings

# Issue deprecation warning when module is imported
warnings.warn(
    "domain_hierarchy module is deprecated. Use DomainGraph with WikidataResolver instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Dict, List

# Domain Hierarchy Definition
# Each domain has: level, description, aliases (EN/CN), parent, children
DOMAIN_HIERARCHY: Dict[str, Dict] = {
    # ========== Level 0: Root Domains ==========
    "Technology": {
        "level": 0,
        "description": "Technology and computing",
        "aliases": ["tech", "technology", "计算机", "科技"],
        "children": ["AI", "Software", "Hardware", "Internet"],
        "cross_domains": ["MedicalAI", "FinTech", "EduTech"],
    },
    "Medical": {
        "level": 0,
        "description": "Medical and healthcare",
        "aliases": ["medical", "healthcare", "health", "医疗", "健康", "医药"],
        "children": ["Pharmaceutical", "MedicalTechnology", "Healthcare", "Biotechnology"],
        "cross_domains": ["MedicalAI", "DigitalHealth", "MedTech"],
    },
    "Science": {
        "level": 0,
        "description": "Scientific research",
        "aliases": ["science", "scientific", "科学研究", "科学"],
        "children": ["Physics", "Chemistry", "Biology", "Environment"],
        "cross_domains": ["AI4Science"],
    },
    "Business": {
        "level": 0,
        "description": "Business and commerce",
        "aliases": ["business", "commerce", "商业", "商务", "企业"],
        "children": ["Finance", "Marketing", "Management", "Startup"],
        "cross_domains": ["FinTech", "MarTech"],
    },
    "Finance": {
        "level": 0,
        "description": "Finance and investment",
        "aliases": ["finance", "financial", "investment", "金融", "投资", "财务"],
        "children": ["Banking", "Stock", "Crypto", "Insurance"],
        "cross_domains": ["FinTech"],
    },
    "Education": {
        "level": 0,
        "description": "Education and learning",
        "aliases": ["education", "learning", "教育", "学习", "学术"],
        "children": ["K12", "HigherEd", "OnlineLearning", "EdTech"],
        "cross_domains": ["EduTech"],
    },
    "Society": {
        "level": 0,
        "description": "Society and culture",
        "aliases": ["society", "culture", "社会", "文化"],
        "children": ["Politics", "Law", "Environment", "SocialIssues"],
        "cross_domains": [],
    },
    "Entertainment": {
        "level": 0,
        "description": "Entertainment and media",
        "aliases": ["entertainment", "media", "娱乐", "媒体"],
        "children": ["Movies", "Music", "Gaming", "Sports"],
        "cross_domains": [],
    },

    # ========== Level 1: Primary Subdomains ==========
    "AI": {
        "level": 1,
        "description": "Artificial Intelligence",
        "aliases": ["ai", "artificial intelligence", "人工智能", "AI技术"],
        "parent": "Technology",
        "children": ["MachineLearning", "DeepLearning", "NLP", "ComputerVision"],
        "cross_domains": ["MedicalAI", "FinTech", "EduTech", "AI4Science", "AIAgent"],
    },
    "Software": {
        "level": 1,
        "description": "Software development",
        "aliases": ["software", "programming", "软件开发", "编程", "程序"],
        "parent": "Technology",
        "children": ["WebDev", "MobileDev", "CloudComputing", "OpenSource"],
        "cross_domains": [],
    },
    "Hardware": {
        "level": 1,
        "description": "Hardware and electronics",
        "aliases": ["hardware", "electronics", "硬件", "电子"],
        "parent": "Technology",
        "children": ["Semiconductor", "Robotics", "IoT", "ConsumerElectronics"],
        "cross_domains": ["MedTech"],
    },
    "Internet": {
        "level": 1,
        "description": "Internet and web",
        "aliases": ["internet", "web", "互联网", "网络"],
        "parent": "Technology",
        "children": ["SocialMedia", "ECommerce", "SaaS", "Cybersecurity"],
        "cross_domains": ["DigitalHealth", "EdTech"],
    },

    "Pharmaceutical": {
        "level": 1,
        "description": "Pharmaceutical industry",
        "aliases": ["pharmaceutical", "pharma", "drug", "制药", "医药", "药品"],
        "parent": "Medical",
        "children": ["SmallMolecule", "Biotech", "Generic", "Vaccine"],
        "cross_domains": ["MedicalAI", "DigitalHealth"],
    },
    "MedicalTechnology": {
        "level": 1,
        "description": "Medical technology",
        "aliases": ["medical technology", "medtech", "医疗技术", "医疗器械"],
        "parent": "Medical",
        "children": ["MedicalAI", "MedicalDevices", "MedicalImaging", "SurgicalRobotics"],
        "cross_domains": ["MedicalAI"],
    },
    "Healthcare": {
        "level": 1,
        "description": "Healthcare services",
        "aliases": ["healthcare", "hospital", "clinical", "医疗服务", "医院", "临床"],
        "parent": "Medical",
        "children": ["HospitalManagement", "Telemedicine", "HealthInsurance", "PublicHealth"],
        "cross_domains": ["DigitalHealth"],
    },
    "Biotechnology": {
        "level": 1,
        "description": "Biotechnology",
        "aliases": ["biotech", "biotechnology", "生物技术", "生物科技"],
        "parent": "Medical",
        "children": ["GeneEditing", "CellTherapy", "Proteomics", "SyntheticBiology"],
        "cross_domains": ["MedicalAI"],
    },

    # ========== Level 2: Secondary Cross-Domain Subdomains ==========
    "MedicalAI": {
        "level": 2,
        "description": "AI in medical and healthcare",
        "aliases": [
            "medical ai", "ai medical", "healthcare ai", "ai healthcare",
            "AI医疗", "医疗AI", "人工智能医疗", "智能医疗",
            "artificial intelligence in healthcare", "medical machine learning",
            "clinical AI", "AI诊断", "智能诊断",
        ],
        "parent": "MedicalTechnology",
        "children": ["AI4DrugDiscovery", "ClinicalAI", "MedicalImagingAI", "HealthcareAI", "AIMedicalDiagnosis"],
        "cross_domains": [],
    },
    "DigitalHealth": {
        "level": 2,
        "description": "Digital health solutions",
        "aliases": [
            "digital health", "digital healthcare", "health tech",
            "数字健康", "数字医疗", "健康科技", "医疗数字化",
            "telemedicine", "telehealth", "远程医疗",
            "health app", "wellness app", "健康管理",
        ],
        "parent": "Healthcare",
        "children": ["Telemedicine", "HealthApps", "Wearables", "HealthData"],
        "cross_domains": [],
    },
    "FinTech": {
        "level": 2,
        "description": "Financial technology",
        "aliases": [
            "fintech", "financial technology", "financial tech",
            "金融科技", "科技金融", " fintech",
            "payment", "payments", "支付", " payments",
        ],
        "parent": "Finance",
        "children": ["DigitalPayment", "Blockchain", "InsurTech", "WealthTech"],
        "cross_domains": [],
    },
    "EduTech": {
        "level": 2,
        "description": "Educational technology",
        "aliases": [
            "edtech", "educational technology", "education tech",
            "教育科技", "教育技术", "智慧教育",
            "e-learning", "online education", "在线教育",
        ],
        "parent": "Education",
        "children": ["OnlineLearning", "EdAI", "SmartClassroom", "EdPlatform"],
        "cross_domains": [],
    },
    "AI4Science": {
        "level": 2,
        "description": "AI for scientific research",
        "aliases": [
            "ai for science", "ai science", "scientific AI", "AI science",
            "AI科学", "科学智能", "AI驱动的科学研究",
            "ai in research", "computational biology", "计算生物学",
        ],
        "parent": "Science",
        "children": ["AIBio", "AIChemistry", "AIPhysics", "ClimateAI"],
        "cross_domains": [],
    },
    "AIAgent": {
        "level": 2,
        "description": "AI agents and autonomous systems",
        "aliases": [
            "ai agent", "ai agents", "agentic ai", "autonomous ai",
            "AI智能体", "AI代理", "智能代理", "自主AI",
            "agent", "agentic", "autonomous", "agentic AI",
        ],
        "parent": "AI",
        "children": ["RAG", "ToolUse", "MultiAgent", "AutonomousAgent"],
        "cross_domains": [],
    },
    "MarTech": {
        "level": 2,
        "description": "Marketing technology",
        "aliases": [
            "martech", "marketing technology", "marketing tech",
            "营销科技", "营销技术", "数字营销",
        ],
        "parent": "Business",
        "children": ["MarketingAI", "CRM", "Analytics", "Advertising"],
        "cross_domains": [],
    },
    "MedTech": {
        "level": 2,
        "description": "Medical device technology",
        "aliases": [
            "medtech", "medical device", "medical equipment",
            "医疗设备", "医疗器械", "医疗装置",
        ],
        "parent": "MedicalTechnology",
        "children": ["Implant", "Diagnostic", "Monitoring", "Surgical"],
        "cross_domains": [],
    },

    # ========== Level 3: Detailed Subdomains ==========
    "MachineLearning": {
        "level": 3,
        "description": "Machine learning",
        "aliases": ["machine learning", "ml", "机器学习"],
        "parent": "AI",
        "children": ["SupervisedLearning", "UnsupervisedLearning", "ReinforcementLearning"],
        "cross_domains": [],
    },
    "DeepLearning": {
        "level": 3,
        "description": "Deep learning",
        "aliases": ["deep learning", "dl", "深度学习"],
        "parent": "AI",
        "children": ["NeuralNetwork", "Transformer", "CNN", "RNN"],
        "cross_domains": [],
    },
    "NLP": {
        "level": 3,
        "description": "Natural language processing",
        "aliases": ["nlp", "natural language processing", "自然语言处理", "NLP"],
        "parent": "AI",
        "children": ["LLM", "TextMining", "SentimentAnalysis", "MachineTranslation"],
        "cross_domains": [],
    },
    "LLM": {
        "level": 4,
        "description": "Large language models",
        "aliases": ["llm", "large language model", "大语言模型", "LLM", "语言模型"],
        "parent": "NLP",
        "children": ["GPT", "Claude", "Gemini", "OpenSourceLLM"],
        "cross_domains": [],
    },
    "ComputerVision": {
        "level": 3,
        "description": "Computer vision",
        "aliases": ["computer vision", "cv", "图像识别", "计算机视觉"],
        "parent": "AI",
        "children": ["ImageClassification", "ObjectDetection", "Segmentation"],
        "cross_domains": [],
    },
    "MedicalImagingAI": {
        "level": 3,
        "description": "AI for medical imaging",
        "aliases": [
            "medical imaging ai", "ai medical imaging", "radiology ai",
            "AI医学影像", "医学影像AI", "放射学AI",
            "AI诊断影像", "医学图像识别",
        ],
        "parent": "MedicalAI",
        "children": ["CTAI", "MRIAI", "XrayAI", "PathologyAI"],
        "cross_domains": [],
    },
    "ClinicalAI": {
        "level": 3,
        "description": "AI for clinical applications",
        "aliases": [
            "clinical ai", "ai clinical", "clinical decision support",
            "AI临床", "临床AI", "临床决策支持",
            " CDS", "electronic health record ai",
        ],
        "parent": "MedicalAI",
        "children": ["DiagnosisAI", "TreatmentAI", "DrugInteractionAI"],
        "cross_domains": [],
    },
    "AI4DrugDiscovery": {
        "level": 3,
        "description": "AI for drug discovery",
        "aliases": [
            "ai drug discovery", "ai pharma", "computational drug",
            "AI药物发现", "AI制药", "计算药物设计",
            "drug discovery ai", "ai discovery",
        ],
        "parent": "MedicalAI",
        "children": ["VirtualScreening", "MolecularDynamics", "ADMETPrediction"],
        "cross_domains": [],
    },
    "HealthcareAI": {
        "level": 3,
        "description": "AI for healthcare management",
        "aliases": [
            "healthcare ai", "hospital ai", "ai healthcare management",
            "AI医院管理", "医疗管理AI", "智慧医院",
        ],
        "parent": "MedicalAI",
        "children": ["PatientFlowAI", "ResourceAI", "RevenueCycleAI"],
        "cross_domains": [],
    },
    "AIMedicalDiagnosis": {
        "level": 3,
        "description": "AI medical diagnosis",
        "aliases": [
            "ai diagnosis", "ai diagnostic", "computer aided diagnosis",
            "AI诊断", "智能诊断", "计算机辅助诊断",
            "cad", "诊断AI", "medical diagnosis ai",
        ],
        "parent": "MedicalAI",
        "children": [],
        "cross_domains": [],
    },
    "Telemedicine": {
        "level": 3,
        "description": "Telemedicine and remote care",
        "aliases": ["telemedicine", "telehealth", "远程医疗", "线上医疗"],
        "parent": "DigitalHealth",
        "children": ["VirtualVisit", "RemoteMonitoring", "TeleICU"],
        "cross_domains": [],
    },
    "HealthApps": {
        "level": 3,
        "description": "Health and wellness applications",
        "aliases": ["health app", "wellness app", "健康应用", "健康App"],
        "parent": "DigitalHealth",
        "children": ["MentalHealth", "Fitness", "Diet", "Sleep"],
        "cross_domains": [],
    },
    "Wearables": {
        "level": 3,
        "description": "Wearable health devices",
        "aliases": ["wearable", "wearable device", "可穿戴设备", "智能穿戴"],
        "parent": "DigitalHealth",
        "children": ["Smartwatch", "FitnessTracker", "MedicalWearable"],
        "cross_domains": [],
    },
    "Blockchain": {
        "level": 3,
        "description": "Blockchain technology",
        "aliases": ["blockchain", "crypto", "cryptocurrency", "区块链"],
        "parent": "FinTech",
        "children": ["DeFi", "Web3", "NFT", "DAO"],
        "cross_domains": [],
    },
    "DigitalPayment": {
        "level": 3,
        "description": "Digital payment systems",
        "aliases": ["digital payment", "mobile payment", "电子支付", "移动支付"],
        "parent": "FinTech",
        "children": ["MobileWallet", "Contactless", "CrossBorder"],
        "cross_domains": [],
    },
    "OnlineLearning": {
        "level": 3,
        "description": "Online learning platforms",
        "aliases": ["online learning", "e-learning", "在线学习", "网络课程"],
        "parent": "EduTech",
        "children": ["MOOC", "CoursePlatform", "LMS"],
        "cross_domains": [],
    },
    "EdAI": {
        "level": 3,
        "description": "AI in education",
        "aliases": ["ai education", "ai learning", "教育AI", "AI教育"],
        "parent": "EduTech",
        "children": ["AdaptiveLearning", "AI Tutor", "AutoGrading"],
        "cross_domains": [],
    },
    "RAG": {
        "level": 3,
        "description": "Retrieval augmented generation",
        "aliases": ["rag", "retrieval augmented generation", "RAG", "检索增强生成"],
        "parent": "AIAgent",
        "children": ["VectorDB", "KnowledgeGraph", "HybridSearch"],
        "cross_domains": [],
    },
    "AIBio": {
        "level": 3,
        "description": "AI in biology",
        "aliases": ["ai biology", "computational biology", "AI生物", "计算生物学"],
        "parent": "AI4Science",
        "children": ["ProteinFolding", "GenomicsAI", "DrugTargetAI"],
        "cross_domains": [],
    },
}


def get_domain_by_name(name: str) -> Dict:
    """Get domain info by name (case-insensitive)."""
    name_lower = name.lower()
    for domain, info in DOMAIN_HIERARCHY.items():
        if domain.lower() == name_lower:
            return info
        # Check aliases
        for alias in info.get("aliases", []):
            if alias.lower() == name_lower:
                return info
    return None


def get_cross_domain_parents(domain: str) -> List[str]:
    """Get parent domains that can form cross-domain with given domain."""
    domain_info = get_domain_by_name(domain)
    if not domain_info:
        return []
    return domain_info.get("cross_domains", [])


def get_all_aliases() -> Dict[str, List[str]]:
    """Get all aliases mapping to canonical domain names."""
    aliases = {}
    for domain, info in DOMAIN_HIERARCHY.items():
        aliases[domain] = info.get("aliases", [])
    return aliases


def detect_domains_in_text(text: str) -> List[Dict]:
    """
    Detect domains in text using keyword matching.

    Args:
        text: Input text (English or Chinese)

    Returns:
        List of detected domains with match info
    """
    text_lower = text.lower()
    detected = []

    for domain, info in DOMAIN_HIERARCHY.items():
        score = 0.0
        matches = []

        # Check main name
        if domain.lower() in text_lower:
            score += 1.0
            matches.append(domain)

        # Check aliases
        for alias in info.get("aliases", []):
            alias_lower = alias.lower()
            if alias_lower in text_lower:
                # Exact alias match
                if alias_lower == domain.lower():
                    continue  # Already counted
                score += 0.8
                matches.append(alias)

            # Substring match (for longer aliases)
            elif len(alias_lower) > 3 and alias_lower in text_lower:
                score += 0.5
                matches.append(alias)

        if score > 0:
            # Calculate depth weight (deeper = more specific)
            level = info.get("level", 0)
            depth_weight = 1.0 + (5 - level) * 0.1  # Higher for deeper domains

            detected.append({
                "domain": domain,
                "score": min(1.0, score * depth_weight / 10),
                "matches": matches,
                "level": level,
                "description": info.get("description", ""),
                "cross_domains": info.get("cross_domains", []),
            })

    # Sort by score descending
    detected.sort(key=lambda x: x["score"], reverse=True)
    return detected


def get_domain_hierarchy_path(domain: str) -> List[str]:
    """Get the full hierarchy path from root to domain."""
    path = []
    current = domain
    visited = set()

    while current and current not in visited:
        visited.add(current)
        path.insert(0, current)
        domain_info = get_domain_by_name(current)
        if not domain_info:
            break
        current = domain_info.get("parent", "")

    return path


def calculate_cross_domain_score(domain1: str, domain2: str) -> float:
    """
    Calculate cross-domain similarity between two domains.

    Returns:
        Score from 0.0 to 1.0 indicating cross-domain relationship strength
    """
    # Get hierarchy paths
    path1 = get_domain_hierarchy_path(domain1)
    path2 = get_domain_hierarchy_path(domain2)

    if not path1 or not path2:
        return 0.0

    # Find lowest common ancestor
    lca = None
    for i in range(min(len(path1), len(path2))):
        if path1[i] == path2[i]:
            lca = path1[i]
        else:
            break

    if not lca:
        return 0.0

    # Wu-Palmer similarity
    depth_lca = len(path1) + len(path2) - 2 * (len(path1) - path1.index(lca) - 1)
    # Simplified: depth_lca = position in path1 + position in path2

    lca_index1 = path1.index(lca)
    lca_index2 = path2.index(lca)
    depth_sum = (len(path1) - lca_index1) + (len(path2) - lca_index2)

    if depth_sum == 0:
        return 1.0

    wu_palmer = 2 * (len(path1) - lca_index1 - 1) / depth_sum if depth_sum > 0 else 0.0

    # Check if cross-domain (LCA is at level 0)
    lca_info = get_domain_by_name(lca)
    lca_level = lca_info.get("level", 0) if lca_info else 0

    if lca_level == 0:
        # Cross-domain case - boost semantic similarity
        cross_domain_info1 = get_domain_by_name(domain1)
        cross_domain_info2 = get_domain_by_name(domain2)
        cross1 = cross_domain_info1.get("cross_domains", []) if cross_domain_info1 else []
        cross2 = cross_domain_info2.get("cross_domains", []) if cross_domain_info2 else []

        # Direct cross-domain relationship
        if domain2 in cross1 or domain1 in cross2:
            return 0.7 + 0.3 * wu_palmer

        # Indirect (share same cross-domain parent)
        if set(cross1) & set(cross2):
            return 0.5 + 0.3 * wu_palmer

        return 0.3 + 0.3 * wu_palmer

    return 0.3 + 0.7 * wu_palmer


__all__ = [
    "DOMAIN_HIERARCHY",
    "get_domain_by_name",
    "get_cross_domain_parents",
    "get_all_aliases",
    "detect_domains_in_text",
    "get_domain_hierarchy_path",
    "calculate_cross_domain_score",
]
