---
type: concept
status: draft
source_status: personal-note
reading_status: mixed
review_stage: ai-extracted
topics: [literature, taxonomy]
keywords: [topic_cleanup, paper_topics]
created: 2026-05-18
updated: 2026-05-18
sources: []
---

# Topic Cleanup Report

This report records the conversion of paper page `topics:` to the revised paper topic registry. Only paper page frontmatter was changed. Detailed mechanism, method, and maintenance terms were moved to `keywords:`.

After frontmatter conversion, paper page `## Keywords` display lines were also synced to match the updated frontmatter.

## Active Topic Set

- `aerosol`
- `microphysics`
- `cloud_physics`
- `remote_sensing`
- `modeling`
- `instrumentation`
- `tropical_cyclone`
- `precipitation`
- `wildfire`
- `radar_meteorology`
- `field_campaign`
- `climate_change`

## Conversion Rules Applied

| Old topic | New topic(s) | Keyword(s) added |
|---|---|---|
| `cloud_microphysics` | `microphysics` | `` |
| `wildfire_smoke` | `wildfire`, `aerosol` | `wildfire_smoke` |
| `pyrocb` | `wildfire`, `aerosol` | `pyrocb` |
| `radiative_forcing` | `aerosol`, `climate_change` | `radiative_forcing` |
| `aerosol_cloud_radiative_effects` | `aerosol`, `climate_change` | `aerosol_cloud_radiative_effects` |
| `aerosol_cloud_interaction` | `aerosol` | `aerosol_cloud_interaction` |
| `stratospheric_aerosol` | `aerosol` | `stratospheric_aerosol` |
| `retrieval_validation` | `remote_sensing` | `retrieval_validation` |
| `lidar` | `remote_sensing` | `lidar` |
| `field_campaigns` | `field_campaign` | `` |
| `radar_metrology` | `instrumentation` | `radar_metrology` |
| `needs_triage` | `` | `needs_triage` |

## Changed Paper Pages

