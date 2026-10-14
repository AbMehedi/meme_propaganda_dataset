# Cleanup provenance — 14 October 2026

## Confirmed findings

The original repository root was the intended starter folder, with no nested Git
repository found. Its working tree was clean; ignored virtual environments, OCR
corrections and runtime data were present. The reflog shows checkout from master
at c14ed58 to campnet-label-studio-starter, followed by 0cc3819 (starter), 2744bb8
(annotation phase), ba9e6dc and b7eb6d4 (latest UI improvements). The inherited
collection files explain the mixed file tree; no accidental merge is visible in
this sequence. The exact original intention cannot be proved from Git history.

GitHub origin was verified as https://github.com/AbMehedi/meme_propaganda_dataset.git.
Remote main remained c14ed58396dd53a5e2422da738129e142c243b57 and the UI branch
remained b7eb6d42f97c22439701795b11c318775ec19730 during investigation.

## Base and scope

The clean branch starts at c14ed58, immediately before the starter commits. A
single curated commit replaces the inherited collection tree with the relevant
latest starter files. Old collection code remains in ancestry for provenance;
it is absent from the new branch's checked-out deliverable. No shared history is
rewritten. This branch is not merged into main.

Retained: latest Python pilot package, XML interfaces and generator, import/export
and optional model utilities, OCR review utility and records, corrected OCR,
17-image pilot, guidelines, training codebook, launchers and tests.
Excluded: downloader, database migration/collection OCR pipeline, their utils,
Docker files, old collection README and research plan, full 406-image frozen data,
raw collection images, QA outputs, old generated task previews, environments,
runtime databases and generated dry-run/model logs. Original experimental reports
remain historical; their generated logs are preserved in the recovery snapshot.

## Preservation

The original checkout, branches, ignored files and frozen dataset were left in
place. A verified original-all-refs.bundle includes branches, stash and history.
An original-files snapshot includes all non-environment working files (including
ignored corrected OCR and runtime data); virtual environments and caches remain
in the original checkout. The stash contains three research documents and a ZIP;
its annotation guideline is identical to the retained latest guideline. The other
planning documents remain recoverable in the bundle and are outside this starter.

The clean checkout is separate from the original. Local copies of frozen inputs
are used only for validation and ignored by Git. Requirements now install the
verified Label Studio stack; OCR dependencies are optional. The example config
contains no credentials. New runtime and experiment outputs are ignored.

## Validation performed

- All 19 unit tests passed with local frozen inputs available.
- A staged-file export without the full dataset passed 17 tests; two full-freeze
  checks skipped explicitly. Fixed test runtime-directory creation for fresh clones.
- Rebuilt into a disposable output: 17 image/database/OCR matches, three explicit
  exclusions and one author-reviewed empty transcription.
- Label Studio 1.23.2 validated all three pilot XML interfaces. Real API integration
  checked 17 imports, idempotent import, authenticated image bytes, eight synthetic
  manual cases, blind Stage A and assisted save/edit/reject/export handling.
- Fresh deliverable started a separate Label Studio server on port 18091 and
  returned HTTP 200 from /health; the test process was stopped afterward.
- pip check found no broken requirements in the existing environment.
- PowerShell launcher parsed successfully; added configurable LAN address and a
  missing-environment error. Removed the obsolete hard-coded host address.
- All 409 frozen source files (excluding SQLite transient sidecars) matched the
  preservation snapshot by SHA-256 after validation.
- Reviewed the staged 65-file tree, base diff and whitespace check. CSVs and the
  authoritative guideline preserve byte-level line endings for stored fingerprints.

No fresh network dependency installation, browser interaction, OCR model download,
or live model inference was performed. Dependencies were exercised in the existing
Python 3.11 environment. The API/HTTP checks do not establish browser layout or
mouse interaction correctness. Historical experimental results remain historical.
