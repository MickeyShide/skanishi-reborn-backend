"""
Tests for Achievement logic in FrontendDataBusinessService.

Covers:
- _build_achievements mapping logic
"""

from types import SimpleNamespace
from unittest import TestCase

from app.services.business.frontend_data import FrontendDataBusinessService


class BuildAchievementsTests(TestCase):
    def test_build_achievements_maps_correctly(self) -> None:
        service = object.__new__(FrontendDataBusinessService)
        
        ach1 = SimpleNamespace(id="a1", name="First Blood", rarity="common", icon="icon1")
        ach2 = SimpleNamespace(id="a2", name="Master", rarity="legendary", icon="icon2")
        
        # user_ach1 is unlocked, user_ach2 is in progress
        user_ach1 = SimpleNamespace(unlocked=True, progress_percent=100)
        user_ach2 = SimpleNamespace(unlocked=False, progress_percent=45)
        
        states = [
            (ach1, user_ach1),
            (ach2, user_ach2),
        ]
        
        result = service._build_achievements(states)
        
        self.assertEqual(len(result), 2)
        
        self.assertEqual(result[0].id, "a1")
        self.assertTrue(result[0].unlocked)
        self.assertEqual(result[0].progress, 100)
        
        self.assertEqual(result[1].id, "a2")
        self.assertFalse(result[1].unlocked)
        self.assertEqual(result[1].progress, 45)

    def test_build_achievements_handles_none_user_achievement(self) -> None:
        service = object.__new__(FrontendDataBusinessService)
        
        ach = SimpleNamespace(id="a1", name="Secret", rarity="rare", icon="icon")
        
        states = [(ach, None)]
        
        result = service._build_achievements(states)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "a1")
        self.assertFalse(result[0].unlocked)
        self.assertEqual(result[0].progress, 0)
