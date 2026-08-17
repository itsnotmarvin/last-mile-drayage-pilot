# I-95 inbound appointment-risk analysis

Date analyzed: 2026-08-16  
Traffic week tested: 2026-08-17 through 2026-08-21  
Time zone: America/New_York  
Destination: APM Terminals Elizabeth gate

## Result

Esri's time-dependent route estimates do not show a recurring congestion window severe enough to consume a 15-minute approach buffer on the I-95 / New Jersey Turnpike Exit 13A corridor. The completed southbound observations range from 5 to 8 minutes over 4.0 km. The maximum is 8 minutes at 3:00 p.m. Monday; the usual post-7:00 a.m. value is 7 minutes. A northbound Friday 2:00 p.m. spot-check is also 7 minutes over 4.0 km.

That does not mean a truck cannot miss an appointment. A truck entering the approach with fewer than 8 minutes of lead can be late under the observed traffic. Esri does not model the terminal's external queue or gate-processing time, so a 15-minute lead remains thin operationally even when the road segment is moving normally.

## Appointment controls tested

- Primary regulatory/operational node: `reg_apm_appointment`.
- Terminal-hours control: APM's published regular gate hours are Monday-Friday, 6:00 a.m. to 4:00 p.m. for empties, dry loads, and reefer loads. OOG cutoff is 3:30 p.m. and is outside the scoped standard-load movement.
- Separate access controls that can prevent gate entry even when road travel is on time: `reg_apm_safety_induction`, `reg_panynj_sealink_twic`, `reg_panynj_rfid`, and `reg_panynj_dtr`.

## Operational interpretation

| Lead at I-95 approach origin | Finding |
| --- | --- |
| Less than 5 minutes | Late in every completed sample. |
| 5-7 minutes | Material travel-only miss risk; several weekday periods take 6-8 minutes. |
| 8-14 minutes | Fits the observed roadway maximum, but leaves 0-6 minutes for terminal queueing and variability. |
| 15-19 minutes | No travel-only miss in the completed sample; still limited gate-queue protection. |
| 20 minutes | Recommended normal minimum at the approach origin. |
| 30 minutes | Recommended during 7:00-9:00 a.m., 2:00-4:00 p.m., or whenever the live incident/closure layer shows a problem. |

For the 4:00 p.m. regular gate cutoff, the latest travel-only departure supported by the observed maximum is 3:52 p.m. That is not a dispatch recommendation because it provides no queue allowance. A practical dispatch target is no later than 3:30-3:40 p.m. at the tested I-95 approach point, subject to the current appointment and terminal instructions.

## Method

The ArcGIS web map item `c99508642018486a9f1a5009a85cdcfe` was configured with Esri World Traffic beneath the project route layers. The route used the already evaluated Exit 13A inbound geometry. `Driving Time` was selected as the impedance because it exposes Esri's time-dependent traffic behavior; the Map Viewer `Trucking Time` option did not expose the same traffic behavior. This choice measures traffic on the selected corridor and is not a truck-legality determination.

The completed southbound sample includes Monday-Thursday at 5:00, 6:00, 7:00, 8:00, 9:00 a.m., noon, 2:00, 3:00, and 4:00 p.m., plus Friday at 2:00 p.m. The northbound sample contains a Friday 2:00 p.m. spot-check. Raw values are preserved in `data/raw/observations/esri_world_traffic_i95_approaches_2026_08_16.json`.

## Limits

- The result is a planning screen, not an on-time guarantee.
- Traffic estimates exclude terminal queueing and gate processing.
- Live incidents, closures, construction, weather, and unusual port demand can invalidate the historical pattern.
- The northbound direction needs the same expanded weekday sampling before it can be compared statistically with southbound.
- The traffic impedance does not replace the separate truck-legality finding or current roadside signage.
