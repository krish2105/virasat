# VIRASAT — Data card

Every file is listed with source, licence, date, extent, CRS and SHA-256 in
`data/MANIFEST.md`. This card explains what the data is good for and what it is not.

## Sources actually on disk

| Dataset | What | Resolution / date | Licence | Used for |
|---|---|---|---|---|
| Sentinel-2 L2A, tile 43REK | Bands B02/B03/B04/B08, windowed to the study bbox | 10 m; 2019-12-26 (0.04 % cloud) and 2025-12-04 (0.001 %) | Copernicus Sentinel data — free and open | Block-scale change pairs (780 tiles of 320 m), evidence true-colour crops |
| Google Open Buildings 2.5D Temporal v1 | Building presence, fractional count, height | ~4 m effective (delivered at 0.5 m, read at 4 m from overviews); annual 2016–2023 | CC BY 4.0 / ODbL 1.0 | Building-scale NEW_CONSTRUCTION / DEMOLITION / VERTICAL_ADDITION candidates; change masks; massing heights |
| OpenStreetMap | Roads, city wall, gates; 7,579 building footprints | as of 2026-09-09 | ODbL (attribution in the UI footer) | Georeferencing control network; footprints; chowkri cut lines; 3D massing |
| UNESCO WHC document 176277 | Vector map of the inscribed property and buffer | 1:10,000 nominal | UNESCO statutory document | Core and buffer polygons (georeferenced, see ARCHITECTURE.md) |
| JHCPR 2020 | Jaipur (Walled City) Heritage Conservation and Protection Regulations 2020, incl. Architectural Control Guidelines annexure | notified 2020; 85 pp machine-readable | Government of Rajasthan public notification | RAG corpus: 178 clause chunks |

## Not on disk (blocked)

* **Bhoonidhi LISS-4 (5.8 m)** — requires NRSC registration. Would roughly triple the tile count for the core.
* **Mapillary street-level imagery** — requires a free token. The loader and blur-at-ingest test exist; no image has been ingested. The facade classifier therefore has no data.
* **Heritage Regulation 2022** — not findable online; the 2020 regulation is used and cited by name.
* **Ground truth labels** — 0 of 400 tile-pair labels, 0 of 60 clause-pair labels. Every metric that needs them reports BLOCKED.

## Derived layers and how honest they are

* **Core / buffer polygons**: georeferenced from the official map by landmark seed + road-network ICP; RMS 15.6 m, 95 % of map road vertices matched. Areas come out 9.5 % below the inscribed figures at the data-fitted scale, and forcing the nominal scale makes the road fit worse — so the polygons are kept as drawn and the discrepancy is recorded in `data/boundaries/georeference_report.json`.
* **Chowkris**: geometry derived from the core polygon cut along PCA lines through the named bazaar streets. **Names assigned from the published grid description; unverified by the JNN Heritage Cell.** Fairness slices depend on these names.
* **Open Buildings candidates**: 103 buildings whose presence/height changed between 2016 and 2023 (35 new, 30 demolished, 38 taller). The confidence shown is the dataset's own presence score, *not* a calibrated output of our detector — the UI says so on every change. Open Buildings is itself derived from Sentinel-2 by a model; its errors are inherited.
* **Evidence crops**: 320 m windows of Sentinel-2 true colour, upscaled ×8 with nearest-neighbour so pixels stay honest; the mask is the presence delta (red = lost, green = gained).

## Known biases

* OSM footprint coverage reflects mapping effort, which is uneven across chowkris; a fairness gate computed only on OSM-anchored candidates can therefore be biased before any model runs.
* Sentinel-2 at 10 m cannot see a single haveli. Block-scale change only.
* Season is matched (December/December) so vegetation phenology is not a confound in the Sentinel pair; the Open Buildings annual layers are mid-year composites.

## Privacy

No names, owners, tax or occupancy data enter the system. Building ids are `B-` + a hash of the OSM way id. Street imagery, when ingested, is face- and plate-blurred in memory before any byte is written, and the writer refuses unblurred arrays (tested).
