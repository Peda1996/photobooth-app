from pathlib import Path

import pytest
from PIL import Image

from photobooth.models.stillretry import StillRetry
from photobooth.plugins.blitz_wache.blitz_wache import BlitzWache, image_brightness


def _img(tmp_path: Path, name: str, value: int) -> Path:
    path = tmp_path / name
    Image.new("RGB", (200, 150), (value, value, value)).save(path)
    return path


def test_image_brightness(tmp_path):
    mean, dark_share = image_brightness(_img(tmp_path, "black.jpg", 0))
    assert mean < 5
    assert dark_share > 0.9

    mean, dark_share = image_brightness(_img(tmp_path, "mid.jpg", 120))
    assert 110 < mean < 130
    assert dark_share < 0.1


def test_normal_image_no_retry(tmp_path):
    plugin = BlitzWache()
    assert plugin.acq_still_check(_img(tmp_path, "n.jpg", 120)) is None


def test_black_image_requests_retry_with_ambient_values(tmp_path):
    plugin = BlitzWache()
    retry = plugin.acq_still_check(_img(tmp_path, "b.jpg", 2))
    assert isinstance(retry, StillRetry)
    assert retry.parameters == {"iso": "Auto", "shutterspeed": "1/60"}


def test_overexposed_image_requests_retry(tmp_path):
    plugin = BlitzWache()
    retry = plugin.acq_still_check(_img(tmp_path, "w.jpg", 252))
    assert isinstance(retry, StillRetry)
    assert retry.parameters["iso"] == "100"


def test_failure_reported_after_dark_streak_and_resolved(tmp_path):
    plugin = BlitzWache()
    black = _img(tmp_path, "b.jpg", 2)
    for _ in range(plugin._config.common.failure_after_dark_in_row):
        plugin.acq_still_check(black)
    assert plugin._failure is True
    assert plugin.get_stats().stats[0].val == "BLITZAUSFALL?"

    plugin.acq_still_check(_img(tmp_path, "n.jpg", 120))
    assert plugin._failure is False


def test_disabled_plugin_does_nothing(tmp_path):
    plugin = BlitzWache()
    plugin._config.common.enabled = False
    assert plugin.acq_still_check(_img(tmp_path, "b.jpg", 0)) is None


def test_resolve_extreme_choice():
    from photobooth.utils.cameraparameters import resolve_extreme_choice

    apertures = ["3.5", "4", "5.6", "8", "22"]
    assert resolve_extreme_choice("min", apertures) == "3.5"
    assert resolve_extreme_choice("max", apertures) == "22"
    assert resolve_extreme_choice("min", ["Auto", "100", "200"]) == "100"
    assert resolve_extreme_choice("max", ["1/4000", "1/60", "1/30", "1", "bulb"]) == "1"
    assert resolve_extreme_choice("5.6", apertures) == "5.6"
    assert resolve_extreme_choice("min", ["Auto"]) == "min"
