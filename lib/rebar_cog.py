from Autodesk.Revit import DB
import math

FEET_TO_MM = 304.8  # Conversion from feet to mm


class RebarCoG:
    def __init__(self, rebar_collector):
        """Calculates rebar CoG
        Arguments:
        rebar_collector: DB.FilteredElementCollector
        """
        self.rebar_collector = rebar_collector
        self.multiplanaroption = DB.Structure.MultiplanarOption.IncludeAllMultiplanarCurves

    @staticmethod
    def _is_rebar_group(rebar_object):
        """Checks if object is a rebar group
        Arg:
            rebar_object: DB.Structure.Rebar"""
        n_bars = rebar_object.NumberOfBarPositions
        if n_bars > 1:
            return True
        else:
            return False

    @staticmethod
    def _compute_segment_centroid(curve, diameter, index):
        """Computes segment centroid.
        Arguments:
        curve (DB.Line or DB.Curve)
        diameter (float)
        Returns:
        list[centroid, mass]
            where:
            centroid(list) - [x(float), y(float), z(float)] in mm
            mass - float value in kg
        """
        # Conversion from feet to mm
        r_o = 7.85e-6  # kg/mm3
        r = diameter / 2  # mm
        area = math.pi * r**2
        length = curve.Length * FEET_TO_MM
        volume = area * length
        mass = volume * r_o
        r = diameter / 2  # mm
        if isinstance(curve, DB.Line):
            sp_X = curve.GetEndPoint(0).X * FEET_TO_MM
            sp_Y = curve.GetEndPoint(0).Y * FEET_TO_MM
            sp_Z = curve.GetEndPoint(0).Z * FEET_TO_MM
            ep_X = curve.GetEndPoint(1).X * FEET_TO_MM
            ep_Y = curve.GetEndPoint(1).Y * FEET_TO_MM
            ep_Z = curve.GetEndPoint(1).Z * FEET_TO_MM
            cp_X = (sp_X + ep_X) / 2
            cp_Y = (sp_Y + ep_Y) / 2
            cp_Z = (sp_Z + ep_Z) / 2
            # centroid = DB.XYZ(cp_X, cp_Y, cp_Z)
            centroid = [cp_X, cp_Y, cp_Z]
            return centroid, mass
        if isinstance(curve, DB.Arc):
            arc_radius = curve.Radius * FEET_TO_MM
            arc_center_X = curve.Center.X * FEET_TO_MM
            arc_center_Y = curve.Center.Y * FEET_TO_MM
            arc_center_Z = curve.Center.Z * FEET_TO_MM
            # Midpoint of arc
            a_mp_X = curve.Evaluate(0.5, True).X * FEET_TO_MM
            a_mp_Y = curve.Evaluate(0.5, True).Y * FEET_TO_MM
            a_mp_Z = curve.Evaluate(0.5, True).Z * FEET_TO_MM
            # Calculate 'x' coordinate of centroid for arc
            circumference = 2 * math.pi * arc_radius
            theta = math.radians(length / circumference * 360)
            alpha = theta / 2
            # Scalar value [mm]
            radius2 = arc_radius + r
            radius1 = arc_radius - r
            # TODO: Check results with p computed for annular sector, is it better?
            p = (2 * math.sin(alpha) / (3 * alpha)) * (radius2**3 - radius1**3) / (radius2**2 - radius1**2)
            # p = arc_radius * math.sin(alpha) / alpha
            # Calculate a line vector and unit vector between center and midpoint
            v_X = a_mp_X - arc_center_X
            v_Y = a_mp_Y - arc_center_Y
            v_Z = a_mp_Z - arc_center_Z
            # Calculate line length
            v_L = math.sqrt(v_X**2 + v_Y**2 + v_Z**2)
            # Calculate unit vector
            if v_L != 0:
                u_X = v_X / v_L
                u_Y = v_Y / v_L
                u_Z = v_Z / v_L
            else:
                raise ZeroDivisionError
            # Centroid point
            cp_X = arc_center_X + p * u_X
            cp_Y = arc_center_Y + p * u_Y
            cp_Z = arc_center_Z + p * u_Z
            # centroid = DB.XYZ(cp_X, cp_Y, cp_Z)
            centroid = [cp_X, cp_Y, cp_Z]  # OK
            return centroid, mass

    @staticmethod
    def _compute_centroid(list_of_centroids, list_of_masses):
        """
        Arguments:
        List of centroids - centroid of each segment of bar
        List of masses - mass for each segment of bar
        Structure:
        List of centroids [x,y,z], [x,y,z],
        List of masses [M1, M2, M3]
        Returns:
        list of coordinates of CoG [x, y, z]"""

        coord_mass = [[list_of_masses[i] * j for j in sub] for i, sub in enumerate(list_of_centroids)]
        # coord_mass = [[xM1, yM1,zM1], [xM2, yM2, zM2], ...]
        sum_xm = sum(i[0] for i in coord_mass)
        sum_ym = sum(i[1] for i in coord_mass)
        sum_zm = sum(i[2] for i in coord_mass)
        sum_mass = sum(list_of_masses)
        if sum_mass != 0:
            cog_x = sum_xm / sum_mass
            cog_y = sum_ym / sum_mass
            cog_z = sum_zm / sum_mass
            return [cog_x, cog_y, cog_z], sum_mass
        else:
            raise ZeroDivisionError

    @staticmethod
    def _get_rebar_diam(rebar):
        diam = rebar.LookupParameter("Bar Diameter")
        return diam.AsDouble() * 304.8

    @staticmethod
    def _get_existing_bar_index(bar_object):
        """Checks if rebar exists at given position (can be hidden or removed)
        Arguments:
            rebar_object(DB.Structure.Rebar): the rebar object
        Returns:
            indexes(list(int))"""
        indexes = []
        n_bars = bar_object.NumberOfBarPositions
        for i in range(0, n_bars):
            if bar_object.DoesBarExistAtPosition(i):
                indexes.append(i)
        return indexes

    def _get_curve_from_group(self, rebar, index):
        """Returns a curve from rebar at given index from rebar group
        Arguments:
            rebar (DB.Structure.Rebar): the rebar object
            index (int): the index of a bar in group
        Returns:
            DB.Line or DB.Curve"""
        if (
            rebar.DistributionType == DB.Structure.DistributionType.Uniform
            or DB.Structure.DistributionType.VaryingLength
        ):
            rebar_curve = rebar.GetTransformedCenterlineCurves(False, False, False, self.multiplanaroption, index)
        else:
            rebar_curve = rebar.GetCenterlineCurves(False, False, False, self.multiplanaroption, index)
        return rebar_curve

    def get_cog(self):
        """Calculates the CoG and mass of selected rebars
        Returns:
            list[list[float], float]"""
        all_bar_centroids = []
        all_bar_masses = []
        for rebar in self.rebar_collector:
            rebar_diam = self._get_rebar_diam(rebar)
            # Check if rebar object is group
            if self._is_rebar_group(rebar_object=rebar):
                # Compute centroid for each bar in group
                for i in self._get_existing_bar_index(rebar):
                    rebar_curve = self._get_curve_from_group(rebar, i)
                    # Compute centroid for each segment
                    centroids = []
                    masses = []
                    for curve in rebar_curve:
                        segment_centroid = self._compute_segment_centroid(curve, rebar_diam, i)
                        centroids.append(segment_centroid[0])
                        masses.append(segment_centroid[1])
                        # Compute centroid and total mass for each bar
                    cog = self._compute_centroid(centroids, masses)[0]
                    mass = self._compute_centroid(centroids, masses)[1]
                    # Add to global list
                    all_bar_centroids.append(cog)
                    all_bar_masses.append(mass)
            else:  # single rebar object
                index = 0
                # Get bar curves
                rebar_curve = rebar.GetCenterlineCurves(False, False, False, self.multiplanaroption, index)
                # Compute centroid for each segment
                centroids = []
                masses = []
                for curve in rebar_curve:
                    segment_centroid = self._compute_segment_centroid(curve, rebar_diam, index)
                    centroids.append(segment_centroid[0])
                    masses.append(segment_centroid[1])
                    # Compute centroid and total mass for each bar
                cog = self._compute_centroid(centroids, masses)[0]
                mass = self._compute_centroid(centroids, masses)[1]
                # Add to global list
                all_bar_centroids.append(cog)
                all_bar_masses.append(mass)
        final_cog = self._compute_centroid(all_bar_centroids, all_bar_masses)[0]
        total_mass = self._compute_centroid(all_bar_centroids, all_bar_masses)[1]
        return final_cog, total_mass
