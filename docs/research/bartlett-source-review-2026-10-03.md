# Bartlett Springs source and correction-state review

Date: 2026-10-03. Scope: acquisition research for the approved fault-zone potential-field case; not a completed field inversion or a replacement of the accepted case list.

## Primary provenance and actual access

The [USGS release](https://www.usgs.gov/data/gravity-aeromagnetic-magnetic-potential-and-physical-property-data-bartlett-springs-fault-zone) identifies [DOI 10.5066/P90F5TGH](https://doi.org/10.5066/P90F5TGH) and declares CC0 1.0. Its [Science Data Catalog entry](https://data.usgs.gov/datacatalog/data/USGS:64188a2ed34eb496d1d1d359) exposes the original [FGDC metadata](https://data.usgs.gov/datacatalog/metadata/USGS.64188a2ed34eb496d1d1d359.xml). That XML was actually retrieved: 37,384 bytes, SHA-256 `84d3d512f9deba53ae0251c74354c389b8723d056375390d2bfebd28c24b8295`. The raw metadata is retained in ignored research storage; no original measurements have been fabricated from it.

Direct ScienceBase root/item JSON requests returned HTTP 403 browser challenges from both the workstation and ML VPS. The DOI resolves to the same challenged item. A usable metadata endpoint does not establish accessible raw attachments. No challenge bypass, provider email, credential use, or data replacement was attempted.

## Measurement versus derived quantity

| Metadata entity | Named values and units | Scientific contract |
| --- | --- | --- |
| `bsf_gravity_data.csv` | `id`, latitude/longitude NAD27 in degrees; elevation in feet; observed gravity and all anomaly/correction channels in mGal | Preserve principal facts and correction history. The source's `observed_gravity` is already corrected for tides/drift and tied to IGSN1971, not a raw instrument reading. |
| `mag_grid.csv` | NAD27 longitude/latitude and total-field magnetic anomaly in nT | A compiled, datum-adjusted 200 m grid is not an unprocessed airborne line survey. It cannot satisfy M03 flight/tie-line QC by itself. |
| `psgr.csv` | NAD27 longitude/latitude and magnetic potential in nT-km | A transformed magnetic-potential product is not directly measured gravity or magnetic intensity. Keep this quantity separate. |
| `bsf-properties.csv` | Grain/dry/saturated density in g/cm3, susceptibility with distinct cgs/SI scale factors, remanent magnetization and orientation | A sample property is not a complete volume or a site-calibrated petrophysical prior. No cgs/SI or moment/volume conversion without the physical normalization. |

The gravity principal facts include `free-air-anomaly`, `simple_Bouguer_anomaly`, inner-zone terrain correction/code, total terrain correction, `Complete_Bouguer_anomaly`, and isostatic anomaly. Each is a distinct state; none is silently treated as uncorrected absolute gravity.

The processing account says observed gravity already incorporates tidal and instrument-drift correction and base ties (CH39 980,094.15 mGal; bCH35 980,119.04 mGal). Complete Bouguer values additionally incorporate curvature and terrain to 166.7 km with a 2,670 kg/m3 reduction density. Isostatic values then use an Airy-Heiskanen calculation with 25 km sea-level crust, 400 kg/m3 contrast and 2,670 kg/m3 topographic load. A future M01 workflow must refuse to apply those operations again to the corresponding derived channels. A comparison against a different normal-gravity model is a declared new calculation, not reproduction of the provider's anomaly.

The elevation attribute definition is literally `elevation_ft_NVD29`; the XML has no formal spatial-reference section establishing an unambiguous vertical datum. Retain that source string and flag the ambiguity rather than silently changing it to an ellipsoidal or modern vertical datum. Latitude/longitude attribute definitions establish NAD27, so WGS84 transformation also requires a recorded, valid transformation and any grid/accuracy limitation. Metadata alone cannot supply missing measurement uncertainties or a raw acquisition time series.

## Additional author archive, not a substitute claim

[Su and collaborators' research repository](https://github.com/Y326s/Natural_Hydrogen_YS) at inspected commit `a5ec72645970d70673ac8c1ede2b4bc9789d43aa` cites the USGS Bartlett release and uses Clear Lake gravity/magnetic data. It links the [version-2 archive, DOI 10.5281/zenodo.16975696](https://zenodo.org/records/16975696). The Zenodo API declares CC BY 4.0 and a 121,295,137-byte ZIP with MD5 `7ef5beb984425bf0edabd829cf880187`; GitHub's code licence is MIT. Dataset licensing is recorded from the archive, not inferred from the code licence. Version 1 is different bytes and is not silently used for version 2.

The archive was subsequently downloaded and verified: 121,295,137 bytes with the declared MD5, SHA-256 `337a2d9070493773af06aee11a19d591e6468ecf0f062dd75c194a04476c0cdf`. Its 40-entry inventory expands to 299,907,397 bytes. Selected members are 335,377-byte gravity CSV, 28,531,313-byte magnetic CSV, 193,035,546-byte topography CSV and 96,913-byte README PDF. Member hashes are pinned in the source ledger. No third-party code or saved inversion was executed.

The gravity file has actual OG/FAA/SBA/TTC/CBA/ISO principal-fact channels and WGS84/UTM10N horizontal coordinate labels; the vertical label `zWGS84` alone does not establish the elevation transformation or datum. These observations are an author-transformed/compiled dataset, not proof of byte identity with original Bartlett attachments. The script uses isostatic anomaly and changes the gravity sign for upward-positive SimPEG. Its magnetic data are a grid rather than flight-line records; it adds an assumed 1,000-foot terrain clearance and silently replaces missing interpolated heights with 1,200 m. That substitution is specifically rejected for this platform: unknown acquisition elevation remains a flagged/ineligible observation. Preprocessed author arrays cannot be relabelled as untouched station measurements or subsurface truth. The archive's hydrogen-target interpretation is a hypothesis, not observed hydrogen or uniquely determined geology.

## Required next gates

1. Retrieve the exact original principal-fact attachments or prove byte/semantic identity for an attributed permitted copy; retain retrieval/hash and all licence notices.
2. Independently parse every channel with explicit correction state, horizontal/vertical datum, units, finite/missingness and error policy. Unknown units/datum do not become guessed metadata.
3. Decide which channels are valid for M01 QC/comparison versus M02/M04/M11 modelling; preserve remanent and wrong-correction negative controls.
4. Run independent forward/heldout/sensitivity oracles on actual observations. Do not add geological truth to a field case or optimize choices against withheld data.
5. Author the worked field case and linked instrument only from those measured results. Keep this access/correction finding separate from final case acceptance.

## Local intake completion evidence

The bounded continuation imported the exact existing ZIP and FGDC XML with `acquire.py --file`, checked the complete 40-entry / 299907397-byte ZIP inventory, and selectively verified/extracted just four pinned CSV/PDF objects (221999149 bytes). Both PowerShell and Git Bash entrypoints produced the same profile apart from their UTC timestamps; identical reruns preserved selected objects and receipts. No saved array, provider script, notebook, inversion or canonical case was opened/executed/published.

The actual gravity CSV has 2929 rows, 70 missing FAA values and 70 missing SBA values (140 explicit missing/nonfinite flags), duplicate station IDs `SROA55` and `SROR4`, and one duplicated finite XYZ tuple. Other named channels have 2929 finite values. No rows were excluded or uncertainty values fabricated. For 2859 available triples, the arithmetic `CBA - SBA - TTC` difference ranges approximately from -1.42 to -0.02 mGal; this is not a forward-model residual or a proof of physical closure. Height datum, station-level original/author processing lineage and measurement uncertainties remain unresolved and `modelling_eligible` is false.

Exact archive/member/receipt/profile hashes, attributed rights, aggregate channel bounds and read-only isolated environment are persisted in [compact inspection evidence](potential-source-intake-evidence-2026-10-03.json), not as raw bytes or station/solver arrays in Git. [Guide 11](../guides/11_potential_source_intake.md) documents reproducible local commands and negative controls. These findings satisfy source-inspection gates only; the required method/field gates above remain open.
