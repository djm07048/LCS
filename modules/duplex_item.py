from modules.item_cropper import ItemCropper
from modules.overlayer import Overlayer
from pathlib import Path
import fitz
from utils.ratio import Ratio
from utils.pdf_utils import PdfUtils
from utils.solution_info import ThemeInfo
from utils.overlay_object import *
from utils.coord import Coord
from utils.path import *
from item_cropper import ItemCropper
import json

# item마다의 정보를 담는 클래스

import os
import json
class DuplexItemBuilder:
    def __init__(self, items, curr_page, book_name):
        self.items = items
        self.book_name = book_name
        self.curr_page = curr_page
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
            trimmed_pdf = item_pdf.replace('.pdf', '_trimmed.pdf')
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
        if sd_code[5:7] == 'KC' or sd_code[5:7] == 'NC':
            source = code2cite(sd_code)     #'{2026}학년도 {6월} {20}번 {지1}'
            text_number = source.split(" ")[2][:-1]
            text_cite = source

        else:
            source = sdcode2cite(sd_code)
            text_number = source.split(" ")[4][:-1]
            text_cite = source.split(" ")[1] + " " + source.split(" ")[2] + " " + source.split(" ")[3] + " " + source.split(" ")[4]

        compo = self.get_component_on_resources(3)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(15.88), Ratio.mm_to_px(9.7), 0), "Montserrat-Bold.ttf", 22,
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
        if sd_code[5:7] == 'KC' or sd_code[5:7] == 'NC':
            source = code2cite(sd_code)  # '{2026}학년도 {6월} {20}번 {지1}' or '{2026}학년도
            text_cite = source + " 개념"

        else:
            sd_source = sdcode2cite(sd_code)
            text_cite = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + \
                        sd_source.split(" ")[4] + " " + "개념"


        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(41), Ratio.mm_to_px(8.62), 0),
                                    "Pretendard-ExtraBold.ttf", 13,
                                    text_exam, (1, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(62), Ratio.mm_to_px(9), 0),
                                      "Pretendard-Bold.ttf", 16,
                                      text_number, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(215.3), Ratio.mm_to_px(5.6), 0), "Pretendard-Medium.ttf",10,
                                      text_cite, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)
        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_cite)

        box.rect = compo.src_rect

        return box
    def bake_title_theory_sv(self, sd_code, list_theory_piece_code):
        #piece_code = ["WIND UP 고체편 120p", "WIND UP 고체편 121p", "WIND UP 고체편 122p"]
        compo = self.get_component_on_resources(35)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        text_exam = ''.join(list_theory_piece_code[0].split(" ")[2])
        text_number = ', '.join([list_theory_piece_code[i].split(" ")[3] for i in range(len(list_theory_piece_code))])

        if sd_code[5:7] == 'KC' or sd_code[5:7] == 'NC':
            source = code2cite(sd_code)  # '{2026}학년도 {6월} {20}번 {지1}' or '{2026}학년도
            text_sd_number = source.split(" ")[2][:-1]
            text_cite = source + " 개념"

        else:
            sd_source = sdcode2cite(sd_code)
            text_sd_number = sd_source.split(" ")[4][:-1]
            text_cite = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + \
                        sd_source.split(" ")[4] + " " + "개념"

        to_sd_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(15.88), Ratio.mm_to_px(9.7), 0), "Montserrat-Bold.ttf", 22,
                                    text_sd_number, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)

        to_exam = TextOverlayObject(0, Coord(Ratio.mm_to_px(71), Ratio.mm_to_px(8.62), 0),
                                    "Pretendard-ExtraBold.ttf", 13,
                                    text_exam, (1, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(92), Ratio.mm_to_px(9), 0),
                                      "Pretendard-Bold.ttf", 16,
                                      text_number, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(215.3), Ratio.mm_to_px(5.6), 0), "Pretendard-Medium.ttf",10,
                                      text_cite, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)
        box.add_child(to_sd_number)
        box.add_child(to_exam)
        box.add_child(to_number)
        box.add_child(to_cite)

        box.rect = compo.src_rect

        return box

    def bake_title_rel_sol(self, sd_code, rel_code):
        if sd_code[5:7] == 'KC' or sd_code[5:7] == 'NC':
            source = code2cite(sd_code)     #'{2026}학년도 {6월} {20}번 {지1}'
            text_number = source.split(" ")[2][:-1] + chr(64 + self.rel_number[rel_code])
            text_cite = source + " 연계"
        else:
            sd_source = sdcode2cite(sd_code)
            text_number = str(sd_source.split(" ")[4][:-1]) + chr(64 + self.rel_number[rel_code])
            text_cite = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " 연계"

        if rel_code[5:7] == 'KC' or rel_code[5:7] == 'NC':
            text_ref = code2cite(rel_code)            # 2026학년도 6월 12번 지1
        else:
            rel_source = self.rel_ref[rel_code]
            if rel_source:
                text_ref = "Squeeze " + rel_source.split("_")[-2] + " " + rel_source.split("_")[-1]   #Squeeze 고체5 T번
            else:
                text_ref = "신규 문항"         #신규 문항

        compo = self.get_component_on_resources(4)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(12.88), Ratio.mm_to_px(9.7), 0), "Montserrat-Bold.ttf", 22,
                                    text_number, (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER)
        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(215.3), Ratio.mm_to_px(5.6), 0), "Pretendard-Medium.ttf", 10,
                                    text_cite, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)
        to_ref = TextOverlayObject(0, Coord(Ratio.mm_to_px(35), Ratio.mm_to_px(9), 0), "Pretendard-Bold.ttf", 16,
                                    text_ref, (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)

        button = self.get_component_on_resources(6)
        x0 = Ratio.mm_to_px(35) + to_ref.get_width() + Ratio.mm_to_px(3)
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

    def bake_solution_object(self, solution_info, TF, item_pdf, FigType="그림"):
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
            so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2), Ratio.mm_to_px(0), 2), so_compo))
            answer = self.get_problem_answer(item_pdf)
            to = TextOverlayObject(0, Coord(Ratio.mm_to_px(24.5 + 2), Ratio.mm_to_px(5), 2),
                                    "NanumSquareNeo-cBd.ttf", 16,
                                    str(answer), (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT)
            so.add_child(to)
            so.height = so_compo.src_rect.height + Ratio.mm_to_px(3.5)

        elif self.get_commentary_data()[solution_info.hexcode] == "SA":  # 말풍선
            shade = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(2), 0, -1), Rect(0, 0, Ratio.mm_to_px(105), so_compo.src_rect.height + Ratio.mm_to_px(5)),
                                       (0.2, 0, 0, 0), Ratio.mm_to_px(2.5) / (so_compo.src_rect.height + Ratio.mm_to_px(5)))
            handle = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(90 + 2), so_compo.src_rect.height + Ratio.mm_to_px(5), 2),
                                            self.get_component_on_resources(27))
            compo = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(2.5 + 2), Ratio.mm_to_px(2.5), 2),
                                           so_compo)
            so.add_child(shade)
            so.add_child(handle)
            so.add_child(compo)
            so.height = so_compo.src_rect.height + Ratio.mm_to_px(5 + 5 + 2.5)

        elif self.get_commentary_data()[solution_info.hexcode][:1] == "S" and self.get_commentary_data()[solution_info.hexcode] != "SA":  # 일반 해설
            # 로고 추가
            type_component = self.get_component_on_resources(34)
            so.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 0), type_component))

            # 자료 이름 추가
            if FigType:
                to_fig_type = TextOverlayObject(0, Coord(Ratio.mm_to_px(26), Ratio.mm_to_px(5.15), 2),
                                                "Pretendard-Medium.ttf", 12, FigType, (0, 0, 0, 1),
                                                fitz.TEXT_ALIGN_LEFT)
                so.add_child(to_fig_type)

            # 내용 컴포넌트 추가
            so_compo = Component(item_pdf, 0, solution_info.rect)
            so_shade = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(3), Ratio.mm_to_px(10), 2),
                                          Rect(0, 0, Ratio.mm_to_px(102), so_compo.src_rect.height + Ratio.mm_to_px(2)),
                                          (0.1, 0, 0, 0))
            so_cco = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(4), Ratio.mm_to_px(11), 2),
                                            so_compo)
            so.add_child(so_shade)
            so.add_child(so_cco)
            so.height = so_compo.src_rect.height + Ratio.mm_to_px(12 + 5)

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
            so.height = solution_info.rect.height + Ratio.mm_to_px(7)

        return so

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer, local_start_page, align):
        # 페이지 레이아웃 설정
        x0_list = [[Ratio.mm_to_px(22), Ratio.mm_to_px(136)], [Ratio.mm_to_px(18), Ratio.mm_to_px(132)]]
        y0 = Ratio.mm_to_px(47)
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        # 현재 페이지의 짝/홀수 확인 (우수/좌수)
        current_absolute_page = local_start_page + overlayer.doc.page_count - 1
        page_side = current_absolute_page % 2

        # 우단 -> 좌단 순으로 적재
        # num이 짝수(0,2,4...)면 우단, 홀수(1,3,5...)면 좌단
        column = (num + 1) % 2

        # 좌표 선택
        x0 = x0_list[page_side][column]

        # 새 리스트 생성 및 추가
        doc_page_index = overlayer.doc.page_count - 1
        paragraph_list = ListOverlayObject(doc_page_index, Coord(x0, y0, 0), height, align)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer: Overlayer, local_start_page, item_number=1, align=3):
        if child is None:
            print("Warning: child is None")
            return num
        # 기존 리스트에 추가 가능하면 추가하고 num 그대로 반환
        if paragraph.add_child(child):
            return num

        # 첫 번째 리스트인 경우 (num=0)
        if num == 0:
            # 첫 번째 리스트 생성 (우단)
            self.append_new_list_to_paragraph(paragraph, num, overlayer, local_start_page, align)
            paragraph.add_child(child)
            return num + 1

        # 두 번째 이상의 리스트인 경우

        # 이전 열 확인 (num-1의 열)
        prev_column = (num - 1) % 2

        # 이전 열이 좌단(1)이면 다음 페이지로 넘어감 (우단->좌단 순서에서)
        if prev_column == 1:  # 좌단이 채워짐 -> 새 페이지 필요
            # 현재 페이지의 짝/홀수 확인
            new_absolute_page = local_start_page + overlayer.doc.page_count
            template_page_num = 31 - (new_absolute_page % 2)

            self.add_page_with_index(overlayer, template_page_num, item_number, local_start_page)

        # 새 리스트 추가
        self.append_new_list_to_paragraph(paragraph, num, overlayer, local_start_page, align)
        paragraph.add_child(child)
        return num + 1

    def append_new_list_to_paragraph_piece(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer,
                                                 local_start_page, align):
        # 페이지 레이아웃 설정
        x0_list = [[Ratio.mm_to_px(22), Ratio.mm_to_px(136)], [Ratio.mm_to_px(18), Ratio.mm_to_px(132)]]
        y0 = Ratio.mm_to_px(47)
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        # 현재 작업 중인 페이지의 절대 번호 계산
        current_absolute_page = local_start_page + overlayer.doc.page_count - 1

        # 현재 페이지의 짝/홀수 확인 (우수/좌수)
        page_side = current_absolute_page % 2

        # 좌단 -> 우단 순으로 적재
        column = num % 2

        # 좌표 선택
        x0 = x0_list[page_side][column]

        # 새 리스트 생성 및 추가 (문서 내 페이지 인덱스 사용)
        doc_page_index = overlayer.doc.page_count - 1
        paragraph_list = ListOverlayObject(doc_page_index, Coord(x0, y0, 0), height, align)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)

    def add_child_to_paragraph_piece(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num,
                                           overlayer: Overlayer, local_start_page, item_number=1, align=0):
        # 기존 리스트에 추가 가능하면 추가하고 num 그대로 반환
        if paragraph.add_child(child):
            return num

        # 첫 번째 리스트인 경우 (==0)
        if len(paragraph.child) == 0:
            # 첫 번째 리스트 생성 (좌단)
            self.append_new_list_to_paragraph_piece(paragraph, num, overlayer, local_start_page, align)
            paragraph.add_child(child)
            return num + 1

        # 이전 열 확인 (num-1의 열)
        prev_column = (num - 1) % 2

        # 이전 열이 우단(1)이면 다음 페이지로 넘어감
        if prev_column == 1:  # 우단이 채워짐 -> 새 페이지 필요
            # 새로 추가될 페이지의 절대 번호 계산
            new_absolute_page = local_start_page + overlayer.doc.page_count
            template_page_num = 31 - (new_absolute_page % 2)

            # 새 페이지 추가
            self.add_page_with_index(overlayer, template_page_num, item_number, local_start_page)

        # 새 리스트 추가
        self.append_new_list_to_paragraph_piece(paragraph, num, overlayer, local_start_page, align)
        paragraph.add_child(child)

        return num + 1

    def build_page_sd_sol(self, sd_code):
        # 로컬 페이지 기준점 설정
        local_start_page = self.curr_page
        item_number = self.items[sd_code]['number']

        doc_sd_sol = fitz.open()
        overlayer = Overlayer(doc_sd_sol)

        # 페이지 인덱스 추가
        self.add_page_with_index(overlayer, 31 - local_start_page % 2, item_number, local_start_page)

        # 페이지 전체 컨테이너 생성 (문서 내 0번 페이지)
        page_container = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))

        # 제목 컴포넌트 추가 (로컬 기준)
        title_sd_sol = self.bake_title_sd_sol(sd_code)
        current_page_index = local_start_page + overlayer.doc.page_count - 1
        page_side = current_page_index % 2
        title_x = Ratio.mm_to_px(22 - page_side * 4)
        title_sd_sol.coord = Coord(title_x, Ratio.mm_to_px(24), 0)
        page_container.add_child(title_sd_sol)

        # 문제 컴포넌트 추가 (로컬 기준)
        problem = self.get_problem_component(sd_code)
        problem_x = Ratio.mm_to_px(22 - (local_start_page % 2) * 4 - 0.762)
        problem_compo = ComponentOverlayObject(0, Coord(problem_x, Ratio.mm_to_px(47), 0), problem)
        page_container.add_child(problem_compo)

        # 전체 컨테이너 오버레이
        page_container.overlay(overlayer, Coord(0, 0, 0))

        # 솔루션 부분 (로컬 기준으로 처리)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        sd_pdf = code2pdf(sd_code)
        with fitz.open(sd_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        solutions_info.reverse()
        for solution_info in solutions_info:
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], sd_pdf)
            paragraph_cnt = self.add_child_to_paragraph(paragraph, so, paragraph_cnt, overlayer, local_start_page, item_number)

        paragraph.overlay(overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_sd_sol.page_count

        return doc_sd_sol

    def build_page_theory(self, sd_code, list_theory_piece_code):
        # 로컬 페이지 기준점 설정
        local_start_page = self.curr_page
        item_number = self.items[sd_code]['number']

        doc_theory = fitz.open()
        overlayer = Overlayer(doc_theory)

        # 페이지 인덱스 추가
        self.add_page_with_index(overlayer, 31 - local_start_page % 2, item_number, local_start_page)

        # 페이지 전체 컨테이너 생성
        page_container = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))

        # 제목 컴포넌트 추가 (로컬 기준)
        if self.book_name[0:2] == "SV":
            title_theory = self.bake_title_theory_sv(sd_code, list_theory_piece_code)
        else:
            title_theory = self.bake_title_theory(sd_code, list_theory_piece_code)
        current_page_index = local_start_page + overlayer.doc.page_count - 1
        page_side = current_page_index % 2
        title_x = Ratio.mm_to_px(22 - page_side * 4)
        title_theory.coord = Coord(title_x, Ratio.mm_to_px(24), 0)
        page_container.add_child(title_theory)

        # 전체 컨테이너 오버레이
        page_container.overlay(overlayer, Coord(0, 0, 0))

        # 이론 조각 부분 처리 (로컬 기준)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 1       #좌단이 비어있음.

        pcsv = self.bake_problem_comment_sv(sd_code)
        pcsv.overlay(overlayer, Coord(Ratio.mm_to_px(22 - (local_start_page % 2) * 4), Ratio.mm_to_px(47), 0))
        for piece_code in list_theory_piece_code:
            piece = self.bake_theory_piece(piece_code)
            paragraph_cnt = self.add_child_to_paragraph_piece(paragraph, piece, paragraph_cnt, overlayer,
                                                                    local_start_page, item_number, align=0)

        paragraph.overlay(overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_theory.page_count
        return doc_theory

    def build_page_rel_sol(self, sd_code, rel_code):
        # 로컬 페이지 기준점 설정
        local_start_page = self.curr_page
        item_number = self.items[sd_code]['number']

        doc_rel_sol = fitz.open()
        overlayer = Overlayer(doc_rel_sol)

        # 첫 페이지 추가 (로컬 기준)
        # 페이지 인덱스 추가
        self.add_page_with_index(overlayer, 31 - local_start_page % 2, item_number, local_start_page)

        # 페이지 전체 컨테이너 생성
        page_container = AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(371))

        # 제목 컴포넌트 추가 (로컬 기준)
        current_page_index = local_start_page + overlayer.doc.page_count - 1
        page_side = current_page_index % 2
        title_rel_sol = self.bake_title_rel_sol(sd_code, rel_code)
        title_x = Ratio.mm_to_px(22 - page_side * 4)
        title_rel_sol.coord = Coord(title_x, Ratio.mm_to_px(24), 0)
        page_container.add_child(title_rel_sol)

        # 문제 컴포넌트 추가 (로컬 기준)
        problem = self.get_problem_component(rel_code)
        problem_x = Ratio.mm_to_px(22 - (local_start_page % 2) * 4 - 0.762)
        problem_compo = ComponentOverlayObject(0, Coord(problem_x, Ratio.mm_to_px(47), 0), problem)
        page_container.add_child(problem_compo)

        # 전체 컨테이너 오버레이
        page_container.overlay(overlayer, Coord(0, 0, 0))

        # 솔루션 부분 (로컬 기준으로 처리)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        rel_pdf = code2pdf(rel_code)
        with fitz.open(rel_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        solutions_info.reverse()
        for solution_info in solutions_info:
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], rel_pdf)
            paragraph_cnt = self.add_child_to_paragraph(paragraph, so, paragraph_cnt, overlayer, local_start_page, item_number)

        paragraph.overlay(overlayer, Coord(0, 0, 0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += doc_rel_sol.page_count
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
            "SB": 34,  # linking 2
            "SC": 34,  # linking 3
            "SD": 34,  # linking 4
            "SE": 34  # linking 5
        }
        return sol_type_dict

    def get_problem_answer(self, item_pdf):
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            return answer

    def bake_problem_comment_sv(self, item_code):
        # title 추가
        curr_y = 0
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        item_pdf = code2pdf(item_code)
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sFigType = ic.get_fig_type_of_solutions_from_file(file, 10)

        for solution_info in solutions_info:
            commentary_key = self.get_commentary_data()[solution_info.hexcode]
            if commentary_key[:1] == "S" and commentary_key != "SA":
                # so는 AreaOverlayObject
                so = self.bake_solution_object(solution_info, None, item_pdf, sFigType[solution_info.hexcode])
                so.coord.y = curr_y
                problem.add_child(so)
                solution_height = so.get_height() + Ratio.mm_to_px(2)
                curr_y += solution_height  # curr_y는 개별 높이만 더하기

        problem.height = curr_y
        return problem


    def get_commentary_data(self):
        with open(RESOURCES_PATH + "/commentary.json") as file:
            commentary_data = json.load(file)
        return commentary_data

    def build_page_memo(self):
        memo_doc = fitz.open()
        memo_overlayer = Overlayer(memo_doc)
        memo_overlayer.add_page(self.get_component_on_resources(37))

        return memo_doc

    def add_page_with_index(self, overlayer, resource_page_num, item_number, local_start_page):
        overlayer.add_page(self.get_component_on_resources(resource_page_num))
        """
        Args:
            overlayer: Overlayer 객체
            item_number: 표시할 문항번호 (1, 2, 3...)
            page_num: 실제 페이지 번호
        """
        current_page_index = overlayer.doc.page_count - 1
        page_num = local_start_page + current_page_index
        print(f"Adding page with index: {resource_page_num}, item_number: {item_number}, current_page_index: {current_page_index}, page_num: {page_num}")
        index_object = self.get_component_on_resources(32 + (page_num % 2))
        x0 = Ratio.mm_to_px(0) if page_num % 2 == 1 else Ratio.mm_to_px(250)
        y0 = Ratio.mm_to_px(8 + 16 * item_number)

        page_num_object = ComponentOverlayObject(current_page_index, Coord(x0, y0, 10), index_object)

        xText = Ratio.mm_to_px(10.5) if page_num % 2 == 1 else Ratio.mm_to_px(1.5)
        yText = Ratio.mm_to_px(7.764)
        align = fitz.TEXT_ALIGN_RIGHT if page_num % 2 == 1 else fitz.TEXT_ALIGN_LEFT

        to = TextOverlayObject(current_page_index, Coord(xText, yText, 10),
                               "Pretendard-Bold.ttf", 15, str(item_number),
                               (0, 0, 0, 0), align)

        page_num_object.add_child(to)
        page_num_object.overlay(overlayer, page_num_object.coord)