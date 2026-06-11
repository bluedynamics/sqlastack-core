"""sqlastack.plone - Optional Plone/Zope integration.

Uses conditional imports. When Zope packages are not installed
(e.g., in a Celery worker), this module is inert.
"""

from __future__ import annotations

from sqlastack.core.exceptions import ZopeNotAvailable

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
