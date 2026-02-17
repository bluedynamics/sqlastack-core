"""sqlastack.plone - Optional Plone/Zope integration.

Uses conditional imports. When Zope packages are not installed
(e.g., in a Celery worker), this module is inert.
"""

try:
    from zope.sqlalchemy import register as _register  # noqa: F401
    from transaction import get as _get_transaction  # noqa: F401

    HAS_ZOPE = True
except ImportError:
    HAS_ZOPE = False
