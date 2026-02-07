"""
Embedder for chunked GitLab Handbook documents.

Reads:
  data/chunks/handbook_chunks.jsonl

Writes:
  data/embeddings/handbook_embeddings.jsonl

Each output record contains:
- chunk_id
- embedding (list[float])
- text
- metadata
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from sentence_transformers import SentenceTransformer


CHUNKS_FILE = Path("data/chunks/handbook_chunks.jsonl")
OUTPUT_DIR = Path("data/embeddings")
OUTPUT_FILE = OUTPUT_DIR / "handbook_embeddings.jsonl"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 16


def load_chunks(path: Path) -> Iterable[dict]:
    """
    Reads chunked JSONL file line by line.

    Why:
    - Streaming read (memory safe)
    - Works for large datasets
    """
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def embed_texts(
    model: SentenceTransformer, texts: List[str]
) -> List[List[float]]:
    """
    Generates embeddings for a batch of texts.

    Why batch?
    - Faster than one-by-one
    - Prevents GPU/CPU thrashing
    """
    return model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).tolist()


def write_embeddings(
    model: SentenceTransformer,
    chunks: Iterable[dict],
    output_path: Path,
) -> None:
    """
    Main embedding loop.

    For each chunk:
    - extract text
    - generate embedding
    - write embedding + metadata to JSONL
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    buffer = []
    written = 0

    with output_path.open("w", encoding="utf-8") as out:
        for chunk in chunks:
            buffer.append(chunk)

            if len(buffer) >= BATCH_SIZE:
                written += process_batch(model, buffer, out)
                buffer.clear()

        # process leftover chunks
        if buffer:
            written += process_batch(model, buffer, out)

    print(
        f"[embedder] wrote {written} embeddings → {output_path}"
    )


def process_batch(
    model: SentenceTransformer,
    batch: List[dict],
    out_file,
) -> int:
    """
    Processes a single batch of chunks.
    - Easier testing
    - Easier retries later
    """
    texts = [item["text"] for item in batch]
    embeddings = embed_texts(model, texts)

    for item, vector in zip(batch, embeddings):
        record = {
            "chunk_id": item["chunk_id"],
            "embedding": vector,
            "text": item["text"],
            "section": item["section"],
            "heading_context": item["heading_context"],
            "source": item["source"],
            "source_path": item["source_path"],
        }

        out_file.write(json.dumps(record) + "\n")

    return len(batch)


def run_embedder() -> None:
    """
    Entry point:
    - load model
    - stream chunks
    - write embeddings
    """
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Chunks file not found: {CHUNKS_FILE}. Run chunker first."
        )

    print(f"[embedder] loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    chunks = load_chunks(CHUNKS_FILE)
    write_embeddings(model, chunks, OUTPUT_FILE)


if __name__ == "__main__":
    run_embedder()
