from modules.kice_cropper import KiceCropper
from modules.builder_squeeze import SQBuilder
from modules.builder_squeeze_mini import SQMiniBuilder
from modules.builder_duplex import DXBuilder
from modules.exam_test import ExamTestBuilder
from modules.builder_sweep import SWBuilder

from pathlib import Path
import json
from utils.path import *

def crop_all_kice(input = INPUT_PATH + '/1425'):
    folder_path = Path(input)
    pdf_files = folder_path.glob('*.pdf')

    for pdf_file in pdf_files:
        pdf_src_path = str(pdf_file)
        item_code = pdf_file.stem
        print(item_code, end=' ', flush=True)
        kc = KiceCropper(pdf_name=pdf_src_path)
        ret = kc.extract_problems(accuracy=10)
        print(f'extracted {ret} items')
        kc.save_original()
        kc.save_caption_from_original()

def build_squeeze_paper(input=INPUT_PATH+"/squeeze_item.json", output=OUTPUT_PATH + "/output.pdf", log_callback=None):
    if log_callback:
        log_callback("squeeze Paper Build Start")
        log_callback(f"Building {input} to {output}")
    with open(input, encoding='UTF8') as file:
        items = json.load(file)
    bd = SQBuilder(items)
    bd.build(output, log_callback=log_callback)

def build_squeeze_mini_paper(input, output, log_callback=None):
    if log_callback:
        log_callback("squeeze mini Paper Build Start")
        log_callback(f"Buliding {input} to {output}")
    with open(input, encoding='UTF8') as file:
        items = json.load(file)
    bd = SQMiniBuilder(items)
    bd.build(output, log_callback=log_callback)

def build_duplex(input, output, log_callback=None):
    if log_callback:
        log_callback("Duplex Paper Build Start")
        log_callback(f"Building {input} to {output}")
    with open(input, encoding='UTF8') as file:
        items = json.load(file)
    bd = DXBuilder(items)
    bd.build(output, log_callback=log_callback)

def build_exam_test(input, output, log_callback=None):
    if log_callback:
        log_callback("Exam Test Paper Build Start")
        log_callback(f"Building {input} to {output}")
    with open(input, encoding='UTF8') as file:
        items = json.load(file)
    book_name = Path(output).name
    bd = ExamTestBuilder(items, book_name)
    bd.build_test(output)

def build_sweep(input, output, log_callback=None):
    if log_callback:
        log_callback("Sweep Paper Build Start")
        log_callback(f"Building {input} to {output}")
    with open(input, encoding='UTF8') as file:
        items = json.load(file)
    bd = SWBuilder(items)
    bd.build(output, log_callback=log_callback)


#numpy version 1.46 으로 하였을 때 정상