# RKF Beginner Setup And First Research Project

This guide installs RKF from GitHub in the recommended local single-machine
mode. Shared Drive storage is an advanced, experimental setup and is not needed
for a first run.

## Requirements

- Git
- Python 3.9 or newer
- Codex app
- A writable local folder

RKF core has no required pip package, and the static dashboard needs no Node.js.

## Clone And Preview

```bash
git clone https://github.com/ChenHau-Lan/ResearchWiki.git
cd ResearchWiki
python3 tools/bootstrap_rkf.py
```

Preview is non-mutating. A clean clone reports `status: ready` and redacted
`would-create` / `would-initialize` operations. Resolve any `blocker_codes`
before applying; bootstrap refuses overlapping roots, nonempty storage, and
symlink config/storage/skill targets. Relative storage paths may not traverse
outside the checkout with `..`; use an explicit absolute path for an intentional
external storage root. Unwritable parents fail during preview.

## Apply And Verify

```bash
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --strict
```

After `--install-connector`, reopen the project or start a new Codex task so the
new task loads the updated skill catalog, then ask it to “Activate RKF.”

The optional connector lets other local projects resolve this checkout and
installs the repository's exact `rkf-auto-connect` skill into the machine-local
Codex skill directory. Neither is committed. Bootstrap creates ignored local
wiki, raw, and private-evidence roots plus a matching opaque writer registry.
Existing config or a differing installed skill is preserved and reported as
unverified; use the diagnostic rather than trying to overwrite it.
The skill bundle uses an exact manifest (`SKILL.md` plus
`agents/openai.yaml`). Apply stages the skill, creates the connector last, and
rolls back only byte-matching artifacts and empty directories created by that
attempt if a write fails.
`ready` means the required repository files, storage handles, and connection
doctor are usable. When this machine is configured as the designated writer,
it also means the writer registry is available.

## First Codex Task

```text
Activate RKF.
Show the current world context, paper queue, and lint status.
```

Every task starts with RKF OFF. Capture a first DOI as metadata-only and keep
the candidate/evidence boundary explicit.

## Connect Another Project

Preview:

```bash
python3 tools/rkf_auto_connect.py connect-project "/path/to/MyResearchProject" --project-name "MyResearchProject"
```

Apply after review:

```bash
python3 tools/rkf_auto_connect.py connect-project "/path/to/MyResearchProject" --project-name "MyResearchProject" --apply
```

This adds a v2 marker and missing project-local `RKF/` bridge files without
copying the database or overwriting existing notes. Legacy v1 upgrades require
the separate `--apply-upgrade` flag. Bridge files are completed before the
marker is written, and a failed attempt rolls back only content created by that
attempt.

## Dashboard And Discovery

Ask Codex to create an aggregate-only dashboard preview. Maintainers can also
run:

```bash
python3 tools/build_public_dashboard.py preview
```

Render the exact preview as an ignored, self-contained page before approval:

```bash
python3 tools/build_public_dashboard.py review --preview-id PREVIEW_ID
```

Open that preview's `review/index.html`. It is marked `PRIVATE REVIEW · NOT
PUBLISHED`, does not modify `site/`, and works without a local server. Publishing
the local site data requires the exact returned `preview_id` and
`snapshot_hash`. Remote GitHub Pages activation remains a separate deployment
decision.

For a clean install, start discovery with an explicit public-safe query because
the topic registry is initially empty. After you create and review your own
topics, Codex can use a topic ID and its `default_search_strings`; unknown or
retired topic IDs fail closed. Record only the exact approved preview and
accept only selected candidate IDs. Acceptance defaults to inbox/SourceRecord
capture with no paper draft and no claim promotion. OpenAlex is optional and
requires a machine-local API key.

See:

- [Traditional Chinese full guide](GETTING_STARTED.zh-TW.md)
- [Public dashboard and GitHub Pages](workflows/public-dashboard.zh-TW.md)
- [Paper discovery and safe intake](workflows/paper-discovery.zh-TW.md)
- [Auto-connect workflow](workflows/rkf-auto-connect.zh-TW.md)

## Validation And Privacy

```bash
python3 -m unittest discover -s tests
python3 tools/public_safety_scan.py
```

Never commit `rkf.workspace.toml`, `.rkf_data/`, `.rkf_private/`, PDFs, article
text, private Drive paths, machine-local connectors, keys, or tokens.
