# coding=utf-8
from ladybug.epw import EPW

from ladybug_radiance.skymatrix import SkyMatrix


def test_from_epw():
    """Test init from_epw"""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw(epw_path)

    assert len(sky_from_epw.wea) == 8760
    assert sky_from_epw.north == 0
    assert not sky_from_epw.high_density
    assert sky_from_epw.ground_reflectance == 0.2
    assert len(sky_from_epw) == 145
    for direct, diffuse in sky_from_epw:
        assert direct >= 0
        assert diffuse >= 0
    assert len(sky_from_epw.data) == 3
    assert sky_from_epw.benefit_matrix is None

    hoys = list(range(24))
    sky_from_epw = SkyMatrix.from_epw(epw_path, hoys, 20, True, 0.25)

    assert len(sky_from_epw.wea) == 24
    assert sky_from_epw.north == 20
    assert sky_from_epw.high_density
    assert sky_from_epw.ground_reflectance == 0.25
    assert len(sky_from_epw) == 577


def test_from_epw_benefit():
    """Test int from_epw_benefit"""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw_benefit(epw_path)

    assert len(sky_from_epw.wea) == 8760
    assert sky_from_epw.north == 0
    assert not sky_from_epw.high_density
    assert sky_from_epw.ground_reflectance == 0.2
    assert len(sky_from_epw) == 145
    assert len(sky_from_epw.data) == 3
    assert sky_from_epw.benefit_matrix is not None

    hoys = list(range(24))
    sky_from_epw = SkyMatrix.from_epw_benefit(epw_path, 18, 2, hoys, 20, True, 0.25)

    assert len(sky_from_epw.wea) == 24
    assert sky_from_epw.north == 20
    assert sky_from_epw.high_density
    assert sky_from_epw.ground_reflectance == 0.25
    assert len(sky_from_epw) == 577
    for direct, diffuse in sky_from_epw:
        assert direct >= 0
        assert diffuse >= 0


def test_from_stat():
    """Test init from_stat"""
    stat_path = './tests/assets/stat/chicago.stat'
    sky_from_stat = SkyMatrix.from_stat(stat_path)

    assert len(sky_from_stat.wea) == 8760
    assert sky_from_stat.north == 0
    assert not sky_from_stat.high_density
    assert sky_from_stat.ground_reflectance == 0.2
    assert len(sky_from_stat) == 145
    for direct, diffuse in sky_from_stat:
        assert direct >= 0
        assert diffuse >= 0
    assert len(sky_from_stat.data) == 3
    assert sky_from_stat.benefit_matrix is None

    hoys = list(range(24))
    sky_from_stat = SkyMatrix.from_stat(stat_path, hoys, 20, True, 0.25)

    assert len(sky_from_stat.wea) == 24
    assert sky_from_stat.north == 20
    assert sky_from_stat.high_density
    assert sky_from_stat.ground_reflectance == 0.25
    assert len(sky_from_stat) == 577
    for direct, diffuse in sky_from_stat:
        assert direct >= 0
        assert diffuse >= 0


def test_from_ashrae_clear_sky():
    """Test int from_ashrae_clear_sky"""
    epw_path = './tests/assets/epw/chicago.epw'
    epw_obj = EPW(epw_path)
    clear_sky = SkyMatrix.from_ashrae_clear_sky(epw_obj.location)

    assert len(clear_sky.wea) == 8760
    assert clear_sky.north == 0
    assert not clear_sky.high_density
    assert clear_sky.ground_reflectance == 0.2
    assert len(clear_sky) == 145
    for direct, diffuse in clear_sky:
        assert direct >= 0
        assert diffuse >= 0
    assert len(clear_sky.data) == 3
    assert clear_sky.benefit_matrix is None

    hoys = list(range(24))
    clear_sky = SkyMatrix.from_ashrae_clear_sky(
        epw_obj.location, 1, hoys, 20, True, 0.25)

    assert len(clear_sky.wea) == 24
    assert clear_sky.north == 20
    assert clear_sky.high_density
    assert clear_sky.ground_reflectance == 0.25
    assert len(clear_sky) == 577
    for direct, diffuse in clear_sky:
        assert direct >= 0
        assert diffuse >= 0
