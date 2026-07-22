import secrets

from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import User


async def resolve_user(
    response: Response,
    db: Session = Depends(get_db),
    guest_token: str | None = Cookie(default=None),
) -> User:
    settings = get_settings()
    cookie_name = settings.guest_cookie_name

    if guest_token:
        user = db.query(User).filter(User.guest_token == guest_token).one_or_none()
        if user:
            return user

    token = secrets.token_urlsafe(24)
    user = User(guest_token=token)
    db.add(user)
    db.commit()
    db.refresh(user)
    response.set_cookie(
        key=cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return user


def ensure_owner(resource_user_id, current_user: User) -> None:
    if resource_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
