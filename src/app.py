from contextlib import asynccontextmanager
from datetime import datetime
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import Annotated, Mapping, Optional, Sequence
import json

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Form, UploadFile, status
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.backend import EntroFeedBackend
from src.storage.singleton import get_storage
from src.logging import HealthCheckFilter
from src.models.feed import Feed
from src.models.health import HealthCheck
from src.services.feed.service import EntroFeedRSS
from src.scheduler import get_scheduler, setup_rss_polling, setup_daily_tasks
from src.settings import GlobalSettings, Themes

JSON = "application/json"

logger = getLogger("uvicorn.error")
base_path = Path(__file__).parent.parent  # go up from src/ to project root

storage_handler = get_storage()

bk = EntroFeedBackend(db=storage_handler)
rss = EntroFeedRSS(db=storage_handler)

logger.addFilter(HealthCheckFilter())
getLogger("uvicorn.access").addFilter(HealthCheckFilter())

p_settings: GlobalSettings = storage_handler.get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all plugin types to trigger registration
    from src.plugins.llm import create_llm_handler  # noqa
    from src.plugins.notification import NotificationPluginRegistry  # noqa
    from src.plugins.content import ContentPluginRegistry  # noqa

    # Run plugin startup hooks
    from src.kernel.registry import PluginRegistry
    await PluginRegistry.run_startup_hooks()

    # Initialize user interests from user.md if exists
    try:
        from src.services.ontology import get_ontology_registry
        ontology = get_ontology_registry()
        interests = ontology.init_user_interests_from_file()
        if interests:
            logger.info(f"Initialized {len(interests)} user interests from user.md")
        else:
            logger.info("No user.md found or no interests to initialize")
    except Exception as e:
        logger.warning(f"Failed to initialize user interests: {e}")

    # Load feeds from feeds.yml if database is empty
    existing_feeds = storage_handler.get_feeds()
    if not existing_feeds:
        logger.info("No feeds found in database, loading from feeds.yml")
        rss.load_feeds()

    # Update feed count metric
    try:
        from src.metrics import FEED_COUNT
        FEED_COUNT.set(len(storage_handler.get_feeds()))
    except Exception:
        pass

    # Initialize and start the scheduler
    scheduler = get_scheduler()
    setup_rss_polling(interval_minutes=p_settings.refresh_interval)
    setup_daily_tasks()
    scheduler.start()
    logger.info(f"Scheduler started with RSS polling every {p_settings.refresh_interval} minutes")

    yield

    # Shutdown scheduler on app shutdown
    scheduler.shutdown(wait=True)


app = FastAPI(lifespan=lifespan, title="EntroFeed", openapi_url="/openapi.json")

# Static file mounts
app.mount("/static", StaticFiles(directory=base_path / "src" / "static"), name="static")
app.mount("/assets", StaticFiles(directory=base_path / "src" / "assets"), name="assets")

# SPA fallback: serve index.html for client-side routes under /_app/
# Only serves index.html if the requested path is NOT an actual file
@app.get("/_app/{path:path}")
async def serve_spa_fallback(path: str):
    file_path = base_path / "frontend" / "dist" / path
    # If the file exists, let StaticFiles handle it
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    # Otherwise serve index.html for SPA routing
    import time
    index_path = base_path / "frontend" / "dist" / "index.html"
    content = index_path.read_text()
    # Fix asset paths: ./assets -> /_app/assets
    content = content.replace('./assets/', '/_app/assets/')
    # Add cache-busting timestamp to JS and CSS files
    ts = int(time.time())
    content = content.replace('.js"', f'.js?v={ts}"')
    content = content.replace('.css"', f'.css?v={ts}"')
    return HTMLResponse(content)

# Mount React SPA at /_app/ to avoid shadowing API routes
app.mount("/_app", StaticFiles(directory=base_path / "frontend" / "dist", html=True), name="frontend")


@app.get("/", include_in_schema=False, name="root")
async def root():
    """Redirect root to SPA."""
    return RedirectResponse("/_app/")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(base_path / "src" / "static" / "icons" / "favicon.ico")


