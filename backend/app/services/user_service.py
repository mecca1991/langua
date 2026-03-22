from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import JWTPayload


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.users = UserRepository(db)

    async def ensure_user(self, payload: JWTPayload) -> User:
        existing = await self.users.get_by_id(payload.sub)
        if existing is not None:
            return existing

        user = User(
            id=payload.sub,
            email=payload.email,
            name=payload.name,
            avatar_url=payload.avatar_url,
        )
        user = await self.users.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
