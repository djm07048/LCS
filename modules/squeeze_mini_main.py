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
from modules.squeeze_main import MainsolBuilder
import json


# KC이면 문항은 original, 해설은 Main에서 가져옴
# NC or 자작이면 문항은 pdf, 해설도 pdf에서 가져옴

class MainsolBuilderSqueezeMini(MainsolBuilder):
    def build_right(self, item_code, page_num):
        # Main Solution 우수 Page: 문항 번호, 문제 이미지, 원본 이미지, 해설 조각

        for item in self.get_item_list():
            if item['item_code'] == item_code:
                item_num = item['mainsub']
        right_page = AreaOverlayObject(page_num, Coord(0, 0, 0), Ratio.mm_to_px(371))
        origin = self.bake_origin(item_code)
        topic = self.bake_topic(item_code)

        component = self.get_problem_component(item_code)
        right_page.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(118), Ratio.mm_to_px(46), 0), component))
        right_page.add_child(
            TextOverlayObject(0, Coord(Ratio.mm_to_px(108), Ratio.mm_to_px(59), 0), "Montserrat-Bold.ttf", 48, item_num,
                              (1, 0, 0, 0), fitz.TEXT_ALIGN_RIGHT))
        origin.coord = Coord(Ratio.mm_to_px(108) - origin.rect.width, Ratio.mm_to_px(64), 0)
        right_page.add_child(origin)
        topic.coord = Coord(Ratio.mm_to_px(108) - topic.rect.width, Ratio.mm_to_px(71.5), 0)
        right_page.add_child(topic)
        white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(118 - 0.5), Ratio.mm_to_px(46), 0),
                                       Rect(0, 0, Ratio.mm_to_px(3.0 + 0.5), Ratio.mm_to_px(5.5)), (1, 1, 1))
        right_page.add_child(white_box)

        y_end = 46 + Ratio.px_to_mm(component.src_rect.height)

        # 최대 사이즈를 기본 값으로 설정
        memo_component = self.get_component_on_resources(43)
        if y_end < 180:
            memo_component = self.get_component_on_resources(39)
        elif y_end < 197.5:
            memo_component = self.get_component_on_resources(40)
        elif y_end < 211:
            memo_component = self.get_component_on_resources(41)
        elif y_end < 238:
            memo_component = self.get_component_on_resources(42)
        elif y_end < 278.5:
            memo_component = self.get_component_on_resources(43)
        right_page.add_child(ComponentOverlayObject(0, Coord(0, 0, 0), memo_component))
        return right_page

    def build_left(self, item_code, page_num):
        for item in self.get_item_list():
            if item['item_code'] == item_code:
                item_num = item['mainsub']
        left_page = AreaOverlayObject(page_num, Coord(0, 0, 0), Ratio.mm_to_px(371))
        left_page.add_child(
            TextOverlayObject(0, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(59), 0), "Montserrat-Bold.ttf", 48, item_num,
                              (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT))
        origin = self.bake_origin(item_code)
        origin.coord = Coord(Ratio.mm_to_px(50), Ratio.mm_to_px(59 - 2 - 11), 0)
        # topic을 추가한 것이 다르다.
        topic = self.bake_topic(item_code)
        topic.coord = Coord(Ratio.mm_to_px(50), Ratio.mm_to_px(59 - 5.5), 0)

        left_page.add_child(origin)
        left_page.add_child(topic)

        white_box = ShapeOverlayObject(0, Coord(Ratio.mm_to_px(18 - 8), Ratio.mm_to_px(65.5), 0),
                                       Rect(0, 0, Ratio.mm_to_px(3 + 8), Ratio.mm_to_px(5.5)), (1, 1, 1))
        left_page.add_child(white_box)

        component = self.get_problem_component(item_code)
        if isinstance(component, str):
            component = Component(component, 0, fitz.Rect(0, 0, 0, 0))  # Create a Component object if it's a string

        if not hasattr(component, 'src_pdf'):
            raise AttributeError(f"Component does not have 'src_pdf' attribute: {component}")

        left_page.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(65.5), 0), component))

        main_pdf = code2Main(item_code) if item_code[5:7] == 'KC' else code2pdf(item_code)
        with fitz.open(main_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)

        linking = ListOverlayObject(0, Coord(Ratio.mm_to_px(134), Ratio.mm_to_px(59), 0), Ratio.mm_to_px(347), 0)
        solving = ListOverlayObject(0, Coord(Ratio.mm_to_px(134), Ratio.mm_to_px(347), 0), Ratio.mm_to_px(347), 0)
        for solution_info in solutions_info:
            sol_commentary_data = self.get_commentary_data()
            if solution_info.hexcode not in sol_commentary_data:
                continue
            so = self.bake_solution_object(solution_info, sTF[solution_info.hexcode], main_pdf)
            if so is None:
                continue

            if sol_commentary_data[solution_info.hexcode][:1] == 'S':
                linking.add_child(so)
            else:
                solving.add_child(so)

        left_page.add_child(linking)
        solving.coord.y -= solving.get_height()
        solving_bar_component = self.get_component_on_resources(38)
        solving_bar = ComponentOverlayObject(0, Coord(Ratio.mm_to_px(134), Ratio.mm_to_px(
            347) - solving_bar_component.src_rect.height - solving.get_height(), 0), solving_bar_component)
        left_page.add_child(solving)
        left_page.add_child(solving_bar)

        return left_page

    def build(self):
        new_doc = fitz.open()

        self.resources_pdf = RESOURCES_PATH + "/squeeze_main_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

        self.overlayer = Overlayer(new_doc)

        item_list = self.get_item_list()
        if len(item_list) == 0:
            return None

        for i in range(len(item_list)):
            self.overlayer.add_page(self.get_component_on_resources(12))
            right_page = self.build_right(item_list[i]['item_code'], i*2)
            right_page.overlay(self.overlayer, Coord(0,0,0))
            self.overlayer.add_page(self.get_component_on_resources(45))
            left_page = self.build_left(item_list[i]['item_code'], i*2+1)
            left_page.overlay(self.overlayer, Coord(0,0,0))

        for page_num in range(self.overlayer.doc.page_count):
            self.add_unit_title(page_num, self.get_unit_title(self.topic))

        self.resources_doc.close()
        return new_doc