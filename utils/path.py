import os
from utils.path import *

KICE_DB_PATH = r'T:\THedu\KiceDB'
ITEM_DB_PATH = r'T:\THedu\ItemDB'
NICE_DB_PATH = r'T:\THedu\NiceDB'

RESOURCES_PATH = r'T:\Software\LCS\resources'
TEMPORARY_PATH = r'T:\Software\LCS\temporary'

INPUT_PATH = r'T:\Software\LCS\input'
OUTPUT_PATH = r'T:\Software\LCS\output'
BOOK_DB_PATH = r'T:\Software\LCS\input\BookDB'
EXAM_DB_PATH = r'T:\Software\LCS\input\ExamDB'
HISTORY_DB_PATH = r'T:\Software\LCS\input\HistoryDB'


MONTH_DICT = {"01": "예비시행", "06": "6월", "09": "9월", "11": "대수능", "03": "3월", "04": "4월", "05": "5월", "07": "7월", "10": "10월"}
MONTH_REV_DICT = {v: k for k, v in MONTH_DICT.items()}

SDCONT_DICT = {"SV": "시대인재 서바이벌", "SZ": "시대인재 서바이벌전국", "BR": "시대인재 브릿지", "BZ": "시대인재 브릿지전국",
               "WL": "시대인재 수능모의평가", "SN": "시대인재 서바이벌N", "ZG": "정태혁 모의고사"}
SDCONT_REV_DICT = {v: k for k, v in SDCONT_DICT.items()}

SUBJECT_DICT = {"E1": "지1", "E2": "지2", "C1": "화1", "C2": "화2", "P1": "물1", "P2": "물2", "B1": "생1", "B2": "생2", "XS": "통과"}
SUBJECT_REV_DICT = {v: k for k, v in SUBJECT_DICT.items()}

SECTION_DICT = {"01": "KC", "06": "KC", "09": "KC", "11": "KC", "03": "NC", "04": "NC", "05": "NC", "07": "NC", "10": "NC"}

def get_item_path(item_code):
    if item_code[5:7] == 'KC':
        return KICE_DB_PATH
    elif item_code[5:7] == 'NC':
        return NICE_DB_PATH
    else:
        return ITEM_DB_PATH


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
    #'E1aaaKC260620' -> '{2026}학년도 {6월} {20}번 {지1}'
    parsed_code = parse_code(code)
    yyyy = "20" + str(parsed_code["number"][0:2])
    mo = MONTH_DICT[parsed_code["number"][2:4]]
    nn = int(parsed_code["number"][4:])
    subject = SUBJECT_DICT[parsed_code["subject"]]
    if parsed_code["section"] == "KC":
        unit = "학년도"
    elif parsed_code["section"] == "NC":
        unit = "년"
    else:
        unit = "학년도"

    return f"{yyyy}{unit} {mo} {nn}번 {subject}"

@staticmethod
def sdcode2cite(code: str) -> str:
    #'E1aaaSV261620' -> '{2026}학년도 {시대인재 서바이벌} {16}{회} {20}번 {지1}'
    #'E1aaaZG261620' -> '{2026}학년도 {정태혁 모의고사} {16}{회} {20}번 {지1}'
    subject = SUBJECT_DICT[code[0:2]]
    cont = SDCONT_DICT[code[5:7]]
    yyyy = "20" + str(code[7:9])
    mo = int(code[9:11])
    nn = int(code[11:13])
    if cont == "수능모의평가":
        cont_unit = "월"
    else:
        cont_unit = "회"

    return f"{yyyy}학년도 {cont} {mo}{cont_unit} {nn}번 {subject}"

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
def code2hwp(code: str) -> str:
    return os.path.join(code2folder(code), f"{code}.hwp")

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