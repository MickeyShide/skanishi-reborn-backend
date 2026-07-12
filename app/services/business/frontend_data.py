from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
import inspect
from math import asin, cos, pi, radians, sin, sqrt

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.achievement import Achievement, UserAchievement
from app.db.models.enums import Rarity, UIColorToken
from app.db.models.event import Event
from app.db.models.item_secrets import ItemSecret
from app.db.models.quest import Quest
from app.db.models.user import User
from app.db.models.xp_event import XpEvent
from app.schemas.common import MapPointsQueryParams, XpHistoryQueryParams
from app.schemas.frontend import (
    AchievementResponse,
    AchievementsResponse,
    AchievementSummaryResponse,
    ActiveEventResponse,
    FrontendAppStateResponse,
    FrontendUserResponse,
    LatestAchievementResponse,
    MapPinResponse,
    MapPointsResponse,
    NearbyPointResponse,
    PointDetailResponse,
    ProfileLinkResponse,
    QuestCardResponse,
    QuestsResponse,
    RecentRewardResponse,
    ScanClaimRequest,
    ScanClaimResponse,
    StatCardResponse,
    XpHistoryGroupResponse,
    XpHistoryItemResponse,
    XpHistoryResponse,
    XpWeekSummaryResponse,
)
from app.services.achievement import AchievementService
from app.services.business.base import BusinessService
from app.services.errors import RewardAlreadyClaimedError, ScanNotFoundError
from app.services.event import EventService
from app.services.item_secret import ItemSecretService
from app.services.quest import QuestService
from app.services.user import UserService
from app.services.validation import ValidationService
from app.services.xp_event import XpEventService


