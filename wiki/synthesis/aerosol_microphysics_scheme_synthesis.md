---
type: synthesis
status: draft
source_status: peer-reviewed
reading_status: mixed
review_stage: discussed
topics: [aerosol, microphysics, modeling, climate_change]
keywords: [aerosol_scheme, microphysics_scheme, aerosol_microphysics_coupling, aerosol_cloud_interaction]
created: 2026-05-18
updated: 2026-05-18
sources: [stier_aerosol-climate_2005, mann_description_2010, liu_minimal_2012, tilmes_description_2023, morrison_new_2008, gettelman_new_2008, milbrandt_multimoment_2005, thompson_study_2014, forkel_sensitivity_2015, joos_coupling_2020]
---

# Aerosol Microphysics Scheme Synthesis

## Research Question

How have aerosol schemes and microphysics schemes developed in atmospheric models, and how are aerosol and cloud microphysics processes coupled?

## Current Working Answer

Aerosol schemes and cloud microphysics schemes developed along parallel tracks: aerosol schemes moved from prescribed/simple mass tracers toward modal and sectional representations of size, composition, mixing state, and aerosol microphysics; cloud microphysics schemes moved from diagnostic/single-moment bulk treatments toward double-moment, multi-moment, bin/sectional, and aerosol-aware formulations. The coupling frontier is the interface between aerosol activation, cloud droplet/ice nucleation, wet removal, cloud radiative properties, and precipitation formation.

## Aerosol Scheme Development

- Early climate aerosol schemes often prioritized computational feasibility and radiative forcing, representing aerosol mass by species or simple modes.
- Modal aerosol schemes represent size distributions with a small number of lognormal modes. ECHAM5-HAM and GLOMAP-mode are important global examples [stier_aerosol-climate_2005; mann_description_2010].
- CAM5 MAM introduced a modal aerosol module with a more complete MAM7 and reduced MAM3, making the complexity/cost tradeoff explicit [liu_minimal_2012].
- Sectional aerosol schemes resolve aerosol size bins more explicitly. CARMA in CESM2 is a recent example and enables modal-vs-sectional comparison inside the same model framework [tilmes_description_2023].

## Aerosol Scheme Categories

- Bulk/species-mass schemes: efficient, often represent aerosol mass by species and use simplified size/composition assumptions.
- Modal schemes: represent size distributions as lognormal modes; assumptions include fixed or prescribed modal width, mode membership, and mixing-state simplification.
- Sectional/bin schemes: discretize particle size into bins; more flexible for growth and size-resolved processes but computationally expensive.
- Mixing-state-resolving or particle-resolved approaches: conceptually more complete but usually too expensive for long climate integrations.
- Aerosol-aware cloud schemes: use aerosol number or climatology to activate droplets and/or ice nuclei inside a cloud microphysics parameterization [thompson_study_2014].

## Microphysics Scheme Development

- Bulk one-moment schemes predict hydrometeor mass mixing ratios and diagnose number/size properties.
- Two-moment schemes predict both mass and number for one or more hydrometeor categories, improving size-distribution control and aerosol sensitivity [morrison_new_2008; gettelman_new_2008].
- Multi-moment schemes add higher moments such as radar reflectivity, allowing spectral shape to vary more flexibly [milbrandt_multimoment_2005].
- Bin/spectral schemes explicitly resolve particle size distributions and are often used as process-level benchmarks, but their cost limits routine NWP/climate use.
- Aerosol-aware microphysics adds activation and/or aerosol availability to bulk schemes; Thompson-Eidhammer is a key WRF example [thompson_study_2014].

## How Many Microphysics Scheme Types?

There is no meaningful fixed total number because every model has its own named implementation and variants. A useful taxonomy has at least five families:

- Diagnostic/saturation adjustment or very simple cloud schemes.
- One-moment bulk schemes.
- Two-moment bulk schemes.
- Multi-moment bulk schemes.
- Bin/sectional/spectral schemes.
- Particle-based or super-droplet schemes can be treated as an emerging sixth family.

Within WRF alone, users encounter many named schemes, while climate models have separate families such as CAM MG/MG2 and GFDL AM3 two-moment schemes. Therefore, the robust answer is not a global count but a classification by prognostic moments, particle-size treatment, hydrometeor categories, aerosol awareness, and coupling to radiation/chemistry.

## Current Weaknesses in Microphysics Schemes

The main gap is not simply adding more categories; it is uncertainty in process closure under unresolved variability. The weak points are:

- Aerosol activation and ice nucleation under subgrid vertical velocity, supersaturation, and mixing variability.
- Representation of hydrometeor size-distribution shape and its evolution.
- Secondary ice production and mixed-phase processes.
- Coupling consistency between cloud microphysics, aerosol removal, chemistry, radiation, and turbulence.
- Scale awareness: parameters tuned for cloud-resolving or mesoscale grids may not transfer cleanly to kilometer-scale, global storm-resolving, or climate grids.
- Evaluation limits: many schemes can match one observable while compensating through incorrect process pathways.

## Aerosol-Microphysics Coupling

At least the following model families in this wiki now have explicit or semi-explicit aerosol-microphysics coupling evidence:

- CAM5/CESM with MAM and two-moment stratiform cloud microphysics: couples aerosol properties to activation and cloud/radiation-relevant microphysics [liu_minimal_2012; morrison_new_2008; gettelman_new_2008].
- CESM2 with CARMA: sectional aerosol coupled to chemistry, clouds, radiation, and transport [tilmes_description_2023].
- WRF Thompson-Eidhammer aerosol-aware microphysics: couples water-friendly aerosol to droplet activation and ice-friendly aerosol to ice activation [thompson_study_2014].
- WRF-Chem: online chemistry/aerosol/cloud interactions; sensitivity depends on microphysics scheme choice [forkel_sensitivity_2015].
- EMAC-MADE3: couples modal aerosol to cirrus ice formation [joos_coupling_2020].
- ECHAM5-HAM and UKCA/GLOMAP-mode provide global aerosol-climate/microphysics frameworks that connect aerosol lifecycle to optical and cloud-relevant properties [stier_aerosol-climate_2005; mann_description_2010].

Main coupling processes:

- CCN activation to cloud droplet number.
- IN or dust-related ice nucleation.
- Aerosol wet scavenging and in-cloud/below-cloud removal.
- Cloud droplet effective radius and cloud optical properties.
- Autoconversion/accretion/precipitation susceptibility through droplet number and size.
- Aerosol-radiation interactions and semi-direct effects.
- Cirrus ice formation and aerosol-ice interactions.

## Evidence Against / Complications

- Forkel et al. show that changing only the microphysics scheme in WRF-Chem can change aerosol-radiation-cloud responses, meaning aerosol coupling cannot be evaluated independently from microphysics closure [forkel_sensitivity_2015].
- MAM3 vs MAM7 and CARMA vs MAM4 show that aerosol complexity can be reduced, but not without process-specific biases and size-range/mixing-state assumptions [liu_minimal_2012; tilmes_description_2023].
- Thompson-Eidhammer gives explicit aerosol-aware behavior, but simplified aerosol inputs and climatological profiles can still dominate results if not constrained by observations [thompson_study_2014].

## Open Questions

- Which aerosol complexity is sufficient for tropical cyclone precipitation problems: simple prescribed CCN, modal aerosol, or online chemistry?
- Which microphysics uncertainties dominate aerosol effects: activation, autoconversion, mixed-phase ice, or sedimentation?
- How transferable are aerosol-aware microphysics schemes across convective, stratiform, fog, and tropical cyclone environments?
- Can radar/DSD observations constrain the microphysical parameters that most affect aerosol sensitivity?
