"""End-to-end tests: every case runs the real CLI over a real HTML file.

No network, no mocks. Each check family gets a fixture with planted
defects and is asserted on the exact string it reports back, because a
report that names the wrong string is worse than no report.
"""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(REPO))

import website_bar  # noqa: E402

EXAMPLE_BAR = REPO / "config" / "example-bar.json"


def run(target, bar=EXAMPLE_BAR, as_json=False):
    argv = [str(target), "--bar", str(bar)] + (["--json"] if as_json else [])
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = website_bar.main(argv)
    return code, out.getvalue() + err.getvalue()


def run_json(target, bar=EXAMPLE_BAR):
    code, output = run(target, bar, as_json=True)
    return code, json.loads(output)


def failures(payload, family):
    for result in payload["families"]:
        if result["family"] == family:
            return result["failures"]
    raise AssertionError(f"no such family: {family}")


def bar_with(tmpdir, **overrides):
    """The example bar with named check families replaced."""
    bar = json.loads(EXAMPLE_BAR.read_text(encoding="utf-8"))
    for family, config in overrides.items():
        bar["checks"][family] = config
    path = Path(tmpdir) / "bar.json"
    path.write_text(json.dumps(bar), encoding="utf-8")
    return path


class DemoPages(unittest.TestCase):
    def test_passing_page_clears_the_bar(self):
        code, output = run(REPO / "demo" / "passing-page.html")
        self.assertEqual(code, 0, output)
        self.assertIn("PASS: 0 failure(s)", output)

    def test_failing_page_reports_its_five_planted_defects(self):
        code, payload = run_json(REPO / "demo" / "failing-page.html")
        self.assertEqual(code, 1)
        rules = sorted(f["rule"] for r in payload["families"] for f in r["failures"])
        self.assertEqual(rules, [
            "banned-opener", "duration-bounds", "emoji-bullets",
            "h1-word-ceiling", "reduced-motion",
        ])


class HeadlineEconomy(unittest.TestCase):
    def test_word_ceiling_quotes_the_offending_heading(self):
        _, payload = run_json(FIXTURES / "headings.html")
        hit = next(f for f in failures(payload, "headline_economy")
                   if f["rule"] == "h1-word-ceiling")
        self.assertEqual(hit["evidence"],
                         "this headline keeps going well past any sensible ceiling")
        self.assertIn("9 words, ceiling is 7", hit["message"])
        self.assertTrue(hit["location"].endswith("headings.html:5"))

    def test_banned_opener_names_the_phrase(self):
        _, payload = run_json(FIXTURES / "headings.html")
        hit = next(f for f in failures(payload, "headline_economy")
                   if f["rule"] == "banned-opener")
        self.assertIn('"Discover"', hit["message"])
        self.assertEqual(hit["evidence"], "Discover the shorter way")

    def test_title_case_heading_is_flagged_with_its_words(self):
        _, payload = run_json(FIXTURES / "headings.html")
        hit = next(f for f in failures(payload, "headline_economy")
                   if f["rule"] == "sentence-case")
        self.assertIn("For", hit["message"])
        self.assertIn("Modern", hit["message"])


class MotionDurations(unittest.TestCase):
    def test_linked_stylesheet_durations_are_graded_and_located(self):
        _, payload = run_json(FIXTURES / "motion-linked.html")
        hits = [f for f in failures(payload, "motion_durations")
                if f["rule"] == "duration-bounds"]
        messages = " | ".join(h["message"] for h in hits)
        self.assertIn("1500ms is past the absolute ceiling", messages)
        self.assertIn("80ms is jarring", messages)
        self.assertIn("900ms is past the absolute ceiling", messages)
        self.assertTrue(all(h["location"].startswith("motion.css:") for h in hits))

    def test_transition_delay_is_not_read_as_a_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "delay.html"
            page.write_text(
                "<html><head><style>@media (prefers-reduced-motion: reduce)"
                "{ * { transition: none; } }\n.a { transition: opacity 200ms 1200ms ease; }"
                "</style></head><body><h1>Delay is not duration</h1></body></html>",
                encoding="utf-8")
            _, payload = run_json(page)
        self.assertEqual(failures(payload, "motion_durations"), [])

    def test_reduced_motion_is_only_owed_when_the_page_animates(self):
        _, payload = run_json(FIXTURES / "static.html")
        self.assertEqual(failures(payload, "motion_durations"), [])

    def test_animating_page_without_reduced_motion_fails(self):
        _, payload = run_json(FIXTURES / "motion-linked.html")
        self.assertTrue(any(f["rule"] == "reduced-motion"
                            for f in failures(payload, "motion_durations")))


