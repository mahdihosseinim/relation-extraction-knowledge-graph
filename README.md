# relation-extraction-knowledge-graph
# Persian Relation Extraction & Knowledge Graph

A Persian-language information extraction and knowledge graph system built with
Gemini, Neo4j, FastAPI, Streamlit, LangChain, and Neo4j GraphRAG.

The project extracts entities and relationships from Persian text, stores the
result as a knowledge graph in Neo4j, and allows users to query the graph using
natural-language questions.

---

## Project Structure

```text
.
├── RE_Module/
│   └── Relation Extraction and Streamlit user interface
│
├── neo4j_module/
│   └── Knowledge Graph ingestion, Neo4j storage,
│       Text2Cypher, and FastAPI service
│
└── README.md
