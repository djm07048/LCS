import os
from utils.path import *

KICE_DB_PATH = r'T:\THedu\KiceDB'
ITEM_DB_PATH = r'T:\THedu\ItemDB'
NICE_DB_PATH = r'T:\THedu\NiceDB'

MONTH_DICT = {"01": "예비시행", "06": "6월", "09": "9월", "11": "대수능", "03": "3월", "04": "4월", "07": "7월", "10": "10월"}
MONTH_REV_DICT = {v: k for k, v in MONTH_DICT.items()}
SUBJECT_DICT = {"E1": "지1", "E2": "지2", "C1": "화1", "C2": "화2", "P1": "물1", "P2": "물2", "B1": "생1", "B2": "생2", "XS": "통과"}
SUBJECT_REV_DICT = {v: k for k, v in SUBJECT_DICT.items()}

SECTION_DICT = {"01": "KC", "06": "KC", "09": "KC", "11": "KC", "03": "NC", "04": "NC", "07": "NC", "10": "NC"}


@staticmethod
def parse_code(code: str) -> list:
    parsed_code = {"subject" : "E1",
                   "topic" : "zzz",
                   "section" : "ZG",
                   "number" : "999999"}
    parsed_code["subject"] = code[0:2]
    parsed_code["topic"] = code[2:5]
    parsed_code["section"] = code[5:7]
    parsed_code["number"] = code[7:13]
    return parsed_code
@staticmethod
def code2cite(code: str) -> str:
    parsed_code = parse_code(code)
    yyyy = "20" + str(parsed_code["number"][0:2])
    mo = MONTH_DICT[parsed_code["number"][2:4]]
    nn = int(parsed_code["number"][4:])
    subject = SUBJECT_DICT[parsed_code["subject"]]
    return f"{yyyy}학년도 {mo} {nn}번 {subject}"

@staticmethod
def cite2code(citation: str, topic: str) -> str:
    parsed_citation = citation.split(" ")
    yy = parsed_citation[0][2:4]
    mo = MONTH_REV_DICT[parsed_citation[1]]
    nn = parsed_citation[2][:-2]
    subject = SUBJECT_REV_DICT[parsed_citation[3]]

    return f"{subject}{topic}{yy}{mo}{int(nn):02d}"

@staticmethod
def code2folder(item_code: str) -> str:
    parsed = parse_code(item_code)
    if parsed["section"] == "KC":
        base_path= KICE_DB_PATH
    elif parsed["section"] == "NC":
        base_path= NICE_DB_PATH
    else:
        base_path= ITEM_DB_PATH

    return rf"{base_path}\{parsed['topic']}\{item_code}"

@staticmethod
def code2pdf(code: str) -> str:
    return os.path.join(code2folder(code), f"{code}.pdf")

@staticmethod
def code2caption(code: str) -> str:
    return os.path.join(code2folder(code), f"{code}_caption.pdf")

@staticmethod
def code2original(code: str) -> str:
    return os.path.join(code2folder(code), f"{code}_original.pdf")

@staticmethod
def code2Main(code: str) -> str:
    return os.path.join(code2folder(code), f"{code}_Main.pdf")

@staticmethod
def code2modified(code: str) -> str:
    return os.path.join(code2folder(code), f"{code}_modified.pdf")