from __future__ import annotations

from functools import wraps
from typing import Any
from typing import Callable
from typing import TypeVar

from flask import abort
from flask import g

from app.auth import login_required

F = TypeVar("F", bound=Callable[..., Any])


def roles_required(*roles: str) -> Callable[[F], F]:
    def decorator(view: F) -> F:
        @login_required
        @wraps(view)
        def wrapped_view(**kwargs: Any):  # type: ignore[no-untyped-def]
            if g.user is None:
                abort(403)

            if g.user["role"] not in roles:
                abort(403)

            return view(**kwargs)

        return wrapped_view  # type: ignore[return-value]

    return decorator

