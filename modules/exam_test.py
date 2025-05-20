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
from modules.duplex_ans import DXAnswerBuilder
import json
import os
import json

# exam = 모의고사
# test = 문제지
# ans = 정답
# sol = 해설지


class ExamTestBuilder():
    def __init__(self, items):
        self.items = {
        item['item_code']: {
        'number': item['number'],
        'score': item['score'],
        'para': item['para']
        }
        for item in items
}
        # {item_code1: {'number': 1, 'score': 2, 'para': '1L'},
        #  item_code2: {'number': 2, 'score': 2, 'para': '1R'}, ...}

    def get_para_dict(self):
        # 297 * 420

        # 1P
        # 38 (header의 시작 위치) + 49 (header의 세로 길이) + 4 (header 하단 여백) = 91
        # 420 (페이지 높이) - 13.5 (꼬리말 높이) - 30 (아래 여백 높이) = 376.5
        # 31 (좌 여백 너비)
        # 31 (좌 여백 너비) + 112 (단 너비) = 143
        # 31 (좌 여백 너비) + 112 (단 너비) + 11 (단과 단 사이 여백) = 154
        # 31 (좌 여백 너비) + 112 (단 너비) + 11 (단과 단 사이 여백) + 112 (단 너비) = 266

        xLL = 31
        xLR = 143
        xRL = 154
        xRR = 266

        yT1 = 91
        yT234 = 56.5
        yB = 376.5
        yB4R = 349.16

        rect_1L = Rect(xLL, yT1, xLR, yB)
        rect_1R = Rect(xRL, yT1, xRR, yB)


        # 2P
        # 56.6 (위 여백 높이)
        rect_2L = Rect(xLL, yT234, xLR, yB)
        rect_2R = Rect(xRL, yT234, xRR, yB)

        # 3P
        rect_3L = Rect(xLL, yT234, xLR, yB)
        rect_3R = Rect(xRL, yT234, xRR, yB)

        # 4P
        # 376.5 (box의 끝 위치) - 22.34 (box의 세로 길이) - 5 (box 상단 여백) = 349.16
        rect_4L = Rect(xLL, yT234, xLR, yB)
        rect_4R = Rect(xRL, yT234, xRR, yB4R)

        dict = {
            "1L": rect_1L,
            "1R": rect_1R,
            "2L": rect_2L,
            "2R": rect_2R,
            "3L": rect_3L,
            "3R": rect_3R,
            "4L": rect_4L,
            "4R": rect_4R
        }

        for rect in dict.values():
            rect.x0 = Ratio.mm_to_px(rect.x0)
            rect.y0 = Ratio.mm_to_px(rect.y0)
            rect.x1 = Ratio.mm_to_px(rect.x1)
            rect.y1 = Ratio.mm_to_px(rect.y1)

        return dict

    def get_number_compo(self, number):
        # 견명조, 13.0pt
        number_resources_pdf = RESOURCES_PATH + "/exam_number_resources.pdf"
        number_resources_doc = fitz.open(number_resources_pdf)
        number_compo = Component(number_resources_pdf, int(number) - 1, number_resources_doc.load_page(int(number) - 1).rect)
        return number_compo

    def get_item_list_on_paragraph(self):
        item_list = [[] for i in range(8)]

        item_code_list = self.items.keys()
        for item_code in item_code_list:
            item_para = self.items[item_code]['para']
            if item_para == '1L':
                item_list[0].append(item_code)
            elif item_para == '1R':
                item_list[1].append(item_code)
            elif item_para == '2L':
                item_list[2].append(item_code)
            elif item_para == '2R':
                item_list[3].append(item_code)
            elif item_para == '3L':
                item_list[4].append(item_code)
            elif item_para == '3R':
                item_list[5].append(item_code)
            elif item_para == '4L':
                item_list[6].append(item_code)
            elif item_para == '4R':
                item_list[7].append(item_code)
        return item_list

    def bake_problem(self, item_code):
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)

        if item_code[5:7] == 'KC':  # kice problem
            if os.path.exists(code2original(item_code).replace(".pdf", "_trimmed.pdf")):
                item_pdf = code2original(item_code).replace(".pdf", "_trimmed.pdf")
            else:
                item_pdf = code2original(item_code)

            with fitz.open(item_pdf) as file:
                page = file.load_page(0)
                component = Component(item_pdf, 0, page.rect)
                problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(4 - 0.83), problem.height, 0), component)
                white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 0), Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                               (0, 0, 0, 0))
        else:
            item_pdf = code2pdf(item_code)
            with fitz.open(item_pdf) as file:
                ic = ItemCropper()
                prect = ic.get_problem_rect_from_file(file, 10)
                component = Component(item_pdf, 0, prect)
                problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(4 - 0.83), problem.height, 0), component)
                white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 0), Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                               (0, 0, 0, 0))
        problem_object.add_child(white_box)
        problem.add_child(problem_object)

        problem_number = self.items[item_code]['number']
        compo = self.get_number_compo(problem_number)
        no = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0.65), 10), compo)
        problem.add_child(no)

        problem.height += problem_object.get_height()
        return problem

    def add_child_to_paragraph_test(self, paragraph: ParagraphOverlayObject, item_code):
        problem = self.bake_problem(item_code)
        paragraph.add_child(problem)
        pass

    def get_component_on_resources(self, number):
        resources_pdf = RESOURCES_PATH + "/exam_test_resources.pdf"
        resources_doc = fitz.open(resources_pdf)
        component = Component(resources_pdf, number, resources_doc.load_page(number).rect)
        return component

    def get_component_on_header(self, output):
        filename = Path(output).stem
        page_num = int(filename.split('_')[-2][:-1]) - 1
        header_pdf = RESOURCES_PATH + "/exam_header_resources.pdf"
        header_doc = fitz.open(header_pdf)
        component = Component(header_pdf, page_num, header_doc.load_page(page_num).rect)
        return component

    def get_component_on_offset(self):
        offset_pdf = RESOURCES_PATH + "/exam_offset_resources.pdf"
        offset_doc = fitz.open(offset_pdf)
        component = Component(offset_pdf, 0, offset_doc.load_page(0).rect)
        return component

    def build_test(self, output):
        test_doc = fitz.open()
        self.overlayer = Overlayer(test_doc)

        offset_compo = self.get_component_on_offset()

        for i in range(4):
            self.overlayer.add_page(self.get_component_on_resources(i))
            self.overlayer.pdf_overlay(i, Coord(0, 0, 0), offset_compo)

        header_compo = self.get_component_on_header(output)
        self.overlayer.pdf_overlay(0, Coord(Ratio.mm_to_px(297/2 - 150/2), Ratio.mm_to_px(40 - 1.914), 5), header_compo)

        paragraph = ParagraphOverlayObject()
        para_dict = self.get_para_dict()
        item_list = self.get_item_list_on_paragraph()
        print(f'item_list: {item_list}')
        print(f'para_dict: {para_dict.items()}')
        i = 0
        for para_code, rect in para_dict.items():
            # 4L만 semijustify, 나머지는 justify
            align = 2 if para_code == '4R' else 1
            paragraph_list = ListOverlayObject(int(para_code[0:1]) - 1, Coord(rect.x0, rect.y0, 0), rect.height, align)
            for item_code in item_list[i]:
                problem = self.bake_problem(item_code)
                paragraph_list.add_child(problem)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            i += 1

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        PdfUtils.save_to_pdf(test_doc, output, garbage=4)
        test_doc.close()

        DXA = DXAnswerBuilder(self.items)
        DXA.build_answer_page(output)


    def get_problem_answer(self, item_pdf):
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            return answer

    def get_answer(self):
        pass

    def build_ans(self):
        ans_doc = fitz.open()
        self.overlayer = Overlayer(ans_doc)
        self.overlayer.add_page(self.get_component_on_resources(4))     #4p는 정답지

        # 정답지에 문제 번호 넣기
        for i in range(1, 21, 1):
            item_code = next((item_code for item_code, info in self.items.items() if info['number'] == i), None)
            answer = self.get_problem_answer(item_code)
            score = self.items[item_code]['score']

            # answer_compo
            # score_compo
