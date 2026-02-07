"""
Cleaner for GitLab Handbook HTML pages.

Reads:
  data/raw/pages/*.html

Writes:
  data/clean/handbook_clean.jsonl

Each JSONL record contains:
- url
- section
- cleaned_text
- source_path
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup


RAW_PAGES_DIR = Path("data/raw/pages")
OUTPUT_DIR = Path("data/clean")
OUTPUT_FILE = OUTPUT_DIR / "handbook_clean.jsonl"

def extract_main_content(html: str) -> str:
    """
    Robust extraction of main handbook content.
    Tries multiple containers and falls back safely.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Remove obvious non-content blocks
    for tag in soup.find_all(["nav", "footer", "aside"]):
        tag.decompose()

    # Try common main content containers
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", role="main")
        or soup.body
    )

    if not main:
        return ""

    lines: list[str] = []

    for elem in main.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = elem.get_text(strip=True)
        if not text:
            continue

        if elem.name.startswith("h"):
            lines.append(f"\n{text.upper()}\n")
        elif elem.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    cleaned = "\n".join(lines)
    cleaned = "\n".join(
        line.strip() for line in cleaned.splitlines() if line.strip()
    )

    return cleaned



def classify_section_from_path(path: Path) -> str:
    name = path.name.lower()
    if "finance" in name:
        return "finance"
    if "security" in name:
        return "security"
    if "legal" in name:
        return "legal"
    if "people" in name:
        return "people-group"
    return "handbook"


def iter_html_files(directory: Path) -> Iterable[Path]:
    return sorted(p for p in directory.glob("*.html") if p.is_file())


def clean_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    records_written = 0

    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        for html_path in iter_html_files(RAW_PAGES_DIR):
            html = html_path.read_text(encoding="utf-8", errors="ignore")

            cleaned_text = extract_main_content(html)
            if not cleaned_text:
                continue

            record = {
                "source": "gitlab_handbook",
                "section": classify_section_from_path(html_path),
                "cleaned_text": cleaned_text,
                "source_path": str(html_path),
            }

            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            records_written += 1

    print(f"[cleaner] wrote {records_written} cleaned documents → {OUTPUT_FILE}")


if __name__ == "__main__":
    clean_all()
