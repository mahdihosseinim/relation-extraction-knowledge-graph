import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Neo4jGraphLoader:
    """
    Stores one resolved document at a time in Neo4j.

    Current MVP behavior:
        - Neo4j contains only the latest uploaded document.
        - Loading a new document replaces the previous graph.
        - Deletion and insertion happen in one transaction.

    Expected input:
        Output of EntityResolver.

    Responsibilities:
        - Validate entity types against schema_registry.json
        - Validate relationship types against schema_registry.json
        - Replace the previous graph atomically
        - Store node properties
        - Store relationship properties, including `evidence`
    """

    # ---------------------------------------------------------
    # Cypher Queries
    # ---------------------------------------------------------

    # 1. clear all nodes and graph relationships.
    CLEAR_GRAPH_QUERY = """
    MATCH (n)
    DETACH DELETE n
    """

    # 2. creat noede if not exist/ update if exist
    NODE_QUERY = """
    MERGE (
        n:$($label) {
            document_id: $document_id,
            entity_key: $entity_key
        }
    )

    SET n.name = $name
    SET n += $properties

    RETURN count(n) AS node_count
    """

    # 3. creat relationsip if not exist/ update if exist
    RELATIONSHIP_QUERY = """
    MATCH (
        source {
            document_id: $document_id,
            entity_key: $source_key
        }
    )

    MATCH (
        target {
            document_id: $document_id,
            entity_key: $target_key
        }
    )

    MERGE (source)-[r:$($relation_type)]->(target)

    SET r += $properties

    RETURN count(r) AS relationship_count
    """

    # These fields belong to the storage layer.
    # Entity properties are not allowed to overwrite them.
    NODE_RESERVED_PROPERTIES = {
        "document_id",
        "entity_key",
        "name",
    }

    _SKIP = object()

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def __init__(self, connection,
        schema_path: str | Path = "schema_registry.json"):

        self.connection = connection

        schema_path = Path(schema_path)

        if not schema_path.is_absolute():
            schema_path = PROJECT_ROOT / schema_path

        self.schema_path = schema_path.resolve()

        self.allowed_entity_types = set()
        self.allowed_relationship_types = set()

        self._reload_schema() # ایا اسکیما معتبر و قابل خوندن هست موقع ایجاد شیء؟

    # =========================================================
    # Public API
    # =========================================================

    def replace_document(self, graph_data: dict) -> dict:
        """
        Replace the currently stored graph with graph_data.

        Processing order:

            1. Reload schema
            2. Validate new data
            3. Start one Neo4j transaction
            4. Delete previous graph
            5. Create new nodes
            6. Create new relationships
            7. Commit

        If validation or database writing fails, the previous
        graph is not replaced successfully.
        """

        # Schema Evolution may update the registry between
        # document uploads, so always refresh it. > آخرین آپدیت اسکیما رو داشته باشیم
        self._reload_schema()

        # IMPORTANT:
        # Validation happens before deleting existing data.
        # dictionary of: document_id, entities and relationships
        prepared_data = self._validate_and_prepare(graph_data)

        database = self.connection.config.get("database", "neo4j")

        with self.connection.driver.session(database=database) as session:

            result = session.execute_write(
                self._replace_document_transaction,
                prepared_data,
            )

        return result

    # =========================================================
    # Transaction
    # =========================================================

    @classmethod
    def _replace_document_transaction(cls, tx, graph_data: dict) -> dict:
        """
        Delete the previous graph and write the new graph
        inside one managed Neo4j transaction.
        """

        # ----------------------------
        # Delete previous graph
        # ----------------------------

        clear_result = tx.run(cls.CLEAR_GRAPH_QUERY)

        clear_summary = clear_result.consume()

        deleted_nodes = (clear_summary.counters.nodes_deleted)

        deleted_relationships = (clear_summary.counters.relationships_deleted)

        # ----------------------------
        # Write new graph
        # ----------------------------

        write_result = cls._write_document(tx, graph_data)

        return {
            "document_id": graph_data["document_id"],

            "deleted_nodes": deleted_nodes,

            "deleted_relationships": deleted_relationships,

            "entities_loaded":
                write_result[
                    "entities_loaded"
                ],

            "relationships_loaded":
                write_result[
                    "relationships_loaded"
                ],
        }

    # =========================================================
    # Graph writing
    # =========================================================

    @classmethod
    def _write_document(cls, tx, graph_data: dict) -> dict:
        """
        Write entities first and relationships afterwards.
        """

        document_id = graph_data["document_id"]

        entities = graph_data["entities"]

        relationships = graph_data["relationships"]

        # ----------------------------
        # Entities
        # ----------------------------

        for entity in entities:

            result = tx.run(
                cls.NODE_QUERY,

                document_id=document_id,

                entity_key=entity["entity_key"],

                label=entity["type"],

                name=entity["name"],

                properties=entity["properties"]
            )

            record = result.single()

            if (record is None
                 or record["node_count"] != 1):
                raise RuntimeError(
                    "Unexpected Neo4j result while "
                    "writing entity. have made None or more nodes!"
                    f"'{entity['entity_key']}'."
                )

        # ----------------------------
        # Relationships
        # ----------------------------

        for relationship in relationships:

            result = tx.run(
                cls.RELATIONSHIP_QUERY,

                document_id=document_id,

                source_key=relationship["source"],

                target_key=relationship["target"],

                relation_type=relationship["type"],

                properties=relationship["properties"]
            )

            record = result.single()

            if (
                record is None
                or record["relationship_count"] != 1):
                raise RuntimeError(
                    "Could not create relationship: "
                    f"{relationship['source']} "
                    f"-[{relationship['type']}]-> "
                    f"{relationship['target']}"
                )

        return {
            # number_of_
            "entities_loaded": len(entities),

            # number_of_
            "relationships_loaded": len(relationships),
        }

    # =========================================================
    # Validation --> استراکچر دیتای تابع رزالور رو چک میکنه تا درست باشه
    # points to func and variables: allowed_entity_types(that get from reload_schema), _prepare_properties
    # =========================================================

    def _validate_and_prepare(self, graph_data: dict,) -> dict:
        """
        Validate EntityResolver output before Neo4j is changed.

        This validation is intentionally lightweight.

        It checks structural correctness and whether entity /
        relationship types exist in schema_registry.json.

        **It does NOT validate semantic source/target type rules.**
        """

        if not isinstance(graph_data, dict):
            raise TypeError(
                "graph_data must be a dictionary."
            )

        # ----------------------------
        # document_id
        # ----------------------------

        document_id = graph_data.get("document_id")

        if (not isinstance(document_id,str) or
            not document_id.strip()):

            raise ValueError(
                "document_id must be a non-empty string."
            )

        document_id = document_id.strip()

        # ----------------------------
        # entities / relationships
        # ----------------------------

        raw_entities = graph_data.get("entities", [])

        raw_relationships = graph_data.get("relationships",[])

        if not isinstance(raw_entities, list):
            raise TypeError(
                "entities must be a list."
            )

        if not isinstance(raw_relationships, list):
            raise TypeError(
                "relationships must be a list."
            )

        # =====================================================
        # Entities
        # =====================================================

        prepared_entities = []

        entity_keys = set()

        for entity in raw_entities:

            if not isinstance(entity, dict):
                # print(
                #     "[WARNING] Skipping entity: "
                #     "Entity must be a dictionary."
                # )
                # continue
                raise TypeError(
                    "Each entity must be a dictionary."
                )

            entity_key = entity.get("entity_key")

            entity_name = entity.get("name")

            entity_type = entity.get("type")

            # ----------------------------
            # entity_key
            # ----------------------------

            if (not isinstance(entity_key,str)
                or not entity_key.strip()):
                raise ValueError(
                    "Every entity must have "
                    "a non-empty entity_key."
                )

            entity_key = entity_key.strip()

            #  entity key must be uniq
            if entity_key in entity_keys:
                raise ValueError(
                    "Duplicate entity_key detected: "
                    f"'{entity_key}'"
                )

            # ----------------------------
            # name
            # ----------------------------

            if (not isinstance(entity_name, str)
                or not entity_name.strip()):
                print(
                    f"[WARNING] Skipping entity '{entity_key}': "
                    "Name is empty or invalid."
                )
                continue
                # raise ValueError(
                #     f"Entity '{entity_key}' must "
                #     "have a non-empty name."
                # )

            if (
                not isinstance(entity_type, str)
                or not entity_type.strip()):
                print(
                    f"[WARNING] Skipping entity '{entity_key}': "
                    "Type is empty or invalid.")
                continue
                # raise ValueError(
                # f"Entity '{entity_key}' must have "
                #  "a non-empty string type."
                # )                

            entity_name = entity_name.strip()

            # ----------------------------
            # entity type
            # ----------------------------
            """
            #------مکانیزم اول
            # رویکرد بسیار سختگیرانه. اگر موجودیت پیدا شد که داخل اسکیما نبود برنامه متوقف بشه
            if (entity_type not in self.allowed_entity_types):
                raise ValueError(
                    f"Entity type '{entity_type}' "
                    "is not defined in "
                    "schema_registry.json."
                )
            """      


            """
            #----مکانیزم دوم:
            # رویکرد نسبتا سخت گیرانه. اگر موجودیت بود که تو اسکیما نبود فقط رد بشه بره سراغ رابطه بعدی
            if entity_type not in self.allowed_entity_types:
                print(f"[WARNING] Skipping entity '{entity_key}' with unknown type: '{entity_type}'")
                continue  # این دستور باعث می‌شود کدهای پایین اجرا نشود و این موجودیت دور ریخته شود
            """

            # ----مکانیزم سوم: انعطاف‌پذیر (هشدار دادن ولی اضافه کردن) ===
            # در این حالت، اگر موجودیت در شِما نباشد، فقط یک پیام چاپ می‌شود اما به گراف اضافه می‌گردد
            # این رویکرد تا قبل از اینکه ماژول آپدیت اسکیما ساخته شود معتبر است.
            if entity_type not in self.allowed_entity_types:
                print(f"[INFO] Unknown entity type '{entity_type}' detected for '{entity_key}'. Adding it to the graph anyway.")


            entity_keys.add(entity_key)

            properties = (
                self._prepare_properties(entity.get("properties",{}),
                                         reserved_keys=(self.NODE_RESERVED_PROPERTIES)
                )
            )

            prepared_entities.append(
                {
                    "entity_key": entity_key,

                    "name": entity_name,

                    "type": entity_type,

                    "properties": properties,
                }
            )

        # =====================================================
        # Relationships
        # =====================================================

        prepared_relationships = []

        for relationship in raw_relationships:

            # هرکدوم از رابطه ها خودش یک دیکشنری هست یا نه
            if not isinstance(relationship,dict):
                raise TypeError(
                    "Each relationship must "
                    "be a dictionary."
                )

            source = relationship.get("source")

            target = relationship.get("target")

            relation_type = relationship.get("type")

            # ----------------------------
            # source
            # ----------------------------

            if (not isinstance(source, str,) 
                or not source.strip()):

                raise ValueError(
                    "Relationship source must be "
                    "a non-empty entity_key."
                )

            source = source.strip()

            # ----------------------------
            # target
            # ----------------------------

            if (not isinstance(target, str,)
                or not target.strip()
            ):
                raise ValueError(
                    "Relationship target must be "
                    "a non-empty entity_key."
                )

            target = target.strip()

            # ----------------------------
            # references must exist
            # ----------------------------

            if source not in entity_keys:
                print(f"[WARNING] Skipping relationship: Source_id '{source}' is missing in entities.")
                continue
                # raise ValueError(
                #     f"Relationship source '{source}' "
                #     "does not exist in entities."
                # )

            if target not in entity_keys:
                print(f"[WARNING] Skipping relationship: Target_id '{target}' is missing in entities.")
                continue
                # raise ValueError(
                #     f"Relationship target '{target}' "
                #     "does not exist in entities."
                # )

            # ----------------------------
            # relationship type
            # ----------------------------
            if (
                not isinstance(relation_type, str)
                or not relation_type.strip()
            ):
                raise ValueError(
                    f"Relationship '{source}' -> '{target}' "
                    "must have a non-empty string type."
                )

            relation_type = relation_type.strip()
            """
            #------مکانیزم اول
            # رویکرد بسیار سختگیرانه. اگر موجودیت پیدا شد که داخل اسکیما نبود برنامه متوقف بشه
            if (relation_type not in self.allowed_relationship_types):

                raise ValueError(
                    f"Relationship type "
                    f"'{relation_type}' is not "
                    "defined in schema_registry.json. "
                    "Schema Evolution must process "
                    "this relationship before loading."
                )        
            """

            """
            #----مکانیزم دوم:
            # رویکرد نسبتا سخت گیرانه. اگر موجودیت بود که تو اسکیما نبود فقط رد بشه بره سراغ رابطه بعدی
            if relation_type not in self.allowed_relationship_types:
                print(f"[WARNING] Skipping unknown relationship type: '{relation_type}'")
                continue
            """

            # ----مکانیزم سوم: انعطاف‌پذیر (هشدار دادن ولی اضافه کردن) ===
            #  اگر رابطه در شِما نباشد، فقط یک پیام چاپ می‌شود اما به گراف اضافه می‌گردد
            # این رویکرد تا قبل از اینکه ماژول آپدیت اسکیما ساخته شود معتبر است.
            if relation_type not in self.allowed_relationship_types:
                print(f"[INFO] Unknown relationship '{relation_type}' detected. Adding to graph.")


            properties = (
                self._prepare_properties(relationship.get("properties",{}))
            )

            prepared_relationships.append(
                {
                    "source": source,

                    "target": target,

                    "type": relation_type,

                    "properties": properties,
                }
            )

        return {
            "document_id": document_id,

            "entities": prepared_entities,

            "relationships": prepared_relationships,
        }

    # =========================================================
    # Schema
    # =========================================================

    def _reload_schema(self):
        """
        Reload schema_registry.json.

        Future Schema Evolution can modify the registry,
        therefore the Loader reloads it before every document.
        """

        if not self.schema_path.exists():

            raise FileNotFoundError(
                "Schema registry not found: "
                f"{self.schema_path}"
            )

        with self.schema_path.open("r", encoding="utf-8") as file:

            schema = json.load(file)

        self.allowed_entity_types = (
            self._extract_schema_names(schema.get("entity_types",[]))
        )

        self.allowed_relationship_types = (
            self._extract_schema_names(schema.get("relationship_types",{}))
        )

        if not self.allowed_entity_types:

            raise ValueError(
                "No entity types were found "
                "in schema_registry.json."
            )

        if not self.allowed_relationship_types:

            raise ValueError(
                "No relationship types were found "
                "in schema_registry.json."
            )

    @staticmethod
    def _extract_schema_names(schema_section) -> set:
        """
        Supports:

        ["Person", "Organization"]

        {
            "WORKS_AT": {...},
            "HEAD_OF": {...}
        }

        [
            {"name": "Person"},
            {"name": "Organization"}
        ]
        """

        names = set()

        """
        # for take entities name:
        "entity_types": [
        "Person",
        "Organization",
        "Location",
        ......
        """
        if isinstance(schema_section, dict):

            names.update(
                str(key)
                for key
                in schema_section.keys()
            )

            return names

        """
        for relationships: -> check schema_registary
        
        """
        if isinstance(schema_section,list):

            for item in schema_section:

                if isinstance(item, str):
                    names.add(item)

                elif isinstance(item, dict):

                    name = item.get("name")

                    if name:
                        names.add(str(name))

        return names

    # =========================================================
    # Property preparation
    # =========================================================

    @classmethod
    def _prepare_properties(cls, properties: Any, reserved_keys=None) -> dict:
        """
        Convert extracted properties into Neo4j-compatible
        property values.

        `evidence` requires no special handling.
        It is stored exactly like other string properties.
        """

        if properties is None:
            return {}

        if not isinstance(properties, dict):
            raise TypeError(
                "properties must be a dictionary."
            )

        reserved_keys = (reserved_keys or set())

        prepared = {}

        for raw_key, value in (properties.items()):

            key = str(raw_key)

            if key in reserved_keys:
                continue

            prepared_value = (cls._prepare_property_value(value))

            if (prepared_value is cls._SKIP):
                continue

            prepared[key] = prepared_value

        return prepared

    @classmethod
    def _prepare_property_value(cls, value: Any,):
        """
        Convert arbitrary JSON-compatible values into
        values that Neo4j can store as properties.
        """

        if value is None:
            return cls._SKIP

        # Scalars
        if isinstance(value,(str, bool,int,float)):
            return value

        # Nested map
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)

        # Lists
        if isinstance(value,list):

            if not value:
                return []

            # Lists containing null or complex values are
            # preserved as JSON rather than causing Neo4j
            # property errors.
            if any(item is None for item in value):
                return json.dumps(value, ensure_ascii=False,)

            if all(isinstance(item, str) 
                   for item in value):
                return value

            if all(isinstance(item, bool)
                   for item in value):
                return value

            if all(type(item) is int
                   for item in value):
                return value

            if all(
                type(item) in (int, float)
                for item in value):
                return [
                    float(item)
                    for item in value
                ]

            return json.dumps(value, ensure_ascii=False)

        # Defensive fallback
        return str(value)


















