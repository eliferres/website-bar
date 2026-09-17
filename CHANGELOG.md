# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- website-bar installs as a command: `pipx install git+https://github.com/eliferres/website-bar` puts `website-bar` on your PATH, and `website-bar --version` prints the version.

### Changed
- CI runs the tests on Python 3.9, 3.11 and 3.13; 3.13 replaces 3.12, so the newest supported release is covered.
- Reorganized the README: the walkthrough, the bar format and the check families sit under plainer headings, the file table is one sentence under Quick start, and the license line closes the file.

### Fixed
- The demo transcript and the terminal picture showed an abridged report: the header lines, the offending strings and their line numbers were all missing. Both now come from a real run, and a new test replays every recorded command and fails if a single character drifts.
- The demo picture no longer cuts its long lines off at the right edge: rows wider than the box ran past it mid-word with no ellipsis. Only the drawing changed; the recorded session is untouched.
- The terminal picture ends on the failing page's verdict instead of cutting off mid-run, and its description and alt text name what it shows; the run on the clean page stays in the walkthrough below it.
- The CI step that grades the demo pages asserted only that the failing page exited non-zero, so a crashed run counted as a pass. It now requires exit 1 exactly.
- A bar file holding valid JSON that is not an object, `[]` for one, crashed with a traceback and exit 1. It now refuses with one line naming the file, and exit 2, like every other unreadable bar file.
- A bar file with a misspelled or missing `checks` key graded nothing and printed a PASS at exit 0, so a page nothing had checked came back green. A bar with no `checks` key is now refused with one line naming the file, and exit 2.
- An unexpected exception left the tool exiting 1, the same code as a page that failed its bar, so a CI job gating on exit 1 read a crash as a graded failure. Any exception the tool does not expect now prints one line naming it as a bug in website-bar, with the exception type and message, and exits 2.
- A bar whose top-level `bar` key holds null, a string or a list crashed with a traceback after the page was graded. It is now refused when the file loads, with one line naming the file, and exit 2.
- A bar whose `checks` is null, or whose check family holds a string instead of a settings object, crashed the same way. The bar's shape is now checked when it loads and refused by name, and a setting the checks cannot use is caught before it can become a traceback, so every unusable bar file ends in one line and exit 2.
- Every setting in a bar file is now checked against the type its check family reads when the file loads, and the first one that does not fit is refused with one line naming the family, the setting and the type expected, and exit 2. A setting name no family reads is refused the same way. A string where the phrase list belongs used to match letter by letter and report invented failures against a clean page, and a misspelled `enabled` used to turn its family off and report a PASS at exit 0.
- The README and the module docstring listed three causes of exit 2 and the tool has six: both now name a bar file shaped so the checks cannot use it, and a bug in website-bar itself, in the same words.
- The README and the module docstring documented only exit 0 and exit 1. Both now document exit 2, which the tool has always used for bad usage, an unreadable page and an unreadable bar file, so a CI job can tell a failing page from a broken run.

## [1.1.0](https://github.com/eliferres/website-bar/releases/tag/v1.1.0) - 2026-09-03

### Added
- Added a terminal demo to the README's first screen, showing website_bar.py failing the demo page on five rules, then passing the clean page across all four check families.
- Added a test for the color-count rule, the one craft_basics rule that had no test of its own.
- Added macos-latest to the CI matrix alongside ubuntu-latest.

### Changed
- Added type hints to the seven remaining functions in website_bar.py, matching the file's existing style.

## [1.0.0](https://github.com/eliferres/website-bar/releases/tag/v1.0.0) - 2026-08-31

First public release.
