---
name: translator
description: "多语言翻译，支持中英文互译及其他语言"
metadata:
  builtin_skill_version: "1.0"
  copaw:
    emoji: "🌐"
    requires:
      tools: ["translate_text", "get_entry_content"]
---

# Translator

多语言翻译助手，支持文章和内容的翻译需求。

## When to Use

- 用户请求翻译特定内容
- 阅读外文文章需要中文翻译
- 将中文内容翻译成英文
- 理解多语言RSS源的内容

## How to Use

### 步骤 1: 获取原始内容

使用 `get_entry_content` 获取需要翻译的内容：

```
get_entry_content(entry_id="<entry_id>")
```

### 步骤 2: 执行翻译

使用 `translate_text` 工具进行翻译：

```
translate_text(text="<原文>", target_lang="zh")
```

### 支持的目标语言

| 语言代码 | 语言 |
|---------|------|
| zh | 中文（简体） |
| en | 英语 |
| ja | 日语 |
| ko | 韩语 |
| fr | 法语 |
| de | 德语 |
| es | 西班牙语 |

### 步骤 3: 返回翻译结果

```json
{
  "original": {
    "text": "原文",
    "language": "en"
  },
  "translation": {
    "text": "译文",
    "language": "zh"
  },
  "quality": "high/medium/low",
  "notes": "翻译说明或注释"
}
```

## 翻译类型

### 1. 全文翻译
- 翻译整篇文章
- 保留原文结构和格式
- 适用于深度阅读

### 2. 摘要翻译
- 翻译文章摘要或关键段落
- 保留核心信息
- 适用于快速浏览

### 3. 即时翻译
- 翻译用户输入的短文本
- 即时响应
- 适用于查询和对话

## Tools

- `translate_text`: 执行翻译
- `get_entry_content`: 获取需要翻译的文章内容

## Example

### 示例 1: 翻译文章

```
用户: 帮我翻译这篇英文文章

助手:
1. get_entry_content 获取文章内容
2. 分析语言(English)
3. 翻译为中文
4. 返回完整译文
```

### 示例 2: 翻译指定段落

```
用户: 把这段话翻译成英文：人工智能正在改变医疗诊断

助手:
1. 调用 translate_text(text="人工智能正在改变医疗诊断", target_lang="en")
2. 返回: "AI is transforming medical diagnosis"
```

## Best Practices

1. **明确目标语言** - 确认用户想要的翻译方向
2. **保留专有名词** - 人名、品牌名等保留原文
3. **理解上下文** - 同一词在不同领域有不同翻译
4. **标注语言** - 明确说明原文和译文语言
5. **提供备选** - 关键术语可提供多种译法

## 注意事项

1. **机器翻译局限** - 复杂专业内容可能需要人工校对
2. **文化差异** - 某些表达可能需要本地化调整
3. **专业术语** - 医学、法律等专业领域建议核实
