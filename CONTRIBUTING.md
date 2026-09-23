# Contributing

Contributions to documentation, passive telemetry, diagnostics and test coverage
are welcome. Telemetry and recordings are passive; the explicit device-time
alignment button is the only production write action. Changes must
preserve one receiving TCP connection per entry and must not introduce polling
or control commands as a side effect of setup, reconnect or recording.

## Development setup

The project requires Python 3.14.2 or later. Development dependencies, including
the Home Assistant test harness, are pinned through `uv.lock`.

```sh
uv sync --locked --group dev
uv run pytest -q
uv run ruff check custom_components tests tools/inventory_capture.py tools/compare_captures.py
uv run ruff format --check custom_components tests tools/inventory_capture.py tools/compare_captures.py
git diff --check
```

Tests use minimal fixtures and simulated gateways. They must not access real
hardware. The CI test workflow runs the suite and lint/format checks; a separate
workflow validates HACS metadata. HACS validation is not a physical-device test.

## Repository structure

| Path | Purpose |
|---|---|
| `custom_components/proxon_hesp/` | Installable Home Assistant integration |
| `custom_components/proxon_hesp/hesp/` | Protocol decoding and transport modules |
| `tests/` | Protocol, Home Assistant and lifecycle regression tests |
| `tests/fixtures/` | Minimal reviewed recorded test vectors |
| `tools/` | Offline analysis, checksum derivation and protocol research helpers |
| `docs/` | Public compatibility, protocol and diagnostic documentation |

Some research helpers model queries or a bounded diagnostic exchange. They are
not connected to the production receiver and are not supported user-facing
controls. Generating a candidate query does not establish safe bus access or
validate a response interpretation.

## Adding or changing a data point

Provide a minimal independently recorded telegram with complete identity,
selector, length and checksum. Explain the proposed interpretation and its
source: display comparison, reference documentation or an explicitly experimental
hypothesis. A valid checksum alone does not confirm meaning.

For a new entity, specify units, default enabled state, names in English and
German, valid ranges, invalid/missing-data handling and freshness behaviour.
Test fragmentation, wrong identities, corrupt data and relevant edge cases.
Do not turn missing data into zero, off or fault-free. Invalid channels must not
invalidate valid neighbouring channels.

Preserve existing unique IDs and user settings. Avoid assigning statistics classes
until counter/reset behaviour is known. Extend the existing inventory and replay
tools instead of introducing incompatible framing or checksum rules.

## Documentation and privacy

Write user documentation in German and developer references in English, following
the language policy below. Explain
supported behaviour, reproducible evidence and limitations. Keep implementation
history only when it helps migration or understanding a current design decision.

Do not commit personal investigation diaries, service records, full diagnostic
exports, photo/video filenames, private absolute paths, credentials or household
operating histories. Store working notes outside the repository; `tmp/` and
`captures/` are ignored for local analysis. Review staged changes, including new
fixtures, before publishing. Ignore rules do not protect already tracked files.

Prefer small sanitized test vectors and reproducible checks over publishing entire
recordings. Keep source attribution in [NOTICE.md](NOTICE.md) when adapting
reference material. Removing a file in a new commit does not remove it from
existing Git history, tags or release assets.

## Release preparation

Before a functional release:

1. Run the complete test suite, lint/format checks and HACS validation.
2. Verify upgrade behaviour from 0.8.0, including entity identities, user settings,
   availability and diagnostic export. Report simulated checks and live acceptance
   separately.
3. Update the manifest version, project version, lockfile and release notes.
4. Review the public diff for private data and unresolved claims.
5. Publish the reviewed changes, then run **Publish release** on `main` to create
   the matching tag and GitHub release. The workflow extracts only the matching
   version section from `RELEASE_NOTES.md`; missing, empty or duplicate sections
   fail publication. Do not overwrite an existing release.

A development push does not publish a release or update a user's installation.
HACS updates still require user installation and a Home Assistant restart.

## Documentation language

User documentation and release notes are maintained in German. README.en.md is
an English entry point, not a complete translated manual. Code, code comments,
this contribution guide and protocol/offline-analysis references remain English.
The Home Assistant UI retains both German and English translations.

Keep each document in its assigned language and label links to English technical
references from user guides. Preserve protocol identifiers, CLI arguments and
machine-readable status values literally. Do not translate license texts.
Distinguish released behavior from unreleased changes. Release bodies must contain
only the matching version section; translating the local changelog does not update
previously published GitHub release bodies or files in existing tags.

See [offline analysis](docs/OFFLINE_ANALYSIS.md) for the command-line workflow
and [German documentation](README.md#dokumentation) for user-facing instructions.
