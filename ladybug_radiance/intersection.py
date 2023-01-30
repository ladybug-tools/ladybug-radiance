"""Function to compute the intersection between vectors and points."""
from __future__ import division
import os
import subprocess
import tempfile
import math

from ladybug_geometry.geometry3d import Face3D, Mesh3D
from ladybug.futil import write_to_file_by_name
from ladybug.viewsphere import view_sphere

from .config import folders

if folders.radbin_path is not None:
    OCONV_EXE = os.path.join(folders.radbin_path, 'oconv.exe') if \
        os.name == 'nt' else os.path.join(folders.radbin_path, 'oconv')
    RCONTRIB_EXE = os.path.join(folders.radbin_path, 'rcontrib.exe') if \
        os.name == 'nt' else os.path.join(folders.radbin_path, 'rcontrib')
else:
    OCONV_EXE, RCONTRIB_EXE = None, None
BLACK = 'void plastic black 0 0 5 0.0 0.0 0.0 0.0 0.0'


def intersection_matrix(vectors, points, normals, context_geometry,
                        offset_distance=0, numericalize=False, sim_folder=None):
    """Compute the intersection matrix between vectors and points.

    Args:
        vectors: A list of ladybug geometry Vector3D which will be projected from
            the points of the study_mesh through the context_geometry.
        points: A list of ladybug geometry Point3D representing the sensors
            to be studied.
        normals: A list of ladybug geometry Vector3D that matches the length of
            the points list and indicate the normal direction of each point.
            THESE VECTORS MUST BE NORMALIZED.
        context_geometry: A list of ladybug geometry Face3D and/or Mesh3D that
            can block the vectors projected from the test points.
        offset_distance: An optional number to offset the sensor points before
            the vectors are cast through the context_geometry. (Default: 0).
        numericalize: A boolean to note whether the output matrix should contain
            numbers representing the cosine of the angle between the normal and
            each vector or it should simply be a matrix of booleans for whether
            the vector is seen by the surface (True) or not (False). Numbers
            can be useful for computing radiation and irradiance while the booleans
            are more helpful for direct sun and view studies. (Default: False).
        sim_folder: An optional path to a folder where the simulation files
            will be written. If None, a temporary directory will be
            used. (Default: None).

    Returns:
        A lists of lists, which can be used to account for context shade surrounding
        visualizations or geometry. The matrix will have a length equal to the points
        (and normals). Each sub-list consists of booleans and has a length equal to
        the number of vectors. True indicates that a certain patch is seen and False
        indicates that the match is blocked.
    """
    # set a default sim folder if None is specified
    if sim_folder is None:
        sim_folder = tempfile.gettempdir()
    # account for the offset distance
    if offset_distance != 0:
        points = [pt.move(vec * offset_distance) for pt, vec in zip(points, normals)]

    # write the geometry to .rad files
    geo_strs = [BLACK]
    base_geo = 'black polygon {} 0 0 {} {}'
    for i, geo in enumerate(context_geometry):
        if isinstance(geo, Face3D):
            coords = tuple(str(v) for pt in geo.vertices for v in pt.to_array())
            poly_id = 'poly_{}'.format(i)
            geo_str = base_geo.format(poly_id, len(coords), ' '.join(coords))
            geo_strs.append(geo_str)
        elif isinstance(geo, Mesh3D):
            for fi, f_geo in enumerate(geo.face_vertices):
                coords = tuple(str(v) for pt in f_geo for v in pt.to_array())
                poly_id = 'poly_{}_{}'.format(i, fi)
                geo_str = base_geo.format(poly_id, len(coords), ' '.join(coords))
                geo_strs.append(geo_str)
    scene_file = 'geometry.rad'
    write_to_file_by_name(sim_folder, scene_file, '\n'.join(geo_strs))

    # write the vectors to a file
    vec_mod = 'void light {} 0 0 3 1.0 1.0 1.0'
    base_vec = '{} source {} 0 0 4 {} 0.533'
    vec_strs, vec_mods = [], []
    for i, vec in enumerate(vectors):
        mod_id = 'vec_light{}'.format(i)
        source_id = 'vec_{}'.format(i)
        vec_mods.append(mod_id)
        vec_strs.append(vec_mod.format(mod_id))
        dir_coords = ' '.join(str(v) for v in vec.to_array())
        vec_str = base_vec.format(mod_id, source_id, dir_coords)
        vec_strs.append(vec_str)
    vec_file, vec_mod_file = 'vectors.rad', 'vectors.mod'
    write_to_file_by_name(sim_folder, vec_file, '\n'.join(vec_strs))
    write_to_file_by_name(sim_folder, vec_mod_file, '\n'.join(vec_mods))

    # create the .pts file
    sensors = []
    for pt, vec in zip(points, normals):
        sen_str = '%s %s' % (' '.join(str(v) for v in pt), ' '.join(str(v) for v in vec))
        sensors.append(sen_str)
    pts_file = 'sensors.pts'
    write_to_file_by_name(sim_folder, pts_file, '\n'.join(sensors))

    # get the environment variables and update the current working directory
    assert OCONV_EXE is not None, 'No Radiance installation was found.'
    g_env = os.environ.copy()
    if folders.env:
        for k, v in folders.env.items():
            if k.strip().upper() == 'PATH':
                g_env['PATH'] = os.pathsep.join((v, g_env['PATH']))
            else:
                g_env[k] = v
    cur_dir = os.getcwd()
    os.chdir(sim_folder)

    # create the octree
    scene_oct = 'scene.oct'
    cmd = '"{}" "{}" "{}" > "{}"'.format(OCONV_EXE, vec_file, scene_file, scene_oct)
    cmd = cmd.replace('\\', '/')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, env=g_env)
    process.communicate()

    # run the ray tracing command
    output_mtx = 'results.mtx'
    rad_par = '-V- -aa 0.0 -y {} -I -faf -ab 0 -dc 1.0 -dt 0.0 -dj 0.0 -dr 0 -M "{}"'
    rc_options = rad_par.format(
        len(points), os.path.join(os.path.abspath(sim_folder), vec_mod_file))
    cmd = '"{}" {} "{}" < "{}"'.format(RCONTRIB_EXE, rc_options, scene_oct, pts_file)
    cmd = '{} | rmtxop -fa - -c 14713 0 0 | getinfo -  > {}'.format(cmd, output_mtx)
    cmd = cmd.replace('\\', '/')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, env=g_env)
    process.communicate()

    # put back the current working directory and load the intersection matrix
    os.chdir(cur_dir)
    int_mtx = []
    with open(os.path.join(sim_folder, output_mtx), 'r') as rf:
        if numericalize:
            for row in rf:
                int_mtx.append([float(v) for v in row.split()])
        else:
            for row in rf:
                int_mtx.append([bool(float(v)) for v in row.split()])
    return int_mtx


