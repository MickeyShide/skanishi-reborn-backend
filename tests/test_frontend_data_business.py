from datetime import UTC, datetime, timedelta
from decimal import Decimal
from decimal import Decimal
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models.enums import Rarity, UIColorToken
from app.schemas.common import MapPointsQueryParams, XpHistoryQueryParams
from app.schemas.frontend import ScanClaimRequest
from app.schemas.item import ItemFullResponse
from app.schemas.validation import ValidationShortResponse
from app.services.business.frontend_data import FrontendDataBusinessService
from app.services.errors import RewardAlreadyClaimedError


def build_map_secret(
    secret_id: int,
    *,
    latitude: str,
    longitude: str,
    name: str,
    category: str = "AR-сцена",
    rarity: Rarity = Rarity.RARE,
    reward_xp: int = 100,
    quest_id: str | None = None,
    hidden: bool = False,
):
    return SimpleNamespace(
        id=secret_id,
        item_id=secret_id + 100,
        title=name,
        category=category,
        rarity=rarity,
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        reward_xp=reward_xp,
        description=f"Описание {name}",
        quest_id=quest_id,
        is_big=False,
        has_hint=False,
        hidden=hidden,
    )


def build_mock_user(user_id: int = 77) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        first_name="Нэйт",
        display_name=None,
        username="nate_void",
        public_id=f"0xN4TE{user_id}",
        rank=142,
        level=14,
        level_progress=70,
        xp=7090,
        next_level_xp=10000,
        streak_days=6,
        season_label="СЕЗОН 2 · ПУЛЬС ГОРОДА",
    )


