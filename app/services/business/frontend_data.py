from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.achievement import Achievement, UserAchievement
from app.db.models.enums import Rarity, UIColorToken
from app.db.models.event import Event
from app.db.models.map_point import MapPoint
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
)
from app.services.achievement import AchievementService
from app.services.business.base import BusinessService
from app.services.errors import RewardAlreadyClaimedError, ScanNotFoundError
from app.services.event import EventService
from app.services.map_point import MapPointService
from app.services.quest import QuestService
from app.services.user import UserService
from app.services.xp_event import XpEventService


class FrontendDataBusinessService(BusinessService):
    achievement_service: AchievementService
    event_service: EventService
    map_point_service: MapPointService
    quest_service: QuestService
    user_service: UserService
    xp_event_service: XpEventService

    def __init__(
        self,
        session: AsyncSession | None = None,
    ) -> None:
        super().__init__(session=session)

    async def get_app_state(self, current_user: User) -> FrontendAppStateResponse:
        user = current_user
        quests = await self.quest_service.get_active_quests()
        active_event = await self.event_service.get_active_event()
        map_points = await self.map_point_service.get_active_points()
        map_points_by_id = {point.id: point for point in map_points}
        claimed_ids = await self._get_claimed_scan_ids(user.id, list(map_points_by_id))
        recent_events = await self.xp_event_service.get_recent_user_events(
            user_id=user.id,
            limit=3,
        )
        xp_history_events = await self.xp_event_service.get_user_history(
            user_id=user.id,
            limit=50,
            offset=0,
        )
        achievement_states = await self.achievement_service.get_user_achievement_states(
            user_id=user.id
        )
        scan_count = await self.xp_event_service.count_user_events_by_tag(
            user_id=user.id,
            tag="SCAN",
        )

        map_data = self._build_map_data(
            map_points=map_points,
            claimed_ids=claimed_ids,
            quest_lookup=self._build_quest_lookup(quests),
            lat=None,
            lon=None,
            radius_meters=1000,
            done=None,
        )
        achievements = self._build_achievements(achievement_states)
        unlocked_count = sum(1 for achievement in achievements if achievement.unlocked)
        stats = self._build_stats(
            scan_count=scan_count,
            point_count=len(map_points),
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
                self._build_recent_reward(event, map_points_by_id)
                for event in recent_events
            ],
            map_pins=map_data["map_pins"],
            nearby_points=map_data["nearby_points"],
            point_details=map_data["point_details"],
            stats=stats,
            profile_links=profile_links,
            xp_history_groups=self._build_xp_history_groups(
                xp_history_events,
                map_points_by_id,
            ),
            achievements=achievements,
        )

    async def get_map_points(self, current_user: User, params: MapPointsQueryParams) -> MapPointsResponse:
        user = current_user
        quests = await self.quest_service.get_active_quests()
        map_points = await self.map_point_service.get_active_points(
            rarity=params.rarity,
            category=params.category,
        )
        claimed_ids = await self._get_claimed_scan_ids(
            user.id,
            [point.id for point in map_points],
        )
        map_data = self._build_map_data(
            map_points=map_points,
            claimed_ids=claimed_ids,
            quest_lookup=self._build_quest_lookup(quests),
            lat=params.lat,
            lon=params.lon,
            radius_meters=params.radius_meters,
            done=params.done,
        )

        return MapPointsResponse(**map_data)

    async def get_quests(self, current_user: User) -> QuestsResponse:
        quests = await self.quest_service.get_active_quests()

        return QuestsResponse(
            items=[self._build_quest_card(quest) for quest in quests]
        )

    async def get_xp_history(self, current_user: User, params: XpHistoryQueryParams) -> XpHistoryResponse:
        user = current_user
        events = await self.xp_event_service.get_user_history(
            user_id=user.id,
            limit=params.limit,
            offset=params.offset,
            tag=params.tag,
        )
        map_points = await self.map_point_service.get_active_points()
        map_points_by_id = {point.id: point for point in map_points}

        return XpHistoryResponse(
            groups=self._build_xp_history_groups(events, map_points_by_id)
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

    async def claim_scan_reward(self, current_user: User, dto: ScanClaimRequest) -> ScanClaimResponse:
        user = current_user
        map_point = await self.map_point_service.get_active_point_by_id(dto.scan_id)
        if map_point is None:
            raise ScanNotFoundError()

        source = self.xp_event_service.build_scan_source(dto.scan_id)
        existing_event = await self.xp_event_service.get_user_event_by_source(
            user_id=user.id,
            source=source,
        )
        if existing_event is not None:
            raise RewardAlreadyClaimedError()

        claimed_at = datetime.now(UTC)
        updated_user = await self.user_service.apply_scan_reward(
            user,
            reward_xp=map_point.reward_xp,
        )
        await self.xp_event_service.create_scan_claim_event(
            user_id=user.id,
            scan_id=dto.scan_id,
            reward_xp=map_point.reward_xp,
            occurred_at=claimed_at,
            color=self._get_color_for_rarity(map_point.rarity),
        )
        self.user = updated_user

        return ScanClaimResponse(
            xp=map_point.reward_xp,
            user=self._build_frontend_user(updated_user),
            claimed_at=claimed_at,
        )

    async def _get_claimed_scan_ids(
        self,
        user_id: int,
        point_ids: list[str],
    ) -> set[str]:
        sources = [
            self.xp_event_service.build_scan_source(point_id)
            for point_id in point_ids
        ]
        claimed_sources = await self.xp_event_service.get_user_claimed_scan_sources(
            user_id=user_id,
            sources=sources,
        )

        return {
            source.removeprefix("scan:")
            for source in claimed_sources
            if source.startswith("scan:")
        }

    def _build_map_data(
        self,
        *,
        map_points: list[MapPoint],
        claimed_ids: set[str],
        quest_lookup: dict[str, str],
        lat: float | None,
        lon: float | None,
        radius_meters: int,
        done: bool | None,
    ) -> dict[str, object]:
        points_with_distance = []
        for point in map_points:
            is_done = point.id in claimed_ids
            if done is not None and is_done is not done:
                continue

            distance_meters = (
                self._distance_meters(
                    lat,
                    lon,
                    float(point.latitude),
                    float(point.longitude),
                )
                if lat is not None and lon is not None
                else None
            )
            if distance_meters is not None and distance_meters > radius_meters:
                continue

            points_with_distance.append((point, is_done, distance_meters))

        if lat is not None and lon is not None:
            points_with_distance.sort(
                key=lambda row: (
                    row[2] if row[2] is not None else float("inf"),
                    row[0].name,
                )
            )
        else:
            points_with_distance.sort(key=lambda row: row[0].name)

        map_pins = [self._build_map_pin(point) for point, _, _ in points_with_distance]
        nearby_points = [
            self._build_nearby_point(point, is_done, distance_meters)
            for point, is_done, distance_meters in points_with_distance
        ]
        point_details = {
            point.id: self._build_point_detail(
                point=point,
                is_done=is_done,
                distance_meters=distance_meters,
                quest_lookup=quest_lookup,
            )
            for point, is_done, distance_meters in points_with_distance
        }

        return {
            "map_pins": map_pins,
            "nearby_points": nearby_points,
            "point_details": point_details,
        }

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
            next_level_xp=user.next_level_xp,
            streak_days=user.streak_days,
            season=user.season_label or "",
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
        map_points_by_id: dict[str, MapPoint],
    ) -> RecentRewardResponse:
        return RecentRewardResponse(
            source=self._format_xp_source(event.source, map_points_by_id),
            xp=abs(event.xp),
            multiplier=self._format_multiplier(event.multiplier),
            time=self._format_relative_time(event.occurred_at),
            color=event.color or UIColorToken.CYAN,
        )

    @staticmethod
    def _build_map_pin(point: MapPoint) -> MapPinResponse:
        return MapPinResponse(
            id=point.id,
            name=point.name,
            coords=(float(point.latitude), float(point.longitude)),
            rarity=point.rarity,
            big=point.is_big,
            hint=point.has_hint,
        )

    def _build_nearby_point(
        self,
        point: MapPoint,
        is_done: bool,
        distance_meters: float | None,
    ) -> NearbyPointResponse:
        return NearbyPointResponse(
            id=point.id,
            name=point.name,
            coords=(float(point.latitude), float(point.longitude)),
            category=point.category,
            rarity=point.rarity,
            distance=self._format_distance(distance_meters, uppercase=False),
            done=is_done,
        )

    def _build_point_detail(
        self,
        *,
        point: MapPoint,
        is_done: bool,
        distance_meters: float | None,
        quest_lookup: dict[str, str],
    ) -> PointDetailResponse:
        return PointDetailResponse(
            id=point.id,
            name=point.name,
            category=point.category.upper(),
            distance=self._format_distance(distance_meters, uppercase=True),
            rarity=point.rarity,
            reward=point.reward_xp,
            status="Пройдено" if is_done else "Не пройдено",
            quest=quest_lookup.get(point.quest_id or "", "Без квеста"),
            description=point.description,
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
                icon="gem",
                title="Инвентарь",
                subtitle="Каталог предметов",
                color=UIColorToken.VIOLET_HI,
                to="/profile",
            ),
        ]

    def _build_xp_history_groups(
        self,
        events: list[XpEvent],
        map_points_by_id: dict[str, MapPoint],
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
                                map_points_by_id,
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
        map_points_by_id: dict[str, MapPoint],
    ) -> str:
        if source.startswith("scan:"):
            point_id = source.removeprefix("scan:")
            point = map_points_by_id.get(point_id)
            if point is not None:
                return f"Скан · {point.name}"

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
