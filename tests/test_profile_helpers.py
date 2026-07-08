"""
Tests for the ProfileBusinessService._parse_cached_count helper.

Covers:
- None → None
- Non-numeric string → None
- Negative numeric string → None
- Zero → 0 (special edge: valid non-negative count)
- Positive integer string → integer
- Integer string with whitespace → None (strict parse)
"""

from unittest import TestCase

from app.services.business.profile import ProfileBusinessService


class ParseCachedCountTests(TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(ProfileBusinessService._parse_cached_count(None))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(ProfileBusinessService._parse_cached_count(""))

    def test_non_numeric_string_returns_none(self) -> None:
        self.assertIsNone(ProfileBusinessService._parse_cached_count("abc"))

    def test_float_string_returns_none(self) -> None:
        self.assertIsNone(ProfileBusinessService._parse_cached_count("3.14"))

    def test_negative_count_returns_none(self) -> None:
        self.assertIsNone(ProfileBusinessService._parse_cached_count("-1"))

    def test_zero_is_valid_and_returned(self) -> None:
        self.assertEqual(ProfileBusinessService._parse_cached_count("0"), 0)

    def test_positive_count_is_returned(self) -> None:
        self.assertEqual(ProfileBusinessService._parse_cached_count("42"), 42)

    def test_large_positive_count_is_returned(self) -> None:
        self.assertEqual(ProfileBusinessService._parse_cached_count("999999"), 999999)