# ------------------------------------------------------------------
# import json
# from pathlib import Path
# from typing import Any


# class Neo4jGraphLoader:
#     """
#     Loads resolved relation-extraction data into Neo4j.

#     Expected input:
#         Output of EntityResolver.

#     Responsibilities:
#         - Validate basic graph structure
#         - Validate entity/relation types against schema_registry.json
#         - Create/update nodes
#         - Create/update relationships
#         - Preserve relationship evidence such as source_text
#         - Load one document atomically in a single transaction

#     Not responsible for:
#         - Entity Resolution
#         - Relation normalization
#         - Schema evolution
#         - Cross-document identity resolution
#     """

#     NODE_QUERY = """
#     MERGE (n {
#         document_id: $document_id,
#         entity_key: $entity_key
#     })

#     SET n:$($label)
#     SET n.name = $name
#     SET n += $properties

#     RETURN count(n) AS matched_count
#     """

#     RELATIONSHIP_QUERY = """
#     MATCH (source {
#         document_id: $document_id,
#         entity_key: $source_key
#     })

#     MATCH (target {
#         document_id: $document_id,
#         entity_key: $target_key
#     })

#     MERGE (source)-[r:$($relation_type)]->(target)

#     SET r += $properties

#     RETURN count(r) AS matched_count
#     """

