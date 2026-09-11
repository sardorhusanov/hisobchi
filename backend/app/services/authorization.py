from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from app.models.entities import Role, User
from fastapi import HTTPException, status

P = ParamSpec("P")
T = TypeVar("T")


class PermissionDenied(Exception):
    pass


def can_manage_members(user: User) -> bool:
    return user.role in {Role.SUPER_ADMIN, Role.OWNER}


def can_view_members(user: User) -> bool:
    return user.role in {Role.SUPER_ADMIN, Role.OWNER, Role.PARTNER}


def require_member_management(user: User) -> None:
    if not can_manage_members(user):
        raise PermissionDenied("Only super admin or owner can manage members")


def to_http_permission_error(error: PermissionDenied) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))


def authorized(
    check: Callable[[User], None],
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    def decorator(handler: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(handler)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            user = kwargs.get("current_user")
            if not isinstance(user, User):
                raise PermissionDenied("Authenticated user is required")
            check(user)
            return await handler(*args, **kwargs)

        return wrapped

    return decorator
