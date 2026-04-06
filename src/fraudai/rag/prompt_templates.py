"""Prompt templates for RAG context injection into agent responses.

Each template is designed to be filled with retrieved legal passages
and injected into the agent's system or user prompt before LLM generation.
"""

# ---------------------------------------------------------------------------
# Generic RAG context template (Harvey, Jessica, Mike, Rachel)
# ---------------------------------------------------------------------------

RAG_CONTEXT_TEMPLATE = """\
The following legal context was retrieved from the Spanish Official Gazette (BOE) \
and EU regulations. Use this information to support your response. \
Always cite the specific law, article, and date when referencing legal provisions.

{context}

---
Corpus version: {corpus_version}
Retrieved {n_results} relevant passages."""

# ---------------------------------------------------------------------------
# Louis-specific template (exhaustive citations, exact article references)
# ---------------------------------------------------------------------------

LOUIS_RAG_TEMPLATE = """\
LEGAL REFERENCES (from BOE consolidated legislation database):
{context}

INSTRUCTIONS FOR CITATION:
- Always cite the exact article number and law title
- Include the publication date and last consolidation date
- If the article has been modified, note the modification
- Cite in the user's language but keep legal references in their original form
---
Corpus version: {corpus_version}"""

# ---------------------------------------------------------------------------
# Single result formatting template
# ---------------------------------------------------------------------------

SINGLE_RESULT_TEMPLATE = """\
[{norma_titulo} -- {articulo}]
Published: {fecha_publicacion} | Consolidated: {fecha_consolidacion} | Status: {estado}
BOE ID: {boe_id}

{text}"""
