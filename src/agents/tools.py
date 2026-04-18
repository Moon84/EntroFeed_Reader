# -*- coding: utf-8 -*-
"""EntroFeed Agent Tools - Built-in tools for RSS/Feed operations."""

import json
import urllib.request
import urllib.parse
from datetime import datetime

from src.services.ontology import get_ontology_registry


# ============ RSS/Feed Tools ============

def list_feeds() -> str:
    """List all configured RSS feeds.

    Returns:
        JSON string with feed list
    """
    from src.backend import EntroFeedBackend
    from src.storage.singleton import get_storage

    storage = get_storage()
    backend = EntroFeedBackend(db=storage)
    feeds = backend.list_feeds()

    return json.dumps({
        "count": len(feeds),
        "feeds": feeds
    }, indent=2)


def get_feed_entries(feed_id: str = None, limit: int = 20) -> str:
    """Get entries from a specific feed or recent entries.

    Args:
        feed_id: Feed ID (optional, if None gets recent entries)
        limit: Maximum entries to return

    Returns:
        JSON string with entries
    """
    from src.backend import EntroFeedBackend
    from src.storage.singleton import get_storage

    storage = get_storage()
    backend = EntroFeedBackend(db=storage)

    if feed_id:
        entries = list(backend.list_entries(feed_id=feed_id))
    else:
        entries = list(backend.list_entries(feed_id=None, recent=True))

    entries = entries[:limit]

    return json.dumps({
        "count": len(entries),
        "entries": entries
    }, indent=2)


def get_entry_content(feed_entry_id: str) -> str:
    """Get full content of a feed entry.

    Args:
        feed_entry_id: Entry ID

    Returns:
        JSON string with entry content
    """
    import asyncio
    from src.backend import EntroFeedBackend
    from src.storage.singleton import get_storage

    storage = get_storage()
    backend = EntroFeedBackend(db=storage)

    async def get_content():
        return await backend.get_entry_content(feed_entry_id=feed_entry_id)

    content = asyncio.run(get_content())

    return json.dumps(content, indent=2, default=str)


def search_entries(query: str, limit: int = 10) -> str:
    """Search entries by title or content.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        JSON string with matching entries
    """
    from src.backend import EntroFeedBackend
    from src.storage.singleton import get_storage

    storage = get_storage()
    backend = EntroFeedBackend(db=storage)

    # Simple search implementation
    all_feeds = backend.list_feeds()
    results = []

    for feed in all_feeds:
        entries = list(backend.list_entries(feed_id=feed["id"]))
        for entry in entries:
            if query.lower() in entry.get("title", "").lower():
                results.append(entry)
            elif query.lower() in entry.get("content", "").lower():
                results.append(entry)

    return json.dumps({
        "count": len(results),
        "query": query,
        "entries": results[:limit]
    }, indent=2, default=str)


# ============ Ontology/Interest Tools ============

def get_user_interests(category: str = None) -> str:
    """Get user interests.

    Args:
        category: Optional category filter

    Returns:
        JSON string with user interests
    """
    from src.services.ontology.types import InterestCategory

    registry = get_ontology_registry()

    cat = None
    if category:
        try:
            cat = InterestCategory(category.lower())
        except ValueError:
            pass

    interests = registry.get_user_interests(category=cat)

    return json.dumps({
        "count": len(interests),
        "interests": [i.to_dict() for i in interests]
    }, indent=2, default=str)


def add_user_interest(
    name: str,
    category: str = "other",
    priority: int = 3
) -> str:
    """Add explicit user interest.

    Args:
        name: Interest name (tag)
        category: Category
        priority: Priority (0-5)

    Returns:
        JSON string with result
    """
    from src.services.ontology.types import InterestTag, InterestCategory, TagSource

    registry = get_ontology_registry()

    try:
        cat = InterestCategory(category.lower())
    except ValueError:
        cat = InterestCategory.OTHER

    tag = InterestTag(
        name=name.lower(),
        category=cat,
        source=TagSource.EXPLICIT,
        confidence=1.0
    )

    interest = registry.add_interest(tag, priority)

    return json.dumps({
        "success": True,
        "interest": interest.to_dict()
    }, indent=2, default=str)


