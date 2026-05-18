---
type: synthesis
status: draft
source_status: peer-reviewed
reading_status: mixed
review_stage: discussed
topics: [aerosol, modeling, climate_change]
keywords: [aerosol_scheme, aerosol_microphysics, modal_aerosol, sectional_aerosol, aerosol_cloud_interaction]
created: 2026-05-18
updated: 2026-05-18
sources: [stier_aerosol-climate_2005, mann_description_2010, liu_minimal_2012, tilmes_description_2023, thompson_study_2014, forkel_sensitivity_2015, joos_coupling_2020]
---

# Aerosol Scheme Development Synthesis

## Research Question

How have aerosol schemes in atmospheric models developed, what classes of aerosol schemes are commonly used, and what assumptions do they make?

## Current Working Answer

Aerosol schemes developed from computationally cheap mass/species representations toward modal and sectional aerosol microphysics. The main tension is always the same: represent enough aerosol size, composition, mixing state, activation potential, and removal physics to support climate/cloud questions, without making the model too expensive for long simulations.

## Development Path

- Early and simplified schemes often treated aerosol mass by species, with limited size-resolution and simplified optical/cloud activation behavior.
- Modal aerosol schemes represent size distributions with a small number of lognormal modes. ECHAM5-HAM and GLOMAP-mode are important global examples [stier_aerosol-climate_2005; mann_description_2010].
- CAM5 MAM made the complexity tradeoff explicit through MAM7 and simplified MAM3 [liu_minimal_2012].
- Sectional aerosol schemes resolve size bins more explicitly. CARMA in CESM2 is a recent example and is useful for comparing modal and sectional behavior in a climate-model framework [tilmes_description_2023].
- Aerosol-aware microphysics schemes bridge aerosol schemes and cloud microphysics by using aerosol properties or climatologies for droplet/ice activation [thompson_study_2014].

## Scheme Categories

- Bulk/species-mass schemes: efficient, but usually assume simplified size distribution and mixing state.
- Modal schemes: represent aerosol size distributions as lognormal modes.
- Sectional/bin schemes: discretize the aerosol size distribution into bins.
- Mixing-state-resolving or particle-resolved schemes: conceptually richer, but generally too expensive for routine global climate integrations.
- Aerosol-aware cloud schemes: do not always carry full online aerosol chemistry, but use aerosol number or type to affect cloud droplet and/or ice nucleation.

## Common Assumptions

- Aerosol size distribution can be represented by a small number of modes or bins.
- Modal width may be fixed or weakly constrained.
- Mixing state is simplified; internally mixed assumptions are common.
- Aerosol activation can be parameterized from size/composition and model-resolved or diagnosed supersaturation.
- Emissions, aging, wet removal, and vertical transport are uncertain but often strongly shape cloud-relevant aerosol.
- Reduced schemes such as MAM3 assume that a cheaper representation can preserve key aerosol-climate behavior for long simulations [liu_minimal_2012].

## Coupling From the Aerosol-Scheme Side

Aerosol schemes couple into cloud microphysics mostly through:

- CCN activation to cloud droplet number.
- IN or dust/ice-nucleating-particle effects on ice formation.
- Aerosol wet scavenging and in-cloud processing.
- Cloud droplet effective radius and cloud optical properties.
- Aerosol-radiation and semi-direct effects.
- Cirrus ice formation in aerosol-climate models such as EMAC-MADE3 [joos_coupling_2020].

## Evidence Against / Complications

- More aerosol detail is not automatically better if emissions, removal, or activation closure are poorly constrained.
- Modal vs sectional schemes can differ in size distribution and aging behavior, but the value of extra complexity depends on the target process [tilmes_description_2023].
- WRF-Chem sensitivity work suggests aerosol-cloud outcomes depend strongly on the selected cloud microphysics scheme, so aerosol scheme evaluation cannot be isolated from microphysics closure [forkel_sensitivity_2015].

## Open Questions

- For tropical cyclone precipitation, is prescribed CCN enough, or is online aerosol chemistry needed?
- Which aerosol processes dominate uncertainty: emissions, aging, wet removal, activation, or ice nucleation?
- For wildfire smoke / PyroCb, does sectional aerosol treatment materially change stratospheric aging and cloud-coupling conclusions?
