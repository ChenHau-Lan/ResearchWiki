# DOI Dashboard

This board tracks where each resolved DOI is in the paper-source ingest process.

## DOI Status Board

| Last Name_Year | Journal | DOI | Wiki Status | PDF | Full Text |
|---|---|---|---|---|---|

## DOI Notes

| DOI | Next Action | Updated | Note |
|---|---|---|---|

## Status Legend

- `new`: newly added, not processed yet.
- `metadata_ok`: title/authors/year/venue/DOI checked.
- `candidate_found`: metadata, DOI, PDF, or legal source candidates exist but
  have not been approved for evidence use.
- `pdf_checkpoint_required`: a candidate PDF, URL, screenshot, or local file
  needs human approval before being treated as evidence.
- `pdf_downloaded`: approved PDF evidence is present in the configured PDF root.
- `full_text_needed`: metadata exists, readable full text is missing.
- `full_text_done`: QCed `raw/full_text/<paper_file_key>.md` exists.
- `wiki_done`: `wiki/literature/<slug>.md` exists.
- `abstract_only`: only abstract was available; the paper page must say so.
- `blocked`: DOI/source/access problem needs human decision.
