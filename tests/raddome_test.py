# coding=utf-8
from ladybug_geometry.geometry3d import Point3D, Mesh3D
from ladybug.compass import Compass
from ladybug.legend import LegendParameters
from ladybug.graphic import GraphicContainer

from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.visualize.raddome import RadiationDome


def test_raddome_init():
    """Test init from_epw"""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw(epw_path)
    rad_dome = RadiationDome(sky_from_epw)

    assert rad_dome.azimuth_count == 72
    assert rad_dome.altitude_count == 18
    assert isinstance(rad_dome.legend_parameters, LegendParameters)
    assert not rad_dome.plot_irradiance
    assert isinstance(rad_dome.center_point, Point3D)
    assert rad_dome.radius == 100
    assert rad_dome.projection is None
    assert rad_dome.north == 0
    assert len(rad_dome.direction_vectors) == 72 * 18 + 1
    assert len(rad_dome.total_values) == 72 * 18 + 1
    assert len(rad_dome.direct_values) == 72 * 18 + 1
    assert len(rad_dome.diffuse_values) == 72 * 18 + 1
    assert not rad_dome.is_benefit

    dome_mesh, compass, graphic, dome_title = rad_dome.draw()

    assert isinstance(dome_mesh, Mesh3D)
    assert isinstance(compass, Compass)
    assert isinstance(graphic, GraphicContainer)
    assert isinstance(dome_title, str)
