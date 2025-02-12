from modules.kice_cropper import KiceCropper
from modules.builder import Builder

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
    bd = Builder(items)
    bd.build(output, log_callback=log_callback)

if __name__ == '__main__':
    build_squeeze_paper()
    pass

#numpy version 1.46 으로 하였을 때 정상