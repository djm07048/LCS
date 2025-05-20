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
    ## itme by item으로 build 하게됨.
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
        text_number = source.split(" ")[3] + " " + source.split(" ")[4]

        compo = self.get_component_on_resources(0)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(62), Ratio.mm_to_px(9), 0), "Pretendard-ExtraBold.ttf", 16,
                                    text_number, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        box.add_child(to_number)
        box.rect = compo.src_rect

        return box

    def bake_title_piece(self):
        list_piece_code = self.list_theory_piece_code

        #piece_code = ["WIND UP 고체편 120p", "WIND UP 고체편 121p", "WIND UP 고체편 122p"]
        compo = self.get_component_on_resources(1)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        text_exam = ' '.join(list_piece_code[0].split(" ")[2])
        text_number = ', '.join([list_piece_code[i].split(" ")[3] for i in range(len(list_piece_code))])

        sd_source = sdcode2cite(self.unit_item_code)
        text_sd = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " " + "개념"

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(41), Ratio.mm_to_px(8.62), 0),
                                    "Pretendard-ExtraBold.ttf", 13,
                                    text_exam, (1, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        text_exam_width = to_exam.get_width()
        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(62), Ratio.mm_to_px(9), 0),
                                      "Pretendard-ExtraBold.ttf", 16,
                                      text_number, (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)

        to_sd = TextOverlayObject(0, Coord(Ratio.mm_to_px(213), Ratio.mm_to_px(5.5), 0), "Pretendard-Medium.ttf", 10,
                                text_sd, (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_sd)

        box.rect = compo.src_rect

        return box
    def bake_title_rel(self, item_code, number):
        compo = self.get_component_on_resources(2)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        if item_code[5:7] == 'KC' or item_code[5:7] == 'NC':
            text_exam = code2cite(item_code)
        else:
            source = get_related_item_reference(item_code)
            text_exam = "Squeeze " + source.split("_")[1] + " " + source.split("_")[2]

        sd_source = sdcode2cite(self.unit_item_code)
        text_sd = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " " + "연계"

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(12.876), Ratio.mm_to_px(9.5), 0), "Montserrat-Bold.ttf", 22,
                                      number, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(35), Ratio.mm_to_px(9), 0),"Pretendard-ExtraBold.ttf", 16,
                                    text_exam, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        to_sd = TextOverlayObject(0, Coord(Ratio.mm_to_px(213), Ratio.mm_to_px(5.5), 0), "Pretendard-Medium.ttf", 10,
                                text_sd, (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_sd)

        box.rect = compo.src_rect

        return box


    def bake_title_sol(self, item_code, number):
        compo = self.get_component_on_resources(3)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        if item_code[5:7] == 'KC' or item_code[5:7] == 'NC':
            text_exam = code2cite(item_code)
        else:
            source = get_related_item_reference(item_code)
            text_exam = "Squeeze " + source.split("_")[1] + " " + source.split("_")[2]

        sd_source = sdcode2cite(self.unit_item_code)
        text_sd = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " " + "연계"

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(12.876), Ratio.mm_to_px(9.5), 0), "Montserrat-Bold.ttf", 22,
                                    number, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(35), Ratio.mm_to_px(9), 0),"Pretendard-ExtraBold.ttf", 16,
                                    text_exam, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        exam_x1 = to_exam.get_width() + Ratio.mm_to_px(35)

        to_sd = TextOverlayObject(0, Coord(Ratio.mm_to_px(213), Ratio.mm_to_px(5.5), 0), "Pretendard-Medium.ttf", 10,
                                text_sd, (0, 0, 0, 1), fitz.TEXT_ALIGN_RIGHT)

        frame_compo = self.get_component_on_resources(4)
        frame = ComponentOverlayObject(0, Coord(exam_x1 + Ratio.mm_to_px(5.5), Ratio.mm_to_px(0), 0), frame_compo)

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_sd)
        box.add_child(frame)

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

    def get_problem_answer(self, item_pdf):
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            return answer

    def get_commentary_data(self):
        with open(RESOURCES_PATH + "/commentary.json") as file:
            commentary_data = json.load(file)
        return commentary_data

    def append_new_list_to_paragraph_sd(self, paragraph: ParagraphOverlayObject, num):
        #TODO: item별로 따로 제작하기 때문에 page 정하는 logic이 필요함
        if num % 4 == 0:
            self.overlayer.add_page(self.get_component_on_resources(28 + self.page % 2))
            pass
        elif num % 4 == 2:
            self.overlayer.add_page(self.get_component_on_resources(29 - self.page % 2))
            pass

        x0_list = [18, 133, 20, 135]  # LL, LR, RL, RR의 x0
        x0 = x0_list[num % 4]
        paragraph_list = ListOverlayObject(num // 2, Coord(Ratio.mm_to_px(x0), Ratio.mm_to_px(48), 0),
                                           Ratio.mm_to_px(287), 0)
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
                                           Ratio.mm_to_px(287 + 33), 2)
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

        solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(5), Ratio.mm_to_px(6), 2), solution_component))
        solution_object.height = solution_component.src_rect.height + Ratio.mm_to_px(6 + 3)

        return solution_object

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
                if sol_commentary_data[solution_info.hexcode] == 'SA':      #말풍선
                    so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                    solution_component = Component(code2pdf(self.unit_item_code), 0, solution_info.rect)
                    bubble_height = solution_component.src_rect.height + Ratio.mm_to_px(5)

                    # SA 내용 줄 수에 따른 변화
                    # 7.575 -> 13.008 -> 18.441 -> 23.874 -> 29.307
                    bubble_shade = ShapeOverlayObject(0, Coord(0, 0, -1), Rect(0, 0, Ratio.mm_to_px(105), bubble_height),
                                                      (0.2, 0, 0, 0), Ratio.mm_to_px(2.5)/bubble_height)
                    bubble_handle = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(85), bubble_height, 2),
                                                            self.get_component_on_resources(27))
                    '''
                    if bubble_height < Ratio.mm_to_px(13.008 - 1):
                        bubble_compo = 32
                    elif bubble_height < Ratio.mm_to_px(18.441 - 1):
                        bubble_compo = 33
                    elif bubble_height < Ratio.mm_to_px(23.874 - 1):
                        bubble_compo = 34
                    elif bubble_height < Ratio.mm_to_px(29.307 - 1):
                        bubble_compo = 35
                    else:
                        bubble_compo = 36
                    bubble = ComponentOverlayObject(0, Coord(0, 0, 0),
                                                    self.get_component_on_resources(bubble_compo))
                    '''
                    compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5), Ratio.mm_to_px(2.5), 2),
                                                   solution_component)

                    so.add_child(bubble_shade)
                    so.add_child(bubble_handle)
                    so.add_child(compo)

                    so.height = bubble_height + Ratio.mm_to_px(5 + 5 + 2.5)

                if sol_commentary_data[solution_info.hexcode] == 'answer':  # 정답
                    so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                    solution_component = self.get_component_on_resources(26)
                    soc = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 2),
                                                    solution_component)
                    answer = self.get_problem_answer(code2pdf(self.unit_item_code))
                    to = TextOverlayObject(0, Coord(Ratio.mm_to_px(26), Ratio.mm_to_px(5), 2),
                                                    "NanumSquareNeo-cBd.ttf", 16,
                                                    str(answer), (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
                    so.add_child(soc)
                    so.add_child(to)
                    so.height = solution_component.src_rect.height

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

    def bake_problem(self, item_code, number):
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        problem_title = self.bake_title_rel(item_code, number)
        problem.add_child(problem_title)
        problem.height += problem_title.get_height() + Ratio.mm_to_px(3)
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
                problem.height += Ratio.mm_to_px(8)
        else:
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

    def build_page_rel(self, item_number):
        list_rel_item_code = self.list_rel_item_code

        rel_doc = fitz.open()
        self.overlayer = Overlayer(rel_doc)

        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        i = 0
        for item_code in list_rel_item_code:
            problem = self.bake_problem(item_code, f'{item_number}{chr(i+65)}')
            i += 1
            paragraph_cnt = self.add_child_to_paragraph_rel(paragraph, problem, paragraph_cnt)

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        return rel_doc

    def add_child_to_paragraph_theory(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph_theory(paragraph, num)
        paragraph.add_child(child)
        return num + 1

    def append_new_list_to_paragraph_theory(self, paragraph: ParagraphOverlayObject, num):
        evenodd = (self.page + (num % 4) % 2) % 2

        if num % 4 == 0:
            self.overlayer.add_page(self.get_component_on_resources(30 + evenodd))
            pass
        elif num % 4 == 2:
            self.overlayer.add_page(self.get_component_on_resources(30 + evenodd))
            pass

        x0_list = [18, 133, 20, 135]  # LL, LR, RL, RR의 x0
        x0 = x0_list[num % 4]
        y0 = Ratio.mm_to_px(48)


        paragraph_list = ListOverlayObject(num // 2, Coord(Ratio.mm_to_px(x0), y0, 0),
                                           Ratio.mm_to_px(287), 0)
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
            piece.height += Ratio.mm_to_px(10)
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
                piece.height += piece_title.get_height() + Ratio.mm_to_px(5)
                #overlay 시 좌우 나누어서 18, 20 위치에 나오게 하기
                piece.overlay(self.overlayer, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(22), 0))
            i += 1
        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        return theory_doc

    def build_page_sol(self, item_number):
        sol_whole_doc = fitz.open()

        i = 0
        for item_code in self.list_rel_item_code:
            sol_item_doc = fitz.open()
            self.overlayer = Overlayer(sol_item_doc)
            first_page = AreaOverlayObject(0, Coord(0, 0, 0), 0)
            title_sol = self.bake_title_sol(item_code, f'{item_number}{chr(i+65)}')
            i += 1
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
                    if sol_commentary_data[solution_info.hexcode] == 'SA':      #말풍선
                        so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                        solution_component = Component(code2pdf(self.unit_item_code), 0, solution_info.rect)
                        bubble_height = solution_component.src_rect.height + Ratio.mm_to_px(5)

                        # SA 내용 줄 수에 따른 변화
                        # 7.575 -> 13.008 -> 18.441 -> 23.874 -> 29.307
                        bubble_shade = ShapeOverlayObject(0, Coord(0, 0, -1),
                                                          Rect(0, 0, Ratio.mm_to_px(105), bubble_height),
                                                          (0.2, 0, 0, 0), Ratio.mm_to_px(2.5) / bubble_height)
                        bubble_handle = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(85), bubble_height, 2),
                                                               self.get_component_on_resources(27))
                        '''
                        if bubble_height < Ratio.mm_to_px(13.008 - 1):
                            bubble_compo = 32
                        elif bubble_height < Ratio.mm_to_px(18.441 - 1):
                            bubble_compo = 33
                        elif bubble_height < Ratio.mm_to_px(23.874 - 1):
                            bubble_compo = 34
                        elif bubble_height < Ratio.mm_to_px(29.307 - 1):
                            bubble_compo = 35
                        else:
                            bubble_compo = 36
                        bubble = ComponentOverlayObject(0, Coord(0, 0, 0),
                                                        self.get_component_on_resources(bubble_compo))
                        '''
                        compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5), Ratio.mm_to_px(2.5), 2),
                                                       solution_component)

                        so.add_child(bubble_shade)
                        so.add_child(bubble_handle)
                        so.add_child(compo)

                        so.height = bubble_height + Ratio.mm_to_px(5 + 5 + 2.5)

                    if sol_commentary_data[solution_info.hexcode] == 'answer':  # 정답
                        so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
                        solution_component = self.get_component_on_resources(26)
                        soc = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 2),
                                                    solution_component)
                        answer = self.get_problem_answer(code2pdf(self.unit_item_code))
                        to = TextOverlayObject(0, Coord(Ratio.mm_to_px(26), Ratio.mm_to_px(5), 2),
                                               "NanumSquareNeo-cBd.ttf", 16,
                                               str(answer), (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
                        so.add_child(soc)
                        so.add_child(to)
                        so.height = solution_component.src_rect.height + Ratio.mm_to_px(3)

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

    def build_page_memo(self):
        memo_doc = fitz.open()
        memo_overlayer = Overlayer(memo_doc)
        memo_overlayer.add_page(self.get_component_on_resources(37))

        return memo_doc

#TODO: 홀/짝 맞춰서 x0 및 삽입 page 결정하는 logic