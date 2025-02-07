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

from utils.path import *
@staticmethod
def parse_item_folder_path(item_code: str) -> str:
    parsed = parse_code(item_code)
    if parsed["section"] == "KC": base_path= KICE_DB_PATH
    else: base_path= ITEM_DB_PATH

    return f"{base_path}/{parsed['topic']}/{item_code}"

@staticmethod
def parse_item_pdf_path(item_code: str) -> str:
    return f"{parse_item_folder_path(item_code)}/{item_code}.pdf"

def parse_item_caption_path(item_code: str) -> str:
    return f"{parse_item_folder_path(item_code)}/{item_code}_caption.pdf"

def parse_item_original_path(item_code: str) -> str:
    return f"{parse_item_folder_path(item_code)}/{item_code}_original.pdf"

def parse_item_Main_path(item_code: str) -> str:
    return f"{parse_item_folder_path(item_code)}/{item_code}_Main.pdf"