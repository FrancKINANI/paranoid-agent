#!/usr/bin/env python3
"""Verify the documentation set: link resolution, code fences, and risky claims.

Run from the repository root:  python3 scripts/check_docs.py
Exit code 0 = all structural checks pass, 1 = at least one failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$")
# Phrases that must never appear unqualified. Each is allowed only if the same
# line contains one of the hedge words.
RISKY = [
    "anonymous",
    "untraceable",
    "unlinkable",
    "guarantee",
    "proven",
    "fully private",
    "cannot be traced",
]
HEDGES = (
    "not", "no ", "never", "unless", "cannot", "qualified", "partial", "weaker",
    "claim", "unproven", "would", "does not", "isn't", "cannot be", "advisory",
    "reduce", "reduces", "reduced", "we do not", "never claimed", "if ", "scope",
)


def slugify(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"`|\*|_|\[|\]|\(|\)|:|\?|\.|,|'|\"|/", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def headings_of(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {slugify(m.group(1)) for m in (HEADING_RE.match(l) for l in text.splitlines()) if m}


def check_claims(rel: Path, lines: list[str]) -> list[str]:
    """Flag phrases that must never appear unqualified.

    Scans by paragraph, not by line, so a hedge on the next line still counts —
    otherwise the checker cries wolf on ordinary wrapping. Headings and fenced
    code are skipped: a heading is a label, not an assertion.
    """
    out: list[str] = []
    in_fence = False
    block: list[str] = []
    start = 0

    def flush(start_line: int, body: list[str]) -> None:
        if not body:
            return
        joined = " ".join(body).lower()
        for phrase in RISKY:
            if phrase in joined and not any(h in joined for h in HEDGES):
                snippet = " ".join(body)[:100]
                out.append(f"{rel}:{start_line}: unhedged '{phrase}': {snippet}")

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            flush(start, block)
            block, start = [], lineno + 1
            continue
        if in_fence or stripped.startswith("#"):
            continue
        if not stripped:
            flush(start, block)
            block, start = [], lineno + 1
            continue
        if not block:
            start = lineno
        block.append(stripped)
    flush(start, block)
    return out


def main() -> int:
    docs = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").glob("*.md"))
    failures: list[str] = []
    warnings: list[str] = []

    for doc in docs:
        rel = doc.relative_to(ROOT)
        text = doc.read_text(encoding="utf-8")
        lines = text.splitlines()

        # 1. Code fences must be balanced.
        fences = sum(1 for l in lines if l.startswith("```"))
        if fences % 2:
            failures.append(f"{rel}: unbalanced code fences ({fences} fence lines)")

        # 2. Relative links must resolve; #fragments must exist as headings.
        for lineno, line in enumerate(lines, 1):
            for match in LINK_RE.finditer(line):
                target = match.group(2)
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part, _, fragment = target.partition("#")
                if not path_part:  # same-file anchor
                    resolved = doc
                else:
                    resolved = (doc.parent / path_part).resolve()
                if not resolved.exists():
                    failures.append(f"{rel}:{lineno}: broken link -> {target}")
                    continue
                if fragment and resolved.suffix == ".md":
                    if fragment not in headings_of(resolved):
                        failures.append(
                            f"{rel}:{lineno}: missing anchor #{fragment} in "
                            f"{resolved.relative_to(ROOT)}"
                        )

        # 3. Risky claims must be hedged within their paragraph.
        warnings.extend(check_claims(rel, lines))

    for doc in docs:
        print(f"checked {doc.relative_to(ROOT)}")

    print()
    if warnings:
        print(f"{len(warnings)} claim(s) to review (heuristic, not necessarily wrong):")
        for w in warnings:
            print(f"  ! {w}")
        print()
    if failures:
        print(f"FAILED: {len(failures)} structural problem(s):")
        for f in failures:
            print(f"  x {f}")
        return 1

    print(f"OK: {len(docs)} documents, all relative links and anchors resolve, "
          f"code fences balanced, {len(warnings)} claim(s) flagged for review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