# =============================================================================
# Health & About (JSON APIs - also used by frontend)
# =============================================================================

@app.get("/api/about")
async def api_about():
    """JSON API for app info (used by React frontend)."""
    return {
        **await bk.about(),
        "settings": await bk.get_settings(),
    }


@app.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    return await bk.health_check()


# =============================================================================
# Feed Management (JSON APIs)
# =============================================================================

@app.get("/util/list-feeds")
async def list_feeds() -> Sequence[Mapping]:
    return bk.list_feeds()


@app.get("/util/feed-stats")
async def get_feed_stats():
    """Get statistics for each feed efficiently using SQL COUNT queries."""
    try:
        settings: GlobalSettings = storage_handler.get_settings()
        cutoff_time = int(datetime.now().timestamp()) - (settings.recent_hours * 3600)

        feeds = bk.list_feeds()
        stats = []

        for feed in feeds:
            feed_id = feed["id"]
            # Use direct SQL queries for efficiency
            cursor = storage_handler.conn.cursor()

            # Total recent entries
            cursor.execute(
                "SELECT COUNT(*) FROM feed_entries WHERE feed_id = ? AND published_at > ?",
                (feed_id, cutoff_time)
            )
            total_count = cursor.fetchone()[0]

            # Important count - total_score is not stored in DB, set to 0
            # The scoring is calculated at query time, not persisted
            important_count = 0

            # Unread count
            cursor.execute(
                "SELECT COUNT(*) FROM feed_entries WHERE feed_id = ? AND published_at > ? AND (is_read = 0 OR is_read IS NULL)",
                (feed_id, cutoff_time)
            )
            unread_count = cursor.fetchone()[0]

            stats.append({
                "feed_id": feed_id,
                "total_count": total_count,
                "important_count": important_count,
                "unread_count": unread_count,
            })

        return stats
    except Exception as e:
        logger.error(f"Error in get_feed_stats: {e}")
        raise


@app.get("/util/list-feed-entries")
async def list_feed_entries(
    feed_id: str = None,
    liked: int = 0,
    is_favorite: bool = False,
) -> Sequence[Mapping]:
    """
    List feed entries with optional filtering.

    liked: filter by like status (0 = all, 1 = liked, -1 = disliked)
    is_favorite: if true, only return favorited entries
    """
    if feed_id:
        return list(bk.list_entries(feed_id=feed_id, liked=liked, is_favorite=is_favorite))
    else:
        all_feeds = bk.list_feeds()
        entries = [list(bk.list_entries(feed["id"], liked=liked, is_favorite=is_favorite)) for feed in all_feeds]
        return list(chain.from_iterable(entries))


@app.get("/read/{entry_id}")
async def get_entry_content(entry_id: str, accept: str = "json"):
    """Get full content of a feed entry."""
    result = await bk.get_entry_content(feed_entry_id=entry_id)
    return result


@app.get("/util/list-handlers")
async def list_handlers() -> Sequence[Mapping]:
    handlers = bk.get_handlers()
    return [
        {
            "name": handler["type"],
            "type": handler["handler_type"],
            "configured": True if handler.get("config") else False,
        }
        for handler in handlers
    ]


@app.get("/util/discover-rsshub")
async def discover_rsshub(url: str = ""):
    """Discover available RSSHub routes for a given URL."""
    from src.services.feed.rsshub_discovery import discover_rsshub_routes

    if not url:
        return []

    routes = discover_rsshub_routes(url)
    return routes


# =============================================================================
# Feed CRUD (Form-based POST - used by React frontend)
# =============================================================================

