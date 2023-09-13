# coding=utf-8
import numpy as np

from ladybug_geometry.geometry3d import Vector3D, Point3D, LineSegment3D, Face3D

from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.visualize.radrose import RadiationRose
from ladybug_radiance.intersection import sky_intersection_matrix


def test_intersection():
    """Test the intersection functions."""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw(epw_path)
    rad_rose = RadiationRose(sky_from_epw)
    points = [Point3D(0, 0, 0)] * rad_rose.direction_count
    context_geometry = Face3D.from_extrusion(
        LineSegment3D.from_end_points(Point3D(-2, -2, 0), Point3D(2, -2, 0)),
        Vector3D(0, 0, 2)
    )

    int_mtx = sky_intersection_matrix(
        sky_from_epw, points, rad_rose.direction_vectors, [context_geometry])
    assert len(int_mtx) == rad_rose.direction_count
    assert len(int_mtx[0]) == 290
    assert int_mtx.dtype == np.bool_
    assert not all(int_mtx[0])

    int_mtx = sky_intersection_matrix(
        sky_from_epw, points, rad_rose.direction_vectors, [context_geometry],
        numericalize=True)
    assert len(int_mtx) == rad_rose.direction_count
    assert len(int_mtx[0]) == 290
    assert all(isinstance(v, float) for v in int_mtx[0])
    assert sum(int_mtx[0]) != 0
