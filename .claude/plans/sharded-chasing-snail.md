# Plan: Remove Backward Compatibility Shim Modules

## Context

The `src/` directory has accumulated multiple layers of re-export shims and redundant code from an incremental migration to a PluginRegistry system. The goal is to:

1. Delete all pure re-export shim files
2. Replace the `ImplMixin` + `handler_map` pattern with direct `PluginRegistry` queries
3. Fix broken references
4. Update all import paths to point directly to canonical locations

---

## PHASE 1: Delete Shim/Redundant Files

| File | Reason |
|------|--------|
| `src/models.py` | File (not directory) that shadows `src/models/` package; creates circular import |
| `src/rss.py` | Pure re-export of `EntroFeedRSS` from `src/services/feed/service` |
| `src/llm/__init__.py` | Shim re-exporting from `src/plugins/llm/` |
| `src/llm/openai.py` | Duplicate class (old: `LLMHandler+BaseModel`; new: `ModelWrapperBase+LLMHandler`) |
| `src/llm/ollama.py` | Duplicate class |
| `src/llm/dashscope.py` | Duplicate class |
| `src/llm/dummy.py` | Duplicate class |
| `src/llm/null.py` | Duplicate class |
| `src/agents/skills_manager.py` | Broken shim — imports `get_skills_manager` which doesn't exist |
| `src/ontology/__init__.py` | Pure re-export from `src/services/ontology` |
| `src/impls.py` | Old `ImplMixin` + `handler_map` system; to be replaced by `PluginRegistry` |

---

## PHASE 2: Migrate `StorageHandler` to PluginRegistry

The `ImplMixin` currently provides `handler_map`, `engine_map`, `handler_type_map` via the `type()` hack in `load_storage_config()`. This must be replaced.

### 2a. Add `handler_map` property to `StorageHandler` (db.py)

Replace `reconfigure_handler` abstract method with a concrete implementation that queries `PluginRegistry`:

```python
# In db.py - replace abstract method with:
def reconfigure_handler(self, id: str, config: Mapping) -> HandlerBase:
    """Look up handler by ID across all types and instantiate with config."""
    # Query all plugin types to find handler by ID
    for plugin_type in ("llm", "notification", "content", "storage"):
        if PluginRegistry.has_plugin(plugin_type, id):
            return PluginRegistry.create(plugin_type, id, **config)
    raise KeyError(f"No handler found for id: {id}")

# Add helper to get handlers (used by get_handlers)
def _get_handler_map(self) -> Dict[str, Type[HandlerBase]]:
    """Build unified handler map from PluginRegistry."""
    handler_map: Dict[str, Type[HandlerBase]] = {}
    for plugin_type in ("llm", "notification", "content", "storage"):
        handler_map.update(PluginRegistry.list_plugins(plugin_type))
    return handler_map
```

### 2b. Update storage subclasses (tinydb.py, lmdb.py, sqlite_storage.py, hybrid.py)

Each storage subclass currently relies on `ImplMixin` for `handler_map`. After Phase 2a, `StorageHandler` provides `reconfigure_handler` directly. Remove `ImplMixin` inheritance from any `type()` calls in `load_storage_config`.

### 2c. Update `load_storage_config` (currently in impls.py → move to db.py or kernel/registry.py)

Replace `type()` dynamic mixin with a simple factory:

```python
# Move to src/kernel/registry.py or src/db.py
def load_storage_config() -> StorageHandler:
    from src.kernel.registry import PluginRegistry
    config_type = environ.get("ENTROFEED_STORAGE_HANDLER", "tinydb")
    storage_handler = PluginRegistry.create("storage", config_type)
    return storage_handler
```

### 2d. Update `storage/singleton.py`

```python
# Change from:
from src.impls import load_storage_config
# To:
from src.kernel.registry import load_storage_config
```

### 2e. Delete `impls.py`

All its content (`ImplMixin`, `handler_maps`, `_register_plugins()`, `load_storage_config()`) is now obsolete.

---

## PHASE 3: Fix Broken Import in `entrofeed_agent.py`