@app.post("/api/update_feed/", status_code=status.HTTP_303_SEE_OTHER)
async def update_feed(
    name: Annotated[str, Form()],
    url: Annotated[str, Form()],
    category: Annotated[str, Form()],
    request: Request,
    notify_destination: Annotated[str, Form()] = None,
    notify: Annotated[bool, Form()] = False,
    preview_only: Annotated[bool, Form()] = False,
    refresh_enabled: Annotated[bool, Form()] = False,
    use_script: Annotated[bool, Form()] = False,
    retrieve_content: Annotated[bool, Form()] = False,
):
    try:
        feed = Feed(
            name=name,
            url=url,
            category=category,
            notify=notify,
            notify_destination=notify_destination,
            preview_only=preview_only,
            refresh_enabled=refresh_enabled,
            use_script=use_script,
            retrieve_content=retrieve_content,
        )
        await bk.update_feed(feed=feed)
        # Return redirect to feeds page for progressive enhancement
        return RedirectResponse(url="/feeds", status_code=status.HTTP_303_SEE_OTHER)
    except Exception:
        # On error, redirect to new feed page
        return RedirectResponse(url="/feeds/new", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/refresh_feed/{feed_id}", status_code=status.HTTP_200_OK)
async def refresh_feed(feed_id: str):
    await rss.check_feed_by_id(id=feed_id)
    return {"status": "ok"}


@app.post("/api/delete_feed/{feed_id}", status_code=status.HTTP_200_OK)
async def delete_feed(feed_id: str):
    await bk.delete_feed(feed_id=feed_id)
    return {"status": "ok"}


# =============================================================================
# Handler Config API (used by React frontend)
# =============================================================================

@app.get("/settings/{handler}")
async def get_handler_config(handler: str):
    """Get handler config and schema for the React frontend."""
    return {
        "handler": bk.get_handler_config(handler=handler),
        "schema": bk.get_handler_schema(handler=handler),
    }


# =============================================================================
# Settings Management (Form-based POST)
# =============================================================================

@app.post("/api/update_settings/", status_code=status.HTTP_303_SEE_OTHER)
async def update_settings(
    request: Request,
    theme: Annotated[str, Form()] = "forest",
    refresh_interval: Annotated[int, Form()] = 30,
    send_notification: Annotated[bool, Form()] = False,
    notification: Annotated[str, Form()] = "null_notification",
    content: Annotated[str, Form()] = "playwright",
    llm: Annotated[str, Form()] = "null_llm",
    reading_speed: Annotated[int, Form()] = 200,
    finished_onboarding: Annotated[bool, Form()] = False,
    recent_hours: Annotated[int, Form()] = 24,
):
    settings = GlobalSettings(
        send_notification=send_notification,
        theme=theme,
        refresh_interval=refresh_interval,
        notification_handler_key=notification,
        llm_handler_key=llm,
        content_retrieval_handler_key=content,
        reading_speed=reading_speed,
        finished_onboarding=finished_onboarding,
        recent_hours=recent_hours,
        db=storage_handler,
    )
    await bk.update_settings(settings=settings)
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/api/update_handler/", status_code=status.HTTP_303_SEE_OTHER)
async def update_handler(
    handler: Annotated[str, Form()], config: Annotated[str, Form()], request: Request
):
    try:
        await bk.update_handler(handler=handler, config=config)
        return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)
    except Exception:
        return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)


# =============================================================================
# OPML / Backup / Restore (File Upload/Download)
# =============================================================================

@app.get("/api/export_opml/")
async def export_opml():
    write_path, file_name = await rss.feeds_to_opml()
    return FileResponse(path=write_path, filename=file_name)


@app.get("/api/backup/")
async def backup():
    write_path, file_name = await rss.backup()
    return FileResponse(path=write_path, filename=file_name)


@app.post("/api/restore/", status_code=status.HTTP_200_OK)
async def restore(request: Request, file: UploadFile):
    try:
        await rss.restore(file=file.file)
        return {"status": "ok", "message": "Restore successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/import_opml/", status_code=status.HTTP_200_OK)
