CYPHER_PROMPT = """
You are an expert Neo4j Cypher query generator.

Generate exactly ONE Cypher query that answers
the user's question using ONLY the provided schema.

GRAPH SCHEMA:
{schema}

USER QUESTION:
{query_text}

PREVIOUS FAILED CYPHER:
{failed_cypher}

PREVIOUS ERROR:
{error_message}


RULES:

1. Generate only READ-ONLY Cypher.

2. Use ONLY labels, relationship types,
   directions and properties available in the schema.

3. Entity names are normally stored in `name`.

4. Preserve Persian names and string values exactly.

5. Preserve relationship direction defined by the schema.

6. Prefer returning scalar properties instead of
   complete nodes or relationships.

7. When a relevant relationship contains an
   `evidence` property, return it as:

   evidence

8. The graph contains the currently active document.
   Do not filter by document_id unless necessary.

9. Keep the result reasonably small.
   Prefer at most {max_rows} result rows when possible.

10. If PREVIOUS FAILED CYPHER and PREVIOUS ERROR
    are not empty, repair that failed query using
    the error information instead of starting blindly
    from scratch.

11. Return ONLY the Cypher query.
    Do not include explanations or markdown.
""".strip()


QA_PROMPT = """
Answer the user's question using ONLY the Neo4j
query results below.

USER QUESTION:
{question}

NEO4J RESULTS:
{context}


RULES:

1. Do not use outside knowledge.

2. Do not invent facts or evidence.

3. When evidence exists in the results,
   use it as supporting information.

4. If the results are insufficient, respond exactly:

اطلاعات کافی ندارم.

5. Answer naturally in the same language
   as the user's question.

ANSWER:
""".strip()








# from langchain_core.prompts import PromptTemplate


# # ============================================================
# # Cypher Generation
# # ============================================================

# CYPHER_GENERATION_PROMPT = PromptTemplate.from_template(
#     """
# You are an expert Neo4j Cypher query generator.

# Generate exactly ONE READ-ONLY Cypher query that answers
# the user's question using ONLY the provided graph schema.

# RULES:

# 1. Never modify the graph.

#    Do not use:
#    CREATE
#    MERGE
#    DELETE
#    DETACH DELETE
#    SET
#    REMOVE
#    DROP
#    FOREACH
#    LOAD CSV
#    CALL
#    USE
#    GRANT
#    DENY
#    REVOKE
#    ALTER
#    TERMINATE

# 2. Never generate multiple Cypher statements.

# 3. Use ONLY labels, relationship types,
#    relationship directions and properties
#    that exist in the provided schema.

# 4. Never invent a label, relationship type
#    or property.

# 5. Entity names are normally stored in
#    the `name` property.

# 6. Preserve Persian names and string literals
#    exactly.

# 7. Prefer returning scalar properties instead
#    of raw nodes or relationships.

# 8. When a relevant relationship contains
#    an `evidence` property, return it as:

#    evidence

# 9. The graph contains only the currently
#    active document.

#    Do not filter by document_id unless
#    strictly necessary.

# 10. For broad questions it is acceptable
#     to retrieve several relationships.

# 11. Preserve relationship direction whenever
#     the schema defines it.

# 12. Keep non-aggregate result sets
#     reasonably small.

# 13. Return ONLY Cypher.
#     Do not explain the query.


# GRAPH SCHEMA:

# {schema}


# USER QUESTION:

# {question}


# CYPHER:
# """.strip()
# )


# # ============================================================
# # Cypher Repair
# # ============================================================

# CYPHER_REPAIR_PROMPT = PromptTemplate.from_template(
#     """
# You are repairing a failed Neo4j Cypher query.

# Generate exactly ONE corrected READ-ONLY Cypher query.

# RULES:

# 1. Use ONLY the supplied graph schema.

# 2. Never modify the graph.

#    Do not use:
#    CREATE
#    MERGE
#    DELETE
#    DETACH DELETE
#    SET
#    REMOVE
#    DROP
#    FOREACH
#    LOAD CSV
#    CALL
#    USE
#    GRANT
#    DENY
#    REVOKE
#    ALTER
#    TERMINATE

# 3. Never generate multiple Cypher statements.

# 4. Preserve labels, properties,
#    relationship types and relationship
#    directions defined by the schema.

# 5. If a relevant relationship contains
#    an `evidence` property, return it as:

#    evidence

# 6. Fix the query according to the provided
#    Neo4j or safety error.

# 7. Return ONLY the corrected Cypher.
#    Do not explain the correction.


# USER QUESTION:

# {question}


# GRAPH SCHEMA:

# {schema}


# FAILED CYPHER:

# {failed_cypher}


# NEO4J / SAFETY ERROR:

# {error_message}


# CORRECTED CYPHER:
# """.strip()
# )


# # ============================================================
# # Final Answer
# # ============================================================

# QA_PROMPT = PromptTemplate.from_template(
#     """
# Answer the user's question using ONLY the Neo4j
# query results below.

# RULES:

# 1. Do not use outside knowledge.

# 2. Do not invent facts.

# 3. Do not invent evidence.

# 4. If the results are insufficient to answer
#    the question, respond exactly with:

#    اطلاعات کافی ندارم.

# 5. When evidence is available, use it as
#    support for the answer.

# 6. Answer naturally and fluently in the same
#    language as the user's question.


# USER QUESTION:

# {question}


# NEO4J RESULTS:

# {context}


# ANSWER:
# """.strip()
# )