"""Class for visualizing the impact of radiation from different direction as a rose."""
from __future__ import division
import math

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.line import LineSegment3D
from ladybug_geometry.geometry3d.mesh import Mesh3D

from ladybug.datatype.energyintensity import Radiation
from ladybug.datatype.energyflux import Irradiance
from ladybug.viewsphere import view_sphere
from ladybug.compass import Compass
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters
from ladybug.color import Colorset


class RadiationRose(object):
    """Visualize the impact of radiation from different direction as a rose.

    By default, the Radiation Rose depicts the amount of solar energy received
    by a vertical wall facing each of the directions of the compass rose. This
    is useful for understanding the radiation harm/benefit experienced by different
    building orientations or the orientations with the highest peak cooling load
    (for sky matrices of clear skies). The tilt_angle can be used to assess the
    solar energy falling on geometries that are not perfectly vertical, such
    as a tilted photovoltaic panel.

    Args:
        sky_matrix: A SkyMatrix object, which describes the radiation coming
            from the various patches of the sky.
        intersection_matrix: An optional lists of lists, which can be used to account
            for context shade surrounding the radiation rose. The matrix should
            have a length equal to the direction_count and begin from north moving
            clockwise. Each sub-list should consist of booleans and have a length
            equal to the number of sky patches times 2 (indicating sky patches and
            ground patches). True indicates that a certain patch is seen and False
            indicates that the match is blocked. If None, the radiation rose will
            be computed assuming no obstructions. (Default: None).
        direction_count: An integer greater than or equal to 3, which notes the number
            of arrows to be generated for the radiation rose. (Default: 36).
        tilt_angle: A number between 0 and 90 that sets the vertical tilt angle
            (aka. the altitude) for all of the directions. By default, the Radiation
            Rose depicts the amount of solar energy received by a vertical
            wall (tilt_angle=0). The tilt_angle can be changed to a specific
            value to assess the solar energy falling on geometries that are not
            perfectly vertical, such as a tilted photovoltaic panel. (Default: 0).
        legend_parameters: An optional LegendParameter object to change the display
            of the radiation rose. If None, default legend parameters will be
            used. (Default: None).
        plot_irradiance: Boolean to note whether the radiation rose should be plotted
            with units of total Radiation (kWh/m2) [False] or with units of average
            Irradiance (W/m2) [True]. (Default: False).
        center_point: A point for the center of the rose. (Default: (0, 0, 0)).
        radius: A number to set the radius of the radiation rose. (Default: 100).
        arrow_scale: A fractional number to note the scale of the radiation rose arrows
            in relation to the entire graphic. (Default: 1).

    Properties:
        * direction_count
        * tilt_angle
        * legend_parameters
        * plot_irradiance
        * center_point
        * radius
        * arrow_scale
        * north
        * direction_vectors
        * total_values
        * direct_values
        * diffuse_values
        * metadata
        * is_benefit
    """
    __slots__ = (
        '_north', '_direction_vectors', '_total_values', '_direct_values',
        '_diffuse_values', '_metadata', '_is_benefit', '_direction_count',
        '_tilt_angle', '_legend_parameters', '_plot_irradiance',
        '_center_point', '_radius', '_arrow_scale')

    def __init__(self, sky_matrix, intersection_matrix=None, direction_count=36,
                 tilt_angle=0, legend_parameters=None, plot_irradiance=False,
                 center_point=Point3D(0, 0, 0), radius=100, arrow_scale=1):
        """Initialize RadiationRose."""
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

        # get the vectors and angles for each direction
        self._direction_count = int(direction_count)
        assert self._direction_count >= 3, 'RadiationRose direction_count must be ' \
            'greater than or equal to 3. Got {}.'.format(direction_count)
        assert isinstance(tilt_angle, (float, int)), 'Expected number for tilt_angle. ' \
            'Got {}.'.format(type(tilt_angle))
        assert 0 <= tilt_angle < 90, 'Rose tilt_angle must be between 0 and 90. ' \
            'Got {}.'.format(tilt_angle)
        self._tilt_angle = tilt_angle
        base_dir_vecs = view_sphere.horizontal_radial_vectors(self._direction_count)
        if self._tilt_angle != 0:
            x_axis = Vector3D(1, 0, 0)
            base_vec = Vector3D(0, 1, 0)
            horiz_angle = -2 * math.pi / self._direction_count
            vert_angle = math.radians(self._tilt_angle)
            dir_vecs = tuple(
                base_vec.rotate(x_axis, vert_angle).rotate_xy(horiz_angle * i)
                for i in range(self._direction_count))
        else:
            dir_vecs = base_dir_vecs
        patch_vecs = view_sphere.tregenza_sphere_vectors if len(direct) == 145 else \
            view_sphere.reinhart_sphere_vectors
        cos_angles = [[math.cos(v1.angle(v2)) for v2 in patch_vecs] for v1 in dir_vecs]
        if self._north != 0:
            na = math.radians(self._north)
            self._direction_vectors = tuple(vec.rotate_xy(na) for vec in base_dir_vecs)
        else:
            self._direction_vectors = base_dir_vecs

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

        # override the legend default min and max to make sense for the radiation rose
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

        # process the geometry parameters of the rose
        assert isinstance(center_point, Point3D), 'Expected Point3D for rose center. ' \
            'Got {}.'.format(type(center_point))
        self._center_point = center_point
        assert isinstance(radius, (float, int)), 'Expected number for radius. ' \
            'Got {}.'.format(type(radius))
        assert radius > 0, 'Rose radius must be greater than zero. ' \
            'Got {}.'.format(radius)
        self._radius = radius
        assert isinstance(arrow_scale, (float, int)), \
            'Expected number for arrow_scale. Got {}.'.format(type(arrow_scale))
        assert arrow_scale > 0, \
            'Rose arrow_scale must be greater than zero. Got {}.'.format(arrow_scale)
        self._arrow_scale = arrow_scale

    @property
    def direction_count(self):
        """Get the number of directions for the radiation rose."""
        return self._direction_count

    @property
    def tilt_angle(self):
        """Get the angle of the radiation rose vertical tilt in degrees."""
        return self._tilt_angle

    @property
    def legend_parameters(self):
        """Get the legend parameters assigned to this radiation rose object."""
        return self._legend_parameters

    @property
    def plot_irradiance(self):
        """Get a boolean for whether the rose values are for irradiance in (W/m2)."""
        return self._plot_irradiance

    @property
    def center_point(self):
        """Get a Point3D for the center of the radiation rose."""
        return self._center_point

    @property
    def radius(self):
        """Get a number for the radius of the radiation rose."""
        return self._radius

    @property
    def arrow_scale(self):
        """Get a number for the scale of arrows on the radiation rose."""
        return self._arrow_scale

    @property
    def north(self):
        """Get a number north direction."""
        return self._north

    @property
    def direction_vectors(self):
        """Get a list of vectors for each of the directions the rose is facing.

        All vectors are unit vectors.
        """
        return self._direction_vectors

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
    def metadata(self):
        """Get a tuple of information about the metadata assigned to the radiation rose.
        """
        return self._metadata

    @property
    def is_benefit(self):
        """Boolean to note whether the sky matrix includes benefit information."""
        return self._is_benefit

    def draw(self, rad_type='total', center=None, max_rad=None):
        """Draw an arrow mesh, orientation lines, compass, graphic/legend, and title.

        Args:
            rad_type: Text for the type of radiation to use. Choose from total, direct,
                diffuse. (Default: total).
            center: A Point3D to override the center of the rose. This is useful
                when rendering all of the sky components together and one rose
                should not be on top of another. If None, the center
                point assigned to the object instance is used. (Default: None).
            max_rad: An optional number to set the level of radiation or irradiance
                associated with the full radius of the rose. If None, this is
                determined by the maximum level of radiation in the input data
                but a number can be specified here to fix this at a specific value.
                This is particularly useful when comparing different roses to one
                another. (Default: None).

        Returns:
            arrow_mesh: A colored Mesh3D for the rose arrows.
            orientation_lines: A list of LineSegment3D for each direction.
            compass: A ladybug Compass object for the rose.
            graphic: A GraphicContainer for the colored arrow mesh, indicating the
                legend and title location for the rose.
            rose_title: Text for the title of the rose.
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
        center = self.center_point if center is None else center

        # generate the mesh for the arrows of the rose
        ar_angle = math.pi / self.direction_count
        if max_rad is None:
            len_factor = self.radius / max(self.total_values) if not self.is_benefit \
                else self.radius / max((-min(self.total_values), max(self.total_values)))
        else:
            len_factor = self.radius / max_rad
        verts, faces, f_count = [center], [], 0
        for r_val, dir_vec in zip(rad_data, self.direction_vectors):
            # get key dimensions of the arrow
            arrow_length = abs(r_val) * len_factor
            head_dist = arrow_length * 0.8
            arrow_width = math.tan(ar_angle) * head_dist * 0.9 * self.arrow_scale
            h_vec = dir_vec * head_dist
            w_vec = dir_vec.rotate_xy(math.pi / 2) * arrow_width
            # create the mesh vertices
            right_pt = center.move(h_vec + w_vec)
            end_pt = center.move(dir_vec * arrow_length)
            left_pt = center.move(h_vec - w_vec)
            verts.extend((right_pt, end_pt, left_pt))
            faces.append((0, f_count + 1, f_count + 2, f_count + 3))
            f_count += 3
        arrow_mesh = Mesh3D(verts, faces)

        # generate the frequency lines
        low_cent = Point3D(center.x, center.y, center.z - 0.01)
        orientation_lines = [
            LineSegment3D(low_cent, vec * self.radius) for vec in self.direction_vectors]

        # output the rose visualization, including graphic and compass
        move_fac = self.radius * 1.15
        min_pt = center.move(Vector3D(-move_fac, -move_fac, 0))
        max_pt = center.move(Vector3D(move_fac, move_fac, 0))
        if self.plot_irradiance:
            d_type, unit, typ_str = Irradiance(), 'W/m2', 'Irradiance'
        else:
            d_type, unit, typ_str = Radiation(), 'kWh/m2', 'Radiation'
        graphic = GraphicContainer(
            rad_data, min_pt, max_pt, self.legend_parameters, d_type, unit)
        arrow_mesh.colors = graphic.value_colors
        compass = Compass(self.radius, Point2D(center.x, center.y), self.north)

        # construct a title from the metadata
        st, end = self.metadata[2], self.metadata[3]
        time_str = '{} - {}'.format(st, end) if st != end else st
        if self.is_benefit:
            typ_str = '{} Benefit/Harm'.format(typ_str)
        rose_title = '{} {}\n{}\n{}'.format(
            rad_type.title(), typ_str, time_str,
            '\n'.join([dat for dat in self.metadata[4:]]))

        return arrow_mesh, orientation_lines, compass, graphic, rose_title

    @staticmethod
    def radial_vectors(direction_count, tilt_angle=0):
        """Generate a list of radial vectors."""
        if tilt_angle != 0:
            x_axis = Vector3D(1, 0, 0)
            base_vec = Vector3D(0, 1, 0)
            horiz_angle = -2 * math.pi / direction_count
            vert_angle = math.radians(tilt_angle)
            return tuple(
                base_vec.rotate(x_axis, vert_angle).rotate_xy(horiz_angle * i)
                for i in range(direction_count))
        else:
            return view_sphere.horizontal_radial_vectors(direction_count)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __len__(self):
        return self.direction_count

    def __getitem__(self, key):
        return self._total_values[key], self._direct_values[key], \
            self._diffuse_values[key]

    def __iter__(self):
        return zip(self._total_values, self._direct_values, self._diffuse_values)

    def __repr__(self):
        """Rose object representation."""
        return 'RadiationRose [{} directions]'.format(self.direction_count)
