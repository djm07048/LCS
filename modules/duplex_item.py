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

# item마다의 정보를 담는 클래스

import os
import json

def get_related_item_reference(item_code):
    directory = INPUT_PATH + r"/BookDB"

    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    continue  # Skip empty or invalid JSON files
                for item in data:
                    if item['item_code'] == item_code:
                        if item['mainsub'] is not None:
                            number = item['mainsub']
                        else:
                            if item['item_num'] is not None:
                                number = item['item_num']
                        return f"{filename.replace('.json', '')}_{number}번"
    return None

class DuplexItemBuilder:
    def __init__(self, unit_item_code, list_rel_item_code, list_theory_piece_code, page):
        self.unit_item_code = unit_item_code        #이번 unit의 item_code를 일컫음.
        self.list_rel_item_code = list_rel_item_code
        self.list_theory_piece_code = list_theory_piece_code
        self.resources_pdf = RESOURCES_PATH + "/duplex_item_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)
        self.page = page

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def get_list_of_related_items(self):
        # self.unit_item_code를 기준으로 related item들의 item_code를 list로 반환
        pass

    def get_problem_component(self, item_code):
        ic = ItemCropper()
        item_pdf = code2original(item_code) if item_code[5:7] == 'KC' else code2pdf(item_code)
        with fitz.open(item_pdf) as file:
            page = file.load_page(0)
            component = Component(item_pdf, 0, page.rect) if item_code[5:7] == 'KC'\
                else Component(item_pdf, 0, ic.get_problem_rect_from_file(file, accuracy = 1))
        return component

    def bake_title_sd(self):
        source = sdcode2cite(self.unit_item_code)
        text_exam = source.split(" ")[2] + " " + source.split(" ")[3]
        text_number = source.split(" ")[4]

        compo = Component(self.resources_pdf, 0, self.resources_doc.load_page(0).rect)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(7), Ratio.mm_to_px(20), 0), "Pretendard-SemiBold.ttf", 24,
                                    text_exam, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        text_exam_width = to_exam.get_width()

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(21) + text_exam_width, Ratio.mm_to_px(20), 0), "Pretendard-SemiBold.ttf", 24,
                                    text_number, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        bar = ShapeOverlayObject(0, Coord(text_exam_width + Ratio.mm_to_px(14 - 0.251), Ratio.mm_to_px(8), 0),
                                 Rect(0, 0, Ratio.mm_to_px(0.502), Ratio.mm_to_px(5)), (0, 0, 0, 1))

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(bar)

        box.rect = compo.src_rect

        return box

    def bake_title_rel(self, item_code):
        compo = Component(self.resources_pdf, 1, self.resources_doc.load_page(1).rect)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        if item_code[5:7] == 'KC' or item_code[5:7] == 'NC':
            source = code2cite(item_code)
            text_exam = source.split(" ")[0] + " " + source.split(" ")[1] + " " + " " + source.split(" ")[3]
            text_number = source.split(" ")[2]
        else:
            source = get_related_item_reference(item_code)
            text_exam = "Squeeze " + source.split("_")[1]
            text_number = source.split("_")[2]

        source = sdcode2cite(self.unit_item_code)
        text_unit = source.split(" ")[2] + " " + source.split(" ")[3] + " " + source.split(" ")[4] + " " + "연계"

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(7), Ratio.mm_to_px(20), 0), "Pretendard-SemiBold.ttf", 24,
                                    text_exam, (0.2, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        text_exam_width = to_exam.get_width()

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(21) + text_exam_width, Ratio.mm_to_px(20), 0),
                                      "Pretendard-SemiBold.ttf", 24,
                                      text_number, (0.2, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        bar = ShapeOverlayObject(0, Coord(text_exam_width + Ratio.mm_to_px(14 - 0.251), Ratio.mm_to_px(8), 0),
                                 Rect(0, 0, Ratio.mm_to_px(0.502), Ratio.mm_to_px(5)), (1, 0, 0, 0))

        to_unit = TextOverlayObject(0, Coord(Ratio.mm_to_px(224 - 3), Ratio.mm_to_px(5), 0), "Pretendard-SemiBold.ttf", 15,
                                text_unit, (0, 0, 0, 0.5), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(bar)
        box.add_child(to_unit)

        box.rect = compo.src_rect

        return box

    def bake_title_piece(self):
        list_piece_code = self.list_theory_piece_code

        #piece_code = ["WIND UP 고체편 120p", "WIND UP 고체편 121p", "WIND UP 고체편 122p"]
        compo = Component(self.resources_pdf, 2, self.resources_doc.load_page(2).rect)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        text_exam = ' '.join(list_piece_code[0].split(" ")[0:3])
        text_number = ', '.join([list_piece_code[i].split(" ")[3] for i in range(len(list_piece_code))])

        source = sdcode2cite(self.unit_item_code)
        text_unit = source.split(" ")[2] + " " + source.split(" ")[3] + " " + source.split(" ")[4] + " " + "개념"

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(7), Ratio.mm_to_px(20), 0),
                                    "Pretendard-SemiBold.ttf", 24,
                                    text_exam, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        text_exam_width = to_exam.get_width()
        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(21) + text_exam_width, Ratio.mm_to_px(20), 0),
                                      "Pretendard-SemiBold.ttf", 24,
                                      text_number, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        to_unit = TextOverlayObject(0, Coord(Ratio.mm_to_px(224 - 5), Ratio.mm_to_px(5), 0), "Pretendard-SemiBold.ttf", 15,
                                text_unit, (0, 0, 0, 0.5), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_unit)

        box.rect = compo.src_rect

        return box

    def bake_title_sol(self, item_code):
        # 동글동글한 모양 만들어야 함.
        compo = Component(self.resources_pdf, 3, self.resources_doc.load_page(3).rect)
        box = ComponentOverlayObject(0, Coord(0, 0, 0), compo)

        if item_code[5:7] == 'KC' or item_code[5:7] == 'NC':
            source = code2cite(item_code)
            text_exam = source.split(" ")[0] + " " + source.split(" ")[1] + " " + " " + source.split(" ")[3]
            text_number = source.split(" ")[2] + " 해설"
        else:
            source = get_related_item_reference(item_code)
            text_exam = "Squeeze " + source.split("_")[1]
            text_number = source.split("_")[2] + " 해설"

        source = sdcode2cite(self.unit_item_code)
        text_unit = source.split(" ")[2] + " " + source.split(" ")[3] + " " + source.split(" ")[4] + " " + "연계 해설"

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(7), Ratio.mm_to_px(20), 0), "Pretendard-SemiBold.ttf", 24,
                                    text_exam, (0.2, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        text_exam_width = to_exam.get_width()

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(21) + text_exam_width, Ratio.mm_to_px(20), 0),
                                      "Pretendard-SemiBold.ttf", 24,
                                      text_number, (0.2, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        bubble_exam = ShapeOverlayObject(0, Coord(0, Ratio.mm_to_px(8), 0),
                                 Rect(0, 0, text_exam_width + Ratio.mm_to_px(14), Ratio.mm_to_px(17.5)),(0.2, 0, 0, 0), 5/17.5)

        bubble_exam_width = bubble_exam.rect.width

        bubble_number = ShapeOverlayObject(0, Coord(text_exam_width + Ratio.mm_to_px(14), Ratio.mm_to_px(8), 0),
                                 Rect(0, 0, Ratio.mm_to_px(224 - 3) - bubble_exam_width , Ratio.mm_to_px(17.5)), (0.2, 0, 0, 0), 5/17.5)
        lt_corner = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(-1), 0, 0), Component(self.resources_pdf, 4, self.resources_doc.load_page(4).rect))
        middle_corner = ComponentOverlayObject(0, Coord(text_exam_width + Ratio.mm_to_px(8), 0, 0), Component(self.resources_pdf, 5, self.resources_doc.load_page(5).rect))
        rt_corner = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(224 - 3 - 5), 0, 0), Component(self.resources_pdf, 6, self.resources_doc.load_page(6).rect))

        lt_to_middle_line = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(5), Ratio.mm_to_px(8) - 1, 0),
                                               Rect(0, 0, text_exam_width, 2), (1, 0, 0, 0))
        middle_to_rt_line = ShapeOverlayObject(0, Coord(text_exam_width + Ratio.mm_to_px(19), Ratio.mm_to_px(8 - 0.251), 0),
                                                  Rect(0, 0, Ratio.mm_to_px(224 - 3 - 5 - text_exam_width - 19), Ratio.mm_to_px(0.502)), (1, 0, 0, 0))


        to_unit = TextOverlayObject(0, Coord(Ratio.mm_to_px(224 - 3 - 5), Ratio.mm_to_px(5), 0), "Pretendard-SemiBold.ttf", 15,
                                    text_unit, (0, 0, 0, 0.5), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(bubble_exam)
        box.add_child(bubble_number)
        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_unit)

        box.add_child(lt_corner)
        box.add_child(middle_corner)
        box.add_child(rt_corner)

        '''
        box.add_child(lt_to_middle_line)
        box.add_child(middle_to_rt_line)
        '''

        box.rect = compo.src_rect

        return box

    def get_sol_type_dict(self):
        sol_type_dict = {
            "HA": 9,        #ㄱ
            "HB": 10,       #ㄴ
            "HC": 11,       #ㄷ
            "HD": 12,       #ㄹ
            "HE": 13,       #ㅁ
            "NA": 14,       #1
            "NB": 15,       #2
            "NC": 16,       #3
            "ND": 17,       #4
            "NE": 18,       #5
            "EA": 19,       #A
            "EB": 20,       #B
            "EC": 21,       #C
            "arrow": 22,        #화살표
            "clip": 23,         #클립
            "check": 24,        #체크
            "exc_mark": 25,     #느낌표
            "answer": 26,
            "SA": 27,       #linking 1
        }
        return sol_type_dict

    def get_commentary_data(self):
        with open(RESOURCES_PATH + "/commentary.json") as file:
            commentary_data = json.load(file)
        return commentary_data

    def append_new_list_to_paragraph_sd(self, paragraph: ParagraphOverlayObject, num):
        if num % 4 == 0:
            self.overlayer.add_page(self.get_component_on_resources(28 + self.page))
            pass
        elif num % 4 == 2:
            self.overlayer.add_page(self.get_component_on_resources(29 - self.page))
            pass

        x0_list = [18, 133, 20, 135]  # LL, LR, RL, RR의 x0
        if self.page == 0:
            x0 = x0_list[num]
        else:
            x0 = x0_list[(num + 2) % 4]
        paragraph_list = ListOverlayObject(num // 2, Coord(Ratio.mm_to_px(x0), Ratio.mm_to_px(55), 0),
                                           Ratio.mm_to_px(280), 0)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)
        pass

    def add_child_to_paragraph_sd(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph_sd(paragraph, num)
        paragraph.add_child(child)
        return num + 1

    def append_new_list_to_paragraph_rel(self, paragraph: ParagraphOverlayObject, num): #TODO: 이 함수는 수정 필요
        self.overlayer.add_page(self.get_component_on_resources(30 + num % 2))

        x0_list = [18, 20]  # Lt, Rt의 x0
        if self.page == 0:
            x0 = x0_list[num % 2]
        else:
            x0 = x0_list[(num + 1) % 2]
        paragraph_list = ListOverlayObject(num, Coord(Ratio.mm_to_px(x0), Ratio.mm_to_px(22), 0),
                                           Ratio.mm_to_px(280 + 33), 2)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)
        pass

    def add_child_to_paragraph_rel(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph_rel(paragraph, num)
        paragraph.add_child(child)
        return num + 1

    def bake_solution_object(self, solution_info, TF, item_pdf):
        solution_object = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        solution_component = Component(item_pdf, 0, solution_info.rect)

        sol_type_dict = self.get_sol_type_dict()
        commentary_data = self.get_commentary_data()

        if solution_info.hexcode not in commentary_data:
            # Handle the missing key case
            print(f"Warning: Hexcode {solution_info.hexcode} not found in commentary data.")
            return None

        commentary_key = commentary_data[solution_info.hexcode]
        if commentary_key not in sol_type_dict:
            # Handle the missing key case
            print(f"Warning: Commentary key {commentary_key} not found in solution type dictionary.")
            return None

        res_page_num = self.get_sol_type_dict()[self.get_commentary_data()[solution_info.hexcode]]
        type_component = self.get_component_on_resources(res_page_num)
        solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 2), type_component))

        OX_component = None
        if TF == 1:
            OX_component = self.get_component_on_resources(7)
        if TF == 0:
            OX_component = self.get_component_on_resources(8)
        if OX_component is not None:
            solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 3), OX_component))

        solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(5), Ratio.mm_to_px(8), 2), solution_component))
        solution_object.height = solution_component.src_rect.height + Ratio.mm_to_px(8 + 5)

        return solution_object  #TODO: linking1의 경우에 대한 처리 필요

    def build_page_sd(self):
        sd_doc = fitz.open()
        self.overlayer = Overlayer(sd_doc)

        left_page = AreaOverlayObject(self.page, Coord(0, 0, 0), 0)
        title_sd = self.bake_title_sd()
        title_sd.coord = Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(22), 0)
        left_page.add_child(title_sd)

        with fitz.open(code2pdf(self.unit_item_code)) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        for solution_info in solutions_info:
            so = None
            sol_commentary_data = self.get_commentary_data()
            if solution_info.hexcode in sol_commentary_data:        #commentary data에 hexcode가 있는 경우
                if sol_commentary_data[solution_info.hexcode] == 'SA':
                    so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                    solution_component = Component(code2pdf(self.unit_item_code), 0, solution_info.rect)
                    content_height = solution_component.src_rect.height + Ratio.mm_to_px(5)
                    bubble = ShapeOverlayObject(0, Coord(0, 0, 0),
                                                Rect(0, 0, Ratio.mm_to_px(105), content_height),
                                                (0, 0, 0, 0.2), 2.5/content_height)
                    handle = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(90), content_height, 0),
                                                    self.get_component_on_resources(27))
                    compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5), Ratio.mm_to_px(2.5), 2), solution_component)

                    so.add_child(bubble)
                    so.add_child(handle)
                    so.add_child(compo)

                    so.height = content_height + Ratio.mm_to_px(3 + 7.5)
                else:
                    so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode],
                                                   code2pdf(self.unit_item_code))
            else:
                so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], code2pdf(self.unit_item_code))

            if so is None:
                continue

            paragraph_cnt = self.add_child_to_paragraph_sd(paragraph, so, paragraph_cnt)

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        if self.overlayer.doc.page_count == 0:
            raise ValueError("No pages were added to the document.")

        left_page.overlay(self.overlayer, Coord(0, 0, 0))

        return sd_doc

    def bake_problem(self, item_code):
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        problem_title = self.bake_title_rel(item_code)
        problem.add_child(problem_title)
        problem.height += problem_title.get_height() + Ratio.mm_to_px(7.5)
        if item_code[5:7] == 'KC':  # kice problem
            if os.path.exists(code2original(item_code).replace(".pdf", "_trimmed.pdf")):
                item_pdf = code2original(item_code).replace(".pdf", "_trimmed.pdf")
            else:
                item_pdf = code2original(item_code)
            modified_pdf = code2modified(item_code)

            with fitz.open(item_pdf) as file:
                page = file.load_page(0)
                component = Component(item_pdf, 0, page.rect)
                problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18), problem.height, 0), component)
                white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(18), 0, 0), Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                               (0, 0, 0, 0))

                problem.add_child(problem_object)
                problem_object.add_child(white_box)

                problem.height += problem_object.get_height()

                if Path(modified_pdf).exists():
                    problem.height += Ratio.mm_to_px(10)

                    with fitz.open(modified_pdf) as mod_file:
                        mod_page = mod_file.load_page(0)
                        modified_box = ComponentOverlayObject(0, Coord(0, problem.height, 0),
                                                              Component(modified_pdf, 0, mod_page.rect))
                        problem.add_child(modified_box)
                        problem.height -= modified_box.get_height()

                    problem.height -= Ratio.mm_to_px(20)
                problem.height += Ratio.mm_to_px(12.5)
        else:  #TODO item problem, kice problem과 동기화 해야 함
            item_pdf = code2pdf(item_code)
            with fitz.open(item_pdf) as file:
                ic = ItemCropper()
                prect = ic.get_problem_rect_from_file(file, 10)
                component = Component(item_pdf, 0, prect)
                problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18), problem.height, 0), component)
                white_box = ShapeOverlayObject(0, Coord(0, 0, 0), Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5)),
                                               (0, 0, 0, 0))
                problem_object.add_child(white_box)
                problem.add_child(problem_object)
                problem.height += problem_object.get_height() + Ratio.mm_to_px(12.5)
        return problem

    def build_page_rel(self):
        list_rel_item_code = self.list_rel_item_code

        rel_doc = fitz.open()
        self.overlayer = Overlayer(rel_doc)

        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        for item_code in list_rel_item_code:
            problem = self.bake_problem(item_code)
            paragraph_cnt = self.add_child_to_paragraph_rel(paragraph, problem, paragraph_cnt)

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        return rel_doc

    def add_child_to_paragraph_theory(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph_theory(paragraph, num)
        paragraph.add_child(child)
        return num + 1

    def append_new_list_to_paragraph_theory(self, paragraph: ParagraphOverlayObject, num):
        if num % 4 == 0:
            self.overlayer.add_page(self.get_component_on_resources(30 + self.page % 2))
            pass
        elif num % 4 == 2:
            self.overlayer.add_page(self.get_component_on_resources(30 + self.page % 2))
            pass

        x0_list = [18, 133, 20, 135]  # LL, LR, RL, RR의 x0
        if self.page == 0:
            x0 = x0_list[num]
            y0 = Ratio.mm_to_px(55)
        else:
            x0 = x0_list[(num + 2) % 4]
            y0 = Ratio.mm_to_px(22)


        paragraph_list = ListOverlayObject(num // 2, Coord(Ratio.mm_to_px(x0), y0, 0),
                                           Ratio.mm_to_px(280), 0)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)
        pass

    def bake_theory_piece(self, piece_code):
        piece_pdf = RESOURCES_PATH + "/theory_piece/" + piece_code + ".pdf"

        piece = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        with fitz.open(piece_pdf) as file:
            page = file.load_page(0)
            component = Component(piece_pdf, 0, page.rect)
            piece_object = ResizedComponentOverlayObject(0, Coord(0, piece.height, 0), component, 105/161)
            piece.add_child(piece_object)

            piece.height += piece_object.get_height()
            piece.height += Ratio.mm_to_px(12.5)
        return piece

    def build_page_theory(self):
        list_theory_piece_code = self.list_theory_piece_code
        theory_doc = fitz.open()

        self.overlayer = Overlayer(theory_doc)

        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0
        i = 0

        for piece_code in list_theory_piece_code:
            theory_piece = self.bake_theory_piece(piece_code)
            paragraph_cnt = self.add_child_to_paragraph_theory(paragraph, theory_piece, paragraph_cnt)

            if i == 0:
                piece = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                piece_title = self.bake_title_piece()
                piece.add_child(piece_title)
                piece.height += piece_title.get_height() + Ratio.mm_to_px(7.5)
                #overlay 시 좌우 나누어서 18, 20 위치에 나오게 하기
                piece.overlay(self.overlayer, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(22), 0))
            i += 1
        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        return theory_doc

    def build_page_sol(self):
        sol_whole_doc = fitz.open()

        for item_code in self.list_rel_item_code:
            sol_item_doc = fitz.open()
            self.overlayer = Overlayer(sol_item_doc)
            first_page = AreaOverlayObject(self.page, Coord(0, 0, 0), 0)
            title_sol = self.bake_title_sol(item_code)
            # overlay 시 좌우 나누어서 18, 20 위치에 나오게 하기
            title_sol.coord = Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(22), 0)
            first_page.add_child(title_sol)

            with fitz.open(code2pdf(item_code)) as file:
                ic = ItemCropper()
                solutions_info = ic.get_solution_infos_from_file(file, 10)
                sTF = ic.get_TF_of_solutions_from_file(file, 10)

            paragraph = ParagraphOverlayObject()
            paragraph_cnt = 0

            # problem 추가
            problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)

            if item_code[5:7] == 'KC':  # kice problem
                if os.path.exists(code2original(item_code).replace(".pdf", "_trimmed.pdf")):
                    item_pdf = code2original(item_code).replace(".pdf", "_trimmed.pdf")
                else:
                    item_pdf = code2original(item_code)
                modified_pdf = code2modified(item_code)

                with fitz.open(item_pdf) as file:
                    page = file.load_page(0)
                    component = Component(item_pdf, 0, page.rect)
                    problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), problem.height, 0), component)
                    white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 0),
                                                   Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                                   (0, 0, 0, 0))

                    problem.add_child(problem_object)
                    problem_object.add_child(white_box)

                    problem.height += problem_object.get_height()

                    if Path(modified_pdf).exists():
                        problem.height += Ratio.mm_to_px(10)

                        with fitz.open(modified_pdf) as mod_file:
                            mod_page = mod_file.load_page(0)
                            modified_box = ComponentOverlayObject(0, Coord(0, problem.height, 0),
                                                                  Component(modified_pdf, 0, mod_page.rect))
                            problem.add_child(modified_box)
                            problem.height -= modified_box.get_height()

                        problem.height -= Ratio.mm_to_px(20)
                    problem.height += Ratio.mm_to_px(12.5)
            else:  # item problem
                item_pdf = code2pdf(item_code)
                with fitz.open(item_pdf) as file:
                    ic = ItemCropper()
                    prect = ic.get_problem_rect_from_file(file, 10)
                    component = Component(item_pdf, 0, prect)
                    problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), problem.height, 0), component)
                    white_box = ShapeOverlayObject(0, Coord(0, 0, 0),
                                                   Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5)),
                                                   (0, 0, 0, 0))
                    problem_object.add_child(white_box)
                    problem.add_child(problem_object)
                    problem.height += problem_object.get_height() + Ratio.mm_to_px(12.5)

            paragraph_cnt = self.add_child_to_paragraph_sd(paragraph, problem, paragraph_cnt)

            for solution_info in solutions_info:
                so = None
                sol_commentary_data = self.get_commentary_data()
                if solution_info.hexcode in sol_commentary_data:  # commentary data에 hexcode가 있는 경우
                    if sol_commentary_data[solution_info.hexcode] == 'SA':
                        so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                        solution_component = Component(code2pdf(item_code), 0, solution_info.rect)
                        content_height = solution_component.src_rect.height + Ratio.mm_to_px(5)
                        bubble = ShapeOverlayObject(0, Coord(0, 0, 0),
                                                    Rect(0, 0, Ratio.mm_to_px(105), content_height),
                                                    (0, 0, 0, 0.2), 2.5 / content_height)
                        handle = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(90), content_height, 0),
                                                        self.get_component_on_resources(27))
                        compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5), Ratio.mm_to_px(2.5), 2),
                                                       solution_component)

                        so.add_child(bubble)
                        so.add_child(handle)
                        so.add_child(compo)

                        so.height = content_height + Ratio.mm_to_px(3 + 7.5)
                    else:
                        so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode],
                                                       code2pdf(item_code))
                else:
                    so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode],
                                                   code2pdf(item_code))

                if so is None:
                    continue
                paragraph_cnt = self.add_child_to_paragraph_sd(paragraph, so, paragraph_cnt)

            paragraph.overlay(self.overlayer, Coord(0, 0, 0))

            if self.overlayer.doc.page_count == 0:
                raise ValueError("No pages were added to the document.")

            first_page.overlay(self.overlayer, Coord(0, 0, 0))
            sol_whole_doc.insert_pdf(sol_item_doc)

            sol_item_doc.close()

        return sol_whole_doc


