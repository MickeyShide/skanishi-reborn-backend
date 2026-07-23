from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import Rarity, UIColorToken


class FrontendUserResponse(BaseModel):
    """Профиль пользователя для текущего frontend bundle."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(default="", min_length=0, max_length=160)
    display_name: str | None = None
    username: str = Field(min_length=1, max_length=64)
    id: str = Field(min_length=1, max_length=64)
    rank: int | None = Field(default=None, ge=1)
    level: int = Field(ge=1)
    level_progress: int = Field(alias="levelProgress", ge=0, le=100)
    xp: int = Field(ge=0)
    next_level_xp: int = Field(alias="nextLevelXp", ge=0)
    streak_days: int = Field(alias="streakDays", ge=0)
    season: str = Field(default="")
    season_label: str | None = None
    coins: int = Field(default=0, ge=0)
    active_border_id: int | None = Field(default=None, alias="activeBorderId")
    active_bg_id: int | None = Field(default=None, alias="activeBgId")
    fragments_common: int = Field(default=0)
    fragments_rare: int = Field(default=0)
    fragments_epic: int = Field(default=0)
    fragments_legendary: int = Field(default=0)
    fragments_mythic: int = Field(default=0)


class ActiveEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rarity: Rarity
    title: str = Field(min_length=1, max_length=180)
    xp_multiplier: str = Field(alias="xpMultiplier", min_length=1, max_length=32)
    time_left: str = Field(alias="timeLeft", min_length=1, max_length=32)


class QuestCardResponse(BaseModel):
    id: str = Field(default="", max_length=96)
    name: str = Field(default="", max_length=160)
    step: str = Field(default="", max_length=80)
    progress: int = Field(default=0, ge=0, le=100)
    rarity: Rarity = Rarity.COMMON
    xp: int = Field(default=0, ge=0)
    title: str | None = None
    description: str | None = None
    reward_xp: int | None = None
    reward_item_id: int | None = None
    target_count: int | None = None
    current_progress: int | None = None
    is_completed: bool | None = None
    reward_claimed: bool | None = None


class RecentRewardResponse(BaseModel):
    source: str = Field(min_length=1, max_length=180)
    xp: int = Field(ge=0)
    multiplier: str | None = Field(default=None, max_length=32)
    time: str = Field(min_length=1, max_length=32)
    color: UIColorToken


class MapPinResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    coords: tuple[float, float]
    rarity: Rarity
    big: bool = False
    hint: bool = False
    done: bool = False
    is_masked: bool = False
    item_id: int | None = Field(default=None, alias="itemId")


class NearbyPointResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    coords: tuple[float, float]
    category: str = Field(min_length=1, max_length=64)
    rarity: Rarity
    distance: str = Field(min_length=1, max_length=32)
    done: bool
    is_masked: bool = False
    item_id: int | None = Field(default=None, alias="itemId")


class PointDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=64)
    distance: str = Field(min_length=1, max_length=32)
    rarity: Rarity
    reward: int = Field(ge=0)
    status: str = Field(min_length=1, max_length=64)
    quest: str = Field(min_length=1, max_length=160)
    description: str = Field(default="")
    done: bool = False
    item_id: int | None = Field(default=None, alias="itemId")


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


class XpWeekSummaryResponse(BaseModel):
    total: int
    days: list[int] = Field(min_length=7, max_length=7)


class AchievementResponse(BaseModel):
    id: str = Field(default="unknown", max_length=96)
    icon: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    rarity: Rarity
    unlocked: bool
    progress: int | None = Field(default=None, ge=0, le=100)


class AchievementSummaryResponse(BaseModel):
    unlocked: int = Field(ge=0)
    total: int = Field(ge=0)


class LatestAchievementResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=128)
    description: str
    xp: int
    rarity: Rarity
    unlocked_at: datetime = Field(alias="unlockedAt")


class AchievementsResponse(BaseModel):
    items: list[AchievementResponse]
    summary: AchievementSummaryResponse = Field(
        default_factory=lambda: AchievementSummaryResponse(unlocked=0, total=0)
    )
    total_earned: int | None = None


class XpHistoryResponse(BaseModel):
    groups: list[XpHistoryGroupResponse]
    weekly: XpWeekSummaryResponse = Field(
        default_factory=lambda: XpWeekSummaryResponse(total=0, days=[0] * 7)
    )


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
    xp_weekly: XpWeekSummaryResponse = Field(
        default_factory=lambda: XpWeekSummaryResponse(total=0, days=[0] * 7),
        alias="xpWeekly",
    )
    achievements: list[AchievementResponse]
    achievement_summary: AchievementSummaryResponse = Field(alias="achievementSummary")
    latest_achievement: LatestAchievementResponse | None = Field(default=None, alias="latestAchievement")


class BaseItemResponse(BaseModel):
    id: int
    name: str = ""
    description: str = ""
    type: str = ""
    rarity: str = ""
    image_url: str | None = None
    required_fragments: int = 0


class AppStateResponse(BaseModel):
    season_id: str = ""
    is_season_active: bool = False
    unread_notifications_count: int = 0


class ProfileResponse(BaseModel):
    user: FrontendUserResponse
    total_collections: int = 0
    completed_collections: int = 0


class XpHistoryRowResponse(BaseModel):
    id: str
    source: str
    tag: str
    xp: int
    occurred_at: datetime


from app.schemas.item import ItemFullResponse
from app.schemas.validation import ValidationShortResponse

class RewardItem(BaseModel):
    type: Literal["xp", "coin", "fragment"]
    amount: int
    name: str = Field(min_length=1, max_length=64)
    rarity: Rarity | str | None = None

class ScanClaimRequest(BaseModel):
    token: str | None = Field(default=None, max_length=512)
    event_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    item_tags: list[str] = Field(default_factory=list)


class ScanClaimResponse(BaseModel):
    status: Literal["claimed", "already_collected"] = "claimed"
    item: ItemFullResponse | None = None
    validation: ValidationShortResponse | None = None
    rewards: list[RewardItem] = Field(default_factory=list)
    is_first_blood: bool = False
    user: FrontendUserResponse
    claimed_at: datetime | None = Field(default=None, alias="claimedAt")
    scanned_items: list[object] = Field(default_factory=list)
