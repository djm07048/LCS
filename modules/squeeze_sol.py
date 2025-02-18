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

def get_problem_list(file_path):
    with open(file_path, 'r') as file:
        return file.readline().split(',')

class SolutionBuilder:
    def __init__(self, proitems):
        self.proitems = proitems

    def get_component_on_resources(self, page_num):
        return Component(self.resources_pdf, page_num, self.resources_doc.load_page(page_num).rect)
    
    def get_sol_type_dict(self):
        sol_type_dict = {
            "HA" : 5,
            "HB" : 6,
            "HC" : 7,
            "HD" : 8,
            "HE" : 9,
            "NA" : 10,
            "NB" : 11,
            "NC" : 12,
            "ND" : 13,
            "NE" : 14,
            "EA" : 15,
            "EB" : 16,
            "EC" : 17,
            "arrow" : 18,
            "clip" : 19,
            "check" : 20,
            "exc_mark" : 21,
        }
        return sol_type_dict

    def append_new_list_to_paragraph(self, paragraph: ParagraphOverlayObject, num, overlayer, base):
        if num % 2 == 0:
            overlayer.add_page(base)
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(304), 0)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            #append left area
            pass
        else:
            #append right area on last page
            paragraph_list = ListOverlayObject(num//2, Coord(Ratio.mm_to_px(138.5), Ratio.mm_to_px(34), 0), Ratio.mm_to_px(304), 0)
            paragraph.add_paragraph_list(paragraph_list=paragraph_list)
            pass
        pass

    def add_child_to_paragraph(self, paragraph: ParagraphOverlayObject, child: OverlayObject, num, overlayer, base):
        if paragraph.add_child(child): return num
        self.append_new_list_to_paragraph(paragraph, num, overlayer, base)
        paragraph.add_child(child)
        return num+1

    def get_unit_title(self, unit_code):
        with open(RESOURCES_PATH + "/topic.json", encoding='UTF8') as file:
            topic_data = json.load(file)
        return topic_data[unit_code]

    def bake_unit_cover(self, unit_code, num):
        component = self.get_component_on_resources(2)
        unit_cover = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(24))
        unit_cover.add_child(ComponentOverlayObject(0, Coord(0,0,0), component))
        unit_cover.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(7.5), Ratio.mm_to_px(10), 1), "Cafe24Ohsquare-v2.0.ttf", 25, f"{num}", (0, 0, 0, 0), fitz.TEXT_ALIGN_CENTER))
        unit_cover.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(20), Ratio.mm_to_px(10), 1), "Pretendard-SemiBold.ttf", 16.5, f"{self.get_unit_title(unit_code)}", (0, 0, 0, 1), fitz.TEXT_ALIGN_LEFT))

        return unit_cover

    def bake_problem_title(self, num, answer):
        problem_title = AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(7))
        problem_title.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(1), Ratio.mm_to_px(5.5), 1), "Montserrat-Bold.ttf", 17, f"{num:02d}", (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT))
        problem_title.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(12), Ratio.mm_to_px(5.5), 1), "Pretendard-Bold.ttf", 11, "정답", (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT))
        problem_title.add_child(TextOverlayObject(0, Coord(Ratio.mm_to_px(19.5), Ratio.mm_to_px(5.5), 1), "NanumSquareB.ttf", 11, f"{answer}", (1, 0, 0, 0), fitz.TEXT_ALIGN_LEFT))

        return problem_title

    def bake_solutions(self, commentary_data, item_pdf, solutions_info, sTF):
        solutions = []
        for solution_info in solutions_info:
            if commentary_data[solution_info.hexcode] == "answer":
                continue
            solution_object = AreaOverlayObject(0, Coord(0,0,0), 0)
            solution_component = Component(item_pdf, 0, solution_info.rect)
            sol_type_dict = self.get_sol_type_dict()
            if commentary_data.get(solution_info.hexcode) not in sol_type_dict:
                continue
            res_page_num = sol_type_dict[commentary_data[solution_info.hexcode]]
            type_component = self.get_component_on_resources(res_page_num)
            OX_component = None
            if sTF[solution_info.hexcode] == 1:
                OX_component = self.get_component_on_resources(3)
            if sTF[solution_info.hexcode] == 0:
                OX_component = self.get_component_on_resources(4)
            if OX_component is not None:
                solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(-1), 0, 2), OX_component))

            solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(-1), 0, 1), type_component))
            solution_object.add_child(ComponentOverlayObject(0, Coord(Ratio.mm_to_px(5.5), 0, 1), solution_component))
            solution_object.height = solution_info.rect.height

            solutions.append(solution_object)

        return solutions
                
    def bake_problem(self, commentary_data, item_pdf, problem_num):
        objects = []
        with fitz.open(item_pdf) as file:
            ic = ItemCropper()
            solutions_info = ic.get_solution_infos_from_file(file, 10)
            sTF = ic.get_TF_of_solutions_from_file(file, 10)
            answer = ic.get_answer_from_file(file)
            objects.append(self.bake_problem_title(problem_num, answer))
            objects += self.bake_solutions(commentary_data, item_pdf, solutions_info, sTF)
        return objects

    def build(self):
        fitz.TOOLS.debug = True
        new_doc = fitz.open()

        #setup
        sol_type_dict = self.get_sol_type_dict()

        with open(RESOURCES_PATH + "/commentary.json") as file:
            commentary_data = json.load(file)

        self.resources_pdf = RESOURCES_PATH + "/squeeze_sol_resources.pdf"
        self.resources_doc = fitz.open(self.resources_pdf)

        self.overlayer = Overlayer(new_doc)
        base = self.get_component_on_resources(1)
        # overlayer.add_page(base)
        paragraph = ParagraphOverlayObject()

        paragraph_cnt = 0
        unit_num = 0
        for topic_set in self.proitems:
            self.append_new_list_to_paragraph(paragraph, paragraph_cnt, self.overlayer, base)
            paragraph_cnt += 1
            unit_num += 1
            unit_cover = self.bake_unit_cover(topic_set[0], unit_num)
            paragraph_cnt = self.add_child_to_paragraph(paragraph, unit_cover, paragraph_cnt, self.overlayer, base)

            for item in topic_set[1]:
                item_code = item["item_code"]
                item_pdf = get_item_path(item_code) + f"/{item_code[2:5]}/{item_code}/{item_code}.pdf"
                problem_objects = self.bake_problem(commentary_data, item_pdf, item["item_num"])

                #bind first two object
                height = problem_objects[0].get_height() + problem_objects[1].get_height()
                if paragraph.child[-1].left_height < height:
                    self.append_new_list_to_paragraph(paragraph, paragraph_cnt, self.overlayer, base)
                    paragraph_cnt += 1

                for problem_object in problem_objects:
                    paragraph_cnt = self.add_child_to_paragraph(paragraph, problem_object, paragraph_cnt, self.overlayer, base)
                paragraph.add_child(AreaOverlayObject(0, Coord(0,0,0), Ratio.mm_to_px(20))) #minimal space between problems

        paragraph.overlay(self.overlayer, Coord(0,0,0))

        self.resources_doc.close()

        return new_doc
        pass


    pass