"""DatabaseRegistry - holds one SessionFactory per logical database name."""

from __future__ import annotations

from contextlib import AbstractContextManager
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.config import _load_dotenv
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import UnknownDatabase
from sqlastack.core.session import SessionFactory
import os
import re
import threading


_NAME_RE = re.compile(r"^SQLASTACK_([A-Z0-9]+)_URL$")
_VALID_NAME_RE = re.compile(r"^[a-z0-9]+$")


def _normalize_name(name: str) -> str:
    """Lowercase and validate a database name (must match ``[a-z0-9]+``)."""
    normalized = name.lower()
    if not _VALID_NAME_RE.match(normalized):
        raise ConfigurationError(
            f"Invalid database name {name!r}: must match [a-z0-9]+ "
            "(no underscores — env discovery cannot express them)."
        )
    return normalized


class DatabaseRegistry:
    """Registry of named databases, each backed by a lazily-created SessionFactory.

    Multi-DB-capable by design; today typically one name (``fh``) is registered.
    Names are case-insensitive (normalized to lowercase).

    Thread-safety: lazy factory creation is locked, so a process-wide registry
    can serve concurrent first requests. Registration is meant for startup
    (single-threaded); call :meth:`warm_up` after registering to avoid any
    first-request latency.
    """

    def __init__(self, configs: dict[str, SQLAStackConfig] | None = None) -> None:
        self._configs: dict[str, SQLAStackConfig] = {
            _normalize_name(name): config for name, config in (configs or {}).items()
        }
        self._factories: dict[str, SessionFactory] = {}
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls) -> DatabaseRegistry:
        """Discover all ``SQLASTACK_<NAME>_URL`` variables and build the registry.

        Loads the .env file (if python-dotenv is installed) BEFORE scanning, so
        names defined only in .env are discovered too. Names must be a single
        ``[A-Z0-9]+`` token; underscores are not discoverable.
        """
        _load_dotenv()
        configs: dict[str, SQLAStackConfig] = {}
        for key in os.environ:
            match = _NAME_RE.match(key)
            if match:
                name = match.group(1).lower()
                configs[name] = SQLAStackConfig.from_env(name)
        return cls(configs)

    def register(self, name: str, config: SQLAStackConfig) -> None:
        """Register or replace a named database configuration.

        Raises:
            ConfigurationError: If a SessionFactory for this name is already
                live — replacing it would dispose an engine other threads may
                be using. Dispose explicitly first (shutdown), then register.
        """
        normalized = _normalize_name(name)
        if normalized in self._factories:
            raise ConfigurationError(
                f"Database {normalized!r} is in use (SessionFactory exists). "
                "Dispose it explicitly before re-registering."
            )
        self._configs[normalized] = config

    def register_factory(self, name: str, factory: SessionFactory) -> None:
        """Register a pre-built SessionFactory (tests, embedded engines).

        Note: :meth:`dispose_all` disposes this factory's engine like any
        other — don't dispose a registry holding a borrowed engine unless
        that is intended.
        """
        normalized = _normalize_name(name)
        if normalized in self._factories:
            raise ConfigurationError(
                f"Database {normalized!r} is in use (SessionFactory exists)."
            )
        self._factories[normalized] = factory

    def names(self) -> list[str]:
        """Return all registered names (configs and injected factories), sorted."""
        return sorted(self._configs.keys() | self._factories.keys())

    def session_factory(self, name: str) -> SessionFactory:
        """Return (lazily creating, thread-safe) the SessionFactory for ``name``."""
        normalized = _normalize_name(name)
        factory = self._factories.get(normalized)
        if factory is not None:
            return factory
        if normalized not in self._configs:
            raise UnknownDatabase(
                f"No database registered under name {normalized!r}. "
                f"Known: {self.names()}"
            )
        with self._lock:
            if normalized not in self._factories:
                self._factories[normalized] = SessionFactory(
                    config=self._configs[normalized]
                )
        return self._factories[normalized]

    def warm_up(self) -> None:
        """Eagerly create all SessionFactories (call once at startup)."""
        for name in self.names():
            self.session_factory(name)

    def session_scope(self, name: str) -> AbstractContextManager[Session]:
        """Standalone transactional scope for the named database."""
        return self.session_factory(name).session_scope()

    def zope_session(self, name: str) -> scoped_session[Session]:
        """Shared thread-local Zope session for the named database.

        See :meth:`SessionFactory.zope_session` for the ownership contract.
        """
        return self.session_factory(name).zope_session()

    def remove_zope_sessions(self) -> None:
        """Request-end teardown: remove this thread's Zope sessions everywhere."""
        # copy: another thread's first request may insert a factory mid-iteration
        for factory in list(self._factories.values()):
            factory.remove_zope_session()

    def dispose_all(self) -> None:
        """Dispose all created SessionFactories and their engines (shutdown)."""
        for factory in list(self._factories.values()):
            factory.dispose()
        self._factories.clear()