class SlopPatterns(unittest.TestCase):
    def test_filler_phrase_is_reported_with_its_exact_text(self):
        _, payload = run_json(FIXTURES / "slop.html")
        hit = next(f for f in failures(payload, "slop_patterns")
                   if f["rule"] == "filler-phrase")
        self.assertEqual(hit["evidence"].lower(), "in today's fast-paced world")
        self.assertTrue(hit["location"].endswith("slop.html:10"))

    def test_emoji_bullets_are_counted_against_the_allowance(self):
        _, payload = run_json(FIXTURES / "slop.html")
        hit = next(f for f in failures(payload, "slop_patterns")
                   if f["rule"] == "emoji-bullets")
        self.assertIn("3 lines open with an emoji", hit["message"])


class CraftBasics(unittest.TestCase):
    def test_missing_alt_viewport_and_font_ceiling_all_fire(self):
        _, payload = run_json(FIXTURES / "craft.html")
        hits = {f["rule"]: f for f in failures(payload, "craft_basics")}
        self.assertEqual(sorted(hits), ["font-family-count", "image-alt", "viewport-meta"])
        self.assertEqual(hits["image-alt"]["evidence"], "chart.png")
        self.assertIn("3 font stacks declared", hits["font-family-count"]["message"])

    def test_color_count_ceiling_fires(self):
        # The example bar's max_colors is 12; craft.html stays under it, so
        # color-count has never actually fired in this suite.
        colors = ", ".join(f"#{n:06x}" for n in range(0x111111, 0x111111 + 13 * 0x010101, 0x010101))
        page = f"""<html><head><meta name="viewport" content="width=device-width">
<style>.swatches {{ color: {colors.split(', ')[0]}; }}
{"".join(f'.c{i} {{ color: {c}; }}' for i, c in enumerate(colors.split(', ')))}
</style></head><body><img src="a.png" alt="a"></body></html>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "colors.html"
            path.write_text(page, encoding="utf-8")
            _, payload = run_json(path)
        hit = next(f for f in failures(payload, "craft_basics")
                   if f["rule"] == "color-count")
        self.assertIn("13 distinct colors, ceiling is 12", hit["message"])


class ConfigAndOutput(unittest.TestCase):
    def test_disabling_a_family_skips_it_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            bar = bar_with(tmp, craft_basics={"enabled": False})
            code, payload = run_json(FIXTURES / "craft.html", bar)
        self.assertEqual(failures(payload, "craft_basics"), [])
        self.assertEqual(code, 0)

    def test_raising_a_ceiling_lets_the_same_page_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            bar = bar_with(tmp, headline_economy={
                "enabled": True, "max_words": {"h1": 20}, "banned_openers": []})
            _, payload = run_json(FIXTURES / "headings.html", bar)
        self.assertEqual(failures(payload, "headline_economy"), [])

    def test_json_shape_is_stable(self):
        _, payload = run_json(REPO / "demo" / "failing-page.html")
        self.assertEqual(sorted(payload),
                         ["bar", "families", "notes", "passed", "summary", "target"])
        self.assertEqual(payload["bar"], "North Star example bar")
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["summary"], {"failures": 5, "families_checked": 4})
        for result in payload["families"]:
            self.assertEqual(sorted(result), ["failures", "family", "status"])
            for failure in result["failures"]:
                self.assertEqual(sorted(failure),
                                 ["evidence", "location", "message", "rule"])

    def test_missing_page_exits_two_without_a_traceback(self):
        code, output = run(FIXTURES / "nope.html")
        self.assertEqual(code, 2)
        self.assertIn("no such page", output)

    def test_malformed_bar_exits_two_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            bar = Path(tmp) / "broken-bar.json"
            bar.write_text('{"checks": ', encoding="utf-8")
            code, output = run(REPO / "demo" / "passing-page.html", bar)
        self.assertEqual(code, 2)
        self.assertTrue(output.startswith("website-bar: "), output)

    def test_bar_with_a_null_checks_value_exits_two(self):
        code, output = self.refuse('{"checks": null}')
        self.assertEqual(code, 2)
        self.assertIn('"checks" is not a JSON object', output)

    def test_family_settings_that_are_not_an_object_exit_two(self):
        code, output = self.refuse('{"checks": {"craft_basics": "yes"}}')
        self.assertEqual(code, 2)
        self.assertIn('check family "craft_basics" is not a JSON object', output)

    def test_settings_the_checks_cannot_use_exit_two(self):
        # The shape is right, so only the checks themselves can catch this.
        code, output = self.refuse(
            '{"checks": {"headline_economy": {"enabled": true, "max_words": 7}}}')
        self.assertEqual(code, 2)
        self.assertTrue(output.startswith("website-bar: "), output)

    def test_a_bar_key_that_is_not_an_object_exits_two(self):
        # The name is read after grading, outside every guard, so a "bar"
        # of the wrong type used to surface as a traceback at the end.
        for value in ("null", '"strict"', '["x"]'):
            with self.subTest(value=value):
                code, output = self.refuse(
                    '{"bar": %s, "checks": {"craft_basics": {"enabled": true}}}' % value)
                self.assertEqual(code, 2, output)
                self.assertIn('the bar\'s "bar" is not a JSON object', output)
                self.assertEqual(len(output.strip().splitlines()), 1, output)
                self.assertNotIn("Traceback", output)

    def test_a_bar_with_no_checks_key_exits_two(self):
        for text in ('{"bar": {"name": "empty"}}',
                     '{"bar": {"name": "typo"}, "Checks": {"craft_basics": {"enabled": true}}}'):
            with self.subTest(text=text):
                code, output = self.refuse(text)
                self.assertEqual(code, 2, output)
                self.assertIn('has no "checks" to grade with', output)

    def refuse(self, text):
        """Grade the clean demo page with a bar file holding this text."""
        with tempfile.TemporaryDirectory() as tmp:
            bar = Path(tmp) / "bar.json"
            bar.write_text(text, encoding="utf-8")
            return run(REPO / "demo" / "passing-page.html", bar)

    def test_bar_that_is_not_an_object_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            bar = Path(tmp) / "list-bar.json"
            bar.write_text("[]", encoding="utf-8")
            code, output = run(REPO / "demo" / "passing-page.html", bar)
        self.assertEqual(code, 2)
        self.assertIn("bar file is not a JSON object", output)


class InternalFaults(unittest.TestCase):
    """A fault in the tool must never be mistaken for a graded failure."""

    def test_an_unexpected_exception_exits_two_and_says_it_is_a_bug(self):
        def boom(*args, **kwargs):
            raise RuntimeError("planted fault")

        original = website_bar.grade
        website_bar.grade = boom
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = website_bar.main([
                    str(REPO / "demo" / "passing-page.html"), "--bar", str(EXAMPLE_BAR)])
        finally:
            website_bar.grade = original
        message = err.getvalue()
        self.assertEqual(code, 2, message)
        self.assertEqual(len(message.strip().splitlines()), 1, message)
        self.assertIn("bug in website-bar", message)
        self.assertIn("RuntimeError: planted fault", message)
        self.assertNotIn("Traceback", message)


class VersionFlag(unittest.TestCase):
    def test_version_prints_the_command_name_and_version(self):
        # Written out rather than read from the module, so a version
        # string that drifts from the last release fails here.
        result = subprocess.run(
            [sys.executable, str(REPO / "website_bar.py"), "--version"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "website-bar 1.1.0\n")
        self.assertEqual(result.stderr, "")


class ProcessExitCodes(unittest.TestCase):
    """The codes CI reads, taken from a real process rather than main().

    The CI job gates on the failing demo page exiting exactly 1. Nothing
    else exits 1: every refusal exits 2, and so does an unexpected
    exception, so the three codes are asserted here together.
    """

    def grade(self, target, bar=EXAMPLE_BAR):
        result = subprocess.run(
            [sys.executable, str(REPO / "website_bar.py"), str(target), "--bar", str(bar)],
            cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return result.returncode, result.stdout

    def test_the_demo_pages_exit_zero_and_one(self):
        self.assertEqual(self.grade(REPO / "demo" / "passing-page.html")[0], 0)
        self.assertEqual(self.grade(REPO / "demo" / "failing-page.html")[0], 1)

    def test_an_unusable_bar_exits_two_rather_than_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            bar = Path(tmp) / "bar.json"
            bar.write_text('{"checks": {"craft_basics": "yes"}}', encoding="utf-8")
            code, output = self.grade(REPO / "demo" / "failing-page.html", bar)
        self.assertEqual(code, 2, output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
