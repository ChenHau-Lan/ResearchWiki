---
type: synthesis
status: draft
source_status: peer-reviewed
reading_status: mixed
review_stage: discussed
topics: [microphysics, cloud_physics, modeling, precipitation]
keywords: [microphysics_scheme, bulk_microphysics, two_moment, multimoment, bin_microphysics, aerosol_aware_microphysics]
created: 2026-05-18
updated: 2026-05-18
sources: [morrison_new_2008, gettelman_new_2008, milbrandt_multimoment_2005, thompson_study_2014, forkel_sensitivity_2015]
---

# Microphysics Scheme Development Synthesis

## Research Question

How have cloud microphysics schemes developed historically, how should their types be counted, and what is currently missing?

## Current Working Answer

Microphysics schemes progressed from simple diagnostic or one-moment bulk schemes toward two-moment, multi-moment, bin/spectral, and aerosol-aware schemes. Counting named schemes is less useful than classifying them by prognostic moments, size-distribution treatment, hydrometeor categories, aerosol awareness, and scale assumptions.

## Development Path

- Simple/diagnostic schemes use saturation adjustment or reduced hydrometeor treatment.
- One-moment bulk schemes predict hydrometeor mass mixing ratios and diagnose particle number/size.
- Two-moment schemes predict mass and number, improving control of size distributions and aerosol sensitivity [morrison_new_2008; gettelman_new_2008].
- Multi-moment schemes predict additional moments such as reflectivity, allowing spectral shape to vary more flexibly [milbrandt_multimoment_2005].
- Bin/spectral schemes explicitly resolve particle size distributions and are often used as process benchmarks.
- Aerosol-aware microphysics adds droplet/ice activation and aerosol availability to cloud microphysics [thompson_study_2014].

## How Many Types?

There is no defensible single total number of microphysics schemes because each model has named implementations and variants. A useful taxonomy has at least six families:

- Diagnostic or saturation-adjustment schemes.
- One-moment bulk schemes.
- Two-moment bulk schemes.
- Multi-moment bulk schemes.
- Bin/sectional/spectral schemes.
- Particle-based or super-droplet schemes.

For research organization, classify by family first, then by named implementation.

## What Is Most Missing?

The biggest gap is process closure under unresolved variability, not merely adding more categories. Important weak points:

- Subgrid supersaturation and vertical velocity for aerosol activation.
- Hydrometeor size-distribution shape evolution.
- Ice nucleation and secondary ice production.
- Mixed-phase process representation.
- Coupling consistency between microphysics, aerosol removal, chemistry, radiation, and turbulence.
- Scale awareness across cloud-resolving, kilometer-scale, and climate-grid simulations.
- Observational constraints: schemes can match one observable while using compensating process errors.

## Coupling From the Microphysics Side

Microphysics schemes couple to aerosol processes through:

- Droplet activation and cloud droplet number.
- Autoconversion/accretion changes through droplet number and size.
- Ice nucleation and cirrus formation.
- Wet scavenging and aerosol removal.
- Cloud optical properties via droplet effective radius.
- Precipitation susceptibility.

WRF Thompson-Eidhammer is a direct aerosol-aware microphysics example [thompson_study_2014]. WRF-Chem sensitivity work shows that aerosol-cloud conclusions can change when the microphysics scheme changes [forkel_sensitivity_2015].

## Open Questions

- Which microphysics closure dominates aerosol sensitivity: activation, autoconversion, ice nucleation, sedimentation, or mixed-phase processes?
- Can radar and DSD retrievals constrain the most important microphysics parameters?
- How transferable are aerosol-aware microphysics assumptions across stratiform, convective, fog, and tropical cyclone environments?