| Page | Topics before | Topics after | Keywords added |
|---|---|---|---|
| [[aberson_thirty_2006]] | `cloud_microphysics`, `instrumentation`, `remote_sensing`, `tropical_cyclone` | `microphysics`, `instrumentation`, `remote_sensing`, `tropical_cyclone` | `` |
| [[allen_observationally_2019]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[braun_cloud_resolving_2002]] | `cloud_microphysics`, `modeling`, `tropical_cyclone` | `microphysics`, `modeling`, `tropical_cyclone` | `` |
| [[bretherton_epic_2004]] | `aerosol`, `cloud_microphysics`, `modeling` | `aerosol`, `microphysics`, `modeling` | `` |
| [[bu_influence_2014]] | `cloud_microphysics`, `tropical_cyclone` | `microphysics`, `tropical_cyclone` | `` |
| [[cao_analysis_2008]] | `cloud_microphysics`, `remote_sensing` | `microphysics`, `remote_sensing` | `` |
| [[chen_effects_2006]] | `cloud_microphysics`, `modeling`, `tropical_cyclone` | `microphysics`, `modeling`, `tropical_cyclone` | `` |
| [[chikamoto_multi_year_2017]] | `needs_triage` | `wildfire`, `aerosol` | `needs_triage` |
| [[cui_response_2011]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[curated_baars_unprecedented_2019]] | `remote_sensing`, `aerosol`, `pyrocb`, `lidar` | `remote_sensing`, `aerosol`, `wildfire` | `pyrocb`, `lidar` |
| [[curated_chen_evaluation_2020]] | `remote_sensing`, `stratospheric_aerosol`, `retrieval_validation` | `remote_sensing`, `aerosol` | `stratospheric_aerosol`, `retrieval_validation` |
| [[curated_levin_aerosol_2009]] | `aerosol`, `aerosol_cloud_interaction`, `precipitation` | `aerosol`, `precipitation` | `aerosol_cloud_interaction` |
| [[curated_liu_significant_2022]] | `aerosol`, `pyrocb`, `wildfire_smoke`, `radiative_forcing` | `aerosol`, `wildfire`, `climate_change` | `pyrocb`, `wildfire_smoke`, `radiative_forcing` |
| [[curated_wang_wildfire_2025]] | `aerosol`, `pyrocb`, `wildfire_smoke`, `aerosol_cloud_radiative_effects` | `aerosol`, `wildfire`, `climate_change` | `pyrocb`, `wildfire_smoke`, `aerosol_cloud_radiative_effects` |
| [[gao_study_2021]] | `cloud_microphysics` | `microphysics` | `` |
| [[guo_aerosol_induced_2018]] | `aerosol`, `cloud_microphysics`, `remote_sensing` | `aerosol`, `microphysics`, `remote_sensing` | `` |
| [[hoffmann_limits_2017]] | `aerosol`, `cloud_microphysics`, `modeling` | `aerosol`, `microphysics`, `modeling` | `` |
| [[ilotoviz_relationship_2018]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[intergovernmental_panel_on_climate_change_climate_2014]] | `needs_triage` | `climate_change` | `needs_triage` |
| [[janapati_assessment_2019]] | `cloud_microphysics`, `tropical_cyclone` | `microphysics`, `tropical_cyclone` | `` |
| [[janapati_assessment_2023]] | `cloud_microphysics` | `microphysics` | `` |
| [[krueger_technical_2020]] | `cloud_microphysics` | `microphysics` | `` |
| [[lee_dependence_2011]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[lee_general_2004]] | `needs_triage` | `microphysics` | `needs_triage` |
| [[lee_impacts_2020]] | `aerosol`, `cloud_microphysics`, `modeling` | `aerosol`, `microphysics`, `modeling` | `` |
| [[lee_microphysical_2019]] | `cloud_microphysics` | `microphysics` | `` |
| [[lohse_physicochemical_2020]] | `cloud_microphysics` | `microphysics` | `` |
| [[mahale_variational_2019]] | `cloud_microphysics`, `remote_sensing` | `microphysics`, `remote_sensing` | `` |
| [[mallet_estimation_2009]] | `cloud_microphysics` | `microphysics` | `` |
| [[morrison_bayesian_2019]] | `cloud_microphysics`, `modeling` | `microphysics`, `modeling` | `` |
| [[moumouni_impact_2021]] | `cloud_microphysics`, `modeling` | `microphysics`, `modeling` | `` |
| [[raupach_retrieval_2017]] | `cloud_microphysics`, `remote_sensing` | `microphysics`, `remote_sensing` | `` |
| [[ryzhkov_polarimetric_2022]] | `cloud_microphysics`, `remote_sensing` | `microphysics`, `remote_sensing` | `` |
| [[saide_aerosol_2013]] | `aerosol`, `cloud_microphysics`, `modeling`, `remote_sensing` | `aerosol`, `microphysics`, `modeling`, `remote_sensing` | `` |
| [[saide_assessment_2016]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[seela_raindrop_2018]] | `cloud_microphysics` | `microphysics` | `` |
| [[seifert_aerosol_cloud_precipitation_2012]] | `aerosol`, `cloud_microphysics`, `modeling` | `aerosol`, `microphysics`, `modeling` | `` |
| [[shan_evaluating_2020]] | `cloud_microphysics`, `modeling` | `microphysics`, `modeling` | `` |
| [[shearer_unveiling_2022]] | `cloud_microphysics`, `instrumentation`, `remote_sensing`, `tropical_cyclone` | `microphysics`, `instrumentation`, `remote_sensing`, `tropical_cyclone` | `` |
| [[shpund_effects_2019]] | `cloud_microphysics`, `tropical_cyclone` | `microphysics`, `tropical_cyclone` | `` |
| [[tao_impact_2012_1]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[teller_effects_2006]] | `aerosol`, `cloud_microphysics`, `modeling` | `aerosol`, `microphysics`, `modeling` | `` |
| [[thurai_application_2018]] | `cloud_microphysics`, `modeling` | `microphysics`, `modeling` | `` |
| [[thurai_measurements_2019]] | `cloud_microphysics`, `instrumentation`, `modeling` | `microphysics`, `instrumentation`, `modeling` | `` |
| [[wu_characteristics_2019]] | `cloud_microphysics` | `microphysics` | `` |
| [[yuan_microphysical_2011]] | `aerosol`, `cloud_microphysics` | `aerosol`, `microphysics` | `` |
| [[zhang_statistical_2019]] | `cloud_microphysics` | `microphysics` | `` |

## Remaining Manual Review

No unresolved non-registry paper topics remain after conversion.

## Notes

- Non-paper maintenance pages and keyword pages were not converted.
- Existing `keyword_*` pages remain valid graph entry points.
- `needs_triage` is now a keyword/maintenance marker, not a research topic.
- Paper page body lines `- Topics:` and `- Keywords:` were synced with frontmatter after the conversion.
