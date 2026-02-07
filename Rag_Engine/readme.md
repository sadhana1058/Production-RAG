rag_engine/ — Core Intelligence

This is the heart of our system.

rag_engine/retriever.py

Responsibility

Convert query → embedding

Fetch top-K relevant chunks

Apply score thresholds

Inputs

User query

Optional filters

Outputs

Retrieved chunks

Confidence scores

Why
This is where hallucinations are prevented, not in the LLM.

rag_engine/guardrails.py

Responsibility

Enforce safety & correctness rules

Rules implemented

No retrieval → no answer

Low confidence → refuse

Block prompt injection patterns

Max context length enforcement

Why
Enterprise AI fails without guardrails.

rag_engine/prompt_builder.py

Responsibility

Construct the final LLM prompt

Inject:

System instructions

Retrieved context

Formatting rules

Why
Prompt logic must be testable and versioned, not inline strings.

📄 rag_engine/generator.py

Responsibility

Call the LLM

Parse output

Attach citations

Inputs

Final prompt

Outputs

Answer

Sources

Confidence flag

Why
Keeps LLM usage isolated → easier to swap models.