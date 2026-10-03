# ------------ version3 ----------
import json
import logging
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable


logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "neo4j_config.json"


class Neo4jConnection:
    """
    Manages the Neo4j driver and database connection.
    """

    REQUIRED_CONFIG_KEYS = {
        "uri",
        "username",
        "password",
    }

    def __init__(self, config_path=CONFIG_PATH):
        self.config = self._load_config(config_path)

        self.driver = GraphDatabase.driver(
            self.config["uri"],
            auth=(
                self.config["username"],
                self.config["password"],
            ),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type,exc_value,traceback):
        self.close()

    @classmethod
    def _load_config(cls, config_path):
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}"
            )

        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        missing_keys = (cls.REQUIRED_CONFIG_KEYS- config.keys())

        if missing_keys:
            raise ValueError(
                "Missing required Neo4j configuration "
                f"keys: {sorted(missing_keys)}"
            )

        return config

    def verify_connection(self) -> bool:
        """
        Verify connectivity to the configured Neo4j database.
        """

        try:
            database = self.config.get(
                "database",
                "neo4j",
            )

            with self.driver.session(database=database) as session:

                result = session.run("RETURN 1 AS result")

                record = result.single()

                return (
                    record is not None
                    and record["result"] == 1
                )

        except AuthError:
            logger.error(
                "Authentication to Neo4j failed. "
                "Check username/password."
            )
            return False

        except ServiceUnavailable:
            logger.error(
                "Neo4j database is unavailable. "
                "Check whether the instance is running."
            )
            return False

        except Exception:
            logger.exception(
                "Unexpected error while connecting "
                "to Neo4j."
            )
            return False

    def close(self):
        if self.driver is not None:
            self.driver.close()
            self.driver = None


            
# # ----------------------- version2 ---------------------------
# import json
# import logging
# from pathlib import Path
# from neo4j import GraphDatabase, exceptions

# # تنظیم لاگر برای چاپ خطاهای دیتابیس
# logger = logging.getLogger(__name__)

# PROJECT_ROOT = Path(__file__).resolve().parent.parent
# CONFIG_PATH = PROJECT_ROOT / "config" / "neo4j_config.json"

# class Neo4jConnection:
#     """
#     Neo4j connection manager.
#     """

#     def __init__(self, config_path=CONFIG_PATH):
#         self.config = self._load_config(config_path)
#         self.driver = GraphDatabase.driver(
#             self.config["uri"],
#             auth=(
#                 self.config["username"],
#                 self.config["password"]
#             )
#         )

#     # پشتیبانی از بلوک with
#     def __enter__(self):
#         return self

#     # بسته شدن خودکار در پایان بلوک with
#     def __exit__(self, exc_type, exc_value, traceback):
#         self.close()

#     def _load_config(self, config_path=CONFIG_PATH):
#         path = Path(config_path)
#         if not path.exists():
#             raise FileNotFoundError(
#                 f"Config file not found: {config_path}"
#             )
#         with open(path, "r", encoding="utf-8") as file:
#             return json.load(file)

#     def verify_connection(self) -> bool:
#         """
#         Check Neo4j availability safely.
#         """
#         try:
#             with self.driver.session(database=self.config.get("database", "neo4j")) as session:
#                 result = session.run("RETURN 1 AS result")
#                 record = result.single()
#                 return record["result"] == 1
                
#         except exceptions.AuthError:
#             logger.error("Authentication to Neo4j failed. Check username/password.")
#             return False
#         except exceptions.ServiceUnavailable:
#             logger.error("Neo4j database is unavailable. Is it running?")
#             return False
#         except Exception as e:
#             logger.error(f"Unexpected error connecting to Neo4j: {e}")
#             return False

#     def close(self):
#         if self.driver:
#             self.driver.close()

# # ------------------- version1 ------------------
# import json
# from pathlib import Path

# from neo4j import GraphDatabase


# PROJECT_ROOT = Path(__file__).resolve().parent.parent

# CONFIG_PATH = (
#     PROJECT_ROOT
#     / "config"
#     / "neo4j_config.json"
# )


# class Neo4jConnection:
#     """
#     Neo4j connection manager.
#     """

#     # read json config
#     # bulding driver Object
#     def __init__(self, config_path = CONFIG_PATH):

#         self.config = self._load_config(config_path)

#         self.driver = GraphDatabase.driver(
#             self.config["uri"],
#             auth=(
#                 self.config["username"],
#                 self.config["password"]
#             )
#         )


#     # load & read config
#     def _load_config(self,config_path = CONFIG_PATH):

#         path = Path(config_path)

#         if not path.exists():

#             raise FileNotFoundError(
#                 f"Config file not found: {config_path}"
#             )


#         with open(path, "r", encoding="utf-8") as file:

#             return json.load(file)



#     def verify_connection(self):

#         """
#         Check Neo4j availability.
#         """

#         with self.driver.session(database=self.config["database"]) as session:


#             result = session.run("RETURN 1 AS result")


#             record = result.single()


#             return record["result"] == 1



#     def close(self):

#         self.driver.close()