The call to non-existent `get_skills_manager()` must be replaced:

```python
# Old (broken):
from src.agents.skills_manager import get_skills_manager
manager = get_skills_manager()

# New:
from src.skills.registry import get_skill_registry
manager = get_skill_registry()
```

---

## PHASE 4: Update Import Paths Across All Files

### Pattern A: `from src.models import X` → `from src.models.feed import X` or `src.models.health`

Files: `src/db.py`, `src/handlers.py`, `src/storage/tinydb.py`, `src/storage/lmdb.py`, `src/storage/sqlite_storage.py`, `src/storage/hybrid.py`, `src/services/feed/service.py`, `src/services/ontology/tagging.py`, `src/services/ontology/mckinsey_plugin.py`, `src/services/ontology/registry.py`, `src/plugins/llm/*.py`, `src/plugins/notification/*.py`, `src/plugins/content/*.py`, `src/plugins/storage/tinydb.py`, `src/agents/tools.py`, `src/app.py`, `src/backend.py`

### Pattern B: `from src.ontology import X` → `from src.services.ontology import X`

Files: `src/agents/tools.py`, `src/agents/entrofeed_agent.py`, `src/backend.py`, `src/mcp.py`, `src/scheduler.py`, `src/app.py`, `src/services/recommendation/similar.py`, `src/services/recommendation/interest_based.py`, `src/services/recommendation/trending.py`

### Pattern C: `from src.rss import EntroFeedRSS` → `from src.services.feed.service import EntroFeedRSS`

Files: `src/app.py`, `src/scheduler.py`

### Pattern D: `from src.llm import X` → `from src.plugins.llm import X`

Files: `src/plugins/storage/tinydb.py`, `src/agents/tools.py`, `src/agents/entrofeed_agent.py`

---

## PHASE 5: Update Tests

| File | Changes |
|------|---------|
| `tests/unit/test_models.py` | `from src.models import` → `from src.models.feed import` + `from src.models.health import` |
| `tests/unit/test_backend.py` | `from src.llm.dummy import` → `from src.plugins.llm.dummy import`; `from src.models import` → `from src.models.feed import` |
| `tests/unit/test_impls.py` | Remove entire file — `impls.py` is deleted; or update to test `PluginRegistry` directly |
| `tests/unit/test_settings.py` | Keep `from src.handlers import` (still used) |
| `tests/unit/test_handlers.py` | Keep `from src.handlers import` (still used) |

---

## PHASE 6: Verify

```bash
python -c "from src.app import app"
python -c "from src.models.feed import Feed, FeedEntry"
python -c "from src.services.ontology import PriorityScorer"
python -c "from src.plugins.llm import OpenAILLMHandler"
python -c "from src.services.feed.service import EntroFeedRSS"
python -m pytest tests/unit/ -v
```

---

## Summary of File Changes

**Delete (11 files):**
- `src/models.py`
- `src/rss.py`
- `src/llm/__init__.py`, `src/llm/openai.py`, `src/llm/ollama.py`, `src/llm/dashscope.py`, `src/llm/dummy.py`, `src/llm/null.py`
- `src/agents/skills_manager.py`
- `src/ontology/__init__.py`
- `src/impls.py`

**Modify (~20 files):**
- `db.py` — add `reconfigure_handler` + `_get_handler_map` to `StorageHandler` base class
- `storage/tinydb.py`, `storage/lmdb.py`, `storage/sqlite_storage.py`, `storage/hybrid.py` — update model imports
- `storage/singleton.py` — redirect `load_storage_config` import
- `handlers.py`, `app.py`, `backend.py`, `settings.py`, `mcp.py`, `scheduler.py` — update imports
- `agents/tools.py`, `agents/entrofeed_agent.py` — update imports + fix `get_skills_manager`
- `services/feed/service.py`, `services/ontology/*.py` — update model imports
- `plugins/llm/*.py`, `plugins/notification/*.py`, `plugins/content/*.py` — update model imports
- `tests/unit/test_models.py`, `tests/unit/test_backend.py`, `tests/unit/test_impls.py` — update/remove tests
