# Main-route authority and truck-rule audit

**As of:** July 26, 2026

**Route audited:** the two candidate approaches described in
`data/processed/physical_edges.json`, from the NJ Turnpike Exit 13A or US 1&9
approach to APM Terminals Elizabeth by North Avenue/North Avenue East,
McLester Street, and Tripoli Street.

## Bottom line

The modeled last mile is entirely in **Elizabeth, Union County**. It does not
enter Newark or Essex County.

| Route portion | Road controller | Municipality/county | Current corridor-specific result |
|---|---|---|---|
| NJ Turnpike Exit 13A approach (outside the modeled local-edge set) | New Jersey Turnpike Authority, then NJDOT on the NJ 81 connectors | Elizabeth, Union County | Authority transition only; Newark and Essex County are not involved. |
| North Avenue/North Avenue East | Union County, County Route 624 | Elizabeth, Union County | The city four-ton and five-ton schedules do not list the corridor. Elizabeth Code §10.16.050 separately designates an 80,000-pound zone on a 520-foot part of North Avenue East east of Kapkowski Road. The Union County truck-route schedule is unresolved because §138-9 is broad but Schedule VII, §138-37, is “Reserved.” |
| McLester Street | City of Elizabeth | Elizabeth, Union County | No current city weight, vehicle-class, time-of-day, or turn restriction was found for the modeled portion. |
| Tripoli Street, McLester to approximately 40.6729993, -74.1571966 | City of Elizabeth | Elizabeth, Union County | No current city weight, vehicle-class, time-of-day, or turn restriction was found for the modeled portion. |
| Tripoli Street east of approximately 40.6729993, -74.1571966 to the APM gate | Private terminal road; Port Authority land/facility with APM as lessee and gate operator | Elizabeth, Union County | PANYNJ terminal rules and APM gate controls apply in addition to generally applicable law. PANYNJ’s current terminal-highway ceiling is 128,000 pounds for containerized shipments; oversize approval and terminal credentials may also be required. |

The controller assignments come from the current New Jersey statewide road
centerline service. The service classifies North Avenue as county jurisdiction
with shield CR 624 and SRI `20000624__`; McLester as municipal jurisdiction
with SRI `200413892_`; and Tripoli as municipal west of the listed break
(object 374024) and private east of it (object 395729). The dataset is updated
monthly and segments roads at jurisdictional boundaries. It is strong
operational/GIS evidence, but it is not a deed or legal-boundary survey.

## Controlling text and present effect

### 1. Union County: North Avenue/CR 624

**Who controls it.** Union County controls North Avenue as CR 624. Elizabeth
remains the municipality, and the county’s current policy recognizes municipal
traffic ordinances on county roads through county consenting resolutions.

**Current county provisions.**

- **Union County Code §133-10, “Traffic ordinances.”** The section says the
  county is responsible under state law, that county policy is to adopt a
  consenting resolution after a local ordinance is enacted, and that the
  Commissioners have concurred with municipal traffic ordinances on county
  roads except parking-meter rules.
- **§138-8, “Vehicle weight limits.”** The operative words exclude trucks over
  four tons from only the streets placed in Schedule VI, subject to pickup and
  delivery on those streets.
- **§138-36, Schedule VI.** The current schedule applies that four-ton rule to
  streets in the Union County park system. North Avenue, McLester, and Tripoli
  do not appear.
- **§138-9, “Truck routes.”** This provision says trucks whose combined vehicle
  and load exceed four tons are excluded from streets other than designated
  truck routes.
- **§138-37, Schedule VII.** The schedule that must identify those truck routes
  contains no road and reads **“(Reserved).”**

**Exact current operative text.**

> **§133-10. Traffic ordinances.** “A. State law: The County is responsible.
> B. Union County policy: The County adopts consenting resolutions after
> enactment of local ordinances. C. Comment: The Commissioners have concurred
> with all municipal traffic ordinances on County roads with the exception of
> parking meter installation and regulation.”

> **§138-8. Vehicle weight limits.** “Trucks over four tons' gross weight are
> hereby excluded from the streets or parts of streets described in Schedule
> VI (§138-36), except for the pickup and delivery of materials on such
> streets, said Schedule VI (§138-36) being attached to and made a part of this
> chapter.”

> **§138-9. Truck routes.** “Pursuant to N.J.S.A. 40:67-16.1, the streets or
> parts of streets described in Schedule VII (§138-37), attached to and made a
> part of this chapter, are hereby designated as routes for trucks over four
> tons. All trucks having a total combined gross weight of vehicle plus load in
> excess of four tons shall be excluded from all streets except from those
> streets which form a part of the system of truck routes.”