async def import_opml(request: Request, file: UploadFile):
    try:
        await rss.opml_to_feeds(file=file.file)
        return {"status": "ok", "message": "Import successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# Entry State
# =============================================================================

class EntryStateUpdate(BaseModel):
    is_read: Optional[bool] = None
    liked: Optional[int] = None
    is_favorite: Optional[bool] = None


@app.patch("/api/entries/{entry_id}")
async def update_entry_state(entry_id: str, update: EntryStateUpdate):
    bk.update_entry_state(
        entry_id=entry_id,
        is_read=update.is_read,
        liked=update.liked,
        is_favorite=update.is_favorite,
    )
    return {"status": "ok"}


# =============================================================================
# Recommendations APIs
# =============================================================================

@app.get("/api/recommendations/interest")
async def get_interest_recommendations_api(limit: int = 10):
    from src.services.recommendation import get_interest_recommendations
    return {"recommendations": get_interest_recommendations(limit=limit)}


@app.get("/api/recommendations/trending")
async def get_trending_recommendations_api(limit: int = 10):
    from src.services.recommendation import get_trending_recommendations
    return {"recommendations": get_trending_recommendations(limit=limit)}


@app.get("/api/recommendations/similar/{entry_id}")
async def get_similar_recommendations_api(entry_id: str, limit: int = 5):
    from src.services.recommendation import get_similar_recommendations
    return {"recommendations": get_similar_recommendations(entry_id=entry_id, limit=limit)}


# =============================================================================
# Interest Management APIs
# =============================================================================

@app.get("/api/interests")
async def list_interests(category: str = None):
    from src.services.ontology import get_ontology_registry
    from src.services.ontology.types import InterestCategory

    registry = get_ontology_registry()
    cat = None
    if category:
        try:
            cat = InterestCategory(category.lower())
        except ValueError:
            pass

    interests = registry.get_user_interests(category=cat)
    return {"interests": [i.to_dict() for i in interests]}


@app.post("/api/interests")
async def add_interest(name: str, category: str = "other", priority: int = 3):
    from src.services.ontology import get_ontology_registry
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
    return {"interest": interest.to_dict()}


@app.delete("/api/interests/{interest_id}")
async def remove_interest(interest_id: str):
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()
    success = registry.remove_interest(interest_id)
    return {"success": success}


@app.patch("/api/interests/{interest_id}")
async def update_interest(interest_id: str, priority: int = None):
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()
    if priority is not None:
        interest = registry.update_interest_priority(interest_id, priority)
        if interest:
            return {"interest": interest.to_dict()}
    return {"error": "Interest not found or invalid priority"}


@app.get("/api/interests/inferred")
async def get_inferred_interests(limit: int = 5):
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()
    inferred = registry.infer_new_interests(max_new=limit)
    return {"inferred": [i.to_dict() for i in inferred]}


@app.post("/api/interests/inferred/{tag}")
async def accept_inferred_interest(tag: str, priority: int = 2):
    from src.services.ontology import get_ontology_registry
    from src.services.ontology.types import InterestTag, InterestCategory, TagSource

    registry = get_ontology_registry()
    interest_tag = InterestTag(
        name=tag.lower(),
        category=InterestCategory.OTHER,
        source=TagSource.EXPLICIT,
        confidence=1.0
    )
    interest = registry.accept_inferred_interest(interest_tag, priority)
    return {"interest": interest.to_dict()}


# =============================================================================
# User Profile API (user.md)
# =============================================================================

@app.get("/api/user/profile")
async def get_user_profile():
    """Get user profile content from user.md."""
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()
    content = registry.read_user_profile()
    status = registry.get_user_profile_status()
    return {
        "content": content,
        "status": status,
    }


@app.post("/api/user/profile")
async def save_user_profile(content: str):
    """Save user profile content to user.md and re-initialize interests."""
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()

    success = registry.write_user_profile(content)
    if not success:
        return {"success": False, "error": "Failed to write user profile"}

    # Re-initialize interests from the new profile
    interests = registry.reinitialize_interests_from_profile()

    return {
        "success": True,
        "interests": [i.to_dict() for i in interests],
        "count": len(interests),
    }


@app.get("/api/user/profile/status")
async def get_user_profile_status():
    """Get user profile status (exists, empty, etc)."""
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()
    return registry.get_user_profile_status()


# =============================================================================
# Search API
# =============================================================================

@app.get("/api/search")
async def search_content(q: str = "", limit: int = 10, type: str = "local"):
    if not q:
        return {"results": [], "query": q}

    if type == "similar":
        from src.services.ontology import get_ontology_registry
        registry = get_ontology_registry()
        results = registry.search_similar(q, limit=limit)
        return {"results": results, "query": q, "type": type}
    else:
        from src.agents.tools import search_entries
        import json
        try:
            result = search_entries(q, limit=limit)
            parsed = json.loads(result)
            return {"results": parsed.get("entries", []), "query": q, "type": type}
        except Exception:
            return {"results": [], "query": q, "type": type, "error": "Search failed"}


# =============================================================================
# Content Profile API
# =============================================================================

@app.get("/api/content-profile/{entry_id}")
async def get_content_profile(entry_id: str):
    from src.services.ontology import get_ontology_registry
    registry = get_ontology_registry()
    profile = registry.memory.get_content_profile(entry_id)
    if profile:
        return {"profile": profile.to_dict()}
    return {"profile": None}


# =============================================================================
# Agent Chat APIs
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@app.post("/api/agent/chat")
async def agent_chat(request: ChatRequest):
    from src.agents.session import get_session_manager
    from src.agents.entrofeed_agent import TokenTracker
    from src.agents.tools import TOOL_FUNCTIONS
    from src.plugins.llm import create_llm_handler

    session_manager = get_session_manager()
    session = None
    if request.session_id:
        session = session_manager.get_session(request.session_id)
    if not session:
        session = session_manager.create_session()

    session_manager.add_message_to_session(session.id, "user", request.message)

    system_prompt = """You are EntroFeed, an intelligent RSS reader assistant.

Your capabilities:
1. Browse and summarize RSS feeds
2. Track user interests and content preferences
3. Generate daily digests of important content
4. Help users find relevant information
5. Translate content when needed

You have access to tools to look up feeds, entries, and user interests.
Use them when the user asks about articles, feeds, recommendations, or interests.
Always provide specific, accurate information from the tools."""

    # Define tools in OpenAI format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "list_feeds",
                "description": "List all configured RSS feeds",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_feed_entries",
                "description": "Get entries from a feed or recent entries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feed_id": {"type": "string", "description": "Feed ID (optional)"},
                        "limit": {"type": "integer", "description": "Max entries to return", "default": 20},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_entry_content",
                "description": "Get full content of a feed entry by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "feed_entry_id": {"type": "string", "description": "Entry ID"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_entries",
                "description": "Search entries by title or content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_user_interests",
                "description": "Get user interests",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category filter"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_high_priority_content",
                "description": "Get high priority content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "min_priority": {"type": "integer", "default": 3},
                        "limit": {"type": "integer", "default": 10},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_daily_digest",
                "description": "Get daily digest",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date YYYY-MM-DD"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "translate_text",
                "description": "Translate text between languages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "target_lang": {"type": "string", "description": "Target language code (zh, en, ja, etc.)"},
                    },
                },
            },
        },
    ]

    try:
        llm = create_llm_handler()

        # Build messages for tool calling
        llm_messages = [{"role": "system", "content": system_prompt}]
        context_messages = session.get_context_messages(max_messages=30)
        llm_messages.extend(context_messages)

        max_iters = 5
        for iteration in range(max_iters):
            try:
                result = llm.chat_with_tools(llm_messages, tools)
            except AttributeError:
                # Fallback if chat_with_tools not implemented
                reply_text = llm._make_chat_call(system=system_prompt, prompt=request.message)
                session_manager.add_message_to_session(session.id, "assistant", reply_text)
                TokenTracker.add_usage(
                    model=getattr(llm, 'model', 'unknown'),
                    input_tokens=len(request.message) // 4,
                    output_tokens=len(reply_text) // 4,
                )
                return JSONResponse(content={
                    "reply": reply_text,
                    "success": True,
                    "session_id": session.id,
                    "session_title": session.title,
                })

            assistant_content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])

            # Add assistant message
            if tool_calls:
                llm_messages.append({"role": "assistant", "content": assistant_content or ""})
            else:
                # No tool calls, we're done
                session_manager.add_message_to_session(session.id, "assistant", assistant_content)
                TokenTracker.add_usage(
                    model=getattr(llm, 'model', 'unknown'),
                    input_tokens=len(request.message) // 4,
                    output_tokens=len(assistant_content) // 4,
                )
                return JSONResponse(content={
                    "reply": assistant_content,
                    "success": True,
                    "session_id": session.id,
                    "session_title": session.title,
                })

            # Execute tool calls
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                func_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                tool_id = tc["id"]

                if func_name in TOOL_FUNCTIONS:
                    try:
                        tool_result = TOOL_FUNCTIONS[func_name](**func_args)
                    except Exception as e:
                        tool_result = json.dumps({"error": str(e)})
                else:
                    tool_result = json.dumps({"error": f"Unknown tool: {func_name}"})

                # Add tool result message
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": tool_result,
                })

        # Max iterations reached
        final_content = llm_messages[-1].get("content", "") if llm_messages else "Max iterations reached"
        session_manager.add_message_to_session(session.id, "assistant", final_content)
        return JSONResponse(content={
            "reply": final_content,
            "success": True,
            "session_id": session.id,
            "session_title": session.title,
        })

    except Exception as e:
        logger.error(f"Agent chat failed: {e}")
        return JSONResponse(
            content={"reply": f"I encountered an error: {str(e)}", "success": False, "session_id": session.id},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.get("/api/agent/sessions")
async def list_sessions():
    from src.agents.session import get_session_manager
    manager = get_session_manager()
    sessions = manager.list_sessions()
    return {
        "sessions": [{"id": s.id, "title": s.title, "message_count": len(s.messages),
                      "created_at": s.created_at, "updated_at": s.updated_at} for s in sessions]
    }


@app.post("/api/agent/sessions")
async def create_session():
    from src.agents.session import get_session_manager
    manager = get_session_manager()
    session = manager.create_session()
    return {"id": session.id, "title": session.title, "created_at": session.created_at}


@app.get("/api/agent/sessions/{session_id}")
async def get_session(session_id: str):
    from src.agents.session import get_session_manager
    manager = get_session_manager()
    session = manager.get_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session not found"}, status_code=status.HTTP_404_NOT_FOUND)
    return {"id": session.id, "title": session.title,
            "messages": [m.to_dict() for m in session.messages],
            "created_at": session.created_at, "updated_at": session.updated_at}


@app.delete("/api/agent/sessions/{session_id}")
async def delete_session(session_id: str):
    from src.agents.session import get_session_manager
    manager = get_session_manager()
    success = manager.delete_session(session_id)
    if not success:
        return JSONResponse(content={"error": "Session not found"}, status_code=status.HTTP_404_NOT_FOUND)
    return {"success": True}


@app.post("/api/agent/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    from src.agents.session import get_session_manager
    manager = get_session_manager()
    success = manager.clear_session(session_id)
    if not success:
        return JSONResponse(content={"error": "Session not found"}, status_code=status.HTTP_404_NOT_FOUND)
    return {"success": True}


@app.get("/api/agent/tools")
async def agent_list_tools():
    from src.agents.tools import TOOL_FUNCTIONS
    return {"tools": [{"name": name, "description": func.__doc__ or "No description"}
                      for name, func in TOOL_FUNCTIONS.items()]}


# =============================================================================
# Translation API
# =============================================================================

class TranslationRequest(BaseModel):
    text: str
    target_lang: str = "zh"


@app.post("/api/translate")
async def translate_text(request: TranslationRequest):
    from src.agents.tools import translate_text as do_translate
    import json
    try:
        result = do_translate(text=request.text, target_lang=request.target_lang)
        return JSONResponse(content=json.loads(result))
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return JSONResponse(content={"success": False, "error": str(e)},
                           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# LLM Status APIs
# =============================================================================

@app.get("/api/llm/status")
async def llm_status():
    from src.agents.entrofeed_agent import TokenTracker
    from src.plugins.llm import create_llm_handler, get_default_provider
    from src.backend import EntroFeedBackend

    llm_available = False
    llm_error = None
    llm_model = None

    try:
        storage = get_storage()
        backend = EntroFeedBackend(db=storage)
        _ = backend.get_settings()
        llm_model = get_default_provider()
        llm = create_llm_handler()
        llm_model = getattr(llm, 'model', llm_model) or llm_model
        llm_available = True
    except Exception as e:
        llm_error = str(e)
        llm_available = False

    usage = TokenTracker.get_today_usage()
    return {"available": llm_available, "provider": get_default_provider(),
            "model": llm_model, "error": llm_error, "usage": usage}


@app.get("/api/llm/usage")
async def llm_usage():
    from src.agents.entrofeed_agent import TokenTracker
    return {"today": TokenTracker.get_today_usage(),
            "history": TokenTracker.get_usage_history(days=7)}


@app.get("/metrics")
async def metrics():
    from src.metrics import get_metrics, get_content_type
    return JSONResponse(content=get_metrics().decode("utf-8"), media_type=get_content_type())


@app.get("/api/metrics/json")
async def metrics_json():
    """Return Prometheus metrics as JSON for frontend consumption."""
    from src.metrics import get_metrics
    import re

    metrics_output = get_metrics().decode("utf-8")
    result = {
        "token_usage": {"input": 0, "output": 0, "total": 0},
        "llm_requests": {"success": 0, "error": 0, "total": 0},
        "feed_count": 0,
        "recommendation_requests": {"interest": 0, "trending": 0, "similar": 0, "total": 0},
    }

    # Parse token usage: entrofeed_token_usage_total{model="x",type="input"} value
    for line in metrics_output.split('\n'):
        if line.startswith('entrofeed_token_usage_total'):
            match = re.search(r'type="(\w+)".*?(\d+\.?\d*)$', line)
            if match:
                token_type, value = match.groups()
                value = float(value)
                if token_type == 'input':
                    result["token_usage"]["input"] += value
                elif token_type == 'output':
                    result["token_usage"]["output"] += value
        elif line.startswith('entrofeed_llm_requests_total'):
            match = re.search(r'status="(\w+)".*?(\d+\.?\d*)$', line)
            if match:
                status, value = match.groups()
                value = float(value)
                if status == 'success':
                    result["llm_requests"]["success"] += value
                elif status == 'error':
                    result["llm_requests"]["error"] += value
                result["llm_requests"]["total"] += value
        elif line.startswith('entrofeed_feed_count'):
            match = re.search(r'(\d+\.?\d*)$', line)
            if match:
                result["feed_count"] = float(match.group(1))
        elif line.startswith('entrofeed_recommendation_requests_total'):
            match = re.search(r'type="(\w+)".*?(\d+\.?\d*)$', line)
            if match:
                rec_type, value = match.groups()
                value = float(value)
                result["recommendation_requests"][rec_type] = value
                result["recommendation_requests"]["total"] += value

    return JSONResponse(content=result)


@app.get("/api/plugins/health")
async def plugins_health():
    """Return health status of all registered plugins.

    Checks each plugin's availability including:
    - Required environment variables
    - Connectivity check (if defined)
    """
    from src.kernel.registry import PluginRegistry

    all_results = PluginRegistry.check_all_plugins()

    # Format response
    plugins = {}
    for plugin_type, handlers in all_results.items():
        plugins[plugin_type] = {}
        for plugin_id, check_result in handlers.items():
            plugins[plugin_type][plugin_id] = {
                "available": check_result.available,
                "reason": check_result.reason,
                "missing_env": check_result.missing_env,
            }

    return {
        "plugins": plugins,
        "summary": {
            plugin_type: {
                "total": len(handlers),
                "available": sum(1 for h in handlers.values() if h["available"])
            }
            for plugin_type, handlers in plugins.items()
        }
    }
