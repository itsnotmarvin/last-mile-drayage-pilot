# Inbound traffic analysis: North Avenue corridor evidence

## Executive summary

The official NJDOT station dataset—not the ArcGIS historical-average travel-time layer—is the primary evidence for the historical volume comparison. On the same route identifier (`20000624__`) and in the same 2018 count year, annual average daily traffic at station 182001, immediately upstream of the complete North Avenue approach merge, was **29,973 vehicles per day**. The robust median across the nine same-year records at upstream station 3-3-024 was **15,460**. Near-merge volume was therefore **1.94 times higher**, an increase of **14,513 vehicles per day (93.9%)**.

Later evidence makes the finding more useful without turning it into a current full-merge count. NJDOT's 2024 annual file reports **14,472 vehicles per day** at the upstream station—**6.4% below** the 2018 upstream median—but contains no 2024 row for station 182001. A City of Elizabeth engineering study published in 2022 used seven-day automatic counts and turning-movement counts collected in October 2020 and identified poor peak-period operations at North Avenue/Dowd Avenue and North Avenue/Kapkowski Road–IKEA Drive. Together, the sources support a persistent traffic-concentration concern along the shared corridor. They do **not** establish today's exact volume after all approaches merge, truck-specific delay, travel-time reliability, or a preferred inbound path.

## Dataset-based comparison

| Measure | Upstream station 3-3-024 | Near-merge station 182001 | Change |
|---|---:|---:|---:|
| Total AADT | 15,460 median | 29,973 | +14,513 / +93.9% |
| Eastbound AADT | 8,949 median | 17,403 | +8,454 / +94.5% |
| Westbound AADT | 6,628 median | 12,570 | +5,942 / +89.6% |

Both stations are in Elizabeth, use NJDOT standard route identifier `20000624__` (County Route 624 / North Avenue), and report count year 2018. Station 3-3-024 is at milepoint 0.78 on the Path B North Avenue approach. Station 182001 is at milepoint 1.75, within roughly 65 meters of the graph's all-approach merge node. Because the station is immediately upstream of that node, the comparison shows volume concentration approaching the common corridor; it is not a direct measurement after every approach has joined. The eastbound direction—the inbound movement toward APM—accounts for 58.1% of traffic at station 182001 and carries 38.4% more traffic than the westbound direction.

Station 3-3-024 contains nine records for 2018 with no subannual date field and substantial variation. Using the median limits the influence of three directionally anomalous rows. The result should be reported as an approximate funnel magnitude, not a precision flow balance. Station 182001 is a 48-hour volume station, whereas 3-3-024 is identified as a major station, so collection methods also differ.

## The 2024 upstream count is newer, but the full merge remains unmeasured

NJDOT's later records at upstream station 3-3-024 report AADT of 15,095 in 2021, 15,368 in 2022, and **14,472 in the 2024 annual file**. The 2024 total comprises 8,342 eastbound and 6,130 westbound vehicles per day. It is 988 vehicles per day, or 6.4%, below the 2018 upstream median and 5.8% below the 2022 value. The 2024 file identifies 3-3-024 as a permanent station. It contains no row for station 182001, so the newer evidence refreshes the upstream context but not the near-merge or post-merge volume.

NJDOT also directs users to its current Traffic Viewer and Transportation Data Management System for count details that may not appear in the annual file. Those interfaces should be searched manually for station 182001 and Route 624 milepoint 1.75 before commissioning new collection. Automated access was blocked during this review, so the absence finding is limited to the verifiable 2024 annual file rather than the entire current NJDOT system.

The City of Elizabeth's *Kapkowski Road Corridor Improvements Project Concept Development Report* adds a different kind of evidence. Its traffic program collected seven continuous days of automatic traffic-recorder data at seven locations and 12 manual turning-movement counts between October 19 and October 26, 2020. The analysis identified LOS E movements at North Avenue/Dowd Avenue during weekday peaks and at North Avenue/Kapkowski Road–IKEA Drive during PM and Saturday peaks. Because the observations occurred during the COVID-19 pandemic, the engineers compared them with 2018 pre-pandemic data and applied time-period adjustment factors. The study is therefore appropriate evidence of peak-period operational stress, but its adjusted results should not be described as unmodified 2020 traffic conditions.

The 2021 *Union County Truck Mobility Study* independently identifies the North Avenue segment from Earhart Drive to the New Jersey Turnpike overpass as the highest-AADT county roadway in its inventory, using the same 29,973-vehicle 2018 count. This confirms the official station's corridor significance and location but does not provide a newer measurement.