> **§138-36, Schedule VI.** “In accordance with the provisions of §138-8,
> trucks over four tons' gross weight are hereby excluded from all streets in
> the Union County park system except for the pickup and delivery of materials
> as excepted.” The ensuing schedule lists park-system roads, not this
> corridor.

> **§138-37, Schedule VII.** “In accordance with the provisions of §138-9 the
> following streets or parts of streets are hereby designated as routes for
> trucks over four tons: Name of Street [/] Location [/] (Reserved).”

**Scope and effect.** Section 138-8 is a greater-than-four-ton rule, not a
general truck ban, and its pickup/delivery exception is limited to the park
streets in Schedule VI. It does not reach CR 624. Section 138-9 presents a
different problem: read literally and countywide, it would prohibit every
truck over four tons because §138-37 designates no route. Read in the context
of the surrounding schedules—county properties and park-system roads—it does
not establish a usable CR 624 restriction. The current code, the state road
data marking CR 624 non-restricted, and the official APM route all point away
from treating it as a functioning corridor-wide ban.

**Verification status.** The text remains in the county code updated through
January 2026. No later amendment to §§138-8, 138-9, 138-36, or 138-37 was found.
The county-hosted January 2026 PDF was indexed and reviewed during this audit,
but its origin URL returned 404 during the final July 26 link check. The still
accessible official January 2025 code contains the same quoted provisions.
The only later 2026 codification ordinances found—Nos. 865-2026 and 866-2026,
finally adopted April 30, 2026—amend Chapters 49, 115, and 140, not Chapter
138.
The underlying 1982 Ordinance No. 160 and a county interpretation or
enforcement record were not available online. The safe research conclusion is
therefore **current text, but unresolved scope/enforceability for §138-9**—not
an affirmative finding that CR 624 is either a designated truck route or a
prohibited road.

### 2. Elizabeth: North Avenue, McLester, and municipal Tripoli

**City Code §10.16.010, “Four-ton weight limit—Streets affected.”** It excludes
trucks over four tons from the streets in its table, with an exception for
pickup and delivery on the listed street. North Avenue/North Avenue East,
McLester Street, and Tripoli Street are not in that table. Nearby streets named
in the table do not extend the restriction to this route.

The current operative sentence is: “Trucks over four (4) tons gross weight are
excluded from the street or parts of street described, except for the pickup
and delivery of materials on such street.” The section's current street table
contains none of the modeled corridor streets.

This is a weight-and-location rule. It is not a ban on trucks generally; it
does not create time-of-day, dimensional, or vehicle-class limits. Its
pickup/delivery language is not a general terminal-access exception: it excuses
service on a listed street, not through travel over a listed street merely to
reach a terminal somewhere else.

**§10.16.040, “Five-ton weight limit for trucks—Streets affected.”** It lists
only Westminster Avenue and Wilder Street. It does not apply to the route.

**§10.16.050, “An 80,000 pound overweight vehicle zone limit—Streets
affected.”** The current table designates:

- **Street:** North Avenue East.
- **Location:** beginning 440 feet east of North Avenue East/Kapkowski Road and
  continuing east 520 feet to the vacated North Avenue East connection with the
  Port Authority overweight-vehicle zone.
- **Source history:** Ordinance No. 4654, §1, adopted December 22, 2015.

The exact current table text is: “North Avenue East — Beginning at a point 440
feet east of the intersection of North Avenue East and Kapkowski Road and
continuing east 520 feet to the vacated portion of North Avenue East and its
connection to the Port Authority over weight vehicle zone.”

This is the only current city weight provision that names a modeled corridor
street. The code supplies an 80,000-pound limit and a precise 520-foot
location; it does not state a terminal-access exception. The reference to the
Port Authority zone describes where the segment connects. It does not itself
authorize a vehicle above 80,000 pounds to use the municipal/county-road
segment.

**Turns and times.** The current turning schedules and the city’s 2025–2026
ordinance list were checked for North Avenue, McLester, and Tripoli. No
corridor-specific prohibited turn or through-movement rule was found. The
city’s later 2026 through-movement ordinance, Ordinance No. 6250/§10.08.112,
applies at Reid Street and East Grand Street, not this route. Terminal gate
hours are operational admission rules, not city street restrictions.

**Current status and later amendments.**

