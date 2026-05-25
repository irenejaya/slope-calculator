# -*- coding: utf-8 -*-
"""
Slope calculation utilities for the River Slope Calculator plugin.

Provides DEM sampling along a line geometry and two slope methods:
  1. Average Slope  (Mean Gradient)  :  S = |ΔH| / L
  2. Equal Area Slope                :  S_ea = 2·A_d / L²
"""

from typing import List, Tuple, Optional

from qgis.core import QgsPointXY


def sample_dem_at_endpoints(geometry, dem_provider, transform=None):
    """Sample DEM elevation at the start and end points of a line/multiline.

    Used for Average Slope — avoids building a full profile.

    Returns:
        Tuple (z_start, z_end) in DEM elevation units, or None if either
        sample failed (no-data or outside DEM extent).
    """
    crs_length = geometry.length()
    if crs_length <= 0:
        return None

    start_geom = geometry.interpolate(0.0)
    end_geom = geometry.interpolate(crs_length)
    if start_geom.isEmpty() or end_geom.isEmpty():
        return None

    pts = [start_geom.asPoint(), end_geom.asPoint()]
    if transform is not None:
        try:
            pts = [transform.transform(p) for p in pts]
        except Exception:
            return None

    elevations = []
    for pt in pts:
        val, ok = dem_provider.sample(QgsPointXY(pt.x(), pt.y()), 1)
        if not ok:
            return None
        elevations.append(val)

    return tuple(elevations)


def sample_dem_along_line(
    geometry,
    dem_provider,
    interval_m: float,
    metric_length: float,
    transform=None,
) -> List[Tuple[float, float]]:
    """Sample DEM elevations at regular intervals along a line/multiline geometry.

    Args:
        geometry:       QgsGeometry (Line or MultiLine).
        dem_provider:   QgsRasterDataProvider of the DEM layer.
        interval_m:     Sampling interval in metres.
        metric_length:  True reach length in metres (from QgsDistanceArea).
        transform:      QgsCoordinateTransform (reach CRS → DEM CRS), or None.

    Returns:
        List of (distance_m, elevation) tuples ordered from geometry start.
        Returns an empty list if the geometry is empty or all samples are NoData.
    """
    crs_length = geometry.length()
    if crs_length <= 0 or metric_length <= 0:
        return []

    # Scale factor: CRS-unit distances → metres
    scale = metric_length / crs_length

    # Sampling step in CRS units
    interval_crs = interval_m / scale
    n_steps = max(2, int(crs_length / interval_crs))

    result: List[Tuple[float, float]] = []
    seen: set = set()

    distances_crs = [i * interval_crs for i in range(n_steps + 1)]
    # Always include the exact endpoint
    if distances_crs[-1] < crs_length:
        distances_crs.append(crs_length)

    for d_crs in distances_crs:
        d_crs = min(d_crs, crs_length)
        d_key = round(d_crs, 9)
        if d_key in seen:
            continue
        seen.add(d_key)

        pt_geom = geometry.interpolate(d_crs)
        if pt_geom.isEmpty():
            continue
        pt = pt_geom.asPoint()

        if transform is not None:
            try:
                pt = transform.transform(pt)
            except Exception:
                continue

        val, ok = dem_provider.sample(QgsPointXY(pt.x(), pt.y()), 1)
        if ok:
            result.append((d_crs * scale, val))

    return result


def calc_average_slope(profile: List[Tuple[float, float]]) -> Optional[float]:
    """Average Slope (Mean Gradient): S = |ΔH| / L.

    Absolute elevation difference between the first and last sampled points
    divided by the total reach length.
    """
    if len(profile) < 2:
        return None
    L = profile[-1][0] - profile[0][0]
    if L <= 0:
        return None
    delta_h = abs(profile[0][1] - profile[-1][1])
    return delta_h / L


def calc_equal_area_slope(profile: List[Tuple[float, float]]) -> Optional[float]:
    """Equal Area Slope: S_ea = 2·A_d / L².

    Slope of a straight line through the outlet (downstream end) that creates
    equal areas above and below the longitudinal elevation profile.

    Reference: Ladson (2017); NZ Ministry of Works (1980); ARR 1987 §1.3.2(d).
    """
    if len(profile) < 2:
        return None

    # Orient profile so profile[0] is the downstream (lower) end.
    if profile[0][1] > profile[-1][1]:
        d0 = profile[0][0]
        span = profile[-1][0] - d0
        profile = [(span - (d - d0), h) for d, h in reversed(profile)]

    h_outlet = profile[0][1]
    d_start = profile[0][0]
    L = profile[-1][0] - d_start
    if L <= 0:
        return None

    # Trapezoidal integration of h(x) = elevation(x) - h_outlet
    A_d = 0.0
    for i in range(1, len(profile)):
        d_prev = profile[i - 1][0] - d_start
        d_curr = profile[i][0] - d_start
        h_prev = profile[i - 1][1] - h_outlet
        h_curr = profile[i][1] - h_outlet
        dx = d_curr - d_prev
        A_d += (h_prev + h_curr) * 0.5 * dx

    A_d = abs(A_d)
    return (2.0 * A_d) / (L * L)
