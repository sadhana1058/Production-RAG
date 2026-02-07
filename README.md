# Production-RAG
## Archtecture
rag-service/
│
├── ingestion/
│   ├── crawler
│   ├── cleaner
│   ├── chunker
│   └── embedder
│
├── knowledge/
│   ├── vector_store
│   └── metadata_index
│
├── rag_engine/
│   ├── retriever
│   ├── guardrails
│   ├── prompt_builder
│   └── generator
│
├── api/
│   ├── routes
│   ├── schemas
│   └── auth
│
├── observability/
│   ├── logging
│   └── metrics
│
└── deployment/
    ├── docker
    └── compose

📘 Enterprise Policy Intelligence RAG API

A production-grade Retrieval-Augmented Generation (RAG) service that enables accurate, source-grounded, and auditable Q&A over enterprise policy documents, built using the public GitLab Handbook as a real-world knowledge base.

This system is designed to mirror how RAG is implemented in real companies, with guardrails, observability, async ingestion, and API-first design — not a toy chatbot.

🚀 Problem Statement

In large organizations, employees frequently struggle to find accurate answers across:

HR policies

Security & compliance guidelines

Finance and expense rules

Legal and operational SOPs

Naive LLM chatbots:

Hallucinate answers

Ignore source verification

Lack auditability

This project solves that by enforcing retrieval-only answers, confidence-based refusal, and full observability.

🧠 Solution Overview

This service:

Indexes enterprise policy documents (GitLab Handbook)

Retrieves only relevant, high-confidence context

Generates answers strictly grounded in source documents

Refuses to answer when information is missing

Logs and monitors every decision

🏗️ System Architecture
rag-service/
│
├── ingestion/          # Offline async document ingestion
│   ├── crawler         # Fetch handbook pages
│   ├── cleaner         # Remove HTML noise
│   ├── chunker         # Semantic chunking
│   └── embedder        # Vector embedding
│
├── knowledge/          # Knowledge persistence
│   ├── vector_store    # FAISS / ChromaDB
│   └── metadata_index  # Structured metadata
│
├── rag_engine/         # Core intelligence
│   ├── retriever       # Top-K + threshold retrieval
│   ├── guardrails      # Hallucination & safety checks
│   ├── prompt_builder  # Controlled prompt construction
│   └── generator       # LLM interaction + citations
│
├── api/                # FastAPI service
│   ├── routes          # REST endpoints
│   ├── schemas         # Typed request/response models
│   └── auth            # JWT / API key support
│
├── observability/      # Monitoring & debugging
│   ├── logging         # Structured logs
│   └── metrics         # Prometheus metrics
│
└── deployment/         # Containerization
    ├── docker
    └── compose

🔐 Key Features
✅ Retrieval-Only Answers

LLM can only answer using retrieved handbook content

No external knowledge allowed

🛑 Hallucination Guardrails

Confidence threshold enforced

Low-confidence queries return a refusal

Prevents “made-up” answers

📜 Source Citations

Every answer includes:

Document title

URL

Section reference

🔍 Metadata-Aware Retrieval

Filters by:

Department (HR, Finance, Security)

Document type

Version

📊 Observability & Metrics

Retrieval hit rate

Refusal rate

Query latency

Top failed queries

⚙️ Async Ingestion

Decouples slow ingestion from fast queries

Mirrors real production pipelines

📂 Data Source

This project uses real enterprise documentation from:

GitLab public handbook:

HR policies

Finance & expense guidelines

Security & compliance documentation

Legal policies

These documents closely resemble internal corporate knowledge bases used in production systems.

🔌 API Endpoints
Method	Endpoint	Description
POST	/rag/query	Ask a policy question
POST	/rag/ingest	Trigger document ingestion
GET	/health	Service health check
GET	/metrics	Prometheus metrics
🧪 Example Query

User

What expenses are reimbursable under GitLab’s policy?


Response

{
  "answer": "GitLab reimburses business-related travel, meals, and lodging expenses when pre-approved...",
  "sources": [
    {
      "title": "Expense Reimbursement Policy",
      "url": "https://about.gitlab.com/handbook/finance/expenses/"
    }
  ],
  "confidence": "high"
}

🧰 Tech Stack (All Free / Open Source)

Backend: FastAPI

Embeddings: sentence-transformers (MiniLM)

Vector Store: FAISS / ChromaDB

LLM: Local (Ollama) or free-tier hosted

Monitoring: Prometheus + Grafana

Containerization: Docker

🧠 Design Decisions

Ingestion separated from query path → scalable & reliable

Guardrails before generation → reduced hallucinations

Metadata-driven retrieval → enterprise realism

Observability built-in → debuggable AI

📈 Evaluation Strategy

Gold-standard policy queries

Retrieval confidence tracking

Refusal correctness validation

Latency benchmarks

Future Enhancements

Role-based access control (RBAC)

Multi-tenant document indexing

Slack / Web UI integration

Continuous ingestion with diff detection

Automated retrieval quality evaluation