def sky_intersection_matrix(sky_matrix, points, normals, context_geometry,
                            offset_distance=0, numericalize=False, sim_folder=None):
    """Compute the intersection matrix between a sky matrix through points.

    Args:
        sky_matrix: A SkyMatrix object, which provides the vectors to be projected
            from the points through the context_geometry.
        points: A list of ladybug geometry Point3D representing the sensors
            to be studied.
        normals: A list of ladybug geometry Vector3D that matches the length of
            the points list and indicate the normal direction of each point.
        context_geometry: A list of ladybug geometry Face3D that can block the
            vectors projected from the test points.
        offset_distance: An optional number to offset the sensor points before
            the vectors are cast through the context_geometry. (Default: 0).
        numericalize: A boolean to note whether the output matrix should contain
            numbers representing the cosine of the angle between the normal and
            each vector or it should simply be a matrix of booleans for whether
            the vector is seen by the surface (True) or not (False). Numbers
            can be useful for computing radiation and irradiance while the booleans
            are more helpful for direct sun and view studies. (Default: False).
        sim_folder: An optional path to a folder where the simulation files
            will be written. If None, a temporary directory will be
            used. (Default: None).

    Returns:
        A lists of lists, which can be used to account for context shade surrounding
        visualizations or geometry. The matrix will have a length equal to the points
        (and normals). Each sub-list consists of booleans and has a length equal
        to the number of sky patches times 2 (indicating sky patches and ground patches).
        True indicates that a certain patch is seen and False indicates that the
        match is blocked.
    """
    # process the sky into an acceptable format
    lb_vecs = view_sphere.reinhart_dome_vectors if sky_matrix.high_density \
        else view_sphere.tregenza_dome_vectors
    if sky_matrix.north != 0:
        north_angle = math.radians(sky_matrix.north)
        lb_vecs = tuple(vec.rotate_xy(north_angle) for vec in lb_vecs)
    lb_grnd_vecs = tuple(vec.reverse() for vec in lb_vecs)
    vectors = lb_vecs + lb_grnd_vecs
    # compute the intersection matrix
    return intersection_matrix(
        vectors, points, normals, context_geometry,
        offset_distance, numericalize, sim_folder)
