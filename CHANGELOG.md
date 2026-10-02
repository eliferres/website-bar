# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

Nothing yet.

## [1.2.0](https://github.com/eliferres/website-bar/releases/tag/v1.2.0) - 2026-10-02

### Added
- website-bar installs as a command: `pipx install git+https://github.com/eliferres/website-bar` puts `website-bar` on your PATH, and `website-bar --version` prints the version.
- Stylesheets pulled in with `@import` are now read and graded, from `<style>` blocks and from linked or imported stylesheets, relative paths resolved against the sheet that holds the import and absolute URLs fetched as written. Each stylesheet is read once per page, which also ends an import cycle, and a chain more than ten imports deep stops the run with one line and exit 2. A sluggish transition one import away from the page used to pass unseen.
- A local stylesheet named with a query or fragment, `slow.css?v=3`, is now read from `slow.css`. The suffix was kept as part of the file name, so a sheet that exists stopped the run at exit 2.

### Changed
- CI runs the tests on Python 3.9, 3.11 and 3.13; 3.13 replaces 3.12, so the newest supported release is covered.
- Reorganized the README: the walkthrough, the bar format and the check families sit under plainer headings, the file table is one sentence under Quick start, and the license line closes the file.
- The demo transcript test and the README's slop patterns section now describe the transcript and the emoji-bullet counter in plain terms.
- The README opens with badges for the license, the supported Python versions and the dependency count beside the CI badge.

### Fixed
- The demo transcript and the terminal picture showed an abridged report: the header lines, the offending strings and their line numbers were all missing. Both now come from a real run, and a new test replays every recorded command and fails if a single character drifts.
- The demo picture no longer cuts its long lines off at the right edge: rows wider than the box ran past it mid-word with no ellipsis. Only the drawing changed; the recorded session is untouched.
- The terminal picture shows the run on the failing demo page from the command to its verdict, and its description and alt text name what it shows; the run on the clean page stays in the walkthrough below it.
- The CI step that grades the demo pages asserted only that the failing page exited non-zero, so a crashed run counted as a pass. It now requires exit 1 exactly.
- A bar file holding valid JSON that is not an object, `[]` for one, crashed with a traceback and exit 1. It now refuses with one line naming the file, and exit 2, like every other unreadable bar file.
- A bar file with a misspelled or missing `checks` key graded nothing and printed a PASS at exit 0, so a page nothing had checked came back green. A bar with no `checks` key is now refused with one line naming the file, and exit 2.
- An unexpected exception left the tool exiting 1, the same code as a page that failed its bar, so a CI job gating on exit 1 read a crash as a graded failure. Any exception the tool does not expect now prints one line naming it as a bug in website-bar, with the exception type and message, and exits 2.
- A bar whose top-level `bar` key holds null, a string or a list crashed with a traceback after the page was graded. It is now refused when the file loads, with one line naming the file, and exit 2.
- A bar whose `checks` is null, or whose check family holds a string instead of a settings object, crashed the same way. Both shapes are checked when the file loads and refused by name, with one line and exit 2.
- Every setting in a bar file is now checked against the type its check family reads when the file loads, and the first one that does not fit is refused with one line naming the family, the setting and the type expected, and exit 2. A setting name no family reads is refused the same way. A string where the phrase list belongs used to match letter by letter and report invented failures against a clean page, and a misspelled `enabled` used to turn its family off and report a PASS at exit 0.
- A bar in which no check family is enabled, by an empty `checks` object or by every family set to false, graded nothing and printed a PASS at exit 0. It is now refused with one line naming the file, and exit 2. Turning some families off is unchanged.
- The README and the module docstring documented only exit 0 and exit 1. Both now document exit 2 and name what returns it: bad usage, a page or a stylesheet it links or imports that cannot be read or fetched, a bar file that is missing, not valid JSON or shaped so the checks cannot use it, and a bug in website-bar itself. A CI job can tell a failing page from a broken run.
- A line break inside a heading now separates the words on either side. The heading text was joined with nothing in between, so `<h1>Ship the whole platform<br>to every marketing team</h1>` counted seven words against a ceiling of seven and passed, and `Welcome<br>to the show` got past the banned opener "Welcome to". Every block element and every void element inside a heading separates words the same way, except `<wbr>`, which marks a break point inside one word.
- A `max_words` key that is not a heading tag is now refused when the bar loads, with one line naming the key, and exit 2. The keys were never checked, so `{"title": 3, "h1 ": 3}` set ceilings no heading was measured against and the failing demo page printed PASS at exit 0. `max_words` is the only setting that holds a mapping.
- A `max_words` that gives one heading tag two ceilings in different case, `{"h1": 3, "H1": 9}`, is now refused when the bar loads, with one line naming both keys, and exit 2. Keys are matched without case, so the later one silently won and a six-word h1 passed a ceiling of three.
- A blank or whitespace-only entry in `banned_openers` is now refused when the bar loads, with one line and exit 2. An empty string flagged every heading, and one made of spaces matched none while counting as a rule switched on.
- A headline economy or craft basics family that is enabled with no rule switched on, `{"craft_basics": {"enabled": true}}` for one, graded nothing and printed a PASS at exit 0. It is now refused when the bar loads, with one line naming the family and the settings that would switch a rule on, and exit 2. Motion durations and slop patterns grade on defaults and still need only `enabled`.
- A stylesheet the page links or imports that cannot be read, a missing file or a failed fetch, now stops the run with one line naming the stylesheet, and exit 2. It used to become a note under the report, so a page graded on part of its CSS printed PASS at exit 0. A remote stylesheet linked from a local page is still not fetched and is still named in a note, whether its URL starts with `http://`, `https://` in any case, or `//`; the README lists this under Limitations.
- Durations written with capital units, `1500MS` or `2S`, are now graded. CSS units are case-insensitive, but only lowercase ones were read, so a sluggish transition in capitals passed unseen.

## [1.1.0](https://github.com/eliferres/website-bar/releases/tag/v1.1.0) - 2026-09-03

### Added
- Added a terminal demo to the README's first screen, showing website_bar.py failing the demo page on five rules, then passing the clean page across all four check families.
- Added a test for the color-count rule, the one craft_basics rule that had no test of its own.
- Added macos-latest to the CI matrix alongside ubuntu-latest.

### Changed
- Added type hints to the seven remaining functions in website_bar.py, matching the file's existing style.

## [1.0.0](https://github.com/eliferres/website-bar/releases/tag/v1.0.0) - 2026-08-31

First public release.
