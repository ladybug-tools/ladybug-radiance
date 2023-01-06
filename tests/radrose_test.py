# coding=utf-8
from ladybug_geometry.geometry3d import Point3D, LineSegment3D, Mesh3D
from ladybug.compass import Compass
from ladybug.legend import LegendParameters
from ladybug.graphic import GraphicContainer

from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.visualize.radrose import RadiationRose


def test_radrose_init():
    """Test init from_epw"""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw(epw_path)
    rad_rose = RadiationRose(sky_from_epw)

    assert rad_rose.direction_count == 36
    assert rad_rose.tilt_angle == 0
    assert isinstance(rad_rose.legend_parameters, LegendParameters)
    assert not rad_rose.plot_irradiance
    assert isinstance(rad_rose.center_point, Point3D)
    assert rad_rose.radius == 100
    assert rad_rose.arrow_scale == 1
    assert rad_rose.north == 0
    assert len(rad_rose.direction_vectors) == 36
    assert len(rad_rose.total_values) == 36
    assert len(rad_rose.direct_values) == 36
    assert len(rad_rose.diffuse_values) == 36
    assert not rad_rose.is_benefit

    arrow_mesh, orientation_lines, compass, graphic, rose_title = rad_rose.draw()

    assert isinstance(arrow_mesh, Mesh3D)
    assert all(isinstance(lin, LineSegment3D) for lin in orientation_lines)
    assert isinstance(compass, Compass)
    assert isinstance(graphic, GraphicContainer)
    assert isinstance(rose_title, str)
