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


# Relation-Extraction-Project

```markdown
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
```

---

## Main Workflow

The system consists of two main stages.

### 1. Relation Extraction

Persian text is entered through the Streamlit interface.

The Relation Extraction module uses an LLM to extract:

- Entities
- Entity types and properties
- Relationships between entities
- Relationship properties
- Evidence sentences

The extracted data is converted to structured JSON and sent to the Neo4j
ingestion service.

General extraction format:

```json
{
  "entities": [
    {
      "id": "entity_id",
      "name": "Entity Name",
      "type": "EntityType",
      "properties": {}
    }
  ],
  "relationships": [
    {
      "source": "source_id",
      "target": "target_id",
      "type": "RELATION_TYPE",
      "properties": {
        "evidence": "Supporting sentence"
      }
    }
  ]
}
```

### 2. Knowledge Graph & Text2Cypher

The extracted entities and relationships are processed and stored in Neo4j.

Users can then ask questions in natural language. The Text2Cypher module:

1. Reads the current Neo4j schema
2. Converts the question into Cypher
3. Validates and executes the generated query
4. Repairs invalid Cypher queries when possible
5. Retrieves results and evidence
6. Generates a natural-language answer

---

## Architecture

```text
Persian Text
     |
     v
Relation Extraction
     |
     v
Entities + Relationships
     |
     v
FastAPI /ingest
     |
     v
Neo4j Knowledge Graph
     |
     v
Text2Cypher
     |
     v
FastAPI /query
     |
     v
Natural Language Answer
```

---

## Technologies

- Python
- Gemini API
- Neo4j
- Neo4j GraphRAG
- LangChain
- FastAPI
- Uvicorn
- Streamlit
- Pandas
- Pydantic

---

## Running the Project

### 1. Start Neo4j

Start the Neo4j database using Neo4j Desktop.

Make sure the Neo4j connection settings are correctly configured before
starting the API.

---

### 2. Run the FastAPI Service

From the Neo4j module directory, run:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

For access from another computer on the same local network:

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## API Endpoints

### Health Check

```text
GET /health
```

### Knowledge Graph Ingestion

```text
POST /ingest
```

Expected input:

```json
{
  "entities": [],
  "relationships": []
}
```

### Knowledge Graph Query

```text
POST /query
```

Expected input:

```json
{
  "question": "Your natural-language question"
}
```

The response can contain:

- Natural-language answer
- Generated Cypher query
- Neo4j result rows
- Evidence
- Number of Cypher attempts
- Errors encountered during repair
- Result truncation status

---

## Running the Streamlit Interface

Go to the `RE_Module` directory and run:

```bash
python -m streamlit run app.py
```

The Streamlit interface provides two main sections:

- Relation Extraction
- Knowledge Graph Question Answering

By default, Streamlit is usually available at:

```text
http://localhost:8501
```

---

## Local Network Setup

If the Streamlit client and Neo4j/FastAPI server are running on different
computers:

1. Connect both computers to the same local network.
2. Run FastAPI with `--host 0.0.0.0`.
3. Allow inbound TCP traffic on port `8000` in the server firewall.
4. Configure the RE module with the local IP address of the FastAPI server.

Example:

```text
http://***.***.*.**:8000/ingest
http://***.***.*.**:8000/query
```

---

## Configuration and Security

Before running the system, configure:

- Neo4j URI
- Neo4j username and password
- Gemini API key
- Model settings
- Optional proxy settings

Do not publish real API keys, passwords, access tokens, or other credentials
in the repository.

Use local configuration files or environment variables for sensitive values.

---

## Current Features

- Persian entity extraction
- Persian relationship extraction
- Evidence extraction
- Knowledge graph construction
- Neo4j ingestion
- Entity resolution and normalization
- Runtime Neo4j schema discovery
- Natural-language to Cypher conversion
- Cypher repair
- Model fallback
- Evidence-based question answering
- FastAPI service
- Streamlit user interface

---

## Status

This project is currently under development and is intended for research and
experimental knowledge graph applications.
```
.
