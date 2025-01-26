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
    def __init__(self, items):
        self.items = items

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)
    
    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer, base):
        if num % 2 == 0:
            overlayer.add_page(base)
            #append left area
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(25.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(303), 0)
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
        unit_cover = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(30))
        unit_cover.add_child(ComponentOverlayObject(0, Coord(0,0,0), component))
        unit_cover.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(49), Ratio.mm_to_px(6), 1), "Pretendard-Bold.ttf", 13, f"{num}. {self.get_unit_title(unit_code)}", tuple([int(num%3 == 1)]*3), fitz.TEXT_ALIGN_CENTER))
        return unit_cover

    def bake_unit(self, unit_code, num, problem_num, unit_problem_answers):
        unit = self.bake_unit_cover(unit_code, num)
        component = self.get_component_on_resources(5+(num-1)%3)
        cnt = len(unit_problem_answers)
        for i in range(1,(cnt-1)//5+1):
            unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), component))
            unit.height += component.src_rect.height
        if cnt%5 != 0:
            rect = component.src_rect
            rect.x1 = rect.x0 + Ratio.mm_to_px(9.8) * 2 * (cnt%5) - 1
            last_component = Component(self.resources_pdf, 5+(num-1)%3, rect)
            unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), last_component))
            unit.height += last_component.src_rect.height
        else:
            unit.add_child(ComponentOverlayObject(0, Coord(0,unit.get_height(),0), component))
            unit.height += component.src_rect.height
        
        default_y = Ratio.mm_to_px(30+6.5)
        default_num_x = Ratio.mm_to_px(4.9)
        default_ans_x = Ratio.mm_to_px(14.7)
        for i in range(len(unit_problem_answers)):
            unit.add_child(TextOverlayObject(0, Coord(default_num_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(10)*(i//5), 1), "Pretendard-Medium.ttf", 13, f"{i+problem_num}", tuple([int(num%3 == 1)]*3), fitz.TEXT_ALIGN_CENTER))
            unit.add_child(TextOverlayObject(0, Coord(default_ans_x+Ratio.mm_to_px(19.6)*(i%5), default_y+Ratio.mm_to_px(10)*(i//5), 1), "NanumSquareNeo-cBd.ttf", 13, f"{unit_problem_answers[i]}", tuple([0]), fitz.TEXT_ALIGN_CENTER))
        return unit

    def build(self):
        new_doc = fitz.open()
        
        self.resources_pdf = RESOURCES_PATH + "/weekly_ans_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

        self.overlayer = Overlayer(new_doc)
        base = self.get_component_on_resources(1)
        paragraph = ParagraphOverlayObject()
        paragraph_cnt = 0
        unit_problem_answers = []
        unit_num = 0
        for topic_set in self.items:
            for item in topic_set[1]:
                item_code = item["item_code"]
                item_pdf = get_item_path(item_code) + f"/{item_code[2:5]}/{item_code}/{item_code}.pdf"
                unit_problem_answers.append(self.get_problem_answer(item_pdf))
            unit_num += 1
            unit = self.bake_unit(topic_set[0], unit_num, topic_set[1][0]['item_num'], unit_problem_answers)
            unit_problem_answers = []
            paragraph_cnt = self.add_child_to_paragraph(paragraph, unit, paragraph_cnt, self.overlayer, base)
            paragraph.add_child(AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(15)))

        paragraph.overlay(self.overlayer, Coord(0,0,0))
        #new_doc.save("output/weekly_ans_test.pdf")
        self.resources_doc.close()
        return new_doc
        pass