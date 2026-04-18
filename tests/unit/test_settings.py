from enum import Enum

import pytest

from src.settings import GlobalSettings, Themes


def test_global_settings():
    """Test GlobalSettings model fields and validators."""
    # Test default values
    assert GlobalSettings.__fields__["send_notification"].default is True
    assert GlobalSettings.__fields__["refresh_interval"].default == 5
    assert GlobalSettings.__fields__["reading_speed"].default == 238
    assert GlobalSettings.__fields__["recent_hours"].default == 36
    assert GlobalSettings.__fields__["finished_onboarding"].default is False
    assert (
        GlobalSettings.__fields__["notification_handler_key"].default
        == "null_notification"
    )
    assert GlobalSettings.__fields__["llm_handler_key"].default == "null_llm"
    assert (
        GlobalSettings.__fields__["content_retrieval_handler_key"].default
        == "playwright"
    )


def test_themes_enum():
    """Test Themes enum has expected values."""
    assert Themes.forest.value == "forest"
    assert Themes.dark.value == "dark"
    assert Themes.nord.value == "nord"