#     NODE_RESERVED_PROPERTIES = {
#         "document_id",
#         "entity_key",
#         "name",
#     }

#     _SKIP = object()

#     def __init__(
#         self,
#         connection,
#         schema_path: str
#     ):
#         self.connection = connection
#         self.schema_path = Path(schema_path)

#         self.allowed_entity_types = set()
#         self.allowed_relationship_types = set()

#         self._reload_schema()

#     # ---------------------------------------------------------
#     # Public API
#     # ---------------------------------------------------------

#     def load_document(self, graph_data: dict) -> dict:
#         """
#         Validate and load one document into Neo4j.

#         All nodes and relationships of the document are written
#         in one transaction.

#         If any error occurs, the whole document is rolled back.
#         """

#         # Schema may have been changed by Schema Evolution,
#         # so refresh it before every document load.
#         self._reload_schema()

#         prepared_data = self._validate_and_prepare(graph_data)

#         database = self.connection.config.get(
#             "database",
#             "neo4j"
#         )

#         with self.connection.driver.session(
#             database=database
#         ) as session:

#             result = session.execute_write(
#                 self._write_document,
#                 prepared_data
#             )

#         return result

#     # ---------------------------------------------------------
#     # Transaction
#     # ---------------------------------------------------------

#     @classmethod
#     def _write_document(
#         cls,
#         tx,
#         graph_data: dict
#     ) -> dict:
#         """
#         Write the entire document inside one Neo4j transaction.
#         """

