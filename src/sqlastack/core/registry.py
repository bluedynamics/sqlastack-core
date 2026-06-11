"""DatabaseRegistry - holds one SessionFactory per logical database name."""

from __future__ import annotations

from collections.abc import Generator
from sqlalchemy.orm import Session
from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.exceptions import UnknownDatabase
from sqlastack.core.session import SessionFactory
import contextlib
import os
import re


_NAME_RE = re.compile(r"^SQLASTACK_([A-Z0-9]+)_URL$")


class DatabaseRegistry:
    """Registry of named databases, each backed by a lazily-created SessionFactory.

    Multi-DB-capable by design; today typically one name (``fh``) is registered.
    Adding another database is pure configuration, no code change.

    Not thread-safe: assumes one registry is used per worker/thread. Do not share
    a single registry instance across threads (lazy factory creation is unlocked).
    """

    def __init__(self, configs: dict[str, SQLAStackConfig] | None = None) -> None:
        self._configs: dict[str, SQLAStackConfig] = dict(configs or {})
        self._factories: dict[str, SessionFactory] = {}

    @classmethod
    def from_env(cls) -> DatabaseRegistry:
        """Discover all ``SQLASTACK_<NAME>_URL`` variables and build the registry.

        Database names must be a single ``[A-Z0-9]+`` token; names containing
        underscores (e.g. ``SQLASTACK_MY_DB_URL``) are not discovered.
        """
        configs: dict[str, SQLAStackConfig] = {}
        for key in os.environ:
            match = _NAME_RE.match(key)
            if match:
                name = match.group(1).lower()
                configs[name] = SQLAStackConfig.from_env(name=name)
        return cls(configs)

    def register(self, name: str, config: SQLAStackConfig) -> None:
        """Register or replace a named database configuration.

        If a SessionFactory was already created for this name, it is disposed
        before being replaced, so its engine and connection pool are released.
        """
        self._configs[name] = config
        evicted = self._factories.pop(name, None)
        if evicted is not None:
            evicted.dispose()

    def names(self) -> list[str]:
        """Return all registered names, sorted."""
        return sorted(self._configs)

    def session_factory(self, name: str) -> SessionFactory:
        """Return (lazily creating) the SessionFactory for ``name``."""
        if name not in self._configs:
            raise UnknownDatabase(
                f"No database registered under name {name!r}. Known: {self.names()}"
            )
        if name not in self._factories:
            self._factories[name] = SessionFactory(config=self._configs[name])
        return self._factories[name]

    def session(self, name: str, zope: bool = False) -> Session:
        """Create a new session for the named database."""
        return self.session_factory(name).create(zope=zope)

    @contextlib.contextmanager
    def session_scope(
        self, name: str, zope: bool = False
    ) -> Generator[Session, None, None]:
        """Transactional scope for the named database (delegates to SessionFactory)."""
        with self.session_factory(name).session_scope(zope=zope) as session:
            yield session

    def dispose_all(self) -> None:
        """Dispose all created SessionFactories and their engines."""
        for factory in self._factories.values():
            factory.dispose()
        self._factories.clear()
