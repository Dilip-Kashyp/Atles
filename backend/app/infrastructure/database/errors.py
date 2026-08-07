import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from sqlalchemy.exc import IntegrityError, NoResultFound

from app.domain.shared.exceptions import (
    AlreadyMemberError,
    ConflictError,
    DuplicateEmailError,
    DuplicateSlugError,
    NotFoundError,
)

log = logging.getLogger(__name__)

T = TypeVar("T")

def handle_db_errors(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to intercept SQLAlchemy exceptions and map them to domain exceptions.
    Ensures that domain repositories do not leak infrastructure-level database exceptions.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except IntegrityError as exc:
            # Parse the underlying DB driver error string
            err_msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
            
            # Map specific constraints or keywords to Domain Exceptions
            if "email" in err_msg:
                log.debug("DB IntegrityError mapped to DuplicateEmailError: %s", err_msg)
                raise DuplicateEmailError("A user with this email already exists.") from exc
            
            if "slug" in err_msg:
                log.debug("DB IntegrityError mapped to DuplicateSlugError: %s", err_msg)
                raise DuplicateSlugError("A workspace with this slug already exists.") from exc
                
            if "workspace" in err_msg and ("member" in err_msg or "user" in err_msg):
                log.debug("DB IntegrityError mapped to AlreadyMemberError: %s", err_msg)
                raise AlreadyMemberError("User is already a member of this workspace.") from exc
                
            # Generic Conflict Fallback
            log.warning("Unmapped DB IntegrityError caught: %s", exc)
            raise ConflictError("A database conflict occurred.") from exc
            
        except NoResultFound as exc:
            log.debug("DB NoResultFound mapped to NotFoundError: %s", exc)
            raise NotFoundError("The requested database record was not found.") from exc
            
    return wrapper
