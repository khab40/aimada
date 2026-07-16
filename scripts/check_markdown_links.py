#!/usr/bin/env python3
"""Check local Markdown links and GitHub-style heading anchors."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
HTML_ANCHOR_RE = re.compile(r"(?:id|name)=[\"']([^\"']+)[\"']", re.IGNORECASE)


def github_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[`*_~]", "", value).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value, flags=re.UNICODE)
    return re.sub(r"\s", "-", value)


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        found.update(HTML_ANCHOR_RE.findall(line))
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = github_slug(match.group(1))
        count = counts.get(base, 0)
        counts[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def markdown_files(inputs: list[Path]) -> list[Path]:
    result: set[Path] = set()
    for item in inputs:
        if item.is_file() and item.suffix.lower() == ".md":
            result.add(item.resolve())
        elif item.is_dir():
            result.update(path.resolve() for path in item.rglob("*.md"))
    return sorted(result)


def link_target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split(maxsplit=1)[0]


def validate(files: list[Path]) -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for source in files:
        fenced = False
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            for match in LINK_RE.finditer(line):
                if line[: match.start()].count("`") % 2 == 1:
                    continue
                target = link_target(match.group(1))
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("//"):
                    continue
                path_text = unquote(parsed.path)
                destination = (source.parent / path_text).resolve() if path_text else source
                if not destination.exists():
                    errors.append(f"{source}:{line_number}: missing link target {target}")
                    continue
                fragment = unquote(parsed.fragment)
                if fragment and destination.is_file() and destination.suffix.lower() == ".md":
                    available = anchor_cache.setdefault(destination, anchors(destination))
                    if fragment not in available:
                        errors.append(f"{source}:{line_number}: missing anchor #{fragment} in {destination}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    files = markdown_files(args.paths)
    errors = validate(files)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated {len(files)} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