class FrontendDataBusinessServiceTests(IsolatedAsyncioTestCase):
    async def test_get_map_points_sorts_nearby_and_filters_done(self) -> None:
        user = build_mock_user()
        service = object.__new__(FrontendDataBusinessService)
        service.get_current_user = AsyncMock(return_value=user)
        service.quest_service = MagicMock()
        service.quest_service.get_active_quests = AsyncMock(
            return_value=[SimpleNamespace(id="quest-1", name="Тени Старого города")]
        )
        service.item_secret_service = MagicMock()
        service.item_secret_service.get_active_map_secrets = AsyncMock(
            return_value=[
                build_map_secret(
                    1,
                    latitude="55.760000",
                    longitude="37.630000",
                    name="Дальняя точка",
                    quest_id="quest-1",
                ),
                build_map_secret(
                    2,
                    latitude="55.751620",
                    longitude="37.618660",
                    name="Ближняя точка",
                    quest_id="quest-1",
                ),
            ]
        )
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_secret_ids = AsyncMock(
            return_value={1}
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

        self.assertEqual([point.id for point in result.nearby_points], ["2"])
        self.assertEqual(result.nearby_points[0].distance, "44 м")
        self.assertEqual(result.point_details["2"].status, "Не найдено")

    async def test_hidden_unopened_secret_only_exposes_nearby_coords(self) -> None:
        user = build_mock_user()
        service = object.__new__(FrontendDataBusinessService)
        service.quest_service = MagicMock()
        service.quest_service.get_active_quests = AsyncMock(return_value=[])
        service.item_secret_service = MagicMock()
        service.item_secret_service.get_active_map_secrets = AsyncMock(
            return_value=[
                build_map_secret(
                    3,
                    latitude="55.751620",
                    longitude="37.618660",
                    name="Секретное имя",
                    category="AR-сцена",
                    rarity=Rarity.MYTHIC,
                    reward_xp=500,
                    hidden=True,
                )
            ]
        )
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_secret_ids = AsyncMock(
            return_value=set()
        )

        result = await FrontendDataBusinessService.get_map_points(
            service,
            user,
            MapPointsQueryParams(),
        )

        pin = result.map_pins[0]
        detail = result.point_details["3"]
        distance = FrontendDataBusinessService._distance_meters(
            55.751620,
            37.618660,
            pin.coords[0],
            pin.coords[1],
        )

        self.assertLessEqual(distance, 100)
        self.assertNotEqual(pin.coords, (55.751620, 37.618660))
        self.assertEqual(pin.name, "Скрытый секрет")
        self.assertEqual(pin.rarity, Rarity.COMMON)
        self.assertEqual(detail.description, "")
        self.assertEqual(detail.reward, 0)
        self.assertIsNone(detail.item_id)

    async def test_get_xp_history_returns_weekly_summary_for_filter(self) -> None:
        user = build_mock_user()
        service = object.__new__(FrontendDataBusinessService)
        week_start, week_end = FrontendDataBusinessService._get_current_week_bounds()
        history_event = SimpleNamespace(
            id=1,
            source="bonus:daily",
            tag="BONUS",
            xp=50,
            multiplier=None,
            color=UIColorToken.GOLD,
            occurred_at=week_start + timedelta(days=1, hours=10),
        )
        penalty_event = SimpleNamespace(
            id=2,
            source="bonus:refund",
            tag="BONUS",
            xp=-20,
            multiplier=None,
            color=UIColorToken.PINK,
            occurred_at=week_start + timedelta(days=1, hours=11),
        )
        service.xp_event_service = MagicMock()
        service.xp_event_service.get_user_history = AsyncMock(
            return_value=[history_event]
        )
        service.xp_event_service.get_user_events_between = AsyncMock(
            return_value=[history_event, penalty_event]
        )
        service.item_secret_service = MagicMock()
        service.item_secret_service.get_active_map_secrets = AsyncMock(
            return_value=[]
        )

        result = await FrontendDataBusinessService.get_xp_history(
            service,
            user,
            XpHistoryQueryParams(tag="BONUS"),
        )

        self.assertEqual(result.weekly.days, [0, 70, 0, 0, 0, 0, 0])
        self.assertEqual(result.weekly.total, 70)
        service.xp_event_service.get_user_history.assert_awaited_once_with(
            user_id=77,
            limit=50,
            offset=0,
            tag="BONUS",
        )
        service.xp_event_service.get_user_events_between.assert_awaited_once_with(
            user_id=77,
            occurred_at_from=week_start,
            occurred_at_to=week_end,
            tag="BONUS",
        )

    async def test_claim_scan_reward_creates_event_and_returns_updated_user(
        self,
    ) -> None:
        service = object.__new__(FrontendDataBusinessService)
        user = build_mock_user()
        updated_user = build_mock_user()
        item_secret = build_map_secret(
            1,
            latitude="55.751620",
            longitude="37.618660",
            name="Маяк на крыше",
            rarity=Rarity.EPIC,
            reward_xp=250,
        )

        service.get_current_user = AsyncMock(return_value=user)
        service.item_secret_service = MagicMock()
        service.item_secret_service.get_active_by_secret_hash = AsyncMock(
            return_value=item_secret
        )
        service.xp_event_service = MagicMock()
        service.xp_event_service.build_scan_source.return_value = "scan:1"
        service.xp_event_service.get_user_event_by_source = AsyncMock(return_value=None)
        service.xp_event_service.create_scan_claim_event = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.apply_scan_reward = AsyncMock(return_value=updated_user)
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_validation = AsyncMock(return_value=None)
        service.validation_service.create_validation = AsyncMock(return_value=SimpleNamespace())
        
        # We must mock session so ItemsBusinessService can be instantiated
        service.session = MagicMock()
        service.session.commit = AsyncMock()
        
        with (
            patch("app.core.redis_client.redis_client") as mock_redis,
            patch("app.core.redis_client.redis_fail_open", new_callable=AsyncMock),
            patch("app.services.business.items.ItemsBusinessService") as MockItemsBusinessService,
        ):
            mock_pipe = AsyncMock()
            mock_pipe.execute.return_value = [1]
            mock_redis.pipeline = MagicMock(return_value=mock_pipe)
            mock_pipe.__aenter__.return_value = mock_pipe
            
            # Setup ItemsBusinessService Mock
            mock_items_instance = MagicMock()
            MockItemsBusinessService.return_value = mock_items_instance
            mock_items_instance._decode_item_secret_token = MagicMock(return_value=SimpleNamespace(secret="raw"))
            
            mock_item_service = MagicMock()
            mock_item_service.get_active_catalog_item = AsyncMock(return_value=SimpleNamespace())
            mock_item_service.get_active_item_for_update = AsyncMock(return_value=SimpleNamespace(id=1, validation_count=0))
            mock_item_service.increment_validation_count = AsyncMock()
            mock_items_instance.item_service = mock_item_service
            
            mock_items_instance._build_full_item_response = MagicMock(return_value=ItemFullResponse.model_construct())
            mock_items_instance._build_validation_short_response = MagicMock(return_value=ValidationShortResponse.model_construct())
            
            result = await FrontendDataBusinessService.claim_scan_reward(
                service,
                user,
                ScanClaimRequest(token="1"),
            )

        self.assertEqual(result.status, "claimed")
        self.assertEqual(result.xp, 250)
        self.assertEqual(result.user.id, "0xN4TE77")
        service.xp_event_service.create_scan_claim_event.assert_awaited_once_with(
            user_id=77,
            scan_id="1",
            reward_xp=250,
            occurred_at=result.claimed_at,
            color=UIColorToken.VIOLET_HI,
        )

    async def test_claim_scan_reward_rejects_duplicate(self) -> None:
        user = build_mock_user()
        service = object.__new__(FrontendDataBusinessService)
        service.get_current_user = AsyncMock(return_value=user)
        service.item_secret_service = MagicMock()
        service.item_secret_service.get_active_by_secret_hash = AsyncMock(
            return_value=build_map_secret(
                1,
                latitude="55.751620",
                longitude="37.618660",
                name="Маяк на крыше",
            )
        )
        service.xp_event_service = MagicMock()
        service.xp_event_service.build_scan_source.return_value = "scan:1"
        service.xp_event_service.get_user_event_by_source = AsyncMock(
            return_value=SimpleNamespace(
                id=1,
                occurred_at=datetime(2026, 7, 5, tzinfo=UTC),
                color=UIColorToken.CYAN,
            )
        )
        service.validation_service = MagicMock()
        service.validation_service.get_user_item_validation = AsyncMock(return_value=SimpleNamespace(created_at=datetime.now(UTC)))
        service.validation_service.create_validation = AsyncMock(return_value=SimpleNamespace())
        
        service.session = MagicMock()
        service.session.commit = AsyncMock()
        with (
            patch("app.core.redis_client.redis_client") as mock_redis,
            patch("app.core.redis_client.redis_fail_open", new_callable=AsyncMock),
            patch("app.services.business.items.ItemsBusinessService") as MockItemsBusinessService,
        ):
            mock_pipe = AsyncMock()
            mock_pipe.execute.return_value = [1]
            mock_redis.pipeline = MagicMock(return_value=mock_pipe)
            mock_pipe.__aenter__.return_value = mock_pipe
            
            # Setup ItemsBusinessService Mock
            mock_items_instance = MagicMock()
            MockItemsBusinessService.return_value = mock_items_instance
            mock_items_instance._decode_item_secret_token = MagicMock(return_value=SimpleNamespace(secret="raw"))
            
            mock_item_service = MagicMock()
            mock_item_service.get_active_catalog_item = AsyncMock(return_value=SimpleNamespace())
            mock_item_service.get_active_item_for_update = AsyncMock(return_value=SimpleNamespace(id=1, validation_count=0))
            mock_item_service.increment_validation_count = AsyncMock()
            mock_items_instance.item_service = mock_item_service
            
            mock_items_instance._build_full_item_response = MagicMock(return_value=ItemFullResponse.model_construct())
            mock_items_instance._build_validation_short_response = MagicMock(return_value=ValidationShortResponse.model_construct())
            
            result = await FrontendDataBusinessService.claim_scan_reward(
                service,
                user,
                ScanClaimRequest(token="1"),
            )
            self.assertEqual(result.status, "already_collected")
