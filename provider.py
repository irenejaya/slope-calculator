# -*- coding: utf-8 -*-
"""
River Slope Calculator - Processing Provider

Registers the Compute Reach Slope algorithm under the
"River Slope Calculator" provider in the QGIS Processing Toolbox.
"""

import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon


class SlopeCalculatorProvider(QgsProcessingProvider):
    """Processing provider for the River Slope Calculator plugin."""

    def id(self):
        return 'slope_calculator'

    def name(self):
        return 'River Slope Calculator'

    def longName(self):
        return 'River Slope Calculator'

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QgsProcessingProvider.icon(self)

    def loadAlgorithms(self):
        from .algorithms.reach_slope import ReachSlopeAlgorithm
        self.addAlgorithm(ReachSlopeAlgorithm())
