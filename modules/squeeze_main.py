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
from utils.parse_code import *
from item_cropper import ItemCropper
import json
# KC이면 문항은 original, 해설은 Main에서 가져옴
# KC가 아니면 문항은 pdf, 해설도 pdf에서 가져옴


def get_problem_dict(path):
    folder_path = Path(path)
    pdf_files = folder_path.glob('**/*.pdf')

    problem_dict = dict()
    for pdf_file in pdf_files:
        pdf_src_path = str(pdf_file)
        item_code = pdf_file.stem
        problem_dict[item_code] = pdf_src_path
    return problem_dict

def get_item_json():
    with open("input/squeeze_item.json", encoding='UTF8') as file:
        item_data = json.load(file)
    return item_data

class MainsolBuilder:
    def __init__(self, topic, mainitems):
        self.topic = topic
        self.mainitems = mainitems


    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def get_item_list(self):
        item_list = []
        for item in self.mainitems:
            if item['mainsub'] is not None:
                item_list.append(item)
        
        return item_list

    def get_problem_component(self, item_code):
        ic = ItemCropper()
        item_pdf = parse_item_original_path(item_code) if item_code[5:7] == 'KC' else parse_item_pdf_path(item_code)
        with fitz.open(item_pdf) as file:
            page = file.load_page(0)
            component = Component(item_pdf, 0, page.rect) if item_code[5:7] == 'KC'\
                else Component(item_pdf, 0, ic.get_problem_rect_from_file(file, accuracy = 1))
        return component

    def bake_origin(self, item_code):
        if item_code[5:7] == 'KC':
            source = self.code_to_text(item_code)
            to = TextOverlayObject(0, Coord(0, 0, 0), "Pretendard-Regular.ttf", 12, source, (1, 1, 1),
                                   fitz.TEXT_ALIGN_CENTER)
            to.get_width()
            box = ShapeOverlayObject(0, Coord(0, 0, 0),
                                     Rect(0, 0, Ratio.mm_to_px(4) + to.get_width(), Ratio.mm_to_px(5.5)),
                                     (0, 0, 0, 0.5), 0.5 / 5.5)
            to.coord = Coord(box.rect.width / 2, Ratio.mm_to_px(4.3), 0)
            box.add_child(to)
        else:
            with fitz.open(RESOURCES_PATH + "/squeeze_pro_resources.pdf") as file:
                compo = Component(RESOURCES_PATH + "/squeeze_pro_resources.pdf", 6, file.load_page(6).rect)
                box = ComponentOverlayObject(0, Coord(0, 0, 0), compo)
                box.rect = compo.src_rect  # Ensure the rect attribute is set
        return box

    def code_to_text(self, problem_code):
        subject_text = {
            'P1' : '물1',
            'P2' : '물2',
            'C1' : '화1',
            'C2' : '화2',
            'B1' : '생1',
            'B2' : '생2',
            'E1' : '지1',
            'E2' : '지2',
        }
        month_text = {
            '06' : '6월',
            '09' : '9월',
            '11' : '대수능',
            '01' : '예비시행',
        }
        return f"20{problem_code[7:9]}학년도 {month_text[problem_code[9:11]]} {int(problem_code[11:13])}번 {subject_text[problem_code[0:2]]}"

    def build_right(self, item_code, page_num):
        # Main Solution 우수 Page: 문항 번호, 문제 이미지, 원본 이미지, 해설 조각

        for item in self.get_item_list():
            if item['item_code'] == item_code:
                item_num = item['mainsub']
        right_page = AreaOverlayObject(page_num, Coord(0,0,0), Ratio.mm_to_px(371))
        origin = self.bake_origin(item_code)


        component = self.get_problem_component(item_code)
        right_page.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(118), Ratio.mm_to_px(46), 0), component))
        right_page.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(108), Ratio.mm_to_px(59), 0), "Montserrat-Bold.ttf", 48, item_num, (1, 0, 0, 0), fitz.TEXT_ALIGN_RIGHT))
        origin.coord = Coord(Ratio.mm_to_px(108)-origin.rect.width, Ratio.mm_to_px(64), 0)
        right_page.add_child(origin)
        white_box = ShapeOverlayObject(0,  Coord(Ratio.mm_to_px(118-0.5), Ratio.mm_to_px(46), 0), Rect(0, 0, Ratio.mm_to_px(3.0+0.5), Ratio.mm_to_px(5.5)), (1, 1, 1))
        right_page.add_child(white_box)

        y_end = 46 + Ratio.px_to_mm(component.src_rect.height)

        # 최대 사이즈를 기본 값으로 설정
        memo_component = self.get_component_on_resources(43)
        if y_end < 180: memo_component = self.get_component_on_resources(39)
        elif y_end < 197.5: memo_component = self.get_component_on_resources(40)
        elif y_end < 211: memo_component = self.get_component_on_resources(41)
        elif y_end < 238: memo_component = self.get_component_on_resources(42)
        elif y_end < 278.5: memo_component = self.get_component_on_resources(43)
        right_page.add_child(ComponentOverlayObject(0, Coord(0,0,0), memo_component))
        return right_page

    def get_sol_type_dict(self):
        sol_type_dict = {
            "HA" : 15,
            "HB" : 16,
            "HC" : 17,
            "HD" : 18,
            "HE" : 19,
            "NA" : 20,
            "NB" : 21,
            "NC" : 22,
            "ND" : 23,
            "NE" : 24,
            "EA" : 25,
            "EB" : 26,
            "EC" : 27,
            "arrow" : 28,
            "clip" : 29,
            "check" : 30,
            "exc_mark" : 31,
            "SA" : 32,
            "SB" : 33,
            "SC" : 34,
            "SD" : 35,
            "SE" : 36,

            "answer": 44,
        }
        return sol_type_dict

    def get_commentary_data(self):
        with open(RESOURCES_PATH + "/commentary.json") as file:
            commentary_data = json.load(file)
        return commentary_data

    def bake_solution_object(self, solution_info, TF, item_pdf):
        solution_object = AreaOverlayObject(0, Coord(0,0,0), 0)
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
            OX_component = self.get_component_on_resources(13)
        if TF == 0:
            OX_component = self.get_component_on_resources(14)
        if OX_component is not None:
            solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(0), 0, 1), OX_component))

        solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(6.5), 0, 2), solution_component))
        solution_object.height = solution_info.rect.height

        return solution_object

    def build_left(self, item_code, page_num):
        for item in self.get_item_list():
            if item['item_code'] == item_code:
                item_num = item['mainsub']
        left_page = AreaOverlayObject(page_num, Coord(0, 0, 0), Ratio.mm_to_px(371))
        left_page.add_child(
            TextOverlayObject(0, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(59), 0), "Montserrat-Bold.ttf", 48, item_num,
                              (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT))
        origin = self.bake_origin(item_code)
        origin.coord = Coord(Ratio.mm_to_px(38), Ratio.mm_to_px(59) - origin.rect.height, 0)
        left_page.add_child(origin)

        white_box = ShapeOverlayObject(0,  Coord(Ratio.mm_to_px(18-8), Ratio.mm_to_px(65.5), 0), Rect(0, 0, Ratio.mm_to_px(3+8), Ratio.mm_to_px(5.5)), (1,1,1))
        left_page.add_child(white_box)

        component = self.get_problem_component(item_code)
        if isinstance(component, str):
            component = Component(component, 0, fitz.Rect(0, 0, 0, 0))  # Create a Component object if it's a string

        if not hasattr(component, 'src_pdf'):
            raise AttributeError(f"Component does not have 'src_pdf' attribute: {component}")

        left_page.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(18), Ratio.mm_to_px(65.5), 0), component))

        main_pdf = parse_item_Main_path(item_code) if item_code[5:7] == 'KC' else parse_item_pdf_path(item_code)
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
    
    def get_unit_title(self, unit_code):
        with open(RESOURCES_PATH + "/topic.json", encoding='UTF8') as file:
            topic_data = json.load(file)
        return topic_data[unit_code]
    
    def add_unit_title(self, page_num, title):
        if page_num % 2 == 1:
            unit_title_object = TextOverlayObject(page_num, Coord(Ratio.mm_to_px(28), Ratio.mm_to_px(18.5), 4), "Pretendard-ExtraBold.ttf", 22, title, (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT)
            unit_title_object.overlay(self.overlayer, unit_title_object.coord)

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
            self.overlayer.add_page(self.get_component_on_resources(11))
            left_page = self.build_left(item_list[i]['item_code'], i*2+1)
            left_page.overlay(self.overlayer, Coord(0,0,0))

        for page_num in range(self.overlayer.doc.page_count):
            self.add_unit_title(page_num, self.get_unit_title(self.topic))

        self.resources_doc.close()
        return new_doc