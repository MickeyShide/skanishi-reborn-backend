from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import Rarity, UIColorToken


class FrontendUserResponse(BaseModel):
    """Профиль пользователя для текущего frontend bundle."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=160)
    username: str = Field(min_length=1, max_length=64)
    id: str = Field(min_length=1, max_length=64)
    rank: int | None = Field(default=None, ge=1)
    level: int = Field(ge=1)
    level_progress: int = Field(alias="levelProgress", ge=0, le=100)
    xp: int = Field(ge=0)
    next_level_xp: int = Field(alias="nextLevelXp", ge=0)
    streak_days: int = Field(alias="streakDays", ge=0)
    season: str = Field(default="")


class ActiveEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rarity: Rarity
    title: str = Field(min_length=1, max_length=180)
    xp_multiplier: str = Field(alias="xpMultiplier", min_length=1, max_length=32)
    time_left: str = Field(alias="timeLeft", min_length=1, max_length=32)


class QuestCardResponse(BaseModel):
    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    step: str = Field(min_length=1, max_length=80)
    progress: int = Field(ge=0, le=100)
    rarity: Rarity
    xp: int = Field(ge=0)


class RecentRewardResponse(BaseModel):
    source: str = Field(min_length=1, max_length=180)
    xp: int = Field(ge=0)
    multiplier: str | None = Field(default=None, max_length=32)
    time: str = Field(min_length=1, max_length=32)
    color: UIColorToken


class MapPinResponse(BaseModel):
    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    coords: tuple[float, float]
    rarity: Rarity
    big: bool = False
    hint: bool = False


class NearbyPointResponse(BaseModel):
    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    coords: tuple[float, float]
    category: str = Field(min_length=1, max_length=64)
    rarity: Rarity
    distance: str = Field(min_length=1, max_length=32)
    done: bool


class PointDetailResponse(BaseModel):
    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=64)
    distance: str = Field(min_length=1, max_length=32)
    rarity: Rarity
    reward: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=64)
    quest: str = Field(min_length=1, max_length=160)
    description: str = Field(default="")


class StatCardResponse(BaseModel):
    value: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=32)
    color: UIColorToken


class ProfileLinkResponse(BaseModel):
    icon: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=64)
    subtitle: str = Field(min_length=1, max_length=64)
    color: UIColorToken
    to: str = Field(min_length=1, max_length=64)


class XpHistoryItemResponse(BaseModel):
    source: str = Field(min_length=1, max_length=180)
    tag: str = Field(min_length=1, max_length=32)
    xp: int
    multiplier: str | None = Field(default=None, max_length=32)
    color: UIColorToken
    time: str = Field(min_length=1, max_length=16)


class XpHistoryGroupResponse(BaseModel):
    day: str = Field(min_length=1, max_length=32)
    items: list[XpHistoryItemResponse]


class AchievementResponse(BaseModel):
    icon: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    rarity: Rarity
    unlocked: bool
    progress: int | None = Field(default=None, ge=0, le=100)


class AchievementSummaryResponse(BaseModel):
    unlocked: int = Field(ge=0)
    total: int = Field(ge=0)


class AchievementsResponse(BaseModel):
    items: list[AchievementResponse]
    summary: AchievementSummaryResponse


class XpHistoryResponse(BaseModel):
    groups: list[XpHistoryGroupResponse]


class QuestsResponse(BaseModel):
    items: list[QuestCardResponse]


class MapPointsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    map_pins: list[MapPinResponse] = Field(alias="mapPins")
    nearby_points: list[NearbyPointResponse] = Field(alias="nearbyPoints")
    point_details: dict[str, PointDetailResponse] = Field(alias="pointDetails")


class FrontendAppStateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user: FrontendUserResponse
    active_event: ActiveEventResponse | None = Field(default=None, alias="activeEvent")
    quests: list[QuestCardResponse]
    recent_rewards: list[RecentRewardResponse] = Field(alias="recentRewards")
    map_pins: list[MapPinResponse] = Field(alias="mapPins")
    nearby_points: list[NearbyPointResponse] = Field(alias="nearbyPoints")
    point_details: dict[str, PointDetailResponse] = Field(alias="pointDetails")
    stats: list[StatCardResponse]
    profile_links: list[ProfileLinkResponse] = Field(alias="profileLinks")
    xp_history_groups: list[XpHistoryGroupResponse] = Field(alias="xpHistoryGroups")
    achievements: list[AchievementResponse]


class ScanClaimRequest(BaseModel):
    scan_id: str = Field(
        min_length=1,
        max_length=96,
        description="Идентификатор scan/map point",
    )


class ScanClaimResponse(BaseModel):
    status: Literal["claimed"] = "claimed"
    xp: int = Field(ge=0)
    user: FrontendUserResponse
    claimed_at: datetime | None = None
