import json
import uuid
from pathlib import Path


class RelationNormalizer:
    """
    Normalize LLM extraction output
    before Entity Resolution and Neo4j loading.
    """

    def __init__(self, schema_path: str):

        self.schema = self._load_schema(schema_path)

        self.allowed_relations = set(self.schema.get("relationship_types", {}).keys())
       


    def _load_schema(self, schema_path: str):

        path = Path(schema_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Schema not found: {schema_path}"
            )

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)



    def normalize(self, raw_data: dict, document_id: str) -> dict:
        """
        Main normalization pipeline.
        """

        entities = self._normalize_entities(raw_data.get("entities", []))

        relationships = self._normalize_relationships(raw_data.get("relationships", []))


        return {

            "document_id": document_id,

            "entities": entities,

            "relationships": relationships
        }



    def _normalize_entities(
        self,
        entities: list
    ) -> list:
        """
        Normalize entities without changing identity.
        LLM id is preserved as source_id.
        """

        normalized = []


        for entity in entities:


            source_id = entity.get("id")


            # اگر مدل ID تولید نکرد
            # یک شناسه موقت می‌سازیم تا پایپ لاین خراب نشود
            if not source_id:

                source_id = (
                    f"temp_"
                    f"{uuid.uuid4().hex[:8]}"
                )


            normalized.append({

                "source_id": source_id,


                "name":
                    entity.get("name",""),


                "type":entity.get("type","UNKNOWN"),


                "properties":entity.get("properties",{})
            })


        return normalized



    def _normalize_relationships(self,relationships: list) -> list:
        """
        Normalize relationships.
        Does not modify relation semantics.
        """

        normalized = []


        for relation in relationships:


            relation_type = relation.get("type","UNKNOWN")


            normalized.append({

                "source":
                    relation.get(
                        "source"
                    ),


                "target":
                    relation.get(
                        "target"
                    ),


                "type":
                    relation_type,


                # فقط بررسی می‌کنیم
                # Schema را تغییر نمی‌دهیم

                "schema_exists":
                    relation_type
                    in
                    self.allowed_relations,


                "properties":
                    relation.get(
                        "properties",
                        {}
                    )
            })


        return normalized

# import json
# from pathlib import Path
# from copy import deepcopy


# class RelationNormalizer:
#     """
#     Normalize LLM extraction output
#     before Entity Resolution and Neo4j loading.
#     """

#     def __init__(self, schema_path: str):

#         self.schema = self._load_schema(schema_path)

#         self.allowed_relations = set(self.schema.get("relationship_types", {}).keys())


#     def _load_schema(self, schema_path: str):

#         path = Path(schema_path)

#         if not path.exists():
#             raise FileNotFoundError(
#                 f"Schema not found: {schema_path}"
#             )

#         with open(path, "r", encoding="utf-8") as file:
#             return json.load(file)


#     def normalize(self, raw_data: dict, document_id: str) -> dict:

#         data = deepcopy(raw_data)


#         entities = self._normalize_entities(data.get("entities", []))


#         relationships = self._normalize_relationships(data.get("relationships", []))


#         return {

#             "document_id": document_id,

#             "entities": entities,

#             "relationships": relationships
#         }



#     def _normalize_entities(self, entities: list) -> list:


#         normalized = []


#         for entity in entities:


#             source_id = entity.get("id")



#             normalized.append({

#                 "source_id": source_id,

#                 "name": entity.get("name", ""),

#                 "type":entity.get("type", "UNKNOWN"),

#                 "properties": entity.get("properties", {})

#             })


#         return normalized



#     def _normalize_relationships(self,relationships: list) -> list:

#         normalized = []


#         for relation in relationships:

#             relation_type = relation.get("type","UNKNOWN")


#             normalized.append({

#                 "source":relation.get("source"),

#                 "target": relation.get("target"),

#                 "type":relation_type,



#                 "schema_exists": relation_type in self.allowed_relations,


#                 "properties": relation.get("properties", {})

#             })


#         return normalized
# import json
# from pathlib import Path
# from copy import deepcopy


# class RelationNormalizer:
#     """
#     Normalize LLM extraction output
#     before Entity Resolution and Neo4j loading.
#     """

#     def __init__(self, schema_path: str):

#         self.schema = self._load_schema(schema_path)

#         self.allowed_relations = set(
#             self.schema
#             .get("relationship_types", {})
#             .keys()
#         )


#     def _load_schema(self, schema_path: str):

#         path = Path(schema_path)

#         if not path.exists():
#             raise FileNotFoundError(
#                 f"Schema not found: {schema_path}"
#             )

#         with open(
#             path,
#             "r",
#             encoding="utf-8"
#         ) as file:
#             return json.load(file)


#     def normalize(
#         self,
#         raw_data: dict,
#         document_id: str
#     ) -> dict:


#         data = deepcopy(raw_data)


#         entities = self._normalize_entities(
#             data.get("entities", [])
#         )


#         relationships = self._normalize_relationships(
#             data.get("relationships", [])
#         )


#         return {

#             "document_id": document_id,

#             "entities": entities,

#             "relationships": relationships
#         }



#     def _normalize_entities(
#         self,
#         entities: list
#     ) -> list:


#         normalized = []


#         for entity in entities:


#             source_id = entity.get("id")


#             # اگر LLM اشتباهاً ID نداد
#             # فعلاً حذف نمی‌کنیم، فقط علامت می‌زنیم

#             normalized.append({

#                 "source_id": source_id,

#                 "name":
#                     entity.get(
#                         "name",
#                         ""
#                     ),

#                 "type":
#                     entity.get(
#                         "type",
#                         "UNKNOWN"
#                     ),

#                 "properties":
#                     entity.get(
#                         "properties",
#                         {}
#                     )

#             })


#         return normalized



#     def _normalize_relationships(
#         self,
#         relationships: list
#     ) -> list:


#         normalized = []


#         for relation in relationships:


#             relation_type = relation.get(
#                 "type",
#                 "UNKNOWN"
#             )


#             normalized.append({

#                 "source":
#                     relation.get(
#                         "source"
#                     ),

#                 "target":
#                     relation.get(
#                         "target"
#                     ),

#                 "type":
#                     relation_type,


#                 # فقط گزارش
#                 # در این مرحله Schema تغییر نمی‌کند

#                 "schema_exists":
#                     relation_type
#                     in
#                     self.allowed_relations,


#                 "properties":
#                     relation.get(
#                         "properties",
#                         {}
#                     )

#             })


#         return normalized