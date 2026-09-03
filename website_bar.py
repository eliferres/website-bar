#!/usr/bin/env python3
"""Grade a web page against a named craft bar defined in config.

Design taste is usually argued in adjectives. This grades it in numbers:
you name a best-in-class standard, write its measurable habits into a
JSON bar, and every page gets the same deterministic report - per rule,
pass or fail, with the exact offending string and where it lives.

Four check families: headline economy, motion durations, slop patterns,
craft basics. Each is individually toggleable in the bar config.

Stdlib only. Exit 0 when the page clears the bar, 1 when it does not.

Usage:
    python3 website_bar.py <url-or-file> --bar config/example-bar.json [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path

FAMILY_ORDER = ("headline_economy", "motion_durations", "slop_patterns", "craft_basics")
FAMILY_TITLES = {
    "headline_economy": "headline economy",
    "motion_durations": "motion durations",
    "slop_patterns": "slop patterns",
    "craft_basics": "craft basics",
}

CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
DECLARATION = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+)")
TIME_VALUE = re.compile(r"(-?\d*\.?\d+)(ms|s)\b")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FUNC_COLOR = re.compile(r"\b(?:rgba?|hsla?)\([^)]*\)")
# The blocks people actually reach for as bullet glyphs: pictographs,
# dingbats, misc symbols, arrows, and the variation selector.
EMOJI = re.compile(
    "[\U0001f300-\U0001faff☀-➿⬀-⯿←-⇿️]"
)
ACRONYM = re.compile(r"^[A-Z0-9&/.-]+$")


class Finding:
    """One rule violation, carrying the evidence that proves it."""

    def __init__(
        self, rule: str, message: str, evidence: str = "", location: str = ""
    ) -> None:
        self.rule = rule
        self.message = message
        self.evidence = evidence
        self.location = location

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "message": self.message,
            "evidence": self.evidence,
            "location": self.location,
        }


class Page(HTMLParser):
    """Everything the checks need, collected in one pass over the source.

    Line numbers come from the parser itself so every finding can point at
    the source line rather than making the reader search for the string.
    """

    def __init__(self, label: str) -> None:
        super().__init__(convert_charrefs=True)
        self.label = label
        self.headings: list[tuple[int, str, int]] = []
        self.inline_styles: list[tuple[str, str, int]] = []
        self.style_blocks: list[tuple[str, int]] = []
        self.stylesheet_hrefs: list[str] = []
        self.images: list[tuple[str, str | None, int]] = []
        self.has_viewport = False
        self.text_chunks: list[tuple[str, int]] = []
        self._heading_level = 0
        self._heading_text: list[str] = []
        self._heading_line = 0
        self._in_style = False
        self._in_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        line = self.getpos()[0]
        if "style" in attr and attr["style"].strip():
            self.inline_styles.append((attr["style"], f"<{tag} style>", line))
        if tag == "style":
            self._in_style = True
        elif tag == "script":
            self._in_script = True
        elif tag == "link" and "stylesheet" in attr.get("rel", "").lower():
            if attr.get("href"):
                self.stylesheet_hrefs.append(attr["href"])
        elif tag == "img":
            self.images.append((attr.get("src", ""), attr.get("alt"), line))
        elif tag == "meta" and attr.get("name", "").lower() == "viewport":
            self.has_viewport = True
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = int(tag[1])
            self._heading_text = []
            self._heading_line = line

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False
        elif tag == "script":
            self._in_script = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading_level:
            text = " ".join("".join(self._heading_text).split())
            if text:
                self.headings.append((self._heading_level, text, self._heading_line))
            self._heading_level = 0

    def handle_data(self, data: str) -> None:
        line = self.getpos()[0]
        if self._in_style:
            self.style_blocks.append((data, line))
            return
        if self._in_script:
            return
        if self._heading_level:
            self._heading_text.append(data)
        for offset, raw in enumerate(data.splitlines()):
            text = raw.strip()
            if text:
                self.text_chunks.append((text, line + offset))

    def at(self, line: int) -> str:
        return f"{self.label}:{line}"


class Source:
    """A stylesheet or inline block, with a label for locating findings."""

    def __init__(self, text: str, label: str, line_offset: int = 0) -> None:
        self.text = CSS_COMMENT.sub("", text)
        self.label = label
        self.line_offset = line_offset

    def at(self, index: int) -> str:
        return f"{self.label}:{self.line_offset + self.text[:index].count(chr(10))}"


def read_target(target: str, timeout: float) -> tuple[str, str, str]:
    """Return (html, base, label) for a URL or a local path."""
    if re.match(r"^https?://", target):
        with urllib.request.urlopen(target, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, "replace"), target, target
    path = Path(target)
    if not path.is_file():
        raise FileNotFoundError(f"no such page: {target}")
    return path.read_text(encoding="utf-8", errors="replace"), str(path), str(path)


def collect_css(page: Page, base: str, timeout: float) -> tuple[list[Source], list[str]]:
    """Gather inline styles, <style> blocks, and linked stylesheets.

    Unreadable stylesheets are reported rather than swallowed: a bar that
    silently skips a file would grade the page on a fraction of its CSS.
    """
    sources = [Source(css, f"{page.label} {where}", line) for css, where, line in page.inline_styles]
    sources += [Source(css, page.label, line) for css, line in page.style_blocks]
    notes = []
    for href in page.stylesheet_hrefs:
        try:
            sources.append(Source(read_stylesheet(href, base, timeout), href, 1))
        except (OSError, ValueError, urllib.error.URLError) as err:
            notes.append(f"stylesheet not read: {href} ({err})")
    return sources, notes


def read_stylesheet(href: str, base: str, timeout: float) -> str:
    if re.match(r"^https?://", base):
        url = urllib.parse.urljoin(base, href)
        with urllib.request.urlopen(url, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, "replace")
    if re.match(r"^https?://", href):
        raise ValueError("remote stylesheet on a local page")
    return (Path(base).parent / href).read_text(encoding="utf-8", errors="replace")


def declarations(
    sources: list[Source], names: tuple[str, ...]
) -> Iterator[tuple[Source, str, str, int]]:
    """Yield (source, property, value, index) for the properties asked for."""
    for source in sources:
        for match in DECLARATION.finditer(source.text):
            prop = match.group(1).lower()
            if prop in names:
                yield source, prop, match.group(2).strip(), match.start()


def durations_ms(prop: str, value: str) -> list[float]:
    """Times a browser would treat as durations, in milliseconds.

    In the `transition` and `animation` shorthands the first time value is
    the duration and the second is the delay, so only the first counts.
    """
    found = []
    for segment in value.split(","):
        times = TIME_VALUE.findall(segment)
        if prop.endswith("-duration"):
            found.extend(times)
        elif times:
            found.append(times[0])
    return [float(number) * (1.0 if unit == "ms" else 1000.0) for number, unit in found]


def check_headline_economy(page: Page, config: dict) -> list[Finding]:
    ceilings = {k.lower(): v for k, v in config.get("max_words", {}).items()}
    openers = config.get("banned_openers", [])
    proper = {w.lower() for w in config.get("proper_nouns", [])}
    findings = []
    for level, text, line in page.headings:
        tag = f"h{level}"
        words = text.split()
        ceiling = ceilings.get(tag)
        if ceiling is not None and len(words) > ceiling:
            findings.append(Finding(
                f"{tag}-word-ceiling",
                f"{tag} runs {len(words)} words, ceiling is {ceiling}",
                text, page.at(line)))
        for opener in openers:
            if text.lower().startswith(opener.lower()):
                findings.append(Finding(
                    "banned-opener",
                    f"{tag} opens with the banned phrase \"{opener}\"",
                    text, page.at(line)))
        if config.get("require_sentence_case"):
            shouty = [
                w for w in words[1:]
                if w[:1].isupper() and not ACRONYM.match(w)
                and w.strip(".,:;!?").lower() not in proper
            ]
            if len(shouty) >= config.get("title_case_word_allowance", 1) + 1:
                findings.append(Finding(
                    "sentence-case",
                    f"{tag} reads as title case ({', '.join(shouty)})",
                    text, page.at(line)))
    return findings


def check_motion_durations(page: Page, sources: list[Source], config: dict) -> list[Finding]:
    low = config.get("min_ms", 0)
    high = config.get("max_ms", 10_000)
    ceiling = config.get("hard_max_ms", high)
    findings = []
    motion_seen = False
    props = ("transition", "transition-duration", "animation", "animation-duration")
    for source, prop, value, index in declarations(sources, props):
        for ms in durations_ms(prop, value):
            motion_seen = True
            if ms == 0:
                continue
            if ms > ceiling:
                verdict = f"{ms:g}ms is past the absolute ceiling of {ceiling:g}ms"
            elif ms > high:
                verdict = f"{ms:g}ms is sluggish, bar tops out at {high:g}ms"
            elif ms < low:
                verdict = f"{ms:g}ms is jarring, bar starts at {low:g}ms"
            else:
                continue
            findings.append(Finding(
                "duration-bounds", verdict,
                f"{prop}: {value}", source.at(index)))
    if motion_seen and config.get("require_reduced_motion"):
        if not any("prefers-reduced-motion" in s.text for s in sources):
            findings.append(Finding(
                "reduced-motion",
                "the page animates but never honors prefers-reduced-motion",
                "", page.label))
    return findings


def check_slop_patterns(page: Page, config: dict) -> list[Finding]:
    findings = []
    for phrase in config.get("phrases", []):
        pattern = re.compile(re.escape(phrase), re.I)
        for text, line in page.text_chunks:
            match = pattern.search(text)
            if match:
                findings.append(Finding(
                    "filler-phrase",
                    f"copy leans on the filler phrase \"{phrase}\"",
                    match.group(0), page.at(line)))
    allowance = config.get("max_emoji_bullets", 0)
    bullets = [(t, line) for t, line in page.text_chunks if EMOJI.match(t)]
    if len(bullets) > allowance:
        first, line = bullets[0]
        findings.append(Finding(
            "emoji-bullets",
            f"{len(bullets)} lines open with an emoji, allowance is {allowance}",
            first, page.at(line)))
    return findings


def check_craft_basics(page: Page, sources: list[Source], config: dict) -> list[Finding]:
    findings = []
    max_fonts = config.get("max_font_families")
    if max_fonts is not None:
        stacks = {
            " ".join(value.replace('"', "").replace("'", "").lower().split())
            for _, _, value, _ in declarations(sources, ("font-family",))
        }
        if len(stacks) > max_fonts:
            findings.append(Finding(
                "font-family-count",
                f"{len(stacks)} font stacks declared, ceiling is {max_fonts}",
                "; ".join(sorted(stacks)), page.label))
    max_colors = config.get("max_colors")
    if max_colors is not None:
        colors = set()
        for source in sources:
            colors |= {normalize_hex(c) for c in HEX_COLOR.findall(source.text)}
            colors |= {" ".join(c.lower().split()) for c in FUNC_COLOR.findall(source.text)}
        if len(colors) > max_colors:
            findings.append(Finding(
                "color-count",
                f"{len(colors)} distinct colors, ceiling is {max_colors}",
                ", ".join(sorted(colors)), page.label))
    if config.get("require_alt_text"):
        for src, alt, line in page.images:
            if not (alt or "").strip():
                findings.append(Finding(
                    "image-alt",
                    "image carries no alt text",
                    src or "(no src)", page.at(line)))
    if config.get("require_viewport_meta") and not page.has_viewport:
        findings.append(Finding(
            "viewport-meta",
            "no viewport meta tag, so the page cannot be trusted on mobile",
            "", page.label))
    return findings


def normalize_hex(value: str) -> str:
    body = value[1:].lower()
    if len(body) in (3, 4):
        body = "".join(c * 2 for c in body)
    return "#" + body


def grade(page: Page, sources: list[Source], bar: dict) -> list[dict]:
    checks = bar.get("checks", {})
    results = []
    for family in FAMILY_ORDER:
        config = checks.get(family, {})
        if not config.get("enabled", False):
            results.append({"family": family, "status": "skipped", "failures": []})
            continue
        if family == "headline_economy":
            findings = check_headline_economy(page, config)
        elif family == "motion_durations":
            findings = check_motion_durations(page, sources, config)
        elif family == "slop_patterns":
            findings = check_slop_patterns(page, config)
        else:
            findings = check_craft_basics(page, sources, config)
        results.append({
            "family": family,
            "status": "fail" if findings else "pass",
            "failures": [f.as_dict() for f in findings],
        })
    return results


def report(results: list[dict], bar_name: str, target: str, notes: list[str]) -> str:
    failures = sum(len(r["failures"]) for r in results)
    lines = ["website-bar report", f"bar: {bar_name}", f"target: {target}", ""]
    for result in results:
        title = FAMILY_TITLES[result["family"]]
        lines.append(f"{title}: {result['status'].upper()}")
        for failure in result["failures"]:
            lines.append(f"  - {failure['message']}")
            if failure["evidence"]:
                lines.append(f"      found: {failure['evidence']}")
            if failure["location"]:
                lines.append(f"      at:    {failure['location']}")
        lines.append("")
    for note in notes:
        lines.append(f"note: {note}")
    if notes:
        lines.append("")
    checked = sum(1 for r in results if r["status"] != "skipped")
    skipped = len(results) - checked
    verdict = "FAIL" if failures else "PASS"
    lines.append(
        f"{verdict}: {failures} failure(s) across {checked} check families"
        f" ({skipped} disabled in this bar)"
    )
    return "\n".join(lines)


def load_bar(path: Path) -> dict:
    bar = json.loads(path.read_text(encoding="utf-8"))
    unknown = set(bar.get("checks", {})) - set(FAMILY_ORDER)
    if unknown:
        raise ValueError(f"unknown check families in bar: {', '.join(sorted(unknown))}")
    return bar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Grade a page against a named craft bar.")
    parser.add_argument("target", help="URL or path to an HTML file")
    parser.add_argument("--bar", required=True, help="path to a bar config JSON file")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    parser.add_argument("--timeout", type=float, default=10.0, help="network timeout, seconds")
    args = parser.parse_args(argv)

    try:
        bar = load_bar(Path(args.bar))
        html, base, label = read_target(args.target, args.timeout)
    except (OSError, ValueError, urllib.error.URLError) as err:
        print(f"website-bar: {err}", file=sys.stderr)
        return 2

    page = Page(label)
    page.feed(html)
    page.close()
    sources, notes = collect_css(page, base, args.timeout)
    results = grade(page, sources, bar)
    bar_name = bar.get("bar", {}).get("name", Path(args.bar).stem)
    failures = sum(len(r["failures"]) for r in results)

    if args.json:
        print(json.dumps({
            "bar": bar_name,
            "target": label,
            "passed": failures == 0,
            "families": results,
            "notes": notes,
            "summary": {
                "failures": failures,
                "families_checked": sum(1 for r in results if r["status"] != "skipped"),
            },
        }, indent=2))
    else:
        print(report(results, bar_name, label, notes))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
