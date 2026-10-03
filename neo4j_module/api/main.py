import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pipeline import KnowledgeGraphPipeline


from text2cypher.pipeline import (
    Text2CypherPipeline,
    GeminiServiceError,
)

logger = logging.getLogger(__name__)


app = FastAPI(
    title="Neo4j Knowledge Graph Service",
    version="0.1.0",
)


# ============================================================
# Request Model
# ============================================================

class IngestRequest(BaseModel):
    """
    Raw relation-extraction output from the RE module.
    """

    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]


# ============================================================
# Response Model
# ============================================================

class IngestResponse(BaseModel):

    ok: bool
    document_id: str

    entities_loaded: int
    relationships_loaded: int

    deleted_nodes: int
    deleted_relationships: int


# ============================================================
# Text2Cypher Request Model
# ============================================================

class QueryRequest(BaseModel):
    """
    Natural-language question that should be
    answered using the current Neo4j graph.
    """

    question: str


# ============================================================
# Text2Cypher Response Model
# ============================================================

class QueryResponse(BaseModel):

    ok: bool

    answer: str

    cypher: str | None

    attempts: int

    rows: list[dict[str, Any]]

    evidence: list[str]

    errors: list[str]

    truncated: bool


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# Ingestion
# ============================================================

@app.post(
    "/ingest",
    response_model=IngestResponse,
)
def ingest(
    request: IngestRequest
):
    """
    Receive raw relation-extraction JSON
    and load it into Neo4j.
    """

    try:

        # Convert the validated API request
        # into exactly the format expected
        # by KnowledgeGraphPipeline.
        raw_data = {

            "entities":
                request.entities,

            "relationships":
                request.relationships,
        }


        with KnowledgeGraphPipeline() as pipeline:

            result = (
                pipeline.process_extraction(
                    raw_data=raw_data
                )
            )


        storage = result[
            "storage_result"
        ]


        return {

            "ok":
                True,

            "document_id":
                result["document_id"],

            "entities_loaded":
                storage[
                    "entities_loaded"
                ],

            "relationships_loaded":
                storage[
                    "relationships_loaded"
                ],

            "deleted_nodes":
                storage[
                    "deleted_nodes"
                ],

            "deleted_relationships":
                storage[
                    "deleted_relationships"
                ],
        }


    except (
        ValueError,
        TypeError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


    except Exception:

        logger.exception(
            "Unexpected ingestion error."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Internal knowledge graph "
                "processing error."
            ),
        )


# ============================================================
# Text2Cypher Query
# ============================================================

@app.post(
    "/query",
    response_model=QueryResponse,
)
def query_graph(
    request: QueryRequest
):
    """
    Receive a natural-language question,
    query the current Neo4j knowledge graph,
    and return a grounded answer.
    """

    try:

        with Text2CypherPipeline() as pipeline:

            result = pipeline.ask(
                request.question
            )


        return result


    # --------------------------------------------------------
    # Invalid request
    # --------------------------------------------------------

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


    # --------------------------------------------------------
    # Gemini unavailable / rate limit / network problem
    # --------------------------------------------------------

    except GeminiServiceError as exc:

        logger.error(
            "Gemini service error: %s",
            exc,
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "LLM service is temporarily "
                "unavailable."
            ),
        )


    # --------------------------------------------------------
    # Unexpected Neo4j / Python / application error
    # --------------------------------------------------------

    except Exception:

        logger.exception(
            "Unexpected Text2Cypher error."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Internal Text2Cypher "
                "processing error."
            ),
        )

