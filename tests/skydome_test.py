# coding=utf-8
from ladybug_geometry.geometry3d import Point3D, Mesh3D
from ladybug.compass import Compass
from ladybug.legend import LegendParameters
from ladybug.graphic import GraphicContainer

from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.visualize.skydome import SkyDome


def test_skydome_init():
    """Test init from_epw"""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw(epw_path)
    sky_dome = SkyDome(sky_from_epw)

    assert isinstance(sky_dome.legend_parameters, LegendParameters)
    assert not sky_dome.plot_irradiance
    assert isinstance(sky_dome.center_point, Point3D)
    assert sky_dome.radius == 100
    assert sky_dome.projection is None
    assert sky_dome.north == 0
    assert len(sky_dome.patch_vectors) == 145
    assert len(sky_dome.total_values) == 145
    assert len(sky_dome.direct_values) == 145
    assert len(sky_dome.diffuse_values) == 145
    assert not sky_dome.is_benefit

    dome_mesh, dome_compass, graphic, dome_title, values = sky_dome.draw()

    assert isinstance(dome_mesh, Mesh3D)
    assert isinstance(dome_compass, Compass)
    assert isinstance(graphic, GraphicContainer)
    assert isinstance(dome_title, str)

    hoys = list(range(24))
    sky_from_epw = SkyMatrix.from_epw(epw_path, hoys, 20, True, 0.25)
    sky_dome = SkyDome(sky_from_epw)

    assert sky_dome.north == 20
    assert len(sky_dome.patch_vectors) == 577
    assert len(sky_dome.total_values) == 577
    assert len(sky_dome.direct_values) == 577
    assert len(sky_dome.diffuse_values) == 577


def test_skydome_benefit():
    """Test int from_epw_benefit"""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw_benefit(epw_path)
    sky_dome = SkyDome(sky_from_epw, plot_irradiance=True)

    assert sky_dome.plot_irradiance
    assert sky_dome.is_benefit
    dome_mesh, dome_compass, graphic, dome_title, values = sky_dome.draw()

    assert isinstance(dome_mesh, Mesh3D)
    assert isinstance(dome_compass, Compass)
    assert isinstance(graphic, GraphicContainer)
    assert isinstance(dome_title, str)
