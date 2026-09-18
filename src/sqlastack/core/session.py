"""Session factory - Abstract Factory pattern."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Generator

import sqlalchemy.exc
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
from sqlastack.core.exceptions import ConfigurationError
from sqlastack.core.exceptions import RollbackFailed
from sqlastack.core.exceptions import translate_exception

logger = logging.getLogger(__name__)


class SessionFactory:
    """Abstract Factory for SQLAlchemy sessions.

    Two distinct APIs for two distinct session kinds:

    - :meth:`create` / :meth:`session_scope`: standalone sessions with
      explicit commit (Celery workers, scripts, tests).
    - :meth:`zope_session` / :meth:`remove_zope_session`: the SHARED
      thread-local session registered with zope.sqlalchemy, whose transaction
      lifecycle is owned by the Zope transaction manager (Plone).
    """

    def __init__(
        self,
        engine: Engine | None = None,
        config: SQLAStackConfig | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            engine: Pre-created engine. Takes precedence over config.
            config: Configuration used to create an engine.

        Raises:
            ConfigurationError: If neither engine nor config is given.
        """
        if engine is not None:
            self._engine = engine
        elif config is not None:
            self._engine = create_sqlastack_engine(config)
        else:
            raise ConfigurationError(
                "SessionFactory requires either an engine or a config; "
                "implicit environment lookup was removed (use "
                "SQLAStackConfig.from_env(name) explicitly)."
            )
        self._session_factory = sessionmaker(bind=self._engine)
        self._scoped_session: scoped_session[Session] | None = None

    @property
    def engine(self) -> Engine:
        """Return the underlying SQLAlchemy engine."""
        return self._engine

    def create(self) -> Session:
        """Create a NEW standalone SQLAlchemy session.

        The caller owns the session (close it). For the Zope-managed shared
        session use :meth:`zope_session` instead.
        """
        return self._session_factory()

    def zope_session(self) -> scoped_session[Session]:
        """Return the SHARED, thread-local Zope-managed session proxy.

        This is NOT a new session: every call in the same thread returns the
        same underlying session, registered with zope.sqlalchemy. Its
        transaction lifecycle is owned by the Zope transaction manager
        (``transaction.commit()`` / ``transaction.abort()``). Do NOT call
        ``close()`` on it; call :meth:`remove_zope_session` at the end of the
        request/task instead.

        Uses a dedicated ``sessionmaker`` so that registering zope.sqlalchemy's
        transaction events does not attach them to the standalone sessionmaker.
        Sharing one sessionmaker would pollute standalone sessions with the
        Zope ``before_commit`` hook and break direct ``session.commit()``.

        Raises:
            ZopeNotAvailable: If zope.sqlalchemy is not installed (checked on
                every call).
        """
        from sqlastack.plone import _check_zope

        _check_zope()
        if self._scoped_session is None:
            from sqlastack.plone import create_scoped_zope_session

            zope_session_factory = sessionmaker(bind=self._engine)
            self._scoped_session = create_scoped_zope_session(zope_session_factory)
        return self._scoped_session

    def remove_zope_session(self) -> None:
        """Dispose the CURRENT thread's Zope session (request-end teardown).

        Safe to call when no Zope session was ever created. Each worker
        thread must call this itself; it cannot clean up other threads.
        """
        if self._scoped_session is not None:
            self._scoped_session.remove()

    @contextlib.contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Standalone transactional scope: commit on success, rollback on
        exception, always close.

        Raises:
            IntegrityError / DataError / ProgrammingError / CommitFailed:
                Translated commit-time failures.
            RollbackFailed: If rollback itself fails.
        """
        session = self.create()
        try:
            yield session
            session.commit()
        except sqlalchemy.exc.SQLAlchemyError as exc:
            try:
                session.rollback()
            except sqlalchemy.exc.SQLAlchemyError as rollback_exc:
                raise RollbackFailed(
                    str(rollback_exc), original=rollback_exc
                ) from exc
            raise translate_exception(exc) from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """Dispose engine and this thread's Zope session.

        Note: scoped sessions created by OTHER threads are not removed here —
        call :meth:`remove_zope_session` per thread, or only dispose at
        process shutdown when no sessions are live.
        """
        self.remove_zope_session()
        self._engine.dispose()
