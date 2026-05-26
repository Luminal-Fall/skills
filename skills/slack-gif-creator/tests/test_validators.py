"""Tests for slack-gif-creator/core/validators.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.validators import is_slack_ready, validate_gif

PIL = pytest.importorskip("PIL", reason="Pillow not installed")
from PIL import Image


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_gif(path: Path, width: int, height: int, frames: int = 2) -> Path:
    """Create a minimal GIF file at the given path."""
    imgs = [Image.new("RGB", (width, height), color=(i * 30, 100, 200)) for i in range(frames)]
    imgs[0].save(
        path,
        save_all=True,
        append_images=imgs[1:],
        loop=0,
        duration=100,
        format="GIF",
    )
    return path


# ---------------------------------------------------------------------------
# validate_gif — emoji mode (128x128)
# ---------------------------------------------------------------------------

def test_valid_128x128_emoji_passes(tmp_path):
    gif = _make_gif(tmp_path / "emoji.gif", 128, 128)
    passes, results = validate_gif(gif, is_emoji=True, verbose=False)
    assert passes is True
    assert results["width"] == 128
    assert results["height"] == 128


def test_valid_64x64_emoji_passes(tmp_path):
    gif = _make_gif(tmp_path / "small.gif", 64, 64)
    passes, _ = validate_gif(gif, is_emoji=True, verbose=False)
    assert passes is True


def test_oversized_200x200_emoji_fails(tmp_path):
    gif = _make_gif(tmp_path / "big.gif", 200, 200)
    passes, _ = validate_gif(gif, is_emoji=True, verbose=False)
    assert passes is False


def test_non_square_128x64_emoji_fails(tmp_path):
    gif = _make_gif(tmp_path / "rect.gif", 128, 64)
    passes, _ = validate_gif(gif, is_emoji=True, verbose=False)
    assert passes is False


def test_128x128_is_optimal(tmp_path):
    gif = _make_gif(tmp_path / "emoji.gif", 128, 128)
    _, results = validate_gif(gif, is_emoji=True, verbose=False)
    assert results["optimal"] is True


def test_64x64_is_not_optimal(tmp_path):
    gif = _make_gif(tmp_path / "small.gif", 64, 64)
    _, results = validate_gif(gif, is_emoji=True, verbose=False)
    assert results["optimal"] is False


# ---------------------------------------------------------------------------
# validate_gif — message mode (non-emoji)
# ---------------------------------------------------------------------------

def test_valid_message_gif_passes(tmp_path):
    gif = _make_gif(tmp_path / "msg.gif", 480, 320)
    passes, _ = validate_gif(gif, is_emoji=False, verbose=False)
    assert passes is True


def test_extreme_aspect_ratio_message_fails(tmp_path):
    gif = _make_gif(tmp_path / "wide.gif", 1000, 100)
    passes, _ = validate_gif(gif, is_emoji=False, verbose=False)
    assert passes is False


# ---------------------------------------------------------------------------
# validate_gif — error cases
# ---------------------------------------------------------------------------

def test_nonexistent_file_returns_false():
    passes, results = validate_gif("/tmp/does_not_exist_12345.gif", verbose=False)
    assert passes is False
    assert "error" in results


def test_results_contain_expected_keys(tmp_path):
    gif = _make_gif(tmp_path / "emoji.gif", 128, 128)
    _, results = validate_gif(gif, is_emoji=True, verbose=False)
    for key in ("width", "height", "size_kb", "frame_count", "passes", "is_emoji"):
        assert key in results


def test_frame_count_correct(tmp_path):
    gif = _make_gif(tmp_path / "multi.gif", 128, 128, frames=5)
    _, results = validate_gif(gif, is_emoji=True, verbose=False)
    assert results["frame_count"] == 5


# ---------------------------------------------------------------------------
# is_slack_ready — thin wrapper
# ---------------------------------------------------------------------------

def test_is_slack_ready_returns_true_for_valid(tmp_path):
    gif = _make_gif(tmp_path / "ok.gif", 128, 128)
    assert is_slack_ready(gif, is_emoji=True, verbose=False) is True


def test_is_slack_ready_returns_false_for_invalid(tmp_path):
    gif = _make_gif(tmp_path / "bad.gif", 300, 300)
    assert is_slack_ready(gif, is_emoji=True, verbose=False) is False
