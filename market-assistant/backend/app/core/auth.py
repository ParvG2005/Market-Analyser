import uuid

from fastapi import Header

DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(
    x_dev_user: uuid.UUID | None = Header(default=None),
) -> uuid.UUID:
    # Dev/test stub: honor an explicit X-Dev-User header (lets tests exercise
    # per-user scoping), else fall back to a fixed dev user. Phase 11 replaces
    # this with real JWT auth.
    return x_dev_user if x_dev_user is not None else DEV_USER_ID


async def get_current_user_id_from_ws_token(token: str) -> uuid.UUID:
    # Dev/test stub for WS auth: treat the token as the user's UUID.
    # Phase 11 replaces with real token verification.
    return uuid.UUID(token)
