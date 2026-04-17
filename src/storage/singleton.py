"""Storage singleton - avoids circular import by importing impls lazily."""

_storage_instance = None


def get_storage():
    """Get or create the singleton storage handler instance."""
    global _storage_instance
    if _storage_instance is None:
        from src.kernel.registry import load_storage_config
        _storage_instance = load_storage_config()
    return _storage_instance
