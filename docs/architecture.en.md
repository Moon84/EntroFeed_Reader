# EntroFeed Architecture Documentation

## Overview

EntroFeed is an intelligent RSS reader that combines traditional feed aggregation with LLM-powered recommendations. The architecture follows a modular design with clear separation of concerns.

## System Components

### Backend Layer (FastAPI)

#### Core Components

**app.py** - FastAPI Application
- Main entry point for the web server
- Route definitions for all API endpoints
- Lifespan management for startup/shutdown
- Static file mounting for frontend assets

**backend.py** - EntroFeedBackend
- Core business logic handler
- Feed and entry management
- Settings and handler configuration
- Health checks and about information

**rss.py** - EntroFeedRSS
- RSS/Atom feed parsing via feedparser
- Feed polling and update checking
- OPML import/export
- Backup and restore functionality

#### Storage Layer

**storage/** - Storage Handlers
- `sqlite_storage.py` - SQLite + ChromaDB implementation
- Interface for adding new storage backends

**Storage Interface Requirements:**
- `get_feeds()`, `upsert_feed()`, `delete_feed()`
- `get_entries()`, `get_feed_entry()`, `upsert_feed_entry()`
- `get_settings()`, `upsert_settings()`
- `get_handlers()`, `upsert_handler()`
- `get_poll_state()`, `set_poll_state()`, `update_poll_state()`

#### Recommendation Engine

**recommender/** - Recommendation System
- `similar.py` - Content-based similarity recommendations
- `interest_based.py` - User interest-based recommendations
- `trending.py` - Trending content recommendations

**Ontology System**
- `registry.py` - Central ontology registry
- `priority_scorer.py` - Article priority scoring
- Memory system for tracking user interests

#### Agent System

**agents/** - AI Agent Implementation
- `entrofeed_agent.py` - Main agent class (extends ReActAgent)
- `tools.py` - Built-in tools for agent operations
- `skills_manager.py` - Skill loading and execution

**Agent Tools:**
- `list_feeds` - List all RSS feeds
- `get_feed_entries` - Get entries from a feed
- `get_entry_content` - Get full content of an entry
- `search_entries` - Search entries by query
- `get_user_interests` - Get user interests
- `add_user_interest` - Add a user interest
- `get_daily_digest` - Generate daily digest
- `translate_text` - Translate content

#### Handler System

**llm/** - LLM Handler
- Unified interface for multiple LLM providers
- Support for DashScope, Ollama, OpenAI
- `create_llm_handler()` factory function

**notification/** - Notification Handlers
- `ntfy.py` - ntfy.sh notifications
- `jira.py` - Jira tickets
- Matrix, Slack support via simplematrixbotlib and slack_sdk

**impls/** - Handler Registration
- `load_storage_config()` - Load configured storage handler
- Handler registry for content retrieval, LLM, notifications

### Frontend Layer (React)

#### Pages

- `Dashboard.tsx` - Main dashboard with statistics
- `FeedList.tsx` - Feed management
- `FeedEntries.tsx` - Entry list for a feed
- `ArticleReader.tsx` - Full article reading view
- `Recommendations.tsx` - Recommendation tabs
- `Agent.tsx` - AI Assistant chat interface
- `Settings.tsx` - Global settings
- `Onboarding.tsx` - First-time setup wizard

#### Components

- `Layout.tsx` - App layout with sidebar navigation
- `EntryCard.tsx` - Feed entry card component
- `FeedCard.tsx` - Feed card component

#### State Management

- React Query for server state
- React Router for navigation
- i18n for internationalization

### API Endpoints

#### Feed Management
- `GET /feeds/` - List all feeds
- `GET /feeds/{id}` - Get feed configuration
- `POST /api/update_feed/` - Create/update feed
- `GET /api/refresh_feed/{feed_id}` - Refresh single feed
- `GET /api/delete_feed/{feed_id}` - Delete feed

#### Entry Management
- `GET /recent/` - Recent entries across all feeds
- `GET /list-entries/{feed_id}` - Entries for specific feed
- `GET /read/{feed_entry_id}` - Full entry content

#### Recommendations
- `GET /api/recommendations/interest` - Interest-based recommendations
- `GET /api/recommendations/trending` - Trending recommendations
- `GET /api/recommendations/similar/{entry_id}` - Similar entries

#### User Interests
- `GET /api/interests` - List user interests
- `POST /api/interests` - Add new interest
- `DELETE /api/interests/{interest_id}` - Remove interest
- `PATCH /api/interests/{interest_id}` - Update interest priority

#### Settings
- `GET /settings/` - Settings page
- `POST /api/update_settings/` - Update settings

#### Backup/Restore
- `GET /api/export_opml/` - Export feeds as OPML
- `GET /api/backup/` - Full JSON backup
- `POST /api/restore/` - Restore from backup
- `POST /api/import_opml/` - Import OPML

#### Agent Chat
- `POST /api/agent/chat` - Send message to agent (with session context)
- `GET /api/agent/sessions` - List all chat sessions
- `POST /api/agent/sessions` - Create new chat session
- `GET /api/agent/sessions/{id}` - Get session with message history
- `DELETE /api/agent/sessions/{id}` - Delete chat session
- `POST /api/agent/sessions/{id}/clear` - Clear session messages

#### Translation
- `POST /api/translate` - Translate text using LLM

#### LLM Status
- `GET /api/llm/status` - Check LLM provider connectivity and model info
- `GET /api/llm/usage` - Get today's token usage statistics

#### Entry State Sync
- `PATCH /api/entries/{entry_id}` - Update entry read/like/favorite state

## Data Models

### Feed
```python
class Feed(BaseModel):
    id: str
    name: str
    url: str
    category: str
    preview_only: bool = False
    notify: bool = False
    refresh_enabled: bool = False
    use_script: bool = False
    retrieve_content: bool = False
```

### FeedEntry
```python
class FeedEntry(BaseModel):
    id: str
    feed_id: str
    title: str
    url: str
    published_at: int
    updated_at: int
    preview: Optional[str]
    content: Optional[str]
    authors: Optional[List[str]]
    total_score: Optional[float]
    recency_score: Optional[float]
    authority_score: Optional[float]
    relevance_score: Optional[float]
    impact_score: Optional[float]
    tags: Optional[List[Tag]]
    matched_interests: Optional[List[str]]
    has_ontology_match: Optional[bool]
    # State fields (added later)
    is_read: bool = False
    liked: int = 0  # -1, 0, 1
    is_favorite: bool = False
    read_at: Optional[int] = None
```

### GlobalSettings
```python
class GlobalSettings(BaseModel):
    send_notification: bool
    theme: str
    refresh_interval: int
    reading_speed: int
    notification_handler_key: Optional[str]
    llm_handler_key: Optional[str]
    content_retrieval_handler_key: Optional[str]
    recent_hours: int
    finished_onboarding: bool
```

### ChatSession
```python
class ChatSession(BaseModel):
    id: str
    title: str
    messages: List[ChatMessage]
    created_at: int
    updated_at: int

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: int
```

### LLMUsage
```python
class LLMUsage(BaseModel):
    date: str  # YYYY-MM-DD
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    request_count: int
```

## Storage Schema

### SQLite Tables

**feeds**
- id (TEXT PRIMARY KEY)
- name, url, category, type
- preview_only, notify, refresh_enabled, use_script, retrieve_content
- notify_destination
- poll_state (JSON)

**entries**
- id (TEXT PRIMARY KEY)
- feed_id (TEXT FOREIGN KEY)
- title, url, preview, content, authors (JSON)
- published_at, updated_at
- total_score, recency_score, authority_score, relevance_score, impact_score
- tags (JSON), matched_interests (JSON), has_ontology_match
- is_read, liked, is_favorite, read_at (state fields)

**entry_content**
- id (TEXT PRIMARY KEY)
- feed_id (TEXT FOREIGN KEY)
- content, summary, byline
- word_count, reading_time, reading_level
- unretrievable, banned

**handlers**
- id (TEXT PRIMARY KEY)
- type (handler_type enum)
- config (JSON)

**settings**
- Single row with all settings as JSON

### ChromaDB Collections

**content_embeddings**
- id: entry_id
- embedding: article content vector
- document: title + content text

## Recommendation Algorithms

### Similar Content (Vector Search)
1. Get current entry's content
2. Generate query embedding
3. Search ChromaDB for similar entries
4. Filter by minimum similarity threshold
5. Rank by similarity score

### Interest-Based Recommendations
1. Get user's explicit and inferred interests
2. Score all recent entries against interests
3. Weight by interest priority and match confidence
4. Return top N entries sorted by combined score

### Trending Recommendations
1. Aggregate entries from last 24-48 hours
2. Count mentions across feeds
3. Apply time decay weighting
4. Factor in authority scores
5. Return top trending entries

## Extension Points

### Adding a New LLM Handler
1. Create new file in `app/llm/`
2. Implement handler class with `get_content()` and `summarize()` methods
3. Register in `app/impls.py`
4. Add configuration schema

### Adding a New Storage Backend
1. Implement all methods from storage interface
2. Register in `load_storage_config()`
3. Ensure compatibility with ChromaDB embeddings

### Adding a New Notification Handler
1. Create new file in `app/notification/`
2. Implement `send_notification(feed, entry)` method
3. Register in handler registry

## Security Considerations

- API keys stored in configuration, not in code
- Backups contain secrets - treat as sensitive
- User agent identifies application for content owners
- Banned domains list prevents scraping blocked sites
