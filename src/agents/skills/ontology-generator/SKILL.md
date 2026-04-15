---
name: ontology-generator
description: Generate comprehensive ontological knowledge graphs in [[wikilinks]] syntax for InfraNodus visualization. Use when the user requests to create an ontology, extract entities and relationships from text, or generate knowledge graph structures.
version: 1.0
---

# Ontology Generator for InfraNodus

Generate ontological knowledge graphs in InfraNodus format using [[wikilinks]] syntax. Output can be pasted directly into InfraNodus.com to visualize as a network and develop gaps and clusters with AI.

## Input Types

Accept two input types:

1. **Topic**: Generate comprehensive ontology for a given domain
2. **Text**: Extract ontological structure from provided text

## Entity Generation Principles

Generate comprehensive responses with multiple elements. Explore the full variety of entities belonging to the domain of inquiry. Include various types of:

- Entities
- Classes
- Relationships
- Axioms
- Rules

**Critical**: Avoid hierarchical structures with one central idea. First iteration should be comprehensive, long, and cover the widest possible domain. Generate network structures, not trees.

## Output Format

Each entity uses [[wikilink]] syntax. Relations are described in plain text within the same paragraph. Relation codes appear at paragraph end in [squarebrackets].

### Syntax Pattern

```
[[entity1]] relation description [[entity2]] [relationCode]
```

### Formatting Rules

- Each relation = separate paragraph line
- Minimum 8 paragraphs per relationship type
- Each statement MUST have at least 2 entities in [[wikilinks]]
- Each statement MUST have a [relationCode]

### Relation Codes

Use ONLY these relation codes (unless user provides alternatives):

- `[isA]` - Class membership
- `[partOf]` - Component relationship
- `[hasAttribute]` - Properties and characteristics
- `[relatedTo]` - General associations
- `[dependentOn]` - Dependencies
- `[causes]` - Causal relationships
- `[locatedIn]` - Spatial relationships
- `[occursAt]` - Temporal occurrences
- `[derivedFrom]` - Origin and derivation
- `[opposes]` - Contradictory relationships

## Scoring & Tagging Framework

For news article analysis and scoring, use the following ontology-based scoring system:

### Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| recency_score | 40% | How recent is the article |
| authority_score | 30% | Source credibility and type |
| relevance_score | 30% | Match with user interests/ontology |

### Recency Scoring

| Time Range | Score |
|------------|-------|
| < 1 hour | 1.0 |
| 1-6 hours | 0.9 |
| 6-12 hours | 0.8 |
| 12-24 hours | 0.7 |
| > 24 hours | 0.5 |

### Authority Scoring

| Source Type | Score |
|-------------|-------|
| 顶级期刊 (Nature, Science) | 1.0 |
| 顶会 (NeurIPS, ICML) | 0.95 |
| 预印本 (arXiv) | 0.9 |
| 权威媒体 (WSJ, FT) | 0.85 |
| 行业媒体 (TechCrunch) | 0.8 |
| 社交媒体 (Twitter) | 0.6 |

### Relevance Scoring

Based on ontology matching:
- User interest tags vs article tags
- Entity overlap with user's domain ontology
- Keyword matching against user topics

### Total Score Formula

```
total_score = recency_score * 0.4 + authority_score * 0.3 + relevance_score * 0.3
```

## Tagging Categories

Based on ontology structure, articles can be tagged with:

| Category | Description |
|----------|-------------|
| 技术 (Technology) | AI, Cloud, Security, etc. |
| 商业 (Business) | Strategy, Finance, Marketing, etc. |
| 科学 (Science) | Research, Innovation, etc. |
| 行业 (Industry) | Healthcare, Finance, Education, etc. |
| 政策 (Policy) | Regulations, Government, etc. |

## Workflow for News Analysis

1. **Extract Content**: Get article title, summary, source, date
2. **Match Ontology**: Compare against user interest ontology
3. **Calculate Scores**: Compute recency, authority, relevance
4. **Generate Tags**: Based on topic/industry ontology
5. **Output Results**: Return scores and tags

## Example: News Analysis with Ontology

```
Article: "OpenAI 发布 GPT-5"
- Source: OpenAI Blog
- Published: 2 hours ago
- User Interest: AI, 大模型, OpenAI

Analysis:
- recency_score: 0.9 (< 6 hours)
- authority_score: 0.95 (Official source)
- relevance_score: 0.85 (High match with user interests)
- total_score: 0.9

Tags: ["AI", "大模型", "OpenAI", "技术"]
```
