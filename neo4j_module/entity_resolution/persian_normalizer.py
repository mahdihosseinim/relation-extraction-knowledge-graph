import re

import persian


class PersianEntityNormalizer:
    """
    Persian entity-name normalizer.

    Public contract remains unchanged:
        str -> str
    """

    def normalize(self,text: str,) -> str:

        if (
            not isinstance(text, str)
            or not text.strip()
        ):
            return ""

        # Persian library normalization:
        # - Arabic/Persian character normalization
        # - Persian digits
        # - Persian spacing normalization
        text = persian.normalize_persian(text)

        # EntityResolver currently expects
        # half-space and normal space variations
        # to resolve to the same representation.
        text = text.replace("\u200c"," ")

        # Latin aliases/names should compare
        # case-insensitively.
        text = text.lower()

        #  حذف اعراب 
        text = re.sub(r'[\u064B-\u065F]', '', text)

        # حذف کشیدگی حروف (Tatweel)
        text = text.replace("\u0640", "")

        # یکسان‌سازی الف و همزه 
        text = text.replace("آ", "ا")
        text = text.replace("أ", "ا")
        text = text.replace("إ", "ا")
        text = text.replace("ؤ", "و")
        text = text.replace("ئ", "ی")
        text = text.replace("ة", "ه")

        # حذف علائم نگارشی
        text = re.sub(r'[!,.،؛:؟\-\(\)\[\]{}]', ' ', text)

        # پاکسازی نهایی فواصل (حذف فواصل متوالی و فواصل ابتدا/انتها)
        text = re.sub(r"\s+", " ", text).strip()

        return text



# ------v1: hazme hs dependancy
# from hazm import Normalizer
# import re


# class PersianEntityNormalizer:
#     """
#     Persian text normalization
#     for Entity Resolution.
#     """

#     def __init__(self):

#         self.normalizer = Normalizer()


#     def normalize(self, text: str) -> str:
#         """
#         Normalize Persian entity names.
#         """

#         if not text:
#             return ""


#         # Hazm normalization
#         text = self.normalizer.normalize(text)


#         # یکسان سازی ی و ک عربی
#         text = text.replace("ي", "ی")
#         text = text.replace("ك", "ک")


#         # حذف نیم فاصله
#         text = text.replace("\u200c", " ")

#         # تبدیل به حروف کوچک کلمات موجودیت انگلیسی
#         text = text.lower()

#         # حذف فاصله‌های اضافی
#         text = re.sub(r"\s+"," ", text)


#         # حذف فاصله ابتدا و انتها
#         text = text.strip()


#         return text