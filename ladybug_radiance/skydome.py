"""Class for visualizing sky matrices on a dome."""
import math

from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.mesh import Mesh3D

from ladybug.viewsphere import view_sphere
from ladybug.compass import Compass
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters


class SkyDome(object):
    """Visualize a sky matrix as a colored dome, subdivided into patches.

    Args:
        sky_matrix: A SkyMatrix object, which describes the radiation coming
            from the various patches of the sky.
        legend_parameters: An optional LegendParameter object to change the display
            of the sky dome. If None, some default legend parameters will be
            used. (Default: None).
        center_point: A point for the center of the dome. (Default: (0, 0, 0))
        radius: A number to set the radius of the sky dome. (Default: 100).
        projection: Optional text for the name of a projection to use from the sky
            dome hemisphere to the 2D plane. If None, a 3D sky dome will be drawn
            instead of a 2D one. (Default: None) Choose from the following.

                * Orthographic
                * Stereographic

    Properties:
        * sky_matrix
        * legend_parameters
        * center_point
        * radius
        * projection
        * patch_vectors
        * total_values
        * direct_values
        * diffuse_values
    """

    def __init__(self, sky_matrix, legend_parameters=None, center_point=Point3D(0, 0, 0),
                 radius=100, projection=None):
        """Initialize SkyDome."""
        # set defaults for global variables
        _scale_ = 1 if _scale_ is None else _scale_
        radius = (100 * _scale_) / conversion_to_meters()
        if _center_pt_ is not None:  # process the center point into a Point2D
            center_pt3d = to_point3d(_center_pt_)
            z = center_pt3d.z
        else:
            center_pt3d, z = Point3D(), 0

        # deconstruct the sky matrix and derive key data from it
        metadata, direct, diffuse = de_objectify_output(_sky_mtx)
        north = metadata[0]  # first item is the north angle
        sky_type = 1 if len(direct) == 145 else 2  # i for tregenza; 2 for reinhart
        total = [dirr + difr for dirr, difr in zip(direct, diffuse)] # total radiation

        # override the legend default min and max to make sense for domes
        l_par = legend_par_.duplicate() if legend_par_ is not None else LegendParameters()
        if l_par.min is None:
            l_par.min = 0
        if l_par.max is None:
            l_par.max = max(total)

        # output patch patch vectors
        patch_vecs_lb = view_sphere.tregenza_dome_vectors if len(total) == 145 \
            else view_sphere.reinhart_dome_vectors
        patch_vecs = [from_vector3d(vec) for vec in patch_vecs_lb]

        # create the dome meshes
        if not show_comp_:  # only create the total dome mesh
            mesh, compass, legend, title, mesh_values = \
                draw_dome(total, center_pt3d, 'Total', l_par)
            patch_values = total
        else:  # create domes for total, direct and diffuse
            # loop through the 3 radiation types and produce a dome
            mesh, compass, legend, title, mesh_values = [], [], [], [], []
            rad_types = ('Total', 'Direct', 'Diffuse')
            rad_data = (total, direct, diffuse)
            for dome_i in range(3):
                cent_pt = Point3D(center_pt3d.x + radius * 3 * dome_i,
                                center_pt3d.y, center_pt3d.z)
                dome_mesh, dome_compass, dome_legend, dome_title, dome_values = \
                    draw_dome(rad_data[dome_i], cent_pt, rad_types[dome_i], l_par)
                mesh.append(dome_mesh)
                compass.extend(dome_compass)
                legend.extend(dome_legend)
                title.append(dome_title)
                mesh_values.append(dome_values)
            patch_values = list_to_data_tree(rad_data)
            mesh_values = list_to_data_tree(mesh_values)

    def draw_dome(self, dome_type='total', center=None):
        """Draw a dome mesh, compass, legend, and title for a sky dome.

        Args:
            dome_type: Text for the type of dome to draw. Choose from total, direct,
                diffuse. (Default: total).
            center: Point3D for the center of the sun path. If None, defaults
                will be used, generated from the center point assigned to the
                object instance. (Default: None).

        Returns:
            dome_mesh: A colored mesh for the dome based on dome_data.
            dome_compass: A compass for the dome.
            dome_legend: A legend for the colored dome mesh.
            dome_title: A title for the dome.
            values: A list of radiation values that align with the dome_mesh faces.
        """
        # create the dome mesh and ensure patch values align with mesh faces
        if len(dome_data) == 145:  # tregenza sky
            lb_mesh = view_sphere.tregenza_dome_mesh_high_res.scale(radius)
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
        else:  #reinhart sky
            lb_mesh = view_sphere.reinhart_dome_mesh.scale(radius)
            values = dome_data + [dome_data[-1]] * 11  # last patch has triangular faces

        # move and/or rotate the mesh as needed
        if north != 0:
            lb_mesh = lb_mesh.rotate_xy(math.radians(north), Point3D())
        if center != Point3D():
            lb_mesh = lb_mesh.move(Vector3D(center.x, center.y, center.z))

        # project the mesh if requested
        if projection_ is not None:
            if projection_.title() == 'Orthographic':
                pts = (Compass.point3d_to_orthographic(pt) for pt in lb_mesh.vertices)
            elif projection_.title() == 'Stereographic':
                pts = (Compass.point3d_to_stereographic(pt, radius, center)
                    for pt in lb_mesh.vertices)
            else:
                raise ValueError(
                    'Projection type "{}" is not recognized.'.format(projection_))
            pts3d = tuple(Point3D(pt.x, pt.y, z) for pt in pts)
            lb_mesh = Mesh3D(pts3d, lb_mesh.faces)

        # output the dome visualization, including legend and compass
        move_fac = radius * 0.15
        min_pt = lb_mesh.min.move(Vector3D(-move_fac, -move_fac, 0))
        max_pt = lb_mesh.max.move(Vector3D(move_fac, move_fac, 0))
        graphic = GraphicContainer(values, min_pt, max_pt, legend_par)
        graphic.legend_parameters.title = 'kWh/m2'
        lb_mesh.colors = graphic.value_colors
        dome_mesh = from_mesh3d(lb_mesh)
        dome_legend = legend_objects(graphic.legend)
        dome_compass = compass_objects(
            Compass(radius, Point2D(center.x, center.y), north), z, None, projection_,
            graphic.legend_parameters.font)

        # construct a title from the metadata
        st, end = metadata[2], metadata[3]
        time_str = '{} - {}'.format(st, end) if st != end else st
        title_txt = '{} Radiation\n{}\n{}'.format(
            dome_name, time_str, '\n'.join([dat for dat in metadata[4:]]))
        dome_title = text_objects(title_txt, graphic.lower_title_location,
                                graphic.legend_parameters.text_height,
                                graphic.legend_parameters.font)

        return dome_mesh, dome_compass, dome_legend, dome_title, values
