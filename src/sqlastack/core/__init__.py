"""sqlastack.core - Core SQL access layer infrastructure."""

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
from sqlastack.core.exceptions import SQLAStackError
from sqlastack.core.session import SessionFactory

__all__ = [
    "SQLAStackConfig",
    "SQLAStackError",
    "SessionFactory",
    "create_sqlastack_engine",
]
