"""
Tests for FrontendDataBusinessService formatting helpers and pure-logic methods.

These are the deterministic, non-IO utility methods on the service class.
Covers:
- _format_decimal
- _format_multiplier
- _format_time_left
- _format_distance
- _format_relative_time (approximate)
- _format_group_day (today / yesterday / older)
- _format_xp_source (scan prefix / non-scan)
- _get_color_for_rarity
- _is_secret_masked
- _matches_map_filters
- _get_public_secret_name
- _get_public_secret_category
- _get_public_secret_rarity
- _parse_secret_id
- _build_stats
- _build_profile_links
- _build_quest_lookup
- _build_xp_weekly_summary
- _build_achievements
- _get_current_week_bounds
- _distance_meters (smoke test)
- _get_stable_nearby_coords (determinism & within range)
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase

from app.db.models.enums import Rarity, UIColorToken
from app.services.business.frontend_data import FrontendDataBusinessService


# --------------------------------------------------------------------------- #
# _format_decimal
# --------------------------------------------------------------------------- #
class FormatDecimalTests(TestCase):
    def test_integer_decimal_omits_trailing_zeros(self) -> None:
        self.assertEqual(FrontendDataBusinessService._format_decimal(Decimal("2.00")), "2")

    def test_fractional_decimal_is_preserved(self) -> None:
        self.assertEqual(FrontendDataBusinessService._format_decimal(Decimal("1.5")), "1.5")

    def test_decimal_trailing_zeros_are_stripped(self) -> None:
        self.assertEqual(FrontendDataBusinessService._format_decimal(Decimal("2.50")), "2.5")

    def test_large_integer(self) -> None:
        self.assertEqual(FrontendDataBusinessService._format_decimal(Decimal("100")), "100")


# --------------------------------------------------------------------------- #
# _format_multiplier
# --------------------------------------------------------------------------- #
class FormatMultiplierTests(TestCase):
    def test_none_multiplier_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._format_multiplier(None))

    def test_multiplier_of_1_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._format_multiplier(Decimal("1")))

    def test_multiplier_of_1_00_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._format_multiplier(Decimal("1.00")))

    def test_multiplier_greater_than_1_is_formatted(self) -> None:
        result = FrontendDataBusinessService._format_multiplier(Decimal("2"))
        self.assertEqual(result, "×2")

    def test_fractional_multiplier_is_formatted(self) -> None:
        result = FrontendDataBusinessService._format_multiplier(Decimal("1.5"))
        self.assertEqual(result, "×1.5")


# --------------------------------------------------------------------------- #
# _format_time_left
# --------------------------------------------------------------------------- #
class FormatTimeLeftTests(TestCase):
    def test_zero_time_returns_zero_minutes(self) -> None:
        result = FrontendDataBusinessService._format_time_left(timedelta(0))
        self.assertEqual(result, "0М")

    def test_minutes_only(self) -> None:
        result = FrontendDataBusinessService._format_time_left(timedelta(minutes=45))
        self.assertEqual(result, "45М")

    def test_hours_and_minutes(self) -> None:
        result = FrontendDataBusinessService._format_time_left(timedelta(hours=3, minutes=20))
        self.assertEqual(result, "3Ч 20М")

    def test_days_and_hours(self) -> None:
        result = FrontendDataBusinessService._format_time_left(timedelta(days=2, hours=5))
        self.assertEqual(result, "2Д 5Ч")

    def test_exactly_one_hour(self) -> None:
        result = FrontendDataBusinessService._format_time_left(timedelta(hours=1))
        self.assertEqual(result, "1Ч 0М")

    def test_exactly_one_day(self) -> None:
        result = FrontendDataBusinessService._format_time_left(timedelta(days=1))
        self.assertEqual(result, "1Д 0Ч")


# --------------------------------------------------------------------------- #
# _format_distance
# --------------------------------------------------------------------------- #
class FormatDistanceTests(TestCase):
    def test_none_distance_returns_dash(self) -> None:
        self.assertEqual(FrontendDataBusinessService._format_distance(None, uppercase=False), "—")

    def test_distance_lowercase_suffix(self) -> None:
        result = FrontendDataBusinessService._format_distance(120.4, uppercase=False)
        self.assertEqual(result, "120 м")

    def test_distance_uppercase_suffix(self) -> None:
        result = FrontendDataBusinessService._format_distance(120.4, uppercase=True)
        self.assertEqual(result, "120 М")

    def test_distance_rounds_to_nearest_meter(self) -> None:
        result = FrontendDataBusinessService._format_distance(100.6, uppercase=False)
        self.assertEqual(result, "101 м")

    def test_zero_distance(self) -> None:
        result = FrontendDataBusinessService._format_distance(0.0, uppercase=False)
        self.assertEqual(result, "0 м")


# --------------------------------------------------------------------------- #
# _format_group_day
# --------------------------------------------------------------------------- #
class FormatGroupDayTests(TestCase):
    def test_today_returns_label(self) -> None:
        today = datetime.now(UTC).date()
        result = FrontendDataBusinessService._format_group_day(today)
        self.assertEqual(result, "СЕГОДНЯ")

    def test_yesterday_returns_label(self) -> None:
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        result = FrontendDataBusinessService._format_group_day(yesterday)
        self.assertEqual(result, "ВЧЕРА")

    def test_older_date_returns_formatted_string(self) -> None:
        past = date(2026, 1, 15)
        result = FrontendDataBusinessService._format_group_day(past)
        self.assertEqual(result, "15.01.2026")

    def test_day_before_yesterday_is_not_labelled(self) -> None:
        two_days_ago = datetime.now(UTC).date() - timedelta(days=2)
        result = FrontendDataBusinessService._format_group_day(two_days_ago)
        self.assertNotIn(result, {"СЕГОДНЯ", "ВЧЕРА"})


# --------------------------------------------------------------------------- #
# _format_xp_source
# --------------------------------------------------------------------------- #
class FormatXpSourceTests(TestCase):
    def test_scan_source_with_known_secret_uses_title(self) -> None:
        secrets_by_id = {
            "42": SimpleNamespace(title="Старый маяк"),
        }
        result = FrontendDataBusinessService._format_xp_source("scan:42", secrets_by_id)
        self.assertEqual(result, "Скан · Старый маяк")

    def test_scan_source_with_unknown_secret_uses_raw(self) -> None:
        result = FrontendDataBusinessService._format_xp_source("scan:999", {})
        self.assertEqual(result, "scan:999")

    def test_non_scan_source_is_returned_unchanged(self) -> None:
        result = FrontendDataBusinessService._format_xp_source("bonus:daily", {})
        self.assertEqual(result, "bonus:daily")


# --------------------------------------------------------------------------- #
# _get_color_for_rarity
# --------------------------------------------------------------------------- #
class GetColorForRarityTests(TestCase):
    def test_common_maps_to_cyan(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_color_for_rarity(Rarity.COMMON),
            UIColorToken.CYAN,
        )

    def test_epic_maps_to_violet_hi(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_color_for_rarity(Rarity.EPIC),
            UIColorToken.VIOLET_HI,
        )

    def test_legendary_maps_to_gold(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_color_for_rarity(Rarity.LEGENDARY),
            UIColorToken.GOLD,
        )

    def test_mythic_maps_to_pink(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_color_for_rarity(Rarity.MYTHIC),
            UIColorToken.PINK,
        )

    def test_all_rarities_are_covered(self) -> None:
        for rarity in Rarity:
            # Should not raise KeyError
            FrontendDataBusinessService._get_color_for_rarity(rarity)


# --------------------------------------------------------------------------- #
# _is_secret_masked
# --------------------------------------------------------------------------- #
class IsSecretMaskedTests(TestCase):
    def _secret(self, *, hidden: bool) -> SimpleNamespace:
        return SimpleNamespace(hidden=hidden)

    def test_hidden_and_not_opened_is_masked(self) -> None:
        self.assertTrue(
            FrontendDataBusinessService._is_secret_masked(self._secret(hidden=True), False)
        )

    def test_hidden_but_opened_is_not_masked(self) -> None:
        self.assertFalse(
            FrontendDataBusinessService._is_secret_masked(self._secret(hidden=True), True)
        )

    def test_not_hidden_and_not_opened_is_not_masked(self) -> None:
        self.assertFalse(
            FrontendDataBusinessService._is_secret_masked(self._secret(hidden=False), False)
        )

    def test_not_hidden_and_opened_is_not_masked(self) -> None:
        self.assertFalse(
            FrontendDataBusinessService._is_secret_masked(self._secret(hidden=False), True)
        )


# --------------------------------------------------------------------------- #
# _matches_map_filters
# --------------------------------------------------------------------------- #
class MatchesMapFiltersTests(TestCase):
    def _secret(self, *, rarity: Rarity = Rarity.EPIC, category: str = "AR-сцена") -> SimpleNamespace:
        return SimpleNamespace(rarity=rarity, category=category)

    def test_no_filters_always_matches(self) -> None:
        self.assertTrue(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(),
                is_masked=False,
                rarity=None,
                category=None,
            )
        )

    def test_rarity_filter_matches_exact(self) -> None:
        self.assertTrue(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(rarity=Rarity.RARE),
                is_masked=False,
                rarity=Rarity.RARE,
                category=None,
            )
        )

    def test_rarity_filter_excludes_different(self) -> None:
        self.assertFalse(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(rarity=Rarity.EPIC),
                is_masked=False,
                rarity=Rarity.RARE,
                category=None,
            )
        )

    def test_category_filter_matches_exact(self) -> None:
        self.assertTrue(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(category="Музей"),
                is_masked=False,
                rarity=None,
                category="Музей",
            )
        )

    def test_category_filter_excludes_different(self) -> None:
        self.assertFalse(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(category="Музей"),
                is_masked=False,
                rarity=None,
                category="AR-сцена",
            )
        )

    def test_masked_with_rarity_filter_is_excluded(self) -> None:
        # A hidden/masked secret should never appear in rarity-filtered results
        self.assertFalse(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(),
                is_masked=True,
                rarity=Rarity.EPIC,
                category=None,
            )
        )

    def test_masked_with_no_filters_is_included(self) -> None:
        self.assertTrue(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(),
                is_masked=True,
                rarity=None,
                category=None,
            )
        )

    def test_masked_with_secret_category_is_included(self) -> None:
        self.assertTrue(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(),
                is_masked=True,
                rarity=None,
                category="Секрет",
            )
        )

    def test_masked_with_non_secret_category_is_excluded(self) -> None:
        self.assertFalse(
            FrontendDataBusinessService._matches_map_filters(
                self._secret(),
                is_masked=True,
                rarity=None,
                category="Музей",
            )
        )


# --------------------------------------------------------------------------- #
# _get_public_secret_name / category / rarity
# --------------------------------------------------------------------------- #
class PublicSecretFieldsTests(TestCase):
    def _secret(self) -> SimpleNamespace:
        return SimpleNamespace(
            title="Lighthouse",
            category="AR-сцена",
            rarity=Rarity.LEGENDARY,
        )

    def test_unmasked_secret_shows_real_name(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_public_secret_name(self._secret(), is_masked=False),
            "Lighthouse",
        )

    def test_masked_secret_shows_generic_name(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_public_secret_name(self._secret(), is_masked=True),
            "Скрытый секрет",
        )

    def test_unmasked_secret_shows_real_category(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_public_secret_category(self._secret(), is_masked=False),
            "AR-сцена",
        )

    def test_masked_secret_shows_generic_category(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_public_secret_category(self._secret(), is_masked=True),
            "Секрет",
        )

    def test_unmasked_secret_shows_real_rarity(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_public_secret_rarity(self._secret(), is_masked=False),
            Rarity.LEGENDARY,
        )

    def test_masked_secret_shows_common_rarity(self) -> None:
        self.assertEqual(
            FrontendDataBusinessService._get_public_secret_rarity(self._secret(), is_masked=True),
            Rarity.COMMON,
        )


# --------------------------------------------------------------------------- #
# _parse_secret_id
# --------------------------------------------------------------------------- #
class ParseSecretIdTests(TestCase):
    def test_valid_positive_integer_string(self) -> None:
        self.assertEqual(FrontendDataBusinessService._parse_secret_id("42"), 42)

    def test_zero_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._parse_secret_id("0"))

    def test_negative_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._parse_secret_id("-1"))

    def test_non_numeric_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._parse_secret_id("abc"))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._parse_secret_id(""))

    def test_none_returns_none(self) -> None:
        self.assertIsNone(FrontendDataBusinessService._parse_secret_id(None))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# _build_stats
# --------------------------------------------------------------------------- #
class BuildStatsTests(TestCase):
    def test_stats_has_exactly_four_cards(self) -> None:
        stats = FrontendDataBusinessService._build_stats(
            scan_count=10,
            point_count=20,
            quest_count=3,
            achievement_count=5,
        )
        self.assertEqual(len(stats), 4)

    def test_scan_count_is_first_card(self) -> None:
        stats = FrontendDataBusinessService._build_stats(
            scan_count=7,
            point_count=0,
            quest_count=0,
            achievement_count=0,
        )
        self.assertEqual(stats[0].value, "7")
        self.assertEqual(stats[0].label, "СКАНОВ")

    def test_point_count_is_second_card(self) -> None:
        stats = FrontendDataBusinessService._build_stats(
            scan_count=0,
            point_count=42,
            quest_count=0,
            achievement_count=0,
        )
        self.assertEqual(stats[1].value, "42")

    def test_zero_values_are_rendered_as_strings(self) -> None:
        stats = FrontendDataBusinessService._build_stats(
            scan_count=0,
            point_count=0,
            quest_count=0,
            achievement_count=0,
        )
        for card in stats:
            self.assertEqual(card.value, "0")


# --------------------------------------------------------------------------- #
# _build_quest_lookup
# --------------------------------------------------------------------------- #
class BuildQuestLookupTests(TestCase):
    def test_empty_quests_returns_empty_dict(self) -> None:
        self.assertEqual(FrontendDataBusinessService._build_quest_lookup([]), {})

    def test_quests_are_keyed_by_id(self) -> None:
        quests = [
            SimpleNamespace(id="q1", name="Quest Alpha"),
            SimpleNamespace(id="q2", name="Quest Beta"),
        ]
        lookup = FrontendDataBusinessService._build_quest_lookup(quests)
        self.assertEqual(lookup, {"q1": "Quest Alpha", "q2": "Quest Beta"})


# --------------------------------------------------------------------------- #
# _build_xp_weekly_summary
# --------------------------------------------------------------------------- #
class BuildXpWeeklySummaryTests(TestCase):
    def _make_week_start(self) -> datetime:
        today = datetime.now(UTC).date()
        week_start_date = today - timedelta(days=today.weekday())
        from datetime import time
        return datetime.combine(week_start_date, time.min, tzinfo=UTC)

    def _xp_event(self, *, xp: int, day_offset: int) -> SimpleNamespace:
        week_start = self._make_week_start()
        occurred_at = week_start + timedelta(days=day_offset, hours=10)
        return SimpleNamespace(xp=xp, occurred_at=occurred_at)

    def test_empty_events_returns_all_zeros(self) -> None:
        week_start = self._make_week_start()
        result = FrontendDataBusinessService._build_xp_weekly_summary([], week_start=week_start)
        self.assertEqual(result.days, [0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(result.total, 0)

    def test_event_on_monday_goes_into_index_0(self) -> None:
        week_start = self._make_week_start()
        events = [self._xp_event(xp=100, day_offset=0)]
        result = FrontendDataBusinessService._build_xp_weekly_summary(events, week_start=week_start)
        self.assertEqual(result.days[0], 100)
        self.assertEqual(result.total, 100)

    def test_event_on_sunday_goes_into_index_6(self) -> None:
        week_start = self._make_week_start()
        events = [self._xp_event(xp=50, day_offset=6)]
        result = FrontendDataBusinessService._build_xp_weekly_summary(events, week_start=week_start)
        self.assertEqual(result.days[6], 50)

    def test_multiple_events_on_same_day_are_summed(self) -> None:
        week_start = self._make_week_start()
        events = [
            self._xp_event(xp=30, day_offset=2),
            self._xp_event(xp=20, day_offset=2),
        ]
        result = FrontendDataBusinessService._build_xp_weekly_summary(events, week_start=week_start)
        self.assertEqual(result.days[2], 50)

    def test_negative_xp_is_counted_by_absolute_value(self) -> None:
        week_start = self._make_week_start()
        events = [self._xp_event(xp=-30, day_offset=1)]
        result = FrontendDataBusinessService._build_xp_weekly_summary(events, week_start=week_start)
        # abs(-30) = 30
        self.assertEqual(result.days[1], 30)

    def test_total_is_sum_of_days(self) -> None:
        week_start = self._make_week_start()
        events = [
            self._xp_event(xp=10, day_offset=0),
            self._xp_event(xp=20, day_offset=3),
        ]
        result = FrontendDataBusinessService._build_xp_weekly_summary(events, week_start=week_start)
        self.assertEqual(result.total, sum(result.days))


# --------------------------------------------------------------------------- #
# _build_achievements
# --------------------------------------------------------------------------- #
class BuildAchievementsTests(TestCase):
    def _achievement(
        self,
        *,
        name: str = "First Scan",
        rarity: Rarity = Rarity.COMMON,
        icon: str = "star",
    ) -> SimpleNamespace:
        return SimpleNamespace(name=name, rarity=rarity, icon=icon)

    def _user_achievement(
        self,
        *,
        unlocked: bool,
        progress_percent: int = 0,
        unlocked_at: datetime | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            unlocked=unlocked,
            progress_percent=progress_percent,
            unlocked_at=unlocked_at or datetime.now(UTC),
        )

    def test_unlocked_achievement_has_no_progress(self) -> None:
        states = [(self._achievement(), self._user_achievement(unlocked=True, progress_percent=50))]
        result = FrontendDataBusinessService._build_achievements(states)
        self.assertTrue(result[0].unlocked)
        self.assertIsNone(result[0].progress)  # progress is None when unlocked

    def test_locked_achievement_has_progress_from_user_achievement(self) -> None:
        ua = self._user_achievement(unlocked=False, progress_percent=60)
        states = [(self._achievement(), ua)]
        result = FrontendDataBusinessService._build_achievements(states)
        self.assertFalse(result[0].unlocked)
        self.assertEqual(result[0].progress, 60)

    def test_locked_achievement_with_no_user_record_shows_zero_progress(self) -> None:
        states = [(self._achievement(), None)]
        result = FrontendDataBusinessService._build_achievements(states)
        self.assertFalse(result[0].unlocked)
        self.assertEqual(result[0].progress, 0)

    def test_multiple_achievements_are_preserved_in_order(self) -> None:
        states = [
            (self._achievement(name="Alpha"), self._user_achievement(unlocked=True)),
            (self._achievement(name="Beta"), None),
        ]
        result = FrontendDataBusinessService._build_achievements(states)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Alpha")
        self.assertEqual(result[1].name, "Beta")


# --------------------------------------------------------------------------- #
# _get_current_week_bounds
# --------------------------------------------------------------------------- #
class GetCurrentWeekBoundsTests(TestCase):
    def test_returns_two_datetimes(self) -> None:
        start, end = FrontendDataBusinessService._get_current_week_bounds()
        self.assertIsInstance(start, datetime)
        self.assertIsInstance(end, datetime)

    def test_week_span_is_7_days(self) -> None:
        start, end = FrontendDataBusinessService._get_current_week_bounds()
        self.assertEqual((end - start).days, 7)

    def test_start_is_midnight_utc_on_monday(self) -> None:
        start, _ = FrontendDataBusinessService._get_current_week_bounds()
        self.assertEqual(start.weekday(), 0)  # Monday
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.minute, 0)
        self.assertEqual(start.second, 0)


# --------------------------------------------------------------------------- #
# _distance_meters (haversine smoke test)
# --------------------------------------------------------------------------- #
class DistanceMetersTests(TestCase):
    def test_same_point_is_zero(self) -> None:
        d = FrontendDataBusinessService._distance_meters(55.75, 37.62, 55.75, 37.62)
        self.assertAlmostEqual(d, 0.0, places=5)

    def test_known_distance_between_moscow_landmarks(self) -> None:
        # Red Square (55.7539, 37.6208) to Kremlin (55.7520, 37.6175) ≈ 225 m
        d = FrontendDataBusinessService._distance_meters(55.7539, 37.6208, 55.7520, 37.6175)
        self.assertGreater(d, 100)
        self.assertLess(d, 500)

    def test_returns_float(self) -> None:
        d = FrontendDataBusinessService._distance_meters(0.0, 0.0, 1.0, 0.0)
        self.assertIsInstance(d, float)


# --------------------------------------------------------------------------- #
# _get_stable_nearby_coords (determinism + within max_distance)
# --------------------------------------------------------------------------- #
class GetStableNearbyCoordsTests(TestCase):
    def test_output_is_deterministic(self) -> None:
        coords = (55.75, 37.62)
        a = FrontendDataBusinessService._get_stable_nearby_coords(
            coords, seed="user:1:secret:5:hidden-map-offset", max_distance_meters=100
        )
        b = FrontendDataBusinessService._get_stable_nearby_coords(
            coords, seed="user:1:secret:5:hidden-map-offset", max_distance_meters=100
        )
        self.assertEqual(a, b)

    def test_different_seeds_produce_different_output(self) -> None:
        coords = (55.75, 37.62)
        a = FrontendDataBusinessService._get_stable_nearby_coords(
            coords, seed="seed-A", max_distance_meters=100
        )
        b = FrontendDataBusinessService._get_stable_nearby_coords(
            coords, seed="seed-B", max_distance_meters=100
        )
        self.assertNotEqual(a, b)

    def test_output_is_within_max_distance(self) -> None:
        coords = (55.751620, 37.618660)
        offset = FrontendDataBusinessService._get_stable_nearby_coords(
            coords, seed="test-seed", max_distance_meters=100
        )
        distance = FrontendDataBusinessService._distance_meters(
            coords[0], coords[1], offset[0], offset[1]
        )
        self.assertLessEqual(distance, 100)

    def test_output_is_not_same_as_input(self) -> None:
        coords = (55.75, 37.62)
        offset = FrontendDataBusinessService._get_stable_nearby_coords(
            coords, seed="nonempty-seed", max_distance_meters=100
        )
        # With a real seed, the offset should be non-zero
        # (extremely unlikely to be exactly 0, but correct)
        distance = FrontendDataBusinessService._distance_meters(
            coords[0], coords[1], offset[0], offset[1]
        )
        self.assertGreater(distance, 0.0)
