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
- `full_text_needed`: metadata exists, readable full text is missing.
- `full_text_done`: QCed `raw/full_text/<paper_file_key>.md` exists.
- `wiki_done`: `wiki/literature/<slug>.md` exists.
- `abstract_only`: only abstract was available; the paper page must say so.
- `blocked`: DOI/source/access problem needs human decision.
