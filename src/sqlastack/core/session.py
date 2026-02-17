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

    Creates sessions in standalone mode (zope=False). Zope-integrated
    sessions (zope=True) are deferred to Phase 2.
    """

    def __init__(
        self,
        engine: Engine | None = None,
        config: SQLAStackConfig | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            engine: Pre-created engine. Takes precedence over config.
            config: Configuration. If None and engine is None, loaded from env.
        """
        if engine is not None:
            self._engine = engine
        elif config is not None:
            self._engine = create_sqlastack_engine(config)
        else:
            self._engine = create_sqlastack_engine()
        self._session_factory = sessionmaker(bind=self._engine)

    @property
    def engine(self) -> Engine:
        """Return the underlying SQLAlchemy engine."""
        return self._engine

    def create(self, zope: bool = False) -> Session:
        """Create a new session.

        Args:
            zope: If True, raises NotImplementedError (Phase 2).
                  If False, creates a standard SQLAlchemy session.

        Returns:
            A new SQLAlchemy Session instance.
        """
        if zope:
            raise NotImplementedError(
                "Zope session integration is not yet implemented. Use zope=False."
            )
        return self._session_factory()

    @contextlib.contextmanager
    def session_scope(self, zope: bool = False) -> Generator[Session, None, None]:
        """Context manager providing a transactional scope.

        Commits on success, rolls back on exception, always closes.

        Raises:
            IntegrityError: On constraint violation.
            DataError: On invalid data.
            ProgrammingError: On SQL syntax error.
            CommitFailed: On other commit failures.
            RollbackFailed: If rollback itself fails.
        """
        session = self.create(zope=zope)
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
        self._engine.dispose()
