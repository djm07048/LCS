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
import json

def get_problem_dict(path):
    folder_path = Path(path)
    pdf_files = folder_path.glob('**/*.pdf')

    problem_dict = dict()
    for pdf_file in pdf_files:
        pdf_src_path = str(pdf_file)
        item_code = pdf_file.stem
        problem_dict[item_code] = pdf_src_path
    return problem_dict

def get_problem_list(file_path):
    with open(file_path, 'r') as file:
        return file.readline().split(',')

class AnswerBuilder:
    def __init__(self, proitems, mainitems):
        self.proitems = proitems
        self.mainitems = mainitems

    def get_proitems_list(self):
        # Return the list of proitems directly
        return list(self.proitems)

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer, base):
        if num % 2 == 0:
            overlayer.add_page(base)
            #append left area
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(25.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 0)
            #paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(25.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 0)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        else:
            #append right area on last page
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(136.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 0)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        pass

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer, base):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph(paragraph, num, overlayer, base)
        paragraph.add_child(child)
        return num+1

    def get_problem_answer(self, item_pdf):
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            return answer

    def get_unit_title(self, unit_code):
        with open(RESOURCES_PATH + "/topic.json", encoding='UTF8') as file:
            topic_data = json.load(file)
        return topic_data[unit_code]

    def bake_unit_cover(self, unit_code, num):
        component = self.get_component_on_resources(2+(num-1)%3)
        unit_cover = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(20))
        unit_cover.add_child(ComponentOverlayObject(0, Coord(0,0,0), component))
        if unit_code == 'Main':
            unit_title = '주요 문항 A to Z'
        elif unit_code == 'Mini':
            unit_title = f'주요 문항 총정리'
        else:
            unit_title = f'{num-1}. {self.get_unit_title(unit_code)}'
        unit_cover.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(49), Ratio.mm_to_px(6), 1), "Pretendard-ExtraBold.ttf", 13, f"{unit_title}", tuple([0, 0, 0, int(num%3 == 0)]), fitz.TEXT_ALIGN_CENTER))
        return unit_cover

    def bake_unit(self, unit_code, num, unit_problem_numbers, unit_problem_answers):
        unit = self.bake_unit_cover(unit_code, num)
        component = self.get_component_on_resources(5+(num-1)%3)
        cnt = len(unit_problem_answers)

        #5문항씩 묶어서 박스 추가
        for i in range(1,(cnt-1)//5+1):
            unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), component))
            unit.height += component.src_rect.height

        #5문항 미만일 때 문항 추가
        if cnt%5 != 0:
            rect = component.src_rect
            rect.x1 = rect.x0 + Ratio.mm_to_px(9.8) * 2 * (cnt%5) - 1
            last_component = Component(self.resources_pdf, 5+(num-1)%3, rect)
            unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), last_component))
            unit.height += last_component.src_rect.height
        #5번째 문항은 오른쪽으로 밀지 않고 문항 추가
        else:
            unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), component))
            unit.height += component.src_rect.height

        default_y = Ratio.mm_to_px(20+6.5)
        default_num_x = Ratio.mm_to_px(4.9)
        default_ans_x = Ratio.mm_to_px(14.7)

        if unit_code == 'Main':
            for i in range(len(unit_problem_answers)):
                unit.add_child(TextOverlayObject(0, Coord(default_num_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(11)*(i//5), 1), "Montserrat-Bold.ttf", 13, f"{unit_problem_numbers[i]}", tuple([0, 0, 0, int(num%3 == 0)]), fitz.TEXT_ALIGN_CENTER))
                unit.add_child(TextOverlayObject(0, Coord(default_ans_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(11)*(i//5), 1), "NanumSquareNeo-cBd.ttf", 13, f"{unit_problem_answers[i]}", (0, 0, 0, 1), fitz.TEXT_ALIGN_CENTER))
        else:
            for i in range(len(unit_problem_answers)):
                unit.add_child(TextOverlayObject(0, Coord(default_num_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(11)*(i//5), 1), "Pretendard-ExtraBold.ttf", 13, f"{unit_problem_numbers[i]}", tuple([0, 0, 0, int(num%3 == 0)]), fitz.TEXT_ALIGN_CENTER))
                unit.add_child(TextOverlayObject(0, Coord(default_ans_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(11)*(i//5), 1), "NanumSquareNeo-cBd.ttf", 13, f"{unit_problem_answers[i]}", (0, 0, 0, 1), fitz.TEXT_ALIGN_CENTER))
        return unit

    def build(self):
        new_doc = fitz.open()

        self.resources_pdf = RESOURCES_PATH + "/squeeze_ans_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

        self.overlayer = Overlayer(new_doc)

        base = self.get_component_on_resources(1)
        paragraph = ParagraphOverlayObject()

        paragraph_cnt = 0
        unit_problem_answers = []
        unit_problem_numbers = []
        unit_num = 0

        mainitems_whole = []
        for topic_set in self.mainitems:
            mainitems_whole.extend(topic_set[1])
        mainitems_whole.sort(key=lambda x: x['mainsub'])

        proitems_list = self.get_proitems_list()

        # Ensure each element in proitems_list is a tuple with exactly two elements
        valid_proitems_list = []
        for item in proitems_list:
            if isinstance(item, tuple) and len(item) == 2:
                valid_proitems_list.append(item)
            else:
                print(f"Warning: Invalid item in proitems_list: {item}")

        combined_items = [("Main", mainitems_whole)] + valid_proitems_list if mainitems_whole is not None else valid_proitems_list

        self.proitems = dict(combined_items)

        for topic_set in self.proitems.items():
            for item in topic_set[1]:
                item_code = item["item_code"]
                item_pdf = code2pdf(item_code)
                if item_code[5:7] == 'KC':
                    number = item['item_num']
                else:
                    number = item['mainsub']
                unit_problem_numbers.append(number)
                unit_problem_answers.append(self.get_problem_answer(item_pdf))
            unit_num += 1

        # 유체3의 경우, 이 부분을 if not Main일 때만 실행
            unit = self.bake_unit(topic_set[0], unit_num, unit_problem_numbers, unit_problem_answers)
            unit_problem_answers = []
            unit_problem_numbers = []
            paragraph_cnt = self.add_child_to_paragraph(paragraph, unit, paragraph_cnt, self.overlayer, base)
            paragraph.add_child(AreaOverlayObject(0, Coord(0, 0, 0), Ratio.mm_to_px(15)))

        paragraph.overlay(self.overlayer, Coord(0, 0, 0))
        self.resources_doc.close()
        return new_doc