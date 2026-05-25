# -*- coding: utf-8 -*-
"""
River Slope Calculator - Compute Reach Slope Algorithm

Computes slope for each reach feature (line / multiline) from an underlying DEM
using:
  1. Average Slope  (Mean Gradient)  :  S = |ΔH| / L
  2. Equal Area Slope                :  S_ea = 2·A_d / L²

Runs inside the native QGIS Processing framework — the standard Processing
algorithm dialog is used as the UI.
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsFeature,
    QgsFeatureSink,
    QgsFields,
    QgsField,
    QgsDistanceArea,
    QgsCoordinateTransform,
    QgsProject,
    NULL,
)

try:
    # Qt6 / QGIS 3.34+ preferred path
    from qgis.PyQt.QtCore import QMetaType
    _DOUBLE_TYPE = QMetaType.Type.Double
    _USE_QMETATYPE = True
except Exception:
    from qgis.PyQt.QtCore import QVariant
    _DOUBLE_TYPE = QVariant.Double
    _USE_QMETATYPE = False

from ..utils.constants import (
    DEFAULT_SAMPLING_INTERVAL,
    DEFAULT_FIELD_AVERAGE,
    DEFAULT_FIELD_EAS,
    UNIT_CHOICES,
    UNIT_MULTIPLIERS,
)
from ..utils.slope_utils import (
    sample_dem_at_endpoints,
    sample_dem_along_line,
    calc_average_slope,
    calc_equal_area_slope,
)


def _make_double_field(name: str) -> QgsField:
    """Create a double field compatible with Qt5 and Qt6 builds."""
    return QgsField(name, _DOUBLE_TYPE, 'double', 20, 8)


class ReachSlopeAlgorithm(QgsProcessingAlgorithm):
    """Calculate reach slope from a DEM using Average Slope and/or Equal Area Slope."""

    INPUT = 'INPUT'
    DEM = 'DEM'
    METHOD = 'METHOD'
    INTERVAL = 'INTERVAL'
    FIELD_AVERAGE = 'FIELD_AVERAGE'
    FIELD_EAS = 'FIELD_EAS'
    UNIT = 'UNIT'
    OUTPUT = 'OUTPUT'

    METHOD_CHOICES = ['Average Slope', 'Equal Area Slope', 'Both']

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    def name(self):
        return 'compute_slope'

    def displayName(self):
        return 'Compute Reach Slope'

    def group(self):
        return 'River Slope Calculator'

    def groupId(self):
        return 'slope_calculator'

    def shortHelpString(self):
        return (
            '<b>Compute Reach Slope</b><br><br>'
            'Calculates the slope of each reach feature from an underlying DEM '
            'by sampling elevations at a regular interval along the line.<br><br>'
            '<b>Method 1 — Average Slope (Mean Gradient)</b><br>'
            '<code>S = |ΔH| / L</code><br>'
            'Absolute elevation difference between reach endpoints divided by '
            'the total reach length. Simple and robust.<br><br>'
            '<b>Method 2 — Equal Area Slope</b><br>'
            '<code>S<sub>ea</sub> = 2·A<sub>d</sub> / L²</code><br>'
            'Slope of a line through the outlet with equal enclosed areas above '
            'and below the longitudinal profile. Used in ARR 1987 Bransby Williams '
            'time-of-concentration formula.<br><br>'
            '<b>Output:</b> Copy of the reach layer with one or two new slope '
            'fields. Unit is selectable: <b>m/m</b> (dimensionless) or '
            '<b>%</b> (percent).<br><br>'
            '<b>Note:</b> DEM elevation values must be in metres.'
        )

    def createInstance(self):
        return ReachSlopeAlgorithm()

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT,
            'Reach layer (line / multiline)',
            [QgsProcessing.SourceType.TypeVectorLine],
        ))

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.DEM,
            'DEM raster (elevation in metres)',
        ))

        self.addParameter(QgsProcessingParameterEnum(
            self.METHOD,
            'Method',
            options=self.METHOD_CHOICES,
            defaultValue=2,
        ))

        self.addParameter(QgsProcessingParameterNumber(
            self.INTERVAL,
            'Sampling interval — metres (used for Equal Area Slope)',
            type=QgsProcessingParameterNumber.Type.Double,
            minValue=0.1,
            defaultValue=DEFAULT_SAMPLING_INTERVAL,
        ))

        self.addParameter(QgsProcessingParameterString(
            self.FIELD_AVERAGE,
            'Average Slope field name',
            defaultValue=DEFAULT_FIELD_AVERAGE,
        ))

        self.addParameter(QgsProcessingParameterString(
            self.FIELD_EAS,
            'Equal Area Slope field name',
            defaultValue=DEFAULT_FIELD_EAS,
        ))

        self.addParameter(QgsProcessingParameterEnum(
            self.UNIT,
            'Output unit',
            options=UNIT_CHOICES,
            defaultValue=0,
        ))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT,
            'Output reach layer with slope fields',
        ))

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def processAlgorithm(self, parameters, context, feedback):
        reaches = self.parameterAsSource(parameters, self.INPUT, context)
        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)
        interval = self.parameterAsDouble(parameters, self.INTERVAL, context)
        field_avg = self.parameterAsString(parameters, self.FIELD_AVERAGE, context).strip() or DEFAULT_FIELD_AVERAGE
        field_eas = self.parameterAsString(parameters, self.FIELD_EAS, context).strip() or DEFAULT_FIELD_EAS
        unit_idx = self.parameterAsEnum(parameters, self.UNIT, context)
        unit_multiplier = UNIT_MULTIPLIERS[unit_idx]

        do_avg = method_idx in (0, 2)
        do_eas = method_idx in (1, 2)

        if reaches is None:
            raise QgsProcessingException('Invalid reach layer.')
        if dem_layer is None or not dem_layer.isValid():
            raise QgsProcessingException('Invalid DEM raster.')

        dem_provider = dem_layer.dataProvider()

        # Build output fields (copy input + new slope fields)
        out_fields = QgsFields(reaches.fields())
        if do_avg:
            out_fields.append(_make_double_field(field_avg))
        if do_eas:
            out_fields.append(_make_double_field(field_eas))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields,
            reaches.wkbType(),
            reaches.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException('Could not create output sink.')

        # CRS transform: reach layer → DEM CRS (for sampling)
        reach_crs = reaches.sourceCrs()
        dem_crs = dem_layer.crs()
        transform = (
            QgsCoordinateTransform(reach_crs, dem_crs, QgsProject.instance())
            if reach_crs != dem_crs else None
        )

        # Distance area for metric length calculation
        da = QgsDistanceArea()
        da.setSourceCrs(reach_crs, QgsProject.instance().transformContext())
        da.setEllipsoid(QgsProject.instance().ellipsoid())

        total = reaches.featureCount()
        null_count = 0
        n_input_fields = reaches.fields().count()

        for i, feat in enumerate(reaches.getFeatures()):
            if feedback.isCanceled():
                break

            feedback.setProgress(int(i / total * 100) if total > 0 else 0)

            geom = feat.geometry()
            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(geom)

            for j in range(n_input_fields):
                out_feat.setAttribute(j, feat.attribute(j))

            slope_avg = None
            slope_eas = None

            if geom is None or geom.isEmpty():
                feedback.pushWarning(
                    'Feature {}: empty geometry — skipped.'.format(feat.id())
                )
                null_count += 1
            else:
                try:
                    metric_len = da.measureLength(geom)

                    if do_eas:
                        profile = sample_dem_along_line(
                            geom, dem_provider, interval, metric_len, transform
                        )
                        if len(profile) < 2:
                            feedback.pushWarning(
                                'Feature {}: fewer than 2 valid DEM samples — '
                                'check DEM coverage.'.format(feat.id())
                            )
                            null_count += 1
                        else:
                            slope_eas = calc_equal_area_slope(profile)
                            if do_avg:
                                slope_avg = calc_average_slope(profile)
                    elif do_avg:
                        endpoints = sample_dem_at_endpoints(
                            geom, dem_provider, transform
                        )
                        if endpoints is None:
                            feedback.pushWarning(
                                'Feature {}: could not sample DEM at endpoints.'
                                .format(feat.id())
                            )
                            null_count += 1
                        else:
                            z_start, z_end = endpoints
                            if metric_len > 0:
                                slope_avg = abs(z_start - z_end) / metric_len

                except Exception as e:
                    feedback.pushWarning(
                        'Feature {} error: {}'.format(feat.id(), e)
                    )
                    null_count += 1

            attr_idx = n_input_fields
            if do_avg:
                out_feat.setAttribute(
                    attr_idx,
                    slope_avg * unit_multiplier if slope_avg is not None else NULL,
                )
                attr_idx += 1
            if do_eas:
                out_feat.setAttribute(
                    attr_idx,
                    slope_eas * unit_multiplier if slope_eas is not None else NULL,
                )

            sink.addFeature(out_feat, QgsFeatureSink.Flag.FastInsert)

        feedback.setProgress(100)

        if null_count:
            feedback.pushWarning(
                '{} feature(s) produced NULL slope values. '
                'Check DEM coverage and CRS settings.'.format(null_count)
            )

        return {self.OUTPUT: dest_id}