- The online Elizabeth Code is Supplement 31, codified through Ordinance No.
  6138, passed June 24, 2025.
- The city’s official 2026 ordinance register was separately checked through
  the ordinances posted as of July 26, 2026.
- Ordinance No. 6290, passed and approved May 26, 2026, amended §10.16.010 to
  add only Front Street from the Elizabeth River crossing to Port Avenue. By
  its terms it becomes effective 20 days after passage and mayoral approval.
  It does not change North Avenue, McLester, or Tripoli.
- No repeal or amendment of §10.16.050 after Ordinance No. 4654 was found.

The city code and register establish that these provisions remain on the
books. The separate county-consent/NJDOT approval record and proof of installed
weight-limit signs were not located. Those items should be obtained before
making an enforcement-grade conclusion about §10.16.050.

### 3. State truck-access rule: what “terminal access” actually does

**N.J.A.C. 16:32-1.1 through 1.5** applies only to:

- double-trailer truck combinations; and
- standard trucks wider than 96 inches but no wider than 102 inches.

It is not the general truck code. A conventional truck no wider than 96 inches
does not receive or need an exception under this chapter.

For the covered vehicles, the rule establishes a National Network, a New
Jersey Access Network, and local unrestricted roads. CR 624 is a county
600-series road and is not listed in Appendix C as part of the New Jersey
Access Network.

Under the current **§16:32-1.5(a)(2)**, a 102-inch-wide standard truck may use a
local unrestricted road only as necessary to reach a terminal by the direct
route. It may carry documents such as a bill of lading, manifest, route map, or
dispatcher confirmation under §16:32-1.5(b). The January 3, 2023 amendment
changed the local-road sentence from the former collective “they” to “a
102-inch-wide standard truck”; the present text therefore does not give the
same local-unrestricted-road permission to a double-trailer combination.

Most importantly, **§16:32-1.2(e)** preserves municipal ordinances, county
resolutions, weight postings, and local truck-route restrictions. Terminal
access does **not** override Elizabeth’s 80,000-pound segment, a valid posted
county restriction, bridge clearance, or another applicable rule. The chapter
was readopted November 30, 2022, amended effective January 3, 2023, and expires
November 30, 2029.

### 4. Private Tripoli segment and APM terminal

The official state road-centerline service changes Tripoli from municipal to
private at approximately **40.6729993, -74.1571966**. PANYNJ’s 2026 official
statement says the Elizabeth-Port Authority Marine Terminal is owned by the
Port Authority. APM Terminals North America is the container-terminal lessee;
its lease was extended through 2062. APM’s own directions send trucks from
North Avenue to McLester, right on Tripoli, and then to its entrance.

The practical control split is:

- **PANYNJ:** terminal land/common facility, marine-terminal highways, Port
  Authority tariff, security framework, and overarching permission to use the
  terminal.
- **APM:** its leased premises, truck appointment and operating process, and
  admission at the APM gate, subject to the lease and applicable PANYNJ rules.

Relevant current provisions in **PANYNJ Marine Terminal Tariff FMC Schedule
No. PA-10, effective May 1, 2026** are:

- **Subrules 34-035 and 34-045:** define a marine terminal to include vehicular
  roadways and define a Marine Terminal Highway as a terminal portion PANYNJ
  makes available for general or limited highway use.
- **Subrule 34-046:** containerized shipments on Marine Terminal Highways may
  not exceed 128,000 pounds gross vehicle weight or the manufacturer’s safe
  working load. A vehicle over 16 feet 3 inches high or 11 feet wide needs
  approval from the Manager, Marine Terminals.
- **Subrule 34-090:** permission to enter or use a terminal is conditioned on
  compliance with PANYNJ rules; application on a leased premise depends on the
  lease.
- **Subrule 34-105:** terminal users must comply with all applicable
  governmental laws and directions. This prevents the 128,000-pound
  terminal-highway ceiling from acting as an exception to an off-terminal
  80,000-pound road limit.
- **Subrules 34-1000 and 34-1100:** a “Drayage Truck” is an on-road vehicle
  over 33,000 pounds GVWR serving a PANYNJ terminal for cargo movement, with
  listed exclusions; every covered drayage truck seeking entry must be in the
  Drayage Truck Registry.
- **Subrule 34-1121:** terminal facilities must check the registry for gate
  compliance.

PANYNJ’s current truck-information page separately lists limited operating
hours for overweight or overwidth containerized cargo: 8:00 a.m.–3:00 p.m. on
Monday, Wednesday, and Friday. That is a terminal operating window, not a city
street ordinance.

