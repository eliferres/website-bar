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
        if element.get("font-size"):
            continue  # the window title bar, the one row with its own size
        tspans = element.findall(f"{SVG}tspan")
        if tspans:
            rows.append(("cmd", tspans[-1].text or ""))
        elif element.get("class") == "cmd":
            raw = element.text or ""
            rows.append(("cmd-cont", raw[4:] if raw.startswith("    ") else raw))
        else:
            rows.append(("out", element.text or ""))
    return rows


def shows_whole(row, line):
    """A row is the output line itself, or that line cut once at the end."""
    if row == line:
        return True
    head = row[: -len(ELLIPSIS)]
    return (row.endswith(ELLIPSIS) and row.count(ELLIPSIS) == 1
            and len(head) < len(line) and line.startswith(head))


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
    """demo/terminal.svg holds whole commands with all of their output.

    The picture fits as many whole commands as it can, so it may stop before
    the last entry, but only between commands: nothing it shows may be
    invented, nothing an entry printed may be left out, and no row may sit
    out of order.
    """

    def test_the_picture_shows_whole_entries_in_order(self):
        entries = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
        rows = svg_rows()
        self.assertTrue(rows, "the picture has no session rows")
        index = 0
        for entry in entries:
            if index == len(rows):
                break  # the picture stopped at a command boundary
            kind, text = rows[index]
            self.assertEqual(kind, "cmd", f"row {index + 1} should open {entry['cmd']}")
            chunks = [text]
            index += 1
            while index < len(rows) and rows[index][0] == "cmd-cont":
                chunks.append(rows[index][1])
                index += 1
            self.assertEqual(rejoin(chunks), entry["cmd"],
                             "the command rows do not rebuild the recorded command")
            for line in [l for l in entry["out"].splitlines() if l.strip()]:
                self.assertLess(index, len(rows),
                                f"the picture stops inside {entry['cmd']}, before {line!r}")
                kind, text = rows[index]
                self.assertEqual(kind, "out", f"row {index + 1} should be output line {line!r}")
                self.assertTrue(
                    shows_whole(text, line),
                    f"row {index + 1} is {text!r}, expected {line!r} whole or end-trimmed "
                    "with one ellipsis")
                index += 1
        self.assertEqual(index, len(rows),
                         f"{len(rows) - index} drawn row(s) the transcript does not account for")

    def test_the_readme_shows_the_picture(self):
        self.assertIn('src="demo/terminal.svg"',
                      (REPO / "README.md").read_text(encoding="utf-8"))


def rejoin(chunks):
    """Undo the drawing's wrapping: a wrapped row ends in " \\" and the chunks
    rejoin with the one space the break ate."""
    return " ".join(c[:-2] if c.endswith(" \\") else c for c in chunks)


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
