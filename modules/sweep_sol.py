from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import SolutionInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.path import *
from item_cropper import ItemCropper
import json
# KC이면 문항은 original, 해설은 Main에서 가져옴
# NC or 자작이면 문항은 pdf, 해설도 pdf에서 가져옴


class SWSolBuilder:
    def __init__(self, items, curr_page):
        self.items = items
        self.curr_page = curr_page
        self.item_cropper = ItemCropper()
        #self.theme_cropper = ThemeCropper()
        self.resources_pdf = RESOURCES_PATH + '/sweep_pro_resources.pdf'
        self.resources_doc = fitz.open(self.resources_pdf)
        self.theme_dictionary = self.get_theme_json()
        print(self.items)
        result = {}
        for item in self.items:
            theme = item["theme"]
            if theme not in result:
                result[theme] = []

            # item_code를 키로, 나머지를 값으로 하는 딕셔너리 추가
            item_data = {k: v for k, v in item.items() if k != "item_code"}
            result[theme].append({item["item_code"]: item_data})
        self.items_by_theme = result
        print(f"Items by theme: {self.items_by_theme}")


    def get_theme_json(self):
        theme_json_path = Path(RESOURCES_PATH) / 'sweep_theme.json'
        if not theme_json_path.exists():
            raise FileNotFoundError(f"Theme JSON file not found at {theme_json_path}")
        with open(theme_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def build_page_main_sol_lt(self):
        """해설 페이지를 생성"""
        pass

    def build_page_main_sol_rt(self):
        pass

    def build_page_sub(self):
        pass

