from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1 import achievement as achievement_api
from app.api.v1 import app_state as app_state_api
from app.api.v1 import map as map_api
from app.api.v1 import quest as quest_api
from app.api.v1 import scan as scan_api
from app.api.v1 import xp as xp_api
from app.db.models.enums import Rarity, UIColorToken
from app.db.models.user import UserRole
from app.main import app
from app.schemas.frontend import (
    AchievementResponse,
    AchievementsResponse,
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
    ScanClaimResponse,
    StatCardResponse,
    XpHistoryGroupResponse,
    XpHistoryItemResponse,
    XpHistoryResponse,
)
from app.schemas.user import UserMe
from app.services.business.frontend_data import FrontendDataBusinessService
from app.services.errors import RewardAlreadyClaimedError, ScanNotFoundError
from app.services.token import TokenService


def build_access_token() -> str:
    user = UserMe(
        id=1,
        tg_id=777,
        first_name="Mickey",
        last_name="Shide",
        photo_url=None,
        is_private=True,
        username="mickey",
        is_premium=False,
        role=UserRole.USER,
    )
    return TokenService().create_access_token(user)


def build_frontend_user() -> FrontendUserResponse:
    return FrontendUserResponse(
        name="Нэйт",
        username="nate_void",
        id="0xN4TE",
        rank=142,
        level=14,
        levelProgress=68,
        xp=6840,
        nextLevelXp=10000,
        streakDays=6,
        season="СЕЗОН 2 · ПУЛЬС ГОРОДА",
    )


def build_map_points_response() -> MapPointsResponse:
    return MapPointsResponse(
        mapPins=[
            MapPinResponse(
                id="roof-beacon",
                name="Маяк на крыше",
                coords=(55.75162, 37.61866),
                rarity=Rarity.EPIC,
                big=True,
            )
        ],
        nearbyPoints=[
            NearbyPointResponse(
                id="roof-beacon",
                name="Маяк на крыше",
                coords=(55.75162, 37.61866),
                category="AR-сцена",
                rarity=Rarity.EPIC,
                distance="120 м",
                done=False,
            )
        ],
        pointDetails={
            "roof-beacon": PointDetailResponse(
                id="roof-beacon",
                name="Маяк на крыше",
                category="AR-СЦЕНА",
                distance="120 М",
                rarity=Rarity.EPIC,
                reward=180,
                status="Не пройдено",
                quest="Тени Старого города",
                description="Описание точки",
            )
        },
    )


def build_app_state_response() -> FrontendAppStateResponse:
    return FrontendAppStateResponse(
        user=build_frontend_user(),
        activeEvent=ActiveEventResponse(
            rarity=Rarity.MYTHIC,
            title="Затмение: Ночь Реликвий",
            xpMultiplier="×3 XP",
            timeLeft="2Д 14Ч",
        ),
        quests=[
            QuestCardResponse(
                id="old-town-shadows",
                name="Тени Старого города",
                step="Точка 3 из 5",
                progress=60,
                rarity=Rarity.EPIC,
                xp=450,
            )
        ],
        recentRewards=[
            RecentRewardResponse(
                source="Скан · ТЦ «Орбита»",
                xp=120,
                multiplier="×2",
                time="12 мин назад",
                color=UIColorToken.CYAN,
            )
        ],
        mapPins=build_map_points_response().mapPins,
        nearbyPoints=build_map_points_response().nearbyPoints,
        pointDetails=build_map_points_response().pointDetails,
        stats=[
            StatCardResponse(value="218", label="СКАНОВ", color=UIColorToken.CYAN)
        ],
        profileLinks=[
            ProfileLinkResponse(
                icon="bolt",
                title="История XP",
                subtitle="6 840 за сезон",
                color=UIColorToken.CYAN,
                to="/xp",
            )
        ],
        xpHistoryGroups=[
            XpHistoryGroupResponse(
                day="СЕГОДНЯ",
                items=[
                    XpHistoryItemResponse(
                        source="Скан · Маяк на крыше",
                        tag="AR",
                        xp=180,
                        multiplier="×3",
                        color=UIColorToken.CYAN,
                        time="14:22",
                    )
                ],
            )
        ],
        achievements=[
            AchievementResponse(
                icon="qr",
                name="Первый скан",
                rarity=Rarity.COMMON,
                unlocked=True,
            )
        ],
    )


