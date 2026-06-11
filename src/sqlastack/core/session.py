"""Session factory - Abstract Factory pattern."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Generator

import sqlalchemy.exc
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from sqlastack.core.config import SQLAStackConfig
from sqlastack.core.engine import create_sqlastack_engine
from sqlastack.core.exceptions import CommitFailed
from sqlastack.core.exceptions import DataError
from sqlastack.core.exceptions import IntegrityError
from sqlastack.core.exceptions import ProgrammingError
from sqlastack.core.exceptions import RollbackFailed

logger = logging.getLogger(__name__)


def _translate_exception(exc: sqlalchemy.exc.SQLAlchemyError) -> Exception:
    """Translate a SQLAlchemy exception into a sqlastack exception."""
    if isinstance(exc, sqlalchemy.exc.IntegrityError):
        return IntegrityError(str(exc), original=exc)
    if isinstance(exc, sqlalchemy.exc.DataError):
        return DataError(str(exc), original=exc)
    if isinstance(exc, sqlalchemy.exc.ProgrammingError):
        return ProgrammingError(str(exc), original=exc)
    return CommitFailed(str(exc), original=exc)


class SessionFactory:
    """Abstract Factory for SQLAlchemy sessions.

    Creates sessions in two modes:
    - Standalone (zope=False): Standard SQLAlchemy session with explicit commit.
    - Zope-integrated (zope=True): Session registered with zope.sqlalchemy,
      managed by the Zope transaction manager.
    """

    def __init__(
        self,
        engine: Engine | None = None,
        config: SQLAStackConfig | None = None,
        keep_session: bool = False,
    ) -> None:
        """Initialize the factory.

        Args:
            engine: Pre-created engine. Takes precedence over config.
            config: Configuration. If None and engine is None, loaded from env.
            keep_session: If True, keep Zope sessions open after transaction ends.
        """
        if engine is not None:
            self._engine = engine
        elif config is not None:
            self._engine = create_sqlastack_engine(config)
        else:
            self._engine = create_sqlastack_engine()
        self._session_factory = sessionmaker(bind=self._engine)
        self._keep_session = keep_session
        self._scoped_session = None

    @property
    def engine(self) -> Engine:
        """Return the underlying SQLAlchemy engine."""
        return self._engine

    def _ensure_scoped_session(self):
        """Lazily create the scoped session for Zope mode.

        Uses a dedicated ``sessionmaker`` so that registering zope.sqlalchemy's
        transaction events does not attach them to the standalone sessionmaker.
        Sharing one sessionmaker would pollute standalone sessions with the
        Zope ``before_commit`` hook and break direct ``session.commit()``.
        """
        if self._scoped_session is None:
            from sqlastack.plone import create_scoped_zope_session

            zope_session_factory = sessionmaker(bind=self._engine)
            self._scoped_session = create_scoped_zope_session(
                zope_session_factory,
                keep_session=self._keep_session,
            )
        return self._scoped_session

    def create(self, zope: bool = False) -> Session:
        """Create a new session.

        Args:
            zope: If True, returns a Zope-integrated session.
                  If False, creates a standard SQLAlchemy session.

        Returns:
            A new SQLAlchemy Session instance.

        Raises:
            ZopeNotAvailable: If zope=True but zope.sqlalchemy is not installed.
        """
        if zope:
            return self._ensure_scoped_session()
        return self._session_factory()

    @contextlib.contextmanager
    def session_scope(self, zope: bool = False) -> Generator[Session, None, None]:
        """Context manager providing a transactional scope.

        In standalone mode (zope=False): commits on success, rolls back on
        exception, always closes.

        In Zope mode (zope=True): yields the session without commit/rollback.
        The Zope transaction manager handles the transaction lifecycle.

        Raises:
            IntegrityError: On constraint violation (standalone mode).
            DataError: On invalid data (standalone mode).
            ProgrammingError: On SQL syntax error (standalone mode).
            CommitFailed: On other commit failures (standalone mode).
            RollbackFailed: If rollback itself fails (standalone mode).
            ZopeNotAvailable: If zope=True but zope.sqlalchemy is not installed.
        """
        if zope:
            session = self.create(zope=True)
            yield session
            return

        session = self.create(zope=False)
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
            raise _translate_exception(exc) from exc
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        """Dispose of the underlying engine and all connections."""
        if self._scoped_session is not None:
            self._scoped_session.remove()
        self._engine.dispose()
