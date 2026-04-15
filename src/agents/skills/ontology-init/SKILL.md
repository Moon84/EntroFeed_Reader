---
name: ontology-init
description: 基于麦肯锡方法论的用户兴趣初始化 - 通过深度研究初始化精准用户兴趣画像
version: 1.0.0
tags:
  - ontology
  - user-interest
  - initialization
  - mcKinsey
  - research
---

# SKILL: 用户兴趣初始化 (User Interest Initialization)

**版本**: v1.0 | **方法论**: 麦肯锡 + MECE | **应用场景**: EntroFeed RSS 阅读器用户画像初始化

---

## 核心定位

帮助用户在 EntroFeed 中初始化精准的兴趣画像，通过麦肯锡式深度研究确定：
1. 用户关注的**技术赛道** (Technology Tracks)
2. 用户关注的**行业领域** (Industry Domains)
3. 优先级和权重分配 (Priorities & Weights)

---

## 一、输入类型

### 1.1 用户背景 (User Background)
```
用户背景信息:
- 职业: 研究人员/工程师/投资人/创业者/学生
- 领域: AI/医疗/金融/生物/教育
- 目标: 技术追踪/投资决策/学术研究/商业决策
- 经验: 入门/进阶/专家
```

### 1.2 研究方向初始化
```
研究方向类型:
- 横向研究: 跨领域技术趋势
- 纵向深耕: 单一领域深度跟踪
- 投资视角: 赛道评估与标的筛选
- 学术研究: 前沿进展与文献追踪
```

---

## 二、MECE 兴趣分类框架

### 2.1 一级分类 (L1 Categories)

使用 MECE 原则确保不重不漏:

| 类别 | 范围 | 关键词 |
|------|------|--------|
| **技术 (Technology)** | AI/ML, Software, Hardware, Infrastructure | AI, ML, model, algorithm, computing |
| **医疗健康 (Medical)** | 生物医药, 医疗器械, 健康服务 | medical, health, clinical, patient |
| **商业 (Business)** | 创业, 投资, 市场, 竞争 | startup, funding, market, competitor |
| **科学 (Science)** | 基础研究, 学术发表 | research, study, discovery, publication |
| **监管 (Regulatory)** | 政策, 合规, 标准 | policy, regulation, approval, FDA |

### 2.2 二级分类 (L2 Sub-categories)

**技术类**:
- AI/ML: 机器学习, 深度学习, LLM, NLP, CV
- Software: 编程语言, 框架, 开发工具
- Hardware: 芯片, GPU, 传感器
- Infrastructure: 云, 边缘, 存储, 网络

**医疗类**:
- 生物医药: 药物研发, 基因治疗, 抗体
- 医疗器械: 诊断设备, 手术机器人, 可穿戴
- 健康服务: 医院, 保险, 远程医疗

**商业类**:
- 创业: 融资, 退出, 孵化器
- 投资: VC, PE, 二级市场
- 市场: 规模, 增速, 竞争格局

### 2.3 三级标签 (L3 Tags)

具体兴趣标签 (从 feeds.yml category 提取):

```
Tier1-ArXiv:          arXiv cs.AI, cs.LG, cs.CV, q-bio
Tier1-Journals:       Nature Medicine, Nature Biotech, Nature Biomedical Eng
medRxiv:             General, Oncology, Neurology, Cardiovascular
Regulatory:          FDA, EMA, NIH
Industry-AI-Tech:    Google Health, Healthcare IT News, MedTech
Industry-Biotech:    STAT News, FierceBiotech, Endpoints News
Industry-VC:         TechCrunch Healthcare, FierceHealthcare
```

---

## 三、初始化流程

### Phase 1: Intake & Profiling (用户画像)

**执行步骤**:
1. 询问用户背景
2. 确定研究目标
3. 设定优先级

**输出模板**:
```
用户画像:
├─ 职业: [职业类型]
├─ 领域: [主要领域]
├─ 目标: [使用目的]
├─ 经验: [专业程度]
└─ 偏好: [内容类型偏好]
```

### Phase 2: MECE Interest Extraction (兴趣提取)

**MECE 分析框架**:
```
提取用户兴趣使用 MECE 不重不漏原则:

横向维度 (What):
├─ 技术类
│  ├─ AI/ML: [具体标签]
│  ├─ Software: [具体标签]
│  └─ Hardware: [具体标签]
├─ 医疗类
│  ├─ 生物医药: [具体标签]
│  ├─ 医疗器械: [具体标签]
│  └─ 健康服务: [具体标签]
├─ 商业类
│  ├─ 创业: [具体标签]
│  ├─ 投资: [具体标签]
│  └─ 市场: [具体标签]
└─ 科学类
   └─ [具体标签]

纵向维度 (Depth):
├─ 核心关注: [每天追踪]
├─ 定期关注: [每周追踪]
└─ 偶尔关注: [每月追踪]
```

### Phase 3: Priority Assignment (优先级分配)

