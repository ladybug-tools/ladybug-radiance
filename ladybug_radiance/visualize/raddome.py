"""Class for visualizing the impact of radiation from different directions over a dome.
"""
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


class RadiationDome(object):
    """Visualize the radiation falling from different directions over a dome.

    The Radiation Dome depicts the amount of solar energy received by all directions
    over a dome. This is useful for understanding the optimal orientation of solar
    panels and how the performance of the panel will be impacted if it's orientation
    is off from the optimal position. It can also be used to identify the optimal
    wall orientation for passive solar heating when used with skies of
    radiation harm/benefit. When used with clear sky matrices, it can identify
    the orientations that result in the highest and lowest peak cooling load.

    Args:
        sky_matrix: A SkyMatrix object, which describes the radiation coming
            from the various patches of the sky.
        intersection_matrix: An optional lists of lists, which can be used to account
            for context shade surrounding the radiation dome. The matrix should
            have a length equal to the (azimuth_count * altitude_count) + 1 and begin
            from north moving clockwise, continuing up the dome with each revolution.
            The last vector refers to a perfectly vertical orientation.
            Each sub-list should consist of booleans and have a length equal to
            the number of sky patches times 2 (indicating sky patches followed by
            ground patches). True indicates that a certain patch is seen and False
            indicates that the match is blocked. If None, the radiation dome will
            be computed assuming no obstructions. (Default: None).
        azimuth_count: An integer greater than or equal to 3, which notes the number
            of horizontal orientations to be evaluated on the dome. (Default: 72).
        altitude_count: An integer greater than or equal to 3, which notes the number
            of vertical orientations to be evaluated on the dome. (Default: 18).
        legend_parameters: An optional LegendParameter object to change the display
            of the radiation dome. If None, default legend parameters will be
            used. (Default: None).
        plot_irradiance: Boolean to note whether the radiation dome should be plotted
            with units of total Radiation (kWh/m2) [False] or with units of average
            Irradiance (W/m2) [True]. (Default: False).
        center_point: A point for the center of the dome. (Default: (0, 0, 0)).
        radius: A number to set the radius of the radiation dome. (Default: 100).
        projection: Optional text for the name of a projection to use from the sky
            dome hemisphere to the 2D plane. If None, a 3D sky dome will be drawn
            instead of a 2D one. (Default: None) Choose from the following.

                * Orthographic
                * Stereographic

    Properties:
        * azimuth_count
        * altitude_count
        * legend_parameters
        * plot_irradiance
        * center_point
        * radius
        * projection
        * north
        * direction_vectors
        * dome_mesh
        * total_values
        * direct_values
        * diffuse_values
        * metadata
        * is_benefit
    """
    __slots__ = (
        '_north', '_metadata', '_is_benefit', '_direction_vectors', '_dome_mesh',
        '_total_values', '_direct_values', '_diffuse_values',
        '_azimuth_count', '_altitude_count', '_legend_parameters', '_plot_irradiance',
        '_center_point', '_radius', '_projection')
    PROJECTIONS = ('Orthographic', 'Stereographic')

    def __init__(self, sky_matrix, intersection_matrix=None, azimuth_count=72,
                 altitude_count=18, legend_parameters=None, plot_irradiance=False,
                 center_point=Point3D(0, 0, 0), radius=100, projection=None):
        """Initialize RadiationDome."""
        # deconstruct the sky matrix and derive key data from it
        metadata, direct, diffuse = sky_matrix.data
        self._metadata = metadata
        self._north = metadata[0]  # first item is the north angle
        self._plot_irradiance = bool(plot_irradiance)
        if plot_irradiance:
            factor = 1000 / sky_matrix.wea_duration \
                if hasattr(sky_matrix, 'wea_duration') else \
                1000 / (((metadata[3] - metadata[2]).total_seconds() / 3600) + 1)
            direct = tuple(v * factor for v in direct)
            diffuse = tuple(v * factor for v in diffuse)
        elif not isinstance(direct, tuple):
            direct, diffuse = tuple(direct), tuple(diffuse)

        # get the radiation coming from the ground
        dir_ground = ((sum(direct) / len(direct)) * metadata[1],) * len(direct)
        dif_ground = ((sum(diffuse) / len(diffuse)) * metadata[1],) * len(diffuse)
        all_dir = direct + dir_ground
        all_dif = diffuse + dif_ground

        # check the altitude and azimuth inputs
        self._azimuth_count = int(azimuth_count)
        assert self._azimuth_count >= 3, 'RadiationDome azimuth_count must be ' \
            'greater or equal to 3. Got {}.'.format(azimuth_count)
        self._altitude_count = int(altitude_count)
        assert self._altitude_count >= 3, 'RadiationDome altitude_count must be ' \
            'greater or equal to 3. Got {}.'.format(altitude_count)

        # get the vectors for each direction and compute their relation to the sky mtx
        dir_vecs = self.dome_vectors(self._azimuth_count, self._altitude_count)
        patch_vecs = view_sphere.tregenza_sphere_vectors if len(direct) == 145 else \
            view_sphere.reinhart_sphere_vectors
        cos_angles = [[math.cos(v1.angle(v2)) for v2 in patch_vecs] for v1 in dir_vecs]
        if self._north != 0:
            na = math.radians(self._north)
            self._direction_vectors = tuple(vec.rotate_xy(na) for vec in dir_vecs)
        else:
            self._direction_vectors = dir_vecs

        # compute the radiation values for each direction
        point_relation = []
        if intersection_matrix is None:
            for cos_a in cos_angles:
                pt_rel = []
                for a in cos_a:
                    w = 0 if a < 0 else a
                    pt_rel.append(w)
                point_relation.append(pt_rel)
        else:
            for int_vals, cos_a in zip(intersection_matrix, cos_angles):
                pt_rel = []
                for iv, a in zip(int_vals, cos_a):
                    w = 0 if a < 0 or not iv else a
                    pt_rel.append(w)
                point_relation.append(pt_rel)
        total_res, direct_res, diff_res = [], [], []
        for pt_rel in point_relation:
            dir_v = sum(r * w for r, w in zip(pt_rel, all_dir))
            dif_v = sum(r * w for r, w in zip(pt_rel, all_dif))
            direct_res.append(dir_v)
            diff_res.append(dif_v)
            total_res.append(dir_v + dif_v)
        self._direct_values = tuple(direct_res)
        self._diffuse_values = tuple(diff_res)
        self._total_values = tuple(total_res)

        # override the legend default min and max to make sense for the radiation dome
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
        assert radius > 0, 'Dome radius must be greater than zero. ' \
            'Got {}.'.format(radius)
        self._radius = radius
        if projection is not None:
            assert projection in self.PROJECTIONS, 'Projection "{}" is not recognized.' \
                ' Choose from: {}.'.format(projection, self.PROJECTIONS)
        self._projection = projection

        # use the direction vectors to create a mesh of the sky dome
        vertices = []
        for vec in self._direction_vectors:
            vertices.append(self.center_point.move(vec * self._radius))
        faces, pt_i, az_ct = [], 0, self._azimuth_count
        for row_count in range(self._altitude_count - 1):
            for _ in range(az_ct - 1):
                faces.append((pt_i, pt_i + 1, pt_i + az_ct + 1, pt_i + az_ct))
                pt_i += 1  # advance the number of vertices
            faces.append((pt_i, pt_i - az_ct + 1, pt_i + 1, pt_i + az_ct))
            pt_i += 1  # advance the number of vertices
        # add triangular faces to represent the last circular patch
        end_vert_i = len(vertices) - 1
        start_vert_i = len(vertices) - self._azimuth_count - 1
        for tr_i in range(0, self._azimuth_count - 1):
            faces.append((start_vert_i + tr_i, end_vert_i, start_vert_i + tr_i + 1))
        faces.append((end_vert_i - 1, end_vert_i, start_vert_i))
        self._dome_mesh = Mesh3D(vertices, faces)

    @property
    def azimuth_count(self):
        """Get the number of horizontal orientations for the radiation dome."""
        return self._azimuth_count

    @property
    def altitude_count(self):
        """Get the number of vertical directions for the radiation dome."""
        return self._altitude_count

    @property
    def legend_parameters(self):
        """Get the legend parameters assigned to this radiation dome object."""
        return self._legend_parameters

    @property
    def plot_irradiance(self):
        """Get a boolean for whether the dome values are for irradiance in (W/m2)."""
        return self._plot_irradiance

    @property
    def center_point(self):
        """Get a Point3D for the center of the radiation dome."""
        return self._center_point

    @property
    def radius(self):
        """Get a number for the radius of the radiation dome."""
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
    def direction_vectors(self):
        """Get a list of vectors for each of the directions the dome is evaluating.

        All vectors are unit vectors.
        """
        return self._direction_vectors

    @property
    def dome_mesh(self):
        """Get a Mesh3D of the radiation dome with the center point and radius.

        This dome will be properly oriented to the north of the input sky matrix
        but it will not have any colors assigned to it.
        """
        return self._dome_mesh

    @property
    def total_values(self):
        """Get a tuple of values for the total radiation/irradiance of each direction."""
        return self._total_values

    @property
    def direct_values(self):
        """Get a tuple of values for the direct radiation/irradiance of each direction.
        """
        return self._direct_values

    @property
    def diffuse_values(self):
        """Get a tuple of values for the diffuse radiation/irradiance of each direction.
        """
        return self._diffuse_values

    @property
    def max_direction(self):
        """Get a the direction with the maximum total radiation/irradiance."""
        sort_v = [v for _, v in sorted(zip(self._total_values, self._direction_vectors))]
        return sort_v[-1]

    @property
    def max_point(self):
        """Get a point on the dome with the maximum total radiation/irradiance."""
        base_pt = self.center_point.move(self.max_direction * self.radius)
        if self.projection is not None:
            if self.projection.title() == 'Orthographic':
                base_pt2d = Compass.point3d_to_orthographic(base_pt)
                return Point3D(base_pt2d.x, base_pt2d.y, self.center_point.z)
            elif self.projection.title() == 'Stereographic':
                base_pt2d = Compass.point3d_to_stereographic(
                    base_pt, self.radius, self.center_point)
                return Point3D(base_pt2d.x, base_pt2d.y, self.center_point.z)
        return base_pt

    @property
    def max_info(self):
        """Get a text string with information about the maximum radiation/irradiance.

        This includes the altitude, azimuth, and radiation/irradiance value.
        """
        max_value = max(self.total_values)
        unit = 'W/m2' if self.plot_irradiance else 'kWh/m2'
        max_ind = self.total_values.index(max_value)
        max_az = (max_ind % self.azimuth_count) * (360 / self.azimuth_count)
        max_alt = math.floor(max_ind / self.azimuth_count) * (90 / self.altitude_count)
        return 'azimuth: {} deg\naltitude: {} deg\nvalue: {} {}'.format(
            int(max_az), int(max_alt), round(max_value, 1), unit)

    @property
    def metadata(self):
        """Get a tuple of information about the metadata assigned to the radiation dome.
        """
        return self._metadata

    @property
    def is_benefit(self):
        """Boolean to note whether the sky matrix includes benefit information."""
        return self._is_benefit

    def draw(self, rad_type='total', center=None):
        """Draw an dome mesh, compass, graphic/legend, and title.

        Args:
            rad_type: Text for the type of radiation to use. Choose from total, direct,
                diffuse. (Default: total).
            center: A Point3D to override the center of the dome. This is useful
                when rendering all of the sky components together and one dome
                should not be on top of another. If None, the center
                point assigned to the object instance is used. (Default: None).

        Returns:
            dome_mesh: A colored Mesh3D for the dome radiation.
            compass: A ladybug Compass object for the dome.
            graphic: A GraphicContainer for the colored arrow mesh, indicating the
                legend and title location for the dome.
            dome_title: Text for the title of the dome.
        """
        # get the dome data to be plotted and the center point
        if rad_type.lower() == 'total':
            rad_data = self.total_values
        elif rad_type.lower() == 'direct':
            rad_data = self.direct_values
        elif rad_type.lower() == 'diffuse':
            rad_data = self.diffuse_values
        else:
            raise ValueError('Radiation type "{}" not recognized.'.format(rad_type))

        if center is not None and center != self.center_point:
            center = center
            move_vec = center - self.center_point
            dome_mesh = self.dome_mesh.move(move_vec)
        else:
            center = self.center_point
            dome_mesh = self.dome_mesh

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
            rad_data, min_pt, max_pt, self.legend_parameters, d_type, unit)
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

        return dome_mesh, dome_compass, graphic, dome_title

    @staticmethod
    def dome_vectors(azimuth_count, altitude_count):
        """Generate a list of vectors over the dome."""
        horiz_angle = -2 * math.pi / azimuth_count
        vert_angle = (math.pi / 2) / altitude_count
        dome_vecs = []
        for v in range(altitude_count):
            x_axis = Vector3D(1, 0, 0)
            base_vec = Vector3D(0, 1, 0)
            n_vec = base_vec.rotate(x_axis, vert_angle * v)
            for h in range(azimuth_count):
                dome_vecs.append(n_vec.rotate_xy(horiz_angle * h))
        dome_vecs.append(Vector3D(0, 0, 1))
        return dome_vecs

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
        """Radiation Dome object representation."""
        return 'RadiationDome [{} patches]'.format(len(self._total_values))
