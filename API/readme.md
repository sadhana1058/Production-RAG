api/ — Production Interface

How the world talks to your RAG system

api/routes.py

Responsibility

Define REST endpoints

Orchestrate RAG pipeline

Endpoints

/rag/query

/rag/ingest

/health

Why
API-first design = production mindset.

api/schemas.py

Responsibility

Request/response validation

Typed contracts

Why

Prevents garbage input

Enables OpenAPI docs

Critical for scaling teams

api/auth.py

Responsibility

Authentication (JWT / API keys)

Attach user roles

Why
Future-proofing:

Role-based retrieval

Multi-tenant systems