## Independent network cross-check

The archived FHWA Highway Performance Monitoring System attributes provide an independent, same-year-within-source check for 2020. On North Avenue route ID `20041769__`, AADT rises from 14,960 on the western segment to 21,434 on the downstream segment, a 43.3% increase. This supports the direction of the funnel finding, but the FHWA segments do not coincide with the two NJDOT station locations and should not be treated as validation of the exact 93.9% magnitude.

## Decision and operational use

The shared corridor is the correct traffic-management unit. Route A and Route B become operationally coupled once they reach North Avenue, so downstream exposure must not be duplicated when comparing paths. The combined evidence supports four actions:

1. place traffic monitoring and incident alerts on the common North Avenue-to-McLester segment;
2. retain separate approach-level measurements before the merge so Path A and Path B can eventually be compared fairly; and
3. install or obtain a current seven-day count immediately after the complete approach merge, including vehicle classification; and
4. record terminal-gate queue and service time separately from roadway delay.

No path wins yet. AADT is a volume metric; it cannot produce p80/p95 travel time, planning-time index, buffer time, or terminal queue reliability. Those require repeated weekday truck observations or raw interval count/speed data.

## Caveats and next collection

- AADT is an annualized average, not an hourly congestion profile.
- The 1.94× comparison is a same-year 2018 historical comparison, not a 2026 traffic estimate.
- Station 182001 is immediately upstream of the complete approach merge and is not a true post-merge counter.
- The added volume between stations cannot be assigned exclusively to Path A; local access and other ramps may contribute.
- NJDOT station records do not separate trucks from all vehicles.
- The City of Elizabeth's 2020 counts were collected during the pandemic and adjusted against 2018 pre-pandemic data.
- The independent FHWA truck fields are segment-level estimates, and `AADT_SINGL` combines single-unit trucks with buses.
- The 2024 annual file contains no station 182001 row; the current NJDOT station system still requires a manual station search.
- No gate-queue observations are currently available.

The next collection should use a downstream screenline immediately after the last approach joins and before McLester/Tripoli or another access point changes the flow. Pair it with counters on the major incoming approaches and video covering the merge. Collect seven consecutive nonholiday days in 15-minute intervals, including direction, vehicle classification, truck share, and speed. Preserve weather, construction, incident, terminal-gate-hour, and appointment-volume context. Repeated weekday truck travel times should cover 05:00–07:00, 07:00–10:00, 10:00–14:00, 14:00–17:00, and 17:00–19:00. Only then should the project calculate merged AADT, peak-hour volume, approach contributions, median, p80, p95, planning-time index, buffer time, and a path ranking.

## Sources

- New Jersey Department of Transportation, *Traffic Counts Data*, dataset `c74r-6c8d`, retrieved 2026-08-20. Archived query: `data/raw/observations/njdot_route_624_station_aadt_2018_2026_08_20.json`.
- New Jersey Department of Transportation, *Traffic Counts Data*, upstream station 3-3-024 records for 2020–2022, retrieved 2026-08-20. Archived query: `data/raw/observations/njdot_route_624_station_3-3-024_aadt_2020_2022_2026_08_20.json`.
- New Jersey Department of Transportation, *TrafficCount2024DataSetwithAADTs.csv*, upstream station 3-3-024, retrieved 2026-08-20: https://www.nj.gov/transportation/refdata/roadway/mdb/TrafficCount2024DataSetwithAADTs.csv. Archived extract: `data/raw/observations/njdot_traffic_count_2024_station_3-3-024_2026_08_20.json`.
- New Jersey Department of Transportation, *Interactive Traffic Count Reports*, current-system entry points, last updated May 1, 2025: https://www.nj.gov/transportation/refdata/roadway/trafficreport.shtm.
- City of Elizabeth, *Kapkowski Road Corridor Improvements Project Concept Development Report*, August 2022: https://www.elizabethnj.org/DocumentCenter/View/5308/01_Kapkowski-Rd-Corridor-Improvements-Final-CD-Rept-0822.
- Union County, *Union County Truck Mobility Study Final Report*, June 2021: https://ucnj.org/wp-content/uploads/2024/07/Union-County-Truck-Mobility-Study-Final-Report_Compressed.pdf.
- Federal Highway Administration, *National Highway System shapefile, version 2025-08-08*, archived Union County study-route extract: `data/raw/gis/official/fhwa_nhs_2025_union_study_extract_2026_08_07.geojson`.
- Canonical route geometry and merge-node roles: `data/processed/physical_edges.json` and `data/processed/physical_nodes.geojson`.
