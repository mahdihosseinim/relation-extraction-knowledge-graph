# ----- version2 -------
from copy import deepcopy

from .persian_normalizer import PersianEntityNormalizer


class EntityResolver:
    """
    MVP Entity Resolver.

    Strategy:
        Persian normalization
        +
        Exact match (normalized name + type)

    Responsibilities:
        - Merge duplicate entities
        - Merge entity properties
        - Convert relationship endpoints
          from source_id to entity_key
    """

    def __init__(self):
        self.normalizer = PersianEntityNormalizer()


    def resolve(self, data: dict) -> dict:

        entities = data.get("entities",[])

        relationships = data.get("relationships",[])

        # key:
        # (normalized_name, entity_type)
        #
        # value:
        # resolved entity
        entity_groups = {}

        # Maps LLM source_id -> resolved entity_key
        source_to_entity = {}

        entity_counter = 1


        # =====================================================
        # Entity Resolution
        # =====================================================

        for entity in entities:

            normalized_name = (self.normalizer.normalize(entity.get("name","")))

            entity_type = entity.get("type","UNKNOWN")

            key = (normalized_name,entity_type)


            # -----------------------------------------------
            # New resolved entity
            # -----------------------------------------------

            if key not in entity_groups:

                entity_key = (f"entity_{entity_counter}")

                entity_counter += 1

                entity_groups[key] = {

                    "entity_key": entity_key,

                    "source_ids": [],

                    "name": entity.get("name",""),

                    "type": entity_type,

                    "properties": {}
                }


            current_entity = (entity_groups[key])


            # -----------------------------------------------
            # Keep source IDs for internal resolution/debug.
            #
            # GraphLoader does NOT store source_ids in Neo4j.
            # -----------------------------------------------

            current_entity["source_ids"].append(entity.get("source_id"))


            # -----------------------------------------------
            # Merge properties
            # -----------------------------------------------

            self._merge_properties(current_entity["properties"], 
                                   entity.get("properties",{}))


            # -----------------------------------------------
            # source_id -> entity_key
            # -----------------------------------------------

            source_to_entity[entity.get("source_id")] = current_entity["entity_key"]


        resolved_entities = list(entity_groups.values())


        # =====================================================
        # Relationship endpoint resolution
        # =====================================================

        resolved_relationships = []

        for relation in relationships:

            resolved_relationships.append(
                {

                    "source":source_to_entity.get(relation.get("source"),
                                                  relation.get("source")),

                    "target":
                        source_to_entity.get(
                            relation.get("target"),
                            relation.get("target")
                        ),

                    "type":
                        relation.get("type"),

                    # Defensive copy:
                    # Resolver must not mutate
                    # Normalizer output.
                    "properties":
                        deepcopy(relation.get("properties",{}))
                }
            )


        return {

            "document_id": data.get("document_id"),

            "entities": resolved_entities,

            "relationships": resolved_relationships
        }


    # =========================================================
    # Property merging
    # =========================================================

    @staticmethod
    def _merge_properties(target: dict, source: dict):
        """
        Merge entity properties without losing values.

        Examples:

        aliases:
            ["دکتر سهرابی", "خود او"]
            +
            ["سهرابی"]

        becomes:

            ["دکتر سهرابی", "خود او", "سهرابی"]


        role:
            "مدیرعامل"
            +
            "مشاور"

        becomes:

            ["مدیرعامل", "مشاور"]
        """

        for key, value in source.items():

            # -----------------------------------------------
            # Property does not exist yet
            # -----------------------------------------------

            if key not in target:

                target[key] = deepcopy(value)
                continue

            existing = target[key]


            # -----------------------------------------------
            # Same value -> nothing to do
            # -----------------------------------------------

            if existing == value:
                continue


            # -----------------------------------------------
            # Normalize both sides into lists
            # -----------------------------------------------

            existing_values = (
                existing
                if isinstance(existing,list)
                else [existing]
            )

            new_values = (
                value
                if isinstance(value,list)
                else [value]
            )


            # -----------------------------------------------
            # Flat unique merge
            # -----------------------------------------------

            merged_values = []

            for item in (existing_values+ new_values):

                if item not in merged_values:

                    merged_values.append(deepcopy(item))

            target[key] = (merged_values)



## ----------- version1 ---------
# from persian_normalizer import PersianEntityNormalizer


# class EntityResolver:
#     """
#     MVP Entity Resolver

#     Strategy:
#     Persian normalization
#     +
#     Exact match (name + type)

#     Handles:
#     - duplicate entities
#     - property merging
#     - relationship updating
#     """


#     def __init__(self):

#         self.normalizer = PersianEntityNormalizer()



#     def resolve(self, data: dict) -> dict:

#         entities = data.get("entities",[])

#         relationships = data.get("relationships", [])

#         entity_groups = {}      # موجودیت های ادغام شده 
#         source_to_entity = {}   # mapp list for old_entity -> new_entity
#         entity_counter = 1      # counter for new entity


#         # -----------------------------
#         # Entity Deduplication    -> بر اساس: ("name", "type")
#         # -----------------------------
#         for entity in entities:

#             normalized_name = (self.normalizer.normalize(entity.get("name", "")))

#             entity_type = entity.get("type", "UNKNOWN")
#             # entity_type = (self.normalizer.normalize(entity.get("name", "")))

#             key = (normalized_name, entity_type)

#             # اگر موجودیت با این نام و نوع قبلاً وجود نداشت، یک گروه جدید بسازیم
#             # ورگرنه از این حلقع رد شده و باید با گروه های قبلی ادغام شود
#             if key not in entity_groups:

#                 entity_key = (f"entity_{entity_counter}")

#                 entity_counter += 1

#                 entity_groups[key] = {

#                     "entity_key": entity_key,

#                     "source_ids": [],

#                     "name":entity.get("name", ""),

#                     "type": entity_type,

#                     "properties": {}

#                 }

#             current_entity = entity_groups[key]


#             # saving source_id into the current entity structure
#             current_entity["source_ids"].append(entity.get("source_id"))


#             # merging properties
#             self._merge_properties(current_entity["properties"], entity.get("properties",{}))


#             # Mapping
#             source_to_entity[entity.get("source_id")] = current_entity["entity_key"]



#         # dict -> list

#         resolved_entities = list(entity_groups.values())


#         # -----------------------------
#         # Update Relationships
#         # -----------------------------
#         resolved_relationships = []

#         for relation in relationships:
#             resolved_relationships.append({

#                 "source":
#                     source_to_entity.get(
#                         relation.get("source"),
#                         relation.get("source")
#                     ),


#                 "target":
#                     source_to_entity.get(relation.get("target"),relation.get("target")),


#                 "type":
#                     relation.get("type"),


#                 "properties":
#                     relation.get("properties",{})

#             })



#         return {

#             "document_id":
#                 data.get("document_id"),


#             # "schema_version":
#             #     data.get(
#             #         "schema_version",
#             #         "1.0"
#             #     ),


#             "entities":
#                 resolved_entities,


#             "relationships":
#                 resolved_relationships

#         }



#     def _merge_properties(self,target: dict,source: dict):
#         """
#         Merge properties without losing information.
#         """

#         for key, value in source.items():

#             if key not in target:
#                 target[key] = value



#             else:
#                 existing = target[key]

#                 # مقدار مشابه
#                 if existing == value:
#                     continue

#                 # اگر قبلا لیست بود

#                 if isinstance(existing, list):
#                     if value not in existing:
#                         existing.append(value)

#                 else:
#                     target[key] = [existing,value]