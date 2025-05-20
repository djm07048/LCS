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
class DuplexItemBuilder:
    def __init__(self, items, curr_page):
        self.items = items
        self.curr_page = curr_page
        self.doc_page = 0           #이번 doc에 한정한 page 번호
        self.resources_pdf = RESOURCES_PATH + "/duplex_item_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)
        self.rel_ref = {}
        self.rel_number = {}
        self.space_btw_problem = Ratio.mm_to_px(7)
        pass

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def get_problem_component(self, item_code):
        ic = ItemCropper()
        if item_code[5:7] == 'KC':
            item_pdf = code2original(item_code)
            trimmed_pdf = code2original(item_pdf).replace('_original.pdf', '_trimmed.pdf')
            if os.path.exists(trimmed_pdf):
                item_pdf = trimmed_pdf
        else:
            item_pdf = code2pdf(item_code)

        with fitz.open(item_pdf) as file:
            page = file.load_page(0)
            component = Component(item_pdf, 0, page.rect) if item_code[5:7] == 'KC' \
                else Component(item_pdf, 0, ic.get_problem_rect_from_file(file, accuracy=1))
        return component

    def bake_title_sd_sol(self, sd_code):
        source = sdcode2cite(sd_code)
        text_number = source.split(" ")[4][:-1]
        text_cite = source.split(" ")[1] + " " + source.split(" ")[2] + " " + source.split(" ")[3] + " " + source.split(" ")[4]

        compo = self.get_component_on_resources(3)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(15.32), Ratio.mm_to_px(9.7), 0), "Montserrat-Bold.ttf", 22,
                                    text_number, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(35), Ratio.mm_to_px(9), 0), "Pretendard-Bold.ttf", 16,
                                    text_cite, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        button = self.get_component_on_resources(5)
        x0 = Ratio.mm_to_px(35) + to_cite.get_width() + Ratio.mm_to_px(3)
        button = ComponentOverlayObject(0, Coord(x0, Ratio.mm_to_px(0), 2), button)

        box.add_child(to_number)
        box.add_child(to_cite)
        box.add_child(button)
        box.rect = compo.src_rect

        return box

    def bake_title_theory(self, sd_code, list_theory_piece_code):
        #piece_code = ["WIND UP 고체편 120p", "WIND UP 고체편 121p", "WIND UP 고체편 122p"]
        compo = self.get_component_on_resources(2)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        text_exam = ''.join(list_theory_piece_code[0].split(" ")[2])
        text_number = ', '.join([list_theory_piece_code[i].split(" ")[3] for i in range(len(list_theory_piece_code))])

        sd_source = sdcode2cite(sd_code)
        text_ref = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " " + "개념"

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(41), Ratio.mm_to_px(8.62), 0),
                                    "Pretendard-ExtraBold.ttf", 13,
                                    text_exam, (1, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(62), Ratio.mm_to_px(9), 0),
                                      "Pretendard-Bold.ttf", 16,
                                      text_number, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        to_ref = TextOverlayObject(0, Coord(Ratio.mm_to_px(215.8), Ratio.mm_to_px(11), 0), "Pretendard-Medium.ttf",10,
                                      text_ref, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_ref)

        box.rect = compo.src_rect

        return box

    def bake_title_rel_sol(self, sd_code, rel_code):
        sd_source = sdcode2cite(sd_code)
        text_number = str(sd_source.split(" ")[4][:-1]) + chr(64 + self.rel_number[rel_code])
        text_cite = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " 연계"
        if rel_code[5:7] == 'KC' or rel_code[5:7] == 'NC':
            text_ref = sdcode2cite(rel_code)            # 2026학년도 6월 12번 지1
        else:
            rel_source = self.rel_ref[rel_code]
            if rel_source:
                text_ref = "Squeeze " + rel_source.split("_")[-1]   #Squeeze 고체5 T번
            else:
                text_ref = "신규 문항"         #신규 문항

        compo = self.get_component_on_resources(1)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(15.32), Ratio.mm_to_px(9.7), 0), "Montserrat-Bold.ttf", 22,
                                    text_number, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(35), Ratio.mm_to_px(9), 0), "Pretendard-Bold.ttf", 16,
                                    text_cite, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
        to_ref = TextOverlayObject(0, Coord(Ratio.mm_to_px(213.8), Ratio.mm_to_px(11), 0), "Pretendard-Medium.ttf",10,
                                      text_ref, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)

        button = self.get_component_on_resources(6)
        x0 = Ratio.mm_to_px(35) + to_cite.get_width() + Ratio.mm_to_px(3)
        button = ComponentOverlayObject(0, Coord(x0, Ratio.mm_to_px(0), 2), button)

        box.add_child(to_number)
        box.add_child(to_cite)
        box.add_child(to_ref)
        box.add_child(button)
        box.rect = compo.src_rect

        return box

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

    def bake_solution_object(self, solution_info, TF, item_pdf):
        so = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        so_compo = Component(item_pdf, 0, solution_info.rect)

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
        if self.get_commentary_data()[solution_info.hexcode] == "answer":
            so_compo = self.get_component_on_resources(26)
            so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), Ratio.mm_to_px(0), 2), so_compo))
            answer = self.get_problem_answer(item_pdf)
            to = TextOverlayObject(0, Coord(Ratio.mm_to_px(24.5), Ratio.mm_to_px(5), 2),
                                    "NanumSquareNeo-cBd.ttf", 16,
                                    str(answer), (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
            so.add_child(to)
            so.height = so_compo.src_rect.height
        elif self.get_commentary_data()[solution_info.hexcode] == "SA":  # 말풍선
            shade = ShapeOverlayObject(0, Coord(0, 0, -1), Rect(0, 0, Ratio.mm_to_px(105), so_compo.src_rect.height + Ratio.mm_to_px(5)),
                                       (0.2, 0, 0, 0), Ratio.mm_to_px(2.5) / (so_compo.src_rect.height + Ratio.mm_to_px(5)))
            handle = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(90), so_compo.src_rect.height + Ratio.mm_to_px(5), 2),
                                            self.get_component_on_resources(27))
            compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5), Ratio.mm_to_px(2.5), 2),
                                           so_compo)
            so.add_child(shade)
            so.add_child(handle)
            so.add_child(compo)
            so.height = so_compo.src_rect.height + Ratio.mm_to_px(5 + 5 + 2.5)
        else:       #정오 선지
            res_page_num = self.get_sol_type_dict()[self.get_commentary_data()[solution_info.hexcode]]
            type_component = self.get_component_on_resources(res_page_num)
            so.add_child(ComponentOverlayObject(0, Coord(0, 0, 0), type_component))

            OX_component = None
            if TF == 1:
                OX_component = self.get_component_on_resources(7)
            if TF == 0:
                OX_component = self.get_component_on_resources(8)
            if OX_component is not None:
                so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 100), OX_component))

            so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(6.5), Ratio.mm_to_px(6), 2), so_compo))
            so.height = solution_info.rect.height + Ratio.mm_to_px(6)

        return so

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer, align):
        x0_list = [[Ratio.mm_to_px(22), Ratio.mm_to_px(133)], [Ratio.mm_to_px(18), Ratio.mm_to_px(129)]]     #[[우수 Lt, 우수 Rt], [좌수 Lt, 좌수 Rt]]
        y0 = Ratio.mm_to_px(47)     #24에는 제목이 들어가게 되어 있음, paragraph는 47부터 정의됨
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        x0 = x0_list[(self.doc_page + self.curr_page) % 2][(num + 1) % 2]     #페이지 우수 좌수 구분 후, 페이지 내 좌단과 우단 판별, 우단 부터 채우고, 좌단 채움
        paragraph_list = ListOverlayObject(self.doc_page, Coord(x0, y0, 0), height, align)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)
        pass

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer: Overlayer, align=0):  #아래로 정렬.
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph(paragraph, num, overlayer, align)
        paragraph.add_child(child)
        # 현재가 '좌단'이라면, 새로운 page를 만들어주고 끝내기.
        if num % 2 == 1:
            overlayer.add_page(self.get_component_on_resources(31 - (self.curr_page % 2)))      #홀짝 판정해야 해서 좌우 구분 필요
            self.curr_page += 1
        return num + 1

    def build_page_sd_sol(self, sd_code):
        self.doc_page = 0
        #page 정의
        doc_sd_sol = fitz.open()
        self.overlayer = Overlayer(doc_sd_sol)
        self.overlayer.add_page(self.get_component_on_resources(31 - self.curr_page % 2))        #첫페이지 삽입
        '''
        #title, problem 삽입
        area = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))
        title_sd_sol = self.bake_title_sd_sol(sd_code)
        area.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18 + (self.curr_page % 2) * 4), Ratio.mm_to_px(24)), title_sd_sol))
        problem = self.get_problem_component(sd_code)
        area.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18 + (self.curr_page % 2) * 4), Ratio.mm_to_px(47)), problem))
        area.overlay(self.overlayer, Coord(0, 0, 0))
        '''
        #paragraph 정의
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        sd_pdf = code2pdf(sd_code)
        with fitz.open(sd_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        solutions_info.reverse()                        #역순으로 채워야 해서 뒤집어야 함.
        for solution_info in solutions_info:
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], sd_pdf)
            self.add_child_to_paragraph(paragraph, so, paragraph_cnt, self.overlayer)

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        return doc_sd_sol

    def build_page_theory(self, sd_code, list_theory_piece_code):
        self.doc_page = 0
        # page 정의
        doc_theory = fitz.open()
        self.overlayer = Overlayer(doc_theory)
        self.overlayer.add_page(self.get_component_on_resources(31 - self.curr_page % 2))  # 첫페이지 삽입

        # title, problem 삽입
        area = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))
        title_theory = self.bake_title_theory(sd_code, list_theory_piece_code)
        tt_compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18 + (self.curr_page % 2) * 4), Ratio.mm_to_px(24)), title_theory)
        area.add_child(tt_compo)
        area.overlay(self.overlayer, Coord(0, 0, 0))

        # paragraph 정의
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        for piece_code in list_theory_piece_code:
            piece = self.bake_theory_piece(piece_code)
            self.add_child_to_paragraph(paragraph, piece, paragraph_cnt, self.overlayer, align=0)
        paragraph.overlay(self.overlayer, Coord(0, 0, 0))
        return doc_theory

    def build_page_rel_sol(self, sd_code, rel_code):
        self.doc_page = 0
        # page 정의
        doc_rel_sol = fitz.open()
        self.overlayer = Overlayer(doc_rel_sol)
        self.overlayer.add_page(self.get_component_on_resources(31 - self.curr_page % 2))  # 첫페이지 삽입
        '''
        # title, problem 삽입
        area = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(347))
        title_rel_sol = self.bake_title_rel_sol(sd_code, rel_code)
        area.add_child(
            ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18 + (self.curr_page % 2) * 4), Ratio.mm_to_px(24)),
                                   title_rel_sol))
        problem = self.get_problem_component(rel_code)
        area.add_child(
            ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18 + (self.curr_page % 2) * 4), Ratio.mm_to_px(47)),
                                   problem))
        area.overlay(self.overlayer, Coord(0, 0, 0))
        '''
        # paragraph 정의
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        rel_pdf = code2pdf(rel_code)
        with fitz.open(rel_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        solutions_info.reverse()  # 역순으로 채워야 해서 뒤집어야 함.
        for solution_info in solutions_info:
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], rel_pdf)
            self.add_child_to_paragraph(paragraph, so, paragraph_cnt, self.overlayer)

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))

        return doc_rel_sol

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


    '''
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
                        to = TextOverlayObject(0, Coord(Ratio.mm_to_px(24.5), Ratio.mm_to_px(5), 2),
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
    '''
    def build_page_memo(self):
        memo_doc = fitz.open()
        memo_overlayer = Overlayer(memo_doc)
        memo_overlayer.add_page(self.get_component_on_resources(37))

        return memo_doc
