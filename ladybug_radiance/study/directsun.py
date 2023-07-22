"""Class for visualizing the direct sun hours falling onto a mesh."""
from __future__ import division

from ladybug_geometry.bounding import bounding_box
from ladybug_geometry.geometry3d import Vector3D, Mesh3D, Face3D
from ladybug.datatype.time import Time
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters
from ladybug.color import Colorset

from ..intersection import intersection_matrix


class DirectSunStudy(object):
    """Visualize the direct sun hours falling onto a study_mesh.

    Such direct sun calculations can be used for shadow studies of outdoor
    environments or can be used to estimate glare potential from direct sun
    on the indoors.

    Args:
        vectors: Sun vectors, which will be used to determine the number of hours
            of direct sun received by the test study_mesh. These vectors can be
            computed using the ladybug.sunpath module.
        study_mesh: A ladybug geometry Mesh3D, which represents the geometry on
            which the direct sun is being studied.
        context_geometry: A list of ladybug geometry Face3D and/or Mesh3D that
            can block the sun.
        timestep: A positive integer for the number of timesteps per hour at
            which the sun vectors were generated. This is used to correctly
            interpret the time duration represented by each of the input sun
            vectors. (Default: 1 for 1 vector per hour).
        offset_distance: An optional number to offset the sensor points before
            the vectors are cast through the context_geometry. (Default: 0).
        by_vertex: A boolean to indicate whether the study should be run for
            each vertex of the study_mesh (True) or each face of the study
            mesh (False). (Default: False).
        sim_folder: An optional path to a folder where the simulation files will
            be written. If None, a temporary directory will be used. (Default: None).

    Properties:
        * vectors
        * timestep
        * study_mesh
        * context_geometry
        * offset_distance
        * by_vertex
        * sim_folder
        * study_points
        * study_normals
        * intersection_matrix
        * direct_sun_hours
    """
    __slots__ = (
        '_vectors', '_timestep', '_study_mesh', '_context_geometry',
        '_offset_distance', '_by_vertex', '_study_points', '_study_normals',
        '_sim_folder', '_intersection_matrix', '_direct_sun_hours')

    def __init__(self, vectors, study_mesh, context_geometry, timestep=1,
                 offset_distance=0, by_vertex=False, sim_folder=None):
        """Initialize RadiationDome."""
        # set default values, which will be overwritten when the study is run
        self._offset_distance = float(offset_distance)
        self._by_vertex = bool(by_vertex)
        # set the key properties of the object
        self.vectors = vectors
        self.timestep = timestep
        self.study_mesh = study_mesh
        self.context_geometry = context_geometry
        self.sim_folder = sim_folder
        # set default values, which will be overwritten when the study is run
        self._intersection_matrix = None
        self._direct_sun_hours = None

    @property
    def vectors(self):
        """Get or set a list of vectors for the sun vectors used in the study."""
        return self._vectors

    @vectors.setter
    def vectors(self, value):
        if not isinstance(value, tuple):
            try:
                value = tuple(value)
            except (ValueError, TypeError):
                raise ValueError('Expected tuple or list for vectors. '
                                 'Got {}.'.format(type(value)))
        for geo in value:
            assert isinstance(geo, Vector3D), 'Expected Vector3D for ' \
                'DirectSunStudy vectors. Got {}.'.format(type(geo))
        self._vectors = value
        self._intersection_matrix = None
        self._direct_sun_hours = None

    @property
    def timestep(self):
        """Get or set an integer for the timestep at which the vectors were generated."""
        return self._timestep

    @timestep.setter
    def timestep(self, value):
        self._timestep = int(value)
        assert self._timestep > 0, 'DirectSunStudy timestep must be ' \
            'greater than 0. Got {}.'.format(value)
        self._direct_sun_hours = None

    @property
    def study_mesh(self):
        """Get or set a SkyMatrix object for the sky used in the study."""
        return self._study_mesh

    @study_mesh.setter
    def study_mesh(self, value):
        assert isinstance(value, Mesh3D), 'Expected Mesh3D for DirectSunStudy ' \
            'study_mesh. Got {}.'.format(type(value))
        self._study_mesh = value
        self._reset_points()

    @property
    def context_geometry(self):
        """Get or set a tuple of Face3D and Mesh3D for the geometry that can block sun.
        """
        return self._context_geometry

    @context_geometry.setter
    def context_geometry(self, value):
        if not isinstance(value, tuple):
            try:
                value = tuple(value)
            except (ValueError, TypeError):
                raise ValueError('Expected tuple or list for context_geometry. '
                                 'Got {}.'.format(type(value)))
        for geo in value:
            assert isinstance(geo, (Face3D, Mesh3D)), 'Expected Face3D or Mesh3D for ' \
                'DirectSunStudy context_geometry. Got {}.'.format(type(geo))
        self._context_geometry = value
        self._intersection_matrix = None
        self._direct_sun_hours = None

    @property
    def offset_distance(self):
        """Get or set a number for the offset distance used in the study."""
        return self._offset_distance

    @offset_distance.setter
    def offset_distance(self, value):
        assert isinstance(value, (float, int)), \
            'Expected number for offset_distance. Got {}.'.format(type(value))
        self._offset_distance = value
        self._reset_points()

    @property
    def by_vertex(self):
        """Get or set a boolean for whether the study should be run for each vertex."""
        return self._by_vertex

    @by_vertex.setter
    def by_vertex(self, value):
        self._by_vertex = bool(value)
        self._reset_points()

    @property
    def sim_folder(self):
        """Get or set text for the path where the simulation files are written."""
        return self._sim_folder

    @sim_folder.setter
    def sim_folder(self, value):
        if value is not None:
            assert isinstance(value, str), 'Expected file path string for sim_folder. ' \
                'Got {}.'.format(type(value))
        self._sim_folder = value

    @property
    def study_points(self):
        """Get a tuple of Point3Ds for the points of the study."""
        return self._study_points

    @property
    def study_normals(self):
        """Get a tuple of Vector3Ds for the normals of the study."""
        return self._study_normals

    @property
    def intersection_matrix(self):
        """Get a list of lists for the intersection matrix computed by the study."""
        if self._intersection_matrix is None:
            self._compute_intersection_matrix()
        return self._intersection_matrix

    @property
    def direct_sun_hours(self):
        """Get a list of values for the number of hours falling on the study_mesh."""
        if self._direct_sun_hours is None:
            self.compute()
        return self._direct_sun_hours

    def compute(self):
        """Compute the direct sun hour values of the study.

        Note that this method is automatically called under the hood when accessing
        any results of the study and these results have not already been computed.
        So using this method is not necessary to correctly use this class. However,
        explicitly calling this method can help control when the time consuming
        part of the study runs, which is particularly helpful for larger studies.
        """
        # compute the intersection matrix
        if self._intersection_matrix is None:
            self._compute_intersection_matrix()
        # sum the intersection and sky matrices
        t_step = self.timestep
        self._direct_sun_hours = [
            sum(int_list) / t_step for int_list in self._intersection_matrix]

    def draw(self, legend_parameters=None):
        """Draw a colored study_mesh, compass, graphic/legend, and title.

        Args:
            legend_parameters: An optional LegendParameter object to change the display
                of the direct sun study. If None, default legend parameters will be
                used. (Default: None).

        Returns:
            colored_mesh: A colored Mesh3D for the study results.
            graphic: A GraphicContainer for the colored mesh, indicating the
                legend and title location for the study.
            title: Text for the title of the study.
        """
        # get the direct sun data
        d_type, unit, title = Time(), 'hr', 'Direct Sun Hours'
        sun_data = self.direct_sun_hours

        # override the legend colors sense for the direct sun study
        if legend_parameters is not None:
            assert isinstance(legend_parameters, LegendParameters), \
                'Expected LegendParameters. Got {}.'.format(type(legend_parameters))
            l_par = legend_parameters.duplicate()
        else:
            l_par = LegendParameters()
        if l_par.are_colors_default:
            l_par.colors = Colorset.ecotect()

        # create the mesh, graphic container, and title
        min_pt, max_pt = bounding_box((self.study_mesh,) + self.context_geometry)
        graphic = GraphicContainer(
            sun_data, min_pt, max_pt, l_par, d_type, unit)
        colored_mesh = self.study_mesh
        colored_mesh.colors = graphic.value_colors

        return colored_mesh, graphic, title

    def _reset_points(self):
        """Reset the study points and normals used in the study."""
        points = self._study_mesh.vertices if self._by_vertex else \
            self._study_mesh.face_centroids
        normals = self._study_mesh.vertex_normals if self._by_vertex else \
            self._study_mesh.face_normals
        if self._offset_distance != 0:
            points = tuple(
                pt.move(vec * self._offset_distance) for pt, vec in zip(points, normals))
        self._study_points = points
        self._study_normals = normals
        self._intersection_matrix = None
        self._direct_sun_hours = None

    def _compute_intersection_matrix(self):
        """Compute intersection matrix."""
        rev_vecs = [v.reverse() for v in self.vectors]
        self._intersection_matrix = intersection_matrix(
            rev_vecs, self.study_points, self.study_normals,
            self.context_geometry, self.offset_distance, numericalize=False,
            sim_folder=self.sim_folder)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __len__(self):
        return len(self.study_points)

    def __repr__(self):
        """Direct Sun Study object representation."""
        return 'DirectSunStudy [{} values]'.format(len(self.study_points))

