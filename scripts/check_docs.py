#!/usr/bin/env python3
"""Verify the documentation set: link resolution, code fences, Mermaid blocks, risky claims.

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
# Mermaid fails to render a fenced block unless the first line names a diagram type.
MERMAID_STARTS = (
    "sequenceDiagram", "stateDiagram", "stateDiagram-v2", "flowchart", "graph",
    "classDiagram", "erDiagram", "gantt", "pie", "timeline", "journey",
    "quadrantChart", "mindmap", "gitGraph", "sankey-beta", "xychart-beta",
)
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


def fenced_blocks(lines: list[str]):
    """Yield (opening_fence_line, info_string, [(lineno, line), ...]) per block."""
    opened: int | None = None
    info = ""
    body: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            if opened is None:
                opened, info, body = lineno, line.strip()[3:].strip(), []
            else:
                yield opened, info, body
                opened = None
            continue
        if opened is not None:
            body.append((lineno, line))
    if opened is not None:  # unclosed; the fence-count check reports it
        yield opened, info, body


def check_mermaid(rel: Path, lines: list[str]) -> list[str]:
    """Flag Mermaid blocks that will not render.

    Both rules here come from real breakage that the fence-balance check could not
    see: a stray opening fence produced an *empty* block with the diagram spilled
    into prose, and a `;` inside a sequence message made Mermaid parse the rest of
    the line as a new statement.
    """
    out: list[str] = []
    for fence_line, info, body in fenced_blocks(lines):
        if info != "mermaid":
            continue
        text = [line for _, line in body]
        first = next((line.strip() for line in text if line.strip()), "")
        if not first:
            out.append(
                f"{rel}:{fence_line}: empty mermaid block - a second fence line closes it "
                f"immediately, so the diagram renders as nothing"
            )
            continue
        if not first.startswith(MERMAID_STARTS):
            out.append(
                f"{rel}:{fence_line}: mermaid block does not open with a diagram type, "
                f"first line is {first[:40]!r}"
            )
        for lineno, line in body:
            if ";" in line:
                out.append(
                    f"{rel}:{lineno}: ';' inside a mermaid block - Mermaid reads it as a "
                    f"statement separator, not as punctuation; use a comma or a dash"
                )
    return out


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
    # Every markdown file in the tree, including docs/learn/, minus hidden and
    # vendored directories.
    docs = sorted(
        p
        for p in ROOT.rglob("*.md")
        if not any(part.startswith(".") or part in {"node_modules", "venv"}
                   for part in p.parts)
    )
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

        # 3. Mermaid blocks must be renderable: non-empty, typed, no `;`.
        failures.extend(check_mermaid(rel, lines))

        # 4. Risky claims must be hedged within their paragraph.
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
          f"code fences balanced, mermaid blocks well formed, "
          f"{len(warnings)} claim(s) flagged for review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