#         document_id = graph_data["document_id"]

#         entities = graph_data["entities"]
#         relationships = graph_data["relationships"]

#         # First create all nodes
#         for entity in entities:

#             result = tx.run(
#                 cls.NODE_QUERY,

#                 document_id=document_id,
#                 entity_key=entity["entity_key"],
#                 label=entity["type"],
#                 name=entity["name"],
#                 properties=entity["properties"],
#             )

#             record = result.single()

#             if (
#                 record is None
#                 or record["matched_count"] != 1
#             ):
#                 raise RuntimeError(
#                     "Unexpected node creation/match result for "
#                     f"entity_key={entity['entity_key']}"
#                 )

#         # Then create relationships
#         for relation in relationships:

#             result = tx.run(
#                 cls.RELATIONSHIP_QUERY,

#                 document_id=document_id,
#                 source_key=relation["source"],
#                 target_key=relation["target"],
#                 relation_type=relation["type"],
#                 properties=relation["properties"],
#             )

#             record = result.single()

#             if (
#                 record is None
#                 or record["matched_count"] != 1
#             ):
#                 raise RuntimeError(
#                     "Could not create relationship "
#                     f"{relation['source']} "
#                     f"-[{relation['type']}]-> "
#                     f"{relation['target']}"
#                 )

