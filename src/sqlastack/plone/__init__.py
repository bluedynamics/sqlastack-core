"""sqlastack.plone - Optional Plone/Zope integration.

Uses conditional imports. When Zope packages are not installed
(e.g., in a Celery worker), this module is inert.
"""

from __future__ import annotations

from sqlastack.core.exceptions import ZopeNotAvailable
from sqlastack.core.registry import DatabaseRegistry
import threading

try:
    from zope.sqlalchemy import mark_changed  # noqa: F401
    from zope.sqlalchemy import register as _register

    HAS_ZOPE = True
except ImportError:
    HAS_ZOPE = False


def _check_zope() -> None:
    """Raise ZopeNotAvailable if zope.sqlalchemy is not installed."""
    if not HAS_ZOPE:
        raise ZopeNotAvailable(
            "zope.sqlalchemy is not installed. "
            "Install sqlastack-core[zope] to use Zope integration."
        )


def create_scoped_zope_session(
    session_factory,
    keep_session: bool = False,
):
    """Create a scoped session registered with zope.sqlalchemy.

    Args:
        session_factory: A SQLAlchemy sessionmaker instance.
        keep_session: If True, keep the session open after transaction ends.

    Returns:
        A scoped_session instance registered with zope.sqlalchemy.
    """
    from sqlalchemy.orm import scoped_session

    _check_zope()
    scoped = scoped_session(session_factory)
    _register(scoped, keep_session=keep_session)
    return scoped


_registry: DatabaseRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> DatabaseRegistry:
    """Return the process-wide DatabaseRegistry (built lazily from env).

    First access runs ``DatabaseRegistry.from_env()`` + ``warm_up()`` under a
    lock, so concurrent first requests share one registry and pay no
    per-request engine construction afterwards.
    """
    global _registry
    registry = _registry
    if registry is None:
        with _registry_lock:
            registry = _registry
            if registry is None:
                registry = DatabaseRegistry.from_env()
                registry.warm_up()
                _registry = registry
    return registry


def reset_registry() -> None:
    """Dispose and forget the process-wide registry (tests, shutdown)."""
    global _registry
    with _registry_lock:
        if _registry is not None:
            _registry.dispose_all()
            _registry = None


def close_zope_sessions(event=None) -> None:
    """End-of-request teardown: remove this thread's Zope sessions.

    Registered (by consuming Plone add-ons, e.g. sqlastack.formstore) as a
    subscriber for ZPublisher's ``IPubSuccess`` AND ``IPubFailure``. A request
    that never touched SQL is a no-op — the registry is not built here.
    """
    registry = _registry
    if registry is not None:
        registry.remove_zope_sessions()
