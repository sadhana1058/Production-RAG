ingestion/ — Offline Knowledge Builder

Purpose: Convert GitLab Handbook pages into clean, structured, searchable knowledge.

This layer never answers user queries.
It only prepares data.

ingestion/crawler.py

Responsibility

Fetch raw content from GitLab Handbook URLs

Handle retries, timeouts

Avoid re-downloading unchanged pages

Inputs

List of URLs

Crawl config

Outputs

Raw HTML or Markdown

Page metadata (URL, timestamp)

Why it exists

Separates data acquisition from processing

In real companies, crawling is replaceable (S3, CMS, Confluence, etc.)

ingestion/cleaner.py

Responsibility

Strip navigation bars, footers, side menus

Remove irrelevant boilerplate

Normalize whitespace

Inputs

Raw HTML

Outputs

Clean, readable text

Why
LLMs + embeddings hate noisy HTML.
This step massively improves retrieval quality.

ingestion/chunker.py

Responsibility

Split cleaned text into semantically meaningful chunks

Preserve section boundaries

Add chunk IDs

Inputs

Clean text

Chunking config (size, overlap)

Outputs

List of text chunks

Why

Chunking strategy directly affects hallucination rate

Production systems tune this carefully

ingestion/embedder.py

Responsibility

Convert chunks → embedding vectors

Attach metadata to each chunk

Inputs

Text chunks

Embedding model

Outputs

(embedding, text, metadata) records

Why
Embedding is expensive → isolated + batchable.