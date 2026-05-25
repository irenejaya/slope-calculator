# -*- coding: utf-8 -*-
"""
River Slope Calculator - QGIS Plugin

Computes the slope of each river reach feature (line / multiline) from an
underlying DEM raster using either:
  1. Average Slope  (Mean Gradient)  :  S = |ΔH| / L
  2. Equal Area Slope                :  S_ea = 2·A_d / L²
"""

__author__ = 'Irene Jaya'
__date__ = '2026-05-23'
__copyright__ = '(C) 2026, Irene Jaya'


def classFactory(iface):
    """
    Load the plugin class.

    Args:
        iface: A QGIS interface instance

    Returns:
        SlopeCalculatorPlugin instance
    """
    from .plugin import SlopeCalculatorPlugin
    return SlopeCalculatorPlugin(iface)