## Terminal-access answer by rule

| Rule | Does terminal access create an exception? |
|---|---|
| Elizabeth §10.16.010 four-ton list | No general terminal exception. The exception is pickup/delivery on the specifically listed street; the modeled streets are not listed. |
| Elizabeth §10.16.050 80,000-pound North Avenue East zone | No exception appears in the section. The Port Authority connection is part of the location description only. |
| Union County §138-8/§138-36 park-road limit | Only pickup/delivery on the affected park street; the route is not in the schedule. |
| Union County §138-9/§138-37 | No express terminal exception. Scope is unresolved because the required route schedule is empty. |
| N.J.A.C. 16:32-1.5 | Yes, but only the direct-access permission the section gives to the covered vehicle class, and only over qualifying roads. It does not override local/county restrictions. |
| PANYNJ/APM gate | Terminal business is the reason for admission, but admission is conditional: registry, security, dimensional/weight approval, appointment, and operator requirements can still bar entry. |

## Remaining verification gaps

1. Obtain Union County’s underlying Ordinance No. 160 (May 6, 1982) and a
   written county interpretation of §138-9/§138-37.
2. Obtain the county consenting resolution and any state traffic-order or
   approval file for Elizabeth Ordinance No. 4654/§10.16.050.
3. Photograph and geolocate posted weight, turn, and truck-route signs on the
   520-foot §10.16.050 segment and at the municipal/private Tripoli boundary.
4. Use the PANYNJ/APM lease exhibits or a parcel/title record if a
   deed-precision boundary between public Tripoli, terminal common road, and
   APM’s leasehold is required.

## Primary sources

- [NJGIN statewide road centerlines](https://www.nj.gov/njgin/edata/roads/)
  and [current service metadata](https://www.arcgis.com/sharing/rest/content/items/fc3d0a95921b4026b386643eef5ff088/info/metadata/metadata.xml?format=default&output=html)
- [NJDOT route-subtype definitions](https://www.nj.gov/transportation/refdata/gis/metadatafaq.shtm)
- [Laws of Union County, updated through January 2026 (indexed official copy; origin link unavailable at final check)](https://ucnj.org/commissioners/wp-content/uploads/sites/29/2026/04/Laws-of-Union-County-2026.pdf)
  and [accessible official January 2025 code containing the same cited provisions](https://ucnj.org/wp-content/uploads/2025/01/Laws-of-Union-County-1-6-2025.pdf)
- [Union County Ordinance No. 865-2026](https://ucnj.org/press-releases/public-notices/2026/03/30/ordinance-865-2026/)
  and [final notice for Ordinance No. 866-2026](https://ucnj.org/press-releases/public-notices/2026/05/01/ordinance-866-2026-2/)
- [Elizabeth Code, Chapter 10.16](https://library.municode.com/nj/elizabeth/codes/code_of_ordinances?nodeId=TIT10VETR_CH10.16WELI_10.16.030FONWELIIOPE)
- [Elizabeth official ordinance register](https://www.elizabethnj.org/272/City-Ordinances)
  and [Ordinance No. 6290](https://www.elizabethnj.org/DocumentCenter/View/10814/Ord-No-6290-Amend-1016010-4-ton-weight-limit-streets-to-add-Front-St-at-Elizabeth-River-Cossing-to-Port-Ave)
- [NJDOT current Truck Routing Regulations](https://www.nj.gov/transportation/freight/trucking/routing_regulations.shtm)
  and [2023 readoption](https://www.nj.gov/transportation/freight/trucking/pdf/R.2023%20d.002%20%2855%20N.J.R.%2072%28a%29%29.pdf)
- [PANYNJ Marine Terminal Tariff PA-10, effective May 1, 2026](https://www.panynj.gov/content/dam/port/doing-business-pdfs/Port%20Authority%20Marine%20Terminal%20Tariff%20FMC%20Schedule%20No.%20PA%2010%20%28Effective%20May%201%20%2C2026%29.pdf)
- [PANYNJ 2026 official statement: ownership and APM lease](https://www.panynj.gov/content/dam/corporate/consolidated-bonds-%26-notes-pdfs/port-authority-OS-series-251.pdf)
- [APM Terminals Elizabeth contact and directions](https://www.apmterminals.com/en/port-elizabeth/contact/contact-and-directions)
- [PANYNJ truck information](https://www.panynj.gov/port/en/shipping/truck.html)
