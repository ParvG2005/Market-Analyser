import uuid

from fastapi import Header, HTTPException, status
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.security import verify_token

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_dev_user: uuid.UUID | None = Header(default=None),
) -> uuid.UUID:
    settings = get_settings()
    # 1) A real Bearer token is authoritative in EVERY environment.
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :].strip()
        try:
            return verify_token(token, settings).id
        except ValidationError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    # 2) Non-prod dev/test convenience: honor X-Dev-User, else the fixed dev user.
    #    (Preserves existing test behavior; NEVER active in prod.)
    if settings.env != "prod":
        return x_dev_user if x_dev_user is not None else DEV_USER_ID
    # 3) Prod with no/invalid bearer -> reject.
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")


async def get_current_user_id_from_ws_token(token: str) -> uuid.UUID:
    settings = get_settings()
    try:
        return verify_token(token, settings).id
    except (HTTPException, ValidationError):
        # Non-prod fallback: legacy test path treats the token as a raw user UUID.
        if settings.env != "prod":
            try:
                return uuid.UUID(token)
            except ValueError:
                pass
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from None