class TestFrontendDataRoutes:
    @property
    def client(self) -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    def test_app_state_returns_payload(self) -> None:
        expected = build_app_state_response()

        async def fake_get_app_state(self):
            return expected

        with patch.object(
            FrontendDataBusinessService,
            "get_app_state",
            fake_get_app_state,
        ):
            response = self.client.get(
                "/app/state",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode="json")

    def test_map_points_returns_payload_and_parses_query(self) -> None:
        expected = build_map_points_response()
        captured = {}

        async def fake_get_map_points(self, params):
            captured["params"] = params
            return expected

        with patch.object(
            FrontendDataBusinessService,
            "get_map_points",
            fake_get_map_points,
        ):
            response = self.client.get(
                "/map/points",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                params={
                    "lat": 55.75,
                    "lon": 37.61,
                    "radius_meters": 500,
                    "done": "false",
                },
            )

        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode="json")
        assert captured["params"].lat == 55.75
        assert captured["params"].lon == 37.61
        assert captured["params"].radius_meters == 500
        assert captured["params"].done is False

    def test_quests_returns_items(self) -> None:
        expected = QuestsResponse(
            items=[
                QuestCardResponse(
                    id="old-town-shadows",
                    name="Тени Старого города",
                    step="Точка 3 из 5",
                    progress=60,
                    rarity=Rarity.EPIC,
                    xp=450,
                )
            ]
        )

        async def fake_get_quests(self):
            return expected

        with patch.object(
            FrontendDataBusinessService,
            "get_quests",
            fake_get_quests,
        ):
            response = self.client.get(
                "/quests",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode="json")

    def test_xp_history_returns_groups(self) -> None:
        expected = XpHistoryResponse(
            groups=[
                XpHistoryGroupResponse(
                    day="СЕГОДНЯ",
                    items=[
                        XpHistoryItemResponse(
                            source="Скан · Маяк на крыше",
                            tag="AR",
                            xp=180,
                            multiplier="×3",
                            color=UIColorToken.CYAN,
                            time="14:22",
                        )
                    ],
                )
            ]
        )

        async def fake_get_xp_history(self, params):
            return expected

        with patch.object(
            FrontendDataBusinessService,
            "get_xp_history",
            fake_get_xp_history,
        ):
            response = self.client.get(
                "/xp/history",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode="json")

    def test_achievements_returns_summary(self) -> None:
        expected = AchievementsResponse(
            items=[
                AchievementResponse(
                    icon="qr",
                    name="Первый скан",
                    rarity=Rarity.COMMON,
                    unlocked=True,
                )
            ],
            summary={"unlocked": 23, "total": 60},
        )

        async def fake_get_achievements(self):
            return expected

        with patch.object(
            FrontendDataBusinessService,
            "get_achievements",
            fake_get_achievements,
        ):
            response = self.client.get(
                "/achievements",
                headers={"Authorization": f"Bearer {build_access_token()}"},
            )

        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode="json")

    def test_scan_claim_returns_payload(self) -> None:
        expected = ScanClaimResponse(
            xp=250,
            user=build_frontend_user(),
            claimed_at=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        )

        async def fake_claim_scan_reward(self, dto):
            assert dto.scan_id == "roof-beacon"
            return expected

        with patch.object(
            FrontendDataBusinessService,
            "claim_scan_reward",
            fake_claim_scan_reward,
        ):
            response = self.client.post(
                "/scan/claim",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                json={"scan_id": "roof-beacon"},
            )

        assert response.status_code == 200
        assert response.json() == expected.model_dump(mode="json")

    def test_scan_claim_propagates_not_found(self) -> None:
        async def fake_claim_scan_reward(self, dto):
            raise ScanNotFoundError()

        with patch.object(
            FrontendDataBusinessService,
            "claim_scan_reward",
            fake_claim_scan_reward,
        ):
            response = self.client.post(
                "/scan/claim",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                json={"scan_id": "missing"},
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "scan_not_found"

    def test_scan_claim_propagates_conflict(self) -> None:
        async def fake_claim_scan_reward(self, dto):
            raise RewardAlreadyClaimedError()

        with patch.object(
            FrontendDataBusinessService,
            "claim_scan_reward",
            fake_claim_scan_reward,
        ):
            response = self.client.post(
                "/scan/claim",
                headers={"Authorization": f"Bearer {build_access_token()}"},
                json={"scan_id": "roof-beacon"},
            )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "reward_already_claimed"

    def test_frontend_data_routes_require_authorization(self) -> None:
        paths = [
            ("get", "/app/state"),
            ("get", "/map/points"),
            ("get", "/quests"),
            ("get", "/xp/history"),
            ("get", "/achievements"),
            ("post", "/scan/claim"),
        ]

        for method, path in paths:
            if method == "post":
                response = self.client.post(path, json={"scan_id": "roof-beacon"})
            else:
                response = self.client.get(path)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "missing_authorization"


class TestFrontendDataRouteContracts:
    def test_handlers_do_not_expose_session_dependency(self) -> None:
        import inspect

        for handler in [
            app_state_api.get_app_state,
            map_api.get_map_points,
            quest_api.get_quests,
            xp_api.get_xp_history,
            achievement_api.get_achievements,
            scan_api.claim_scan_reward,
        ]:
            parameters = inspect.signature(handler).parameters
            assert "session" not in parameters
            assert "service" not in parameters

    def test_routers_are_registered(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)

        assert client.get("/app/state").status_code == 401
        assert client.get("/map/points").status_code == 401
        assert client.get("/quests").status_code == 401
        assert client.get("/xp/history").status_code == 401
        assert client.get("/achievements").status_code == 401
        assert (
            client.post("/scan/claim", json={"scan_id": "roof-beacon"}).status_code
            == 401
        )
