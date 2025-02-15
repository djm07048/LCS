import os
#TODO: 모든 경로를 path 또는 parse_code로부터 받도록 바꾸기
#TODO: 모든 경로를 윈도우즈 기준 역슬래시로


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

def parse_code_citation(item_code: str) -> str:
    parsed_code = parse_code(item_code)
    yyyy = "20" + str(parsed_code["number"][0:2])
    month_dict = {"01": "예비시행", "06": "6월", "09": "9월", "11": "대수능"}
    mo = month_dict[parsed_code["number"][2:4]]
    nn = int(parsed_code["number"][4:])
    subject_dict = {"E1":"지1", "E2":"지2"}
    subject = subject_dict[parsed_code["subject"]]


    return f"{yyyy}학년도 {mo} {nn}번 {subject}"

from utils.path import *
@staticmethod
def parse_item_folder_path(item_code: str) -> str:
    parsed = parse_code(item_code)
    if parsed["section"] == "KC": base_path= KICE_DB_PATH
    else: base_path= ITEM_DB_PATH

    return rf"{base_path}\{parsed['topic']}\{item_code}"

@staticmethod
def parse_item_pdf_path(item_code: str) -> str:
    return os.path.join(parse_item_folder_path(item_code), f"{item_code}.pdf")

def parse_item_caption_path(item_code: str) -> str:
    return os.path.join(parse_item_folder_path(item_code), f"{item_code}_caption.pdf")

def parse_item_original_path(item_code: str) -> str:
    return os.path.join(parse_item_folder_path(item_code), f"{item_code}_original.pdf")

def parse_item_Main_path(item_code: str) -> str:
    return os.path.join(parse_item_folder_path(item_code), f"{item_code}_Main.pdf")

def parse_item_modified_path(item_code: str) -> str:
    return os.path.join(parse_item_folder_path(item_code), f"{item_code}_modified.pdf")