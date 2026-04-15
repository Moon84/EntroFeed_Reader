from contextlib import asynccontextmanager
from datetime import datetime
from itertools import chain
from logging import getLogger
from pathlib import Path
from typing import Annotated, Mapping, Optional, Sequence

from fastapi import FastAPI, Form, UploadFile, status
from pydantic import BaseModel
from fastapi.requests import Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.backend import EntroFeedBackend
from src.storage.singleton import get_storage
from src.logging import HealthCheckFilter
from src.models import Feed, HealthCheck
from src.rss import EntroFeedRSS
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
    """Get statistics for each feed."""
    settings: GlobalSettings = storage_handler.get_settings()
    cutoff_time = int(datetime.now().timestamp()) - (settings.recent_hours * 3600)

    feeds = bk.list_feeds()
    stats = []

    for feed in feeds:
        feed_id = feed["id"]
        entries = list(bk.list_entries(feed_id=feed_id))
        recent_entries = [e for e in entries if e.get("sort_time", 0) >= cutoff_time]
        important_count = sum(1 for e in recent_entries if e.get("total_score", 0) >= 0.5)

        stats.append({
            "feed_id": feed_id,
            "total_count": len(recent_entries),
            "important_count": important_count,
        })

    return stats


@app.get("/util/list-feed-entries")
async def list_feed_entries(feed_id: str = None) -> Sequence[Mapping]:
    if feed_id:
        return list(bk.list_entries(feed_id=feed_id))
    else:
        all_feeds = bk.list_feeds()
        entries = [list(bk.list_entries(feed["id"])) for feed in all_feeds]
        return list(chain.from_iterable(entries))


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
    theme: Annotated[str, Form()],
    refresh_interval: Annotated[int, Form()],
    request: Request,
    send_notification: Annotated[bool, Form()] = False,
    notification: Annotated[str, Form()] = None,
    content: Annotated[str, Form()] = None,
    llm: Annotated[str, Form()] = None,
    reading_speed: Annotated[int, Form()] = None,
    finished_onboarding: Annotated[bool, Form()] = False,
    recent_hours: Annotated[int, Form()] = None,
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
    from src.recommender import get_interest_recommendations
    return {"recommendations": get_interest_recommendations(limit=limit)}


@app.get("/api/recommendations/trending")
async def get_trending_recommendations_api(limit: int = 10):
    from src.recommender import get_trending_recommendations
    return {"recommendations": get_trending_recommendations(limit=limit)}


@app.get("/api/recommendations/similar/{entry_id}")
async def get_similar_recommendations_api(entry_id: str, limit: int = 5):
    from src.recommender import get_similar_recommendations
    return {"recommendations": get_similar_recommendations(entry_id=entry_id, limit=limit)}


# =============================================================================
# Interest Management APIs
# =============================================================================

@app.get("/api/interests")
async def list_interests(category: str = None):
    from src.ontology import get_ontology_registry
    from src.ontology.types import InterestCategory

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
    from src.ontology import get_ontology_registry
    from src.ontology.types import InterestTag, InterestCategory, TagSource

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
    from src.ontology import get_ontology_registry
    registry = get_ontology_registry()
    success = registry.remove_interest(interest_id)
    return {"success": success}


@app.patch("/api/interests/{interest_id}")
async def update_interest(interest_id: str, priority: int = None):
    from src.ontology import get_ontology_registry
    registry = get_ontology_registry()
    if priority is not None:
        interest = registry.update_interest_priority(interest_id, priority)
        if interest:
            return {"interest": interest.to_dict()}
    return {"error": "Interest not found or invalid priority"}


@app.get("/api/interests/inferred")
async def get_inferred_interests(limit: int = 5):
    from src.ontology import get_ontology_registry
    registry = get_ontology_registry()
    inferred = registry.infer_new_interests(max_new=limit)
    return {"inferred": [i.to_dict() for i in inferred]}


@app.post("/api/interests/inferred/{tag}")
async def accept_inferred_interest(tag: str, priority: int = 2):
    from src.ontology import get_ontology_registry
    from src.ontology.types import InterestTag, InterestCategory, TagSource

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
# Search API
# =============================================================================

@app.get("/api/search")
async def search_content(q: str = "", limit: int = 10, type: str = "local"):
    if not q:
        return {"results": [], "query": q}

    if type == "similar":
        from src.ontology import get_ontology_registry
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
    from src.ontology import get_ontology_registry
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
    from src.llm import create_llm_handler

    session_manager = get_session_manager()
    session = None
    if request.session_id:
        session = session_manager.get_session(request.session_id)
    if not session:
        session = session_manager.create_session()

    session_manager.add_message_to_session(session.id, "user", request.message)
    context_messages = session.get_context_messages(max_messages=20)

    system_prompt = """You are EntroFeed, an intelligent RSS reader assistant.

Your capabilities:
1. Browse and summarize RSS feeds
2. Track user interests and content preferences
3. Generate daily digests of important content
4. Help users find relevant information
5. Translate content when needed

Available tools:
- list_feeds, get_feed_entries, get_entry_content, search_entries
- get_user_interests, add_user_interest, get_high_priority_content
- get_daily_digest, translate_text

Be helpful, concise, and focused on delivering value to the user."""

    try:
        llm = create_llm_handler()
        llm_messages = [{"role": "system", "content": system_prompt}]
        llm_messages.extend(context_messages)
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
    from src.llm import create_llm_handler, get_default_provider
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
