import json
from pathlib import Path

from google import genai


PROJECT_ROOT = Path(__file__).resolve().parent

CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "text2cypher_config.json"
)


with CONFIG_PATH.open(
    "r",
    encoding="utf-8"
) as file:

    config = json.load(file)


client = genai.Client(
    api_key=config["api_key"]
)


response = client.models.generate_content(
    model=config["primary_model"],
    contents="فقط بنویس: اتصال موفق است"
)


print(response.text)