class FrontendDataBusinessService(BusinessService):
    achievement_service: AchievementService
    event_service: EventService
    item_secret_service: ItemSecretService
    quest_service: QuestService
    user_service: UserService
    validation_service: ValidationService
    xp_event_service: XpEventService

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(session=session)

    async def get_app_state(self, current_user: User) -> FrontendAppStateResponse:
        session = await self._get_session()

        # Record the login and update streak (idempotent within the same calendar day)
        from app.services.streak import StreakService
        streak_svc = StreakService(session)
        user = await streak_svc.record_login(current_user)

        quests = await self.quest_service.get_active_quests()
        active_event = await self.event_service.get_active_event()
        map_secrets = await self.item_secret_service.get_active_map_secrets()
        map_secrets_by_id = {str(secret.id): secret for secret in map_secrets}
        opened_ids = await self._get_opened_secret_ids(
            user.id,
            [secret.id for secret in map_secrets],
        )
        recent_events = await self.xp_event_service.get_recent_user_events(
            user_id=user.id,
            limit=3,
        )
        xp_history_events = await self.xp_event_service.get_user_history(
            user_id=user.id,
            limit=50,
            offset=0,
        )
        week_start, week_end = self._get_current_week_bounds()
        xp_week_events = await self.xp_event_service.get_user_events_between(
            user_id=user.id,
            occurred_at_from=week_start,
            occurred_at_to=week_end,
        )
        achievement_states = await self.achievement_service.get_user_achievement_states(
            user_id=user.id
        )
        scan_count = await self.xp_event_service.count_user_events_by_tag(
            user_id=user.id,
            tag="SCAN",
        )

        map_data = self._build_map_data(
            map_secrets=map_secrets,
            opened_ids=opened_ids,
            quest_lookup=self._build_quest_lookup(quests),
            user_id=user.id,
            lat=None,
            lon=None,
            radius_meters=1000,
            rarity=None,
            category=None,
            done=None,
        )
        achievements = self._build_achievements(achievement_states)
        unlocked_count = sum(1 for achievement in achievements if achievement.unlocked)
        achievement_summary = AchievementSummaryResponse(
            unlocked=unlocked_count,
            total=len(achievement_states),
        )

        latest_achievement = None
        unlocked_states = [
            (ach, u_ach) for ach, u_ach in achievement_states
            if u_ach and u_ach.unlocked and u_ach.unlocked_at
        ]
        if unlocked_states:
            latest_ach, latest_u_ach = max(unlocked_states, key=lambda x: x[1].unlocked_at)
            latest_achievement = LatestAchievementResponse(
                name=latest_ach.name,
                description=latest_ach.description,
                xp=latest_ach.reward_xp,
                rarity=latest_ach.rarity,
                unlocked_at=latest_u_ach.unlocked_at,
            )

        stats = self._build_stats(
            scan_count=scan_count,
            point_count=len(map_secrets),
            quest_count=len(quests),
            achievement_count=unlocked_count,
        )
        profile_links = self._build_profile_links(
            user=user,
            achievement_unlocked=unlocked_count,
            achievement_total=len(achievement_states),
        )

        return FrontendAppStateResponse(
            user=self._build_frontend_user(user),
            active_event=self._build_active_event(active_event),
            quests=[self._build_quest_card(quest) for quest in quests],
            recent_rewards=[
                self._build_recent_reward(event, map_secrets_by_id)
                for event in recent_events
            ],
            map_pins=map_data["map_pins"],
            nearby_points=map_data["nearby_points"],
            point_details=map_data["point_details"],
            stats=stats,
            profile_links=profile_links,
            xp_history_groups=self._build_xp_history_groups(
                xp_history_events,
                map_secrets_by_id,
            ),
            xp_weekly=self._build_xp_weekly_summary(
                xp_week_events,
                week_start=week_start,
            ),
            achievements=achievements,
            achievement_summary=achievement_summary,
            latest_achievement=latest_achievement,
        )

    async def get_map_points(
        self,
        current_user: User,
        params: MapPointsQueryParams,
    ) -> MapPointsResponse:
        user = current_user
        quests = await self.quest_service.get_active_quests()
        map_secrets = await self.item_secret_service.get_active_map_secrets()
        opened_ids = await self._get_opened_secret_ids(
            user.id,
            [secret.id for secret in map_secrets],
        )
        map_data = self._build_map_data(
            map_secrets=map_secrets,
            opened_ids=opened_ids,
            quest_lookup=self._build_quest_lookup(quests),
            user_id=user.id,
            lat=params.lat,
            lon=params.lon,
            radius_meters=params.radius_meters,
            rarity=params.rarity,
            category=params.category,
            done=params.done,
        )

        return MapPointsResponse(**map_data)

    async def get_quests(self, current_user: User) -> QuestsResponse:
        quests = await self.quest_service.get_active_quests()

        return QuestsResponse(
            items=[self._build_quest_card(quest) for quest in quests]
        )

    async def get_xp_history(
        self,
        current_user: User,
        params: XpHistoryQueryParams,
    ) -> XpHistoryResponse:
        user = current_user
        events = await self.xp_event_service.get_user_history(
            user_id=user.id,
            limit=params.limit,
            offset=params.offset,
            tag=params.tag,
        )
        week_start, week_end = self._get_current_week_bounds()
        week_events = await self.xp_event_service.get_user_events_between(
            user_id=user.id,
            occurred_at_from=week_start,
            occurred_at_to=week_end,
            tag=params.tag,
        )
        map_secrets = await self.item_secret_service.get_active_map_secrets()
        map_secrets_by_id = {str(secret.id): secret for secret in map_secrets}

        return XpHistoryResponse(
            groups=self._build_xp_history_groups(events, map_secrets_by_id),
            weekly=self._build_xp_weekly_summary(
                week_events,
                week_start=week_start,
            ),
        )

    async def get_achievements(self, current_user: User) -> AchievementsResponse:
        user = current_user
        states = await self.achievement_service.get_user_achievement_states(
            user_id=user.id
        )
        items = self._build_achievements(states)
        unlocked_count = sum(1 for item in items if item.unlocked)

        return AchievementsResponse(
            items=items,
            summary=AchievementSummaryResponse(
                unlocked=unlocked_count,
                total=len(states),
            ),
        )

    async def claim_scan_reward(
        self,
        current_user: User,
        dto: ScanClaimRequest,
    ) -> ScanClaimResponse:
        user = current_user
        
        # 0. Anti-Fraud & Rate Limiting
        from app.core.redis_client import redis_client, redis_fail_open
        from sqlalchemy.exc import IntegrityError
        from app.services.errors import ValidationConflictError, ScanNotFoundError, InvalidSecretTokenError
        from app.services.business.items import ItemsBusinessService
        
        redis = redis_client
        rate_limit_key = f"rate_limit:scan:{user.id}"
        
        # Atomically increment and set TTL using Redis Pipeline
        pipeline = redis.pipeline(transaction=True)
        if inspect.isawaitable(pipeline):
            pipeline = await pipeline

        async with pipeline as pipe:
            await pipe.incr(rate_limit_key)
            await pipe.expire(rate_limit_key, 5) # 5 seconds window
            results = await pipe.execute()
            
        requests_in_window = results[0]
        if not isinstance(requests_in_window, int):
            try:
                requests_in_window = int(requests_in_window)
            except (TypeError, ValueError):
                requests_in_window = 1

        if requests_in_window > 1:
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Слишком частые запросы на сканирование. Подождите 5 секунд.")
        
        items_service = ItemsBusinessService(self.session)
        try:
            claims = items_service._decode_item_secret_token(dto.token)
            raw_secret = claims.secret
        except InvalidSecretTokenError:
            raw_secret = dto.token

        hashed_secret = self.item_secret_service.hash_secret(raw_secret)
        item_secret = await self.item_secret_service.get_active_by_secret_hash(hashed_secret)
        if item_secret is None:
            # Check for UGC Sticker
            from app.db.models.user_stickers import UserSticker, UserStickerScan
            from sqlalchemy import select
            ugc_sticker = await self.session.execute(
                select(UserSticker).where(UserSticker.token == raw_secret, UserSticker.is_active.is_(True))
            )
            ugc_sticker = ugc_sticker.scalar_one_or_none()
            
            if ugc_sticker:
                from datetime import datetime, UTC
                from fastapi import HTTPException
                
                if ugc_sticker.user_id == current_user.id:
                    raise HTTPException(status_code=400, detail="Нельзя сканировать свой собственный стикер")
                    
                existing_scan = await self.session.execute(
                    select(UserStickerScan).where(
                        UserStickerScan.user_id == current_user.id,
                        UserStickerScan.sticker_id == ugc_sticker.id
                    )
                )
                if existing_scan.scalar_one_or_none():
                    return ScanClaimResponse(
                        status="already_collected",
                        item=None,
                        validation=None,
                        rewards=[],
                        user=self._build_frontend_user(user),
                        claimed_at=datetime.now(UTC),
                    )
                    
                # UGC logic
                scan = UserStickerScan(user_id=current_user.id, sticker_id=ugc_sticker.id)
                self.session.add(scan)
                
                ugc_sticker.scan_count += 1
                
                scanner_xp = 50
                scanner_coins = 5
                
                creator_xp = 25
                creator_coins = 2
                
                claimed_at = datetime.now(UTC)
                
                # Creator gets passive income
                from app.db.models.system_events import OutboxEvent
                from app.core.logger import request_id_ctx
                
                outbox_event_passive = OutboxEvent(
                    event_type="ugc_passive_income",
                    payload={
                        "event_id": f"ugc_income_{ugc_sticker.id}_{current_user.id}",
                        "creator_id": ugc_sticker.user_id,
                        "scanner_id": current_user.id,
                        "reward_xp": creator_xp,
                        "reward_coins": creator_coins,
                        "sticker_id": ugc_sticker.id,
                        "request_id": request_id_ctx.get(),
                    }
                )
                self.session.add(outbox_event_passive)
                
                # Scanner gets active rewards
                outbox_event_active = OutboxEvent(
                    event_type="scan_claimed",
                    payload={
                        "event_id": f"scan_ugc_{current_user.id}_{ugc_sticker.id}",
                        "user_id": current_user.id,
                        "scan_id": f"ugc_{ugc_sticker.id}",
                        "reward_xp": scanner_xp,
                        "reward_coins": scanner_coins,
                        "rarity": "common",
                        "claimed_at": claimed_at.isoformat(),
                        "request_id": request_id_ctx.get(),
                    }
                )
                self.session.add(outbox_event_active)
                
                await self.session.commit()
                
                frontend_user = self._build_frontend_user(user)
                frontend_user.xp += scanner_xp
                frontend_user.coins += scanner_coins
                
                rewards = [
                    {"type": "xp", "amount": scanner_xp, "name": "Опыт"},
                    {"type": "coin", "amount": scanner_coins, "name": "Монеты"}
                ]
                
                return ScanClaimResponse(
                    status="claimed",
                    item=None,
                    validation=None,
                    rewards=rewards,
                    user=frontend_user,
                    claimed_at=claimed_at,
                )
            
            raise ScanNotFoundError()

        from datetime import datetime, timedelta, UTC
        now_utc = datetime.now(UTC)
        if item_secret.cooldown_until is not None and item_secret.cooldown_until > now_utc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="QR_ON_COOLDOWN")

        catalog_row = await items_service.item_service.get_active_catalog_item(item_secret.item_id)
        if catalog_row is None:
            raise ScanNotFoundError()

        item = await items_service.item_service.get_active_item_for_update(item_secret.item_id)
        if item is None:
            raise ScanNotFoundError()

        existing_validation = await self.validation_service.get_user_item_validation(
            user_id=current_user.id,
            item_id=item.id,
        )
        item_response = items_service._build_full_item_response(catalog_row)
        
        if existing_validation is not None:
            return ScanClaimResponse(
                status="already_collected",
                item=item_response,
                validation=items_service._build_validation_short_response(existing_validation),
                rewards=[],
                user=self._build_frontend_user(user),
                claimed_at=existing_validation.created_at,
            )

        rank = item.validation_count + 1
        await items_service.item_service.increment_validation_count(item)

        try:
            validation = await self.validation_service.create_validation(
                user_id=current_user.id,
                item_id=item.id,
                item_secret_id=item_secret.id,
                rank=rank,
            )
        except IntegrityError as exc:
            raise ValidationConflictError() from exc

        await redis_fail_open(
            lambda: redis_client.delete(f"user:{current_user.id}:validation_count"),
            default=0,
        )

        claimed_at = datetime.now(UTC)
        
        import random
        base_xp = item_secret.reward_xp
        reward_xp = base_xp
        reward_coins = 0

        rarity_val = item_secret.rarity.value if hasattr(item_secret.rarity, "value") else item_secret.rarity
        
        if rarity_val == "mythic":
            reward_xp = base_xp * 5
            reward_coins = random.randint(50, 100)
        elif rarity_val == "legendary":
            reward_xp = base_xp * 3
            reward_coins = random.randint(20, 50)
        elif rarity_val == "epic":
            reward_xp = base_xp * 2
            if random.random() < 0.5:
                reward_coins = random.randint(10, 20)
        elif rarity_val == "rare":
            reward_xp = int(base_xp * 1.5)
            if random.random() < 0.2:
                reward_coins = random.randint(5, 10)

        reward_fragment_amount = 0
        reward_fragment_rarity = rarity_val
        if rarity_val == "mythic":
            reward_fragment_amount = random.randint(2, 3)
        elif rarity_val == "legendary":
            reward_fragment_amount = random.randint(1, 2)
        elif rarity_val == "epic":
            reward_fragment_amount = 1
        elif rarity_val == "rare":
            if random.random() < 0.5:
                reward_fragment_amount = 1
        elif rarity_val == "common":
            if random.random() < 0.3:
                reward_fragment_amount = 1

        is_first_blood = False
        if item_secret.validation_count == 0:
            is_first_blood = True
            reward_xp *= 5
            if reward_coins > 0:
                reward_coins *= 2

        rewards = [{"type": "xp", "amount": reward_xp, "name": "Опыт"}]
        if reward_coins > 0:
            rewards.append({"type": "coin", "amount": reward_coins, "name": "Монеты"})
        if reward_fragment_amount > 0:
            rewards.append({"type": "fragment", "amount": reward_fragment_amount, "name": f"Осколок ({reward_fragment_rarity})", "rarity": reward_fragment_rarity})

        if reward_xp > 0 or reward_coins > 0 or reward_fragment_amount > 0:
            # Create XP Event only if there's XP (for history logging)
            if reward_xp > 0:
                await self.xp_event_service.create_scan_claim_event(
                    user_id=user.id,
                    scan_id=str(item_secret.id),
                    reward_xp=reward_xp,
                    occurred_at=claimed_at,
                    color=self._get_color_for_rarity(item_secret.rarity),
                )

            from app.db.models.system_events import OutboxEvent
            from app.core.logger import request_id_ctx
            
            outbox_event = OutboxEvent(
                event_type="scan_claimed",
                payload={
                    "event_id": f"scan_{user.id}_{item_secret.id}",
                    "user_id": user.id,
                    "scan_id": str(item_secret.id),
                    "reward_xp": reward_xp,
                    "reward_coins": reward_coins,
                    "reward_fragment_amount": reward_fragment_amount,
                    "reward_fragment_rarity": reward_fragment_rarity,
                    "rarity": rarity_val,
                    "claimed_at": claimed_at.isoformat(),
                    "request_id": request_id_ctx.get(),
                }
            )
            self.session.add(outbox_event)

        item_secret.validation_count += 1
        item_secret.cooldown_until = now_utc + timedelta(hours=24)

        await self.session.commit()
        
        frontend_user = self._build_frontend_user(user)
        frontend_user.xp += reward_xp
        if reward_coins > 0:
            frontend_user.coins += reward_coins
        if reward_fragment_amount > 0:
            frag_attr = f"fragments_{reward_fragment_rarity.lower()}"
            if hasattr(frontend_user, frag_attr):
                setattr(frontend_user, frag_attr, getattr(frontend_user, frag_attr) + reward_fragment_amount)
            
        return ScanClaimResponse(
            status="claimed",
            item=item_response,
            validation=items_service._build_validation_short_response(validation),
            rewards=rewards,
            is_first_blood=is_first_blood,
            user=frontend_user,
            claimed_at=claimed_at,
        )

    async def _get_opened_secret_ids(
        self,
        user_id: int,
        secret_ids: list[int],
    ) -> set[str]:
        opened_ids = await self.validation_service.get_user_item_secret_ids(
            user_id=user_id,
            item_secret_ids=secret_ids,
        )

        return {str(secret_id) for secret_id in opened_ids}

    def _build_map_data(
        self,
        *,
        map_secrets: list[ItemSecret],
        opened_ids: set[str],
        quest_lookup: dict[str, str],
        user_id: int,
        lat: float | None,
        lon: float | None,
        radius_meters: int,
        rarity: Rarity | None,
        category: str | None,
        done: bool | None,
    ) -> dict[str, object]:
        secrets_with_distance = []
        for secret in map_secrets:
            secret_id = self._secret_public_id(secret)
            is_opened = secret_id in opened_ids
            is_masked = self._is_secret_masked(secret, is_opened)

            if not self._matches_map_filters(
                secret,
                is_masked=is_masked,
                rarity=rarity,
                category=category,
            ):
                continue

            if done is not None and is_opened is not done:
                continue

            coords = self._get_public_secret_coords(
                secret,
                user_id=user_id,
                is_opened=is_opened,
            )
            distance_meters = (
                self._distance_meters(
                    lat,
                    lon,
                    coords[0],
                    coords[1],
                )
                if lat is not None and lon is not None
                else None
            )
            if distance_meters is not None and distance_meters > radius_meters:
                continue

            secrets_with_distance.append(
                (secret, is_opened, is_masked, coords, distance_meters)
            )

        if lat is not None and lon is not None:
            secrets_with_distance.sort(
                key=lambda row: (
                    row[4] if row[4] is not None else float("inf"),
                    row[0].title,
                )
            )
        else:
            secrets_with_distance.sort(key=lambda row: row[0].title)

        map_pins = [
            self._build_map_pin(
                secret,
                is_opened=is_opened,
                is_masked=is_masked,
                coords=coords,
            )
            for secret, is_opened, is_masked, coords, _ in secrets_with_distance
        ]
        nearby_points = [
            self._build_nearby_point(
                secret,
                is_opened=is_opened,
                is_masked=is_masked,
                coords=coords,
                distance_meters=distance_meters,
            )
            for secret, is_opened, is_masked, coords, distance_meters
            in secrets_with_distance
        ]
        point_details = {
            self._secret_public_id(secret): self._build_point_detail(
                secret=secret,
                is_opened=is_opened,
                is_masked=is_masked,
                distance_meters=distance_meters,
                quest_lookup=quest_lookup,
            )
            for secret, is_opened, is_masked, _, distance_meters
            in secrets_with_distance
        }

        return {
            "map_pins": map_pins,
            "nearby_points": nearby_points,
            "point_details": point_details,
        }

    @staticmethod
    def _secret_public_id(secret: ItemSecret) -> str:
        return str(secret.id)

    @staticmethod
    def _parse_secret_id(raw_secret_id: str) -> int | None:
        try:
            secret_id = int(raw_secret_id)
        except (TypeError, ValueError):
            return None

        return secret_id if secret_id > 0 else None

    @staticmethod
    def _is_secret_masked(secret: ItemSecret, is_opened: bool) -> bool:
        return secret.hidden and not is_opened

    @staticmethod
    def _matches_map_filters(
        secret: ItemSecret,
        *,
        is_masked: bool,
        rarity: Rarity | None,
        category: str | None,
    ) -> bool:
        if is_masked:
            if rarity is not None:
                return False
            return category is None or category == "Секрет"

        if rarity is not None and secret.rarity != rarity:
            return False

        return category is None or secret.category == category

    @staticmethod
    def _get_public_secret_name(secret: ItemSecret, *, is_masked: bool) -> str:
        return "Скрытый секрет" if is_masked else secret.title

    @staticmethod
    def _get_public_secret_category(secret: ItemSecret, *, is_masked: bool) -> str:
        return "Секрет" if is_masked else secret.category

    @staticmethod
    def _get_public_secret_rarity(secret: ItemSecret, *, is_masked: bool) -> Rarity:
        return Rarity.COMMON if is_masked else secret.rarity

    def _get_public_secret_coords(
        self,
        secret: ItemSecret,
        *,
        user_id: int,
        is_opened: bool,
    ) -> tuple[float, float]:
        lat = float(secret.latitude) if secret.latitude is not None else 0.0
        lon = float(secret.longitude) if secret.longitude is not None else 0.0
        exact_coords = (lat, lon)
        if not self._is_secret_masked(secret, is_opened):
            return exact_coords

        return self._get_stable_nearby_coords(
            exact_coords,
            seed=f"{user_id}:{secret.id}:hidden-map-offset",
            max_distance_meters=50,
        )

    @staticmethod
    def _get_stable_nearby_coords(
        coords: tuple[float, float],
        *,
        seed: str,
        max_distance_meters: int,
    ) -> tuple[float, float]:
        latitude, longitude = coords
        digest = sha256(seed.encode("utf-8")).digest()
        angle_unit = int.from_bytes(digest[:8], "big") / 2**64
        radius_unit = int.from_bytes(digest[8:16], "big") / 2**64
        angle = angle_unit * 2 * pi
        radius = sqrt(radius_unit) * max_distance_meters
        earth_radius = 6378137
        latitude_rad = radians(latitude)

        delta_lat = (radius * sin(angle)) / earth_radius
        delta_lon = (radius * cos(angle)) / (
            earth_radius * max(cos(latitude_rad), 0.000001)
        )

        return (
            latitude + (delta_lat * 180) / pi,
            longitude + (delta_lon * 180) / pi,
        )

    @staticmethod
    def _build_frontend_user(user: User) -> FrontendUserResponse:
        return FrontendUserResponse(
            name=user.display_name or user.first_name,
            username=user.username or user.public_id or f"user{user.id}",
            id=user.public_id or str(user.id),
            rank=user.rank,
            level=user.level,
            level_progress=user.level_progress,
            xp=user.xp,
            next_level_xp=user.next_level_xp or 1000,
            streak_days=user.streak_days,
            season=user.season_label or "",
            coins=getattr(user, "coins", 0),
            active_border_id=getattr(user, "active_border_id", None),
            active_bg_id=getattr(user, "active_bg_id", None),
        )

    def _build_active_event(self, event: Event | None) -> ActiveEventResponse | None:
        if event is None:
            return None

        now = datetime.now(UTC)
        time_left = max(event.ends_at - now, timedelta())

        return ActiveEventResponse(
            rarity=event.rarity,
            title=event.title,
            xp_multiplier=f"×{self._format_decimal(event.xp_multiplier)} XP",
            time_left=self._format_time_left(time_left),
        )

    @staticmethod
    def _build_quest_card(quest: Quest) -> QuestCardResponse:
        return QuestCardResponse(
            id=quest.id,
            name=quest.name,
            step=quest.step_label,
            progress=quest.progress_percent,
            rarity=quest.rarity,
            xp=quest.reward_xp,
        )

    def _build_recent_reward(
        self,
        event: XpEvent,
        map_secrets_by_id: dict[str, ItemSecret],
    ) -> RecentRewardResponse:
        return RecentRewardResponse(
            source=self._format_xp_source(event.source, map_secrets_by_id),
            xp=abs(event.xp),
            multiplier=self._format_multiplier(event.multiplier),
            time=self._format_relative_time(event.occurred_at),
            color=event.color or UIColorToken.CYAN,
        )

    def _build_map_pin(
        self,
        secret: ItemSecret,
        *,
        is_opened: bool,
        is_masked: bool,
        coords: tuple[float, float],
    ) -> MapPinResponse:
        return MapPinResponse(
            id=self._secret_public_id(secret),
            name=self._get_public_secret_name(secret, is_masked=is_masked),
            coords=coords,
            rarity=self._get_public_secret_rarity(secret, is_masked=is_masked),
            big=False if is_masked else secret.is_big,
            hint=True if is_masked else secret.has_hint,
            done=is_opened,
            is_masked=is_masked,
            item_id=secret.item_id if is_opened else None,
        )

    def _build_nearby_point(
        self,
        secret: ItemSecret,
        *,
        is_opened: bool,
        is_masked: bool,
        coords: tuple[float, float],
        distance_meters: float | None,
    ) -> NearbyPointResponse:
        return NearbyPointResponse(
            id=self._secret_public_id(secret),
            name=self._get_public_secret_name(secret, is_masked=is_masked),
            coords=coords,
            category=self._get_public_secret_category(secret, is_masked=is_masked),
            rarity=self._get_public_secret_rarity(secret, is_masked=is_masked),
            distance=self._format_distance(distance_meters, uppercase=False),
            done=is_opened,
            is_masked=is_masked,
            item_id=secret.item_id if is_opened else None,
        )

    def _build_point_detail(
        self,
        *,
        secret: ItemSecret,
        is_opened: bool,
        is_masked: bool,
        distance_meters: float | None,
        quest_lookup: dict[str, str],
    ) -> PointDetailResponse:
        return PointDetailResponse(
            id=self._secret_public_id(secret),
            name=self._get_public_secret_name(secret, is_masked=is_masked),
            category=self._get_public_secret_category(
                secret,
                is_masked=is_masked,
            ).upper(),
            distance=self._format_distance(distance_meters, uppercase=True),
            rarity=self._get_public_secret_rarity(secret, is_masked=is_masked),
            reward=0 if is_masked else secret.reward_xp,
            status="Найдено" if is_opened else "Не найдено",
            quest=(
                "Скрыто"
                if is_masked
                else quest_lookup.get(secret.quest_id or "", "Без квеста")
            ),
            description="" if is_masked else secret.description,
            done=is_opened,
            item_id=secret.item_id if is_opened else None,
        )

    @staticmethod
    def _build_stats(
        *,
        scan_count: int,
        point_count: int,
        quest_count: int,
        achievement_count: int,
    ) -> list[StatCardResponse]:
        return [
            StatCardResponse(
                value=str(scan_count),
                label="СКАНОВ",
                color=UIColorToken.CYAN,
            ),
            StatCardResponse(
                value=str(point_count),
                label="ТОЧЕК",
                color=UIColorToken.VIOLET_HI,
            ),
            StatCardResponse(
                value=str(quest_count),
                label="КВЕСТОВ",
                color=UIColorToken.GOLD,
            ),
            StatCardResponse(
                value=str(achievement_count),
                label="АЧИВОК",
                color=UIColorToken.PINK,
            ),
        ]

    @staticmethod
    def _build_profile_links(
        *,
        user: User,
        achievement_unlocked: int,
        achievement_total: int,
    ) -> list[ProfileLinkResponse]:
        return [
            ProfileLinkResponse(
                icon="bolt",
                title="История XP",
                subtitle=f"{user.xp} за сезон",
                color=UIColorToken.CYAN,
                to="/xp",
            ),
            ProfileLinkResponse(
                icon="trophy",
                title="Достижения",
                subtitle=f"{achievement_unlocked} из {achievement_total}",
                color=UIColorToken.GOLD,
                to="/achievements",
            ),
            ProfileLinkResponse(
                icon="map",
                title="Инвентарь",
                subtitle="Каталог предметов",
                color=UIColorToken.VIOLET_HI,
                to="/inventory",
            ),
        ]

    def _build_xp_history_groups(
        self,
        events: list[XpEvent],
        map_secrets_by_id: dict[str, ItemSecret],
    ) -> list[XpHistoryGroupResponse]:
        grouped: defaultdict[date, list[XpEvent]] = defaultdict(list)
        for event in events:
            grouped[event.occurred_at.astimezone(UTC).date()].append(event)

        groups: list[XpHistoryGroupResponse] = []
        for day in sorted(grouped.keys(), reverse=True):
            day_events = sorted(
                grouped[day],
                key=lambda event: (event.occurred_at, event.id),
                reverse=True,
            )
            groups.append(
                XpHistoryGroupResponse(
                    day=self._format_group_day(day),
                    items=[
                        XpHistoryItemResponse(
                            source=self._format_xp_source(
                                event.source,
                                map_secrets_by_id,
                            ),
                            tag=event.tag or "XP",
                            xp=abs(event.xp),
                            multiplier=self._format_multiplier(event.multiplier),
                            color=event.color or UIColorToken.CYAN,
                            time=event.occurred_at.astimezone(UTC).strftime("%H:%M"),
                        )
                        for event in day_events
                    ],
                )
            )

        return groups

    @staticmethod
    def _get_current_week_bounds() -> tuple[datetime, datetime]:
        today = datetime.now(UTC).date()
        week_start_date = today - timedelta(days=today.weekday())
        week_start = datetime.combine(week_start_date, time.min, tzinfo=UTC)

        return week_start, week_start + timedelta(days=7)

    @staticmethod
    def _build_xp_weekly_summary(
        events: list[XpEvent],
        *,
        week_start: datetime,
    ) -> XpWeekSummaryResponse:
        week_start_date = week_start.astimezone(UTC).date()
        days = [0] * 7

        for event in events:
            event_day = event.occurred_at.astimezone(UTC).date()
            day_index = (event_day - week_start_date).days
            if 0 <= day_index < 7:
                days[day_index] += abs(event.xp)

        return XpWeekSummaryResponse(total=sum(days), days=days)

    @staticmethod
    def _build_achievements(
        states: list[tuple[Achievement, UserAchievement | None]],
    ) -> list[AchievementResponse]:
        items = []
        for achievement, user_achievement in states:
            unlocked = bool(user_achievement and user_achievement.unlocked)
            progress = None if unlocked else (
                user_achievement.progress_percent if user_achievement is not None else 0
            )
            items.append(
                AchievementResponse(
                    icon=achievement.icon,
                    name=achievement.name,
                    rarity=achievement.rarity,
                    unlocked=unlocked,
                    progress=progress,
                )
            )

        return items

    @staticmethod
    def _build_quest_lookup(quests: list[Quest]) -> dict[str, str]:
        return {quest.id: quest.name for quest in quests}

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        normalized = value.normalize()
        if normalized == normalized.to_integral():
            return str(int(normalized))
        return format(normalized, "f").rstrip("0").rstrip(".")

    @staticmethod
    def _format_multiplier(multiplier: Decimal | None) -> str | None:
        if multiplier is None or multiplier in {Decimal("1"), Decimal("1.00")}:
            return None
        return f"×{FrontendDataBusinessService._format_decimal(multiplier)}"

    @staticmethod
    def _format_time_left(time_left: timedelta) -> str:
        total_seconds = int(time_left.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}Д {hours}Ч"
        if hours > 0:
            return f"{hours}Ч {minutes}М"
        return f"{minutes}М"

    @staticmethod
    def _format_relative_time(occurred_at: datetime) -> str:
        now = datetime.now(UTC)
        delta = now - occurred_at.astimezone(UTC)
        minutes = int(delta.total_seconds() // 60)
        hours = int(delta.total_seconds() // 3600)

        if minutes < 60:
            return f"{max(minutes, 0)} мин назад"
        if hours < 24:
            return f"{hours} ч назад"
        return "вчера"

    @staticmethod
    def _format_distance(distance_meters: float | None, *, uppercase: bool) -> str:
        if distance_meters is None:
            return "—"

        suffix = "М" if uppercase else "м"
        return f"{round(distance_meters)} {suffix}"

    @staticmethod
    def _format_group_day(group_day: date) -> str:
        today = datetime.now(UTC).date()
        if group_day == today:
            return "СЕГОДНЯ"
        if group_day == today - timedelta(days=1):
            return "ВЧЕРА"
        return group_day.strftime("%d.%m.%Y")

    @staticmethod
    def _format_xp_source(
        source: str,
        map_secrets_by_id: dict[str, ItemSecret],
    ) -> str:
        if source.startswith("scan:"):
            secret_id = source.removeprefix("scan:")
            secret = map_secrets_by_id.get(secret_id)
            if secret is not None:
                return f"Скан · {secret.title}"

        return source

    @staticmethod
    def _get_color_for_rarity(rarity: Rarity) -> UIColorToken:
        return {
            Rarity.COMMON: UIColorToken.CYAN,
            Rarity.RARE: UIColorToken.CYAN,
            Rarity.EPIC: UIColorToken.VIOLET_HI,
            Rarity.LEGENDARY: UIColorToken.GOLD,
            Rarity.MYTHIC: UIColorToken.PINK,
        }[rarity]

    @staticmethod
    def _distance_meters(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        radius = 6371000
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)
        delta_lat = lat2_rad - lat1_rad
        delta_lon = lon2_rad - lon1_rad

        a = (
            sin(delta_lat / 2) ** 2
            + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        )
        return 2 * radius * asin(sqrt(a))
