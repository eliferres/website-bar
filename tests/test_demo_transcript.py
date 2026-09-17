"""The demo receipt: demo/transcript.json is replayed, not typed.

Every entry is run with bash in a throwaway copy of the repository and
its combined output and exit code must match the recorded ones exactly,
so the session in demo/terminal.svg cannot drift from what the tool
really prints. Set UPDATE_DEMO_TRANSCRIPT=1 to rewrite the transcript
from a real run; never hand-edit the JSON.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRANSCRIPT = REPO / "demo" / "transcript.json"
PICTURE = REPO / "demo" / "terminal.svg"
CHECKOUT_PLACEHOLDER = "/path/to/checkout"
ELLIPSIS = "…"
SVG = "{http://www.w3.org/2000/svg}"
FIRST_ROW_Y = 80  # rows above this are the window chrome, not session text

SKIP = shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "build", "dist")


def run_in(copy, cmd):
    """Run one transcript command line and return (output, status)."""
    result = subprocess.run(
        ["bash", "-c", cmd], cwd=copy, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True)
    return normalize(result.stdout.rstrip("\n"), copy), result.returncode


def normalize(text, copy):
    """Replace the throwaway copy's path, given and resolved, with a placeholder."""
    for path in (str(Path(copy).resolve()), str(copy)):
        text = text.replace(path, CHECKOUT_PLACEHOLDER)
    return text


def replay():
    """Run every entry in order in one copy of the repository."""
    entries = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "website-bar"
        shutil.copytree(REPO, copy, ignore=SKIP)
        return entries, [run_in(copy, entry["cmd"]) for entry in entries]


def svg_rows():
    """The session rows of the picture, in order, as (kind, text)."""
    rows = []
    for element in ET.parse(PICTURE).getroot().findall(f"{SVG}text"):
        y = element.get("y")
        if y is None or int(y) < FIRST_ROW_Y:
            continue
        tspans = element.findall(f"{SVG}tspan")
        if tspans:
            rows.append(("cmd", tspans[-1].text or ""))
        elif element.get("class") == "cmd":
            raw = element.text or ""
            rows.append(("cmd-cont", raw[4:] if raw.startswith("    ") else raw))
        else:
            rows.append(("out", element.text or ""))
    return rows


def untrimmed(row):
    """A picture row with its one trailing ellipsis removed."""
    return row[: -len(ELLIPSIS)] if row.endswith(ELLIPSIS) else row


class TranscriptReplay(unittest.TestCase):
    def test_every_entry_matches_a_real_run(self):
        entries, results = replay()
        for entry, (output, status) in zip(entries, results):
            with self.subTest(cmd=entry["cmd"]):
                self.assertEqual(
                    output, entry["out"],
                    f"{entry['cmd']}\nexpected:\n{entry['out']}\nactual:\n{output}")
                self.assertEqual(
                    status, entry["status"],
                    f"{entry['cmd']}: expected exit {entry['status']}, got {status}")


class Picture(unittest.TestCase):
    """Every row drawn in demo/terminal.svg traces back to the transcript.

    The picture holds as many rows as it fits, so it may stop part way
    through the session; nothing it does show may be invented.
    """

    def test_every_row_traces_back_to_the_transcript(self):
        entries = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
        rows = svg_rows()
        index, chunks, out_lines = -1, [], []
        for kind, text in rows:
            if kind == "cmd":
                index += 1
                self.assertLess(index, len(entries), f"extra command row: {text}")
                chunks = [text]
                out_lines = [l for l in entries[index]["out"].splitlines() if l.strip()]
                self.assertTrue(rebuild(chunks, entries[index]["cmd"]), text)
            elif kind == "cmd-cont":
                chunks.append(text)
                self.assertTrue(rebuild(chunks, entries[index]["cmd"]),
                                " ".join(chunks))
            else:
                self.assertTrue(out_lines, f"output row with no line left: {text}")
                line = out_lines.pop(0)
                self.assertTrue(
                    line.startswith(untrimmed(text)),
                    f"picture row {text!r} is not a prefix of output line {line!r}")

    def test_the_readme_shows_the_picture(self):
        self.assertIn('src="demo/terminal.svg"',
                      (REPO / "README.md").read_text(encoding="utf-8"))


def rebuild(chunks, cmd):
    """True when the wrapped command rows so far rebuild the start of cmd."""
    joined = " ".join(c[:-2] if c.endswith(" \\") else c for c in chunks)
    return cmd.startswith(joined)


def regenerate():
    entries, results = replay()
    for entry, (output, status) in zip(entries, results):
        entry["out"], entry["status"] = output, status
    TRANSCRIPT.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"rewrote {TRANSCRIPT} from a real run")


if __name__ == "__main__":
    if os.environ.get("UPDATE_DEMO_TRANSCRIPT") == "1":
        regenerate()
    else:
        unittest.main()