def remove_user_interest(interest_id: str) -> str:
    """Remove user interest.

    Args:
        interest_id: Interest ID to remove

    Returns:
        JSON string with result
    """

    registry = get_ontology_registry()
    success = registry.remove_interest(interest_id)

    return json.dumps({
        "success": success,
        "interest_id": interest_id
    }, indent=2, default=str)


def get_high_priority_content(min_priority: int = 3, limit: int = 10) -> str:
    """Get high priority content.

    Args:
        min_priority: Minimum priority threshold
        limit: Maximum results

    Returns:
        JSON string with high priority content
    """

    registry = get_ontology_registry()
    profiles = registry.get_content_by_priority(
        min_priority=min_priority,
        limit=limit
    )

    return json.dumps({
        "count": len(profiles),
        "profiles": [p.to_dict() for p in profiles]
    }, indent=2, default=str)


def process_content_for_user(entry_id: str) -> str:
    """Process content and update user interests.

    Args:
        entry_id: Entry ID to process

    Returns:
        JSON string with processing result
    """
    from src.backend import EntroFeedBackend
    from src.storage.singleton import get_storage

    storage = get_storage()
    backend = EntroFeedBackend(db=storage)
    registry = get_ontology_registry()

    # Get entry
    all_feeds = backend.list_feeds()
    entry = None
    feed = None

    for f in all_feeds:
        entries = list(backend.list_entries(feed_id=f["id"]))
        for e in entries:
            if e.get("id") == entry_id or e.get("url", "").endswith(entry_id):
                entry = e
                feed = f
                break
        if entry:
            break

    if not entry:
        return json.dumps({
            "success": False,
            "error": "Entry not found"
        }, indent=2)

    # Process content
    from src.models.feed import FeedEntry, Feed

    feed_entry = FeedEntry(**entry) if isinstance(entry, dict) else entry
    feed_obj = Feed(**feed) if isinstance(feed, dict) else feed

    profile = registry.process_content(feed_entry, feed_obj)

    return json.dumps({
        "success": True,
        "profile": profile.to_dict()
    }, indent=2, default=str)


# ============ Daily Digest Tools ============

def get_daily_digest(date: str = None) -> str:
    """Generate or retrieve daily digest.

    Args:
        date: Date string (YYYY-MM-DD), defaults to today

    Returns:
        JSON string with digest
    """

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    registry = get_ontology_registry()
    profiles = registry.get_content_by_priority(min_priority=3, limit=20)

    # Filter by date if available
    filtered = []
    for p in profiles:
        created = p.created_at[:10] if p.created_at else ""
        if created == date:
            filtered.append(p)

    digest_items = []
    for profile in filtered[:10]:
        digest_items.append({
            "entry_id": profile.entry_id,
            "priority": profile.priority,
            "tags": [t.name for t in profile.tags],
            "summary": profile.summary[:200] if profile.summary else "",
            "entities": profile.key_entities[:5]
        })

    return json.dumps({
        "date": date,
        "count": len(digest_items),
        "items": digest_items
    }, indent=2, default=str)


# ============ Translation Tools ============

LANGUAGE_NAMES = {
    "zh": "Chinese (Simplified)",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "ar": "Arabic",
}

LANG_MAP = {
    "en": "en",
    "zh": "zh-CN",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "ru": "ru",
    "ar": "ar",
}


