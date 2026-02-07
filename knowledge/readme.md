knowledge/ — Source of Truth

Purpose: Persist knowledge in a way that’s fast, filterable, auditable.

knowledge/vector_store.py

Responsibility

Store embeddings

Perform similarity search

Support metadata filtering

Examples

FAISS

ChromaDB

Inputs

Query embedding

Filters (department, doc_type)

Outputs

Ranked chunks + similarity scores

Why
Retrieval must be fast, deterministic, and inspectable.

knowledge/metadata_index.py

Responsibility

Manage structured metadata

Enable lookups like:

“all finance policies”

“latest version only”

Why separate from vector store
In real systems:

Metadata often lives in SQL

Vectors live elsewhere

This mirrors real architecture.