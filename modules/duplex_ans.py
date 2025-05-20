from utils.coord import Coord
from utils.ratio import Ratio
import fitz
from utils.path import *
from utils.pdf_utils import PdfUtils
from utils.overlay_object import *
from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path


class DXAnswerBuilder:
    y_list = [114.538, 132.398, 150.23, 168.09, 185.949]
    x_answer_list = [55.536, 101.203, 146.87, 192.537]
    x_score_list = [69.929, 115.596, 161.264, 206.931]

    coord_dict = []
    for number in range(20):
        x_answer0 = x_answer_list[number // 5]
        x_score0 = x_score_list[number // 5]
        y0 = y_list[number % 5]
        coord_dict.append({
            "number": number,
            "answer_coord": Coord(Ratio.mm_to_px(x_answer0), Ratio.mm_to_px(y0), 0),
            "score_coord": Coord(Ratio.mm_to_px(x_score0), Ratio.mm_to_px(y0), 0)
        })

    print(f"coord_dict: {coord_dict}")

    def __init__(self, items):
        self.items = {}
        ic = ItemCropper()

        for item_code, item_data in items.items():
            print(f"item_code: {item_code}, item_data: {item_data}")
            dict_entry = {
                item_data['number']: {
                    'item_code': item_code,
                    'score': item_data['score'],  # int; 2 or 3
                    'answer': self.get_problem_answer(code2pdf(item_code))  # int; 1, 2, 3, 4, 5
                }
            }
            self.items.update(dict_entry)

        print(f"items: {self.items}")

        self.resources_pdf = RESOURCES_PATH + "/duplex_answer_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

    def get_problem_answer(self, item_pdf):
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            answer_dict = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
            if answer in answer_dict:
                answer = answer_dict[answer]
            else:
                answer = 0
            return answer
    def build_1p(self):
        return self.resources_doc.load_page(0)

    def get_component_on_header(self, output):
        filename = Path(output).stem
        page_num = int(filename.split('_')[-2][:-1]) - 1
        header_pdf = RESOURCES_PATH + "/exam_header_resources.pdf"
        header_doc = fitz.open(header_pdf)
        component = Component(header_pdf, page_num, header_doc.load_page(page_num).rect)
        return component

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def build_answer_page(self, output):
        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)

        #page1
        overlayer.add_page(self.get_component_on_resources(9))

        filenum = int(Path(output).stem.split('_')[1][:-1])
        filecontents = Path(output).stem.split('_')[0]
        contents = "정태혁 모의고사" if filecontents == "EX" else "정태혁 모의고사"
        text = f"{contents} {filenum}회"
        # 이 부분 text 추가
        text_compo = TextOverlayObject(0, Coord(Ratio.mm_to_px(131), Ratio.mm_to_px(47.5), 0),
                                       "Pretendard-Bold.ttf", 14, text, (0, 0, 0, 1),
                                       fitz.TEXT_ALIGN_CENTER)

        #page2
        overlayer.add_page(self.get_component_on_resources(8))

        #page3
        overlayer.add_page(self.get_component_on_resources(0))

        for number in range(1, 21, 1):
            score = self.items[number]['score']
            answer = self.items[number]['answer']
            score_coord = self.coord_dict[number - 1]['score_coord']
            answer_coord = self.coord_dict[number - 1]['answer_coord']

            answer_compo = self.get_component_on_resources(answer)
            score_compo = self.get_component_on_resources(score + 4)

            overlayer.pdf_overlay(2, answer_coord, answer_compo)
            overlayer.pdf_overlay(2, score_coord, score_compo)

        header_component = self.get_component_on_header(output)
        overlayer.pdf_overlay(2, Coord(Ratio.mm_to_px(262/2 - 150/2), Ratio.mm_to_px(47.5), 0), header_component)

        # page4
        overlayer.add_page(self.get_component_on_resources(8))

        return new_doc

    def build_footer_page(self):
        new_doc = fitz.open()
        overlayer = Overlayer(new_doc)
        overlayer.add_page(self.get_component_on_resources(10))
        return new_doc