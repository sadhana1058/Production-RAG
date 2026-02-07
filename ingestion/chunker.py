# ingestion/chunker.py
"""
Heading-aware chunker for cleaned GitLab Handbook documents.

Reads:
  data/clean/handbook_clean.jsonl

Writes:
  data/chunks/handbook_chunks.jsonl

Chunking strategy:
- Split by headings first
- Then size-limit chunks with overlap
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Dict


CLEAN_FILE = Path("data/clean/handbook_clean.jsonl")
OUTPUT_DIR = Path("data/chunks")
OUTPUT_FILE = OUTPUT_DIR / "handbook_chunks.jsonl"

# Size controls (character-based; robust without tokenizers)
MAX_CHARS = 1200
OVERLAP_CHARS = 200


HEADING_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9 \-/,&()]+$")


def split_by_headings(text: str) -> List[Dict[str, str]]:
    """
    Split text into sections based on ALL-CAPS headings.
    Returns a list of {heading, content}.
    """
    lines = text.splitlines()

    sections = []
    current_heading = "INTRODUCTION"
    buffer: List[str] = []

    for line in lines:
        if HEADING_PATTERN.match(line.strip()):
            # flush previous section
            if buffer:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": "\n".join(buffer).strip(),
                    }
                )
                buffer = []

            current_heading = line.strip()
        else:
            buffer.append(line)

    # flush last section
    if buffer:
        sections.append(
            {
                "heading": current_heading,
                "content": "\n".join(buffer).strip(),
            }
        )

    return sections


def size_limited_chunks(text: str) -> List[str]:
    """
    Split text into overlapping chunks within MAX_CHARS.
    """
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + MAX_CHARS, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == length:
            break

        start = end - OVERLAP_CHARS

    return chunks


def chunk_document(record: dict, doc_index: int) -> List[dict]:
    """
    Chunk a single cleaned document into heading-aware chunks.
    """
    chunks_out = []

    sections = split_by_headings(record["cleaned_text"])

    chunk_counter = 0
    for section in sections:
        heading = section["heading"]
        content = section["content"]

        if not content:
            continue

        sub_chunks = size_limited_chunks(content)

        for sub in sub_chunks:
            chunk_id = f"{record['section']}_{doc_index:04d}_{chunk_counter:02d}"

            chunks_out.append(
                {
                    "chunk_id": chunk_id,
                    "source": record["source"],
                    "section": record["section"],
                    "heading_context": heading,
                    "text": sub,
                    "source_path": record["source_path"],
                }
            )

            chunk_counter += 1

    return chunks_out


def run_chunker() -> None:
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(
            f"Clean file not found: {CLEAN_FILE}. Run cleaner first."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    doc_index = 0

    with CLEAN_FILE.open("r", encoding="utf-8") as fin, OUTPUT_FILE.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            record = json.loads(line)

            chunks = chunk_document(record, doc_index)
            for ch in chunks:
                fout.write(json.dumps(ch, ensure_ascii=False) + "\n")

            total_chunks += len(chunks)
            doc_index += 1

    print(
        f"[chunker] processed {doc_index} documents → "
        f"{total_chunks} chunks written to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    run_chunker()
