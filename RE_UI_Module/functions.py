import os
import requests
import pandas as pd
import json
import time
from hazm import Normalizer

from google import genai
from google.genai import types
from prompt import re_prompt



RESPONSE_FILE = "response.json"


os.environ.setdefault("NO_PROXY", "localhost,***.0.0.*")
os.environ.setdefault("no_proxy", "localhost,***.0.0.*")



GEMINI_API_KEY = "GEMINI_API_KEY"

NEO4J_SERVICE_URL = "http://***.***.**.***:8000/ingest"

# آدرس سرویس پرسش‌وپاسخِ روی لپ‌تاپ هم‌تیمی (که سؤال را می‌گیرد،
# روی Neo4j کوئری Cypher می‌زند و پاسخ را برمی‌گرداند).
QA_SERVICE_URL = "http://***.***.**.***:8000/query"


def ask_question_service(question: str) -> dict:
    """
    سؤال کاربر را به‌صورت {"question": "..."} برای سرویس پرسش‌وپاسخ
    هم‌تیمی می‌فرستد و کل پاسخ JSON برگشتی (شامل answer, cypher,
    attempts, rows, evidence, errors, truncated) را برمی‌گرداند.
    """

    # trust_env=False یعنی پروکسی سیستم نادیده گرفته می‌شود
    # و درخواست مستقیم از طریق وای‌فای به سرور هم‌تیمی می‌رود
    session = requests.Session()
    session.trust_env = False

    try:
        response = session.post(
            QA_SERVICE_URL,
            json={"question": question},
            timeout=30,
            allow_redirects=False,  # دلیل در send_to_neo4j_service توضیح داده شده
        )

        if response.is_redirect or response.status_code in (301, 302, 307, 308):
            raise RuntimeError(
                f"Q&A service redirected the request "
                f"({response.status_code}) to "
                f"{response.headers.get('Location')}. "
                f"آدرس QA_SERVICE_URL را با مسیر دقیق سرویس چک کن."
            )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to the Q&A service.")

    except requests.exceptions.Timeout:
        raise RuntimeError("Q&A service request timed out.")

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Q&A service returned "
            f"{response.status_code}: {response.text}"
        ) from exc

    finally:
        session.close()


def extract_answer_text(result: dict) -> str:
    """
    متن قابل‌نمایش پاسخ را از JSON برگشتی سرویس پرسش‌وپاسخ استخراج
    می‌کند. فرض اصلی این است که فیلد اصلی "answer" نام دارد؛ اگر نبود
    چند نام رایج دیگر را هم امتحان می‌کند تا چیزی گم نشود.
    """

    if not isinstance(result, dict):
        return str(result)

    for key in ("answer", "response", "result", "text"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value

    # اگر هیچ‌کدام از نام‌های رایج پیدا نشد، کل پاسخ خام را نشان بده
    # تا دست‌کم چیزی گم نشود (و بشه بعداً اسم فیلد درست رو فهمید).
    return json.dumps(result, ensure_ascii=False, indent=2)


def send_to_neo4j_service(extraction_result: dict) -> dict:
    # trust_env=False یعنی پروکسی سیستم نادیده گرفته می‌شود
    # و درخواست مستقیم از طریق وای‌فای به سرور هم‌تیمی می‌رود
    session = requests.Session()
    session.trust_env = False

    try:
        response = session.post(
            NEO4J_SERVICE_URL,
            json=extraction_result,
            timeout=30,
            # مهم: اگر این False نباشد و سرور یک ریدایرکت (مثلاً ۳۰۷
            # به‌خاطر فرق "/" در انتهای مسیر، که رفتار پیش‌فرض خیلی از
            # فریم‌ورک‌هاست مثل FastAPI) برگرداند، requests بی‌صدا یک
            # درخواست POST دومِ واقعی هم می‌فرستد تا ریدایرکت را دنبال
            # کند؛ یعنی سرور هم‌تیمی برای یک ارسال منطقی، دو درخواست
            # واقعی می‌بیند. با غیرفعال‌کردنش، به‌جای ارسال پنهانیِ
            # دوباره، خطای واضح می‌گیریم.
            allow_redirects=False,
        )

        if response.is_redirect or response.status_code in (301, 302, 307, 308):
            raise RuntimeError(
                f"Neo4j service redirected the request "
                f"({response.status_code}) to "
                f"{response.headers.get('Location')}. "
                f"آدرس NEO4J_SERVICE_URL را با مسیر دقیق سرویس "
                f"هم‌تیمی (با/بدون '/' در انتها) چک کن."
            )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to Neo4j service.")

    except requests.exceptions.Timeout:
        raise RuntimeError("Neo4j service request timed out.")

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Neo4j service returned "
            f"{response.status_code}: {response.text}"
        ) from exc

    finally:
        session.close()

