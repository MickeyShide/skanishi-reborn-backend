from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.db.models.enums import Rarity, UIColorToken
from app.schemas.common import MapPointsQueryParams
from app.schemas.frontend import ScanClaimRequest
from app.services.business.frontend_data import FrontendDataBusinessService
from app.services.errors import RewardAlreadyClaimedError


def build_map_point(
    point_id: str,
    *,
    latitude: str,
    longitude: str,
    name: str,
    category: str = "AR-сцена",
    rarity: Rarity = Rarity.RARE,
    reward_xp: int = 100,
    quest_id: str | None = None,
):
    return SimpleNamespace(
        id=point_id,
        name=name,
        category=category,
        rarity=rarity,
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        reward_xp=reward_xp,
        description=f"Описание {name}",
        quest_id=quest_id,
        is_big=False,
        has_hint=False,
    )


class FrontendDataBusinessServiceTests(IsolatedAsyncioTestCase):
    async def test_get_map_points_sorts_nearby_and_filters_done(self) -> None:
        user = SimpleNamespace(id=77)
        service = object.__new__(FrontendDataBusinessService)
        service.get_current_user = AsyncMock(return_value=user)
        service.quest_service = MagicMock()
        service.quest_service.get_active_quests = AsyncMock(
            return_value=[SimpleNamespace(id="quest-1", name="Тени Старого города")]
        )
        service.map_point_service = MagicMock()
        service.map_point_service.get_active_points = AsyncMock(
            return_value=[
                build_map_point(
                    "far-point",
                    latitude="55.760000",
                    longitude="37.630000",
                    name="Дальняя точка",
                    quest_id="quest-1",
                ),
                build_map_point(
                    "near-point",
                    latitude="55.751620",
                    longitude="37.618660",
                    name="Ближняя точка",
                    quest_id="quest-1",
                ),
            ]
        )
        service.xp_event_service = MagicMock()
        service.xp_event_service.build_scan_source.side_effect = (
            lambda point_id: f"scan:{point_id}"
        )
        service.xp_event_service.get_user_claimed_scan_sources = AsyncMock(
            return_value={"scan:far-point"}
        )

        result = await FrontendDataBusinessService.get_map_points(
            service,
            user,
            MapPointsQueryParams(
                lat=55.751244,
                lon=37.618423,
                radius_meters=5000,
                done=False,
            ),
        )

        self.assertEqual([point.id for point in result.nearby_points], ["near-point"])
        self.assertEqual(result.nearby_points[0].distance, "44 м")
        self.assertEqual(result.point_details["near-point"].status, "Не пройдено")

    async def test_claim_scan_reward_creates_event_and_returns_updated_user(
        self,
    ) -> None:
        service = object.__new__(FrontendDataBusinessService)
        user = SimpleNamespace(
            id=77,
            first_name="Нэйт",
            display_name=None,
            username="nate_void",
            public_id="0xN4TE",
            rank=142,
            level=14,
            level_progress=70,
            xp=7090,
            next_level_xp=10000,
            streak_days=6,
            season_label="СЕЗОН 2 · ПУЛЬС ГОРОДА",
        )
        updated_user = SimpleNamespace(
            id=77,
            first_name="Нэйт",
            display_name=None,
            username="nate_void",
            public_id="0xN4TE",
            rank=142,
            level=14,
            level_progress=70,
            xp=7090,
            next_level_xp=10000,
            streak_days=6,
            season_label="СЕЗОН 2 · ПУЛЬС ГОРОДА",
        )
        map_point = build_map_point(
            "roof-beacon",
            latitude="55.751620",
            longitude="37.618660",
            name="Маяк на крыше",
            rarity=Rarity.EPIC,
            reward_xp=250,
        )

        service.get_current_user = AsyncMock(return_value=user)
        service.map_point_service = MagicMock()
        service.map_point_service.get_active_point_by_id = AsyncMock(
            return_value=map_point
        )
        service.xp_event_service = MagicMock()
        service.xp_event_service.build_scan_source.return_value = "scan:roof-beacon"
        service.xp_event_service.get_user_event_by_source = AsyncMock(return_value=None)
        service.xp_event_service.create_scan_claim_event = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.apply_scan_reward = AsyncMock(return_value=updated_user)
        service.user_service.apply_scan_reward = AsyncMock(return_value=updated_user)

        result = await FrontendDataBusinessService.claim_scan_reward(
            service,
            user,
            ScanClaimRequest(scan_id="roof-beacon"),
        )

        service.user_service.apply_scan_reward.assert_awaited_once_with(
            user,
            reward_xp=250,
        )
        self.assertEqual(result.status, "claimed")
        self.assertEqual(result.xp, 250)
        self.assertEqual(result.user.id, "0xN4TE")
        self.assertIs(service.user, updated_user)

    async def test_claim_scan_reward_rejects_duplicate(self) -> None:
        user = SimpleNamespace(id=77)
        service = object.__new__(FrontendDataBusinessService)
        service.get_current_user = AsyncMock(return_value=user)
        service.map_point_service = MagicMock()
        service.map_point_service.get_active_point_by_id = AsyncMock(
            return_value=build_map_point(
                "roof-beacon",
                latitude="55.751620",
                longitude="37.618660",
                name="Маяк на крыше",
            )
        )
        service.xp_event_service = MagicMock()
        service.xp_event_service.build_scan_source.return_value = "scan:roof-beacon"
        service.xp_event_service.get_user_event_by_source = AsyncMock(
            return_value=SimpleNamespace(
                id=1,
                occurred_at=datetime(2026, 7, 5, tzinfo=UTC),
                color=UIColorToken.CYAN,
            )
        )

        with self.assertRaises(RewardAlreadyClaimedError):
            await FrontendDataBusinessService.claim_scan_reward(
                service,
                user,
                ScanClaimRequest(scan_id="roof-beacon"),
            )
