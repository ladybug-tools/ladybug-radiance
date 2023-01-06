"""Get a matrix containing radiation values from each patch of a sky dome.

Creating this matrix is a necessary pre-step before doing incident radiation
analysis or generating a visualizations like a radiation rose.

This class uses Radiance's gendaymtx function to calculate the radiation
for each patch of the sky. Gendaymtx is written by Ian Ashdown and Greg Ward.
More information can be found in Radiance manual at:
http://www.radiance-online.org/learning/documentation/manual-pages/pdfs/gendaymtx.pdf
"""
from __future__ import division
import os
import subprocess
import sys

from ladybug.epw import EPW
from ladybug.wea import Wea
from ladybug.viewsphere import view_sphere
from ladybug.config import folders as lb_folders

from .config import folders

if folders.radbin_path is not None:
    GENDAYMTX_EXE = os.path.join(folders.radbin_path, 'gendaymtx.exe') if \
        os.name == 'nt' else os.path.join(folders.radbin_path, 'gendaymtx')
else:
    GENDAYMTX_EXE = None


class SkyMatrix(object):
    """A matrix containing radiation values from each patch of a sky dome.

    Args:
        wea: A Ladybug Wea object.
        north: A number between -360 and 360 for the counterclockwise difference
            between the North and the positive Y-axis in degrees. 90 is West and 270
            is East. (Default: 0).
        high_density: A Boolean to indicate whether the higher-density Reinhart
            sky matrix should be generated (True), which has roughly 4 times
            the sky patches as the (default) original Tregenza sky (False).
            Note that, while the Reinhart sky has a higher resolution and is
            more accurate, it will result in considerably longer calculation
            time for incident radiation studies. (Default: False).
        ground_reflectance: A number between 0 and 1 to note the average ground
            reflectance that is associated with the sky matrix. (Default: 0.2).

    Properties:
        * wea
        * north
        * high_density
        * ground_reflectance
        * benefit_matrix
        * folder
        * wea_duration
        * direct_values
        * diffuse_values
        * metadata
        * data
    """
    # constants for converting RGB values output by gendaymtx to broadband radiation
    PATCHES_PER_ROW = {
        1: view_sphere.TREGENZA_PATCHES_PER_ROW + (1,),
        2: view_sphere.REINHART_PATCHES_PER_ROW + (1,)
    }
    PATCH_ROW_COEFF = {
        1: view_sphere.TREGENZA_COEFFICIENTS,
        2: view_sphere.REINHART_COEFFICIENTS
    }
    LINE_BREAK = b'\n' if sys.version_info > (3, 0) else '\n'
    SEPARATOR = b' ' if sys.version_info > (3, 0) else ' '

    __slots__ = (
        '_wea', '_north', '_high_density', '_ground_reflectance', '_folder',
        '_direct_values', '_diffuse_values', '_benefit_matrix', '_metadata')

    def __init__(self, wea, north=0, high_density=False, ground_reflectance=0.2):
        """Initialize SkyMatrix."""
        self.wea = wea
        self.north = north
        self.high_density = high_density
        self.ground_reflectance = ground_reflectance
        self.benefit_matrix = None
        self.folder = None

    @classmethod
    def from_components(
            cls, location, direct_normal_irradiance, diffuse_horizontal_irradiance,
            hoys=None, north=0, high_density=False, ground_reflectance=0.2):
        """Create a SkyMatrix from individual solar irradiance components.

        Args:
            location: Ladybug location object.
            direct_normal_irradiance: A HourlyContinuousCollection or a
                HourlyDiscontinuousCollection for direct normal irradiance. The
                collection must be aligned with the diffuse_horizontal_irradiance.
            diffuse_horizontal_irradiance: A HourlyContinuousCollection or a
                HourlyDiscontinuousCollection for diffuse horizontal irradiance, The
                collection must be aligned with the direct_normal_irradiance.
            hoys: A list of numbers between 0 and 8760 that represent the hours of the
                year for which to generate the sky matrix. If None, the matrix will
                be for the entire year. (Default: None).
            north: A number between -360 and 360 for the counterclockwise difference
                between the North and the positive Y-axis in degrees. 90 is West
                and 270 is East. (Default: 0).
            high_density: A Boolean to indicate whether the higher-density Reinhart
                sky matrix should be generated (True), which has roughly 4 times
                the sky patches as the (default) original Tregenza sky (False).
                Note that, while the Reinhart sky has a higher resolution and is
                more accurate, it will result in considerably longer calculation
                time for incident radiation studies. (Default: False).
            ground_reflectance: A number between 0 and 1 to note the average ground
                reflectance that is associated with the sky matrix. (Default: 0.2).
        """
        # filter the radiation by hoys if they are input
        if hoys is not None and len(hoys) != 0:
            dni = direct_normal_irradiance.filter_by_hoys(hoys)
            dhi = diffuse_horizontal_irradiance.filter_by_hoys(hoys)
        else:
            dni, dhi = direct_normal_irradiance, diffuse_horizontal_irradiance
        # create the wea and return the SkyMatrix
        wea = Wea(location, dni, dhi)
        return cls(wea, north, high_density, ground_reflectance)

    @classmethod
    def from_components_benefit(
            cls, location, direct_normal_irradiance, diffuse_horizontal_irradiance,
            temperature, balance_temperature=15, balance_offset=2,
            hoys=None, north=0, high_density=False, ground_reflectance=0.2):
        """Create a SkyMatrix representing benefit/harm based on temperature data.

        Args:
            location: Ladybug location object.
            direct_normal_irradiance: A HourlyContinuousCollection or a
                HourlyDiscontinuousCollection for direct normal irradiance. The
                collection must be aligned with the diffuse_horizontal_irradiance.
            diffuse_horizontal_irradiance: A HourlyContinuousCollection or a
                HourlyDiscontinuousCollection for diffuse horizontal irradiance. The
                collection must be aligned with the direct_normal_irradiance.
            temperature: A HourlyContinuousCollection or a HourlyDiscontinuousCollection
                for temperature, which will be used to establish whether radiation
                is desired or not for each time step. The collection must be aligned
                with the irradiance inputs.
            balance_temperature: The temperature in Celsius between which radiation
                switches from being a benefit to a harm. Typical residential buildings
                have balance temperatures as high as 18C and commercial buildings tend
                to have lower values around 12C. (Default 15C).
            balance_offset: The temperature offset from the balance temperature
                in Celsius where radiation is neither harmful nor helpful. (Default: 2).
            hoys: A list of numbers between 0 and 8760 that represent the hours of the
                year for which to generate the sky matrix. If None, the matrix will
                be for the entire year. (Default: None).
            north: A number between -360 and 360 for the counterclockwise difference
                between the North and the positive Y-axis in degrees. 90 is West
                and 270 is East. (Default: 0).
            high_density: A Boolean to indicate whether the higher-density Reinhart
                sky matrix should be generated (True), which has roughly 4 times
                the sky patches as the (default) original Tregenza sky (False).
                Note that, while the Reinhart sky has a higher resolution and is
                more accurate, it will result in considerably longer calculation
                time for incident radiation studies. (Default: False).
            ground_reflectance: A number between 0 and 1 to note the average ground
                reflectance that is associated with the sky matrix. (Default: 0.2).
        """
        # filter the radiation by hoys if they are input
        if hoys is not None and len(hoys) != 0:
            dni = direct_normal_irradiance.filter_by_hoys(hoys)
            dhi = diffuse_horizontal_irradiance.filter_by_hoys(hoys)
            temperature = temperature.filter_by_hoys(hoys)
        else:
            dni, dhi = direct_normal_irradiance, diffuse_horizontal_irradiance
        # create the benefit matrix
        t_low = balance_temperature - balance_offset
        t_high = balance_temperature + balance_offset
        benefit_mtx = []
        for t in temperature:
            if t < t_low:  # low temperatures mean radiation is beneficial
                benefit_mtx.append(True)
            elif t > t_high:  # high temperatures mean radiation is harmful
                benefit_mtx.append(False)
            else:  # the temperature is neutral, meaning radiation has no effect
                benefit_mtx.append(None)
        # create the wea and return the SkyMatrix
        wea = Wea(location, dni, dhi)
        sky_mtx = cls(wea, north, high_density, ground_reflectance)
        sky_mtx.benefit_matrix = benefit_mtx
        return sky_mtx

    @classmethod
    def from_epw(cls, epw_file, hoys=None, north=0, high_density=False,
                 ground_reflectance=0.2):
        """Create a SkyMatrix using the solar irradiance values in an epw file.

        Args:
            epw_file: Full path to epw weather file.
            hoys: A list of numbers between 0 and 8760 that represent the hours of the
                year for which to generate the sky matrix. If None, the matrix will
                be for the entire year. (Default: None).
            north: A number between -360 and 360 for the counterclockwise difference
                between the North and the positive Y-axis in degrees. 90 is West
                and 270 is East. (Default: 0).
            high_density: A Boolean to indicate whether the higher-density Reinhart
                sky matrix should be generated (True), which has roughly 4 times
                the sky patches as the (default) original Tregenza sky (False).
                Note that, while the Reinhart sky has a higher resolution and is
                more accurate, it will result in considerably longer calculation
                time for incident radiation studies. (Default: False).
            ground_reflectance: A number between 0 and 1 to note the average ground
                reflectance that is associated with the sky matrix. (Default: 0.2).
        """
        epw = EPW(epw_file)
        return cls.from_components(
            epw.location, epw.direct_normal_radiation, epw.diffuse_horizontal_radiation,
            hoys, north, high_density, ground_reflectance)

    @classmethod
    def from_epw_benefit(cls, epw_file, balance_temperature=15, balance_offset=2,
                         hoys=None, north=0, high_density=False, ground_reflectance=0.2):
        """Create a SkyMatrix using the solar irradiance values in an epw file.

        Args:
            epw_file: Full path to epw weather file.
            balance_temperature: The temperature in Celsius between which radiation
                switches from being a benefit to a harm. Typical residential buildings
                have balance temperatures as high as 18C and commercial buildings tend
                to have lower values around 12C. (Default 15C).
            balance_offset: The temperature offset from the balance temperature
                in Celsius where radiation is neither harmful nor helpful. (Default: 2).
            hoys: A list of numbers between 0 and 8760 that represent the hours of the
                year for which to generate the sky matrix. If None, the matrix will
                be for the entire year. (Default: None).
            north: A number between -360 and 360 for the counterclockwise difference
                between the North and the positive Y-axis in degrees. 90 is West
                and 270 is East. (Default: 0).
            high_density: A Boolean to indicate whether the higher-density Reinhart
                sky matrix should be generated (True), which has roughly 4 times
                the sky patches as the (default) original Tregenza sky (False).
                Note that, while the Reinhart sky has a higher resolution and is
                more accurate, it will result in considerably longer calculation
                time for incident radiation studies. (Default: False).
            ground_reflectance: A number between 0 and 1 to note the average ground
                reflectance that is associated with the sky matrix. (Default: 0.2).
        """
        epw = EPW(epw_file)
        return cls.from_components_benefit(
            epw.location, epw.direct_normal_radiation, epw.diffuse_horizontal_radiation,
            epw.dry_bulb_temperature, balance_temperature, balance_offset,
            hoys, north, high_density, ground_reflectance)

    @classmethod
    def from_stat(cls, stat_file, hoys=None, north=0, high_density=False,
                  ground_reflectance=0.2):
        """Create a ASHRAE Revised Clear SkyMatrix using the data in .stat file.

        The .stat file must have monthly sky optical depths within it in order to
        create a Wea this way.

        Args:
            stat_file: Full path to a .stat file.
            hoys: A list of numbers between 0 and 8760 that represent the hours of the
                year for which to generate the sky matrix. If None, the matrix will
                be for the entire year. (Default: None).
            north: A number between -360 and 360 for the counterclockwise difference
                between the North and the positive Y-axis in degrees. 90 is West
                and 270 is East. (Default: 0).
            high_density: A Boolean to indicate whether the higher-density Reinhart
                sky matrix should be generated (True), which has roughly 4 times
                the sky patches as the (default) original Tregenza sky (False).
                Note that, while the Reinhart sky has a higher resolution and is
                more accurate, it will result in considerably longer calculation
                time for incident radiation studies. (Default: False).
            ground_reflectance: A number between 0 and 1 to note the average ground
                reflectance that is associated with the sky matrix. (Default: 0.2).
        """
        wea = Wea.from_stat_file(stat_file)
        # filter the radiation by hoys if they are input
        if hoys is not None and len(hoys) != 0:
            wea = wea.filter_by_hoys(hoys)
        return cls(wea, north, high_density, ground_reflectance)

    @classmethod
    def from_ashrae_clear_sky(cls, location, sky_clearness=1, hoys=None, north=0,
                              high_density=False, ground_reflectance=0.2):
        """Create an original ASHRAE Clear SkyMatrix using a location and sky clearness.

        The original ASHRAE Clear Sky is intended to determine peak solar load
        and sizing parameters for HVAC systems.  It is not the sky model
        currently recommended by ASHRAE since it usually overestimates the
        amount of solar irradiance in comparison to the newer ASHRAE Revised
        Clear Sky ("Tau Model"). However, the original model here is still
        useful for cases where monthly optical depth values are not known. For
        more information on the ASHRAE Clear Sky model, see the EnergyPlus
        Engineering Reference:
        https://bigladdersoftware.com/epx/docs/8-9/engineering-reference/climate-calculations.html

        Args:
            location: Ladybug location object.
            sky_clearness: A factor that will be multiplied by the output of
                the model. This is to help account for locations where clear,
                dry skies predominate (e.g., at high elevations) or,
                conversely, where hazy and humid conditions are frequent. See
                Threlkeld and Jordan (1958) for recommended values. Typical
                values range from 0.95 to 1.05 and are usually never more
                than 1.2. Default is set to 1.0.
            hoys: A list of numbers between 0 and 8760 that represent the hours of the
                year for which to generate the sky matrix. If None, the matrix will
                be for the entire year. (Default: None).
            north: A number between -360 and 360 for the counterclockwise difference
                between the North and the positive Y-axis in degrees. 90 is West
                and 270 is East. (Default: 0).
            high_density: A Boolean to indicate whether the higher-density Reinhart
                sky matrix should be generated (True), which has roughly 4 times
                the sky patches as the (default) original Tregenza sky (False).
                Note that, while the Reinhart sky has a higher resolution and is
                more accurate, it will result in considerably longer calculation
                time for incident radiation studies. (Default: False).
            ground_reflectance: A number between 0 and 1 to note the average ground
                reflectance that is associated with the sky matrix. (Default: 0.2).
        """
        wea = Wea.from_ashrae_clear_sky(location, sky_clearness)
        # filter the radiation by hoys if they are input
        if hoys is not None and len(hoys) != 0:
            wea = wea.filter_by_hoys(hoys)
        return cls(wea, north, high_density, ground_reflectance)

    @property
    def wea(self):
        """Get or set a Wea object for the sky matrix."""
        return self._wea

    @wea.setter
    def wea(self, value):
        assert isinstance(value, Wea), \
            'wea must be from type Wea not {}'.format(type(value))
        self._wea = value
        self._direct_values = None
        self._diffuse_values = None
        self._metadata = None

    @property
    def north(self):
        """Get or set a number north direction.

        A number between -360 and 360 for the counterclockwise difference between
        the North and the positive Y-axis in degrees. 90 is West and 270 is East.
        """
        return self._north

    @north.setter
    def north(self, value):
        assert isinstance(value, (float, int)), 'Expected number for ' \
            'SkyMatrix north. Got {}.'.format(type(value))
        assert -360 <= value <= 360, 'SkyMatrix north must be between 0 and 360. ' \
            'Got {}.'.format(value)
        self._north = value

    @property
    def high_density(self):
        """Get or set a boolean for whether the sky is a higher-density Reinhart matrix.
        """
        return self._high_density

    @high_density.setter
    def high_density(self, value):
        self._high_density = bool(value)
        self._direct_values = None
        self._diffuse_values = None
        self._metadata = None

    @property
    def ground_reflectance(self):
        """Get or set a number between 0 and 1 to note the average ground reflectance.
        """
        return self._ground_reflectance

    @ground_reflectance.setter
    def ground_reflectance(self, value):
        assert isinstance(value, (float, int)), 'Expected number for ' \
            'SkyMatrix ground_reflectance. Got {}.'.format(type(value))
        assert 0 <= value <= 1, 'SkyMatrix ground_reflectance must be between 0 and 1.' \
            ' Got {}.'.format(value)
        self._ground_reflectance = value

    @property
    def benefit_matrix(self):
        """Get or set list of True/False values for whether Wea datetimes are beneficial.

        This list must have a length that matches the Wea so that each datetime
        can be matched with a benefit/harm value. True (beneficial) values will
        contribute positively to the value of each sky patch while False (harmful)
        values will contribute negatively. A value of None in the list indicates
        that the hour has neither a benefit or a harmful effect.

        This is None by default, indicating that all radiation values contribute
        positively to each sky patch.
        """
        return self._benefit_matrix

    @benefit_matrix.setter
    def benefit_matrix(self, value):
        if value is not None:
            assert isinstance(value, (list, tuple)), \
                'SkyMatrix.benefit_matrix must be a list. Not {}'.format(type(value))
            assert len(value) == len(self.wea), 'Length of SkyMatrix.benefit_matrix ' \
                '[{}] must equal the length of the sky matrix Wea [{}].'.format(
                    len(value), len(self.wea))
        self._benefit_matrix = value
        self._direct_values = None
        self._diffuse_values = None
        self._metadata = None

    @property
    def folder(self):
        """Get or set the folder in which the Radiance commands are executed.

        If None, it will be written to Ladybug's default EPW folder.
        """
        if self._folder is None:
            return os.path.join(lb_folders.default_epw_folder, 'sky_matrices')
        return self._folder

    @folder.setter
    def folder(self, value):
        if value is not None:
            assert os.path.isdir(value), 'Path for ' \
                'SkyMatrix folder does not exist: {}'.format(type(value))
        self._folder = value

    @property
    def wea_duration(self):
        """Get the duration of the Wea in hours.

        This is useful for converting the radiation values of the sky patches (kWh/m2)
        into irradiance (W/m2).
        """
        return len(self.wea) / self.wea.timestep

    @property
    def direct_values(self):
        """Get the direct radiation values for each of the sky patches."""
        if self._direct_values is None:
            self.compute_sky()
        return self._direct_values

    @property
    def diffuse_values(self):
        """Get the diffuse radiation values for each of the sky patches."""
        if self._diffuse_values is None:
            self.compute_sky()
        return self._diffuse_values

    @property
    def metadata(self):
        """Get a list of metadata associated with the sky matrix."""
        if self._metadata is None:
            self.compute_sky()
        return self._metadata

    @property
    def data(self):
        """Get a matrix of all data associated with the sky matrix.

        The first list contains metadata, followed by direct values and then
        diffuse values.
        """
        if self._metadata is None:
            self.compute_sky()
        return (self._metadata, self._direct_values, self._diffuse_values)

    def compute_sky(self):
        """Compute the values of the sky matrix."""
        # extract metadata needed for all calculations
        wea_duration = len(self.wea) / self.wea.timestep
        metd = self.wea.direct_normal_irradiance.header.metadata
        wea_basename = metd['city'].replace(' ', '_') if 'city' in metd else 'unnamed'

        # if there's a benefit matrix, split the Wea into two files
        if self.benefit_matrix is not None:
            dir_vals1, dif_vals1, dir_vals2, dif_vals2 = [], [], [], []
            zip_obj = zip(
                self.wea.direct_normal_irradiance,
                self.wea.diffuse_horizontal_irradiance,
                self.benefit_matrix
            )
            for dir_v, dif_v, ben in zip_obj:
                if ben:  # time contributes positively
                    dir_vals1.append(dir_v)
                    dif_vals1.append(dif_v)
                    dir_vals2.append(0)
                    dif_vals2.append(0)
                elif ben is None:  # time is neither positive nor negative
                    dir_vals1.append(0)
                    dif_vals1.append(0)
                    dir_vals2.append(0)
                    dif_vals2.append(0)
                else:  # time contributes negatively
                    dir_vals2.append(dir_v)
                    dif_vals2.append(dif_v)
                    dir_vals1.append(0)
                    dif_vals1.append(0)
            # create the first Wea object
            dir_data1 = self.wea.direct_normal_irradiance.duplicate()
            dif_data1 = self.wea.diffuse_horizontal_irradiance.duplicate()
            dir_data1.values = dir_vals1
            dif_data1.values = dif_vals1
            wea_obj1 = Wea(self.wea.location, dir_data1, dif_data1)
            # create the second Wea object
            dir_data2 = self.wea.direct_normal_irradiance.duplicate()
            dif_data2 = self.wea.diffuse_horizontal_irradiance.duplicate()
            dir_data2.values = dir_vals2
            dif_data2.values = dif_vals2
            wea_obj2 = Wea(self.wea.location, dir_data2, dif_data2)
            # write the Wea files
            wea_path1 = os.path.join(self.folder, '{}_benefit'.format(wea_basename))
            wea_path2 = os.path.join(self.folder, '{}_harm'.format(wea_basename))
            wea_file = wea_obj1.write(wea_path1)
            wea_file2 = wea_obj2.write(wea_path2)
        else:  # otherwise, write the Wea to the folder
            wea_path = os.path.join(self.folder, wea_basename)
            wea_file = self.wea.write(wea_path)
            wea_file2 = None

        # execute the Radiance gendaymtx command
        dir_vals, dif_vals = self._run_gendaymtx(wea_file, wea_duration)
        # if there's a second wea, then use it to compute radiation harm
        if wea_file2 is not None:
            dir_vals2, dif_vals2 = self._run_gendaymtx(wea_file2, wea_duration)
            self._direct_values = tuple(db - dh for db, dh in zip(dir_vals, dir_vals2))
            self._diffuse_values = tuple(db - dh for db, dh in zip(dif_vals, dif_vals2))
        else:
            self._direct_values = dir_vals
            self._diffuse_values = dif_vals

        # collect sky metadata like the north, which will be used by other operations
        metadata = [self.north, self.ground_reflectance]
        dts = self.wea.direct_normal_irradiance.datetimes
        metadata.extend([dts[0], dts[-1]])
        for key, val in self.wea.direct_normal_irradiance.header.metadata.items():
            metadata.append('{} : {}'.format(key, val))
        self._metadata = tuple(metadata)

    def _run_gendaymtx(self, wea_file, wea_duration):
        """Run a Wea file through gendaymtx and get direct and diffuse radiation.

        Args:
            wea_file: Path to a Wea file to be run through gendaymtx.
            wea_duration: Number for the duration of the Wea in hours. This is used
                to convert between the average value output by the command and the
                cumulative value that is needed for all ladybug analyses.
        """
        assert GENDAYMTX_EXE is not None, 'No Radiance installation was found.'
        density = 2 if self.high_density else 1
        use_shell = True if os.name == 'nt' else False
        # command for direct patches
        cmds = [GENDAYMTX_EXE, '-m', str(density), '-d', '-O1', '-A', wea_file]
        process = subprocess.Popen(cmds, stdout=subprocess.PIPE, shell=use_shell)
        stdout = process.communicate()
        dir_data_str = stdout[0]
        # command for diffuse patches
        cmds = [GENDAYMTX_EXE, '-m', str(density), '-s', '-O1', '-A', wea_file]
        process = subprocess.Popen(cmds, stdout=subprocess.PIPE, shell=use_shell)
        stdout = process.communicate()
        diff_data_str = stdout[0]
        # parse the data into a single matrix
        dir_vals = self._parse_mtx_data(dir_data_str, wea_duration, density)
        diff_vals = self._parse_mtx_data(diff_data_str, wea_duration, density)
        return dir_vals, diff_vals

    def _parse_mtx_data(self, data_str, wea_duration, sky_density=1):
        """Parse a string of Radiance gendaymtx data to a list of radiation-per-patch.

        This function handles the removing of the header and the conversion of the
        RGB irradiance=per-steradian values to broadband radiation. It also removes
        the first patch, which is the ground and is not used by Ladybug.

        Args:
            data_str: The string that has been output by gendaymtx to stdout.
            wea_duration: Number for the duration of the Wea in hours. This is used
                to convert between the average value output by the command and the
                cumulative value that is needed for all ladybug analyses.
            sky_density: Integer (either 1 or 2) for the density.
        """
        # split lines and remove the header, ground patch and last line break
        data_lines = data_str.split(self.LINE_BREAK)
        patch_lines = data_lines[9:-1]

        # loop through the rows and convert the radiation RGB values
        broadband_irr = []
        patch_counter = 0
        for i, row_patch_count in enumerate(self.PATCHES_PER_ROW[sky_density]):
            row_slice = patch_lines[patch_counter:patch_counter + row_patch_count]
            irr_vals = (self._broadband_radiation(row, i, wea_duration, sky_density)
                        for row in row_slice)
            broadband_irr.extend(irr_vals)
            patch_counter += row_patch_count
        return tuple(broadband_irr)

    def _broadband_radiation(
            self, patch_row_str, row_number, wea_duration, sky_density=1):
        """Parse a row of gendaymtx RGB patch data in W/sr/m2 to radiation in kWh/m2.

        This includes applying broadband weighting to the RGB bands, multiplication
        by the steradians of each patch, and multiplying by the duration of time that
        they sky matrix represents in hours.

        Args:
            patch_row_str: Text string for a single row of RGB patch data.
            row_number: Integer for the row number that the patch corresponds to.
            sky_density: Integer (either 1 or 2) for the density.
            wea_duration: Number for the duration of the Wea in hours. This is used
                to convert between the average value output by the command and the
                cumulative value that is needed for all ladybug analyses.
        """
        R, G, B = patch_row_str.split(self.SEPARATOR)
        w_val = 0.265074126 * float(R) + 0.670114631 * float(G) + 0.064811243 * float(B)
        coeff = self.PATCH_ROW_COEFF[sky_density][row_number]
        return w_val * coeff * wea_duration / 1000

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __len__(self):
        if self._direct_values is None:
            self.compute_sky()
        return len(self._direct_values)

    def __getitem__(self, key):
        if self._direct_values is None:
            self.compute_sky()
        return self._direct_values[key], self._diffuse_values[key]

    def __iter__(self):
        if self._direct_values is None:
            self.compute_sky()
        return zip(self._direct_values, self._diffuse_values)

    def __repr__(self):
        """Sky Matrix object representation."""
        return "SkyMatrix [%s]" % self.wea.location.city
