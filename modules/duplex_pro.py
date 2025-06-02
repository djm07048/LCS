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

class DuplexProBuilder:
    def __init__(self, items, curr_page):
        self.items = items
        self.curr_page = curr_page
        self.resources_pdf = RESOURCES_PATH + "/duplex_item_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)
        self.rel_ref = {}
        self.rel_number = {}
        self.space_btw_problem = Ratio.mm_to_px(25)
        for i in self.items.keys():
            number = 1
            for rel_item in self.items[i]['list_rel_item_code']:
                self.rel_ref.update({rel_item : self.get_related_item_reference(rel_item)})
                self.rel_number.update({rel_item : number})
                number += 1
        pass

    def get_related_item_reference(self, item_code):
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

    #bake titles
    def bake_title_sd(self, sd_code):
        source = sdcode2cite(sd_code)
        text_number = source.split(" ")[4][:-1]
        text_cite = source.split(" ")[1] + " " + source.split(" ")[2] + " " + source.split(" ")[3] + " " + source.split(" ")[4]

        compo = self.get_component_on_resources(0)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(4.5), Ratio.mm_to_px(11.67), 0), "Montserrat-Bold.ttf", 22,
                                    text_number, (0, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)
        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(215.3), Ratio.mm_to_px(5.6), 0), "Pretendard-Medium.ttf",10,
                                      text_cite, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_number)
        box.add_child(to_cite)
        box.rect = compo.src_rect

        return box

    def bake_title_rel(self, sd_code, rel_code):
        sd_source = sdcode2cite(sd_code)
        text_number = str(sd_source.split(" ")[4][:-1]) + chr(64 + self.rel_number[rel_code])
        text_cite = sd_source.split(" ")[1] + " " + sd_source.split(" ")[2] + " " + sd_source.split(" ")[3] + " " + sd_source.split(" ")[4] + " 연계"
        if rel_code[5:7] == 'KC' or rel_code[5:7] == 'NC':
            text_ref = code2cite(rel_code)            # 2026학년도 6월 12번 지1
        else:
            rel_source = self.rel_ref[rel_code]
            if rel_source:
                text_ref = "Squeeze " + rel_source.split("_")[-2] + " " + rel_source.split("_")[-1] #Squeeze 고체5 T번
            else:
                text_ref = "신규 문항"         #신규 문항

        compo = self.get_component_on_resources(1)
        box = ComponentOverlayObject(0, Coord(0,0,0), compo)

        to_number = TextOverlayObject(0, Coord(Ratio.mm_to_px(4.5), Ratio.mm_to_px(11.67), 0), "Montserrat-Bold.ttf", 22,
                                    text_number, (0, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)
        to_cite = TextOverlayObject(0, Coord(Ratio.mm_to_px(215.3), Ratio.mm_to_px(5.6), 0), "Pretendard-Medium.ttf",10,
                                      text_cite, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)
        to_ref = TextOverlayObject(0, Coord(Ratio.mm_to_px(213.8), Ratio.mm_to_px(11), 0), "Pretendard-Medium.ttf",10,
                                      text_ref, (0, 0, 0, 0.8), fitz.TEXT_ALIGN_RIGHT)

        box.add_child(to_number)
        box.add_child(to_cite)
        box.add_child(to_ref)
        box.rect = compo.src_rect

        return box

    def bake_problem_sd(self, sd_code):
        #title 추가
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        problem_title = self.bake_title_sd(sd_code)
        problem.add_child(problem_title)
        modified_pdf = code2modified(sd_code)

        #component 추가
        component = self.get_problem_component(sd_code)
        problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(44), Ratio.mm_to_px(8), 0), component)
        white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(44), Ratio.mm_to_px(8), 0),
                                       Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                       (0, 0, 0, 0))
        curr_height = problem_object.get_height() + Ratio.mm_to_px(8)
        problem.add_child(problem_object)
        problem_object.add_child(white_box)

        #modified 추가
        if Path(modified_pdf).exists():
            with fitz.open(modified_pdf) as mod_file:
                mod_page = mod_file.load_page(0)
                modified_box = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(44), curr_height + Ratio.mm_to_px(2.5), 0),
                                                      Component(modified_pdf, 0, mod_page.rect))
                problem.add_child(modified_box)
                curr_height += modified_box.get_height() + Ratio.mm_to_px(2.5)     #더해지는 값이 원본 - 수정사항박스 간 간격을 결정함
        problem.height = curr_height + self.space_btw_problem                      #더해지는 값이 문항 - 문항 간 간격을 결정함
        return problem


    def bake_problem_rel(self, sd_code, rel_code):
        #title 추가
        problem = AreaOverlayObject(0, Coord(0, 0, 0), 0)
        problem_title = self.bake_title_rel(sd_code, rel_code)
        problem.add_child(problem_title)
        modified_pdf = code2modified(sd_code)

        #rel_component 추가
        rel_component = self.get_problem_component(rel_code)
        problem_object = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(44), Ratio.mm_to_px(8), 0), rel_component)
        white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(44), Ratio.mm_to_px(8), 0),
                                       Rect(0, 0, Ratio.mm_to_px(3), Ratio.mm_to_px(5.5)),
                                       (0, 0, 0, 0))
        curr_height = problem_object.get_height() + Ratio.mm_to_px(8)
        problem.add_child(problem_object)
        problem_object.add_child(white_box)

        #modified 추가
        if Path(modified_pdf).exists():
            with fitz.open(modified_pdf) as mod_file:
                mod_page = mod_file.load_page(0)
                modified_box = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(44), curr_height + Ratio.mm_to_px(2.5), 0),
                                                      Component(modified_pdf, 0, mod_page.rect))
                problem.add_child(modified_box)
                curr_height += modified_box.get_height() + Ratio.mm_to_px(2.5)     #더해지는 값이 원본 - 수정사항박스 간 간격을 결정함
        problem.height = curr_height + self.space_btw_problem                      #더해지는 값이 문항 - 문항 간 간격을 결정함
        return problem

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer: Overlayer,
                                           local_start_page):
        x0_list = [[Ratio.mm_to_px(22), Ratio.mm_to_px(133)],
                   [Ratio.mm_to_px(18), Ratio.mm_to_px(129)]]  # [[우수 Lt, 우수 Rt], [좌수 Lt, 좌수 Rt]]
        y0 = Ratio.mm_to_px(24)
        y1 = Ratio.mm_to_px(347)
        height = y1 - y0

        # 현재 작업 중인 페이지의 절대 번호 계산
        current_absolute_page = local_start_page + overlayer.doc.page_count - 1

        # 현재 페이지의 짝/홀수 확인 (우수/좌수)
        page_side = current_absolute_page % 2

        x0 = x0_list[page_side][0]  # 항상 왼쪽 컬럼 사용 (single column layout)

        # 새 리스트 생성 및 추가 (문서 내 페이지 인덱스 사용)
        doc_page_index = overlayer.doc.page_count - 1
        paragraph_list = ListOverlayObject(doc_page_index, Coord(x0, y0, 0), height, 2)
        paragraph.add_paragraph_list(paragraph_list=paragraph_list)

        pass

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num,
                                     overlayer: Overlayer, local_start_page):
        if paragraph.add_child(child):
            return num
        # 새로운 page를 만들어주고 끝내기
        # 새로 추가될 페이지의 절대 번호 계산
        new_absolute_page = local_start_page + overlayer.doc.page_count
        template_page_num = 29 - (new_absolute_page % 2)  # 홀짝 판정해서 좌우 구분
        overlayer.add_page(self.get_component_on_resources(template_page_num))

        # 새 리스트 생성
        self.append_new_list_to_paragraph(paragraph, num, overlayer, local_start_page)
        paragraph.add_child(child)

        # num 증가
        num += 1
        return num

    def build_page_pro(self):
        local_start_page = self.curr_page

        pro_doc = fitz.open()
        self.overlayer = Overlayer(pro_doc)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0

        for sd_code in self.items.keys():
            problem_sd = self.bake_problem_sd(sd_code)
            paragraph_cnt = self.add_child_to_paragraph(paragraph, problem_sd, paragraph_cnt, self.overlayer, local_start_page)

            for rel_code in self.items[sd_code]['list_rel_item_code']:
                problem_rel = self.bake_problem_rel(sd_code, rel_code)
                paragraph_cnt = self.add_child_to_paragraph(paragraph, problem_rel, paragraph_cnt, self.overlayer, local_start_page)

        paragraph.overlay(self.overlayer, Coord(0,0,0))

        # 완료 후 전역 카운터 업데이트
        self.curr_page += pro_doc.page_count

        return pro_doc