#         return {
#             "document_id": document_id,
#             "entities_processed": len(entities),
#             "relationships_processed": len(relationships),
#         }

#     # ---------------------------------------------------------
#     # Validation / preparation
#     # ---------------------------------------------------------

#     def _validate_and_prepare(
#         self,
#         graph_data: dict
#     ) -> dict:

#         if not isinstance(graph_data, dict):
#             raise TypeError(
#                 "graph_data must be a dictionary."
#             )

#         document_id = graph_data.get("document_id")

#         if (
#             not isinstance(document_id, str)
#             or not document_id.strip()
#         ):
#             raise ValueError(
#                 "document_id must be a non-empty string."
#             )

#         raw_entities = graph_data.get(
#             "entities",
#             []
#         )

#         raw_relationships = graph_data.get(
#             "relationships",
#             []
#         )

#         if not isinstance(raw_entities, list):
#             raise TypeError(
#                 "entities must be a list."
#             )

#         if not isinstance(raw_relationships, list):
#             raise TypeError(
#                 "relationships must be a list."
#             )

#         prepared_entities = []
#         entity_keys = set()

#         # ----------------------------
#         # Prepare entities
#         # ----------------------------

#         for entity in raw_entities:

#             if not isinstance(entity, dict):
#                 raise TypeError(
#                     "Each entity must be a dictionary."
#                 )

