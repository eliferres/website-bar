# Contributing

Welcome things:

- New checks, if the rule is measurable from HTML/CSS source and every
  threshold lives in the bar config rather than the code.
- Parser fixes: real-world markup that the checks read wrong.
- Fixes to anything the README claims that turns out not to be true.
- Example bars for a domain (docs site, dashboard, landing page), as a
  file in `config/`, with a line saying what was measured.

Ground rules: `website_bar.py` stays stdlib-only and single-file, every
check ships a fixture with a planted defect, and the assertion is on the
exact string the report gives back. Keep
`python3 -m unittest discover -s tests` green. Taste arguments belong in
an issue about a number in a config, not in the checker.
