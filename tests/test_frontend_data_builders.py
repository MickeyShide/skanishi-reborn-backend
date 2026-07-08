"""
Tests for FrontendDataBusinessService user/profile response builders.

Covers:
- _build_frontend_user: field mapping, display_name priority, username fallback
- _build_profile_links: structure, count, XP subtitle, achievement subtitle
"""

from types import SimpleNamespace
from unittest import TestCase

from app.db.models.enums import UIColorToken
from app.services.business.frontend_data import FrontendDataBusinessService


def _make_user(
    *,
    id: int = 1,
    first_name: str = "Alice",
    last_name: str | None = None,
    display_name: str | None = None,
    username: str | None = "alice42",
    public_id: str | None = "0xALICE",
    rank: int | None = 10,
    level: int = 5,
    level_progress: int = 60,
    xp: int = 4500,
    next_level_xp: int = 10000,
    streak_days: int = 3,
    season_label: str | None = "СЕЗОН 2",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name,
        username=username,
        public_id=public_id,
        rank=rank,
        level=level,
        level_progress=level_progress,
        xp=xp,
        next_level_xp=next_level_xp,
        streak_days=streak_days,
        season_label=season_label,
    )


class BuildFrontendUserTests(TestCase):
    def test_display_name_takes_priority_over_first_name(self) -> None:
        user = _make_user(display_name="Алиса В.", first_name="Alice")
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.name, "Алиса В.")

    def test_first_name_used_when_no_display_name(self) -> None:
        user = _make_user(display_name=None, first_name="Bob")
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.name, "Bob")

    def test_username_is_used_as_username_field(self) -> None:
        user = _make_user(username="bob_marley")
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.username, "bob_marley")

    def test_public_id_used_as_username_when_no_username(self) -> None:
        user = _make_user(username=None, public_id="0xBOB", id=42)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.username, "0xBOB")

    def test_user_id_fallback_when_no_username_and_no_public_id(self) -> None:
        user = _make_user(username=None, public_id=None, id=42)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.username, "user42")

    def test_public_id_used_as_id_field(self) -> None:
        user = _make_user(public_id="0xSPECIAL", id=9)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.id, "0xSPECIAL")

    def test_numeric_id_as_string_used_when_no_public_id(self) -> None:
        user = _make_user(public_id=None, id=9)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.id, "9")

    def test_next_level_xp_defaults_to_1000_when_zero(self) -> None:
        user = _make_user(next_level_xp=0)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.next_level_xp, 1000)

    def test_non_zero_next_level_xp_is_preserved(self) -> None:
        user = _make_user(next_level_xp=5000)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.next_level_xp, 5000)

    def test_season_label_is_used_as_season(self) -> None:
        user = _make_user(season_label="СЕЗОН 3 · ТЕСТ")
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.season, "СЕЗОН 3 · ТЕСТ")

    def test_missing_season_label_defaults_to_empty_string(self) -> None:
        user = _make_user(season_label=None)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.season, "")

    def test_all_numeric_fields_are_mapped_correctly(self) -> None:
        user = _make_user(rank=5, level=3, level_progress=75, xp=2000, streak_days=7)
        result = FrontendDataBusinessService._build_frontend_user(user)
        self.assertEqual(result.rank, 5)
        self.assertEqual(result.level, 3)
        self.assertEqual(result.level_progress, 75)
        self.assertEqual(result.xp, 2000)
        self.assertEqual(result.streak_days, 7)


class BuildProfileLinksTests(TestCase):
    def test_returns_exactly_three_links(self) -> None:
        user = _make_user(xp=7000)
        result = FrontendDataBusinessService._build_profile_links(
            user=user, achievement_unlocked=3, achievement_total=10
        )
        self.assertEqual(len(result), 3)

    def test_first_link_is_xp_history(self) -> None:
        user = _make_user(xp=7000)
        result = FrontendDataBusinessService._build_profile_links(
            user=user, achievement_unlocked=3, achievement_total=10
        )
        self.assertEqual(result[0].to, "/xp")
        self.assertEqual(result[0].title, "История XP")
        self.assertIn("7000", result[0].subtitle)  # shows XP amount

    def test_second_link_is_achievements(self) -> None:
        user = _make_user(xp=0)
        result = FrontendDataBusinessService._build_profile_links(
            user=user, achievement_unlocked=4, achievement_total=12
        )
        self.assertEqual(result[1].to, "/achievements")
        self.assertIn("4", result[1].subtitle)
        self.assertIn("12", result[1].subtitle)

    def test_third_link_is_inventory(self) -> None:
        user = _make_user()
        result = FrontendDataBusinessService._build_profile_links(
            user=user, achievement_unlocked=0, achievement_total=0
        )
        self.assertEqual(result[2].to, "/inventory")

    def test_all_links_have_colors(self) -> None:
        user = _make_user()
        result = FrontendDataBusinessService._build_profile_links(
            user=user, achievement_unlocked=0, achievement_total=0
        )
        for link in result:
            self.assertIsInstance(link.color, UIColorToken)

    def test_zero_achievements_renders_correctly(self) -> None:
        user = _make_user()
        result = FrontendDataBusinessService._build_profile_links(
            user=user, achievement_unlocked=0, achievement_total=0
        )
        self.assertIn("0", result[1].subtitle)
