---
type: synthesis
status: reviewed
source_status: peer-reviewed
reading_status: mixed
review_stage: integrated
topics: [aerosol, microphysics, modeling, climate_change]
keywords: [aerosol_scheme, microphysics_scheme, aerosol_microphysics_coupling, aerosol_cloud_interaction]
created: 2026-05-18
updated: 2026-05-18
sources: [stier_aerosol-climate_2005, mann_description_2010, liu_minimal_2012, tilmes_description_2023, morrison_new_2008, gettelman_new_2008, milbrandt_multimoment_2005, thompson_study_2014, forkel_sensitivity_2015, joos_coupling_2020]
---

# Aerosol Microphysics Scheme Synthesis

This page is now a bridge page. The previous combined topic has been split into two primary synthesis pages:

- [[aerosol_scheme_development_synthesis|Aerosol Scheme Development Synthesis]]
- [[microphysics_scheme_development_synthesis|Microphysics Scheme Development Synthesis]]

Use the split pages for future updates. Keep this page only for cross-theme coupling notes and backward compatibility with earlier links.

## Cross-Theme Coupling Question

How are aerosol schemes and cloud microphysics schemes coupled in atmospheric models?

## Current Working Answer

Aerosol schemes and cloud microphysics schemes developed along parallel tracks: aerosol schemes moved from prescribed/simple mass tracers toward modal and sectional representations of size, composition, mixing state, and aerosol microphysics; cloud microphysics schemes moved from diagnostic/single-moment bulk treatments toward double-moment, multi-moment, bin/sectional, and aerosol-aware formulations. The coupling frontier is the interface between aerosol activation, cloud droplet/ice nucleation, wet removal, cloud radiative properties, and precipitation formation.

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
