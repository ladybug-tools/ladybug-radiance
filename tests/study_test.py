# coding=utf-8
import pytest

from ladybug_geometry.geometry2d import Point2D, Mesh2D
from ladybug_geometry.geometry3d import Vector3D, Point3D, LineSegment3D, Face3D, Mesh3D
from ladybug.dt import Time
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.graphic import GraphicContainer

from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.study.radiation import RadiationStudy
from ladybug_radiance.study.directsun import DirectSunStudy


def test_radiation_study():
    """Test the RadiationStudy class."""
    epw_path = './tests/assets/epw/chicago.epw'
    sky_from_epw = SkyMatrix.from_epw(epw_path)
    mesh_2d = Mesh2D.from_grid(Point2D(-1, -1), 2, 2, 1, 1)
    mesh = Mesh3D.from_mesh2d(mesh_2d)
    context_geometry = Face3D.from_extrusion(
        LineSegment3D.from_end_points(Point3D(-2, -2, 0), Point3D(2, -2, 0)),
        Vector3D(0, 0, 2)
    )

    rad_study = RadiationStudy(sky_from_epw, mesh, [context_geometry])

    assert isinstance(rad_study.sky_matrix, SkyMatrix)
    assert isinstance(rad_study.study_mesh, Mesh3D)
    assert isinstance(rad_study.context_geometry, tuple)
    assert rad_study.offset_distance == 0
    assert not rad_study.by_vertex
    assert rad_study.sim_folder is None
    assert len(rad_study.study_points) == len(mesh.faces)
    assert len(rad_study.study_normals) == len(mesh.faces)

    int_mtx = rad_study.intersection_matrix
    assert len(int_mtx) == len(mesh.faces)
    assert len(int_mtx[0]) == 290
    assert all(isinstance(v, float) for v in int_mtx[0])
    assert not all(int_mtx[0])

    rad_values = rad_study.radiation_values
    assert all(isinstance(v, float) for v in rad_values)
    irr_values = rad_study.irradiance_values
    assert all(isinstance(v, float) for v in irr_values)
    assert rad_study.total_radiation() == pytest.approx(4584.5, rel=1e-3)

    colored_mesh, graphic, title = rad_study.draw()
    assert isinstance(colored_mesh, Mesh3D)
    assert isinstance(graphic, GraphicContainer)
    assert title == 'Incident Radiation'


def test_direct_sun_study():
    """Test the DirectSun class."""
    nyc = Location('New_York', country='USA', latitude=40.72, longitude=-74.02,
                   time_zone=-5)
    sp = Sunpath.from_location(nyc)
    suns = sp.analemma_suns(Time(12), True, True)
    sun_vecs = [s.sun_vector for s in suns]
    mesh_2d = Mesh2D.from_grid(Point2D(-1, -1), 2, 2, 1, 1)
    mesh = Mesh3D.from_mesh2d(mesh_2d)
    context_geometry = Face3D.from_extrusion(
        LineSegment3D.from_end_points(Point3D(-2, -2, 0), Point3D(2, -2, 0)),
        Vector3D(0, 0, 2)
    )
    sun_study = DirectSunStudy(sun_vecs, mesh, [context_geometry])

    assert isinstance(sun_study.vectors, tuple)
    assert isinstance(sun_study.study_mesh, Mesh3D)
    assert isinstance(sun_study.context_geometry, tuple)
    assert sun_study.offset_distance == 0
    assert not sun_study.by_vertex
    # assert sun_study.sim_folder is None
    assert len(sun_study.study_points) == len(mesh.faces)
    assert len(sun_study.study_normals) == len(mesh.faces)

    int_mtx = sun_study.intersection_matrix
    assert len(int_mtx) == len(mesh.faces)
    assert len(int_mtx[0]) == len(sun_vecs)
    assert all(isinstance(v, bool) for v in int_mtx[0])
    assert not all(int_mtx[0])

    sun_values = sun_study.direct_sun_hours
    assert all(isinstance(v, float) for v in sun_values)

    colored_mesh, graphic, title = sun_study.draw()
    assert isinstance(colored_mesh, Mesh3D)
    assert isinstance(graphic, GraphicContainer)
    assert title == 'Direct Sun Hours'
