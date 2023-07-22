"""Class for visualizing incident radiation (or irradiance) falling onto a mesh."""
from __future__ import division

from ladybug_geometry.bounding import bounding_box
from ladybug_geometry.geometry3d import Mesh3D, Face3D
from ladybug.datatype.energyintensity import Radiation
from ladybug.datatype.energyflux import Irradiance
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters
from ladybug.color import Colorset

from ..intersection import sky_intersection_matrix


class RadiationStudy(object):
    """Visualize the incident radiation (or irradiance) falling onto a study_mesh.

    Such studies of incident radiation can be used to approximate the energy that can
    be collected from photovoltaic or solar thermal systems. They are also useful
    for evaluating the impact of a building's orientation on both energy use and the
    size/cost of cooling systems. For studies of photovoltaic potential or building
    energy use impact, a sky matrix from EPW radiation should be used. For studies
    of cooling system size/cost, a sky matrix derived from the STAT file's clear sky
    radiation should be used.

    Not that no reflections of solar energy are included in the analysis performed by
    this class. Ground reflected irradiance is crudely accounted for by means of an
    emissive "ground hemisphere," which is like the sky dome hemisphere and is derived
    from the ground reflectance that is associated with the connected sky_matrix. This
    means that including geometry that represents the ground surface will effectively
    block such crude ground reflection.

    Args:
        sky_matrix: A SkyMatrix object, which describes the radiation coming
            from the various patches of the sky.
        study_mesh: A ladybug geometry Mesh3D, which represents the geometry on
            which the incident radiation is being studied.
        context_geometry: A list of ladybug geometry Face3D and/or Mesh3D that
            can block the view to the sky and ground.
        offset_distance: An optional number to offset the sensor points before
            the vectors are cast through the context_geometry. (Default: 0).
        by_vertex: A boolean to indicate whether the study should be run for
            each vertex of the study_mesh (True) or each face of the study
            mesh (False). (Default: False).
        sim_folder: An optional path to a folder where the simulation files will
            be written. If None, a temporary directory will be used. (Default: None).

    Properties:
        * sky_matrix
        * study_mesh
        * context_geometry
        * offset_distance
        * by_vertex
        * sim_folder
        * study_points
        * study_normals
        * intersection_matrix
        * radiation_values
        * irradiance_values
        * metadata
        * is_benefit
    """
    __slots__ = (
        '_metadata', '_is_benefit', '_sky_matrix', '_study_mesh', '_context_geometry',
        '_offset_distance', '_by_vertex', '_study_points', '_study_normals',
        '_sim_folder', '_intersection_matrix', '_radiation_values')

    def __init__(self, sky_matrix, study_mesh, context_geometry,
                 offset_distance=0, by_vertex=False, sim_folder=None):
        """Initialize RadiationStudy."""
        # set default values, which will be overwritten when the study is run
        self._offset_distance = float(offset_distance)
        self._by_vertex = bool(by_vertex)
        # set the key properties of the object
        self.sky_matrix = sky_matrix
        self.study_mesh = study_mesh
        self.context_geometry = context_geometry
        self.sim_folder = sim_folder
        # set default values, which will be overwritten when the study is run
        self._intersection_matrix = None
        self._radiation_values = None

    @property
    def sky_matrix(self):
        """Get or set a SkyMatrix object for the sky used in the study."""
        return self._sky_matrix

    @sky_matrix.setter
    def sky_matrix(self, value):
        self._sky_matrix = value
        self._metadata, direct, diffuse = value.data
        self._is_benefit = True if hasattr(value, 'benefit_matrix') and \
            value.benefit_matrix is not None else False
        self._radiation_values = None

    @property
    def study_mesh(self):
        """Get or set a SkyMatrix object for the sky used in the study."""
        return self._study_mesh

    @study_mesh.setter
    def study_mesh(self, value):
        assert isinstance(value, Mesh3D), 'Expected Mesh3D for RadiationStudy ' \
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
                'RadiationStudy context_geometry. Got {}.'.format(type(geo))
        self._context_geometry = value
        self._intersection_matrix = None
        self._radiation_values = None

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
    def radiation_values(self):
        """Get a list of values for the radiation results of the study in kWh/m2."""
        if self._radiation_values is None:
            self.compute()
        return self._radiation_values

    @property
    def irradiance_values(self):
        """Get a list of values for the irradiance results of the study in W/m2."""
        factor = 1000 / self.sky_matrix.wea_duration \
            if hasattr(self.sky_matrix, 'wea_duration') else \
            1000 / (((self.metadata[3] - self.metadata[2]).total_seconds() / 3600) + 1)
        return [r * factor for r in self.radiation_values]

    @property
    def metadata(self):
        """Get a tuple of information about the metadata assigned to the study."""
        return self._metadata

    @property
    def is_benefit(self):
        """Get a boolean to note whether the sky matrix includes benefit information."""
        return self._is_benefit

    def total_radiation(self, conversion_to_meters=1):
        """Get a number for the total radiation of the study in kWh.

        Note that, when the study is run by_vertex, it is assumed that all vertices
        represent the same area.

        Args:
            conversion_to_meters: A number (typically less than 1) to note the
                conversion factor from the mesh area to square meters. This should
                be a conversion in square units and not just linear units. (Default: 1).
        """
        if self.by_vertex:
            full_area = self.study_mesh.area * conversion_to_meters
            total = sum(self.radiation_values) / full_area
        else:
            total = 0
            for rad, area in zip(self.radiation_values, self._study_mesh.face_areas):
                total += rad * area * conversion_to_meters
        return total

    def compute(self):
        """Compute the radiation values of the study.

        Note that this method is automatically called under the hood when accessing
        any results of the study and these results have not already been computed.
        So using this method is not necessary to correctly use this class. However,
        explicitly calling this method can help control when the time consuming
        part of the study runs, which is particularly helpful for larger studies.
        """
        # compute the intersection matrix
        if self._intersection_matrix is None:
            self._compute_intersection_matrix()
        # get the total radiation from the sky matrix
        mtx = self.sky_matrix.data
        sky_rad = [dir_rad + dif_rad for dir_rad, dif_rad in zip(mtx[1], mtx[2])]
        ground_value = (sum(sky_rad) / len(sky_rad)) * self.sky_matrix.ground_reflectance
        ground_rad = [ground_value] * len(sky_rad)
        all_rad = sky_rad + ground_rad
        # multiply the intersection and sky matrices
        self._radiation_values = [
            sum(r * w for r, w in zip(pt_rel, all_rad))
            for pt_rel in self._intersection_matrix
        ]

    def draw(self, legend_parameters=None, plot_irradiance=False):
        """Draw a colored study_mesh, compass, graphic/legend, and title.

        Args:
            legend_parameters: An optional LegendParameter object to change the display
                of the radiation study. If None, default legend parameters will be
                used. (Default: None).
            plot_irradiance: Boolean to note whether the results should be plotted
                with units of total Radiation (kWh/m2) [False] or with units of average
                Irradiance (W/m2) [True]. (Default: False).

        Returns:
            colored_mesh: A colored Mesh3D for the study results.
            graphic: A GraphicContainer for the colored mesh, indicating the
                legend and title location for the study.
            title: Text for the title of the study.
        """
        # get the radiation data
        if plot_irradiance:
            d_type, unit, title = Irradiance(), 'W/m2', 'Incident Irradiance'
            rad_data = self.irradiance_values
        else:
            d_type, unit, title = Radiation(), 'kWh/m2', 'Incident Radiation'
            rad_data = self.radiation_values
        if self.is_benefit:
            title = '{} Benefit/Harm'.format(title)

        # override the legend default min and max to make sense for the radiation study
        if legend_parameters is not None:
            assert isinstance(legend_parameters, LegendParameters), \
                'Expected LegendParameters. Got {}.'.format(type(legend_parameters))
            l_par = legend_parameters.duplicate()
        else:
            l_par = LegendParameters()
        if self.is_benefit:
            if l_par.min is None:
                l_par.min = min((min(rad_data), -max(rad_data)))
            if l_par.max is None:
                l_par.max = max((-min(rad_data), max(rad_data)))
            if l_par.are_colors_default:
                l_par.colors = reversed(Colorset.benefit_harm())
        else:
            if l_par.min is None:
                l_par.min = 0
            if l_par.max is None:
                l_par.max = max(rad_data)

        # create the mesh, graphic container, and title
        min_pt, max_pt = bounding_box((self.study_mesh,) + self.context_geometry)
        graphic = GraphicContainer(
            rad_data, min_pt, max_pt, l_par, d_type, unit)
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
        self._radiation_values = None

    def _compute_intersection_matrix(self):
        """Compute intersection matrix."""
        self._intersection_matrix = sky_intersection_matrix(
            self.sky_matrix, self.study_points, self.study_normals,
            self.context_geometry, self.offset_distance, numericalize=True,
            sim_folder=self.sim_folder)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __len__(self):
        return len(self.study_points)

    def __repr__(self):
        """Radiation Study object representation."""
        return 'RadiationStudy [{} values]'.format(len(self.study_points))
