import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.core.celery_app import celery_app
from app.core.database import session_context
from app.db.models.season import UserSeasonHistory

logger = logging.getLogger(__name__)


@celery_app.task(queue="default")
def close_active_season() -> None:
    """
    Celery Beat task: runs periodically (e.g. daily) to check if the current active
    season has expired. If it has, it archives user progress and resets XP/levels,
    then looks for the next season to activate.
    """
    async def _run() -> None:
        from app.db.models.season import Season
        from app.db.models.user import User

        now = datetime.now(UTC)

        async with session_context() as session:
            # 1. Find the current active season
            active_season_result = await session.execute(
                select(Season).where(Season.is_active.is_(True)).limit(1)
            )
            active_season = active_season_result.scalar_one_or_none()

            if active_season and active_season.ends_at <= now:
                logger.info(f"Season '{active_season.name}' (ID: {active_season.id}) has ended. Closing...")

                # Archive all public users' stats
                users_result = await session.execute(
                    select(User).where(User.is_private.is_(False))
                )
                users = list(users_result.scalars().all())

                histories = []
                for user in users:
                    histories.append(
                        UserSeasonHistory(
                            user_id=user.id,
                            season_id=active_season.id,
                            final_xp=user.xp,
                            final_level=user.level,
                            final_rank=user.rank,
                        )
                    )
                
                session.add_all(histories)

                # Reset all users (even private ones)
                await session.execute(
                    update(User).values(
                        xp=0,
                        level=1,
                        level_progress=0,
                        next_level_xp=1000,
                        rank=None,
                    )
                )

                # Deactivate the current season
                active_season.is_active = False
                session.add(active_season)

                logger.info(f"Archived {len(histories)} users and reset XP for all users.")

                # Try to activate the next season
                next_season_result = await session.execute(
                    select(Season).where(
                        Season.is_active.is_(False),
                        Season.starts_at <= now,
                        Season.ends_at > now
                    ).order_by(Season.starts_at.asc()).limit(1)
                )
                next_season = next_season_result.scalar_one_or_none()

                if next_season:
                    next_season.is_active = True
                    session.add(next_season)
                    # Update users' season_label
                    await session.execute(
                        update(User).values(season_label=next_season.name)
                    )
                    logger.info(f"Activated next season '{next_season.name}'.")
                else:
                    await session.execute(
                        update(User).values(season_label="Межсезонье")
                    )
                    logger.info("No next season available. Set users to 'Межсезонье'.")

                await session.commit()
                logger.info("Season close completed successfully.")
            else:
                logger.debug("No active season to close or season hasn't ended yet.")

    return asyncio.run(_run())
