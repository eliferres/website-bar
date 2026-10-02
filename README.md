# website-bar

Design taste is usually argued in adjectives. website-bar grades it in numbers. Write a best-in-class standard's measurable habits into one JSON bar and every page you ship gets the same report: rule by rule, pass or fail, with the exact offending string and where it lives. No browser, no dependencies, exit codes for CI.

Point it at a URL or a local HTML file. Exit 0 clears the bar, exit 1
does not, and exit 2 means the run never happened: bad usage, a page
or a stylesheet it links that cannot be read or fetched, a bar file
that is missing, not valid JSON, or shaped so the checks cannot use it,
or a bug in website-bar itself. In CI, treat 2 as a broken job rather than a failing page.

![ci](https://github.com/eliferres/website-bar/actions/workflows/ci.yml/badge.svg)

<img src="demo/terminal.svg" width="660" alt="Terminal session showing website-bar grading the failing demo page: five failures across headline economy, motion durations and slop patterns, each with the offending string and its line, then the FAIL verdict.">

## Quick start

Install the command:

```bash
pipx install git+https://github.com/eliferres/website-bar
website-bar your-page.html --bar your-bar.json
```

The tool is not published to a package index; the line above installs it
straight from the repository.

Or clone it and run the demo pages, which is what the walkthrough below
does:

```bash
git clone https://github.com/eliferres/website-bar.git
cd website-bar
python3 website_bar.py demo/failing-page.html --bar config/example-bar.json
python3 website_bar.py demo/passing-page.html --bar config/example-bar.json
```

Zero dependencies, Python 3.9+, no network needed for the demo. The two
demo pages are the walkthrough below: one fails the example bar in five
named ways, one clears it.

The whole tool is `website_bar.py`, the worked bar with every option set
is `config/example-bar.json`, the two graded pages are in `demo/`, and
`tests/` runs the real CLI over `tests/fixtures/`, small pages with one
planted defect family each.

## A failing page, then a passing one

Run the failing page:

```bash
python3 website_bar.py demo/failing-page.html --bar config/example-bar.json
```

Five failures, each naming the string that caused it:

```text
website-bar report
bar: North Star example bar
target: demo/failing-page.html

headline economy: FAIL
  - h1 runs 9 words, ceiling is 7
      found: The complete all-in-one platform for every modern marketing team
      at:    demo/failing-page.html:35
  - h2 opens with the banned phrase "Unlock"
      found: Unlock your potential today
      at:    demo/failing-page.html:39

motion durations: FAIL
  - 1500ms is past the absolute ceiling of 700ms
      found: transition: transform 1500ms ease-in-out
      at:    demo/failing-page.html:30
  - the page animates but never honors prefers-reduced-motion
      at:    demo/failing-page.html

slop patterns: FAIL
  - 5 lines open with an emoji, allowance is 0
      found: 🚀 Fast setup with no configuration
      at:    demo/failing-page.html:46

craft basics: PASS

FAIL: 5 failure(s) across 4 check families (0 disabled in this bar)
```

Fix one of them - the overlong headline:

```bash
python3 - <<'PY'
from pathlib import Path
page = Path("demo/failing-page.html")
page.write_text(page.read_text().replace(
    "The complete all-in-one platform for every modern marketing team",
    "A platform for modern marketing teams"))
PY
python3 website_bar.py demo/failing-page.html --bar config/example-bar.json
```

Four failures left, and the headline economy rule now names only the
banned opener. Put the page back and run the clean one:

```bash
git checkout demo/failing-page.html
python3 website_bar.py demo/passing-page.html --bar config/example-bar.json
echo "exit: $?"
```

`PASS: 0 failure(s) across 4 check families`, exit 0.

For CI or a dashboard, add `--json`:

```bash
python3 website_bar.py demo/failing-page.html --bar config/example-bar.json --json
```

## Writing a bar

A bar is one JSON file. This is `config/example-bar.json` in full - the
numbers are illustrative, and replacing them with habits you measured on
the site you actually admire is the entire setup:

```json
{
  "bar": {
    "name": "North Star example bar",
    "note": "Illustrative numbers. Replace them with habits you measured on the site you actually want to be graded against."
  },
  "checks": {
    "headline_economy": {
      "enabled": true,
      "max_words": { "h1": 7, "h2": 10 },
      "banned_openers": ["Welcome to", "Unlock", "Elevate", "Discover", "Empower"],
      "require_sentence_case": true,
      "title_case_word_allowance": 1,
      "proper_nouns": ["North", "Star", "Monday", "Europe"]
    },
    "motion_durations": {
      "enabled": true,
      "min_ms": 150,
      "max_ms": 400,
      "hard_max_ms": 700,
      "require_reduced_motion": true
    },
    "slop_patterns": {
      "enabled": true,
      "phrases": [
        "in today's fast-paced world",
        "we are thrilled to announce",
        "delve into",
        "seamlessly integrate",
        "game-changing",
        "revolutionize",
        "unlock the power of",
        "take it to the next level",
        "cutting-edge solution",
        "at the end of the day"
      ],
      "max_emoji_bullets": 0
    },
    "craft_basics": {
      "enabled": true,
      "max_font_families": 2,
      "max_colors": 12,
      "require_alt_text": true,
      "require_viewport_meta": true
    }
  }
}
```

Every family carries its own `enabled` flag, so a bar can grade only the
rules you are ready to hold yourself to. Unknown family names are a hard
error rather than a silent no-op.

The file is checked against that shape when it loads, one setting at a
time, and the first thing it cannot use is refused with one line naming
the family and the setting, and exit 2. A setting name no family reads,
`enabld` for one, is refused the same way, so a typo cannot quietly turn
a check off. A bar with no family enabled at all is refused too: a run
that graded nothing is not a passing page. So is a headline economy or
craft basics family that is enabled with every rule left off, since each
of their rules is opt-in; motion durations and slop patterns grade on
defaults, so `enabled` alone is enough for them. The types are the ones shown above: `enabled` and the
`require_` flags hold true or false, `banned_openers`, `proper_nouns` and
`phrases` hold lists of strings, `max_words` maps a heading tag, `h1`
to `h6`, to a non-negative number and refuses any other key, and every remaining number is non-negative and small
enough to print in a verdict.

## The four check families

**Headline economy.** Word-count ceilings per heading level, banned
filler openers, and a sentence-case rule that flags title-cased headings
while ignoring acronyms and a configured proper-noun list. Long headings
are the most reliable single tell of copy nobody edited.

**Motion durations.** Every `transition` and `animation` duration in
inline styles, `<style>` blocks, linked stylesheets and the stylesheets
they pull in with `@import`, graded against a
floor and a ceiling: below the floor reads as jarring, above it as
sluggish, past the hard ceiling as broken. Shorthand delays are not
mistaken for durations. If the page animates at all, it owes a
`prefers-reduced-motion` rule.

**Slop patterns.** Configurable filler phrases matched against the
visible copy, each hit reported with its exact text and line, plus an
emoji-bullet counter for the design-side version of the same tell.

**Craft basics.** Distinct font stacks, distinct colors, image alt
coverage, and the viewport meta tag. Each individually toggleable,
because these are the checks teams most often want partially on.

## Why a config, not a linter with opinions

A style guide that lives in a document gets quoted in review and ignored
in a hurry. The same guide as numbers in a file gets run. The point is
not that seven words is the right ceiling for your h1 - it is that you
picked a page you admire, counted, and wrote the number down, so the next
argument is about the number and not about taste. Bars are diffable,
reviewable, and forkable per project: a marketing site and an internal
dashboard should not be graded by the same file.

Determinism is the other half. The same page and the same bar always
produce the same report, which is what makes this safe to put in CI next
to the tests.

## Limitations

- Static analysis only. Nothing is rendered and no JavaScript runs, so
  computed styles, CSS-in-JS, and motion injected at runtime are
  invisible. A page can pass here and still animate badly in a browser.
- A local page is graded offline, so a stylesheet it links or imports
  by an `http` or `https` URL, a CDN font sheet for one, is not fetched. The
  report names each one in a note; grade the deployed URL to include it.
- Font and color counts are approximate: they count declarations in the
  source, not what actually paints. Design tokens and unused rules both
  inflate them.
- The sentence-case rule is heuristic. Proper nouns outside the
  configured list read as title case, which is a false positive you fix
  by extending the list.
- Slop detection is exact-phrase matching. It catches the clichés you
  name and nothing else; it cannot judge whether a sentence is good.
- A bar encodes one team's taste and inherits its blind spots. Passing
  means "this page keeps the habits we wrote down," never "this page is
  well designed."

MIT licensed. See LICENSE.
