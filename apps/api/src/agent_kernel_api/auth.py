"""API authentication middleware for Agent Kernel."""

from __future__ import annotations

import os
from collections.abc import Iterable

from fastapi import Request
from kernel_identity import ApiKey, Principal, WorkspaceMembership
from kernel_storage import ApiKeyRepository, PrincipalRepository, WorkspaceMembershipRepository
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.types import ASGIApp

AUTH_CONTEXT_STATE_KEY = "auth_context"
DEFAULT_AUTH_EXEMPT_PATHS = frozenset({"/healthz"})


class AuthContext:
    """Authenticated request context loaded from a valid API key."""

    def __init__(
        self,
        *,
        principal: Principal,
        api_key: ApiKey,
        memberships: list[WorkspaceMembership],
    ) -> None:
        self.principal = principal
        self.api_key = api_key
        self.memberships = memberships


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests with an Agent Kernel API key."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        session_factory: sessionmaker[Session],
        exempt_paths: Iterable[str] = DEFAULT_AUTH_EXEMPT_PATHS,
    ) -> None:
        super().__init__(app)
        self._session_factory = session_factory
        self._exempt_paths = frozenset(exempt_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        plaintext_key = extract_api_key(request)
        if plaintext_key is None:
            return _unauthorized("API key is required.")

        with self._session_factory() as session:
            api_key = ApiKeyRepository(session).authenticate(plaintext_key)
            if api_key is None:
                return _unauthorized("API key is invalid, revoked, or expired.")

            principal = PrincipalRepository(session).get(api_key.principal_id)
            if principal is None or principal.disabled:
                return _unauthorized("API key principal is unavailable.")

            memberships = WorkspaceMembershipRepository(session).list_for_principal(principal.id)

        setattr(
            request.state,
            AUTH_CONTEXT_STATE_KEY,
            AuthContext(principal=principal, api_key=api_key, memberships=memberships),
        )
        return await call_next(request)


def api_key_auth_enabled_from_env() -> bool:
    """Return whether API key authentication should be enforced."""

    value = os.getenv("AGENT_KERNEL_API_KEY_AUTH_ENABLED", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def extract_api_key(request: Request) -> str | None:
    """Extract an API key from supported request headers."""

    authorization = request.headers.get("authorization")
    if authorization is not None:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()

    api_key = request.headers.get("x-agent-kernel-api-key")
    if api_key is not None and api_key.strip():
        return api_key.strip()

    return None


def get_auth_context(request: Request) -> AuthContext | None:
    """Return the authenticated context for the request, if middleware loaded one."""

    context = getattr(request.state, AUTH_CONTEXT_STATE_KEY, None)
    if isinstance(context, AuthContext):
        return context
    return None


def _unauthorized(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_401_UNAUTHORIZED,
        content={"detail": message},
    )
