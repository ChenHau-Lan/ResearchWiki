---
type: concept
status: draft
source_status: personal-note
reading_status: mixed
review_stage: discussed
topics: [literature, taxonomy]
keywords: [paper_topics, topic_registry]
created: 2026-05-18
updated: 2026-05-18
sources: []
---

# Paper Topics Registry

This page is the controlled list for `topics:` in paper frontmatter. Use these topics for broad research directions. Use `keywords:` for narrower mechanisms, methods, datasets, and recurring concepts.

## Topic Rules

- Each paper should usually have 1-3 topics.
- Add a new topic only when it represents a durable research direction, not a one-off term.
- If a term is specific enough to describe a mechanism, method, dataset, case, or instrument, put it in `keywords:` instead.
- When adding a new topic, add it to this registry and update relevant synthesis or concept pages.
- Prefer a compact topic set for navigation. If a topic mostly refines another topic, keep the broad term in `topics:` and move the refined term to `keywords:`.

## Active Paper Topics

| Topic | Scope | Use When |
|---|---|---|
| `aerosol` | Aerosol properties, sources, transport, chemistry, loading, and aerosol effects. | The paper is mainly about aerosol processes or aerosol forcing. |
| `microphysics` | Cloud and precipitation microphysics, hydrometeor processes, DSD, warm/cold rain pathways, and microphysics parameterizations. | The paper focuses on microphysical mechanisms, schemes, or microphysical observations. |
| `cloud_physics` | Broader cloud dynamics, thermodynamics, cloud regimes, cloud organization, entrainment, and cloud-radiation interactions. | The paper is about cloud processes beyond microphysics alone. |
| `remote_sensing` | Radar, satellite, lidar, retrievals, validation, and observational inference. | The paper uses or evaluates remote-sensing products or retrieval methods. |
| `modeling` | Numerical models, parameterization tests, sensitivity experiments, simulation design. | The paper is centered on model behavior, model setup, or numerical experiments. |
| `instrumentation` | Instruments, field campaigns, sensors, measurement uncertainty, calibration. | The paper describes measurement systems or instrument-specific interpretation. |
| `tropical_cyclone` | Tropical cyclone structure, genesis, track, intensification, rainfall, eyewall, landfall. | The paper's main meteorological system is a tropical cyclone. |
| `precipitation` | Rainfall processes, precipitation distribution, intensity, extremes, or validation. | The paper's central outcome or process is precipitation. |
| `wildfire` | Wildfire emissions, biomass burning, smoke plumes, PyroCb, aerosol transport, and smoke-cloud effects. | The paper is centered on wildfire or biomass-burning impacts. |
| `radar_meteorology` | Radar observations, polarimetric radar, radar retrievals, radar validation, and radar-based storm interpretation. | The paper is mainly radar-specific rather than general remote sensing. |
| `field_campaign` | Field experiments, aircraft campaigns, campaign datasets, deployment design, and campaign intercomparison. | The paper is organized around a named observational campaign or field deployment. |
| `climate_change` | Long-term climate change, future projections, climate attribution, and changing hazards. | Climate change is a primary framing or result, not only background context. |

## Candidate Topics

Use this section as a staging area before promoting a topic to the active list.

| Candidate | Reason to Consider | Promote When |
|---|---|---|
| `boundary_layer` | May become useful for cloud-topped boundary layer and marine stratocumulus papers. | It becomes a recurring synthesis direction not covered by `cloud_physics`. |
| `radiative_forcing` | Currently may be better as a keyword under aerosol, wildfire_smoke, stratospheric_aerosol, or climate_change. | It becomes a central research direction with multiple synthesis pages. |
| `data_assimilation` | Could group variational or Bayesian retrieval/modeling methods. | It becomes a repeated method family across paper and code pages. |
| `stratospheric_aerosol` | Currently better as `topics: [aerosol]` with `keywords: [stratospheric_aerosol]`. | It becomes a major standalone direction. |

## Simplification Guidance

The active topic list is intentionally a small registry of broad directions, not a full ontology. For paper pages, prefer these patterns:

| If tempted to use | Prefer |
|---|---|
| `cloud_microphysics` as topic | `topics: [microphysics]` |
| `wildfire_smoke` as topic | `topics: [wildfire, aerosol]`, `keywords: [wildfire_smoke]` |
| `field_campaigns` as topic | `topics: [field_campaign]` |
| `radar metrology` as topic | Use `radar_meteorology` unless the paper is specifically about radar measurement uncertainty/calibration; then use `instrumentation` and `keywords: [radar_metrology]`. |
| `pyrocb` as topic | `topics: [wildfire, aerosol]`, `keywords: [pyrocb]` |
| `retrieval_validation` as topic | `topics: [remote_sensing]`, `keywords: [retrieval_validation]` |
| `drop_size_distribution` as topic | `topics: [microphysics]`, `keywords: [drop_size_distribution]` |
| `microphysics_scheme` as topic | `topics: [microphysics, modeling]`, `keywords: [microphysics_scheme]` |
| `landfall` as topic | `topics: [tropical_cyclone, precipitation]`, `keywords: [landfall]` |
| `radiative_forcing` as topic | `topics: [aerosol, climate_change]`, `keywords: [radiative_forcing]` |

## Common Keywords

These are usually better as `keywords:` than `topics:`.

- `aerosol_cloud_interaction`
- `drop_size_distribution`
- `microphysics_scheme`
- `bulk_microphysics`
- `aerosol_scheme`
- `retrieval_validation`
- `landfall`
- `pyrocb`
- `wildfire_smoke`
- `stratospheric_aerosol`
- `warm_rain_suppression`
- `convective_invigoration`