**优先级矩阵**:
```
优先级 0-5:
5 - 核心兴趣: 每天必看, 影响决策
4 - 重要兴趣: 每周必看, 重要参考
3 - 一般兴趣: 每周关注, 保持了解
2 - 边缘兴趣: 偶尔了解, 不主动追踪
1 - 探索兴趣: 有空看看, 可能相关
0 - 已知无兴趣: 明确排除
```

**优先级判定规则**:
```
5分判定 (核心):
├─ 与职业直接相关
├─ 影响核心决策
└─ 每天都看

4分判定 (重要):
├─ 与领域高度相关
├─ 影响战略判断
└─ 每周主动追踪

3分判定 (一般):
├─ 领域相关但非核心
├─ 有价值但非关键
└─ 定期浏览
```

### Phase 4: Interest Verification (验证确认)

**验证清单**:
```
□ MECE 检验: 分类是否不重不漏
□ 优先级检验: 分数是否合理
□ 来源检验: 是否有对应的 RSS 源
□ 可执行性检验: 是否能持续追踪
```

---

## 四、输出格式

### 4.1 用户兴趣初始化 JSON

```json
{
  "user_profile": {
    "background": "研究人员",
    "domain": "AI + Medical",
    "goal": "技术追踪 + 投资决策",
    "expertise": "进阶"
  },
  "interests": [
    {
      "name": "artificial intelligence",
      "category": "technology",
      "priority": 5,
      "confidence": 1.0,
      "source": "explicit",
      "keywords": ["AI", "machine learning", "deep learning"]
    },
    {
      "name": "machine learning",
      "category": "technology",
      "priority": 5,
      "confidence": 1.0,
      "source": "explicit",
      "keywords": ["ML", "neural network", "algorithm"]
    },
    {
      "name": "medical research",
      "category": "medical",
      "priority": 4,
      "confidence": 0.9,
      "source": "explicit",
      "keywords": ["clinical", "treatment", "therapy"]
    }
  ],
  "feed_mappings": [
    {
      "interest": "artificial intelligence",
      "recommended_feeds": [
        "arXiv cs.AI",
        "arXiv cs.LG",
        "TechCrunch AI"
      ]
    },
    {
      "interest": "medical research",
      "recommended_feeds": [
        "Nature Medicine",
        "medRxiv General"
      ]
    }
  ],
  "verification": {
    "mece_valid": true,
    "total_interests": 7,
    "priority_distribution": {"5": 2, "4": 3, "3": 2}
  }
}
```

### 4.2 个性化订阅建议

```
推荐订阅 (基于兴趣):
├─ [Tier1-ArXiv] arXiv cs.AI - AI 核心必读
├─ [Tier1-ArXiv] arXiv cs.LG - ML 核心必读
├─ [Tier1-Journals] Nature Medicine - 医疗必读
├─ [medRxiv] medRxiv Oncology - 肿瘤次要
├─ [Industry-Biotech] FierceBiotech - 行业动态
└─ [Regulatory] FDA Press - 监管动态

可跳过 (低优先级):
├─ [娱乐类] - 无兴趣
└─ [体育类] - 无兴趣
```

---

## 五、触发指令

### 主触发词
```
初始化用户兴趣
设置我的兴趣
开始追踪 [领域]
我想了解 [技术/行业]
我的研究方向是 [方向]
配置 RSS 订阅
```

### 示例输入
```
输入1: 我是 AI 医疗研究者, 想追踪 AI 在医学影像和基因编辑领域的进展
输出: 生成包含 AI, ML, Medical Imaging, Gene Editing 等标签的兴趣画像

输入2: 我是医疗健康投资人, 关注创新药和医疗器械赛道
输出: 生成包含 Drug Development, Medical Device, Investment 等标签的兴趣画像

输入3: 帮我初始化 RSS 订阅, 我做 AI 研究
输出: 推荐 arXiv cs.AI, cs.LG, Nature ML 等订阅源
```

---

## 六、与 Skills 协作

### 可联动 Skills
| Skill | 协作场景 |
|-------|---------|
| `article_analyzer` | 分析文章时使用兴趣标签 |
| `daily_digest` | 生成个性化每日摘要 |
| `mckinsey-tech-analysis` | 深度技术赛道分析 |
| `translator` | 翻译外文内容 |

### 调用示例
```
→ 用 ontology-init 初始化用户兴趣
→ 用 article_analyzer 分析技术文章
→ 用 daily-digest 生成个性化摘要
→ 用 translator 翻译重要外文
```

---

## 七、质量标准

### 输出质量自检
```
【完整性检验】
□ 是否覆盖用户主要领域
□ 优先级是否反映真实需求
□ 是否有对应订阅源

【MECE 检验】
□ 分类是否不重不漏
□ 标签是否准确

【可执行性检验】
□ 兴趣是否可追踪
□ 订阅是否可操作
```

---

## 八、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2026-04-10 | 初始版本, 融合麦肯锡 MECE 框架 |

---

**创建时间**: 2026-04-10
**方法论来源**: 麦肯锡行业研究框架 + MECE 分类原则
**适用领域**: EntroFeed RSS 阅读器用户画像初始化
