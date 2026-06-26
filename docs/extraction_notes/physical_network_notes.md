# Physical Network Notes

## Initial QGIS road-centerline findings

- North Ave was found in the NJ_Roads_shp_Clip layer with SLD_NAME = NORTH AVE, MP_START = 0, MP_END = 0.75, MEASURED_L = 0.75, SRI = 02041097__, ROUTE_SUBT = 7, and ACTIVE = Y. Treat this as a GIS-backed physical segment for the candidate path.

- McLester Street is verified as part of the APM approach route because it appears in APM Terminals Elizabeth directions and is visible in the basemap. However, McLester Street was not found as a named segment in the NJ_Roads_shp_Clip attribute table under SLD_NAME during the initial QGIS pass. Treat the road as route-verified, but with official SRI/milepost attributes unavailable from this source.

- Tripoli Street / the terminal-side access reference is route-relevant because it appears in APM Terminals Elizabeth directions and is visible in the basemap context. However, Tripoli Street was not found as a named segment in the NJ_Roads_shp_Clip attribute table under SLD_NAME during the initial QGIS pass. Treat it as route-verified from APM/basemap evidence, but with official SRI/milepost attributes unavailable from this source.

- Kapkowski Road and Port Street may be relevant only if used for an alternative candidate path. They were not confirmed as usable GIS-backed candidate-path segments in the initial NJ_Roads_shp_Clip SLD_NAME search. Do not include them unless the final candidate path geometry requires them.

## Interpretation

The issue is not that McLester or Tripoli are uncertain as real route features. The issue is that the currently loaded road-centerline source does not provide usable official SRI/milepost attributes for those terminal-side streets in this initial pass.

For physical_edges.json, use:

- North Ave: GIS-backed from NJ_Roads_shp_Clip.
- McLester Street: route-verified from APM directions and basemap; SRI/milepost unavailable from this source.
- Tripoli/internal terminal access reference: route-verified from APM directions and basemap; SRI/milepost unavailable from this source.
