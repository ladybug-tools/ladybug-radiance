"""Class for visualizing sky matrices on a dome."""
from __future__ import division
import math

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.mesh import Mesh3D

from ladybug.datatype.energyintensity import Radiation
from ladybug.datatype.energyflux import Irradiance
from ladybug.viewsphere import view_sphere
from ladybug.compass import Compass
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters
from ladybug.color import Colorset


class SkyDome(object):
    """Visualize a sky matrix as a colored dome, subdivided into patches.

    Args:
        sky_matrix: A SkyMatrix object, which describes the radiation coming
            from the various patches of the sky.
        legend_parameters: An optional LegendParameter object to change the display
            of the sky dome. If None, some default legend parameters will be
            used. (Default: None).
        plot_irradiance: Boolean to note whether the sky dome should be plotted with
            units of total Radiation (kWh/m2) [False] or with units of average
            Irradiance (W/m2) [True]. (Default: False).
        center_point: A point for the center of the dome. (Default: (0, 0, 0)).
        radius: A number to set the radius of the sky dome. (Default: 100).
        projection: Optional text for the name of a projection to use from the sky
            dome hemisphere to the 2D plane. If None, a 3D sky dome will be drawn
            instead of a 2D one. (Default: None) Choose from the following.

                * Orthographic
                * Stereographic

    Properties:
        * legend_parameters
        * plot_irradiance
        * center_point
        * radius
        * projection
        * north
        * patch_vectors
        * total_values
        * direct_values
        * diffuse_values
        * metadata
        * is_benefit
    """
    __slots__ = (
        '_north', '_total_values', '_direct_values', '_diffuse_values',
        '_metadata', '_is_benefit', '_legend_parameters', '_plot_irradiance',
        '_center_point', '_radius', '_projection')

    PROJECTIONS = ('Orthographic', 'Stereographic')

    def __init__(self, sky_matrix, legend_parameters=None, plot_irradiance=False,
                 center_point=Point3D(0, 0, 0), radius=100, projection=None):
        """Initialize SkyDome."""
        # deconstruct the sky matrix and derive key data from it
        metadata, direct, diffuse = sky_matrix.data
        self._north = metadata[0]  # first item is the north angle
        self._plot_irradiance = bool(plot_irradiance)
        if not plot_irradiance:
            self._direct_values = direct
            self._diffuse_values = diffuse
        else:
            factor = 1000 / sky_matrix.wea_duration \
                if hasattr(sky_matrix, 'wea_duration') else \
                1000 / (((metadata[3] - metadata[2]).total_seconds() / 3600) + 1)
            self._direct_values = tuple(v * factor for v in direct)
            self._diffuse_values = tuple(v * factor for v in diffuse)
        zip_obj = zip(self._direct_values, self._diffuse_values)
        self._total_values = tuple(dr + df for dr, df in zip_obj)
        self._metadata = metadata

        # override the legend default min and max to make sense for domes
        if legend_parameters is not None:
            assert isinstance(legend_parameters, LegendParameters), \
                'Expected LegendParameters. Got {}.'.format(type(legend_parameters))
            l_par = legend_parameters.duplicate()
        else:
            l_par = LegendParameters()
        if hasattr(sky_matrix, 'benefit_matrix') and \
                sky_matrix.benefit_matrix is not None:
            if l_par.min is None:
                l_par.min = min((min(self._total_values), -max(self._total_values)))
            if l_par.max is None:
                l_par.max = max((-min(self._total_values), max(self._total_values)))
            if l_par.are_colors_default:
                l_par.colors = reversed(Colorset.benefit_harm())
            self._is_benefit = True
        else:
            if l_par.min is None:
                l_par.min = 0
            if l_par.max is None:
                l_par.max = max(self._total_values)
            self._is_benefit = False
        self._legend_parameters = l_par

        # process the geometry parameters of the dome
        assert isinstance(center_point, Point3D), 'Expected Point3D for dome center. ' \
            'Got {}.'.format(type(center_point))
        self._center_point = center_point
        assert isinstance(radius, (float, int)), 'Expected number for radius. ' \
            'Got {}.'.format(type(radius))
        assert radius > 0, \
            'Dome radius must be greater than zero. Got {}.'.format(radius)
        self._radius = radius
        if projection is not None:
            assert projection in self.PROJECTIONS, 'Projection "{}" is not recognized.' \
                ' Choose from: {}.'.format(projection, self.PROJECTIONS)
        self._projection = projection

    @property
    def legend_parameters(self):
        """Get the legend parameters assigned to this sky dome object."""
        return self._legend_parameters

    @property
    def plot_irradiance(self):
        """Get a boolean for whether the sky dome values are for irradiance in (W/m2)."""
        return self._plot_irradiance

    @property
    def center_point(self):
        """Get a Point3D for the center of the dome."""
        return self._center_point

    @property
    def radius(self):
        """Get a number for the radius of the dome."""
        return self._radius

    @property
    def projection(self):
        """Get text for the projection of the dome."""
        return self._projection

    @property
    def north(self):
        """Get a number north direction."""
        return self._north

    @property
    def patch_vectors(self):
        """Get a list of vectors for each of the patches of the sky dome.

        All vectors are unit vectors and point from the center towards each
        of the patches. They can be used to construct visualizations of the
        rays used to perform radiation analysis.
        """
        return view_sphere.tregenza_dome_vectors if len(self._total_values) == 145 \
            else view_sphere.reinhart_dome_vectors

    @property
    def total_values(self):
        """Get a tuple of values for the total radiation/irradiance of each patch."""
        return self._total_values

    @property
    def direct_values(self):
        """Get a tuple of values for the direct radiation/irradiance of each patch."""
        return self._direct_values

    @property
    def diffuse_values(self):
        """Get a tuple of values for the diffuse radiation/irradiance of each patch."""
        return self._diffuse_values

    @property
    def metadata(self):
        """Get a tuple of information about the metadata assigned to the sky dome."""
        return self._metadata

    @property
    def is_benefit(self):
        """Boolean to note whether the sky matrix includes benefit information."""
        return self._is_benefit

    def draw(self, rad_type='total', center=None):
        """Draw a dome mesh, compass, graphic/legend, and title for the sky dome.

        Args:
            rad_type: Text for the type of radiation to use. Choose from total, direct,
                diffuse. (Default: total).
            center: A Point3D to override the center of the sky dome. This is useful
                when rendering all of the sky components together and one dome should
                not be on top of another. If None, the center point assigned to the
                object instance is used. (Default: None).

        Returns:
            dome_mesh: A colored Mesh3D for the dome.
            dome_compass: A ladybug Compass object for the dome.
            graphic: A GraphicContainer for the colored dome mesh, indicating the
                legend and title location for the dome.
            dome_title: Text for the title of the dome.
            values: A list of radiation values that align with the dome_mesh faces.
        """
        # get the dome data to be plotted
        if rad_type.lower() == 'total':
            dome_data = self.total_values
        elif rad_type.lower() == 'direct':
            dome_data = self.direct_values
        elif rad_type.lower() == 'diffuse':
            dome_data = self.diffuse_values
        else:
            raise ValueError('Radiation type "{}" not recognized.'.format(rad_type))

        # create the dome mesh and ensure patch values align with mesh faces
        if len(dome_data) == 145:  # tregenza sky
            dome_mesh = view_sphere.tregenza_dome_mesh_high_res.scale(self.radius)
            values = []  # high res dome has 3 x 3 faces per patch; we must convert
            tot_i = 0  # track the total number of patches converted
            for patch_i in view_sphere.TREGENZA_PATCHES_PER_ROW:
                row_vals = []
                for val in dome_data[tot_i:tot_i + patch_i]:
                    row_vals.extend([val] * 3)
                for i in range(3):
                    values.extend(row_vals)
                tot_i += patch_i
            values = values + [dome_data[-1]] * 18  # last patch has triangular faces
        else:  # reinhart sky
            dome_mesh = view_sphere.reinhart_dome_mesh.scale(self.radius)
            values = list(dome_data) + [dome_data[-1]] * 11  # triangular last patches

        # move and/or rotate the mesh as needed
        if self.north != 0:
            dome_mesh = dome_mesh.rotate_xy(math.radians(self.north), Point3D())
        center = self.center_point if center is None else center
        if center != Point3D():
            dome_mesh = dome_mesh.move(Vector3D(center.x, center.y, center.z))

        # project the mesh if requested
        if self.projection is not None:
            if self.projection.title() == 'Orthographic':
                pts = (Compass.point3d_to_orthographic(pt) for pt in dome_mesh.vertices)
            elif self.projection.title() == 'Stereographic':
                pts = (Compass.point3d_to_stereographic(pt, self.radius, center)
                       for pt in dome_mesh.vertices)
            pts3d = tuple(Point3D(pt.x, pt.y, center.z) for pt in pts)
            dome_mesh = Mesh3D(pts3d, dome_mesh.faces)

        # output the dome visualization, including graphic and compass
        move_fac = self.radius * 1.15
        min_pt = center.move(Vector3D(-move_fac, -move_fac, 0))
        max_pt = center.move(Vector3D(move_fac, move_fac, 0))
        if self.plot_irradiance:
            d_type, unit, typ_str = Irradiance(), 'W/m2', 'Irradiance'
        else:
            d_type, unit, typ_str = Radiation(), 'kWh/m2', 'Radiation'
        graphic = GraphicContainer(
            values, min_pt, max_pt, self.legend_parameters, d_type, unit)
        dome_mesh.colors = graphic.value_colors
        dome_compass = Compass(self.radius, Point2D(center.x, center.y), self.north)

        # construct a title from the metadata
        st, end = self.metadata[2], self.metadata[3]
        time_str = '{} - {}'.format(st, end) if st != end else st
        if self.is_benefit:
            typ_str = '{} Benefit/Harm'.format(typ_str)
        dome_title = '{} {}\n{}\n{}'.format(
            rad_type.title(), typ_str, time_str,
            '\n'.join([dat for dat in self.metadata[4:]]))

        return dome_mesh, dome_compass, graphic, dome_title, values

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __len__(self):
        return len(self._total_values)

    def __getitem__(self, key):
        return self._total_values[key], self._direct_values[key], \
            self._diffuse_values[key]

    def __iter__(self):
        return zip(self._total_values, self._direct_values, self._diffuse_values)

    def __repr__(self):
        """Sky Dome object representation."""
        return 'SkyDome [{} patches]'.format(len(self._total_values))
