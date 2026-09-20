"""Select exactly one version section from the cumulative changelog."""

import argparse
import re
from pathlib import Path


def release_notes(text: str, version: str) -> str:
    headings = list(re.finditer(r"^## (.+)$", text, re.MULTILINE))
    matches = [
        i
        for i, heading in enumerate(headings)
        if re.match(rf"{re.escape(version)}(?:\s|$)", heading.group(1))
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one release section for {version}")
    index = matches[0]
    heading = headings[index]
    end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
    if not text[heading.end() : end].strip():
        raise ValueError(f"Release section for {version} is empty")
    return text[heading.start() : end].strip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source", type=Path, default=Path("RELEASE_NOTES.md"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(release_notes(args.source.read_text(), args.version))


if __name__ == "__main__":
    main()
