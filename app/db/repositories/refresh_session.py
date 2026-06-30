from uuid import UUID

from sqlalchemy import select

from app.db.models.refresh_session import RefreshSession
from app.db.repositories.base import BaseRepository


class RefreshSessionRepository(BaseRepository[RefreshSession]):
    model = RefreshSession

    async def get_by_jti_and_token_hash(
        self,
        *,
        jti: UUID,
        token_hash: str,
        for_update: bool = False,
    ) -> RefreshSession | None:
        query = select(RefreshSession).where(
            RefreshSession.jti == jti,
            RefreshSession.token_hash == token_hash,
        )

        if for_update:
            query = query.with_for_update()

        result = await self.session.execute(query)

        return result.scalar_one_or_none()