#             entity_key = entity.get(
#                 "entity_key"
#             )

#             name = entity.get(
#                 "name"
#             )

#             entity_type = entity.get(
#                 "type"
#             )

#             if (
#                 not isinstance(entity_key, str)
#                 or not entity_key.strip()
#             ):
#                 raise ValueError(
#                     "Every entity must have a valid entity_key."
#                 )

#             if entity_key in entity_keys:
#                 raise ValueError(
#                     f"Duplicate entity_key detected: "
#                     f"{entity_key}"
#                 )

#             if (
#                 not isinstance(name, str)
#                 or not name.strip()
#             ):
#                 raise ValueError(
#                     f"Entity {entity_key} "
#                     "must have a non-empty name."
#                 )

#             if entity_type not in self.allowed_entity_types:
#                 raise ValueError(
#                     f"Entity type '{entity_type}' "
#                     "is not defined in schema_registry.json."
#                 )

#             entity_keys.add(
#                 entity_key
#             )

#             properties = self._prepare_properties(
#                 entity.get(
#                     "properties",
#                     {}
#                 ),
#                 reserved_keys=
#                     self.NODE_RESERVED_PROPERTIES,
#             )

#             prepared_entities.append(
#                 {
#                     "entity_key": entity_key,
#                     "name": name,
#                     "type": entity_type,
#                     "properties": properties,
#                 }
#             )

