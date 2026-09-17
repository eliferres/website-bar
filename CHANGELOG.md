# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- website-bar installs as a command: `pipx install git+https://github.com/eliferres/website-bar` puts `website-bar` on your PATH, and `website-bar --version` prints the version.

### Changed
- Reorganized the README: the walkthrough, the bar format and the check families sit under plainer headings, the file table is one sentence under Quick start, and the license line closes the file.

### Fixed
- The demo transcript and the terminal picture showed an abridged report: the header lines, the offending strings and their line numbers were all missing. Both now come from a real run, and a new test replays every recorded command and fails if a single character drifts.
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
