# -*- coding: utf-8 -*-
"""Constants for the River Slope Calculator plugin."""

# Default EAS sampling interval (metres)
DEFAULT_SAMPLING_INTERVAL = 1.0

# Default output field names
DEFAULT_FIELD_AVERAGE = 'avg_slope'
DEFAULT_FIELD_EAS = 'eas_slope'

# Output unit choices (index matches UNIT_CHOICES list in the algorithm)
UNIT_CHOICES = ['m/m (dimensionless)', '% (percent)']
UNIT_MULTIPLIERS = [1.0, 100.0]