if __name__ == "__main__":
    new_doc = fitz.open()

    item_dict = [["E1ebhSV260612", ["E1caiZG250009", "E1dbdKC170909", "E1dbeKC230606"], ["WIND UP 고체편 120p", "WIND UP 고체편 121p", "WIND UP 고체편 122p"]],
                 ["E1lecWL260819", ["E1caiZG250010", "E1dbdKC170909"], ["WIND UP 천체편 80p", "WIND UP 천체편 81p"]]]

    for i in item_dict:
        builder = DuplexItemBuilder(i[0], i[1], i[2], 0)

        doc_sd = builder.build_page_sd()

        #builder.page += doc_sd.page_count
        doc_rel = builder.build_page_rel()

        #builder.page += doc_rel.page_count
        doc_theory = builder.build_page_theory()

        #builder.page += doc_theory.page_count
        doc_sol = builder.build_page_sol()

        new_doc.insert_pdf(doc_sd)
        new_doc.insert_pdf(doc_rel)
        new_doc.insert_pdf(doc_theory)
        new_doc.insert_pdf(doc_sol)

    new_doc.save(OUTPUT_PATH + "/duplex_item.pdf")
    new_doc.close()
    doc_sd.close()
    doc_rel.close()
    doc_theory.close()
    doc_sol.close()