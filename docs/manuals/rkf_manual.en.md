# RKF v1 Researcher Manual

RKF is an LLM Wiki-based research knowledge framework for active academic
reading. Its core path is Paper → locator-backed Evidence → human-reviewed
Claim → Synthesis.

## Paper Maturity

`access_state` is `metadata | abstract | partial | fulltext`.
`review_state` is `unread | skimmed | read | annotated | reproduced`.
Legacy reading labels are normalized conservatively and unknown values become
data-quality findings.
When authorized full text is unavailable, use the explicit `needs-user-pdf`
blocker; never infer that a paper was read from metadata alone.

## Five workflows

These are the Common Workflows in the Codex app:

- Add captures DOI, URL, PDF pointer, note or selected paper without promotion.
- Ask retrieves governed context deterministically before optional semantic
  retrieval; evidence-backed claims expose locators.
- Read records annotations, corrections and Evidence.
- Compare & Synthesize records Claim/Synthesis agreement, opposition and gaps.
- Review shows actionable research gaps and connected-project lineage.

The academic-research-suite may search, reason, write or review, but its output
remains a proposal until RKF evidence rules are satisfied.

## Save rules

Candidates and LLM output are not evidence. Verified claims require
human-verified, locator-backed Evidence. PDFs, article text, secrets, private
paths and raw prompts do not enter public knowledge.