#         # ----------------------------
#         # Prepare relationships
#         # ----------------------------

#         prepared_relationships = []

#         for relation in raw_relationships:

#             if not isinstance(relation, dict):
#                 raise TypeError(
#                     "Each relationship must be a dictionary."
#                 )

#             source = relation.get(
#                 "source"
#             )

#             target = relation.get(
#                 "target"
#             )

#             relation_type = relation.get(
#                 "type"
#             )

#             if source not in entity_keys:
#                 raise ValueError(
#                     f"Relationship source '{source}' "
#                     "does not exist in entities."
#                 )

#             if target not in entity_keys:
#                 raise ValueError(
#                     f"Relationship target '{target}' "
#                     "does not exist in entities."
#                 )

#             if (
#                 relation_type
#                 not in self.allowed_relationship_types
#             ):
#                 raise ValueError(
#                     f"Relationship type '{relation_type}' "
#                     "is not defined in schema_registry.json. "
#                     "Run Schema Evolution before loading "
#                     "this document."
#                 )

#             properties = self._prepare_properties(
#                 relation.get(
#                     "properties",
#                     {}
#                 )
#             )

#             prepared_relationships.append(
#                 {
#                     "source": source,
#                     "target": target,
#                     "type": relation_type,
#                     "properties": properties,
#                 }
#             )

#         return {
#             "document_id": document_id,
#             "entities": prepared_entities,
#             "relationships": prepared_relationships,
#         }

#     # ---------------------------------------------------------
#     # Schema
#     # ---------------------------------------------------------

#     def _reload_schema(self):
#         """
#         Reload schema_registry.json.

#         This is intentionally done before each document load,
#         because Schema Evolution may modify the registry.
#         """

#         if not self.schema_path.exists():
#             raise FileNotFoundError(
#                 f"Schema registry not found: "
#                 f"{self.schema_path}"
#             )

#         with self.schema_path.open(
#             "r",
#             encoding="utf-8"
#         ) as file:

#             schema = json.load(file)

#         self.allowed_entity_types = (
#             self._extract_schema_names(
#                 schema.get(
#                     "entity_types",
#                     []
#                 )
#             )
#         )

#         self.allowed_relationship_types = (
#             self._extract_schema_names(
#                 schema.get(
#                     "relationship_types",
#                     {}
#                 )
#             )
#         )

#         if not self.allowed_entity_types:
#             raise ValueError(
#                 "No entity types were found "
#                 "in schema_registry.json."
#             )

#         if not self.allowed_relationship_types:
#             raise ValueError(
#                 "No relationship types were found "
#                 "in schema_registry.json."
#             )

