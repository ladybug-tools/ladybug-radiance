# coding=utf-8
from ladybug_radiance.config import folders


def test_radiance_path():
    """Test that the Radiance path exists."""
    assert folders.radiance_path is not None
