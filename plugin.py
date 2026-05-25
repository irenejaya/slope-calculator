# -*- coding: utf-8 -*-
"""
River Slope Calculator - Main Plugin Class

Registers a Processing provider and a toolbar action that opens the native
QGIS Processing algorithm dialog for Compute Reach Slope.
"""

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from .provider import SlopeCalculatorProvider


class SlopeCalculatorPlugin:
    """Main plugin class for River Slope Calculator."""

    def __init__(self, iface):
        """
        Initialize the plugin.

        Args:
            iface: QGIS interface instance
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu_name = "River Slope Calculator"
        self.toolbar = None
        self.provider = None

    def tr(self, message):
        """Translate string."""
        return QCoreApplication.translate('SlopeCalculatorPlugin', message)

    def initProcessing(self):
        """Register the Processing provider."""
        self.provider = SlopeCalculatorProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Initialize the GUI - called when plugin is loaded."""
        self.initProcessing()

        # Create toolbar
        self.toolbar = self.iface.addToolBar(self.menu_name)
        self.toolbar.setObjectName("SlopeCalculatorToolbar")

        # ---- River Slope Calculator action ----
        icon_path = os.path.join(self.plugin_dir, 'icon.svg')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action_slope = QAction(
            icon,
            self.tr("River Slope Calculator"),
            self.iface.mainWindow()
        )
        self.action_slope.setToolTip(
            "Compute reach slope from DEM\n"
            "(Average Slope & Equal Area Slope)"
        )
        self.action_slope.triggered.connect(self.run_slope)
        self.toolbar.addAction(self.action_slope)
        self.iface.addPluginToMenu(self.menu_name, self.action_slope)
        self.actions.append(self.action_slope)

    def run_slope(self):
        """Open the native QGIS Processing algorithm dialog."""
        from qgis import processing
        processing.execAlgorithmDialog('slope_calculator:compute_slope')

    def unload(self):
        """Unload the plugin - called when plugin is unloaded."""
        # Remove menu items
        for action in getattr(self, 'actions', []):
            self.iface.removePluginMenu(self.menu_name, action)
            self.iface.removeToolBarIcon(action)

        # Remove toolbar
        if getattr(self, 'toolbar', None):
            del self.toolbar
            self.toolbar = None

        # Remove Processing provider
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