#     @staticmethod
#     def _extract_schema_names(
#         schema_section
#     ) -> set:
#         """
#         Support the common schema formats:

#         ["Person", "Organization"]

#         or

#         {
#             "Person": {...},
#             "Organization": {...}
#         }

#         or

#         [
#             {"name": "Person"},
#             {"name": "Organization"}
#         ]
#         """

#         names = set()

#         if isinstance(
#             schema_section,
#             dict
#         ):
#             names.update(
#                 str(key)
#                 for key
#                 in schema_section.keys()
#             )

#             return names

#         if isinstance(
#             schema_section,
#             list
#         ):

#             for item in schema_section:

#                 if isinstance(
#                     item,
#                     str
#                 ):
#                     names.add(
#                         item
#                     )

#                 elif isinstance(
#                     item,
#                     dict
#                 ):

#                     name = item.get(
#                         "name"
#                     )

#                     if name:
#                         names.add(
#                             str(name)
#                         )

#         return names

#     # ---------------------------------------------------------
#     # Neo4j property preparation
#     # ---------------------------------------------------------

#     @classmethod
#     def _prepare_properties(
#         cls,
#         properties: Any,
#         reserved_keys=None
#     ) -> dict:
#         """
#         Convert JSON-compatible values into values that Neo4j
#         can safely store as properties.

#         Nested dictionaries and unsupported lists are stored
#         as JSON strings instead of crashing the loader.
#         """

#         if properties is None:
#             return {}

#         if not isinstance(
#             properties,
#             dict
#         ):
#             raise TypeError(
#                 "properties must be a dictionary."
#             )

#         reserved_keys = (
#             reserved_keys
#             or set()
#         )

#         prepared = {}

#         for raw_key, value in properties.items():

#             key = str(raw_key)

#             # Prevent model-generated properties from
#             # overwriting Loader identity fields.
#             if key in reserved_keys:
#                 continue

#             prepared_value = (
#                 cls._prepare_property_value(
#                     value
#                 )
#             )

#             if prepared_value is cls._SKIP:
#                 continue

#             prepared[key] = prepared_value

#         return prepared

#     @classmethod
#     def _prepare_property_value(
#         cls,
#         value: Any
#     ):

#         # Neo4j SET with null removes properties.
#         # We do not want missing LLM values to accidentally
#         # delete existing values, so ignore them.
#         if value is None:
#             return cls._SKIP

#         # Standard scalar values
#         if isinstance(
#             value,
#             (
#                 str,
#                 bool,
#                 int,
#                 float
#             )
#         ):
#             return value

#         # Nested maps cannot be stored directly
#         # as Neo4j properties.
#         if isinstance(
#             value,
#             dict
#         ):
#             return json.dumps(
#                 value,
#                 ensure_ascii=False
#             )

#         if isinstance(
#             value,
#             list
#         ):

#             if not value:
#                 return []

#             # Lists containing null are not valid
#             # Neo4j property arrays.
#             if any(
#                 item is None
#                 for item in value
#             ):
#                 return json.dumps(
#                     value,
#                     ensure_ascii=False
#                 )

#             # Homogeneous string list
#             if all(
#                 isinstance(item, str)
#                 for item in value
#             ):
#                 return value

#             # Homogeneous boolean list
#             if all(
#                 isinstance(item, bool)
#                 for item in value
#             ):
#                 return value

#             # Homogeneous integer list
#             if all(
#                 type(item) is int
#                 for item in value
#             ):
#                 return value

#             # Numeric list:
#             # normalize int/float mixtures to float
#             if all(
#                 (
#                     type(item) is int
#                     or type(item) is float
#                 )
#                 for item in value
#             ):
#                 return [
#                     float(item)
#                     for item in value
#                 ]

#             # Complex/heterogeneous lists are preserved
#             # as JSON text.
#             return json.dumps(
#                 value,
#                 ensure_ascii=False
#             )

#         # Last-resort representation
#         return str(value)