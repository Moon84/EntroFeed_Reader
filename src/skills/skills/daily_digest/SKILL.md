---
name: daily_digest
description: "汇总多个条目形成每日简报，按优先级排序提取重点"
metadata:
  builtin_skill_version: "1.0"
  copaw:
    emoji: "📰"
    requires:
      tools: ["get_daily_digest", "get_high_priority_content"]
---

# Daily Digest

每日新闻摘要生成器，按优先级排序分门别类汇总。

## When to Use

- 用户请求获取"今日要闻"或"今日简报"
- 整理特定领域当天的最新动态
- 生成每日阅读清单
- 过滤高优先级内容

## How to Use

### 步骤 1: 获取当日内容

使用 `get_daily_digest` 获取当日内容：

```
get_daily_digest(date="2024-04-10")
```

或使用 `get_high_priority_content` 获取最高优先级内容：

```
get_high_priority_content(min_priority=4, limit=10)
```

### 步骤 2: 按类别分组

将内容按主题分类：
- **技术/AI**: 科技、AI、软件开发
- **医学健康**: 医疗、健康、生物技术
- **商业财经**: 金融、市场、商业动态
- **科学研究**: 学术、研究、发现
- **其他**: 不属于以上类别

### 步骤 3: 生成摘要

对每个类别生成简洁摘要：

```json
{
  "date": "2024-04-10",
  "categories": {
    "technology": {
      "count": 5,
      "items": [
        {
          "title": "文章标题",
          "priority": 5,
          "summary": "一句话摘要",
          "reason": "为什么重要"
        }
      ]
    }
  },
  "topStories": ["最重要3条"],
  "recommendedRead": ["推荐阅读2条"]
}
```

## 输出格式

### 简报结构

1. **今日要点 (Top 3)**
   - 当天最重要的3条新闻
   - 简要说明为什么值得关注

2. **分类汇总**
   - 每个类别下2-3条重点
   - 避免信息过载

3. **阅读建议**
   - 根据用户兴趣推荐
   - 标注优先级原因

### 优先级说明

| 优先级 | 含义 | 建议 |
|--------|------|------|
| 5 | 极高 - 必须关注 | 立即阅读 |
| 4 | 高 - 强烈推荐 | 今日阅读 |
| 3 | 中 - 有价值 | 有空阅读 |
| 2 | 低 - 可选 | 收藏备用 |
| 1 | 极低 | 可跳过 |

## Tools

- `get_daily_digest`: 获取指定日期的简报
- `get_high_priority_content`: 获取高优先级内容
- `get_user_interests`: 获取用户兴趣用于个性化推荐
- `list_feeds`: 列出所有订阅源

## Example

```
用户: 给我今天的新闻简报

助手:
1. 调用 get_daily_digest 获取今日内容
2. 按技术、医学、商业分类
3. 识别Top 3:
   - OpenAI发布新模型（技术，优先级5）
   - 新冠疫苗研究突破（医学，优先级5）
   - 美联储利率决策（商业，优先级4）
4. 生成分类摘要
5. 提供阅读建议
```

## Best Practices

1. **控制信息量** - 每日简报应该精炼，避免堆砌
2. **优先级排序** - 最重要的是在最前面
3. **个性化** - 根据用户兴趣调整推荐
4. **注明来源** - 让用户知道信息来自哪里
5. **简洁摘要** - 一句话说明为什么重要
