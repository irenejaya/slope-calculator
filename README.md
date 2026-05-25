# River Slope Calculator

A QGIS plugin that calculates the slope of river reach features from an underlying DEM raster.

Provides two slope methods commonly used in hydrology and hydraulic modelling:

1. **Average Slope (Mean Gradient)** — `S = |ΔH| / L`
2. **Equal Area Slope** — `S_ea = 2·A_d / L²` (ARR 1987, Bransby Williams)

Runs inside the native QGIS Processing framework, so it works from the Processing Toolbox, the model designer, the graphical modeler, and PyQGIS scripts.

---

## Requirements

- QGIS **3.34** or newer (Qt5 and Qt6 builds both supported)
- A reach layer (line or multiline vector)
- A DEM raster with elevation values in **metres**

---

## Installation

### From ZIP

1. Download the latest [release ZIP](https://github.com/irenejaya/slope-calculator/releases) (or build one with `Compress-Archive -Path riverslopecalculator -DestinationPath riverslopecalculator.zip`).
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the ZIP file and click **Install Plugin**.

### From the QGIS Plugin Repository

Once approved, the plugin will be installable from **Plugins → Manage and Install Plugins → All** by searching for *River Slope Calculator*.

---

## Usage

After installation:

- A **River Slope Calculator** toolbar button appears in QGIS.
- A **River Slope Calculator** provider appears in the **Processing Toolbox** containing the *Compute Reach Slope* algorithm.

### Compute Reach Slope — Parameters

| Parameter | Description |
|---|---|
| **Reach layer** | Line / multiline vector layer of river reaches. |
| **DEM raster** | Elevation raster in metres. Can be in a different CRS than the reach layer (an automatic transform is applied). |
| **Method** | `Average Slope`, `Equal Area Slope`, or `Both` (default). |
| **Sampling interval (m)** | Spacing of DEM samples along each reach for the Equal Area Slope. Default: `10` m. |
| **Average Slope field name** | Output field name. Default: `avg_slope`. |
| **Equal Area Slope field name** | Output field name. Default: `eas_slope`. |
| **Output** | Copy of the input reach layer with the requested slope field(s) appended. |

Slope values are **dimensionless** (m/m).

### From PyQGIS

```python
import processing

processing.run("slope_calculator:compute_slope", {
    'INPUT': 'reaches.shp',
    'DEM': 'dem.tif',
    'METHOD': 2,          # 0=Average, 1=Equal Area, 2=Both
    'INTERVAL': 10.0,
    'FIELD_AVERAGE': 'avg_slope',
    'FIELD_EAS': 'eas_slope',
    'OUTPUT': 'memory:',
})
```

---

## Method Details

### Average Slope

The absolute elevation difference between reach endpoints divided by the reach length:

$$S = \frac{|H_{start} - H_{end}|}{L}$$

Simple, robust, and the most commonly reported reach slope.

### Equal Area Slope

The slope of a straight line drawn through the outlet such that the areas enclosed by the line and the longitudinal profile are equal above and below the line:

$$S_{ea} = \frac{2 \cdot A_d}{L^2}$$

where $A_d$ is the area between the actual longitudinal profile and the horizontal at the outlet, computed by trapezoidal integration of DEM samples taken at the user-defined interval.

Adopted in **Australian Rainfall and Runoff (ARR, 1987)** for the Bransby Williams time-of-concentration formula.

**References**

- Ladson, A. (2017). *Hydrology — An Australian Introduction*.
- NZ Ministry of Works and Development (1980).

---

## Notes & Limitations

- DEM units must be **metres**. Vertical units other than metres are not auto-detected.
- Reach length is measured using `QgsDistanceArea` with the project ellipsoid, so geographic CRSs are handled correctly.
- Multi-part lines are supported but each feature is treated as a single profile traced part-by-part.
- Features with empty geometry, or fewer than 2 valid DEM samples, produce `NULL` slope values and a warning in the Processing log.

---

## Issues & Contributions

- Report bugs or request features: <https://github.com/irenejaya/slope-calculator/issues>
- Pull requests welcome.

---

## License

MIT — see [LICENSE](LICENSE).

Copyright © 2026 Irene Jaya.