def translate_with_my_memory(text: str, target_lang: str = "zh", source_lang: str = "en") -> str:
    """Translate using MyMemory API (free, no API key required).
    Handles longer text by chunking (500 chars per request).

    Args:
        text: Text to translate
        target_lang: Target language code
        source_lang: Source language code

    Returns:
        JSON string with translation result
    """
    try:
        langpair = f"{LANG_MAP.get(source_lang, source_lang)}|{LANG_MAP.get(target_lang, target_lang)}"

        # For text longer than 500 chars, translate in chunks
        if len(text) <= 500:
            encoded_text = urllib.parse.quote(text.encode('utf-8'))
            url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={langpair}"
            with urllib.request.urlopen(url, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            if result.get('responseStatus') == 200:
                translated = result['responseData']['translatedText']
            else:
                return json.dumps({
                    "success": False,
                    "error": f"MyMemory error: {result.get('responseDetails', 'Unknown error')}"
                })
        else:
            # Translate in chunks and combine
            chunks = []
            chunk_size = 450  # Leave some margin
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i+chunk_size]
                encoded_text = urllib.parse.quote(chunk.encode('utf-8'))
                url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair={langpair}"
                with urllib.request.urlopen(url, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                if result.get('responseStatus') == 200:
                    chunks.append(result['responseData']['translatedText'])
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"MyMemory error at chunk {i}: {result.get('responseDetails', 'Unknown error')}"
                    })
            translated = ''.join(chunks)

        return json.dumps({
            "success": True,
            "original": {"text": text[:500] + "..." if len(text) > 500 else text, "language": source_lang},
            "translation": {"text": translated, "language": target_lang},
            "provider": "mymemory",
            "usage": {"total_tokens": len(text), "requests": (len(text) // 500) + 1},
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"MyMemory fallback failed: {str(e)}"
        })


def translate_text(text: str, target_lang: str = "zh") -> str:
    """Translate text. Uses MyMemory first, falls back to LLM.

    Args:
        text: Text to translate
        target_lang: Target language code (zh, en, ja, ko, fr, de, es)

    Returns:
        JSON string with translation result
    """
    if not text or not text.strip():
        return json.dumps({
            "success": False,
            "error": "Empty text provided"
        }, indent=2)

    # Detect source language (simple heuristic)
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    source_lang = "zh" if chinese_chars / len(text) > 0.3 else "en"

    # Try MyMemory first (fast, free)
    result = translate_with_my_memory(text, target_lang, source_lang)
    result_obj = json.loads(result)

    if result_obj.get("success"):
        return result

    # Fallback to LLM if MyMemory fails
    return translate_with_llm(text, target_lang, source_lang)


def translate_with_llm(text: str, target_lang: str, source_lang: str = "en") -> str:
    """Translate using LLM (DashScope or other provider)."""
    from src.plugins.llm import create_llm_handler

    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)

    try:
        llm = create_llm_handler()
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create LLM handler: {str(e)}"
        }, indent=2)

    source_name = LANGUAGE_NAMES.get(source_lang, source_lang)

    # Create translation prompt
    prompt = f"""Translate the following text from {source_name} to {target_name}.

Text to translate:
{text}

Respond ONLY with the translation, nothing else. Preserve the formatting if possible."""

    try:
        translation = llm._make_chat_call(system="You are a professional translator.", prompt=prompt)

        # Track token usage
        from src.agents.entrofeed_agent import TokenTracker
        TokenTracker.add_usage(
            model=llm.model if hasattr(llm, 'model') else 'unknown',
            input_tokens=len(text) // 4,  # Rough estimate
            output_tokens=len(translation) // 4,
        )

        return json.dumps({
            "success": True,
            "original": {
                "text": text[:500] + "..." if len(text) > 500 else text,
                "language": source_lang,
            },
            "translation": {
                "text": translation,
                "language": target_lang,
            },
            "usage": TokenTracker.get_today_usage(),
        }, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# Register tool functions for AgentScope
TOOL_FUNCTIONS = {
    "list_feeds": list_feeds,
    "get_feed_entries": get_feed_entries,
    "get_entry_content": get_entry_content,
    "search_entries": search_entries,
    "get_user_interests": get_user_interests,
    "add_user_interest": add_user_interest,
    "remove_user_interest": remove_user_interest,
    "get_high_priority_content": get_high_priority_content,
    "process_content_for_user": process_content_for_user,
    "get_daily_digest": get_daily_digest,
    "translate_text": translate_text,
}


__all__ = [
    "list_feeds",
    "get_feed_entries",
    "get_entry_content",
    "search_entries",
    "get_user_interests",
    "add_user_interest",
    "remove_user_interest",
    "get_high_priority_content",
    "process_content_for_user",
    "get_daily_digest",
    "translate_text",
    "TOOL_FUNCTIONS",
]
