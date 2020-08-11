# Module for computing conversions from latitude / longitude to Universal
# Transverse Mercator (UTM) coordinates.
#
# This file is formatted using the Black code formatter:
# https://github.com/psf/black

import numpy as np

# See:
# https://www.ccgalberta.com/ccgresources/report11/2009-410_converting_latlon_to_utm.pdf
# http://www.gpsy.com/gpsinfo/geotoutm/gantz/LatLong-UTMconversion.cpp.txt

# Constants:
# Values are for the WGS84 ellipsoid (aka EPSG:4326).

# Equatorial radius / semi-major axis (m)
S_MAJ = 6378137

# Inverse flattening
INV_FLAT = 298.257223563

# Point scale factor at central meridian
K0 = 0.9996

# Flattening
FLAT = 1 / INV_FLAT

# Powers of first eccentricity (e^2, e^4, e^6)
E2 = (2 * FLAT) - (FLAT * FLAT)
E4 = E2 * E2
E6 = E2 * E2 * E2

# Second eccentricity squared
EP2 = E2 / (1.0 - E2)

# Coefficients for computation of M:
M1 = 1 - (E2 / 4) - (3 * E4 / 64) - (5 * E6 / 256)
M2 = (3 * E2 / 8) + (3 * E4 / 32) + (45 * E6 / 1024)
M3 = (15 * E4 / 256) + (45 * E6 / 1024)
M4 = 35 * E6 / 3072


def get_central_longitude(lon_deg):
    """Get the central meridian for the zone corresponding to a longitude.

    This function determines the zone that a longitude corresponds to, and the
    central meridian for that zone, all in one step.

    See also http://www.jaworski.ca/utmzones.htm.

    Args:
        lon_deg: Longitude for which to compute the central meridian, in degrees.
            Positive values are interpreted as longitudes east of the Prime
            Meridian.

            This may be a regular `float`, a NumPy array, or a Pandas
            Series.
            If this parameter is array-like, it must be one-dimensional.
    
    Returns:
        The longitude(s) of the central meridian(s) for each input longitude.

        The returned longitudes will be integers, though if the input `lon_deg`
        is a NumPy array or similar, the output will also be as such.
        Positive values indicate longitudes east of the Prime Meridian.

    Examples:
        Knoxville, TN's longitude is 83W. This corresponds to Zone 17, for
        which the central meridian is at 81W:
        >>> get_central_longitude(-83.9232)
        -81.0

        Get the central meridians for Knoxville, TN; Chicago, IL; and Tokyo, JP
        (83W, 87W, and 139E, respectively) as a NumPy array:
        >>> get_central_longitude(np.array([-83.92, -87.63, 139.69]))
        array([-81., -87., 141.])
    """
    return ((lon_deg // -6) * -6) - 3


def convert_to_utm(lat_deg, lon_deg, central_lon_deg):
    """Convert latitude / longitude coordinate pairs to UTM coordinates.

    This function computes UTM easting/northing coordinate pairs from
    latitude/longitude pairs, given the longitude of the central meridian for
    each pair.

    Args:
        lat_deg: Latitudes from which to compute UTM coordinates, in degrees.
            Positive values are interpreted as north of the Equator.
            
            This may be of any type that NumPy can operate on, such as regular
            `float` or `int` values, NumPy arrays, or even Pandas Series objects.
            Array-like parameter values must be one-dimensional.
        
        lon_deg: Longitudes from which to compute UTM coordinates, in degrees.
            Positive values are interpreted as east of the Prime Meridian.

            Like `lat_deg`, this can be of any scalar or one-dimensional type
            compatible with NumPy.

            However, the type and shape (if applicable) of this argument must
            be compatible with the other arguments, though the NumPy
            broadcasting rules apply here.

        central_lon_deg: The longitudes of the central meridians for each input
            coordinate pair, in degrees.

            Like `lat_deg` and `lon_deg`, this can be of any scalar or
            one-dimensional type compatible with NumPy, provided that the type
            and shape are compatible with the other arguments.

    Returns:
        A tuple containing the UTM coordinates corresponding to each input
        latitude and longitude pair, in meters.
        
        Note that the origin for any pair of UTM coordinates is the point where
        the central meridian for its zone intersects the Equator.

        The output types will match that of the inputs: if all scalar values
        are passed in, all scalar values will be returned.

        However, if any of the inputs are NumPy arrays (or are objects that are
        convertible to NumPy arrays, such as Pandas Series objects), the outputs
        will both be NumPy arrays.

    Examples:
        The latitudes/longitudes for the following example locations can be
        found on GeoHack.

        A reference UTM conversion tool from the National Geodetic Survey can
        be found at https://geodesy.noaa.gov/NCAT/.

        | Location      | Latitude/Longitude      | UTM Coordinates        |
        |---------------|-------------------------|------------------------|
        | Knoxville, TN | 35.9617N,   83.9232W    | 236375.816 3983651.642 |
        | Chicago, IL   | 41.881944N, 87.627778W  | 447912.816 4636859.243 |
        | Tokyo, JP     | 35.689722N, 139.692222E | 381669.792 3950322.902 |
        
        Get the UTM coordinates for a single point (Chicago, IL).
        The calculations match the reference tool given above to 2 decimal
        digits, though I'm not sure how useful that will actually be in reality.

        >>> x, y = convert_to_utm(41.881944, -87.627778, -87)
        >>> np.round(x)
        447913.0
        >>> np.round(y)
        4636859.0
        >>> x_cm = np.round(x * 100)
        >>> x_cm
        44791282.0
        >>> y_cm = np.round(y * 100)
        >>> y_cm
        463685924.0

        Get the UTM coordinates for multiple points:
        >>> lat = np.array([35.9617, 41.881944, 35.689722])
        >>> lon = np.array([-83.9232, -87.627778, 139.692222])
        >>> cent_lon = get_central_longitude(lon)
        >>> x, y = convert_to_utm(lat, lon, cent_lon)
        >>> np.round(x)
        array([236376., 447913., 381670.])
        >>> np.round(y)
        array([3983652., 4636859., 3950323.])
    """

    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    cent_lon = np.radians(central_lon_deg)

    # Precomputation:
    N = S_MAJ / np.sqrt(1 - E2 * np.power(np.sin(lat), 2))
    T = np.power(np.tan(lat), 2)
    C = EP2 * np.power(np.cos(lat), 2)
    A = (lon - cent_lon) * np.cos(lat)
    M = S_MAJ * (
        (M1 * lat)
        - (M2 * np.sin(2 * lat))
        + (M3 * np.sin(4 * lat))
        - (M4 * np.sin(6 * lat))
    )

    # Easting:
    x = (
        K0
        * N
        * (
            A
            + ((1 - T + C) * A * A * A / 6)
            + ((5 - (18 * T) + (T * T) + (72 * C) - (58 * EP2)) * np.power(A, 5) / 120)
        )
    )

    # Northing:
    y = K0 * (
        M
        + N
        * np.tan(lat)
        * (
            (A * A / 2)
            + ((5 - T + (9 * C) + (4 * C * C)) * np.power(A, 4) / 24)
            + (
                (61 - (58 * T) + (T * T) + (600 * C) - (330 * EP2))
                * np.power(A, 6)
                / 720
            )
        )
    )

    # N0 = 10,000 km in the Southern Hemisphere.
    y += (lat_deg < 0) * 10000000
    x += 500000  # E0 = 500 km

    return (x, y)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