def send_request_to_api(text, max_retries=3):


    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(
            client_args={
                "proxy": "socks5://127.0.0.1:10808"
            },
            async_client_args={
                "proxy": "socks5://127.0.0.1:10808"
            }
        )
    )

    full_prompt = re_prompt + text



    try:
        for attempt in range(1, max_retries + 1):

            try:

                print(f"API request: attempt {attempt}/{max_retries}")

                response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=full_prompt
                )

                # ==================================================
                # تبدیل پاسخ API به JSON
                # ==================================================

                data = json.loads(response.text)

                new_entities = data.get("entities", [])
                new_relationships = data.get("relationships", [])

                # ==================================================
                # خواندن response.json قبلی
                # ==================================================

                try:

                    with open(
                        RESPONSE_FILE,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        saved_data = json.load(f)

                except (FileNotFoundError, json.JSONDecodeError):

                    saved_data = {
                        "entities": [],
                        "relationships": []
                    }

                # ==================================================
                # اگر ساختار فایل درست نبود
                # ==================================================

                if not isinstance(saved_data, dict):

                    saved_data = {
                        "entities": [],
                        "relationships": []
                    }

                saved_data.setdefault("entities", [])
                saved_data.setdefault("relationships", [])

                # ==================================================
                # اضافه کردن موجودیت‌های جدید
                # ==================================================

                existing_entity_ids = {
                    entity["id"]
                    for entity in saved_data["entities"]
                    if "id" in entity
                }

                added_entities = 0

                for entity in new_entities:

                    entity_id = entity.get("id")

                    if entity_id not in existing_entity_ids:

                        saved_data["entities"].append(entity)

                        existing_entity_ids.add(entity_id)

                        added_entities += 1

                # ==================================================
                # اضافه کردن روابط جدید
                # ==================================================

                existing_relationships = {
                    (
                        relation.get("source"),
                        relation.get("target"),
                        relation.get("type")
                    )
                    for relation in saved_data["relationships"]
                }

                added_relationships = 0

                for relation in new_relationships:

                    relation_key = (
                        relation.get("source"),
                        relation.get("target"),
                        relation.get("type")
                    )

                    if relation_key not in existing_relationships:

                        saved_data["relationships"].append(relation)

                        existing_relationships.add(
                            relation_key
                        )

                        added_relationships += 1

                # ==================================================
                # ذخیره فایل
                # ==================================================

                with open(
                    RESPONSE_FILE,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        saved_data,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

                print(
                    f"Added entities: {added_entities}"
                )

                print(
                    f"Added relationships: {added_relationships}"
                )

                print(
                    "Response successfully updated."
                )

                # خروجی همین درخواست را برمی‌گردانیم
                return data

            # ======================================================
            # مدیریت خطا
            # ======================================================

            except Exception as e:

                print(
                    f"Error in API request "
                    f"(attempt {attempt}/{max_retries}): {e}"
                )

                if attempt < max_retries:

                    print("Retrying in 2 seconds...")

                    time.sleep(2)

                else:

                    print(
                        "Maximum retry attempts reached."
                    )

                    return None

    finally:
        # همیشه کانکشن SOCKS/HTTP باز شده توسط genai.Client را می‌بندیم
        # تا در تماس‌های بعدی به Ollama محلی تداخلی ایجاد نشود.
        try:
            client.close()
        except Exception as close_error:
            print(f"Warning: failed to close genai client cleanly: {close_error}")


def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """
    متن طولانی را بر اساس مرز پاراگراف‌ها (خط خالی) به چند batch
    کوچک‌تر تقسیم می‌کند تا وسط جمله‌ها بریده نشود و هر batch در
    اندازه‌ی مناسبی برای ارسال به Gemini بماند.

    اگر خودِ متن کوتاه‌تر از max_chars باشد، فقط یک batch برمی‌گردد.
    """

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        return []

    batches: list[str] = []
    current_batch = ""

    for paragraph in paragraphs:

        # اگر خودِ یک پاراگراف به‌تنهایی از max_chars بزرگ‌تر بود
        # (نادر)، آن را به‌عنوان یک batch جداگانه قرار می‌دهیم تا
        # گم نشود.
        if len(paragraph) > max_chars:

            if current_batch:
                batches.append(current_batch.strip())
                current_batch = ""

            batches.append(paragraph.strip())
            continue

        if current_batch and len(current_batch) + len(paragraph) + 2 > max_chars:
            batches.append(current_batch.strip())
            current_batch = paragraph
        else:
            current_batch = (
                f"{current_batch}\n\n{paragraph}" if current_batch else paragraph
            )

    if current_batch:
        batches.append(current_batch.strip())

    return batches


def _build_dataframes(entities: list[dict], relationships: list[dict]):
    """
    از فهرست موجودیت‌ها و روابط (که می‌تواند حاصل تجمیع چند batch
    باشد)، دو DataFrame برای نمایش در رابط کاربری می‌سازد.
    """

    # ==========================================================
    # جدول موجودیت‌ها
    # ==========================================================

    entity_rows = []

    for entity in entities:

        row = {
            "ID": entity["id"],
            "نام": entity["name"],
            "نوع": entity["type"],
        }

        # اضافه کردن properties
        for key, value in entity.get(
            "properties",
            {}
        ).items():

            row[key] = value

        entity_rows.append(row)

    df_entities = pd.DataFrame(entity_rows)

    # ==========================================================
    # ساخت دیکشنری ID → Entity
    # ==========================================================

    entity_dict = {
        entity["id"]: entity
        for entity in entities
    }

    # ==========================================================
    # جدول روابط
    # ==========================================================

    relation_rows = []

    for relation in relationships:

        source = entity_dict.get(
            relation["source"],
            {}
        )

        target = entity_dict.get(
            relation["target"],
            {}
        )

        relation_rows.append({
            "From": source.get("name", ""),
            "From ID": relation["source"],
            "To": target.get("name", ""),
            "To ID": relation["target"],
            "Relation": relation["type"]
        })

    df_relations = pd.DataFrame(
        relation_rows
    )

    return df_entities, df_relations


def display_response(text, on_progress=None):
    """
    متن ورودی (حتی طولانی) را به چند batch تقسیم می‌کند و هر batch را
    جداگانه برای استخراج موجودیت/رابطه به Gemini می‌فرستد. هر batch
    همان‌طور که تا الان بود در response.json ذخیره/merge می‌شود.

    فقط بعد از پردازش کامل همه‌ی batch‌ها:
      - کل موجودیت‌ها/روابط تازه‌استخراج‌شده (از همه‌ی batch‌ها با هم)
        یک‌جا برای سرویس Neo4j هم‌تیمی ارسال می‌شود.
      - دو DataFrame برای نمایش در رابط کاربری برگردانده می‌شود.

    on_progress (اختیاری): تابعی به شکل on_progress(current, total)
    که درست قبل از شروع پردازش هر batch صدا زده می‌شود تا رابط کاربری
    بتواند «batch X از Y» را نشان دهد.
    """

    batches = chunk_text(text)
    total_batches = len(batches)

    if total_batches == 0:
        return None, None

    all_entities = []
    all_relationships = []

    for index, batch_text in enumerate(batches, start=1):

        if on_progress:
            on_progress(index, total_batches)

        print(f"Processing batch {index}/{total_batches}...")

        batch_data = send_request_to_api(batch_text)

        # اگر این batch بعد از همه‌ی retry ها شکست خورد، آن را رد کن
        # و بقیه‌ی batch‌ها را ادامه بده (یک batch خراب نباید کل متن
        # طولانی را از دست بدهد).
        if batch_data is None:
            print(
                f"Warning: batch {index}/{total_batches} "
                f"failed after retries and was skipped."
            )
            continue

        all_entities.extend(batch_data.get("entities", []))
        all_relationships.extend(batch_data.get("relationships", []))

    # اگر هیچ batch ای موفق نشد
    if not all_entities and not all_relationships:
        return None, None

    combined_result = {
        "entities": all_entities,
        "relationships": all_relationships,
    }

    # ==========================================================
    # ارسال یک‌جا به سرویس Neo4j هم‌تیمی، فقط بعد از پایان همه‌ی
    # batch‌ها (نه بعد از هر batch)
    # ==========================================================

    try:
        result = send_to_neo4j_service(combined_result)
        print("Neo4j service response:", result)
    except RuntimeError as e:
        print(f"Failed to send to Neo4j: {e}")

    return _build_dataframes(all_entities, all_relationships)

normalizer = Normalizer(
    correct_spacing=True,
    remove_diacritics=True,
    remove_specials_chars=False,
    persian_style=True,
    persian_numbers=False,
    unicodes_replacement=True,
    seperate_mi=True
)

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = normalizer.normalize(text)

    return text